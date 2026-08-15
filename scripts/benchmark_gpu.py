from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import median


def percentile_nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("values cannot be empty")
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be in (0, 1]")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(percentile * len(ordered) + 0.999999) - 1))
    return ordered[index]


def theoretical_tflops(matrix_size: int, duration_ms: float) -> float:
    if matrix_size < 1 or duration_ms <= 0:
        raise ValueError("matrix size and duration must be positive")
    operations = 2 * matrix_size**3
    return operations / (duration_ms / 1000) / 1_000_000_000_000


def run_benchmark(matrix_size: int, warmup: int, iterations: int) -> dict[str, object]:
    try:
        import torch
    except ImportError as error:
        raise RuntimeError("PYTORCH_REQUIRED") from error
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA_NOT_AVAILABLE")
    if min(matrix_size, warmup, iterations) < 1:
        raise ValueError("matrix size, warmup and iterations must be positive")

    torch.manual_seed(20260815)
    device = torch.device("cuda:0")
    torch.cuda.set_device(0)
    torch.cuda.reset_peak_memory_stats(0)
    left = torch.randn((matrix_size, matrix_size), device=device, dtype=torch.float16)
    right = torch.randn((matrix_size, matrix_size), device=device, dtype=torch.float16)
    for _ in range(warmup):
        torch.mm(left, right)
    torch.cuda.synchronize(device)

    timings_ms: list[float] = []
    output = None
    for _ in range(iterations):
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        output = torch.mm(left, right)
        end.record()
        torch.cuda.synchronize(device)
        timings_ms.append(float(start.elapsed_time(end)))
    assert output is not None
    output_checksum = float(output[:16, :16].float().sum().item())
    median_ms = median(timings_ms)
    properties = torch.cuda.get_device_properties(0)
    return {
        "schema_version": "forge.gpu-benchmark.v1",
        "captured_at": datetime.now(UTC).isoformat(),
        "simulation": False,
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "gpu_name": properties.name,
        "gpu_total_memory_bytes": properties.total_memory,
        "matrix_size": matrix_size,
        "dtype": "float16",
        "warmup_iterations": warmup,
        "measured_iterations": iterations,
        "median_ms": median_ms,
        "p95_ms": percentile_nearest_rank(timings_ms, 0.95),
        "minimum_ms": min(timings_ms),
        "maximum_ms": max(timings_ms),
        "median_theoretical_tflops": theoretical_tflops(matrix_size, median_ms),
        "peak_allocated_memory_bytes": torch.cuda.max_memory_allocated(0),
        "output_checksum_sample": output_checksum,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded FORGE CUDA smoke benchmark")
    parser.add_argument("--matrix-size", type=int, default=8192)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_benchmark(args.matrix_size, args.warmup, args.iterations)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
