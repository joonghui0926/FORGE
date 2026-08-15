from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TWISTReplayDiagnostic:
    adapter_id: str
    robot_id: str
    acceptance_scope: str
    source_trajectory_sha256: str
    target_model_sha256: str
    policy_sha256: str
    action_artifact_sha256: str
    gmr_revision: str
    twist_revision: str
    source_start_frame: int
    source_end_frame_exclusive: int
    source_fps: int
    control_hz: int
    target_frame_count: int
    simulated_step_count: int
    policy_device: str
    reference_joint_margin_adjustment_count: int
    nonfinite_frame_count: int
    joint_limit_violation_count: int
    self_collision_frame_count: int
    fall_frame_count: int
    joint_position_rmse_rad: float
    root_height_rmse_m: float
    root_roll_pitch_rmse_rad: float
    root_local_velocity_rmse_m_s: float
    max_penetration_m: float
    max_self_collision_penetration_m: float
    torque_saturation_fraction: float
    robot_ready_accepted: bool
    rejection_reasons: tuple[str, ...]
    simulation: bool = True
    schema_version: str = "forge.twist-g1-replay.v1"

    @property
    def acceptance_state(self) -> str:
        if self.robot_ready_accepted:
            return "robot_ready_for_unitree_g1_sim2sim"
        return "candidate_rejected_by_unitree_g1_sim2sim"

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "acceptance_state": self.acceptance_state}


