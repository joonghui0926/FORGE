from __future__ import annotations

from typing import Any

from forge.contracts.models import ArtifactRef, GPUJobRequest, GPUJobResult


def artifact_ref_from_dict(value: dict[str, Any]) -> ArtifactRef:
    return ArtifactRef(
        kind=str(value["kind"]),
        uri=str(value["uri"]),
        sha256=str(value["sha256"]),
        media_type=str(value.get("media_type", "application/json")),
    )


def gpu_job_request_from_dict(value: dict[str, Any]) -> GPUJobRequest:
    allowed = {
        "schema_version",
        "job_id",
        "idempotency_key",
        "stage",
        "input_artifacts",
        "config_uri",
        "container_image",
        "pipeline_version",
        "output_prefix",
        "attempt",
    }
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"GPU_JOB_UNKNOWN_FIELDS:{','.join(sorted(unknown))}")
    return GPUJobRequest(
        schema_version=str(value.get("schema_version", "forge.gpu-job.v1")),
        job_id=str(value["job_id"]),
        idempotency_key=str(value["idempotency_key"]),
        stage=str(value["stage"]),  # type: ignore[arg-type]
        input_artifacts=tuple(artifact_ref_from_dict(item) for item in value["input_artifacts"]),
        config_uri=str(value["config_uri"]),
        container_image=str(value["container_image"]),
        pipeline_version=str(value["pipeline_version"]),
        output_prefix=str(value["output_prefix"]),
        attempt=int(value.get("attempt", 1)),
    )


def gpu_result_to_dict(result: GPUJobResult) -> dict[str, Any]:
    return {
        "schema_version": result.schema_version,
        "job_id": result.job_id,
        "status": result.status,
        "artifacts": [
            {
                "kind": artifact.kind,
                "uri": artifact.uri,
                "sha256": artifact.sha256,
                "media_type": artifact.media_type,
            }
            for artifact in result.artifacts
        ],
        "metrics": result.metrics,
        "warnings": list(result.warnings),
        "error_code": result.error_code,
        "error_message": result.error_message,
        "simulation": result.simulation,
    }


def gpu_result_from_dict(value: dict[str, Any]) -> GPUJobResult:
    allowed = {
        "schema_version",
        "job_id",
        "status",
        "artifacts",
        "metrics",
        "warnings",
        "error_code",
        "error_message",
        "simulation",
    }
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"GPU_RESULT_UNKNOWN_FIELDS:{','.join(sorted(unknown))}")
    return GPUJobResult(
        schema_version=str(value.get("schema_version", "forge.gpu-result.v1")),
        job_id=str(value["job_id"]),
        status=str(value["status"]),  # type: ignore[arg-type]
        artifacts=tuple(artifact_ref_from_dict(item) for item in value.get("artifacts", ())),
        metrics=dict(value.get("metrics", {})),
        warnings=tuple(str(item) for item in value.get("warnings", ())),
        error_code=str(value["error_code"]) if value.get("error_code") is not None else None,
        error_message=(
            str(value["error_message"]) if value.get("error_message") is not None else None
        ),
        simulation=bool(value.get("simulation", False)),
    )
