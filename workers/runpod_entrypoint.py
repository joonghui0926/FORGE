from __future__ import annotations

import os

from forge.contracts.codec import gpu_job_request_from_dict, gpu_result_to_dict
from forge.integrations.r2.store import R2ObjectStore
from forge.integrations.runpod.handler import RunPodHandler
from workers.processors import PaperPipelineProcessor


def create_handler():
    try:
        import runpod  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError("INSTALL_FORGE_GPU_EXTRA") from error

    store = R2ObjectStore.from_env()
    processor = PaperPipelineProcessor()
    compiler = RunPodHandler(
        store=store,
        processors={"reconstruction": processor, "retarget": processor},
        environment=os.getenv("FORGE_ENV", "production"),
    )

    def handler(event: dict[str, object]) -> dict[str, object]:
        payload = event.get("input")
        if not isinstance(payload, dict) or not isinstance(payload.get("request"), dict):
            return {
                "status": "failed",
                "error_code": "RUNPOD_EVENT_CONTRACT_INVALID",
                "simulation": False,
            }
        try:
            request = gpu_job_request_from_dict(payload["request"])
            return gpu_result_to_dict(compiler.handle(request))
        except Exception as error:
            return {
                "status": "failed",
                "error_code": type(error).__name__.upper(),
                "error_message": str(error),
                "simulation": False,
            }

    return runpod, handler


if __name__ == "__main__":
    runpod, handler = create_handler()
    runpod.serverless.start({"handler": handler})
