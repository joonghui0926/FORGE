import hmac
import os

from fastapi import Header, HTTPException, status
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
    expected = os.getenv("FORGE_CALLBACK_TOKEN", "")
    if not expected or not hmac.compare_digest(expected, x_forge_callback_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid callback token"
        )


async def require_terac_ingest_token(
    x_forge_provider_token: str = Header(...),
) -> None:
    expected = os.getenv("TERAC_INGEST_TOKEN", "")
    if not expected or not hmac.compare_digest(expected, x_forge_provider_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Terac ingest token"
        )
