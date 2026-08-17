from hashlib import sha256
import json
import os

import boto3
from botocore.config import Config

BUCKET = os.environ["R2_BUCKET_NAME"]
ENDPOINT = os.environ["R2_ENDPOINT"]
ACCESS_KEY = os.environ["R2_ACCESS_KEY_ID"]
SECRET_KEY = os.environ["R2_SECRET_ACCESS_KEY"]

MAX_VIDEO_BYTES = 500 * 1024 * 1024  # 500 MB
UPLOAD_EXPIRY_SECONDS = 900  # 15 minutes — matches capture_token TTL
ALLOWED_MIME = {"video/mp4"}


def _client():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def raw_video_key(tenant_id: str, order_id: str, capture_id: str, sha256: str) -> str:
    return f"tenants/{tenant_id}/raw/{order_id}/{capture_id}/{sha256}.mp4"


def consent_key(tenant_id: str, worker_subject_id: str, capture_id: str) -> str:
    return f"tenants/{tenant_id}/private/consent/{worker_subject_id}/{capture_id}.json"


def generate_upload_url(
    tenant_id: str,
    order_id: str,
    capture_id: str,
    sha256: str,
    mime_type: str,
    size_bytes: int,
) -> tuple[str, str]:
    """Returns (presigned_put_url, r2_key). Client must PUT with matching Content-Type."""
    if mime_type not in ALLOWED_MIME:
        raise ValueError(f"Unsupported mime_type: {mime_type!r}")
    if not (0 < size_bytes <= MAX_VIDEO_BYTES):
        raise ValueError(f"size_bytes must be between 1 and {MAX_VIDEO_BYTES} bytes")

    key = raw_video_key(tenant_id, order_id, capture_id, sha256)
    url = _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET, "Key": key, "ContentType": mime_type},
        ExpiresIn=UPLOAD_EXPIRY_SECONDS,
    )
    return url, key


def head_object(r2_key: str) -> dict:
    """Returns object metadata dict. Raises ClientError (404) if not found."""
    return _client().head_object(Bucket=BUCKET, Key=r2_key)


def write_consent_receipt(r2_key: str, receipt: dict) -> tuple[str, int]:
    """Persist the exact rights receipt used to accept a capture."""
    body = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    _client().put_object(
        Bucket=BUCKET,
        Key=r2_key,
        Body=body,
        ContentType="application/json",
    )
    return sha256(body).hexdigest(), len(body)


def generate_download_url(r2_key: str, expires_in: int = 3600) -> str:
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": r2_key},
        ExpiresIn=expires_in,
    )
