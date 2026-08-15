from __future__ import annotations

from dataclasses import dataclass

from forge.contracts.models import QualityResult, ReplayMetrics


@dataclass(frozen=True)
class MotionQualityProfile:
    profile_id: str
    motion_families: tuple[str, ...]
    max_penetration_m: float
    min_contact_phase_f1: float
    required_profile_metrics: tuple[str, ...]
    maximums: dict[str, float]
    minimums: dict[str, float]
    zero_required: tuple[str, ...]


PROFILES: dict[str, MotionQualityProfile] = {
    "manipulation-rigid-v1": MotionQualityProfile(
        profile_id="manipulation-rigid-v1",
        motion_families=("manipulation", "bimanual", "tool_use"),
        max_penetration_m=0.005,
        min_contact_phase_f1=0.80,
        required_profile_metrics=("object_goal_error_m", "contact_temporal_support"),
        maximums={"object_goal_error_m": 0.03},
        minimums={"contact_temporal_support": 0.65},
        zero_required=("dropped_object_count", "unintended_collision_count"),
    ),
    "locomotion-flat-v1": MotionQualityProfile(
        profile_id="locomotion-flat-v1",
        motion_families=("locomotion", "whole_body"),
        max_penetration_m=0.012,
        min_contact_phase_f1=0.85,
        required_profile_metrics=(
            "max_foot_slip_m_s",
            "minimum_support_margin_m",
            "root_tracking_rmse_m",
        ),
        maximums={"max_foot_slip_m_s": 0.08, "root_tracking_rmse_m": 0.05},
        minimums={"minimum_support_margin_m": 0.0},
        zero_required=("fall_count", "self_collision_count"),
    ),
    "mobile-manipulation-v1": MotionQualityProfile(
        profile_id="mobile-manipulation-v1",
        motion_families=("mobile_manipulation",),
        max_penetration_m=0.008,
        min_contact_phase_f1=0.80,
        required_profile_metrics=(
            "base_path_error_m",
            "object_goal_error_m",
            "contact_temporal_support",
        ),
        maximums={"base_path_error_m": 0.08, "object_goal_error_m": 0.03},
        minimums={"contact_temporal_support": 0.65},
        zero_required=("dropped_object_count", "unintended_collision_count"),
    ),
    "navigation-ground-v1": MotionQualityProfile(
        profile_id="navigation-ground-v1",
        motion_families=("navigation", "articulated_machine"),
        max_penetration_m=0.02,
        min_contact_phase_f1=0.75,
        required_profile_metrics=("path_tracking_rmse_m", "minimum_clearance_m"),
        maximums={"path_tracking_rmse_m": 0.10},
        minimums={"minimum_clearance_m": 0.05},
        zero_required=("collision_count", "rollover_count"),
    ),
    "aerial-flight-v1": MotionQualityProfile(
        profile_id="aerial-flight-v1",
        motion_families=("aerial",),
        max_penetration_m=0.02,
        min_contact_phase_f1=0.70,
        required_profile_metrics=(
            "position_tracking_rmse_m",
            "attitude_tracking_rmse_rad",
            "minimum_clearance_m",
        ),
        maximums={"position_tracking_rmse_m": 0.10, "attitude_tracking_rmse_rad": 0.10},
        minimums={"minimum_clearance_m": 0.10},
        zero_required=("collision_count", "unstable_flight_count"),
    ),
    "multi-robot-coordination-v1": MotionQualityProfile(
        profile_id="multi-robot-coordination-v1",
        motion_families=("multi_robot",),
        max_penetration_m=0.01,
        min_contact_phase_f1=0.75,
        required_profile_metrics=("coordination_timing_rmse_s", "minimum_inter_robot_distance_m"),
        maximums={"coordination_timing_rmse_s": 0.10},
        minimums={"minimum_inter_robot_distance_m": 0.05},
        zero_required=("inter_robot_collision_count", "task_deadlock_count"),
    ),
}


@dataclass(frozen=True)
class ValidationInput:
    subject_id: str
    motion_family: str
    profile_id: str
    replay: ReplayMetrics | None
    rights_verified: bool
    checksums_verified: bool
    reconstruction_valid_ratio: float
    contact_observability: float
    evidence_artifact_ids: tuple[str, ...]
    simulation: bool = False


