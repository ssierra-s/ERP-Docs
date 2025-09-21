from django.db import transaction
from django.utils import timezone
from .models import Document, ValidationStep, ValidationAction, DomainEntity
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

import os, uuid
import boto3
from botocore.client import Config

# Cliente para MinIO o S3
class S3Client:
    def __init__(self):
        self.bucket = os.getenv('AWS_S3_BUCKET')  # Nombre del bucket
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.expires = int(os.getenv('AWS_PRESIGN_EXPIRE_SECONDS', '600'))  # Tiempo de expiración en segundos

        # Crear sesión y cliente boto3 para MinIO o AWS S3
        session = boto3.session.Session(
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=self.region
        )
        
        # Cliente para la conexión con MinIO o S3
        self.client = session.client('s3', endpoint_url=os.getenv('AWS_ENDPOINT_URL'),
                                     config=Config(signature_version='s3v4'))

    def presign_put(self, key: str, mime: str, size: int) -> str:
        """Genera una URL pre-firmada para la subida (PUT) de un archivo al bucket"""
        return self.client.generate_presigned_url(
            ClientMethod='put_object',
            Params={'Bucket': self.bucket, 'Key': key, 'ContentType': mime},
            ExpiresIn=self.expires,
            HttpMethod='PUT'
        )
    
    def presign_get(self, key: str) -> str:
        """Genera una URL pre-firmada para la descarga (GET) de un archivo"""
        return self.client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=self.expires
        )


# Función para crear un documento y asignar un flujo de validación
def create_document_with_optional_flow(creator, company_id, entity_type, entity_id, doc_payload, flow_payload=None):
    """
    Crea un documento en la base de datos y opcionalmente agrega un flujo de validación.
    
    :param creator: El usuario que está creando el documento (puede ser None si no es necesario).
    :param company_id: El ID de la empresa asociada.
    :param entity_type: El tipo de entidad asociada (por ejemplo, 'vehicle', 'employee', etc.)
    :param entity_id: El ID de la entidad asociada.
    :param doc_payload: Los metadatos del documento (nombre, tipo MIME, etc.).
    :param flow_payload: Los pasos del flujo de validación (si se proporcionan).
    :return: El documento creado.
    """
    # Si no se pasa un creador, asignamos un "usuario anónimo" predeterminado
    if creator is None:
        creator = User.objects.first()  # Asume que tienes al menos un usuario en tu DB
        if not creator:
            # Si no hay usuarios en la base de datos, asignamos un valor predeterminado (crea un usuario ficticio si es necesario)
            creator = User.objects.create(username="anonymous_user", password="anonymous_password")

    with transaction.atomic():
        # Crear la entidad (si no existe) o obtenerla
        entity, created = DomainEntity.objects.get_or_create(
            company_id=company_id,
            entity_type=entity_type,
            external_id=entity_id
        )

        # Crear el documento
        document = Document.objects.create(
            company_id=company_id,
            entity=entity,  # Asignamos la relación con la entidad
            name=doc_payload['name'],
            mime_type=doc_payload['mime_type'],
            size_bytes=doc_payload['size_bytes'],
            bucket_key=doc_payload['bucket_key'],
            content_hash=doc_payload.get('content_hash', ''),
            validation_status='P',  # Inicialmente, el estado es Pendiente
            created_by=creator,  # Asignamos el creador
        )
        
        # Si hay un flujo de validación, lo agregamos
        if flow_payload:
            for step in flow_payload['steps']:
                # Convertir el 'approver_user_id' a UUID
                approver_user_id = uuid.UUID(step['approver_user_id'])  # Asegúrate de que sea un UUID válido

                # Obtener la instancia de User usando el UUID
                approver = get_user_model().objects.get(id=approver_user_id)

                # Crear el paso de validación
                ValidationStep.objects.create(
                    document=document,
                    order=step['order'],
                    approver=approver,  # Pasamos la instancia de User
                    status='P',  # Todos los pasos empiezan como Pendientes
                )
        
        return document

# Función para rechazar un documento
def reject_document(*, document, actor, reason=""):
    """
    Marca un documento como rechazado, actualizando todos los pasos de validación asociados.
    
    :param document: El documento que será rechazado.
    :param actor: El usuario que realiza el rechazo.
    :param reason: La razón del rechazo (opcional).
    :return: El documento actualizado con el estado de rechazo.
    """
    # Obtén los pasos de validación asociados al documento
    steps = list(document.steps.all())

    # Verifica si el actor tiene permisos para rechazar este documento
    if not any(st.approver_id == actor.id for st in steps):
        raise PermissionError('El usuario no está autorizado para rechazar este documento.')

    # Marcar como rechazado el paso del actor
    actor_steps = [st for st in steps if st.approver_id == actor.id]
    for st in actor_steps:
        st.status = 'R'
        st.acted_at = timezone.now()
        st.save()

    # Registrar la acción de rechazo
    ValidationAction.objects.create(document=document, actor=actor, action='reject', reason=reason)

    # Marcar el documento como rechazado y bloquear nuevas acciones
    document.validation_status = 'R'
    document.save()

    return document

# Función para aprobar un documento
def approve_document(*, document, actor, reason=""):
    steps = list(document.steps.select_related('approver').order_by('order'))

    # Verificamos si el actor tiene permisos para aprobar el documento
    actor_steps = [st for st in steps if st.approver_id == actor.id]
    if not actor_steps:
        raise PermissionError('El usuario no está autorizado para aprobar este documento.')

    # Aprobar el paso de mayor jerarquía
    actor_step = sorted(actor_steps, key=lambda s: s.order)[-1]
    actor_step.status = 'A'
    actor_step.acted_at = timezone.now()
    actor_step.save()

    # Aprobar los pasos anteriores si es el de mayor jerarquía
    for st in steps:
        if st.order < actor_step.order and st.status == 'P':
            st.status = 'A'
            st.acted_at = timezone.now()
            st.save()

    # Si el actor aprobó el último paso, actualizar el estado del documento a Aprobado
    highest_order = max(s.order for s in steps)
    if actor_step.order == highest_order and all(s.status == 'A' for s in steps):
        document.validation_status = 'A'
        document.save()

    return document