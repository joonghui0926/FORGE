from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess, run
from time import perf_counter
import os


@dataclass(frozen=True)
class PipelineExecution:
    adapter_id: str
    command: tuple[str, ...]
    return_code: int
    duration_s: float
    stdout: str
    stderr: str
    expected_outputs: tuple[Path, ...]
    missing_outputs: tuple[Path, ...]
    simulation: bool

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0 and not self.missing_outputs and not self.simulation


class _ExternalAdapter:
    adapter_id: str
    revision: str

    def _assert_checkout(self, checkout: Path) -> None:
        if not checkout.resolve().is_dir():
            raise FileNotFoundError(checkout)
        completed = run(
            ["git", "rev-parse", "HEAD"],
            cwd=checkout,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0 or completed.stdout.strip() != self.revision:
            raise RuntimeError(f"PAPER_ADAPTER_REVISION_MISMATCH:{self.adapter_id}")

    def _execute(
        self,
        command: tuple[str, ...],
        checkout: Path,
        expected_outputs: tuple[Path, ...],
        timeout_s: int,
        environment: dict[str, str] | None = None,
        simulation: bool = False,
        expected_globs: tuple[str, ...] = (),
    ) -> PipelineExecution:
        if simulation:
            return PipelineExecution(
                adapter_id=self.adapter_id,
                command=command,
                return_code=0,
                duration_s=0.0,
                stdout="SIMULATED: command not executed",
                stderr="",
                expected_outputs=expected_outputs,
                missing_outputs=expected_outputs,
                simulation=True,
            )
        self._assert_checkout(checkout)
        safe_environment = {
            key: value
            for key, value in os.environ.items()
            if key
            in {
                "PATH",
                "PYTHONPATH",
                "CUDA_VISIBLE_DEVICES",
                "HF_HOME",
                "HF_TOKEN",
                "MANO_MODEL_DIR",
                "MESHY_API_KEY",
                "OPENAI_API_KEY",
            }
        }
        safe_environment.update(environment or {})
        started = perf_counter()
        completed: CompletedProcess[str] = run(
            list(command),
            cwd=checkout,
            env=safe_environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
        duration = perf_counter() - started
        resolved_outputs = list(expected_outputs)
        missing = [path for path in expected_outputs if not path.exists()]
        for pattern in expected_globs:
            matches = tuple(checkout.glob(pattern))
            if matches:
                resolved_outputs.extend(matches)
            else:
                missing.append(checkout / pattern)
        return PipelineExecution(
            adapter_id=self.adapter_id,
            command=command,
            return_code=completed.returncode,
            duration_s=duration,
            stdout=completed.stdout,
            stderr=completed.stderr,
            expected_outputs=tuple(dict.fromkeys(resolved_outputs)),
            missing_outputs=tuple(missing),
            simulation=False,
        )


class VideoManipAdapter(_ExternalAdapter):
    adapter_id = "videomanip-reconstruction-v1"
    revision = "9d0f286af35d73f4252d115d968e0a9c06542b9c"
    allowed_stages = {
        "frames",
        "clicks",
        "intrinsics",
        "hand_mesh",
        "masks",
        "obj_mesh",
        "obj_pose",
        "retarget",
    }

    def run(
        self,
        checkout: Path,
        object_id: str,
        stages: tuple[str, ...],
        data_root: Path,
        video_dir: Path,
        timeout_s: int = 7200,
        simulation: bool = False,
    ) -> PipelineExecution:
        if not object_id.replace("_", "").replace("-", "").isalnum():
            raise ValueError("object_id must be filesystem-safe")
        if not stages or set(stages) - self.allowed_stages:
            raise ValueError("unsupported VideoManip stage")
        if "clicks" in stages and os.getenv("DISPLAY") is None:
            raise RuntimeError("VIDEOMANIP_INTERACTIVE_CLICKS_REQUIRE_DISPLAY_OR_PRECOMPUTED_INPUT")
        reconstruction = checkout / "reconstruction"
        expected_by_stage = {
            "frames": data_root / object_id / "rgb",
            "intrinsics": data_root / object_id / "cam_K.txt",
            "hand_mesh": data_root / object_id / "human_hand",
            "masks": data_root / object_id / "masks_pred_obj",
            "obj_mesh": data_root / object_id / "mesh_original",
            "obj_pose": data_root / object_id / "obj_mesh",
            "retarget": data_root / object_id / "robot_qpos",
        }
        expected = tuple(expected_by_stage[stage] for stage in stages if stage in expected_by_stage)
        command = (
            "bash",
            "process_videos.sh",
            "--stages",
            ",".join(stages),
            object_id,
        )
        return self._execute(
            command,
            reconstruction,
            expected,
            timeout_s,
            {"DATA_ROOT": str(data_root), "VIDEO_DIR": str(video_dir)},
            simulation,
        )


class DoAsIDoAdapter(_ExternalAdapter):
    adapter_id = "do-as-i-do-heavy-retarget-v1"
    revision = "824591b808c342b20079c3b4198a8c2bdf88c74e"

    def run(
        self,
        checkout: Path,
        task_id: str,
        reconstruction_dir: Path,
        output_root: Path,
        timeout_s: int = 14_400,
        simulation: bool = False,
    ) -> PipelineExecution:
        if not task_id.replace("_", "").replace("-", "").isalnum():
            raise ValueError("task_id must be filesystem-safe")
        retargeting = checkout / "retargeting"
        command = (
            "python",
            "launch.py",
            "--task",
            task_id,
            "--raw-dir",
            str(reconstruction_dir),
            "--output-root-dir",
            str(output_root),
            "--no-show-viewer",
            "--no-wait-on-finish",
        )
        execution = self._execute(
            command, retargeting, (), timeout_s, simulation=simulation
        )
        return PipelineExecution(**self._validate_absolute_do_as_i_do_output(execution, output_root))

    @staticmethod
    def _validate_absolute_do_as_i_do_output(
        execution: PipelineExecution, output_root: Path
    ) -> dict[str, object]:
        patterns = (
            "sharpa/*/*/0/scene.xml",
            "sharpa/*/*/0/trajectory_mjwp*.npz",
            "sharpa/*/*/0/config.yaml",
        )
        outputs: list[Path] = []
        missing: list[Path] = list(execution.missing_outputs)
        for pattern in patterns:
            matches = tuple(output_root.glob(pattern))
            if matches:
                outputs.extend(matches)
            else:
                missing.append(output_root / pattern)
        return {
            "adapter_id": execution.adapter_id,
            "command": execution.command,
            "return_code": execution.return_code,
            "duration_s": execution.duration_s,
            "stdout": execution.stdout,
            "stderr": execution.stderr,
            "expected_outputs": tuple(outputs),
            "missing_outputs": tuple(missing),
            "simulation": execution.simulation,
        }


class GMRAdapter(_ExternalAdapter):
    adapter_id = "gmr-whole-body-retarget-v1"
    revision = "bb1bbe40774794fceb2a7c579a3464a28e68c844"

    def build_command(
        self, robot: str, human_motion_file: Path, output_file: Path
    ) -> tuple[str, ...]:
        if not robot.replace("_", "").replace("-", "").isalnum():
            raise ValueError("robot identifier must be safe")
        return (
            "python",
            "scripts/smplx_to_robot.py",
            "--smplx_file",
            str(human_motion_file),
            "--robot",
            robot,
            "--save_path",
            str(output_file),
        )

    def assert_checkout(self, checkout: Path) -> None:
        self._assert_checkout(checkout)
