from __future__ import annotations

import argparse
import json
from pathlib import Path

from forge.adapters.papers.videomanip_validation import VideoManipMetricEvaluator


def main() -> None:
    parser = argparse.ArgumentParser(description="FORGE diagnostic for VideoManip MoGe output")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--source-video", type=Path, required=True)
    parser.add_argument("--expected-frames", type=int, required=True)
    parser.add_argument("--videomanip-revision", required=True)
    parser.add_argument("--moge-revision", required=True)
    parser.add_argument("--checkpoint-revision", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = VideoManipMetricEvaluator().evaluate(
        args.dataset_root,
        args.source_video,
        expected_frames=args.expected_frames,
        videomanip_revision=args.videomanip_revision,
        moge_revision=args.moge_revision,
        checkpoint_revision=args.checkpoint_revision,
    )
    encoded = json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
