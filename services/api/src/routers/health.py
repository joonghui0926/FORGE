import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "forge-api",
        "release": os.getenv("RENDER_GIT_COMMIT", os.getenv("FORGE_RELEASE", "local"))[:12],
        "pipeline_contract": "multi-participant-v2",
    }
