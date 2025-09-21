from django.db import transaction
from django.utils import timezone
from .models import Document, ValidationFlow, ValidationStep, ValidationAction, CompanyMembership


def can_act_on_document(user, document: Document) -> bool:
    # Seguridad mínima: el usuario debe pertenecer a la empresa del documento
    return CompanyMembership.objects.filter(company=document.company, user=user).exists()


@transaction.atomic
def create_document_with_optional_flow(*, creator, company, entity, doc_payload, flow_payload=None) -> Document:
    """
    doc_payload: dict(name, mime_type, size_bytes, bucket_key, sha256?)
    flow_payload: dict(enabled: bool, steps: [{order, approver_user_id}, ...])
    """
    doc = Document.objects.create(
        company=company,
        entity=entity,
        created_by=creator,
        name=doc_payload["name"],
        mime_type=doc_payload["mime_type"],
        size_bytes=doc_payload["size_bytes"],
        bucket_key=doc_payload["bucket_key"],
        sha256=doc_payload.get("sha256"),
        validation_status=None,
    )
    if flow_payload and flow_payload.get("enabled"):
        flow = ValidationFlow.objects.create(document=doc)
        for step in flow_payload.get("steps", []):
            membership = CompanyMembership.objects.get(company=company, user_id=step["approver_user_id"])
            ValidationStep.objects.create(flow=flow, order=step["order"], approver=membership)
        # Si hay pasos, estado inicial = P
        if flow.steps.exists():
            doc.validation_status = "P"
            doc.save(update_fields=["validation_status"])
    return doc


def _highest_order(flow: ValidationFlow) -> int:
    return flow.steps.order_by("order").last().order


@transaction.atomic
def approve_document(*, document: Document, actor_user, reason: str | None = None):
    if not can_act_on_document(actor_user, document):
        raise PermissionError("Sin acceso a la empresa del documento.")

    flow = getattr(document, "validation_flow", None)
    if not flow:
        # No hay validación; nada que hacer
        return document

    # Encontrar el step del actor (puede haber uno por documento)
    try:
        actor_membership = CompanyMembership.objects.get(company=document.company, user=actor_user)
    except CompanyMembership.DoesNotExist:
        raise PermissionError("Usuario no pertenece a la empresa.")

    actor_step = flow.steps.select_for_update().filter(approver=actor_membership).first()
    if not actor_step:
        raise PermissionError("Usuario no es aprobador de este documento.")

    if document.validation_status == "R" or document.validation_status == "A":
        return document  # terminal o ya aprobado

    # Marcar todos los pasos con order <= actor_step.order como aprobados
    now = timezone.now()
    flow.steps.filter(approved_at__isnull=True, rejected_at__isnull=True, order__lte=actor_step.order)\
        .update(approved_at=now)

    ValidationAction.objects.create(document=document, actor=actor_user, action="approve", reason=reason)

    # Si actor es el de mayor jerarquía (order más alto), documento = Aprobado
    if actor_step.order == _highest_order(flow):
        document.validation_status = "A"
        document.save(update_fields=["validation_status"])
    else:
        # Si aún quedan pasos posteriores sin aprobar, mantener en P
        document.validation_status = "P"
        document.save(update_fields=["validation_status"])

    return document


@transaction.atomic
def reject_document(*, document: Document, actor_user, reason: str | None = None):
    if not can_act_on_document(actor_user, document):
        raise PermissionError("Sin acceso a la empresa del documento.")

    flow = getattr(document, "validation_flow", None)
    if not flow:
        return document

    try:
        actor_membership = CompanyMembership.objects.get(company=document.company, user=actor_user)
    except CompanyMembership.DoesNotExist:
        raise PermissionError("Usuario no pertenece a la empresa.")

    actor_step = flow.steps.select_for_update().filter(approver=actor_membership).first()
    if not actor_step:
        raise PermissionError("Usuario no es aprobador de este documento.")

    if document.validation_status == "A" or document.validation_status == "R":
        return document

    actor_step.rejected_at = timezone.now()
    actor_step.save(update_fields=["rejected_at"])

    ValidationAction.objects.create(document=document, actor=actor_user, action="reject", reason=reason)

    # Rechazo es terminal
    document.validation_status = "R"
    document.save(update_fields=["validation_status"])
    return document
