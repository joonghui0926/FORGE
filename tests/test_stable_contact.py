from __future__ import annotations

import unittest

from forge.geometry import Pose
from forge.modules.stable_contact.compiler import ContactCandidate, StableContactCompiler


def candidate(frame: int, world_object: Pose, local_x: float, visibility: float = 0.9):
    return ContactCandidate(
        frame_index=frame,
        phase_id="support",
        actor_region="left_foot",
        actor_vertex_id=1,
        counterpart_id="ground",
        counterpart_frame="ground",
        contact_type="environment",
        world_point_m=world_object.transform_point((local_x, 0.0, 0.0)),
        world_counterpart=world_object,
        actor_normal_world=(0.0, 0.0, -1.0),
        counterpart_normal_world=(0.0, 0.0, 1.0),
        surface_distance_m=0.002,
        relative_speed_m_s=0.01,
        visibility=visibility,
    )


class StableContactTest(unittest.TestCase):
    def test_canonical_contact_is_invariant_to_world_translation_and_rejects_outlier(self) -> None:
        object_pose = Pose(translation_m=(2.0, -1.0, 0.5))
        candidates = tuple(candidate(frame, object_pose, 0.01 + frame * 0.0002) for frame in range(6))
        candidates += (candidate(6, object_pose, 0.3),)
        result = StableContactCompiler().compile(candidates)
        self.assertEqual(len(result.anchors), 1)
        self.assertAlmostEqual(result.anchors[0].counterpart_point_m[0], 0.0104, places=3)
        self.assertNotIn(6, result.anchors[0].support_frames)

    def test_occlusion_cannot_create_stable_contact(self) -> None:
        pose = Pose.identity()
        result = StableContactCompiler().compile(
            tuple(candidate(frame, pose, 0.01, visibility=0.1) for frame in range(6))
        )
        self.assertFalse(result.anchors)
        self.assertEqual(result.rejection_counts["CONTACT_UNOBSERVED"], 6)


if __name__ == "__main__":
    unittest.main()
