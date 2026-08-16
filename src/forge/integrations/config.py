from __future__ import annotations

import os


def required_env(name: str) -> str:
    """Read a required provider setting without ever falling back silently."""

    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name}_NOT_CONFIGURED")
    return value
