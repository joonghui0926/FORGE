from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from forge.adapters.papers.videomanip_interaction import VideoManipInteractionCompiler


class VideoManipInteractionTest(unittest.TestCase):
    def test_phase_segments_preserve_complete_timeline(self) -> None:
        segments = VideoManipInteractionCompiler.segment_phases((0, 0, 2, 2, 2, 3, 0))
        self.assertEqual(
            [(item["label"], item["start_frame"], item["end_frame"]) for item in segments],
            [
                ("unobserved", 0, 1),
                ("grasp_hold", 2, 4),
                ("transport", 5, 5),
                ("unobserved", 6, 6),
            ],
        )

    def test_missing_source_fails_before_loading_optional_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                VideoManipInteractionCompiler().compile(
                    Path(directory),
                    Path(directory) / "missing.mp4",
                    Path(directory) / "output.npz",
                    fps=30.0,
                    videomanip_revision="a" * 40,
                    sam2_revision="b" * 40,
                    sam2_checkpoint_sha256="c" * 64,
                    hamer_revision="d" * 40,
                    hamer_checkpoint_sha256="e" * 64,
                    vitpose_revision="f" * 40,
                    vitpose_checkpoint_sha256="1" * 64,
                )
