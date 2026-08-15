from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from forge.adapters.papers.videomanip_validation import VideoManipMetricEvaluator


class VideoManipValidationTest(unittest.TestCase):
    def test_missing_dataset_fails_before_loading_optional_runtime(self) -> None:
        with self.assertRaises(FileNotFoundError):
            VideoManipMetricEvaluator().evaluate(
                Path("missing-dataset"),
                Path("missing-video.mp4"),
                expected_frames=1,
                videomanip_revision="a" * 40,
                moge_revision="b" * 40,
                checkpoint_revision="c" * 40,
            )

    def test_missing_video_fails_before_loading_optional_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(FileNotFoundError):
                VideoManipMetricEvaluator().evaluate(
                    Path(temp_dir),
                    Path(temp_dir) / "missing.mp4",
                    expected_frames=1,
                    videomanip_revision="a" * 40,
                    moge_revision="b" * 40,
                    checkpoint_revision="c" * 40,
                )
