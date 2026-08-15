from fastapi import Depends, Header, HTTPException, status
from .models import TenantContext


async def require_tenant(
    authorization: str = Header(...),
) -> TenantContext:
    # TODO: validate JWT, extract tenant_id and user_id, verify tenant exists
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Auth not implemented",
    )


async def require_worker_callback_token(
    x_forge_callback_token: str = Header(...),
) -> None:
    # TODO: verify HMAC token bound to job_id
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Callback auth not implemented",
    )
