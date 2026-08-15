from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from time import perf_counter

from forge.adapters.papers.runners import DoAsIDoAdapter


def main() -> None:
    parser = argparse.ArgumentParser(description="Run pinned Do As I Do stage-5 GPU optimizer")
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--task", default="whisking")
    parser.add_argument("--robot", default="sharpa")
    parser.add_argument("--hand", default="right")
    parser.add_argument("--data-id", type=int, default=0)
    parser.add_argument("--max-sim-steps", type=int, default=100)
    args = parser.parse_args()
    if args.max_sim_steps < 1:
        raise ValueError("max-sim-steps must be positive")

    DoAsIDoAdapter().assert_checkout(args.checkout)
    retargeting_root = args.checkout / "retargeting"
    sys.path.insert(0, str(retargeting_root))
    from launch import load_mjwp_config
    from retargeting.pipeline.optimize_physics import main as optimize_physics

    run_dir = args.output_root / args.robot / args.hand / args.task / str(args.data_id)
    scene_path = run_dir / "scene.xml"
    reference_path = run_dir / "trajectory_kinematic.npz"
    if not scene_path.is_file() or not reference_path.is_file():
        raise FileNotFoundError("DO_AS_I_DO_OPTIMIZER_INPUTS_MISSING")
    config = load_mjwp_config(
        dataset_name="do_as_i_do",
        task=args.task,
        data_id=args.data_id,
        robot_type=args.robot,
        embodiment_type=args.hand,
        output_root_dir=str(args.output_root),
        max_sim_steps=args.max_sim_steps,
        force=True,
        show_viewer=False,
        wait_on_finish=False,
    )
    started = perf_counter()
    optimize_physics(config)
    duration_s = perf_counter() - started
    output_path = run_dir / "trajectory_mjwp.npz"
    if not output_path.is_file():
        raise RuntimeError("DO_AS_I_DO_OPTIMIZER_OUTPUT_MISSING")
    result = {
        "schema_version": "forge.do-as-i-do-optimizer-run.v1",
        "adapter_id": "do-as-i-do-stage5-gpu-v1",
        "revision": DoAsIDoAdapter.revision,
        "task": args.task,
        "robot_id": args.robot,
        "hand": args.hand,
        "max_sim_steps": args.max_sim_steps,
        "duration_s": duration_s,
        "output_sha256": sha256(output_path.read_bytes()).hexdigest(),
        "output_bytes": output_path.stat().st_size,
        "simulation": False,
        "acceptance_state": "candidate_requires_independent_replay",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
