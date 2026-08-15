from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth import require_tenant
from ..models import TenantContext

router = APIRouter()


class PresignedUploadRequest(BaseModel):
    order_id: str
    object_id: str
    viewpoint_bin: str
    mime_type: str
    size_bytes: int


class PresignedUploadResponse(BaseModel):
    capture_token: str      # identifies the pending capture
    upload_url: str         # presigned PUT to R2
    upload_fields: dict     # any additional fields for multipart
    expires_in_seconds: int


class CaptureCompleteRequest(BaseModel):
    capture_token: str
    sha256: str             # client-computed after upload
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
    # TODO: validate order exists, check consent requirement, generate presigned URL from R2
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/complete", response_model=CaptureCompleteResponse)
def complete_capture(
    body: CaptureCompleteRequest,
    ctx: TenantContext = Depends(require_tenant),
) -> CaptureCompleteResponse:
    # TODO: verify sha256 matches R2 object, persist capture record, enqueue pre-QC
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{capture_id}")
def get_capture(
    capture_id: str,
    ctx: TenantContext = Depends(require_tenant),
) -> dict:
    raise HTTPException(status_code=501, detail="Not implemented")
