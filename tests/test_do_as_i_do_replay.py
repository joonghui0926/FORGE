from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from forge.adapters.papers.do_as_i_do_replay import DoAsIDoReplayEvaluator
from workers.processors import PaperPipelineProcessor


class DoAsIDoReplayTest(unittest.TestCase):
    def test_missing_scene_fails_before_loading_optional_runtime(self) -> None:
        with self.assertRaises(FileNotFoundError):
            DoAsIDoReplayEvaluator().evaluate(
                Path("missing-scene.xml"), Path("missing-trajectory.npz")
            )

    def test_worker_rejects_replay_path_traversal(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "REPLAY_PATH_TRAVERSAL"):
                PaperPipelineProcessor._safe_relative_path(Path(directory), "../scene.xml")
