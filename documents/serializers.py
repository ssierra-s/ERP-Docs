from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Company, DomainEntity, Document, ValidationStep, ValidationAction


User = get_user_model()

# Serializer para hacer referencia a una entidad (vehículo, empleado, etc.)
class EntityRefSerializer(serializers.Serializer):
    entity_type = serializers.CharField(max_length=50)
    entity_id = serializers.UUIDField()

# Serializer para crear un documento
class DocumentCreateSerializer(serializers.Serializer):
    company_id = serializers.UUIDField()
    entity = EntityRefSerializer()
    document = serializers.DictField()
    validation_flow = serializers.DictField(required=False)

# Serializer para obtener los detalles del documento
class DocumentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('id', 'name', 'mime_type', 'size_bytes', 'bucket_key', 'validation_status', 'created_at')

# Serializer para aprobar o rechazar un documento
class ApproveRejectSerializer(serializers.Serializer):
    actor_user_id = serializers.UUIDField()
    reason = serializers.CharField(required=False, allow_blank=True)
