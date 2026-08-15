from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from forge.adapters.papers.gmr_headless import GMRHeadlessResult, GMRHeadlessRunner
from forge.contracts.models import GPUJobRequest
from workers.processors import PaperPipelineProcessor


SHA = "a" * 64


class GMRHeadlessTest(unittest.TestCase):
    def test_rejects_unsupported_target_before_loading_runtime(self) -> None:
        with self.assertRaisesRegex(ValueError, "GMR_XSENS_ROBOT_UNSUPPORTED"):
            GMRHeadlessRunner().retarget_xsens_bvh(
                checkout=None,  # type: ignore[arg-type]
                bvh_file=None,  # type: ignore[arg-type]
                output_file=None,  # type: ignore[arg-type]
                robot_id="unsupported_robot",
            )

    def test_worker_emits_candidate_and_never_accepts_it(self) -> None:
        request = GPUJobRequest(
            job_id="job_gmr_test",
            idempotency_key=SHA,
            stage="retarget",
            input_artifacts=(),
            config_uri="r2://forge-dev/config/gmr.json",
            container_image="ghcr.io/forge/worker@sha256:" + SHA,
            pipeline_version="test-v1",
            output_prefix="r2://forge-dev/output/job_gmr_test",
        )
        config = json.dumps(
            {
                "adapter_id": GMRHeadlessRunner.adapter_id,
                "input_kind": "source",
                "robot_id": "unitree_g1",
                "end_frame": 20,
            }
        ).encode("utf-8")

        def fake_run(**kwargs):
            kwargs["output_file"].write_bytes(b"npz-candidate")
            return GMRHeadlessResult(
                adapter_id=GMRHeadlessRunner.adapter_id,
                source_sha256=SHA,
                output_sha256="b" * 64,
                output_path=str(kwargs["output_file"]),
                robot_id="unitree_g1",
                source_frame_count=20,
                output_frame_count=20,
                fps=120,
                duration_s=0.5,
                revision="c" * 40,
            )

        with patch.object(GMRHeadlessRunner, "retarget_xsens_bvh", side_effect=fake_run):
            outputs = PaperPipelineProcessor().process({"source": b"bvh"}, config, request)

        report = json.loads(outputs[0].data)
        self.assertEqual(outputs[0].kind, "retarget_candidate_report")
        self.assertEqual(outputs[1].kind, "robot_trajectory_candidate")
        self.assertEqual(report["acceptance_state"], "candidate_requires_independent_replay")
        self.assertNotIn("accepted", report)
