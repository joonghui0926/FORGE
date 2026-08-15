from __future__ import annotations

from dataclasses import dataclass

from forge.contracts.models import QualityResult, content_hash
from forge.geometry import Pose, matvec, normalize
from forge.modules.skill_ir.models import FramePose


@dataclass(frozen=True)
class RobotTrajectorySample:
    timestamp_s: float
    world_root: Pose
    frame_poses: tuple[FramePose, ...]
    qpos: tuple[float, ...]
    action: tuple[float, ...]


@dataclass(frozen=True)
class RobotEpisode:
    episode_id: str
    source_demonstration_id: str
    motion_family: str
    validation_profile: str
    robot_id: str
    samples: tuple[RobotTrajectorySample, ...]
    replay_artifact_id: str


@dataclass(frozen=True)
class WorldTransform:
    transform_id: str
    pose: Pose
    mode: str = "se3"

    def __post_init__(self) -> None:
        if self.mode not in {"se3", "ground_plane"}:
            raise ValueError("amplification mode must be se3 or ground_plane")
        if self.mode == "ground_plane":
            rotated_gravity = normalize(matvec(self.pose.rotation, (0.0, 0.0, -1.0)))
            if any(abs(a - b) > 1e-6 for a, b in zip(rotated_gravity, (0.0, 0.0, -1.0))):
                raise ValueError("ground_plane transforms must preserve gravity")
            if abs(self.pose.translation_m[2]) > 1e-6:
                raise ValueError("ground_plane transforms cannot move the ground height")


@dataclass(frozen=True)
class GeneratedEpisode:
    episode_id: str
    parent_episode_id: str
    parent_quality_subject_id: str
    transform_id: str
    transform_sha256: str
    trajectory: RobotEpisode
    requires_revalidation: bool = True
    schema_version: str = "forge.generated-episode.v1"


class AmplificationCompiler:
    """Creates lineage-preserving variants only after source replay acceptance."""

    version = "forge-amplification-v1"

    def amplify(
        self,
        source: RobotEpisode,
        source_quality: QualityResult,
        transforms: tuple[WorldTransform, ...],
        environment: str,
    ) -> tuple[GeneratedEpisode, ...]:
        self._authorize(source, source_quality, environment)
        if not transforms:
            raise ValueError("at least one transform is required")
        generated: list[GeneratedEpisode] = []
        for transform in transforms:
            expected_mode = (
                "ground_plane"
                if source.motion_family
                in {
                    "locomotion",
                    "whole_body",
                    "mobile_manipulation",
                    "navigation",
                    "articulated_machine",
                }
                else "se3"
            )
            if transform.mode != expected_mode:
                raise ValueError(f"{source.motion_family} requires {expected_mode} amplification")
            transformed_samples = tuple(
                RobotTrajectorySample(
                    timestamp_s=sample.timestamp_s,
                    world_root=transform.pose.compose(sample.world_root),
                    frame_poses=tuple(
                        FramePose(frame.frame_id, transform.pose.compose(frame.world_pose))
                        for frame in sample.frame_poses
                    ),
                    qpos=sample.qpos,
                    action=sample.action,
                )
                for sample in source.samples
            )
            trajectory = RobotEpisode(
                episode_id=f"{source.episode_id}__{transform.transform_id}",
                source_demonstration_id=source.source_demonstration_id,
                motion_family=source.motion_family,
                validation_profile=source.validation_profile,
                robot_id=source.robot_id,
                samples=transformed_samples,
                replay_artifact_id="PENDING_REVALIDATION",
            )
            transform_dict = {
                "id": transform.transform_id,
                "pose": transform.pose.to_dict(),
                "mode": transform.mode,
                "compiler": self.version,
            }
            generated.append(
                GeneratedEpisode(
                    episode_id=trajectory.episode_id,
                    parent_episode_id=source.episode_id,
                    parent_quality_subject_id=source_quality.subject_id,
                    transform_id=transform.transform_id,
                    transform_sha256=content_hash(transform_dict),
                    trajectory=trajectory,
                )
            )
        return tuple(generated)

    @staticmethod
    def _authorize(source: RobotEpisode, quality: QualityResult, environment: str) -> None:
        if quality.subject_id != source.episode_id:
            raise ValueError("quality result does not belong to the source episode")
        if not quality.accepted or quality.hard_failures:
            raise PermissionError("AMPLIFICATION_REQUIRES_ACCEPTED_SOURCE")
        if quality.replay is None or not quality.replay.replay_success:
            raise PermissionError("AMPLIFICATION_REQUIRES_REPLAY")
        if environment == "production" and quality.simulation:
            raise PermissionError("SIMULATED_QUALITY_FORBIDDEN_IN_PRODUCTION")
