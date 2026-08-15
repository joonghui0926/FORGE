from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from forge.adapters.papers.twist_replay import (
    TWISTG1ReplayEvaluator,
    TWISTReplayDiagnostic,
)
from forge.contracts.models import GPUJobRequest
from workers.processors import PaperPipelineProcessor


SHA = "a" * 64


class TWISTReplayTest(unittest.TestCase):
    def test_missing_inputs_fail_before_optional_runtime_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                TWISTG1ReplayEvaluator().evaluate(
                    root / "missing.npz",
                    root / "missing.xml",
                    root / "missing.pt",
                    root / "output.npz",
                    source_start_frame=0,
                    source_end_frame_exclusive=1,
                    twist_revision="a" * 40,
                )

    def test_mapping_drops_only_unsupported_wrist_axes(self) -> None:
        self.assertEqual(
            TWISTG1ReplayEvaluator._gmr_dof_indices,
            tuple(range(20)) + tuple(range(22, 27)),
        )

    def test_worker_labels_only_successful_replay_as_accepted(self) -> None:
        request = GPUJobRequest(
            job_id="job_twist_test",
            idempotency_key=SHA,
            stage="validate",
            input_artifacts=(),
            config_uri="r2://forge-dev/config/twist.json",
            container_image="ghcr.io/forge/worker@sha256:" + SHA,
            pipeline_version="test-v1",
            output_prefix="r2://forge-dev/output/job_twist_test",
        )
        config = (
            '{"adapter_id":"twist-g1-closed-loop-replay-v1",'
            '"input_kind":"source","source_start_frame":0,'
            '"source_end_frame_exclusive":100,"twist_revision":"' + "b" * 40 + '"}'
        ).encode()

        def fake_evaluate(*args, **kwargs):
            args[3].write_bytes(b"safe-action")
            return TWISTReplayDiagnostic(
                adapter_id=TWISTG1ReplayEvaluator.adapter_id,
                robot_id="unitree_g1_25dof",
                acceptance_scope="unitree_g1_25dof_sim2sim",
                source_trajectory_sha256=SHA,
                target_model_sha256=SHA,
                policy_sha256=SHA,
                action_artifact_sha256=SHA,
                gmr_revision="c" * 40,
                twist_revision="b" * 40,
                source_start_frame=0,
                source_end_frame_exclusive=100,
                source_fps=120,
                control_hz=50,
                target_frame_count=42,
                simulated_step_count=1_000,
                policy_device="cuda",
                reference_joint_margin_adjustment_count=3,
                nonfinite_frame_count=0,
                joint_limit_violation_count=0,
                self_collision_frame_count=0,
                fall_frame_count=0,
                joint_position_rmse_rad=0.1,
                root_height_rmse_m=0.02,
                root_roll_pitch_rmse_rad=0.03,
                root_local_velocity_rmse_m_s=0.1,
                max_penetration_m=0.01,
                max_self_collision_penetration_m=0.0,
                torque_saturation_fraction=0.05,
                robot_ready_accepted=True,
                rejection_reasons=(),
            )

        with patch.object(TWISTG1ReplayEvaluator, "evaluate", side_effect=fake_evaluate):
            outputs = PaperPipelineProcessor().process(
                {"source": b"trajectory"}, config, request
            )
        self.assertEqual(outputs[0].kind, "robot_replay_accepted")
        self.assertEqual(outputs[1].kind, "robot_action_accepted")
        self.assertTrue(__import__("json").loads(outputs[0].data)["robot_ready_accepted"])
