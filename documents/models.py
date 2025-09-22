import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legal_name = models.CharField(max_length=255, default="Sin nombre legal")
    created_at = models.DateTimeField(default=timezone.now)


class CompanyMembership(models.Model):
    """
    Asocia usuarios a compañías y, opcionalmente, define su nivel de aprobación 1–3.
    """
    APPROVAL_LEVELS = [(1, "L1"), (2, "L2"), (3, "L3")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey( 
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_memberships"
    )
    name = models.CharField(max_length=255)
    approval_level = models.PositiveSmallIntegerField(choices=APPROVAL_LEVELS, null=True, blank=True)

    class Meta:
        unique_together = ("company", "user")


class EntityRef(models.Model):
    """
    Entidad genérica (vehículo, empleado, etc.) por referencia.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="entities")
    entity_type = models.CharField(max_length=64)  # p.ej. "vehicle", "employee"
    external_id = models.UUIDField()               # 👈 añadido porque estaba en unique_together
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("company", "entity_type", "external_id")


class Document(models.Model):
    VALIDATION_STATUS = [
        ("P", "Pendiente"),
        ("A", "Aprobado"),
        ("R", "Rechazado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="documents")
    entity = models.ForeignKey(EntityRef, on_delete=models.CASCADE, related_name="documents")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documents_created"
    )
    name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=128)
    size_bytes = models.BigIntegerField()
    bucket_key = models.CharField(max_length=1024)  # ruta o UUID asignado
    sha256 = models.CharField(max_length=64, null=True, blank=True)
    validation_status = models.CharField(max_length=1, choices=VALIDATION_STATUS, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)


class ValidationFlow(models.Model):
    """
    Flujo por documento. Si existe, el documento inicia en P.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name="validation_flow")
    created_at = models.DateTimeField(default=timezone.now)


class ValidationStep(models.Model):
    """
    order más alto = mayor jerarquía.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    flow = models.ForeignKey(ValidationFlow, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveSmallIntegerField()
    approver = models.ForeignKey(CompanyMembership, on_delete=models.PROTECT, related_name="approval_steps")
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["order"]
        unique_together = ("flow", "order")


class ValidationAction(models.Model):
    """
    Bitácora de acciones: aprobar/rechazar con reason.
    """
    ACTIONS = [("approve", "approve"), ("reject", "reject")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="actions")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=16, choices=ACTIONS)
    reason = models.TextField(null=True, blank=True)
    at = models.DateTimeField(default=timezone.now)

class DocumentEvent(models.Model):
    EVENT_TYPES = [("upload", "Upload"), ("download", "Download")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    at = models.DateTimeField(default=timezone.now)
    meta = models.JSONField(default=dict, blank=True)  # opcional: IP, tamaño, headers

    def __str__(self):
        return f"{self.event_type} - {self.document.name} - {self.at}"

