from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from forge.contracts.models import SCHEMA_VERSIONS, content_hash
from forge.geometry import Pose, Vec3


@dataclass(frozen=True)
class ContactAnchor:
    anchor_id: str
    phase_id: str
    actor_region: str
    counterpart_id: str
    counterpart_frame: str
    counterpart_point_m: Vec3
    contact_type: str
    support_frames: tuple[int, ...]
    confidence: float
    uncertainty_m: float
    observability: float

    def __post_init__(self) -> None:
        if not all(
            (self.anchor_id, self.phase_id, self.actor_region, self.counterpart_id, self.counterpart_frame)
        ):
            raise ValueError("contact anchor identifiers are required")
        if len(self.counterpart_point_m) != 3:
            raise ValueError("counterpart_point_m must contain three values")
        if self.contact_type not in {"object", "environment", "self", "tool", "other"}:
            raise ValueError("unsupported contact_type")
        if not self.support_frames:
            raise ValueError("contact anchor needs temporal support")
        if tuple(sorted(set(self.support_frames))) != self.support_frames:
            raise ValueError("support_frames must be sorted and unique")
        if not 0 <= self.confidence <= 1 or not 0 <= self.observability <= 1:
            raise ValueError("confidence and observability must be in [0, 1]")
        if self.uncertainty_m < 0:
            raise ValueError("uncertainty_m must be non-negative")


@dataclass(frozen=True)
class SkillPhase:
    phase_id: str
    name: str
    start_frame: int
    end_frame: int
    required_contact_anchor_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.start_frame < 0 or self.end_frame < self.start_frame:
            raise ValueError("invalid phase frame range")


@dataclass(frozen=True)
class FramePose:
    frame_id: str
    world_pose: Pose

    def __post_init__(self) -> None:
        if not self.frame_id:
            raise ValueError("frame_id is required")


@dataclass(frozen=True)
class SkillSample:
    frame_index: int
    timestamp_s: float
    world_root: Pose
    frame_poses: tuple[FramePose, ...]
    joint_positions: tuple[float, ...]
    joint_velocities: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if self.frame_index < 0 or self.timestamp_s < 0:
            raise ValueError("frame_index and timestamp_s must be non-negative")
        if not self.joint_positions:
            raise ValueError("joint_positions cannot be empty")
        frame_ids = tuple(frame.frame_id for frame in self.frame_poses)
        if len(set(frame_ids)) != len(frame_ids):
            raise ValueError("frame_poses must use unique frame identifiers")
        if self.joint_velocities and len(self.joint_velocities) != len(self.joint_positions):
            raise ValueError("joint velocity and position dimensions must match")

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "timestamp_s": self.timestamp_s,
            "world_root": self.world_root.to_dict(),
            "frame_poses": [
                {"frame_id": frame.frame_id, "world_pose": frame.world_pose.to_dict()}
                for frame in self.frame_poses
            ],
            "joint_positions": list(self.joint_positions),
            "joint_velocities": list(self.joint_velocities),
        }


@dataclass(frozen=True)
class CanonicalSkillIR:
    skill_id: str
    source_demonstration_id: str
    source_actor_type: str
    source_observation_type: str
    motion_family: str
    actor_model_uri: str
    actor_model_sha256: str
    joint_names: tuple[str, ...]
    counterpart_asset_ids: tuple[str, ...]
    gravity_world_m_s2: Vec3
    phases: tuple[SkillPhase, ...]
    samples: tuple[SkillSample, ...]
    contacts: tuple[ContactAnchor, ...]
    coordinate_convention: str
    validation_profile: str
    reconstruction_artifact_ids: tuple[str, ...]
    compiler_version: str
    schema_version: str = SCHEMA_VERSIONS["skill_ir"]

    def __post_init__(self) -> None:
        if not self.skill_id or not self.source_demonstration_id:
            raise ValueError("skill and source identifiers are required")
        if self.source_actor_type not in {"human", "robot", "mixed", "simulation", "unknown"}:
            raise ValueError("unsupported source_actor_type")
        if self.source_observation_type not in {
            "monocular_video",
            "multiview_video",
            "robot_state",
            "teleop_log",
            "simulation_trace",
            "multimodal",
        }:
            raise ValueError("unsupported source_observation_type")
        if self.motion_family not in {
            "manipulation",
            "bimanual",
            "locomotion",
            "whole_body",
            "mobile_manipulation",
            "tool_use",
            "navigation",
            "aerial",
            "articulated_machine",
            "multi_robot",
            "custom",
        }:
            raise ValueError("unsupported motion_family")
        if not self.actor_model_uri.startswith(("r2://", "file://")):
            raise ValueError("actor model must use r2:// or file://")
        if not self.joint_names or len(set(self.joint_names)) != len(self.joint_names):
            raise ValueError("joint_names must be non-empty and unique")
        if not self.phases or not self.samples:
            raise ValueError("Skill IR requires phases and samples")
        frame_indices = tuple(sample.frame_index for sample in self.samples)
        if frame_indices != tuple(sorted(set(frame_indices))):
            raise ValueError("Skill IR sample frames must be sorted and unique")
        if any(len(sample.joint_positions) != len(self.joint_names) for sample in self.samples):
            raise ValueError("every sample must match the declared joint_names dimension")
        anchor_ids = {anchor.anchor_id for anchor in self.contacts}
        for phase in self.phases:
            missing = set(phase.required_contact_anchor_ids) - anchor_ids
            if missing:
                raise ValueError(f"phase references missing contacts: {sorted(missing)}")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["samples"] = [sample.to_dict() for sample in self.samples]
        return value

    @property
    def sha256(self) -> str:
        return content_hash(self.to_dict())
