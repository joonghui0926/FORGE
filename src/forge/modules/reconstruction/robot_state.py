from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from forge.geometry import Pose
from forge.modules.skill_ir.models import (
    CanonicalSkillIR,
    ContactAnchor,
    FramePose,
    SkillPhase,
    SkillSample,
)


@dataclass(frozen=True)
class SourceRobotCalibration:
    robot_id: str
    model_uri: str
    model_sha256: str
    joint_names: tuple[str, ...]
    source_frame_to_canonical_frame: dict[str, str]
    source_length_unit_in_meters: float
    coordinate_convention: str
    calibration_artifact_id: str

    def __post_init__(self) -> None:
        if self.source_length_unit_in_meters <= 0:
            raise ValueError("source length conversion must be positive")
        if not self.joint_names or len(set(self.joint_names)) != len(self.joint_names):
            raise ValueError("calibration joint_names must be unique and non-empty")
        if len(set(self.source_frame_to_canonical_frame.values())) != len(
            self.source_frame_to_canonical_frame
        ):
            raise ValueError("canonical frame mapping must be one-to-one")


@dataclass(frozen=True)
class RobotStateFrame:
    frame_index: int
    timestamp_s: float
    source_world_root: Pose
    source_frame_poses: tuple[FramePose, ...]
    joint_positions: tuple[float, ...]
    joint_velocities: tuple[float, ...] = ()


class RobotStateCompiler:
    version = "forge-robot-state-compiler-v1"

    def compile(
        self,
        skill_id: str,
        source_demonstration_id: str,
        motion_family: str,
        validation_profile: str,
        calibration: SourceRobotCalibration,
        frames: tuple[RobotStateFrame, ...],
        phases: tuple[SkillPhase, ...],
        contacts: tuple[ContactAnchor, ...] = (),
        counterpart_asset_ids: tuple[str, ...] = (),
        observation_type: str = "robot_state",
    ) -> CanonicalSkillIR:
        if not frames:
            raise ValueError("ROBOT_STATE_EMPTY")
        indices = tuple(frame.frame_index for frame in frames)
        timestamps = tuple(frame.timestamp_s for frame in frames)
        if indices != tuple(sorted(set(indices))):
            raise ValueError("ROBOT_STATE_FRAMES_NOT_MONOTONIC")
        if timestamps != tuple(sorted(set(timestamps))):
            raise ValueError("ROBOT_STATE_TIMESTAMPS_NOT_MONOTONIC")

        samples: list[SkillSample] = []
        for frame in frames:
            if len(frame.joint_positions) != len(calibration.joint_names):
                raise ValueError("ROBOT_STATE_JOINT_DIMENSION_MISMATCH")
            values = frame.joint_positions + frame.joint_velocities
            if any(not isfinite(value) for value in values):
                raise ValueError("ROBOT_STATE_NONFINITE")
            mapped_frames: list[FramePose] = []
            for source_frame in frame.source_frame_poses:
                canonical_name = calibration.source_frame_to_canonical_frame.get(
                    source_frame.frame_id
                )
                if canonical_name is None:
                    continue
                mapped_frames.append(
                    FramePose(
                        canonical_name,
                        self._scale_pose(
                            source_frame.world_pose, calibration.source_length_unit_in_meters
                        ),
                    )
                )
            samples.append(
                SkillSample(
                    frame_index=frame.frame_index,
                    timestamp_s=frame.timestamp_s,
                    world_root=self._scale_pose(
                        frame.source_world_root, calibration.source_length_unit_in_meters
                    ),
                    frame_poses=tuple(mapped_frames),
                    joint_positions=frame.joint_positions,
                    joint_velocities=frame.joint_velocities,
                )
            )

        return CanonicalSkillIR(
            skill_id=skill_id,
            source_demonstration_id=source_demonstration_id,
            source_actor_type="robot",
            source_observation_type=observation_type,
            motion_family=motion_family,
            actor_model_uri=calibration.model_uri,
            actor_model_sha256=calibration.model_sha256,
            joint_names=calibration.joint_names,
            counterpart_asset_ids=counterpart_asset_ids,
            gravity_world_m_s2=(0.0, 0.0, -9.81),
            phases=phases,
            samples=tuple(samples),
            contacts=contacts,
            coordinate_convention=calibration.coordinate_convention,
            validation_profile=validation_profile,
            reconstruction_artifact_ids=(calibration.calibration_artifact_id,),
            compiler_version=self.version,
        )

    @staticmethod
    def _scale_pose(pose: Pose, length_unit_in_meters: float) -> Pose:
        return Pose(
            rotation=pose.rotation,
            translation_m=tuple(
                value * length_unit_in_meters for value in pose.translation_m
            ),  # type: ignore[arg-type]
        )
