from rest_framework import status, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Document, ValidationStep
from .services import S3Client, create_document_with_optional_flow, approve_document, reject_document
from .serializers import DocumentCreateSerializer, DocumentDetailSerializer


class DocumentCreateView(views.APIView):
    # No es necesario ningún permiso de autenticación si deseas permitir acceso anónimo
    def post(self, request):
        # Validamos los datos del documento
        ser = DocumentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        payload = ser.validated_data

        # Generar la URL pre-firmada para la subida del archivo
        bucket_key = f"companies/{payload['company_id']}/vehicles/{payload['entity']['entity_id']}/docs/{payload['document']['name']}"
        mime_type = payload['document']['mime_type']  # Tipo MIME del archivo (por ejemplo, application/pdf)
        s3_client = S3Client()
        upload_url = s3_client.presign_put(bucket_key, mime_type, size=payload['document']['size_bytes'])

        # Creamos el documento en la base de datos y el flujo de validación (si es proporcionado)
        doc = create_document_with_optional_flow(
            creator=None,  # No se asigna un creador si no se requiere autenticación
            company_id=payload['company_id'],
            entity_type=payload['entity']['entity_type'],
            entity_id=payload['entity']['entity_id'],
            doc_payload=payload['document'],
            flow_payload=payload.get('validation_flow')
        )

        # Devolvemos la URL pre-firmada y los detalles del documento creado
        return Response({
            'document': DocumentDetailSerializer(doc).data,
            'upload_url': upload_url  # URL para subir el archivo
        }, status=status.HTTP_201_CREATED)


# Vista para descargar un documento
class DocumentDownloadView(views.APIView):
    def get(self, request, document_id):
        # Recuperamos el documento
        doc = get_object_or_404(Document, id=document_id)

        # Generamos la URL pre-firmada para la descarga
        s3_client = S3Client()
        download_url = s3_client.presign_get(doc.bucket_key)

        return Response({'download_url': download_url, 'validation_status': doc.validation_status})


# Vista para aprobar un documento
class DocumentApproveView(views.APIView):
    def post(self, request, document_id):
        # Recuperamos el documento y el actor (usuario)
        document = get_object_or_404(Document, id=document_id)
        actor = request.user  # El actor es el usuario autenticado

        # Llamamos a la función de aprobación
        updated_document = approve_document(document=document, actor=actor, reason=request.data.get('reason', ''))

        return Response({
            'document_id': str(updated_document.id),
            'validation_status': updated_document.validation_status or 'P'
        })


# Vista para rechazar un documento
class DocumentRejectView(views.APIView):
    def post(self, request, document_id):
        # Recuperamos el documento y el actor (usuario)
        document = get_object_or_404(Document, id=document_id)
        actor = request.user  # El actor es el usuario autenticado

        # Llamamos a la función de rechazo
        updated_document = reject_document(document=document, actor=actor, reason=request.data.get('reason', ''))

        return Response({
            'document_id': str(updated_document.id),
            'validation_status': updated_document.validation_status
        })
