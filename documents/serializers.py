from rest_framework import serializers
from .models import Company, CompanyMembership, EntityRef, Document, ValidationFlow, ValidationStep
from django.contrib.auth import get_user_model

User = get_user_model()


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "legal_name", "created_at"]


class CompanyMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = CompanyMembership
        fields = ["id", "company", "user_id", "approval_level"]

    def create(self, validated_data):
        user = User.objects.get(id=validated_data.pop("user_id"))
        return CompanyMembership.objects.create(user=user, **validated_data)


class EntityRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityRef
        fields = ["id", "company", "entity_type", "external_id", "created_at"]


class DocumentCreateSerializer(serializers.Serializer):
    company_id = serializers.UUIDField()
    entity = serializers.DictField()
    document = serializers.DictField()
    validation_flow = serializers.DictField(required=False)

    def validate(self, attrs):
        # Validaciones mínimas
        doc = attrs["document"]
        for k in ["name", "mime_type", "size_bytes", "bucket_key"]:
            if k not in doc:
                raise serializers.ValidationError(f"document.{k} requerido")
        ent = attrs["entity"]
        for k in ["entity_type", "entity_id"]:
            if k not in ent:
                raise serializers.ValidationError(f"entity.{k} requerido")
        return attrs


class DocumentOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id","company","entity","created_by","name","mime_type",
            "size_bytes","bucket_key","sha256","validation_status","created_at"
        ]
        depth = 1
