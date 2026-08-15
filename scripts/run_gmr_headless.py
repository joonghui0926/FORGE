from __future__ import annotations

import argparse
import json
from pathlib import Path

from forge.adapters.papers.gmr_headless import GMRHeadlessRunner


def main() -> None:
    parser = argparse.ArgumentParser(description="FORGE headless GMR Xsens BVH adapter")
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--bvh", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--robot", default="unitree_g1")
    parser.add_argument("--start-frame", type=int)
    parser.add_argument("--end-frame", type=int)
    parser.add_argument("--scale", type=float, default=0.01)
    parser.add_argument("--reset-to-zero", action="store_true")
    parser.add_argument("--offsets", type=Path)
    args = parser.parse_args()
    result = GMRHeadlessRunner().retarget_xsens_bvh(
        checkout=args.checkout,
        bvh_file=args.bvh,
        output_file=args.output,
        robot_id=args.robot,
        start_frame=args.start_frame,
        end_frame=args.end_frame,
        scale=args.scale,
        reset_to_zero=args.reset_to_zero,
        offsets_file=args.offsets,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
