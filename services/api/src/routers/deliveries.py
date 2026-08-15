from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_tenant
from ..models import TenantContext

router = APIRouter()


class DeliveryResponse(BaseModel):
    delivery_id: str
    order_id: str
    dataset_version: str
    download_url: str       # expiring signed URL
    manifest_url: str
    expires_in_seconds: int


@router.get("/{delivery_token}", response_model=DeliveryResponse)
def get_delivery(
    delivery_token: str,
    ctx: TenantContext = Depends(require_tenant),
) -> DeliveryResponse:
    # TODO: validate delivery token, check tenant access, generate expiring signed URLs
    raise HTTPException(status_code=501, detail="Not implemented")
