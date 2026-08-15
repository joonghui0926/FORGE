from __future__ import annotations

import unittest

from scripts.benchmark_gpu import percentile_nearest_rank, theoretical_tflops


class GPUBenchmarkMathTest(unittest.TestCase):
    def test_percentile_and_tflops_are_deterministic(self) -> None:
        self.assertEqual(percentile_nearest_rank([4.0, 1.0, 3.0, 2.0], 0.95), 4.0)
        self.assertEqual(theoretical_tflops(1000, 2.0), 1.0)