class TWISTG1ReplayEvaluator:
    """Run the pinned TWIST tracker against a GMR trajectory in headless MuJoCo."""

    adapter_id = "twist-g1-closed-loop-replay-v1"
    robot_id = "unitree_g1_25dof"
    acceptance_scope = "unitree_g1_25dof_sim2sim"
    _wrist_indices = (19, 24)
    _gmr_dof_indices = tuple(range(20)) + tuple(range(22, 27))

    def evaluate(
        self,
        source_trajectory: Path,
        target_model: Path,
        policy_path: Path,
        output_npz: Path,
        *,
        source_start_frame: int,
        source_end_frame_exclusive: int,
        twist_revision: str,
        device: str = "cuda",
        control_hz: int = 50,
        warmup_s: float = 1.0,
        transition_s: float = 2.0,
    ) -> TWISTReplayDiagnostic:
        for path in (source_trajectory, target_model, policy_path):
            if path.is_symlink() or not path.is_file():
                raise FileNotFoundError(path)
        if control_hz < 1 or warmup_s < 0 or transition_s <= 0:
            raise ValueError("TWIST_REPLAY_CONFIG_INVALID")
        try:
            import mujoco
            import numpy as np
            import torch
        except ImportError as error:
            raise RuntimeError("TWIST_REPLAY_DEPENDENCY_MISSING") from error
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("TWIST_REPLAY_CUDA_UNAVAILABLE")

        with np.load(source_trajectory, allow_pickle=False) as archive:
            required = {"qpos", "fps", "robot_id", "gmr_revision"}
            if not required.issubset(archive.files):
                raise ValueError("TWIST_REPLAY_SOURCE_ARRAY_MISSING")
            source_qpos = np.asarray(archive["qpos"], dtype=np.float64)
            source_fps = int(np.asarray(archive["fps"]).item())
            source_robot = str(np.asarray(archive["robot_id"]).item())
            gmr_revision = str(np.asarray(archive["gmr_revision"]).item())
        if source_robot != "unitree_g1" or source_qpos.ndim != 2 or source_qpos.shape[1] != 36:
            raise ValueError("TWIST_REPLAY_SOURCE_ROBOT_UNSUPPORTED")
        if not 0 <= source_start_frame < source_end_frame_exclusive <= len(source_qpos):
            raise ValueError("TWIST_REPLAY_SOURCE_RANGE_INVALID")
        source_qpos = source_qpos[source_start_frame:source_end_frame_exclusive]
        if not np.isfinite(source_qpos).all():
            raise ValueError("TWIST_REPLAY_SOURCE_NONFINITE")

        model = mujoco.MjModel.from_xml_path(str(target_model.resolve()))
        if (model.nq, model.nv, model.nu) != (32, 31, 25):
            raise ValueError("TWIST_REPLAY_TARGET_MODEL_DIMENSION_MISMATCH")
        simulation_hz = 1_000
        model.opt.timestep = 1.0 / simulation_hz
        if simulation_hz % control_hz:
            raise ValueError("TWIST_REPLAY_CONTROL_RATE_NOT_DIVISIBLE")
        decimation = simulation_hz // control_hz

        target = self._resample_source(source_qpos, source_fps, control_hz, np)
        target, reference_joint_margin_adjustment_count = self._apply_joint_margin(
            target, model, np
        )
        default_dof = np.asarray(
            [
                -0.2, 0.0, 0.0, 0.4, -0.2, 0.0,
                -0.2, 0.0, 0.0, 0.4, -0.2, 0.0,
                0.0, 0.0, 0.0,
                0.0, 0.2, 0.0, 1.2, 0.0,
                0.0, -0.2, 0.0, 1.2, 0.0,
            ],
            dtype=np.float64,
        )
        stiffness = np.asarray(
            [
                100, 100, 100, 150, 40, 40,
                100, 100, 100, 150, 40, 40,
                150, 150, 150,
                40, 40, 40, 40, 20,
                40, 40, 40, 40, 20,
            ],
            dtype=np.float64,
        )
        damping = np.asarray(
            [
                2, 2, 2, 4, 2, 2,
                2, 2, 2, 4, 2, 2,
                4, 4, 4,
                5, 5, 5, 5, 1,
                5, 5, 5, 5, 1,
            ],
            dtype=np.float64,
        )
        torque_limits = np.asarray(
            [
                88, 139, 88, 139, 50, 50,
                88, 139, 88, 139, 50, 50,
                88, 50, 50,
                25, 25, 25, 25, 25,
                25, 25, 25, 25, 25,
            ],
            dtype=np.float64,
        )
        policy = torch.jit.load(str(policy_path.resolve()), map_location=device)
        policy.eval()
        data = mujoco.MjData(model)
        data.qpos[:] = np.concatenate(
            (np.asarray([0.0, 0.0, 0.793, 0.0, 0.0, 0.0, 1.0]), default_dof)
        )
        mujoco.mj_forward(model, data)

        history = np.zeros((10, 105), dtype=np.float32)
        last_action = np.zeros(23, dtype=np.float32)
        action_rows: list[Any] = []
        pd_target_rows: list[Any] = []
        rollout_qpos: list[Any] = []
        rollout_qvel: list[Any] = []
        joint_squared_errors: list[float] = []
        height_squared_errors: list[float] = []
        roll_pitch_squared_errors: list[float] = []
        velocity_squared_errors: list[float] = []
        saturation: list[float] = []
        nonfinite_frame_count = 0
        joint_limit_violation_count = 0
        self_collision_frame_count = 0
        fall_frame_count = 0
        max_penetration_m = 0.0
        max_self_collision_penetration_m = 0.0
        warmup_frames = round(warmup_s * control_hz)
        transition_frames = round(transition_s * control_hz)
        default_mimic = np.concatenate(
            (np.asarray([0.793]), np.zeros(7), default_dof)
        )
        schedule: list[tuple[Any, int | None]] = []
        schedule.extend((default_mimic, None) for _ in range(warmup_frames))
        for frame_index in range(transition_frames):
            alpha = (frame_index + 1) / transition_frames
            schedule.append(((1.0 - alpha) * default_mimic + alpha * target[0], None))
        schedule.extend((row, index) for index, row in enumerate(target))

        for mimic, target_index in schedule:
            current_dof = np.asarray(data.qpos[7:], dtype=np.float32)
            current_velocity = np.asarray(data.qvel[6:], dtype=np.float32)
            current_rpy = self._quat_to_euler(np.asarray(data.qpos[3:7]), np)
            angular_velocity = np.asarray(data.sensor("angular-velocity").data)
            body_dof = np.delete(current_dof, self._wrist_indices)
            body_velocity = np.delete(current_velocity, self._wrist_indices)
            body_velocity[[4, 5, 10, 11]] = 0.0
            proprio = np.concatenate(
                (
                    angular_velocity * 0.25,
                    current_rpy[:2],
                    body_dof - np.delete(default_dof, self._wrist_indices),
                    body_velocity * 0.05,
                    last_action,
                )
            ).astype(np.float32)
            wrist_target = mimic[[27, 32]]
            policy_target = np.delete(mimic, (27, 32)).astype(np.float32)
            current_observation = np.concatenate((policy_target, proprio))
            observation = np.concatenate((current_observation, history.reshape(-1)))
            history[:-1] = history[1:]
            history[-1] = current_observation
            tensor = torch.from_numpy(observation).unsqueeze(0).to(device)
            with torch.inference_mode():
                raw_action = policy(tensor).detach().cpu().numpy().squeeze()
            if raw_action.shape != (23,) or not np.isfinite(raw_action).all():
                nonfinite_frame_count += 1
                raw_action = np.zeros(23, dtype=np.float32)
            last_action = raw_action.astype(np.float32)
            body_pd_target = np.clip(raw_action, -10.0, 10.0) * 0.5
            body_pd_target += np.delete(default_dof, self._wrist_indices)
            pd_target = np.empty(25, dtype=np.float64)
            pd_target[list(self._wrist_indices)] = wrist_target
            pd_target[np.delete(np.arange(25), self._wrist_indices)] = body_pd_target
            pd_target = self._clamp_joint_target(pd_target, model, np)

            for _ in range(decimation):
                torque = (pd_target - data.qpos[7:]) * stiffness - data.qvel[6:] * damping
                torque = self._apply_joint_limit_brake(torque, model, data, np)
                saturation.append(float(np.mean(np.abs(torque) >= torque_limits)))
                data.ctrl[:] = np.clip(torque, -torque_limits, torque_limits)
                mujoco.mj_step(model, data)

            if target_index is None:
                continue
            action_rows.append(last_action.copy())
            pd_target_rows.append(pd_target.copy())
            rollout_qpos.append(data.qpos.copy())
            rollout_qvel.append(data.qvel.copy())
            desired_dof = mimic[8:]
            joint_squared_errors.append(float(np.mean((data.qpos[7:] - desired_dof) ** 2)))
            height_squared_errors.append(float((data.qpos[2] - mimic[0]) ** 2))
            roll_pitch_squared_errors.append(
                float(np.mean((self._quat_to_euler(data.qpos[3:7], np)[:2] - mimic[1:3]) ** 2))
            )
            local_velocity = self._quat_rotate_inverse(
                np.asarray(data.qpos[3:7]), np.asarray(data.qvel[:3]), np
            )
            velocity_squared_errors.append(float(np.mean((local_velocity - mimic[4:7]) ** 2)))
            if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                nonfinite_frame_count += 1
            joint_limit_violation_count += self._joint_limit_violations(model, data)
            has_self_collision = False
            for contact in data.contact:
                penetration = max(0.0, -float(contact.dist))
                max_penetration_m = max(max_penetration_m, penetration)
                body_a = int(model.geom_bodyid[int(contact.geom1)])
                body_b = int(model.geom_bodyid[int(contact.geom2)])
                is_self_collision = body_a > 0 and body_b > 0 and body_a != body_b
                if is_self_collision:
                    max_self_collision_penetration_m = max(
                        max_self_collision_penetration_m, penetration
                    )
                has_self_collision |= is_self_collision and penetration > 0.002
            self_collision_frame_count += int(has_self_collision)
            current_rpy = self._quat_to_euler(np.asarray(data.qpos[3:7]), np)
            fall_frame_count += int(data.qpos[2] < 0.45 or np.max(np.abs(current_rpy[:2])) > 0.8)

        action = np.asarray(action_rows, dtype=np.float32)
        pd_targets = np.asarray(pd_target_rows, dtype=np.float32)
        rollout_positions = np.asarray(rollout_qpos, dtype=np.float32)
        rollout_velocities = np.asarray(rollout_qvel, dtype=np.float32)
        output_npz.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            output_npz,
            timestamp_s=np.arange(len(target), dtype=np.float64) / control_hz,
            target_mimic_observation=target.astype(np.float32),
            policy_action=action,
            pd_target_rad=pd_targets,
            rollout_qpos=rollout_positions,
            rollout_qvel=rollout_velocities,
            stiffness=stiffness.astype(np.float32),
            damping=damping.astype(np.float32),
            torque_limit_nm=torque_limits.astype(np.float32),
        )
        joint_rmse = self._rmse(joint_squared_errors, np)
        height_rmse = self._rmse(height_squared_errors, np)
        roll_pitch_rmse = self._rmse(roll_pitch_squared_errors, np)
        velocity_rmse = self._rmse(velocity_squared_errors, np)
        saturation_fraction = float(np.mean(saturation)) if saturation else 1.0
        rejection_reasons: list[str] = []
        checks = (
            (nonfinite_frame_count == 0, "non-finite replay state"),
            (joint_limit_violation_count == 0, "joint-limit violation"),
            (self_collision_frame_count == 0, "self-collision"),
            (fall_frame_count == 0, "fall detected"),
            (joint_rmse <= 0.25, "joint tracking RMSE above 0.25 rad"),
            (height_rmse <= 0.15, "root-height RMSE above 0.15 m"),
            (roll_pitch_rmse <= 0.30, "root roll/pitch RMSE above 0.30 rad"),
            (velocity_rmse <= 0.50, "root velocity RMSE above 0.50 m/s"),
            (max_penetration_m <= 0.03, "penetration above 0.03 m"),
            (saturation_fraction <= 0.25, "torque saturation above 25%"),
        )
        rejection_reasons.extend(reason for passed, reason in checks if not passed)
        return TWISTReplayDiagnostic(
            adapter_id=self.adapter_id,
            robot_id=self.robot_id,
            acceptance_scope=self.acceptance_scope,
            source_trajectory_sha256=sha256(source_trajectory.read_bytes()).hexdigest(),
            target_model_sha256=sha256(target_model.read_bytes()).hexdigest(),
            policy_sha256=sha256(policy_path.read_bytes()).hexdigest(),
            action_artifact_sha256=sha256(output_npz.read_bytes()).hexdigest(),
            gmr_revision=gmr_revision,
            twist_revision=twist_revision,
            source_start_frame=source_start_frame,
            source_end_frame_exclusive=source_end_frame_exclusive,
            source_fps=source_fps,
            control_hz=control_hz,
            target_frame_count=len(target),
            simulated_step_count=len(schedule) * decimation,
            policy_device=device,
            reference_joint_margin_adjustment_count=reference_joint_margin_adjustment_count,
            nonfinite_frame_count=nonfinite_frame_count,
            joint_limit_violation_count=joint_limit_violation_count,
            self_collision_frame_count=self_collision_frame_count,
            fall_frame_count=fall_frame_count,
            joint_position_rmse_rad=joint_rmse,
            root_height_rmse_m=height_rmse,
            root_roll_pitch_rmse_rad=roll_pitch_rmse,
            root_local_velocity_rmse_m_s=velocity_rmse,
            max_penetration_m=max_penetration_m,
            max_self_collision_penetration_m=max_self_collision_penetration_m,
            torque_saturation_fraction=saturation_fraction,
            robot_ready_accepted=not rejection_reasons,
            rejection_reasons=tuple(rejection_reasons),
        )

    def _resample_source(
        self, qpos: Any, source_fps: int, target_fps: int, np: Any
    ) -> Any:
        duration = (len(qpos) - 1) / source_fps
        target_times = np.arange(int(duration * target_fps) + 1) / target_fps
        source_positions = np.minimum(target_times * source_fps, len(qpos) - 1)
        lower = np.floor(source_positions).astype(np.int64)
        upper = np.minimum(lower + 1, len(qpos) - 1)
        alpha = (source_positions - lower)[:, None]
        root_position = (1.0 - alpha) * qpos[lower, :3] + alpha * qpos[upper, :3]
        quaternion = self._normalized_lerp(qpos[lower, 3:7], qpos[upper, 3:7], alpha, np)
        source_dof = qpos[:, 7:][:, self._gmr_dof_indices]
        dof = (1.0 - alpha) * source_dof[lower] + alpha * source_dof[upper]
        rpy = np.asarray([self._quat_to_euler(value, np) for value in quaternion])
        world_velocity = np.gradient(root_position, 1.0 / target_fps, axis=0)
        local_velocity = np.asarray(
            [
                self._quat_rotate_inverse(quaternion[index], world_velocity[index], np)
                for index in range(len(quaternion))
            ]
        )
        yaw_velocity = np.gradient(np.unwrap(rpy[:, 2]), 1.0 / target_fps)
        return np.concatenate(
            (
                root_position[:, 2:3],
                rpy,
                local_velocity,
                yaw_velocity[:, None],
                dof,
            ),
            axis=1,
        )

    @staticmethod
    def _apply_joint_margin(target: Any, model: Any, np: Any) -> tuple[Any, int]:
        repaired = target.copy()
        adjustment_count = 0
        for target_index, joint_index in enumerate(range(1, model.njnt)):
            if not model.jnt_limited[joint_index]:
                continue
            lower, upper = (float(value) for value in model.jnt_range[joint_index])
            margin = min(0.03, 0.05 * (upper - lower))
            original = repaired[:, 8 + target_index].copy()
            repaired[:, 8 + target_index] = np.clip(
                original, lower + margin, upper - margin
            )
            adjustment_count += int(np.count_nonzero(repaired[:, 8 + target_index] != original))
        return repaired, adjustment_count

    @staticmethod
    def _clamp_joint_target(target: Any, model: Any, np: Any) -> Any:
        clamped = target.copy()
        for target_index, joint_index in enumerate(range(1, model.njnt)):
            if not model.jnt_limited[joint_index]:
                continue
            lower, upper = (float(value) for value in model.jnt_range[joint_index])
            margin = min(0.03, 0.05 * (upper - lower))
            clamped[target_index] = np.clip(
                clamped[target_index], lower + margin, upper - margin
            )
        return clamped

    @staticmethod
    def _apply_joint_limit_brake(torque: Any, model: Any, data: Any, np: Any) -> Any:
        protected = torque.copy()
        for target_index, joint_index in enumerate(range(1, model.njnt)):
            if not model.jnt_limited[joint_index]:
                continue
            lower, upper = (float(value) for value in model.jnt_range[joint_index])
            position = float(data.qpos[7 + target_index])
            velocity = float(data.qvel[6 + target_index])
            brake_zone = min(0.08, 0.1 * (upper - lower))
            if position < lower + brake_zone and velocity < 0:
                protected[target_index] += -8.0 * velocity
            elif position > upper - brake_zone and velocity > 0:
                protected[target_index] += -8.0 * velocity
        return np.asarray(protected)

    @staticmethod
    def _normalized_lerp(first: Any, second: Any, alpha: Any, np: Any) -> Any:
        aligned = second.copy()
        aligned[np.sum(first * aligned, axis=1) < 0] *= -1
        values = (1.0 - alpha) * first + alpha * aligned
        return values / np.linalg.norm(values, axis=1, keepdims=True)

    @staticmethod
    def _quat_to_euler(quaternion: Any, np: Any) -> Any:
        w, x, y, z = quaternion
        roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
        pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1.0, 1.0))
        yaw = np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
        return np.asarray([roll, pitch, yaw])

    @staticmethod
    def _quat_rotate_inverse(quaternion: Any, vector: Any, np: Any) -> Any:
        w = float(quaternion[0])
        xyz = np.asarray(quaternion[1:])
        return vector * (2 * w * w - 1) - 2 * w * np.cross(xyz, vector) + 2 * xyz * np.dot(xyz, vector)

    @staticmethod
    def _joint_limit_violations(model: Any, data: Any) -> int:
        violations = 0
        for joint_index in range(model.njnt):
            if not model.jnt_limited[joint_index] or int(model.jnt_type[joint_index]) not in {2, 3}:
                continue
            value = float(data.qpos[int(model.jnt_qposadr[joint_index])])
            lower, upper = model.jnt_range[joint_index]
            violations += int(value < float(lower) - 1e-6 or value > float(upper) + 1e-6)
        return violations

    @staticmethod
    def _rmse(mean_squared_values: list[float], np: Any) -> float:
        return 0.0 if not mean_squared_values else float(np.sqrt(np.mean(mean_squared_values)))
