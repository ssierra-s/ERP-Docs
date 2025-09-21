import uuid
from django.conf import settings
from django.db import models

class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class CompanyUser(models.Model):
    """Asocia usuarios a empresas para control de acceso."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, blank=True)
    class Meta:
        unique_together = ('company', 'user')


# Entidad genérica referenciable (vehicle, employee, etc.)
class DomainEntity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    entity_type = models.CharField(max_length=50) # p. ej. 'vehicle', 'employee'
    external_id = models.UUIDField() # id de la entidad en su módulo
    class Meta:
        unique_together = ('company', 'entity_type', 'external_id')

class Document(models.Model):
    STATUS_CHOICES = (
        ('P', 'Pendiente'),
        ('A', 'Aprobado'),
        ('R', 'Rechazado'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='documents')
    entity = models.ForeignKey(DomainEntity, on_delete=models.PROTECT, related_name='documents')

    name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.BigIntegerField()
    bucket_key = models.CharField(max_length=1024)
    content_hash = models.CharField(max_length=128, blank=True)  # opcional

    validation_status = models.CharField(max_length=1, choices=STATUS_CHOICES, null=True, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_documents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.id})"

class ValidationStep(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='steps')
    order = models.PositiveIntegerField()  # mayor = mayor jerarquía
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='approval_steps')
    status = models.CharField(max_length=1, choices=Document.STATUS_CHOICES, default='P')
    acted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('document', 'order')
        ordering = ['order']


class ValidationAction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='actions')
    step = models.ForeignKey(ValidationStep, on_delete=models.SET_NULL, null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=10)  # 'approve' | 'reject' | 'auto-approve'
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
