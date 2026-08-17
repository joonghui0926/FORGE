from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol
import json

from forge.contracts.codec import gpu_result_from_dict, gpu_result_to_dict
from forge.contracts.models import ArtifactRef, GPUJobRequest, GPUJobResult
from forge.integrations.r2.store import ObjectStore, parse_r2_uri


@dataclass(frozen=True)
class ProcessorOutput:
    kind: str
    filename: str
    data: bytes
    media_type: str = "application/json"


@dataclass(frozen=True)
class StageResult:
    outputs: tuple[ProcessorOutput, ...]
    metrics: dict[str, float | int | bool | str]
    warnings: tuple[str, ...] = ()
    status: str = "succeeded"

    def __iter__(self):
        return iter(self.outputs)

    def __len__(self) -> int:
        return len(self.outputs)

    def __getitem__(self, index: int) -> ProcessorOutput:
        return self.outputs[index]


class StageProcessor(Protocol):
    def process(
        self, inputs: dict[str, bytes], config: bytes, request: GPUJobRequest
    ) -> tuple[ProcessorOutput, ...] | StageResult: ...


class RunPodHandler:
    """Idempotent worker boundary used inside a RunPod pod/serverless container."""

    def __init__(
        self,
        store: ObjectStore,
        processors: dict[str, StageProcessor],
        environment: str,
    ) -> None:
        self.store = store
        self.processors = processors
        self.environment = environment
        self._completed: dict[str, GPUJobResult] = {}

    def handle(self, request: GPUJobRequest) -> GPUJobResult:
        previous = self._completed.get(request.idempotency_key)
        if previous is not None:
            return previous
        durable_result_uri = self._durable_result_uri(request)
        try:
            encoded_previous = self.store.get_bytes(durable_result_uri)
        except FileNotFoundError:
            pass
        else:
            previous = gpu_result_from_dict(json.loads(encoded_previous.decode("utf-8")))
            self._completed[request.idempotency_key] = previous
            return previous
        processor = self.processors.get(request.stage)
        if processor is None:
            return GPUJobResult(
                job_id=request.job_id,
                status="failed",
                error_code="STAGE_PROCESSOR_MISSING",
                error_message=f"No processor registered for {request.stage}",
                simulation=self.environment != "production",
            )

        started = perf_counter()
        try:
            inputs = {
                artifact.kind: self.store.get_bytes(artifact.uri, artifact.sha256)
                for artifact in request.input_artifacts
            }
            config = self.store.get_bytes(request.config_uri)
            processed = processor.process(inputs, config, request)
            if isinstance(processed, StageResult):
                outputs = processed.outputs
                processor_metrics = processed.metrics
                warnings = processed.warnings
                result_status = processed.status
            else:
                outputs = processed
                processor_metrics = {}
                warnings = ()
                result_status = "succeeded"
            if not outputs:
                raise ValueError("PROCESSOR_OUTPUT_EMPTY")
            if result_status not in {"succeeded", "quality_insufficient"}:
                raise ValueError("PROCESSOR_STATUS_INVALID")
            artifact_refs: list[ArtifactRef] = []
            for output in outputs:
                uri = f"{request.output_prefix.rstrip('/')}/{output.filename}"
                stored = self.store.put_bytes(uri, output.data, output.media_type)
                artifact_refs.append(
                    ArtifactRef(
                        kind=output.kind,
                        uri=stored.uri,
                        sha256=stored.sha256,
                        media_type=stored.media_type,
                    )
                )
            gpu_seconds = perf_counter() - started
            simulation = self.environment != "production"
            result = GPUJobResult(
                job_id=request.job_id,
                status=result_status,  # type: ignore[arg-type]
                artifacts=tuple(artifact_refs),
                metrics={
                    "frames_total": 0,
                    "frames_valid": 0,
                    **processor_metrics,
                    "gpu_seconds": 0 if simulation else max(gpu_seconds, 1e-9),
                    "artifact_count": len(artifact_refs),
                },
                warnings=warnings,
                simulation=simulation,
            )
            self.store.put_bytes(
                durable_result_uri,
                (json.dumps(gpu_result_to_dict(result), sort_keys=True) + "\n").encode("utf-8"),
                "application/json",
            )
            self._completed[request.idempotency_key] = result
            return result
        except (FileNotFoundError, TimeoutError) as error:
            return GPUJobResult(
                job_id=request.job_id,
                status="retryable",
                error_code=type(error).__name__.upper(),
                error_message=str(error),
                simulation=self.environment != "production",
            )
        except Exception as error:
            return GPUJobResult(
                job_id=request.job_id,
                status="failed",
                error_code=type(error).__name__.upper(),
                error_message=str(error),
                simulation=self.environment != "production",
            )

    @staticmethod
    def _durable_result_uri(request: GPUJobRequest) -> str:
        bucket, _ = parse_r2_uri(f"{request.output_prefix.rstrip('/')}/placeholder")
        return f"r2://{bucket}/_forge/idempotency/{request.idempotency_key}.json"
