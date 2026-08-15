from __future__ import annotations

import unittest

from forge.geometry import Pose
from forge.modules.skill_ir.models import CanonicalSkillIR, FramePose, SkillPhase, SkillSample
from tests.helpers import SHA


class GeometryAndSkillIRTest(unittest.TestCase):
    def test_pose_relative_transform_round_trip(self) -> None:
        parent = Pose(translation_m=(1.0, 2.0, 3.0))
        child_local = Pose(translation_m=(0.2, -0.1, 0.3))
        child_world = parent.compose(child_local)
        self.assertTrue(child_world.relative_to(parent).almost_equal(child_local))

    def test_skill_ir_accepts_robot_source_and_whole_body_frames(self) -> None:
        skill = CanonicalSkillIR(
            skill_id="skill_walk",
            source_demonstration_id="demo_robot_01",
            source_actor_type="robot",
            source_observation_type="robot_state",
            motion_family="locomotion",
            actor_model_uri="r2://forge-dev/models/source.urdf",
            actor_model_sha256=SHA,
            joint_names=("hip", "knee"),
            counterpart_asset_ids=("ground",),
            gravity_world_m_s2=(0.0, 0.0, -9.81),
            phases=(SkillPhase("phase_walk", "walk", 0, 1),),
            samples=(
                SkillSample(
                    frame_index=0,
                    timestamp_s=0.0,
                    world_root=Pose.identity(),
                    frame_poses=(FramePose("left_foot", Pose.identity()),),
                    joint_positions=(0.1, 0.2),
                ),
                SkillSample(
                    frame_index=1,
                    timestamp_s=0.02,
                    world_root=Pose(translation_m=(0.01, 0.0, 0.0)),
                    frame_poses=(
                        FramePose("left_foot", Pose(translation_m=(0.0, 0.0, 0.0))),
                    ),
                    joint_positions=(0.11, 0.19),
                ),
            ),
            contacts=(),
            coordinate_convention="right-handed-z-up-meters",
            validation_profile="locomotion-flat-v1",
            reconstruction_artifact_ids=("artifact_state",),
            compiler_version="test",
        )
        self.assertEqual(skill.motion_family, "locomotion")
        self.assertEqual(len(skill.sha256), 64)


if __name__ == "__main__":
    unittest.main()
