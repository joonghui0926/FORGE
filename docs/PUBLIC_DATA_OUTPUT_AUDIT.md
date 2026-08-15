# Public-data output audit

## The product output FORGE must deliver

A successful paper stage is not the product. The sellable unit is a customer-owned,
target-robot episode with all of the following bound by one immutable manifest:

1. synchronized observations and calibration for every sensor;
2. canonical metric Skill IR with named frames, phases, contacts and uncertainty;
3. target robot states **and executable actions/controls** with units and timestamps;
4. exact robot/scene/object assets and controller/config revisions;
5. independent closed-loop replay evidence against the motion-family quality profile;
6. lineage, rights, checksums, model/container revisions and source-to-child relations;
7. explicit rejection records, a dataset card and customer-requested training export.

Raw videos, monocular depth maps, hand meshes and open-loop `qpos` arrays are intermediate
artifacts. They are useful only when they contribute to the episode above.

## Reproducible public runs on the A40

| Public source | Actual output | What passed | Why it is not deliverable yet |
|---|---|---|---|
| VideoManip `real_14_pourtea.mp4` | 148 metric depth/camera frames, 296 SAM2 object masks, 148 HaMeR joint/mesh observations and a 44,547-byte numeric interaction NPZ | 148/148 fused frames; hand–grasp distance median 7.62 mm; 144 contact-candidate frames; `free → transport → target interaction` phases | camera-to-world calibration, rigid object orientation and an exact target robot/action/replay are not present |
| GMR Xsens boxing BVH → TWIST G1 | 1,241-frame, 50 Hz G1 action artifact from a clean 2,977-frame source interval | closed-loop GPU policy + 27,820 MuJoCo steps; no falls, material self-collisions, nonfinite states or joint-limit events; `robot_ready_accepted=true` for G1 25-DoF sim2sim | scoped to the pinned G1 sim2sim model; not physical-hardware approval |
| Do As I Do Sharpa whisking fixture | GPU-optimized `qpos`/`ctrl` candidate using 1,024 parallel rollouts | real A40 optimization; finite states; no joint-limit events in independent replay | 0.537 m free-joint drift and 4.77 mm penetration on the 500-frame run |

The public whole-body path now produces one **scope-qualified robot-ready episode** for
`unitree_g1_25dof_sim2sim`. The manipulation and Do As I Do candidates remain rejected.
FORGE does not promote the sim2sim result to unattended physical-hardware approval.

## VideoManip/MoGe run evidence

- VideoManip revision: `9d0f286af35d73f4252d115d968e0a9c06542b9c`
- MoGe revision: `925b8ed835a7a9cdb7578ba15c658a0afc969030`
- MoGe checkpoint revision: `b135031bae30b5ac2ae141a0e68717795ce38340`
- Checkpoint SHA-256: `280741fd09bc3f403ccff9967784c2a391b52d2c0742ae3efdb21d9f90cc1a01`
- Public video SHA-256: `5f2d2ff7f2164f8e108308742c5a1056015ce04b67f91f8e760003f062e6db94`
- Resolution/frame count: 1280×720, 148 frames
- A40 inference stage wall time: 66 seconds
- Durable evidence: `benchmarks/evidence/videomanip-moge-metric-2026-08-15.json`
- R2 round-trip verified object: `r2://forge-dev/evaluation/videomanip/moge-metric-2026-08-15.json`

## VideoManip interaction evidence

- SAM2 revision/checkpoint: `2b90b9f...` / `2647878d...`
- HaMeR revision/checkpoint: `091de2a...` / `e5cc06f2...`
- ViTPose revision/checkpoint: `d521645...` / `b0555e1e...`
- 148/148 valid hand, grasp-mask and target-mask frames; zero ambiguous actors
- Interaction NPZ SHA-256: `ca4bef79eeb3a7265ba2a264f31ecd49818d41372d57ec889f80ee1f4e205962`
- Evidence: `benchmarks/evidence/videomanip-interaction-2026-08-15.json`
- R2 round-trip: `r2://forge-dev/evaluation/videomanip/interaction/ca4bef79e...npz`

## GMR + TWIST accepted sim2sim evidence

- GMR revision: `bb1bbe40774794fceb2a7c579a3464a28e68c844`
- TWIST revision/policy: `42d8c134...` / `0ec24c54...`
- Source interval: `[768, 3745)`, resampled to 1,241 control frames at 50 Hz
- Replay: 27,820 MuJoCo steps, 0 falls, 0 material self-collisions, 0 joint-limit events
- Tracking: 0.2053 rad joint RMSE, 0.0482 m height RMSE, 0.0693 rad roll/pitch RMSE
- Accepted action SHA-256: `e6b967ca42acb296c57180a7e54e916722c3912108271fdf0dececbff120db3d`
- Evidence: `benchmarks/evidence/twist-g1-replay-2026-08-15.json`
- R2 round-trip: `r2://forge-dev/validated/twist/unitree-g1/e6b967ca...npz`

## Next acceptance path

For manipulation, the remaining path is calibrated camera-to-world plus rigid object 6-DoF,
then target-specific retargeting and independent replay. For physical G1 use, the accepted
sim2sim artifact still requires perturbation tests, exact firmware/SDK/controller pinning and
a supervised hardware acceptance run. Other robots enter through the same target-profile
boundary; acceptance never transfers between embodiments.
