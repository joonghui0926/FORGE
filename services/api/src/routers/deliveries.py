from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import r2
from ..auth import require_tenant
from ..db import get_conn
from ..models import TenantContext

router = APIRouter()


class DeliveryResponse(BaseModel):
    delivery_id: str
    order_id: str
    dataset_version: str
    download_url: str  # expiring signed URL
    manifest_url: str
    expires_in_seconds: int


@router.get("/{delivery_token}", response_model=DeliveryResponse)
def get_delivery(
    delivery_token: str,
    ctx: TenantContext = Depends(require_tenant),
) -> DeliveryResponse:
    with get_conn() as connection:
        row = connection.execute(
            """
            SELECT d.id, d.order_id, d.dataset_version, d.manifest
            FROM deliveries d
            JOIN dataset_orders o ON o.id = d.order_id
            WHERE d.id = %s AND o.tenant_id = %s AND o.state = 'READY'
            """,
            (delivery_token, ctx.tenant_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    manifest = dict(row[3])
    package_key = str(manifest.get("package_key", ""))
    manifest_key = str(manifest.get("manifest_key", ""))
    if not package_key or not manifest_key:
        raise HTTPException(status_code=409, detail="Delivery artifacts incomplete")
    expires_in = 3600
    return DeliveryResponse(
        delivery_id=str(row[0]),
        order_id=str(row[1]),
        dataset_version=str(row[2]),
        download_url=r2.generate_download_url(package_key, expires_in),
        manifest_url=r2.generate_download_url(manifest_key, expires_in),
        expires_in_seconds=expires_in,
    )
