from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from forge.adapters.papers.gmr_headless import GMRHeadlessRunner
from forge.contracts.models import GPUJobRequest, canonical_json
from workers.processors import PaperPipelineProcessor


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the real FORGE GMR worker processor")
    parser.add_argument("--bvh", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--robot", default="unitree_g1")
    parser.add_argument("--start-frame", type=int, default=0)
    parser.add_argument("--end-frame", type=int, default=20)
    args = parser.parse_args()

    source = args.bvh.read_bytes()
    configuration = {
        "adapter_id": GMRHeadlessRunner.adapter_id,
        "input_kind": "source",
        "source_extension": ".bvh",
        "robot_id": args.robot,
        "start_frame": args.start_frame,
        "end_frame": args.end_frame,
        "scale": 0.01,
        "reset_to_zero": True,
    }
    encoded_config = canonical_json(configuration).encode("utf-8")
    idempotency_key = sha256(source + encoded_config).hexdigest()
    request = GPUJobRequest(
        job_id="job_gmr_worker_smoke",
        idempotency_key=idempotency_key,
        stage="retarget",
        input_artifacts=(),
        config_uri="r2://forge-eval/config/gmr-worker-smoke.json",
        container_image="ghcr.io/forge/worker@sha256:" + "a" * 64,
        pipeline_version="gmr-worker-smoke-v1",
        output_prefix="r2://forge-eval/output/job_gmr_worker_smoke",
    )
    outputs = PaperPipelineProcessor().process(
        {"source": source}, encoded_config, request
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    evidence: list[dict[str, object]] = []
    for output in outputs:
        path = args.output_dir / output.filename
        path.write_bytes(output.data)
        evidence.append(
            {
                "kind": output.kind,
                "filename": output.filename,
                "media_type": output.media_type,
                "bytes": len(output.data),
                "sha256": sha256(output.data).hexdigest(),
            }
        )
    print(json.dumps({"outputs": evidence, "simulation": False}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
