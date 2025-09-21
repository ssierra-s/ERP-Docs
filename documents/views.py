from rest_framework import status, views, generics
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
import boto3
import json
from django.conf import settings
from rest_framework.views import APIView
from rest_framework import status, permissions
from .models import Company, CompanyMembership, EntityRef, Document
from .serializers import (
    CompanySerializer, CompanyMembershipSerializer,
    EntityRefSerializer, DocumentCreateSerializer, DocumentOutSerializer
)
from .permissions import IsCompanyMember
from .storage import presign_put, presign_get
from .services import create_document_with_optional_flow, approve_document, reject_document


class CompanyCreateView(generics.CreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer


class CompanyMembershipCreateView(generics.CreateAPIView):
    queryset = CompanyMembership.objects.all()
    serializer_class = CompanyMembershipSerializer
    permission_classes = [IsCompanyMember]


class EntityRefCreateView(generics.CreateAPIView):
    queryset = EntityRef.objects.all()
    serializer_class = EntityRefSerializer
    permission_classes = [IsCompanyMember]


class PresignUploadView(views.APIView):
    permission_classes = [IsCompanyMember]

    def post(self, request):
        """
        Body:
        {
          "company_id": "uuid-company",
          "bucket_key": "companies/.../file.pdf",
          "mime_type": "application/pdf",
          "size_bytes": 12345
        }
        """
        company_id = request.data.get("company_id")
        bucket_key = request.data.get("bucket_key")
        mime = request.data.get("mime_type")
        size = int(request.data.get("size_bytes", 0))
        print(company_id)
        if not (company_id and bucket_key and mime and size):
            return Response({"detail": "Parámetros incompletos."}, status=400)
        # Permiso ya se valida con IsCompanyMember
        url = presign_put(bucket_key, mime, size)
        return Response({"upload_url": url}, status=200)


class DocumentCreateView(views.APIView):
    permission_classes = [IsCompanyMember]

    @transaction.atomic
    def post(self, request):
        """
        Crea el registro en BD (el archivo ya debió subirse con presigned PUT).
        """
        ser = DocumentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        payload = ser.validated_data

        company = get_object_or_404(Company, id=payload["company_id"])
        entity_ref, _ = EntityRef.objects.get_or_create(
            company=company,
            entity_type=payload["entity"]["entity_type"],
            external_id=payload["entity"]["entity_id"],
        )
        doc = create_document_with_optional_flow(
            creator=request.user,
            company=company,
            entity=entity_ref,
            doc_payload=payload["document"],
            flow_payload=payload.get("validation_flow"),
        )
        return Response(DocumentOutSerializer(doc).data, status=status.HTTP_201_CREATED)


class DocumentDownloadView(views.APIView):
    def get(self, request, document_id):
        doc = get_object_or_404(Document, id=document_id)
        # Permisos
        IsCompanyMember().has_object_permission(request, self, doc) or Response(status=403)
        url = presign_get(doc.bucket_key)
        return Response({"download_url": url, "validation_status": doc.validation_status}, status=200)


class DocumentApproveView(views.APIView):
    def post(self, request, document_id):
        doc = get_object_or_404(Document, id=document_id)
        actor_user_id = request.data.get("actor_user_id")
        reason = request.data.get("reason")
        # Asegurar que actor sea el propio usuario o que existe (según tu política).
        # Aquí exigimos que quien llama sea el mismo actor.
        if str(request.user.id) != str(actor_user_id):
            return Response({"detail": "actor_user_id debe ser el usuario autenticado."}, status=403)
        updated = approve_document(document=doc, actor_user=request.user, reason=reason)
        return Response({"document_id": str(updated.id), "validation_status": updated.validation_status}, status=200)


class DocumentRejectView(views.APIView):
    def post(self, request, document_id):
        doc = get_object_or_404(Document, id=document_id)
        actor_user_id = request.data.get("actor_user_id")
        reason = request.data.get("reason")
        if str(request.user.id) != str(actor_user_id):
            return Response({"detail": "actor_user_id debe ser el usuario autenticado."}, status=403)
        updated = reject_document(document=doc, actor_user=request.user, reason=reason)
        return Response({"document_id": str(updated.id), "validation_status": updated.validation_status}, status=200)
    

class DocumentDirectUploadView(APIView):
    """
    Endpoint único:
    - Recibe archivo en multipart
    - Lo sube a MinIO con boto3
    - Crea registro en BD
    - Devuelve datos del documento
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        multipart/form-data:
        - company_id (UUID)
        - entity_type
        - entity_id
        - file (binario)
        - validation_flow (JSON opcional, string o dict)
        """
        company_id = request.data.get("company_id")
        entity_type = request.data.get("entity_type")
        entity_id = request.data.get("entity_id")
        file_obj = request.FILES.get("file")
        validation_flow = request.data.get("validation_flow")
        if not (company_id and entity_type and entity_id and file_obj):
            return Response({"detail": "Parámetros incompletos"}, status=400)

        # Parsear validation_flow si viene como string
        if validation_flow and isinstance(validation_flow, str):
            try:
                validation_flow = json.loads(validation_flow)
            except Exception:
                return Response({"detail": "validation_flow no es un JSON válido"}, status=400)

        company = get_object_or_404(Company, id=company_id)
        entity_ref, _ = EntityRef.objects.get_or_create(
            company=company,
            entity_type=entity_type,
            external_id=entity_id,
        )

        # Generar bucket_key
        bucket_key = f"companies/{company_id}/{entity_type}/{entity_id}/docs/{file_obj.name}"

        # Subir directo a MinIO usando boto3
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.MINIO["ENDPOINT_URL"],
            aws_access_key_id=settings.MINIO["ACCESS_KEY"],
            aws_secret_access_key=settings.MINIO["SECRET_KEY"],
            region_name=settings.MINIO["REGION"],
        )

        s3.upload_fileobj(
            Fileobj=file_obj,
            Bucket=settings.MINIO["BUCKET"],
            Key=bucket_key,
            ExtraArgs={"ContentType": file_obj.content_type},
        )

        # Crear documento en BD
        doc = create_document_with_optional_flow(
            creator=request.user,
            company=company,
            entity=entity_ref,
            doc_payload={
                "name": file_obj.name,
                "mime_type": file_obj.content_type,
                "size_bytes": file_obj.size,
                "bucket_key": bucket_key,
            },
            flow_payload=validation_flow,
        )

        return Response({
            "document_id": str(doc.id),
            "bucket_key": bucket_key,
            "validation_status": doc.validation_status,
        }, status=status.HTTP_201_CREATED)