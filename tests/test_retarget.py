from __future__ import annotations

import unittest
from pathlib import Path

from forge.adapters.papers.runners import GMRAdapter
from forge.geometry import Pose
from forge.modules.retarget.planner import RetargetPlanner, RobotCapability
from forge.modules.reconstruction.robot_state import (
    RobotStateCompiler,
    RobotStateFrame,
    SourceRobotCalibration,
)
from forge.modules.skill_ir.models import CanonicalSkillIR, FramePose, SkillPhase, SkillSample
from tests.helpers import SHA


class RetargetTest(unittest.TestCase):
    def test_gmr_adapter_uses_pinned_public_smplx_cli(self) -> None:
        command = GMRAdapter().build_command(
            "unitree_g1", Path("motion.npz"), Path("robot_motion.pkl")
        )
        self.assertEqual(command[1], "scripts/smplx_to_robot.py")
        self.assertIn("--smplx_file", command)
        self.assertIn("--save_path", command)

    def test_direct_robot_state_is_normalized_to_meters(self) -> None:
        calibration = SourceRobotCalibration(
            robot_id="source_arm",
            model_uri="r2://forge-dev/source.urdf",
            model_sha256=SHA,
            joint_names=("joint",),
            source_frame_to_canonical_frame={"tool0": "primary_effector"},
            source_length_unit_in_meters=0.001,
            coordinate_convention="right-handed-z-up-meters",
            calibration_artifact_id="calibration_1",
        )
        skill = RobotStateCompiler().compile(
            skill_id="skill_robot",
            source_demonstration_id="demo_robot",
            motion_family="manipulation",
            validation_profile="manipulation-rigid-v1",
            calibration=calibration,
            frames=(
                RobotStateFrame(
                    frame_index=0,
                    timestamp_s=0.0,
                    source_world_root=Pose(translation_m=(1000.0, 0.0, 0.0)),
                    source_frame_poses=(
                        FramePose("tool0", Pose(translation_m=(1200.0, 0.0, 0.0))),
                    ),
                    joint_positions=(0.1,),
                ),
            ),
            phases=(SkillPhase("move", "move", 0, 0),),
        )
        self.assertAlmostEqual(skill.samples[0].world_root.translation_m[0], 1.0)
        self.assertEqual(skill.samples[0].frame_poses[0].frame_id, "primary_effector")

    def test_robot_source_can_retarget_to_another_robot(self) -> None:
        skill = CanonicalSkillIR(
            skill_id="skill_nav",
            source_demonstration_id="source_robot_rollout",
            source_actor_type="robot",
            source_observation_type="teleop_log",
            motion_family="navigation",
            actor_model_uri="r2://forge-dev/source.urdf",
            actor_model_sha256=SHA,
            joint_names=("wheel_left", "wheel_right"),
            counterpart_asset_ids=("warehouse",),
            gravity_world_m_s2=(0.0, 0.0, -9.81),
            phases=(SkillPhase("navigate", "navigate", 0, 0),),
            samples=(
                SkillSample(
                    0,
                    0.0,
                    Pose.identity(),
                    (FramePose("base", Pose.identity()),),
                    (0.0, 0.0),
                ),
            ),
            contacts=(),
            coordinate_convention="right-handed-z-up-meters",
            validation_profile="navigation-ground-v1",
            reconstruction_artifact_ids=("artifact_source_state",),
            compiler_version="test",
        )
        robot = RobotCapability(
            robot_id="target_amr",
            model_uri="r2://forge-dev/target.urdf",
            model_sha256=SHA,
            motion_families=("navigation",),
            joint_names=("left", "right"),
            controllable_frames=("base",),
            supports_physics_replay=True,
        )
        plan = RetargetPlanner().build(skill, robot)
        self.assertEqual(plan.robot_id, "target_amr")
        self.assertTrue(plan.requires_physics_solver)


if __name__ == "__main__":
    unittest.main()
