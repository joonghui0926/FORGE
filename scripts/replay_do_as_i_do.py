from __future__ import annotations

import argparse
import json
from pathlib import Path

from forge.adapters.papers.do_as_i_do_replay import DoAsIDoReplayEvaluator


def main() -> None:
    parser = argparse.ArgumentParser(description="FORGE diagnostic replay for Do As I Do")
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = DoAsIDoReplayEvaluator().evaluate(args.scene, args.trajectory)
    encoded = json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
