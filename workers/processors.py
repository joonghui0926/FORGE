from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import tarfile

from forge.adapters.papers.do_as_i_do_replay import DoAsIDoReplayEvaluator
from forge.adapters.papers.gmr_headless import GMRHeadlessRunner
from forge.adapters.papers.runners import DoAsIDoAdapter, PipelineExecution, VideoManipAdapter
from forge.adapters.papers.twist_replay import TWISTG1ReplayEvaluator
from forge.contracts.models import GPUJobRequest, canonical_json
from forge.integrations.runpod.handler import ProcessorOutput


class PaperPipelineProcessor:
    """Runs a pinned paper adapter and returns an auditable output archive."""

    def process(
        self, inputs: dict[str, bytes], config: bytes, request: GPUJobRequest
    ) -> tuple[ProcessorOutput, ...]:
        document = json.loads(config.decode("utf-8"))
        adapter_id = document.get("adapter_id")
        with TemporaryDirectory(prefix=f"forge-{request.job_id}-") as directory:
            workspace = Path(directory)
            if adapter_id == DoAsIDoReplayEvaluator.adapter_id:
                return self._run_do_as_i_do_replay(document, inputs, workspace, request)
            if adapter_id == GMRHeadlessRunner.adapter_id:
                return self._run_gmr_headless(document, inputs, workspace, request)
            if adapter_id == TWISTG1ReplayEvaluator.adapter_id:
                return self._run_twist_replay(document, inputs, workspace, request)
            if adapter_id == VideoManipAdapter.adapter_id:
                execution = self._run_videomanip(document, inputs, workspace)
            elif adapter_id == DoAsIDoAdapter.adapter_id:
                execution = self._run_do_as_i_do(document, inputs, workspace)
            else:
                raise ValueError("PAPER_ADAPTER_UNSUPPORTED")
            if not execution.succeeded:
                missing = ",".join(str(path) for path in execution.missing_outputs)
                raise RuntimeError(
                    f"PAPER_PIPELINE_FAILED:{execution.adapter_id}:"
                    f"rc={execution.return_code}:missing={missing}"
                )
            report = (canonical_json(self._report(execution, request)) + "\n").encode("utf-8")
            archive = self._archive(execution)
            return (
                ProcessorOutput(
                    kind="paper_adapter_execution",
                    filename="paper_adapter_execution.json",
                    data=report,
                ),
                ProcessorOutput(
                    kind="paper_adapter_outputs",
                    filename="paper_adapter_outputs.tar.gz",
                    data=archive,
                    media_type="application/gzip",
                ),
            )

    def _run_gmr_headless(
        self,
        document: dict[str, object],
        inputs: dict[str, bytes],
        workspace: Path,
        request: GPUJobRequest,
    ) -> tuple[ProcessorOutput, ...]:
        extension = str(document.get("source_extension", ".bvh")).lower()
        if extension != ".bvh":
            raise ValueError("GMR_SOURCE_EXTENSION_UNSUPPORTED")
        input_dir = workspace / "input"
        output_dir = workspace / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        source_path = input_dir / "source.bvh"
        output_path = output_dir / "gmr_trajectory.npz"
        source_path.write_bytes(self._select_input(document, inputs))

        offsets_path = None
        offsets_kind = document.get("offsets_input_kind")
        if offsets_kind is not None:
            offsets_path = input_dir / "offsets.json"
            try:
                offsets_path.write_bytes(inputs[str(offsets_kind)])
            except KeyError as error:
                raise ValueError(f"PAPER_ADAPTER_INPUT_KIND_MISSING:{offsets_kind}") from error

        checkout = Path(os.environ.get("GMR_CHECKOUT", "/opt/vendor/GMR"))
        start_frame = document.get("start_frame")
        end_frame = document.get("end_frame")
        result = GMRHeadlessRunner().retarget_xsens_bvh(
            checkout=checkout,
            bvh_file=source_path,
            output_file=output_path,
            robot_id=str(document.get("robot_id", "unitree_g1")),
            start_frame=None if start_frame is None else int(start_frame),
            end_frame=None if end_frame is None else int(end_frame),
            scale=float(document.get("scale", 0.01)),
            reset_to_zero=bool(document.get("reset_to_zero", False)),
            offsets_file=offsets_path,
        )
        report = result.to_dict()
        report["job_id"] = request.job_id
        report["output_path"] = "gmr_trajectory.npz"
        encoded_report = (canonical_json(report) + "\n").encode("utf-8")
        return (
            ProcessorOutput(
                kind="retarget_candidate_report",
                filename="gmr_retarget_report.json",
                data=encoded_report,
            ),
            ProcessorOutput(
                kind="robot_trajectory_candidate",
                filename="gmr_trajectory.npz",
                data=output_path.read_bytes(),
                media_type="application/octet-stream",
            ),
        )

    def _run_do_as_i_do_replay(
        self,
        document: dict[str, object],
        inputs: dict[str, bytes],
        workspace: Path,
        request: GPUJobRequest,
    ) -> tuple[ProcessorOutput, ...]:
        replay_root = workspace / "replay"
        replay_root.mkdir()
        self._extract_tar_safely(self._select_input(document, inputs), replay_root)
        scene_path = self._safe_relative_path(
            replay_root, str(document.get("scene_path", "scene.xml"))
        )
        trajectory_path = self._safe_relative_path(
            replay_root,
            str(document.get("trajectory_path", "trajectory_mjwp.npz")),
        )
        result = DoAsIDoReplayEvaluator().evaluate(scene_path, trajectory_path)
        report = result.to_dict()
        report["job_id"] = request.job_id
        return (
            ProcessorOutput(
                kind="physics_replay_diagnostic",
                filename="do_as_i_do_replay.json",
                data=(canonical_json(report) + "\n").encode("utf-8"),
            ),
        )

    def _run_twist_replay(
        self,
        document: dict[str, object],
        inputs: dict[str, bytes],
        workspace: Path,
        request: GPUJobRequest,
    ) -> tuple[ProcessorOutput, ...]:
        replay_root = workspace / "twist_replay"
        replay_root.mkdir()
        trajectory_path = replay_root / "gmr_trajectory.npz"
        action_path = replay_root / "twist_g1_action.npz"
        trajectory_path.write_bytes(self._select_input(document, inputs))
        model_path = Path(
            os.environ.get(
                "TWIST_G1_MODEL",
                "/opt/vendor/TWIST/assets/g1/g1_sim2sim_with_wrist_roll.xml",
            )
        )
        policy_path = Path(
            os.environ.get(
                "TWIST_G1_POLICY",
                "/opt/vendor/TWIST/assets/twist_general_motion_tracker.pt",
            )
        )
        result = TWISTG1ReplayEvaluator().evaluate(
            trajectory_path,
            model_path,
            policy_path,
            action_path,
            source_start_frame=int(document["source_start_frame"]),
            source_end_frame_exclusive=int(document["source_end_frame_exclusive"]),
            twist_revision=str(document["twist_revision"]),
            device=str(document.get("device", "cuda")),
        )
        report = result.to_dict()
        report["job_id"] = request.job_id
        state = "accepted" if result.robot_ready_accepted else "rejected"
        return (
            ProcessorOutput(
                kind=f"robot_replay_{state}",
                filename="twist_g1_replay.json",
                data=(canonical_json(report) + "\n").encode("utf-8"),
            ),
            ProcessorOutput(
                kind=f"robot_action_{state}",
                filename="twist_g1_action.npz",
                data=action_path.read_bytes(),
                media_type="application/octet-stream",
            ),
        )

    @staticmethod
    def _select_input(document: dict[str, object], inputs: dict[str, bytes]) -> bytes:
        input_kind = str(document.get("input_kind", "source"))
        try:
            return inputs[input_kind]
        except KeyError as error:
            raise ValueError(f"PAPER_ADAPTER_INPUT_KIND_MISSING:{input_kind}") from error

    def _run_videomanip(
        self, document: dict[str, object], inputs: dict[str, bytes], workspace: Path
    ) -> PipelineExecution:
        object_id = str(document["object_id"])
        extension = str(document.get("source_extension", ".mp4"))
        if extension not in {".mp4", ".mov", ".avi"}:
            raise ValueError("VIDEOMANIP_SOURCE_EXTENSION_UNSUPPORTED")
        video_dir = workspace / "video"
        data_root = workspace / "data"
        video_dir.mkdir()
        (video_dir / f"{object_id}{extension}").write_bytes(self._select_input(document, inputs))
        checkout = Path(os.environ.get("VIDEOMANIP_CHECKOUT", "/opt/vendor/VideoManip"))
        return VideoManipAdapter().run(
            checkout=checkout,
            object_id=object_id,
            stages=tuple(str(stage) for stage in document["stages"]),  # type: ignore[union-attr]
            data_root=data_root,
            video_dir=video_dir,
            timeout_s=int(document.get("timeout_s", 7200)),
        )

    def _run_do_as_i_do(
        self, document: dict[str, object], inputs: dict[str, bytes], workspace: Path
    ) -> PipelineExecution:
        reconstruction_dir = workspace / "reconstruction"
        reconstruction_dir.mkdir()
        self._extract_tar_safely(self._select_input(document, inputs), reconstruction_dir)
        checkout = Path(os.environ.get("DO_AS_I_DO_CHECKOUT", "/opt/vendor/do-as-i-do"))
        return DoAsIDoAdapter().run(
            checkout=checkout,
            task_id=str(document["task_id"]),
            reconstruction_dir=reconstruction_dir,
            output_root=workspace / "output",
            timeout_s=int(document.get("timeout_s", 14_400)),
        )

    @staticmethod
    def _extract_tar_safely(data: bytes, target: Path) -> None:
        target_resolved = target.resolve()
        with tarfile.open(fileobj=BytesIO(data), mode="r:*") as archive:
            members = archive.getmembers()
            for member in members:
                destination = (target / member.name).resolve()
                if target_resolved not in destination.parents and destination != target_resolved:
                    raise ValueError("ARCHIVE_PATH_TRAVERSAL")
                if member.issym() or member.islnk():
                    raise ValueError("ARCHIVE_LINKS_FORBIDDEN")
            archive.extractall(target, members=members, filter="data")

    @staticmethod
    def _safe_relative_path(root: Path, relative: str) -> Path:
        candidate = (root / relative).resolve()
        resolved_root = root.resolve()
        if candidate != resolved_root and resolved_root not in candidate.parents:
            raise ValueError("REPLAY_PATH_TRAVERSAL")
        return candidate

    @staticmethod
    def _report(execution: PipelineExecution, request: GPUJobRequest) -> dict[str, object]:
        return {
            "schema_version": "forge.paper-adapter-execution.v1",
            "job_id": request.job_id,
            "adapter_id": execution.adapter_id,
            "command": list(execution.command),
            "return_code": execution.return_code,
            "duration_s": execution.duration_s,
            "expected_outputs": [str(path) for path in execution.expected_outputs],
            "simulation": execution.simulation,
            "stdout_tail": execution.stdout[-4000:],
            "stderr_tail": execution.stderr[-4000:],
        }

    @staticmethod
    def _archive(execution: PipelineExecution) -> bytes:
        buffer = BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for output in execution.expected_outputs:
                archive.add(output, arcname=output.name, recursive=True)
        return buffer.getvalue()
