import uuid
from pathlib import PurePosixPath
import boto3
from botocore.client import Config
from fastapi import HTTPException
from .config import settings

ALLOWED_PREFIXES = {"media", "documents", "images", "logos", "profiles", "news", "events", "sermons", "chat"}

def client():
    if not all([settings.r2_endpoint, settings.r2_bucket, settings.r2_access_key_id, settings.r2_secret_access_key]):
        raise HTTPException(503, "Stockage R2 non configuré")
    return boto3.client(
        "s3", endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto", config=Config(signature_version="s3v4")
    )

def safe_key(prefix: str, filename: str) -> str:
    prefix = prefix.strip("/").split("/")[0]
    if prefix not in ALLOWED_PREFIXES:
        raise HTTPException(400, "Dossier de stockage non autorisé")
    name = PurePosixPath(filename).name.replace(" ", "_")
    if not name or name in {".", ".."}:
        raise HTTPException(400, "Nom de fichier invalide")
    return f"{prefix}/{uuid.uuid4().hex}/{name}"

def presigned_put(key: str, content_type: str):
    return client().generate_presigned_url(
        "put_object", Params={"Bucket": settings.r2_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=settings.r2_presign_expiry_seconds, HttpMethod="PUT"
    )

def presigned_get(key: str):
    if settings.r2_public_base_url:
        return settings.r2_public_base_url.rstrip("/") + "/" + key
    return client().generate_presigned_url("get_object", Params={"Bucket": settings.r2_bucket, "Key": key}, ExpiresIn=settings.r2_presign_expiry_seconds)

def delete(key: str):
    client().delete_object(Bucket=settings.r2_bucket, Key=key)
