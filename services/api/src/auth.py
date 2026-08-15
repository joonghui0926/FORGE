import os

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from .models import TenantContext

_SECRET = os.environ.get("AUTH_SECRET", "")
_ALGORITHM = "HS256"


async def require_tenant(authorization: str = Header(...)) -> TenantContext:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expected: Authorization: Bearer <token>",
        )
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        return TenantContext(
            tenant_id=payload["tenant_id"],
            user_id=payload["sub"],
        )
    except (JWTError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


async def require_worker_callback_token(
    x_forge_callback_token: str = Header(...),
) -> None:
    # TODO: verify HMAC token bound to job_id
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Callback auth not implemented",
    )
