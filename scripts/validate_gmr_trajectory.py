from __future__ import annotations

import argparse
import json
from pathlib import Path

from forge.adapters.papers.gmr_validation import GMRKinematicEvaluator


def main() -> None:
    parser = argparse.ArgumentParser(description="FORGE kinematic diagnostic for GMR output")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--robot", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = GMRKinematicEvaluator().evaluate(args.model, args.trajectory, args.robot)
    encoded = json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
