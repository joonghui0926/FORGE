from __future__ import annotations

import json
import subprocess
from unittest.mock import patch

from forge.contracts.models import GPUJobRequest
from forge.integrations.runpod.handler import StageResult
from tests.helpers import SHA
from workers.processors import PaperPipelineProcessor


def _request() -> GPUJobRequest:
    return GPUJobRequest(
        job_id="job_video_qc",
        idempotency_key=SHA,
        stage="reconstruction",
        input_artifacts=(),
        config_uri="r2://forge-dev/config/video-qc.json",
        container_image="ghcr.io/forge/worker@sha256:" + SHA,
        pipeline_version="forge-compiler-v2",
        output_prefix="r2://forge-dev/output/job_video_qc",
    )


def test_owned_video_qc_reports_full_decode_metrics() -> None:
    config = json.dumps(
        {
            "adapter_id": "forge-video-qc-v1",
            "input_kind": "source",
            "minimum_width_px": 1920,
            "minimum_height_px": 1080,
            "minimum_frame_rate_hz": 30,
        }
    ).encode()
    probe = subprocess.CompletedProcess(
        args=("ffprobe",),
        returncode=0,
        stdout=json.dumps(
            {
                "streams": [
                    {
                        "width": 1920,
                        "height": 1080,
                        "avg_frame_rate": "30/1",
                        "nb_read_frames": "180",
                        "duration": "6.0",
                    }
                ]
            }
        ),
        stderr="",
    )
    decode = subprocess.CompletedProcess(args=("ffmpeg",), returncode=0, stdout="", stderr="")

    with patch("workers.processors.subprocess.run", side_effect=(probe, decode)):
        result = PaperPipelineProcessor().process({"source": b"immutable-mp4"}, config, _request())

    assert isinstance(result, StageResult)
    assert result.status == "succeeded"
    assert result.metrics["frames_total"] == 180
    assert result.metrics["frames_valid"] == 180
    assert result.metrics["claim_level"] == "human_video_training"
    report = json.loads(result.outputs[0].data)
    assert report["full_decode_passed"] is True
    assert report["accepted"] is True


def test_owned_video_qc_fails_closed_on_low_resolution() -> None:
    config = b'{"adapter_id":"forge-video-qc-v1","input_kind":"source"}'
    probe = subprocess.CompletedProcess(
        args=("ffprobe",),
        returncode=0,
        stdout='{"streams":[{"width":1280,"height":720,"avg_frame_rate":"30/1",'
        '"nb_read_frames":"90","duration":"3"}]}',
        stderr="",
    )
    decode = subprocess.CompletedProcess(args=("ffmpeg",), returncode=0, stdout="", stderr="")

    with patch("workers.processors.subprocess.run", side_effect=(probe, decode)):
        result = PaperPipelineProcessor().process({"source": b"small"}, config, _request())

    assert isinstance(result, StageResult)
    assert result.status == "quality_insufficient"
    assert "VIDEO_WIDTH_LOW" in result.warnings
    assert result.metrics["frames_valid"] == 0
