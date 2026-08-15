from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import tarfile

from forge.adapters.papers.runners import DoAsIDoAdapter, PipelineExecution, VideoManipAdapter
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
