from __future__ import annotations

import argparse
import json
from pathlib import Path

from forge.adapters.papers.videomanip_interaction import VideoManipInteractionCompiler


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile VideoManip metric interaction output")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--source-video", type=Path, required=True)
    parser.add_argument("--output-npz", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--fps", type=float, required=True)
    parser.add_argument("--videomanip-revision", required=True)
    parser.add_argument("--sam2-revision", required=True)
    parser.add_argument("--sam2-checkpoint-sha256", required=True)
    parser.add_argument("--hamer-revision", required=True)
    parser.add_argument("--hamer-checkpoint-sha256", required=True)
    parser.add_argument("--vitpose-revision", required=True)
    parser.add_argument("--vitpose-checkpoint-sha256", required=True)
    args = parser.parse_args()
    result = VideoManipInteractionCompiler().compile(
        args.dataset_root,
        args.source_video,
        args.output_npz,
        fps=args.fps,
        videomanip_revision=args.videomanip_revision,
        sam2_revision=args.sam2_revision,
        sam2_checkpoint_sha256=args.sam2_checkpoint_sha256,
        hamer_revision=args.hamer_revision,
        hamer_checkpoint_sha256=args.hamer_checkpoint_sha256,
        vitpose_revision=args.vitpose_revision,
        vitpose_checkpoint_sha256=args.vitpose_checkpoint_sha256,
    )
    encoded = json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n"
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
