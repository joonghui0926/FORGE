from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from ..auth import require_worker_callback_token
from ..models import GPUResultPayload

router = APIRouter()


class JobCallbackRequest(BaseModel):
    result: GPUResultPayload


@router.post("/callback", status_code=status.HTTP_200_OK)
async def gpu_job_callback(
    request: Request,
    x_forge_job_id: str = Header(...),
    _: None = Depends(require_worker_callback_token),
) -> dict:
    body = await request.json()
    # TODO: validate forge.gpu-result.v1, update job status, trigger next workflow step
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{job_id}")
def get_job(
    job_id: str,
    # operator-only route
) -> dict:
    raise HTTPException(status_code=501, detail="Not implemented")
