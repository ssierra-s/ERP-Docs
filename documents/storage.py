import os
import boto3
from botocore.client import Config
from .models import Document

class S3Client:
    def __init__(self):
        self.bucket = os.getenv('AWS_S3_BUCKET')  # Nombre del bucket
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.expires = int(os.getenv('AWS_PRESIGN_EXPIRE_SECONDS', '600'))  # Tiempo de expiración de la URL pre-firmada (10 minutos)

        # Configuración del cliente de S3 (MinIO o AWS S3)
        session = boto3.session.Session(
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=self.region
        )

        # Cliente S3
        self.client = session.client('s3', endpoint_url=os.getenv('AWS_ENDPOINT_URL'),
                                     config=Config(signature_version='s3v4'))

    def presign_put(self, key: str, mime: str, size: int) -> str:
        """Genera una URL pre-firmada para subir (PUT) un archivo al bucket"""
        return self.client.generate_presigned_url(
            ClientMethod='put_object',
            Params={'Bucket': self.bucket, 'Key': key, 'ContentType': mime},
            ExpiresIn=self.expires,  # Tiempo de expiración
            HttpMethod='PUT'  # Método PUT para la carga del archivo
        )
    
    def presign_get(self, key: str) -> str:
        """Genera una URL pre-firmada para la descarga (GET) de un archivo desde el bucket"""
        return self.client.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=self.expires  # Tiempo de expiración de la URL pre-firmada
        )
