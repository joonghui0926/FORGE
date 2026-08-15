from __future__ import annotations

from pathlib import Path
import unittest

from forge.adapters.papers.gmr_validation import GMRKinematicEvaluator


class GMRValidationTest(unittest.TestCase):
    def test_missing_model_fails_before_loading_optional_runtime(self) -> None:
        with self.assertRaises(FileNotFoundError):
            GMRKinematicEvaluator().evaluate(
                Path("missing-model.xml"), Path("missing-trajectory.npz"), "unitree_g1"
            )
