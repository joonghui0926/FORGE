from pydantic import BaseModel
from typing import Any


class TenantContext(BaseModel):
    tenant_id: str
    user_id: str


class ArtifactRef(BaseModel):
    uri: str
    sha256: str


class GPUResultMetrics(BaseModel):
    frames_total: int
    frames_valid: int
    gpu_seconds: float


class GPUResultError(BaseModel):
    code: str
    message: str


class GPUResultPayload(BaseModel):
    schema_version: str
    job_id: str
    status: str
    artifacts: list[ArtifactRef]
    metrics: GPUResultMetrics
    warnings: list[str]
    model_versions_uri: str | None
    error: GPUResultError | None
