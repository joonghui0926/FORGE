from __future__ import annotations

import os
import json
from urllib.request import Request, urlopen

from forge.contracts.codec import gpu_job_request_from_dict, gpu_result_to_dict
from forge.integrations.r2.store import R2ObjectStore
from forge.integrations.runpod.handler import RunPodHandler
from workers.processors import DeliveryPackageProcessor, PaperPipelineProcessor


def create_handler():
    try:
        import runpod  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError("INSTALL_FORGE_GPU_EXTRA") from error

    store = R2ObjectStore.from_env()
    processor = PaperPipelineProcessor()
    package_processor = DeliveryPackageProcessor()
    compiler = RunPodHandler(
        store=store,
        processors={
            "reconstruction": processor,
            "retarget": processor,
            "validate": processor,
            "package": package_processor,
        },
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
            result = gpu_result_to_dict(compiler.handle(request))
            callback_url = str(payload.get("callback_url", ""))
            callback_token = str(payload.get("callback_token", ""))
            if callback_url and callback_token:
                body = json.dumps(result, separators=(",", ":")).encode("utf-8")
                callback_request = Request(
                    callback_url,
                    data=body,
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "X-Forge-Job-Id": request.job_id,
                        "X-Forge-Callback-Token": callback_token,
                    },
                )
                with urlopen(callback_request, timeout=30) as response:
                    if response.status < 200 or response.status >= 300:
                        raise RuntimeError(f"CALLBACK_HTTP_{response.status}")
            return result
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
