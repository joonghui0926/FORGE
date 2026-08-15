from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GMRKinematicDiagnostic:
    adapter_id: str
    trajectory_sha256: str
    model_sha256: str
    robot_id: str
    frame_count: int
    fps: int
    nonfinite_state_count: int
    joint_limit_violation_count: int
    self_collision_frame_count: int
    max_penetration_m: float
    foot_slip_p95_m_s: float
    simulation: bool = False
    acceptance_state: str = "kinematic_diagnostic_requires_dynamic_replay"
    schema_version: str = "forge.gmr-kinematic-diagnostic.v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GMRKinematicEvaluator:
    """Checks GMR qpos against its target MuJoCo model; this is not a dynamic replay."""

    adapter_id = "gmr-kinematic-diagnostic-v1"

    def evaluate(
        self, model_xml: Path, trajectory_npz: Path, robot_id: str
    ) -> GMRKinematicDiagnostic:
        if not model_xml.is_file():
            raise FileNotFoundError(model_xml)
        if not trajectory_npz.is_file():
            raise FileNotFoundError(trajectory_npz)
        try:
            import mujoco
            import numpy as np
        except ImportError as error:
            raise RuntimeError("GMR_VALIDATION_DEPENDENCY_MISSING") from error

        with np.load(trajectory_npz, allow_pickle=False) as archive:
            if "qpos" not in archive.files or "fps" not in archive.files:
                raise ValueError("GMR_VALIDATION_ARRAY_MISSING")
            qpos = np.asarray(archive["qpos"], dtype=np.float64)
            fps = int(np.asarray(archive["fps"]).item())
        if qpos.ndim != 2 or qpos.shape[0] < 2 or fps < 1:
            raise ValueError("GMR_VALIDATION_TRAJECTORY_INVALID")

        model = mujoco.MjModel.from_xml_path(str(model_xml.resolve()))
        if qpos.shape[1] != model.nq:
            raise ValueError("GMR_VALIDATION_QPOS_DIMENSION_MISMATCH")
        data = mujoco.MjData(model)
        nonfinite_state_count = 0
        joint_limit_violation_count = 0
        self_collision_frame_count = 0
        max_penetration_m = 0.0
        foot_body_ids = self._foot_body_ids(model, mujoco)
        foot_positions: dict[int, list[Any]] = {body_id: [] for body_id in foot_body_ids}

        for frame in qpos:
            if not np.isfinite(frame).all():
                nonfinite_state_count += 1
                continue
            data.qpos[:] = frame
            mujoco.mj_forward(model, data)
            joint_limit_violation_count += self._joint_limit_violations(model, data)
            has_self_collision = False
            for contact_index in range(data.ncon):
                contact = data.contact[contact_index]
                max_penetration_m = max(max_penetration_m, max(0.0, -float(contact.dist)))
                body_a = int(model.geom_bodyid[int(contact.geom1)])
                body_b = int(model.geom_bodyid[int(contact.geom2)])
                if body_a > 0 and body_b > 0 and body_a != body_b:
                    has_self_collision = True
            if has_self_collision:
                self_collision_frame_count += 1
            for body_id in foot_body_ids:
                foot_positions[body_id].append(np.copy(data.xpos[body_id]))

        slip_speeds: list[float] = []
        for positions in foot_positions.values():
            if len(positions) < 2:
                continue
            points = np.asarray(positions)
            contact_height = float(np.min(points[:, 2]) + 0.015)
            horizontal_speeds = np.linalg.norm(np.diff(points[:, :2], axis=0), axis=1) * fps
            support = (points[:-1, 2] <= contact_height) & (points[1:, 2] <= contact_height)
            slip_speeds.extend(float(value) for value in horizontal_speeds[support])
        slip_p95 = 0.0 if not slip_speeds else float(np.percentile(slip_speeds, 95))
        return GMRKinematicDiagnostic(
            adapter_id=self.adapter_id,
            trajectory_sha256=sha256(trajectory_npz.read_bytes()).hexdigest(),
            model_sha256=sha256(model_xml.read_bytes()).hexdigest(),
            robot_id=robot_id,
            frame_count=int(qpos.shape[0]),
            fps=fps,
            nonfinite_state_count=nonfinite_state_count,
            joint_limit_violation_count=joint_limit_violation_count,
            self_collision_frame_count=self_collision_frame_count,
            max_penetration_m=max_penetration_m,
            foot_slip_p95_m_s=slip_p95,
        )

    @staticmethod
    def _foot_body_ids(model: Any, mujoco: Any) -> tuple[int, ...]:
        names = ("left_ankle_roll_link", "right_ankle_roll_link")
        ids = tuple(
            int(mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)) for name in names
        )
        if any(body_id < 0 for body_id in ids):
            raise ValueError("GMR_VALIDATION_FOOT_BODY_MISSING")
        return ids

    @staticmethod
    def _joint_limit_violations(model: Any, data: Any) -> int:
        violations = 0
        for joint_index in range(model.njnt):
            if not model.jnt_limited[joint_index]:
                continue
            joint_type = int(model.jnt_type[joint_index])
            if joint_type not in {2, 3}:
                continue
            value = float(data.qpos[int(model.jnt_qposadr[joint_index])])
            lower, upper = model.jnt_range[joint_index]
            if value < float(lower) - 1e-6 or value > float(upper) + 1e-6:
                violations += 1
        return violations
