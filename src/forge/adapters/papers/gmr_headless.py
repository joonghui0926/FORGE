from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

from forge.adapters.papers.runners import GMRAdapter


@dataclass(frozen=True)
class GMRHeadlessResult:
    adapter_id: str
    source_sha256: str
    output_sha256: str
    output_path: str
    robot_id: str
    source_frame_count: int
    output_frame_count: int
    fps: int
    duration_s: float
    revision: str
    simulation: bool = False
    acceptance_state: str = "candidate_requires_independent_replay"
    schema_version: str = "forge.gmr-headless-result.v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GMRHeadlessRunner:
    """Runs GMR retargeting without its mandatory desktop viewer dependency."""

    adapter_id = "gmr-xsens-headless-v1"
    allowed_xsens_robots = frozenset({"unitree_g1", "unitree_h1_2", "Q1", "X1"})

    def retarget_xsens_bvh(
        self,
        checkout: Path,
        bvh_file: Path,
        output_file: Path,
        robot_id: str,
        *,
        start_frame: int | None = None,
        end_frame: int | None = None,
        scale: float = 0.01,
        reset_to_zero: bool = False,
        offsets_file: Path | None = None,
    ) -> GMRHeadlessResult:
        if robot_id not in self.allowed_xsens_robots:
            raise ValueError("GMR_XSENS_ROBOT_UNSUPPORTED")
        if scale <= 0:
            raise ValueError("GMR_BVH_SCALE_MUST_BE_POSITIVE")
        if not bvh_file.is_file():
            raise FileNotFoundError(bvh_file)
        GMRAdapter().assert_checkout(checkout)
        if str(checkout) not in sys.path:
            sys.path.insert(0, str(checkout))

        try:
            import numpy as np
            from general_motion_retargeting import GeneralMotionRetargeting
            from general_motion_retargeting.utils.lafan_vendor import utils
            from general_motion_retargeting.utils.xsens_vendor.BVHParser import Anim, BVHParser
        except ImportError as error:
            raise RuntimeError("GMR_RUNTIME_DEPENDENCY_MISSING") from error

        parser = BVHParser(axis_order="zxy", scale=scale)
        bvh_text = bvh_file.read_text(encoding="utf-8", errors="strict")
        rotations, _ = parser.parse(
            bvh_text,
            start=start_frame,
            end=end_frame,
            reset_to_zero=reset_to_zero,
        )
        offsets = self._load_offsets(offsets_file)
        joint_offsets = np.zeros_like(rotations)
        axes = ("X", "Y", "Z")
        for joint_index, joint_name in enumerate(parser.names):
            configured = offsets.get(joint_name, {})
            for axis_index, axis in enumerate(axes):
                joint_offsets[:, joint_index, axis_index] = float(configured.get(axis, 0.0))
        quaternions, positions, skeleton_offsets, parents = parser._MOTION_data_post_processing(
            rotations + joint_offsets,
            np.copy(parser.positions),
            reset_to_zero=True,
        )
        animation = Anim(quaternions, positions, skeleton_offsets, parents, parser.names)
        global_rotation, global_position = utils.quat_fk(
            animation.quats, animation.pos, animation.parents
        )
        frames: list[dict[str, tuple[Any, Any]]] = []
        for frame_index in range(animation.pos.shape[0]):
            frame = {
                bone: (global_position[frame_index, index], global_rotation[frame_index, index])
                for index, bone in enumerate(animation.bones)
            }
            frame["LeftFootMod"] = frame["LeftAnkle"]
            frame["RightFootMod"] = frame["RightAnkle"]
            frames.append(frame)
        if not frames:
            raise ValueError("GMR_BVH_CONTAINS_NO_FRAMES")
        last = frames[-1]
        human_height = float(
            last["Head_end_site"][0][2]
            - min(last["LeftToe_end_site"][0][2], last["RightToe_end_site"][0][2])
        )
        if human_height <= 0:
            raise ValueError("GMR_BVH_HUMAN_HEIGHT_INVALID")

        started = perf_counter()
        retargeter = GeneralMotionRetargeting(
            src_human="bvh_xsens",
            tgt_robot=robot_id,
            actual_human_height=human_height,
        )
        qpos = np.asarray([retargeter.retarget(frame) for frame in frames])
        duration_s = perf_counter() - started
        if qpos.ndim != 2 or not np.isfinite(qpos).all():
            raise RuntimeError("GMR_OUTPUT_NONFINITE_OR_WRONG_RANK")
        fps = max(1, int(round(1.0 / float(parser.frame_time))))
        source_digest = sha256(bvh_file.read_bytes()).hexdigest()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            output_file,
            qpos=qpos,
            root_position_m=qpos[:, :3],
            root_quaternion_wxyz=qpos[:, 3:7],
            dof_position_rad=qpos[:, 7:],
            fps=np.asarray(fps),
            robot_id=np.asarray(robot_id),
            source_sha256=np.asarray(source_digest),
            gmr_revision=np.asarray(GMRAdapter.revision),
        )
        output_digest = sha256(output_file.read_bytes()).hexdigest()
        return GMRHeadlessResult(
            adapter_id=self.adapter_id,
            source_sha256=source_digest,
            output_sha256=output_digest,
            output_path=str(output_file),
            robot_id=robot_id,
            source_frame_count=len(frames),
            output_frame_count=int(qpos.shape[0]),
            fps=fps,
            duration_s=duration_s,
            revision=GMRAdapter.revision,
        )

    @staticmethod
    def _load_offsets(offsets_file: Path | None) -> dict[str, dict[str, float]]:
        if offsets_file is None:
            return {}
        document = json.loads(offsets_file.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("GMR_OFFSETS_MUST_BE_OBJECT")
        return document
