from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DoAsIDoReplayResult:
    adapter_id: str
    scene_sha256: str
    trajectory_sha256: str
    trajectory_frame_count: int
    trajectory_segment_count: int
    simulated_step_count: int
    model_nq: int
    model_nv: int
    model_nu: int
    trajectory_dt_median_s: float
    model_timestep_s: float
    free_joint_translation_rmse_m: float
    orientation_rmse_rad: float
    hinge_joint_rmse_rad: float
    slide_joint_rmse_m: float
    max_penetration_m: float
    joint_limit_violation_count: int
    nonfinite_state_count: int
    simulation: bool = False
    acceptance_state: str = "diagnostic_only_profile_not_approved"
    schema_version: str = "forge.do-as-i-do-replay.v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DoAsIDoReplayEvaluator:
    """Replays a Do As I Do control trajectory in MuJoCo without accepting it."""

    adapter_id = "do-as-i-do-mujoco-replay-v1"
    required_arrays = frozenset({"qpos", "qvel", "ctrl", "time"})

    def evaluate(self, scene_xml: Path, trajectory_npz: Path) -> DoAsIDoReplayResult:
        if not scene_xml.is_file():
            raise FileNotFoundError(scene_xml)
        if not trajectory_npz.is_file():
            raise FileNotFoundError(trajectory_npz)
        try:
            import mujoco
            import numpy as np
        except ImportError as error:
            raise RuntimeError("DO_AS_I_DO_REPLAY_DEPENDENCY_MISSING") from error

        with np.load(trajectory_npz, allow_pickle=False) as archive:
            missing = self.required_arrays - set(archive.files)
            if missing:
                raise ValueError(f"DO_AS_I_DO_REPLAY_ARRAY_MISSING:{','.join(sorted(missing))}")
            qpos = np.asarray(archive["qpos"], dtype=np.float64)
            qvel = np.asarray(archive["qvel"], dtype=np.float64)
            controls = np.asarray(archive["ctrl"], dtype=np.float64)
            timestamps = np.asarray(archive["time"], dtype=np.float64)
        if qpos.ndim not in {2, 3} or qvel.ndim != qpos.ndim or controls.ndim != qpos.ndim:
            raise ValueError("DO_AS_I_DO_REPLAY_ARRAY_RANK_INVALID")
        if timestamps.ndim != qpos.ndim - 1:
            raise ValueError("DO_AS_I_DO_REPLAY_ARRAY_RANK_INVALID")
        leading_shape = qpos.shape[:-1]
        if qvel.shape[:-1] != leading_shape or controls.shape[:-1] != leading_shape:
            raise ValueError("DO_AS_I_DO_REPLAY_FRAME_COUNT_INVALID")
        if timestamps.shape != leading_shape:
            raise ValueError("DO_AS_I_DO_REPLAY_FRAME_COUNT_INVALID")
        qpos_segments = qpos[None, ...] if qpos.ndim == 2 else qpos
        qvel_segments = qvel[None, ...] if qvel.ndim == 2 else qvel
        control_segments = controls[None, ...] if controls.ndim == 2 else controls
        time_segments = timestamps[None, ...] if timestamps.ndim == 1 else timestamps
        segment_count = int(qpos_segments.shape[0])
        frames_per_segment = int(qpos_segments.shape[1])
        frame_count = segment_count * frames_per_segment
        if frames_per_segment < 2:
            raise ValueError("DO_AS_I_DO_REPLAY_FRAME_COUNT_INVALID")
        if not all(np.isfinite(array).all() for array in (qpos, qvel, controls, timestamps)):
            raise ValueError("DO_AS_I_DO_REPLAY_INPUT_NONFINITE")
        time_steps = np.diff(time_segments.reshape(-1))
        if not np.all(time_steps > 0):
            raise ValueError("DO_AS_I_DO_REPLAY_TIME_NOT_MONOTONIC")

        model = mujoco.MjModel.from_xml_path(str(scene_xml.resolve()))
        if qpos_segments.shape[2] != model.nq or qvel_segments.shape[2] != model.nv:
            raise ValueError("DO_AS_I_DO_REPLAY_STATE_DIMENSION_MISMATCH")
        if control_segments.shape[2] != model.nu:
            raise ValueError("DO_AS_I_DO_REPLAY_CONTROL_DIMENSION_MISMATCH")
        data = mujoco.MjData(model)

        tracking_error_sums = {
            "free_translation": 0.0,
            "orientation": 0.0,
            "hinge": 0.0,
            "slide": 0.0,
        }
        tracking_error_counts = {key: 0 for key in tracking_error_sums}
        max_penetration_m = 0.0
        joint_limit_violation_count = 0
        nonfinite_state_count = 0
        simulated_step_count = 0
        for segment_index in range(segment_count):
            qpos_sequence = qpos_segments[segment_index]
            qvel_sequence = qvel_segments[segment_index]
            control_sequence = control_segments[segment_index]
            time_sequence = time_segments[segment_index]
            mujoco.mj_resetData(model, data)
            data.qpos[:] = qpos_sequence[0]
            data.qvel[:] = qvel_sequence[0]
            data.time = float(time_sequence[0])
            mujoco.mj_forward(model, data)
            for frame_index in range(frames_per_segment - 1):
                data.ctrl[:] = control_sequence[frame_index]
                target_time = float(time_sequence[frame_index + 1])
                while data.time + (float(model.opt.timestep) * 0.5) < target_time:
                    mujoco.mj_step(model, data)
                    simulated_step_count += 1
                self._accumulate_semantic_tracking_error(
                    model,
                    data.qpos,
                    qpos_sequence[frame_index + 1],
                    tracking_error_sums,
                    tracking_error_counts,
                    np,
                )
                if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                    nonfinite_state_count += 1
                for contact_index in range(data.ncon):
                    max_penetration_m = max(
                        max_penetration_m,
                        max(0.0, -float(data.contact[contact_index].dist)),
                    )
                joint_limit_violation_count += self._joint_limit_violations(model, data)

        return DoAsIDoReplayResult(
            adapter_id=self.adapter_id,
            scene_sha256=sha256(scene_xml.read_bytes()).hexdigest(),
            trajectory_sha256=sha256(trajectory_npz.read_bytes()).hexdigest(),
            trajectory_frame_count=frame_count,
            trajectory_segment_count=segment_count,
            simulated_step_count=simulated_step_count,
            model_nq=int(model.nq),
            model_nv=int(model.nv),
            model_nu=int(model.nu),
            trajectory_dt_median_s=float(np.median(time_steps)),
            model_timestep_s=float(model.opt.timestep),
            free_joint_translation_rmse_m=self._rmse(
                tracking_error_sums, tracking_error_counts, "free_translation", np
            ),
            orientation_rmse_rad=self._rmse(
                tracking_error_sums, tracking_error_counts, "orientation", np
            ),
            hinge_joint_rmse_rad=self._rmse(
                tracking_error_sums, tracking_error_counts, "hinge", np
            ),
            slide_joint_rmse_m=self._rmse(
                tracking_error_sums, tracking_error_counts, "slide", np
            ),
            max_penetration_m=max_penetration_m,
            joint_limit_violation_count=joint_limit_violation_count,
            nonfinite_state_count=nonfinite_state_count,
        )

    @staticmethod
    def _rmse(sums: dict[str, float], counts: dict[str, int], key: str, np: Any) -> float:
        count = counts[key]
        return 0.0 if count == 0 else float(np.sqrt(sums[key] / count))

    @staticmethod
    def _accumulate_semantic_tracking_error(
        model: Any,
        actual: Any,
        expected: Any,
        sums: dict[str, float],
        counts: dict[str, int],
        np: Any,
    ) -> None:
        for joint_index in range(model.njnt):
            joint_type = int(model.jnt_type[joint_index])
            address = int(model.jnt_qposadr[joint_index])
            if joint_type == 0:  # free joint: xyz + quaternion wxyz
                translation_error = actual[address : address + 3] - expected[address : address + 3]
                sums["free_translation"] += float(np.dot(translation_error, translation_error))
                counts["free_translation"] += 1
                angle = DoAsIDoReplayEvaluator._quaternion_angle(
                    actual[address + 3 : address + 7],
                    expected[address + 3 : address + 7],
                    np,
                )
                sums["orientation"] += angle * angle
                counts["orientation"] += 1
            elif joint_type == 1:  # ball joint quaternion wxyz
                angle = DoAsIDoReplayEvaluator._quaternion_angle(
                    actual[address : address + 4], expected[address : address + 4], np
                )
                sums["orientation"] += angle * angle
                counts["orientation"] += 1
            elif joint_type == 2:  # slide
                error = float(actual[address] - expected[address])
                sums["slide"] += error * error
                counts["slide"] += 1
            elif joint_type == 3:  # hinge
                error = float(actual[address] - expected[address])
                sums["hinge"] += error * error
                counts["hinge"] += 1

    @staticmethod
    def _quaternion_angle(actual: Any, expected: Any, np: Any) -> float:
        actual_norm = float(np.linalg.norm(actual))
        expected_norm = float(np.linalg.norm(expected))
        if actual_norm <= 1e-12 or expected_norm <= 1e-12:
            return float(np.pi)
        dot = abs(float(np.dot(actual / actual_norm, expected / expected_norm)))
        return float(2.0 * np.arccos(np.clip(dot, 0.0, 1.0)))

    @staticmethod
    def _joint_limit_violations(model: Any, data: Any) -> int:
        violations = 0
        for joint_index in range(model.njnt):
            if not model.jnt_limited[joint_index]:
                continue
            joint_type = int(model.jnt_type[joint_index])
            if joint_type not in {2, 3}:  # slide or hinge
                continue
            position = float(data.qpos[int(model.jnt_qposadr[joint_index])])
            lower, upper = model.jnt_range[joint_index]
            if position < float(lower) - 1e-6 or position > float(upper) + 1e-6:
                violations += 1
        return violations
