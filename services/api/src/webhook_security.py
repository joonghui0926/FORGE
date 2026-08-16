from __future__ import annotations

from hashlib import sha256
import hmac


def verify_hmac_sha256(secret: str, body: bytes, supplied: str) -> bool:
    if not secret or not supplied:
        return False
    value = supplied.removeprefix("sha256=").strip()
    expected = hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()
    return hmac.compare_digest(expected, value)
