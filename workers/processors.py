from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import os
import subprocess
import tarfile

from forge.adapters.papers.do_as_i_do_replay import DoAsIDoReplayEvaluator
from forge.adapters.papers.gmr_headless import GMRHeadlessRunner
from forge.adapters.papers.runners import DoAsIDoAdapter, PipelineExecution, VideoManipAdapter
from forge.adapters.papers.twist_replay import TWISTG1ReplayEvaluator
from forge.contracts.models import GPUJobRequest, canonical_json
from forge.integrations.runpod.handler import ProcessorOutput, StageResult


class PaperPipelineProcessor:
    """Runs a pinned paper adapter and returns an auditable output archive."""

    def process(
        self, inputs: dict[str, bytes], config: bytes, request: GPUJobRequest
    ) -> tuple[ProcessorOutput, ...] | StageResult:
        document = json.loads(config.decode("utf-8"))
        adapter_id = document.get("adapter_id")
        with TemporaryDirectory(prefix=f"forge-{request.job_id}-") as directory:
            workspace = Path(directory)
            if adapter_id == "forge-video-qc-v1":
                return self._run_forge_video_qc(document, inputs, workspace, request)
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
            frame_counts = self._execution_frame_counts(execution)
            frames_total = frame_counts.get("rgb", 0)
            required_frame_counts = [
                count
                for name, count in frame_counts.items()
                if name
                in {"rgb", "cam_info", "depth", "human_hand", "masks_pred_obj", "robot_qpos"}
            ]
            frames_valid = min(required_frame_counts) if required_frame_counts else 0
            return StageResult(
                outputs=(
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
                ),
                metrics={
                    "frames_total": frames_total,
                    "frames_valid": frames_valid,
                    "trajectory_duration_s": execution.duration_s,
                    "claim_level": "human_video_training",
                    "acceptance_scope": "training_data_not_robot_hardware",
                },
                warnings=(
                    "Video reconstruction output is training data, not a hardware-validated robot action.",
                ),
            )

    def _run_forge_video_qc(
        self,
        document: dict[str, object],
        inputs: dict[str, bytes],
        workspace: Path,
        request: GPUJobRequest,
    ) -> StageResult:
        source_path = workspace / "source.mp4"
        source_path.write_bytes(self._select_input(document, inputs))
        timeout_s = int(document.get("timeout_s", 900))
        probe = subprocess.run(
            (
                "ffprobe",
                "-v",
                "error",
                "-count_frames",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,avg_frame_rate,nb_read_frames,duration",
                "-of",
                "json",
                str(source_path),
            ),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
        if probe.returncode != 0:
            raise ValueError(f"VIDEO_PROBE_FAILED:{probe.stderr[-500:]}")
        payload = json.loads(probe.stdout)
        streams = list(payload.get("streams") or [])
        if len(streams) != 1:
            raise ValueError("VIDEO_PRIMARY_STREAM_MISSING")
        stream = streams[0]
        width = int(stream.get("width", 0))
        height = int(stream.get("height", 0))
        numerator, separator, denominator = str(stream.get("avg_frame_rate", "0/1")).partition("/")
        fps = float(numerator) / float(denominator or 1) if separator else float(numerator)
        frame_count = int(stream.get("nb_read_frames") or 0)
        duration_s = float(stream.get("duration") or (frame_count / fps if fps else 0))
        decode = subprocess.run(
            ("ffmpeg", "-v", "error", "-i", str(source_path), "-f", "null", "-"),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
        reasons: list[str] = []
        if decode.returncode != 0:
            reasons.append("VIDEO_DECODE_FAILED")
        if width < int(document.get("minimum_width_px", 1920)):
            reasons.append("VIDEO_WIDTH_LOW")
        if height < int(document.get("minimum_height_px", 1080)):
            reasons.append("VIDEO_HEIGHT_LOW")
        if fps < float(document.get("minimum_frame_rate_hz", 30)):
            reasons.append("VIDEO_FRAME_RATE_LOW")
        if frame_count < 2 or duration_s <= 0:
            reasons.append("VIDEO_DURATION_INVALID")
        report = {
            "schema_version": "forge.video-qc.v1",
            "job_id": request.job_id,
            "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "width_px": width,
            "height_px": height,
            "frame_rate_hz": fps,
            "frame_count": frame_count,
            "duration_s": duration_s,
            "full_decode_passed": decode.returncode == 0,
            "accepted": not reasons,
            "reason_codes": reasons,
            "claim_level": "human_video_training",
        }
        return StageResult(
            outputs=(
                ProcessorOutput(
                    kind="source_video_qc",
                    filename="source_video_qc.json",
                    data=(canonical_json(report) + "\n").encode("utf-8"),
                ),
            ),
            metrics={
                "frames_total": frame_count,
                "frames_valid": frame_count if not reasons else 0,
                "trajectory_duration_s": duration_s,
                "claim_level": "human_video_training",
                "acceptance_scope": "rights_cleared_source_video_training",
                "width_px": width,
                "height_px": height,
                "frame_rate_hz": fps,
            },
            warnings=tuple(reasons),
            status="succeeded" if not reasons else "quality_insufficient",
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
        return StageResult(
            outputs=(
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
            ),
            metrics={
                "frames_total": result.source_frame_count,
                "frames_valid": result.output_frame_count,
                "trajectory_duration_s": result.output_frame_count / result.fps,
                "replay_success": False,
                "claim_level": "sim_validated_robot_trajectory",
                "acceptance_scope": result.acceptance_state,
            },
            warnings=("GMR output is a candidate until an independent replay stage passes.",),
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
        return StageResult(
            outputs=(
                ProcessorOutput(
                    kind="physics_replay_diagnostic",
                    filename="do_as_i_do_replay.json",
                    data=(canonical_json(report) + "\n").encode("utf-8"),
                ),
            ),
            metrics={
                "frames_total": result.trajectory_frame_count,
                "frames_valid": result.trajectory_frame_count - result.nonfinite_state_count,
                "trajectory_duration_s": (
                    result.trajectory_frame_count * result.trajectory_dt_median_s
                ),
                "replay_success": False,
                "max_penetration_m": result.max_penetration_m,
                "joint_limit_violation_count": result.joint_limit_violation_count,
                "claim_level": "sim_validated_robot_trajectory",
                "acceptance_scope": result.acceptance_state,
            },
            warnings=("Do As I Do replay is diagnostic-only and cannot pass the delivery gate.",),
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
        return StageResult(
            outputs=(
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
            ),
            metrics={
                "frames_total": result.target_frame_count,
                "frames_valid": result.target_frame_count - result.nonfinite_frame_count,
                "trajectory_duration_s": result.target_frame_count / result.control_hz,
                "replay_success": result.robot_ready_accepted,
                "max_penetration_m": result.max_penetration_m,
                "joint_limit_violation_count": result.joint_limit_violation_count,
                "claim_level": "sim_validated_robot_trajectory",
                "acceptance_scope": result.acceptance_scope,
            },
            status="succeeded" if result.robot_ready_accepted else "quality_insufficient",
            warnings=tuple(result.rejection_reasons),
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

    @staticmethod
    def _execution_frame_counts(execution: PipelineExecution) -> dict[str, int]:
        counts: dict[str, int] = {}
        for output in execution.expected_outputs:
            if not output.is_dir():
                continue
            files = [path for path in output.rglob("*") if path.is_file()]
            counts[output.name] = len(files)
        return counts


class DeliveryPackageProcessor:
    """Packages only the immutable, already quality-approved R2 artifacts in the job."""

    def process(
        self, inputs: dict[str, bytes], config: bytes, request: GPUJobRequest
    ) -> tuple[ProcessorOutput, ...]:
        document = json.loads(config.decode("utf-8"))
        if document.get("schema_version") != "forge.package-job.v1":
            raise ValueError("PACKAGE_CONFIG_SCHEMA_INVALID")
        declared = list(document.get("artifacts", []))
        if not declared or len(declared) != len(inputs):
            raise ValueError("PACKAGE_ARTIFACT_SET_INCOMPLETE")
        output_contract = dict(document.get("output") or {})
        requested_formats = list(output_contract.get("formats") or ["forge_canonical"])
        if requested_formats != ["forge_canonical"]:
            raise ValueError("PACKAGE_FORMAT_REQUIRES_DEDICATED_ACCEPTED_ACTION_EXPORTER")

        files: list[dict[str, object]] = []
        supporting_outputs: list[ProcessorOutput] = []
        archive_buffer = BytesIO()
        with tarfile.open(fileobj=archive_buffer, mode="w:gz") as archive:
            for item in declared:
                input_kind = str(item["input_kind"])
                data = inputs[input_kind]
                digest = hashlib.sha256(data).hexdigest()
                if digest != str(item["sha256"]):
                    raise ValueError("PACKAGE_ARTIFACT_CHECKSUM_MISMATCH")
                filename = str(item["filename"])
                target = f"artifacts/{filename}"
                info = tarfile.TarInfo(target)
                info.size = len(data)
                info.mtime = 0
                archive.addfile(info, BytesIO(data))
                files.append(
                    {
                        "kind": item["kind"],
                        "path": target,
                        "sha256": digest,
                        "size_bytes": len(data),
                        "source_uri": item["uri"],
                        "demonstration_id": item.get("demonstration_id"),
                    }
                )

            episode_rows = [
                {
                    "demonstration_id": item.get("demonstration_id"),
                    "kind": item["kind"],
                    "path": item["path"],
                    "sha256": item["sha256"],
                }
                for item in files
            ]
            episode_index = "".join(canonical_json(item) + "\n" for item in episode_rows).encode(
                "utf-8"
            )
            self._add_bytes(archive, "exports/forge_canonical/artifact_index.jsonl", episode_index)
            dataset_card = (
                f"# FORGE dataset {document['order_id']}\n\n"
                f"Task: {document.get('skill', {}).get('name', 'unknown')}\n\n"
                f"Claim level: {output_contract.get('claim_level', 'unknown')}\n\n"
                "Start with manifest.json and verify checksums before loading any artifact.\n"
            ).encode("utf-8")
            self._add_bytes(archive, "dataset_card.md", dataset_card)
            if output_contract.get("augmentation") == "training_recipe":
                recipe = {
                    "schema_version": "forge.augmentation-recipe.v1",
                    "execution": "training_time",
                    "preserve_raw_media": True,
                    "seed_required": True,
                    "transforms": [
                        {"name": "temporal_crop", "max_fraction": 0.1},
                        {"name": "brightness", "range": [0.9, 1.1]},
                        {"name": "contrast", "range": [0.9, 1.1]},
                    ],
                    "forbidden": [
                        "horizontal_flip_without_action_semantic_remap",
                        "time_reverse_for_irreversible_tasks",
                        "geometry_warp_without_camera_recalibration",
                    ],
                }
                self._add_bytes(
                    archive,
                    "exports/forge_canonical/augmentation_recipe.json",
                    (canonical_json(recipe) + "\n").encode("utf-8"),
                )

            output_prefix = str(document.get("output_prefix") or request.output_prefix).rstrip("/")
            source_ids = {
                str(item["demonstration_id"]) for item in files if item.get("demonstration_id")
            }
            episode_count = len(source_ids) or len(files)
            quality_summary = (canonical_json(document["quality_decision"]) + "\n").encode("utf-8")
            provenance_rows = [
                {
                    "parent": item.get("demonstration_id") or item["source_uri"],
                    "child": item["path"],
                    "relation": "compiled_to" if item.get("demonstration_id") else "packaged_as",
                    "sha256": item["sha256"],
                }
                for item in files
            ]
            provenance = "".join(canonical_json(item) + "\n" for item in provenance_rows).encode(
                "utf-8"
            )
            model_versions = (
                canonical_json(
                    {
                        "pipeline_release": document.get("pipeline_release"),
                        "package_processor": "forge-delivery-package-v2",
                    }
                )
                + "\n"
            ).encode("utf-8")
            checksums = "".join(
                f"{item['sha256']}  {item['path']}\n"
                for item in sorted(files, key=lambda x: str(x["path"]))
            ).encode("utf-8")
            evidence_files = {
                "quality/summary.json": quality_summary,
                "provenance/graph.jsonl": provenance,
                "provenance/model_versions.json": model_versions,
                "provenance/artifact_checksums.sha256": checksums,
            }
            for path, data in evidence_files.items():
                self._add_bytes(archive, path, data)

            delivery_id = (
                "del_"
                + hashlib.sha256(
                    f"{document['order_id']}:{document['dataset_version']}".encode("utf-8")
                ).hexdigest()[:20]
            )
            manifest = {
                "schema_version": "forge.delivery.v1",
                "order_id": document["order_id"],
                "delivery_id": delivery_id,
                "dataset_version": document["dataset_version"],
                "rights_profile": document["rights_profile"],
                "source_summary": {
                    "submitted": episode_count,
                    "accepted": episode_count,
                    "rejected": 0,
                },
                "episode_summary": {
                    "generated": 0,
                    "validated": episode_count,
                    "delivered": episode_count,
                },
                "quality_summary_uri": f"{output_prefix}/quality_summary.json",
                "provenance_graph_uri": f"{output_prefix}/provenance_graph.jsonl",
                "model_versions_uri": f"{output_prefix}/model_versions.json",
                "checksums_uri": f"{output_prefix}/artifact_checksums.sha256",
                "exports": [
                    {"format": "forge_canonical", "uri": f"{output_prefix}/forge-delivery.tar.gz"}
                ],
                "known_limitations": list(document.get("known_limitations", [])),
                "created_from_pipeline_release": str(document.get("pipeline_release")),
            }
            manifest_data = (canonical_json(manifest) + "\n").encode("utf-8")
            self._add_bytes(archive, "manifest.json", manifest_data)

        supporting_outputs.extend(
            (
                ProcessorOutput("quality_summary", "quality_summary.json", quality_summary),
                ProcessorOutput(
                    "provenance_graph",
                    "provenance_graph.jsonl",
                    provenance,
                    media_type="application/x-ndjson",
                ),
                ProcessorOutput("model_versions", "model_versions.json", model_versions),
                ProcessorOutput(
                    "artifact_checksums",
                    "artifact_checksums.sha256",
                    checksums,
                    media_type="text/plain",
                ),
            )
        )
        return (
            ProcessorOutput(
                kind="delivery_package",
                filename="forge-delivery.tar.gz",
                data=archive_buffer.getvalue(),
                media_type="application/gzip",
            ),
            ProcessorOutput(
                kind="delivery_manifest",
                filename="manifest.json",
                data=manifest_data,
            ),
            *supporting_outputs,
        )

    @staticmethod
    def _add_bytes(archive: tarfile.TarFile, path: str, data: bytes) -> None:
        info = tarfile.TarInfo(path)
        info.size = len(data)
        info.mtime = 0
        archive.addfile(info, BytesIO(data))
