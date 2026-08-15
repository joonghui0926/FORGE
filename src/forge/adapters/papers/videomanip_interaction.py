from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


PHASE_LABELS = (
    "unobserved",
    "free_motion",
    "grasp_hold",
    "transport",
    "target_interaction_hold",
    "target_interaction_motion",
)


@dataclass(frozen=True)
class VideoManipInteractionDiagnostic:
    adapter_id: str
    source_video_sha256: str
    output_npz_sha256: str
    frame_count: int
    fps: float
    width_px: int
    height_px: int
    hand_joint_count: int
    valid_hand_frame_count: int
    valid_grasp_mask_frame_count: int
    valid_target_mask_frame_count: int
    ambiguous_actor_frame_count: int
    grasp_mask_area_px_median: float
    target_mask_area_px_median: float
    hand_grasp_distance_m_p05: float
    hand_grasp_distance_m_median: float
    hand_grasp_distance_m_p95: float
    grasp_target_distance_m_min: float
    grasp_target_distance_m_median: float
    grasp_target_distance_m_max: float
    contact_candidate_frame_count: int
    phase_segments: tuple[dict[str, object], ...]
    phase_labels: tuple[str, ...]
    structural_pass: bool
    robot_ready_accepted: bool
    rejection_reasons: tuple[str, ...]
    videomanip_revision: str
    sam2_revision: str
    sam2_checkpoint_sha256: str
    hamer_revision: str
    hamer_checkpoint_sha256: str
    vitpose_revision: str
    vitpose_checkpoint_sha256: str
    simulation: bool = False
    acceptance_state: str = "metric_interaction_candidate_requires_world_and_target_replay"
    schema_version: str = "forge.videomanip-interaction-diagnostic.v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VideoManipInteractionCompiler:
    """Fuse pinned VideoManip observations into a safe numeric interaction candidate.

    HaMeR's generated ``*_mano_data.npy`` uses a pickled dictionary. This method may only
    read files freshly generated inside the isolated paper worker. It validates and
    immediately rewrites the required numeric fields to a pickle-free NPZ. Customer input
    archives must never be routed into ``human_hand/``.
    """

    adapter_id = "videomanip-metric-interaction-v1"

    def compile(
        self,
        dataset_root: Path,
        source_video: Path,
        output_npz: Path,
        *,
        fps: float,
        contact_distance_m: float = 0.035,
        target_near_distance_m: float = 0.25,
        motion_speed_m_s: float = 0.025,
        videomanip_revision: str,
        sam2_revision: str,
        sam2_checkpoint_sha256: str,
        hamer_revision: str,
        hamer_checkpoint_sha256: str,
        vitpose_revision: str,
        vitpose_checkpoint_sha256: str,
    ) -> VideoManipInteractionDiagnostic:
        if not dataset_root.is_dir():
            raise FileNotFoundError(dataset_root)
        if not source_video.is_file():
            raise FileNotFoundError(source_video)
        if fps <= 0 or contact_distance_m <= 0 or target_near_distance_m <= 0:
            raise ValueError("VIDEOMANIP_INTERACTION_THRESHOLD_INVALID")
        try:
            import cv2
            import numpy as np
        except ImportError as error:
            raise RuntimeError("VIDEOMANIP_INTERACTION_DEPENDENCY_MISSING") from error

        rgb_paths = sorted((dataset_root / "rgb").glob("*.png"))
        if not rgb_paths:
            raise ValueError("VIDEOMANIP_RGB_FRAMES_MISSING")
        first_rgb = cv2.imread(str(rgb_paths[0]), cv2.IMREAD_UNCHANGED)
        if first_rgb is None:
            raise ValueError("VIDEOMANIP_RGB_FRAME_UNREADABLE")
        height, width = int(first_rgb.shape[0]), int(first_rgb.shape[1])
        frame_count = len(rgb_paths)

        hand_joints = np.full((frame_count, 21, 3), np.nan, dtype=np.float32)
        grasp_centroids = np.full((frame_count, 3), np.nan, dtype=np.float32)
        target_centroids = np.full((frame_count, 3), np.nan, dtype=np.float32)
        contact_points = np.full((frame_count, 3), np.nan, dtype=np.float32)
        contact_joint_indices = np.full(frame_count, -1, dtype=np.int16)
        hand_grasp_distances = np.full(frame_count, np.nan, dtype=np.float32)
        grasp_mask_areas = np.zeros(frame_count, dtype=np.int32)
        target_mask_areas = np.zeros(frame_count, dtype=np.int32)
        ambiguous_actor_frames = 0

        for frame_index, rgb_path in enumerate(rgb_paths):
            stem = rgb_path.stem
            intrinsic_path = dataset_root / "cam_info" / f"camera_K_{rgb_path.name}.txt"
            depth_path = dataset_root / "depth" / rgb_path.name
            grasp_path = dataset_root / "masks_pred_obj" / f"{stem}_grasp_object.png"
            target_path = dataset_root / "masks_pred_obj" / f"{stem}_target_object.png"
            mano_path = dataset_root / "human_hand" / f"{stem}_mano_data.npy"
            if any(path.is_symlink() for path in (intrinsic_path, depth_path, grasp_path, target_path, mano_path)):
                raise ValueError("VIDEOMANIP_GENERATED_OUTPUT_SYMLINK_FORBIDDEN")
            if not all(
                path.is_file()
                for path in (intrinsic_path, depth_path, grasp_path, target_path, mano_path)
            ):
                continue

            try:
                intrinsic = np.asarray(np.loadtxt(intrinsic_path), dtype=np.float64)
                depth = cv2.imread(str(depth_path), cv2.IMREAD_UNCHANGED)
                grasp_mask = cv2.imread(str(grasp_path), cv2.IMREAD_GRAYSCALE)
                target_mask = cv2.imread(str(target_path), cv2.IMREAD_GRAYSCALE)
                people = np.load(mano_path, allow_pickle=True).item()
            except (OSError, ValueError, EOFError):
                continue
            if (
                intrinsic.shape != (3, 3)
                or not np.isfinite(intrinsic).all()
                or depth is None
                or depth.shape != (height, width)
                or depth.dtype != np.uint16
                or grasp_mask is None
                or target_mask is None
                or not isinstance(people, dict)
                or not people
            ):
                continue
            if len(people) != 1:
                ambiguous_actor_frames += 1
                continue
            person = people[sorted(people)[0]]
            if not isinstance(person, dict) or "mano_retarget_hand_joints" not in person:
                continue
            joints = np.asarray(person["mano_retarget_hand_joints"], dtype=np.float32)
            if joints.shape != (21, 3) or not np.isfinite(joints).all():
                continue

            grasp_points, grasp_area = self._masked_points(
                depth, grasp_mask, intrinsic, np
            )
            target_points, target_area = self._masked_points(
                depth, target_mask, intrinsic, np
            )
            if grasp_points.size == 0 or target_points.size == 0:
                continue
            distance_m, joint_index, surface_point = self._nearest_surface_point(
                joints, grasp_points, np
            )
            hand_joints[frame_index] = joints
            grasp_centroids[frame_index] = np.median(grasp_points, axis=0)
            target_centroids[frame_index] = np.median(target_points, axis=0)
            contact_points[frame_index] = surface_point
            contact_joint_indices[frame_index] = joint_index
            hand_grasp_distances[frame_index] = distance_m
            grasp_mask_areas[frame_index] = grasp_area
            target_mask_areas[frame_index] = target_area

        valid_hand = np.isfinite(hand_joints).all(axis=(1, 2))
        valid_grasp = np.isfinite(grasp_centroids).all(axis=1)
        valid_target = np.isfinite(target_centroids).all(axis=1)
        complete = valid_hand & valid_grasp & valid_target
        timestamps = np.arange(frame_count, dtype=np.float64) / fps
        grasp_speeds = self._speeds(grasp_centroids, complete, fps, np)
        grasp_target_distances = np.linalg.norm(grasp_centroids - target_centroids, axis=1)
        contact_candidates = complete & (hand_grasp_distances <= contact_distance_m)
        phase_codes = self._phase_codes(
            complete,
            contact_candidates,
            grasp_speeds,
            grasp_target_distances,
            target_near_distance_m,
            motion_speed_m_s,
            np,
        )
        phase_segments = self.segment_phases(tuple(int(value) for value in phase_codes))

        output_npz.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            output_npz,
            frame_index=np.arange(frame_count, dtype=np.int32),
            timestamp_s=timestamps,
            hand_joints_camera_m=hand_joints,
            grasp_object_centroid_camera_m=grasp_centroids,
            target_object_centroid_camera_m=target_centroids,
            hand_grasp_surface_point_camera_m=contact_points,
            hand_grasp_joint_index=contact_joint_indices,
            hand_grasp_distance_m=hand_grasp_distances,
            grasp_object_speed_m_s=grasp_speeds,
            grasp_target_distance_m=grasp_target_distances,
            grasp_mask_area_px=grasp_mask_areas,
            target_mask_area_px=target_mask_areas,
            contact_candidate=contact_candidates.astype(np.uint8),
            phase_code=phase_codes,
        )

        valid_distance = hand_grasp_distances[np.isfinite(hand_grasp_distances)]
        valid_object_distance = grasp_target_distances[np.isfinite(grasp_target_distances)]
        structural_pass = bool(
            complete.all()
            and ambiguous_actor_frames == 0
            and valid_distance.size == frame_count
            and valid_object_distance.size == frame_count
        )
        return VideoManipInteractionDiagnostic(
            adapter_id=self.adapter_id,
            source_video_sha256=sha256(source_video.read_bytes()).hexdigest(),
            output_npz_sha256=sha256(output_npz.read_bytes()).hexdigest(),
            frame_count=frame_count,
            fps=float(fps),
            width_px=width,
            height_px=height,
            hand_joint_count=21,
            valid_hand_frame_count=int(valid_hand.sum()),
            valid_grasp_mask_frame_count=int(valid_grasp.sum()),
            valid_target_mask_frame_count=int(valid_target.sum()),
            ambiguous_actor_frame_count=ambiguous_actor_frames,
            grasp_mask_area_px_median=self._median(grasp_mask_areas[grasp_mask_areas > 0], np),
            target_mask_area_px_median=self._median(target_mask_areas[target_mask_areas > 0], np),
            hand_grasp_distance_m_p05=self._percentile(valid_distance, 5, np),
            hand_grasp_distance_m_median=self._percentile(valid_distance, 50, np),
            hand_grasp_distance_m_p95=self._percentile(valid_distance, 95, np),
            grasp_target_distance_m_min=self._minimum(valid_object_distance, np),
            grasp_target_distance_m_median=self._median(valid_object_distance, np),
            grasp_target_distance_m_max=self._maximum(valid_object_distance, np),
            contact_candidate_frame_count=int(contact_candidates.sum()),
            phase_segments=phase_segments,
            phase_labels=PHASE_LABELS,
            structural_pass=structural_pass,
            robot_ready_accepted=False,
            rejection_reasons=(
                "camera-to-world transform and gravity are not independently calibrated",
                "object orientation and rigid 6-DoF pose are not reconstructed",
                "contact candidates lack opposed surface-normal validation",
                "no target robot model, controller, action trajectory, or closed-loop replay",
            ),
            videomanip_revision=videomanip_revision,
            sam2_revision=sam2_revision,
            sam2_checkpoint_sha256=sam2_checkpoint_sha256,
            hamer_revision=hamer_revision,
            hamer_checkpoint_sha256=hamer_checkpoint_sha256,
            vitpose_revision=vitpose_revision,
            vitpose_checkpoint_sha256=vitpose_checkpoint_sha256,
        )

    @staticmethod
    def _masked_points(depth: Any, mask: Any, intrinsic: Any, np: Any) -> tuple[Any, int]:
        selected = (mask > 0) & (depth > 0)
        rows, columns = np.nonzero(selected)
        if rows.size == 0:
            return np.empty((0, 3), dtype=np.float32), 0
        z = depth[rows, columns].astype(np.float32) / 1000.0
        x = (columns.astype(np.float32) - float(intrinsic[0, 2])) * z / float(
            intrinsic[0, 0]
        )
        y = (rows.astype(np.float32) - float(intrinsic[1, 2])) * z / float(
            intrinsic[1, 1]
        )
        return np.stack((x, y, z), axis=1), int(rows.size)

    @staticmethod
    def _nearest_surface_point(joints: Any, points: Any, np: Any) -> tuple[float, int, Any]:
        best_distance_squared = float("inf")
        best_joint = -1
        best_point = None
        for start in range(0, len(points), 8192):
            chunk = points[start : start + 8192]
            squared = np.sum((chunk[:, None, :] - joints[None, :, :]) ** 2, axis=2)
            flat_index = int(np.argmin(squared))
            point_index, joint_index = np.unravel_index(flat_index, squared.shape)
            value = float(squared[point_index, joint_index])
            if value < best_distance_squared:
                best_distance_squared = value
                best_joint = int(joint_index)
                best_point = chunk[point_index].copy()
        if best_point is None:
            raise ValueError("VIDEOMANIP_GRASP_SURFACE_EMPTY")
        return float(np.sqrt(best_distance_squared)), best_joint, best_point

    @staticmethod
    def _speeds(centroids: Any, valid: Any, fps: float, np: Any) -> Any:
        speeds = np.full(len(centroids), np.nan, dtype=np.float32)
        if len(centroids) == 0:
            return speeds
        speeds[0] = 0.0 if valid[0] else np.nan
        pair_valid = valid[1:] & valid[:-1]
        values = np.linalg.norm(np.diff(centroids, axis=0), axis=1) * fps
        speeds[1:][pair_valid] = values[pair_valid]
        return speeds

    @staticmethod
    def _phase_codes(
        complete: Any,
        contact: Any,
        speed: Any,
        target_distance: Any,
        target_near_distance_m: float,
        motion_speed_m_s: float,
        np: Any,
    ) -> Any:
        moving = np.isfinite(speed) & (speed >= motion_speed_m_s)
        near_target = np.isfinite(target_distance) & (
            target_distance <= target_near_distance_m
        )
        codes = np.zeros(len(complete), dtype=np.int16)
        codes[complete & ~contact] = 1
        codes[complete & contact & ~moving & ~near_target] = 2
        codes[complete & contact & moving & ~near_target] = 3
        codes[complete & contact & ~moving & near_target] = 4
        codes[complete & contact & moving & near_target] = 5
        return codes

    @staticmethod
    def segment_phases(codes: tuple[int, ...]) -> tuple[dict[str, object], ...]:
        if not codes:
            return ()
        segments: list[dict[str, object]] = []
        start = 0
        for frame_index in range(1, len(codes) + 1):
            if frame_index < len(codes) and codes[frame_index] == codes[start]:
                continue
            code = codes[start]
            segments.append(
                {
                    "phase_id": f"phase_{len(segments):04d}",
                    "label": PHASE_LABELS[code],
                    "start_frame": start,
                    "end_frame": frame_index - 1,
                }
            )
            start = frame_index
        return tuple(segments)

    @staticmethod
    def _percentile(values: Any, percentile: float, np: Any) -> float:
        return 0.0 if values.size == 0 else float(np.percentile(values, percentile))

    @staticmethod
    def _median(values: Any, np: Any) -> float:
        return 0.0 if values.size == 0 else float(np.median(values))

    @staticmethod
    def _minimum(values: Any, np: Any) -> float:
        return 0.0 if values.size == 0 else float(np.min(values))

    @staticmethod
    def _maximum(values: Any, np: Any) -> float:
        return 0.0 if values.size == 0 else float(np.max(values))
