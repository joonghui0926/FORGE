from __future__ import annotations

import unittest

from forge.contracts.models import ReplayMetrics
from forge.integrations.pioneer.provider import FixturePioneerProvider, PioneerFeatures
from forge.modules.validation.quality_gate import QualityGate, ValidationInput


class ValidationAndPioneerTest(unittest.TestCase):
    def test_locomotion_profile_requires_balance_and_no_falls(self) -> None:
        replay = ReplayMetrics(
            replay_success=True,
            max_penetration_m=0.002,
            contact_phase_f1=0.92,
            joint_limit_violation_count=0,
            trajectory_duration_s=3.0,
            profile_metrics={
                "max_foot_slip_m_s": 0.03,
                "minimum_support_margin_m": 0.02,
                "root_tracking_rmse_m": 0.02,
                "fall_count": 0,
                "self_collision_count": 0,
            },
        )
        quality = QualityGate().evaluate(
            ValidationInput(
                subject_id="ep_walk",
                motion_family="locomotion",
                profile_id="locomotion-flat-v1",
                replay=replay,
                rights_verified=True,
                checksums_verified=True,
                reconstruction_valid_ratio=0.98,
                contact_observability=0.9,
                evidence_artifact_ids=("replay",),
                simulation=True,
            )
        )
        self.assertTrue(quality.accepted)

    def test_missing_motion_metric_fails_closed(self) -> None:
        replay = ReplayMetrics(True, 0.0, 0.9, 0, 1.0, {"fall_count": 0})
        quality = QualityGate().evaluate(
            ValidationInput(
                "ep_walk",
                "locomotion",
                "locomotion-flat-v1",
                replay,
                True,
                True,
                0.99,
                0.99,
                (),
                True,
            )
        )
        self.assertFalse(quality.accepted)
        self.assertTrue(any(code.startswith("PROFILE_METRIC_MISSING") for code in quality.hard_failures))

    def test_pioneer_fixture_never_runs_in_production(self) -> None:
        features = PioneerFeatures(
            subject_id="demo_1",
            motion_family="manipulation",
            validation_profile="manipulation-rigid-v1",
            reconstruction_valid_ratio=0.9,
            contact_observability=0.8,
            occlusion_ratio=0.1,
            replay_success=None,
            max_penetration_m=None,
            contact_phase_f1=None,
            deterministic_hard_failures=(),
            coverage_cell="front:bottle",
        )
        with self.assertRaises(RuntimeError):
            FixturePioneerProvider().infer(features, "PRE_HEAVY", "production")


if __name__ == "__main__":
    unittest.main()
