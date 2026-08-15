# Reproducible benchmark evidence

`evidence/` contains bounded, non-simulated execution records captured on the RunPod A40
evaluation pod. The source/model revisions and input hashes make each record auditable.

- `a40-smoke-2026-08-15.json`: CUDA FP16 matrix-multiply smoke profile.
- `videomanip-frames-2026-08-15.json`: complete frame extraction from VideoManip's pinned
  example video.
- `videomanip-moge-metric-2026-08-15.json`: official MoGe-2 metric-depth/intrinsics run over
  all 148 public VideoManip frames on A40. The one-to-one artifacts pass structural checks,
  but the record remains unapproved because no independent calibration or robot replay is
  present.
- `gmr-unitree-g1-20f-2026-08-15.json`: Xsens BVH to Unitree G1 trajectory candidate from
  the FORGE headless GMR adapter.
- `do-as-i-do-whisking-replay-2026-08-15.json`: segmented open-loop MuJoCo replay of the
  pinned Sharpa whisking fixture. The diagnostic remains unapproved because penetration and
  joint-limit events require a calibrated profile and investigation.
- `do-as-i-do-stage5-100-gpu-2026-08-15.json`: a real 100-frame MuJoCo Warp optimization
  run using 1,024 parallel rollout samples on A40.
- `do-as-i-do-stage5-100-replay-2026-08-15.json`: independent replay of that newly generated
  candidate. It had no nonfinite states or joint-limit events and 1.08 mm maximum
  penetration, but its open-loop free-joint translation drift is 0.54 m, so it remains
  explicitly unapproved and requires optimizer/replay alignment work.
- `r2-connectivity-2026-08-15.json`: a live write/read/checksum round trip against the
  configured `forge-dev` R2 bucket without customer data.
- `gmr-unitree-g1-full-2026-08-15.json`: the complete 4,249-frame Xsens boxing source
  retargeted to Unitree G1 in 18.93 seconds.
- `gmr-unitree-g1-full-kinematic-2026-08-15.json`: fail-closed diagnostics for that candidate;
  penetration and self-collision metrics reject it pending physics-aware refinement.
- `do-as-i-do-stage5-500-gpu-2026-08-15.json` and its replay record extend the A40 optimizer
  evaluation to 500 frames. The output is still rejected due large free-joint drift.

These files show that a compiler stage executed on real hardware. They do not show that a
trajectory is safe or useful on a customer robot. Only a separate deterministic validation
record from the exact target simulator/robot profile can set an episode to accepted.
