import boto3
from django.conf import settings

def s3_client():
    cfg = settings.MINIO
    print(cfg)
    return boto3.client(
        "s3",
        endpoint_url=cfg["ENDPOINT_URL"],
        aws_access_key_id=cfg["ACCESS_KEY"],
        aws_secret_access_key=cfg["SECRET_KEY"],
        region_name=cfg["REGION"],
    )

def presign_put(bucket_key: str, content_type: str, content_length: int):
    client = s3_client()
    params = {
        "Bucket": settings.MINIO["BUCKET"],
        "Key": bucket_key,
    }
    return client.generate_presigned_url(
        ClientMethod="put_object",
        Params={**params, "ContentType": content_type, "ContentLength": content_length},
        ExpiresIn=settings.MINIO["URL_TTL"],
    )

def presign_get(bucket_key: str):
    client = s3_client()
    params = {"Bucket": settings.MINIO["BUCKET"], "Key": bucket_key}
    return client.generate_presigned_url(
        ClientMethod="get_object",
        Params=params,
        ExpiresIn=settings.MINIO["URL_TTL"],
    )