class QualityGate:
    """Authoritative deterministic gate. Learned QC can prioritize, never override it."""

    policy_version = "forge-deterministic-quality-v1"

    def evaluate(self, value: ValidationInput) -> QualityResult:
        profile = PROFILES.get(value.profile_id)
        if profile is None:
            return self._reject(value, ("UNSUPPORTED_VALIDATION_PROFILE",))
        if value.motion_family not in profile.motion_families:
            return self._reject(value, ("VALIDATION_PROFILE_MOTION_MISMATCH",))

        failures: list[str] = []
        reasons: list[str] = []
        if not value.rights_verified:
            failures.append("RIGHTS_NOT_VERIFIED")
        if not value.checksums_verified:
            failures.append("CHECKSUM_MISMATCH")
        if value.reconstruction_valid_ratio < 0.90:
            failures.append("RECONSTRUCTION_COVERAGE_LOW")
        if value.contact_observability < 0.60:
            failures.append("CONTACT_OBSERVABILITY_LOW")
        if value.replay is None:
            failures.append("REPLAY_MISSING")
        else:
            replay = value.replay
            if not replay.replay_success:
                failures.append("REPLAY_FAILED")
            if replay.max_penetration_m > profile.max_penetration_m:
                failures.append("PENETRATION_EXCEEDED")
            if replay.contact_phase_f1 < profile.min_contact_phase_f1:
                failures.append("CONTACT_PHASE_MISMATCH")
            if replay.joint_limit_violation_count:
                failures.append("JOINT_LIMIT_VIOLATION")
            metrics = replay.profile_metrics
            for metric in profile.required_profile_metrics:
                if metric not in metrics:
                    failures.append(f"PROFILE_METRIC_MISSING:{metric}")
            for metric, maximum in profile.maximums.items():
                if metric in metrics and float(metrics[metric]) > maximum:
                    failures.append(f"PROFILE_MAX_EXCEEDED:{metric}")
            for metric, minimum in profile.minimums.items():
                if metric in metrics and float(metrics[metric]) < minimum:
                    failures.append(f"PROFILE_MIN_NOT_MET:{metric}")
            for metric in profile.zero_required:
                if metric not in metrics:
                    failures.append(f"PROFILE_METRIC_MISSING:{metric}")
                elif float(metrics[metric]) != 0:
                    failures.append(f"PROFILE_ZERO_REQUIRED:{metric}")

        if failures:
            reasons.extend(failures)
        scores = {
            "reconstruction_valid_ratio": max(0.0, min(1.0, value.reconstruction_valid_ratio)),
            "contact_observability": max(0.0, min(1.0, value.contact_observability)),
            "replay_quality": self._replay_score(value.replay, profile),
        }
        return QualityResult(
            subject_id=value.subject_id,
            accepted=not failures,
            hard_failures=tuple(failures),
            reason_codes=tuple(reasons),
            scores=scores,
            replay=value.replay,
            rights_verified=value.rights_verified,
            checksums_verified=value.checksums_verified,
            provider="forge-deterministic",
            policy_version=self.policy_version,
            evidence_artifact_ids=value.evidence_artifact_ids,
            simulation=value.simulation,
        )

    def _reject(self, value: ValidationInput, failures: tuple[str, ...]) -> QualityResult:
        return QualityResult(
            subject_id=value.subject_id,
            accepted=False,
            hard_failures=failures,
            reason_codes=failures,
            scores={"reconstruction_valid_ratio": 0.0, "contact_observability": 0.0},
            replay=value.replay,
            rights_verified=value.rights_verified,
            checksums_verified=value.checksums_verified,
            provider="forge-deterministic",
            policy_version=self.policy_version,
            evidence_artifact_ids=value.evidence_artifact_ids,
            simulation=value.simulation,
        )

    @staticmethod
    def _replay_score(replay: ReplayMetrics | None, profile: MotionQualityProfile) -> float:
        if replay is None or not replay.replay_success:
            return 0.0
        penetration_score = max(0.0, 1.0 - replay.max_penetration_m / profile.max_penetration_m)
        return min(1.0, 0.5 * replay.contact_phase_f1 + 0.5 * penetration_score)
