from __future__ import annotations

import unittest

from forge.geometry import Pose
from forge.modules.amplification.compiler import (
    AmplificationCompiler,
    RobotEpisode,
    RobotTrajectorySample,
    WorldTransform,
)
from forge.modules.skill_ir.models import FramePose
from tests.helpers import accepted_quality


class AmplificationTest(unittest.TestCase):
    def source(self, motion_family: str = "locomotion") -> RobotEpisode:
        return RobotEpisode(
            episode_id="ep_source",
            source_demonstration_id="demo_source",
            motion_family=motion_family,
            validation_profile="locomotion-flat-v1",
            robot_id="robot_1",
            samples=(
                RobotTrajectorySample(
                    timestamp_s=0.0,
                    world_root=Pose(translation_m=(1.0, 0.0, 0.0)),
                    frame_poses=(
                        FramePose("left_foot", Pose(translation_m=(1.0, 0.2, -0.5))),
                    ),
                    qpos=(0.1,),
                    action=(0.0,),
                ),
            ),
            replay_artifact_id="replay_1",
        )

    def test_ground_plane_transform_preserves_body_relative_geometry(self) -> None:
        source = self.source()
        before = source.samples[0].frame_poses[0].world_pose.relative_to(source.samples[0].world_root)
        generated = AmplificationCompiler().amplify(
            source,
            accepted_quality(motion_family="locomotion"),
            (WorldTransform("shift", Pose(translation_m=(2.0, 3.0, 0.0)), "ground_plane"),),
            "development",
        )[0]
        sample = generated.trajectory.samples[0]
        after = sample.frame_poses[0].world_pose.relative_to(sample.world_root)
        self.assertTrue(before.almost_equal(after))
        self.assertTrue(generated.requires_revalidation)

    def test_simulated_acceptance_is_forbidden_in_production(self) -> None:
        with self.assertRaises(PermissionError):
            AmplificationCompiler().amplify(
                self.source(),
                accepted_quality(motion_family="locomotion"),
                (WorldTransform("shift", Pose.identity(), "ground_plane"),),
                "production",
            )


if __name__ == "__main__":
    unittest.main()
