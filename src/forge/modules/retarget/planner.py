from __future__ import annotations

from dataclasses import dataclass

from forge.geometry import Pose
from forge.modules.skill_ir.models import CanonicalSkillIR


@dataclass(frozen=True)
class RobotCapability:
    robot_id: str
    model_uri: str
    model_sha256: str
    motion_families: tuple[str, ...]
    joint_names: tuple[str, ...]
    controllable_frames: tuple[str, ...]
    supports_physics_replay: bool


@dataclass(frozen=True)
class RetargetConstraint:
    frame_index: int
    constraint_type: str
    target_frame: str
    target_pose: Pose | None
    contact_anchor_id: str | None
    weight: float


@dataclass(frozen=True)
class RetargetPlan:
    skill_id: str
    robot_id: str
    motion_family: str
    validation_profile: str
    constraints: tuple[RetargetConstraint, ...]
    requires_physics_solver: bool
    source_skill_ir_sha256: str
    planner_version: str = "forge-retarget-plan-v1"


class RetargetPlanner:
    """Builds embodiment-aware constraints without pretending to solve dynamics locally."""

    def build(self, skill: CanonicalSkillIR, robot: RobotCapability) -> RetargetPlan:
        if skill.motion_family not in robot.motion_families:
            raise ValueError("TARGET_ROBOT_MOTION_FAMILY_UNSUPPORTED")
        if not robot.supports_physics_replay:
            raise ValueError("TARGET_ROBOT_REPLAY_UNAVAILABLE")

        constraints: list[RetargetConstraint] = []
        for sample in skill.samples:
            constraints.append(
                RetargetConstraint(
                    frame_index=sample.frame_index,
                    constraint_type="root_pose",
                    target_frame="root",
                    target_pose=sample.world_root,
                    contact_anchor_id=None,
                    weight=1.0,
                )
            )
            for frame_pose in sample.frame_poses:
                if frame_pose.frame_id in robot.controllable_frames:
                    constraints.append(
                        RetargetConstraint(
                            frame_index=sample.frame_index,
                            constraint_type="frame_pose",
                            target_frame=frame_pose.frame_id,
                            target_pose=frame_pose.world_pose,
                            contact_anchor_id=None,
                            weight=1.0,
                        )
                    )
        for contact in skill.contacts:
            constraints.append(
                RetargetConstraint(
                    frame_index=contact.support_frames[0],
                    constraint_type=f"contact:{contact.contact_type}",
                    target_frame=contact.actor_region,
                    target_pose=None,
                    contact_anchor_id=contact.anchor_id,
                    weight=max(0.1, contact.confidence),
                )
            )

        if not constraints:
            raise ValueError("RETARGET_CONSTRAINTS_EMPTY")
        return RetargetPlan(
            skill_id=skill.skill_id,
            robot_id=robot.robot_id,
            motion_family=skill.motion_family,
            validation_profile=skill.validation_profile,
            constraints=tuple(constraints),
            requires_physics_solver=True,
            source_skill_ir_sha256=skill.sha256,
        )
