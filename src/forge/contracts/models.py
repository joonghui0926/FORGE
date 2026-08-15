from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal
import hashlib
import json
import re


SCHEMA_VERSIONS = {
    "gpu_job": "forge.gpu-job.v1",
    "gpu_result": "forge.gpu-result.v1",
    "reconstruction": "forge.reconstruction.v1",
    "skill_ir": "forge.skill-ir.v1",
    "quality": "forge.quality-result.v1",
    "pioneer": "forge.pioneer-verdict.v1",
    "delivery": "forge.delivery.v1",
}

_SHA256 = re.compile(r"^[a-f0-9]{64}$")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ArtifactRef:
    kind: str
    uri: str
    sha256: str
    media_type: str = "application/json"

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("artifact kind is required")
        if not (self.uri.startswith("r2://") or self.uri.startswith("file://")):
            raise ValueError("artifact URI must use r2:// or file://")
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")


@dataclass(frozen=True)
class GPUJobRequest:
    job_id: str
    idempotency_key: str
    stage: Literal["reconstruction", "retarget", "validate", "package"]
    input_artifacts: tuple[ArtifactRef, ...]
    config_uri: str
    container_image: str
    pipeline_version: str
    output_prefix: str
    attempt: int = 1
    schema_version: str = SCHEMA_VERSIONS["gpu_job"]

    def __post_init__(self) -> None:
        if not self.job_id.startswith("job_"):
            raise ValueError("job_id must start with job_")
        if not _SHA256.fullmatch(self.idempotency_key):
            raise ValueError("idempotency_key must be a sha256")
        if "@sha256:" not in self.container_image:
            raise ValueError("container image must be pinned by digest")
        if not self.output_prefix.startswith("r2://"):
            raise ValueError("output_prefix must use r2://")
        if self.attempt < 1:
            raise ValueError("attempt must be positive")


@dataclass(frozen=True)
class GPUJobResult:
    job_id: str
    status: Literal["succeeded", "failed", "retryable"]
    artifacts: tuple[ArtifactRef, ...] = ()
    metrics: dict[str, float | int] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    error_code: str | None = None
    error_message: str | None = None
    simulation: bool = False
    schema_version: str = SCHEMA_VERSIONS["gpu_result"]

    def __post_init__(self) -> None:
        if self.status == "succeeded" and self.error_code:
            raise ValueError("successful result cannot include an error code")
        if self.status != "succeeded" and not self.error_code:
            raise ValueError("failed/retryable result requires an error code")
        gpu_seconds = float(self.metrics.get("gpu_seconds", 0))
        if self.status == "succeeded" and not self.simulation and gpu_seconds <= 0:
            raise ValueError("production success must report positive gpu_seconds")


@dataclass(frozen=True)
class ReplayMetrics:
    replay_success: bool
    max_penetration_m: float
    contact_phase_f1: float
    joint_limit_violation_count: int
    trajectory_duration_s: float
    profile_metrics: dict[str, float | int | bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_penetration_m < 0:
            raise ValueError("penetration must be expressed as a non-negative meter value")
        if not 0 <= self.contact_phase_f1 <= 1:
            raise ValueError("contact_phase_f1 must be in [0, 1]")
        if self.joint_limit_violation_count < 0:
            raise ValueError("joint_limit_violation_count cannot be negative")
        if self.trajectory_duration_s <= 0:
            raise ValueError("trajectory_duration_s must be positive")


@dataclass(frozen=True)
class QualityResult:
    subject_id: str
    accepted: bool
    hard_failures: tuple[str, ...]
    reason_codes: tuple[str, ...]
    scores: dict[str, float]
    replay: ReplayMetrics | None
    rights_verified: bool
    checksums_verified: bool
    provider: str
    policy_version: str
    evidence_artifact_ids: tuple[str, ...] = ()
    simulation: bool = False
    schema_version: str = SCHEMA_VERSIONS["quality"]

    def __post_init__(self) -> None:
        if self.accepted and self.hard_failures:
            raise ValueError("accepted quality result cannot contain hard failures")
        if self.accepted and (not self.rights_verified or not self.checksums_verified):
            raise ValueError("accepted source requires rights and checksum verification")
        if self.accepted and (self.replay is None or not self.replay.replay_success):
            raise ValueError("accepted source requires a successful physics replay")
        for name, score in self.scores.items():
            if not 0 <= score <= 1:
                raise ValueError(f"score {name} must be in [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
