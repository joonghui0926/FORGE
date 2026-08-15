from __future__ import annotations

import argparse
import json
from pathlib import Path

from forge.adapters.papers.twist_replay import TWISTG1ReplayEvaluator


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay a GMR trajectory with TWIST")
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output-npz", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--twist-revision", required=True)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    result = TWISTG1ReplayEvaluator().evaluate(
        args.trajectory,
        args.model,
        args.policy,
        args.output_npz,
        source_start_frame=args.start,
        source_end_frame_exclusive=args.end,
        twist_revision=args.twist_revision,
        device=args.device,
    )
    encoded = json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
