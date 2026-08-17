import json
import os
import secrets
from datetime import datetime, timezone

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from typing import Literal

from ..auth import require_tenant, require_terac_ingest_token
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
    mime_type: Literal["video/mp4"]
    size_bytes: int
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")  # client-computed before requesting the URL
    environment_id: str = Field(min_length=1, max_length=100)
    take_kind: Literal["success", "failure", "recovery"]
    take_index: int = Field(ge=0, le=29)
    capture_requirement_id: str = Field(pattern=r"^capture_\d{2}$")
    session_id: str = Field(min_length=1, max_length=120)


class PresignedUploadResponse(BaseModel):
    capture_token: str
    upload_url: str
    upload_fields: dict  # empty for presigned PUT; present for future presigned POST
    expires_in_seconds: int


class CaptureCompleteRequest(BaseModel):
    capture_token: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    worker_subject_id: str = Field(pattern=r"^sub_[A-Za-z0-9_-]{8,}$")
    device_orientation: str
    device_camera_facing: str
    consent_confirmed: bool
    declared_rights: list[str]


class CaptureCompleteResponse(BaseModel):
    capture_id: str
    status: str


def _create_upload_url(body: PresignedUploadRequest, ctx: TenantContext) -> PresignedUploadResponse:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT o.id, o.contract FROM dataset_orders o
            JOIN capture_batches b ON b.order_id = o.id
            WHERE o.id = %s AND o.tenant_id = %s AND b.id = %s
            """,
            (body.order_id, ctx.tenant_id, body.batch_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Order or batch not found")
    contract = dict(row[1])
    acquisition = contract.get("acquisition") or {}
    clips_per_participant = int(acquisition.get("clips_per_participant", 6))
    if body.take_index >= clips_per_participant:
        raise HTTPException(status_code=422, detail="take_index exceeds clips_per_participant")
    if body.object_id not in contract["coverage"]["object_ids"]:
        raise HTTPException(status_code=422, detail="object_id is outside the signed contract")
    if body.viewpoint_bin not in contract["coverage"]["viewpoint_bins"]:
        raise HTTPException(status_code=422, detail="viewpoint_bin is outside the signed contract")

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
            "environment_id": body.environment_id,
            "take_kind": body.take_kind,
            "take_index": body.take_index,
            "capture_requirement_id": body.capture_requirement_id,
            "session_id": body.session_id,
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


@router.post("/upload-url", response_model=PresignedUploadResponse)
def get_upload_url(
    body: PresignedUploadRequest,
    ctx: TenantContext = Depends(require_tenant),
) -> PresignedUploadResponse:
    return _create_upload_url(body, ctx)


@router.post("/provider/terac/upload-url", response_model=PresignedUploadResponse)
def get_terac_upload_url(
    body: PresignedUploadRequest,
    _: None = Depends(require_terac_ingest_token),
) -> PresignedUploadResponse:
    with get_conn() as connection:
        row = connection.execute(
            """
            SELECT o.tenant_id
            FROM dataset_orders o JOIN capture_batches b ON b.order_id = o.id
            WHERE o.id = %s AND b.id = %s AND b.terac_campaign_id IS NOT NULL
            """,
            (body.order_id, body.batch_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Active Terac batch not found")
    return _create_upload_url(body, TenantContext(tenant_id=str(row[0]), user_id="provider:terac"))


def _complete_capture(body: CaptureCompleteRequest, ctx: TenantContext) -> CaptureCompleteResponse:
    if not body.consent_confirmed:
        raise HTTPException(status_code=422, detail="consent_confirmed must be true")
    required_rights = {
        "worker_consent",
        "location_release",
        "customer_training_and_evaluation_license",
        "retention_and_deletion_policy_acknowledgement",
    }
    if not required_rights.issubset(body.declared_rights):
        raise HTTPException(status_code=422, detail="required capture rights are incomplete")

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

    with get_conn() as connection:
        existing = connection.execute(
            "SELECT sha256, state::text FROM demonstrations WHERE id = %s",
            (capture_id,),
        ).fetchone()
    if existing is not None:
        if str(existing[0]) != body.sha256:
            raise HTTPException(status_code=409, detail="Capture id already has different content")
        return CaptureCompleteResponse(capture_id=capture_id, status=str(existing[1]))

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
    receipt = {
        "schema_version": "forge.consent-receipt.v1",
        "capture_id": capture_id,
        "worker_subject_id": body.worker_subject_id,
        "consent_confirmed": body.consent_confirmed,
        "declared_rights": sorted(set(body.declared_rights)),
        "device_orientation": body.device_orientation,
        "device_camera_facing": body.device_camera_facing,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    consent_sha256, consent_size = r2.write_consent_receipt(consent_r2_key, receipt)
    consent_artifact_id = _new_id("art_")

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
                INSERT INTO artifacts
                  (id, tenant_id, order_id, kind, r2_key, sha256, size_bytes,
                   schema_version, producer)
                VALUES (%s, %s, %s, 'consent_receipt', %s, %s, %s,
                        'forge.consent-receipt.v1', 'forge-api')
                """,
                (
                    consent_artifact_id,
                    ctx.tenant_id,
                    tok["order_id"],
                    consent_r2_key,
                    consent_sha256,
                    consent_size,
                ),
            )
            conn.execute(
                """
                INSERT INTO demonstrations
                  (id, order_id, batch_id, worker_subject_id, state,
                   video_r2_key, sha256, mime_type, object_id, viewpoint_bin,
                   consent_r2_key, declared_rights, submitted_at, environment_id,
                   take_kind, take_index, capture_requirement_id, session_id,
                   device_orientation, device_camera_facing)
                VALUES (%s, %s, %s, %s, 'SUBMITTED',
                        %s, %s, %s, %s, %s, %s, %s, NOW(),
                        %s, %s, %s, %s, %s, %s, %s)
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
                    tok["environment_id"],
                    tok["take_kind"],
                    tok["take_index"],
                    tok["capture_requirement_id"],
                    tok["session_id"],
                    body.device_orientation,
                    body.device_camera_facing,
                ),
            )
            conn.execute(
                "UPDATE artifacts SET demonstration_id = %s WHERE id IN (%s, %s)",
                (capture_id, artifact_id, consent_artifact_id),
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


@router.post("/complete", response_model=CaptureCompleteResponse)
def complete_capture(
    body: CaptureCompleteRequest,
    ctx: TenantContext = Depends(require_tenant),
) -> CaptureCompleteResponse:
    return _complete_capture(body, ctx)


@router.post("/provider/terac/complete", response_model=CaptureCompleteResponse)
def complete_terac_capture(
    body: CaptureCompleteRequest,
    _: None = Depends(require_terac_ingest_token),
) -> CaptureCompleteResponse:
    try:
        token = jwt.decode(body.capture_token, _SECRET, algorithms=[_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=422, detail="Invalid or expired capture_token")
    return _complete_capture(
        body,
        TenantContext(tenant_id=str(token["tenant_id"]), user_id="provider:terac"),
    )


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
