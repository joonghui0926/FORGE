from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal


class TenantContext(BaseModel):
    tenant_id: str
    user_id: str


class ArtifactRef(BaseModel):
    kind: str
    uri: str
    sha256: str

    @field_validator("uri")
    @classmethod
    def require_r2_uri(cls, value: str) -> str:
        if not value.startswith("r2://"):
            raise ValueError("artifact URI must use r2://")
        return value

    @field_validator("sha256")
    @classmethod
    def require_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        return value


class GPUResultMetrics(BaseModel):
    model_config = ConfigDict(extra="allow")

    frames_total: int = 0
    frames_valid: int = 0
    gpu_seconds: float = 0
    replay_success: bool | None = None
    max_penetration_m: float | None = None
    contact_phase_f1: float | None = None
    joint_limit_violation_count: int | None = None
    trajectory_duration_s: float | None = None


class GPUResultError(BaseModel):
    code: str
    message: str


class GPUResultPayload(BaseModel):
    schema_version: str
    job_id: str
    status: Literal["succeeded", "failed", "retryable", "quality_insufficient"]
    artifacts: list[ArtifactRef]
    metrics: GPUResultMetrics
    warnings: list[str] = Field(default_factory=list)
    model_versions_uri: str | None = None
    error: GPUResultError | None = None
    error_code: str | None = None
    error_message: str | None = None
    simulation: bool = False
