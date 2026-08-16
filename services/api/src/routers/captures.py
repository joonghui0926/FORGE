import json
import os
import secrets
from datetime import datetime, timezone

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel

from ..auth import require_tenant
from ..db import get_conn
from ..models import TenantContext
from .. import r2

router = APIRouter()

_SECRET = os.environ.get("AUTH_SECRET", "")
_ALGORITHM = "HS256"
_TOKEN_TTL = r2.UPLOAD_EXPIRY_SECONDS  # token and presigned URL expire together


def _new_id(prefix: str) -> str:
    return f"{prefix}{secrets.token_urlsafe(12)}"


class PresignedUploadRequest(BaseModel):
    order_id: str
    batch_id: str
    object_id: str  # manipulated object e.g. "bottle_a"
    viewpoint_bin: str
    mime_type: str
    size_bytes: int
    sha256: str  # client-computed before requesting the URL


class PresignedUploadResponse(BaseModel):
    capture_token: str
    upload_url: str
    upload_fields: dict  # empty for presigned PUT; present for future presigned POST
    expires_in_seconds: int


class CaptureCompleteRequest(BaseModel):
    capture_token: str
    sha256: str
    worker_subject_id: str
    device_orientation: str
    device_camera_facing: str
    consent_confirmed: bool
    declared_rights: list[str]


class CaptureCompleteResponse(BaseModel):
    capture_id: str
    status: str


@router.post("/upload-url", response_model=PresignedUploadResponse)
def get_upload_url(
    body: PresignedUploadRequest,
    ctx: TenantContext = Depends(require_tenant),
) -> PresignedUploadResponse:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT o.id FROM dataset_orders o
            JOIN capture_batches b ON b.order_id = o.id
            WHERE o.id = %s AND o.tenant_id = %s AND b.id = %s
            """,
            (body.order_id, ctx.tenant_id, body.batch_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Order or batch not found")

    capture_id = _new_id("cap_")
    try:
        upload_url, r2_key = r2.generate_upload_url(
            tenant_id=ctx.tenant_id,
            order_id=body.order_id,
            capture_id=capture_id,
            sha256=body.sha256,
            mime_type=body.mime_type,
            size_bytes=body.size_bytes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    now = int(datetime.now(timezone.utc).timestamp())
    token = jwt.encode(
        {
            "sub": capture_id,
            "tenant_id": ctx.tenant_id,
            "order_id": body.order_id,
            "batch_id": body.batch_id,
            "object_id": body.object_id,
            "viewpoint_bin": body.viewpoint_bin,
            "r2_key": r2_key,
            "sha256": body.sha256,
            "mime_type": body.mime_type,
            "exp": now + _TOKEN_TTL,
        },
        _SECRET,
        algorithm=_ALGORITHM,
    )

    return PresignedUploadResponse(
        capture_token=token,
        upload_url=upload_url,
        upload_fields={},
        expires_in_seconds=_TOKEN_TTL,
    )


@router.post("/complete", response_model=CaptureCompleteResponse)
def complete_capture(
    body: CaptureCompleteRequest,
    ctx: TenantContext = Depends(require_tenant),
) -> CaptureCompleteResponse:
    if not body.consent_confirmed:
        raise HTTPException(status_code=422, detail="consent_confirmed must be true")
    if not body.declared_rights:
        raise HTTPException(status_code=422, detail="declared_rights must not be empty")

    try:
        tok = jwt.decode(body.capture_token, _SECRET, algorithms=[_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=422, detail="Invalid or expired capture_token")

    if tok["tenant_id"] != ctx.tenant_id:
        raise HTTPException(status_code=403, detail="Token tenant mismatch")
    if tok["sha256"] != body.sha256:
        raise HTTPException(status_code=422, detail="sha256 does not match upload token")

    r2_key = tok["r2_key"]
    capture_id = tok["sub"]

    try:
        head = r2.head_object(r2_key)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("404", "NoSuchKey"):
            raise HTTPException(
                status_code=422,
                detail="Upload not found in R2 — complete the PUT before calling /complete",
            )
        raise HTTPException(status_code=502, detail=f"R2 error: {code}")

    actual_size = head.get("ContentLength", 0)
    artifact_id = _new_id("art_")
    consent_r2_key = r2.consent_key(ctx.tenant_id, body.worker_subject_id, capture_id)

    with get_conn() as conn:
        with conn.transaction():
            conn.execute(
                """
                INSERT INTO artifacts
                  (id, tenant_id, order_id, kind, r2_key, sha256, size_bytes,
                   schema_version, producer)
                VALUES (%s, %s, %s, 'raw_video', %s, %s, %s, 'forge.capture.v1', 'browser_upload')
                """,
                (artifact_id, ctx.tenant_id, tok["order_id"], r2_key, body.sha256, actual_size),
            )
            conn.execute(
                """
                INSERT INTO demonstrations
                  (id, order_id, batch_id, worker_subject_id, state,
                   video_r2_key, sha256, mime_type, object_id, viewpoint_bin,
                   consent_r2_key, declared_rights, submitted_at)
                VALUES (%s, %s, %s, %s, 'SUBMITTED',
                        %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    capture_id,
                    tok["order_id"],
                    tok["batch_id"],
                    body.worker_subject_id,
                    r2_key,
                    body.sha256,
                    tok["mime_type"],
                    tok["object_id"],
                    tok["viewpoint_bin"],
                    consent_r2_key,
                    body.declared_rights,
                ),
            )
            conn.execute(
                """
                INSERT INTO audit_events
                  (entity_type, entity_id, action, actor, after_val)
                VALUES ('demonstration', %s, 'submitted', %s, %s::jsonb)
                """,
                (
                    capture_id,
                    ctx.user_id,
                    json.dumps(
                        {
                            "sha256": body.sha256,
                            "r2_key": r2_key,
                            "size_bytes": actual_size,
                            "declared_rights": body.declared_rights,
                        }
                    ),
                ),
            )

    return CaptureCompleteResponse(capture_id=capture_id, status="SUBMITTED")


@router.get("/{capture_id}")
def get_capture(
    capture_id: str,
    ctx: TenantContext = Depends(require_tenant),
) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT d.id, d.state, d.sha256, d.object_id,
                   d.viewpoint_bin, d.submitted_at, d.created_at
            FROM demonstrations d
            JOIN dataset_orders o ON o.id = d.order_id
            WHERE d.id = %s AND o.tenant_id = %s
            """,
            (capture_id, ctx.tenant_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Capture not found")
    return {
        "capture_id": row[0],
        "state": row[1],
        "sha256": row[2],
        "object_id": row[3],
        "viewpoint_bin": row[4],
        "submitted_at": row[5].isoformat(),
        "created_at": row[6].isoformat(),
    }
