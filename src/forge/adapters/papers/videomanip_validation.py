from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class VideoManipMetricDiagnostic:
    adapter_id: str
    source_video_sha256: str
    videomanip_revision: str
    moge_revision: str
    checkpoint_revision: str
    frame_count: int
    intrinsics_count: int
    depth_map_count: int
    width_px: int
    height_px: int
    missing_intrinsics_count: int
    missing_depth_count: int
    invalid_intrinsics_count: int
    invalid_depth_count: int
    depth_dtype: str
    depth_positive_fraction: float
    depth_saturation_fraction: float
    depth_mm_min: int
    depth_mm_median: float
    depth_mm_p95: float
    depth_mm_max: int
    fx_mean_px: float
    fx_cv: float
    fy_mean_px: float
    fy_cv: float
    cx_range_px: tuple[float, float]
    cy_range_px: tuple[float, float]
    structural_pass: bool
    robot_ready_accepted: bool
    rejection_reasons: tuple[str, ...]
    simulation: bool = False
    acceptance_state: str = (
        "metric_reconstruction_candidate_requires_calibration_and_target_replay"
    )
    schema_version: str = "forge.videomanip-metric-diagnostic.v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VideoManipMetricEvaluator:
    """Validate VideoManip's MoGe intermediate without claiming robot readiness.

    The paper stage writes one camera matrix and one uint16 millimetre depth PNG per RGB
    frame. This evaluator checks that contract and records deterministic statistics. It
    cannot prove metric accuracy from monocular input, infer robot actions, or replace an
    exact-target replay, so its result is always an unapproved perception candidate.
    """

    adapter_id = "videomanip-moge-metric-diagnostic-v1"

    def evaluate(
        self,
        dataset_root: Path,
        source_video: Path,
        *,
        expected_frames: int,
        videomanip_revision: str,
        moge_revision: str,
        checkpoint_revision: str,
    ) -> VideoManipMetricDiagnostic:
        if not dataset_root.is_dir():
            raise FileNotFoundError(dataset_root)
        if not source_video.is_file():
            raise FileNotFoundError(source_video)
        if expected_frames < 1:
            raise ValueError("VIDEOMANIP_EXPECTED_FRAME_COUNT_INVALID")
        try:
            import cv2
            import numpy as np
        except ImportError as error:
            raise RuntimeError("VIDEOMANIP_VALIDATION_DEPENDENCY_MISSING") from error

        rgb_paths = sorted((dataset_root / "rgb").glob("*.png"))
        intrinsics_paths = sorted((dataset_root / "cam_info").glob("camera_K_*.txt"))
        depth_paths = sorted((dataset_root / "depth").glob("*.png"))
        if not rgb_paths:
            raise ValueError("VIDEOMANIP_RGB_FRAMES_MISSING")

        rgb_names = {path.name for path in rgb_paths}
        intrinsics_names = {
            path.name.removeprefix("camera_K_").removesuffix(".txt")
            for path in intrinsics_paths
        }
        depth_names = {path.name for path in depth_paths}
        missing_intrinsics = rgb_names - intrinsics_names
        missing_depth = rgb_names - depth_names

        first_rgb = cv2.imread(str(rgb_paths[0]), cv2.IMREAD_UNCHANGED)
        if first_rgb is None or first_rgb.ndim < 2:
            raise ValueError("VIDEOMANIP_RGB_FRAME_UNREADABLE")
        height, width = (int(first_rgb.shape[0]), int(first_rgb.shape[1]))

        intrinsics: list[Any] = []
        invalid_intrinsics_count = 0
        for path in intrinsics_paths:
            try:
                matrix = np.asarray(np.loadtxt(path), dtype=np.float64)
            except (OSError, ValueError):
                invalid_intrinsics_count += 1
                continue
            if not self._valid_intrinsics(matrix, width, height, np):
                invalid_intrinsics_count += 1
                continue
            intrinsics.append(matrix)

        histogram = np.zeros(65_536, dtype=np.int64)
        invalid_depth_count = 0
        depth_dtype = "missing"
        for path in depth_paths:
            depth = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            if depth is None:
                invalid_depth_count += 1
                continue
            depth_dtype = str(depth.dtype)
            if depth.ndim != 2 or depth.shape != (height, width) or depth.dtype != np.uint16:
                invalid_depth_count += 1
                continue
            histogram += np.bincount(depth.reshape(-1), minlength=65_536)

        total_depth_pixels = int(histogram.sum())
        positive_pixels = total_depth_pixels - int(histogram[0])
        positive_fraction = (
            0.0 if total_depth_pixels == 0 else positive_pixels / total_depth_pixels
        )
        saturation_fraction = (
            0.0 if total_depth_pixels == 0 else int(histogram[-1]) / total_depth_pixels
        )
        depth_min, depth_median, depth_p95, depth_max = self._depth_quantiles(
            histogram, positive_pixels, np
        )

        if intrinsics:
            matrices = np.stack(intrinsics)
            fx = matrices[:, 0, 0]
            fy = matrices[:, 1, 1]
            cx = matrices[:, 0, 2]
            cy = matrices[:, 1, 2]
            fx_mean = float(fx.mean())
            fy_mean = float(fy.mean())
            fx_cv = float(fx.std() / fx_mean)
            fy_cv = float(fy.std() / fy_mean)
            cx_range = (float(cx.min()), float(cx.max()))
            cy_range = (float(cy.min()), float(cy.max()))
        else:
            fx_mean = fy_mean = fx_cv = fy_cv = 0.0
            cx_range = cy_range = (0.0, 0.0)

        frame_count = len(rgb_paths)
        structural_pass = all(
            (
                frame_count == expected_frames,
                len(intrinsics_paths) == expected_frames,
                len(depth_paths) == expected_frames,
                not missing_intrinsics,
                not missing_depth,
                invalid_intrinsics_count == 0,
                invalid_depth_count == 0,
                positive_fraction > 0.5,
            )
        )
        return VideoManipMetricDiagnostic(
            adapter_id=self.adapter_id,
            source_video_sha256=sha256(source_video.read_bytes()).hexdigest(),
            videomanip_revision=videomanip_revision,
            moge_revision=moge_revision,
            checkpoint_revision=checkpoint_revision,
            frame_count=frame_count,
            intrinsics_count=len(intrinsics_paths),
            depth_map_count=len(depth_paths),
            width_px=width,
            height_px=height,
            missing_intrinsics_count=len(missing_intrinsics),
            missing_depth_count=len(missing_depth),
            invalid_intrinsics_count=invalid_intrinsics_count,
            invalid_depth_count=invalid_depth_count,
            depth_dtype=depth_dtype,
            depth_positive_fraction=float(positive_fraction),
            depth_saturation_fraction=float(saturation_fraction),
            depth_mm_min=depth_min,
            depth_mm_median=depth_median,
            depth_mm_p95=depth_p95,
            depth_mm_max=depth_max,
            fx_mean_px=fx_mean,
            fx_cv=fx_cv,
            fy_mean_px=fy_mean,
            fy_cv=fy_cv,
            cx_range_px=cx_range,
            cy_range_px=cy_range,
            structural_pass=structural_pass,
            robot_ready_accepted=False,
            rejection_reasons=(
                "no independent metric-depth or camera-calibration ground truth",
                "no target-robot state/action trajectory",
                "no contact and phase labels",
                "no exact-target closed-loop replay evidence",
            ),
        )

    @staticmethod
    def _valid_intrinsics(matrix: Any, width: int, height: int, np: Any) -> bool:
        return bool(
            matrix.shape == (3, 3)
            and np.isfinite(matrix).all()
            and matrix[0, 0] > 0.0
            and matrix[1, 1] > 0.0
            and 0.0 <= matrix[0, 2] <= width
            and 0.0 <= matrix[1, 2] <= height
            and abs(float(matrix[2, 2]) - 1.0) <= 1e-6
        )

    @staticmethod
    def _depth_quantiles(histogram: Any, positive_pixels: int, np: Any) -> tuple[int, float, float, int]:
        if positive_pixels == 0:
            return 0, 0.0, 0.0, 0
        positive = histogram.copy()
        positive[0] = 0
        cumulative = np.cumsum(positive)

        def percentile(fraction: float) -> int:
            rank = max(1, int(np.ceil(positive_pixels * fraction)))
            return int(np.searchsorted(cumulative, rank, side="left"))

        return percentile(0.0), float(percentile(0.5)), float(percentile(0.95)), percentile(1.0)
