from __future__ import annotations

from forge.contracts.models import QualityResult, ReplayMetrics


SHA = "a" * 64


def accepted_quality(
    subject_id: str = "ep_source", motion_family: str = "manipulation"
) -> QualityResult:
    if motion_family in {"locomotion", "whole_body"}:
        profile_metrics = {
            "max_foot_slip_m_s": 0.02,
            "minimum_support_margin_m": 0.03,
            "root_tracking_rmse_m": 0.02,
            "fall_count": 0,
            "self_collision_count": 0,
        }
    else:
        profile_metrics = {
            "object_goal_error_m": 0.01,
            "contact_temporal_support": 0.9,
            "dropped_object_count": 0,
            "unintended_collision_count": 0,
        }
    replay = ReplayMetrics(
        replay_success=True,
        max_penetration_m=0.001,
        contact_phase_f1=0.95,
        joint_limit_violation_count=0,
        trajectory_duration_s=2.0,
        profile_metrics=profile_metrics,
    )
    return QualityResult(
        subject_id=subject_id,
        accepted=True,
        hard_failures=(),
        reason_codes=(),
        scores={"replay_quality": 0.95},
        replay=replay,
        rights_verified=True,
        checksums_verified=True,
        provider="forge-deterministic",
        policy_version="test-policy-v1",
        evidence_artifact_ids=("artifact_replay",),
        simulation=True,
    )
