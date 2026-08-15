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
| VideoManip `real_14_pourtea.mp4` | 148 RGB frames, 148 MoGe-2 uint16 millimetre depth maps, 148 camera matrices | one-to-one correspondence; all files readable; 100% positive depth; 0% saturation; 0.226–1.664 m range | no calibration ground truth, object/effector trajectory, contacts, target action or replay |
| GMR Xsens boxing BVH | 4,249-frame Unitree G1 `qpos` candidate | finite states and joint limits | 1,272 self-collision frames, 22.8 mm max penetration and 0.0534 m/s support-foot slip p95; no closed-loop action |
| Do As I Do Sharpa whisking fixture | GPU-optimized `qpos`/`ctrl` candidate using 1,024 parallel rollouts | real A40 optimization; finite states; no joint-limit events in independent replay | 0.537 m free-joint drift and 4.77 mm penetration on the 500-frame run |

The correct audit result is therefore **no public candidate is currently a customer-ready
episode**. This is not a pipeline crash: the FORGE quality boundary correctly rejects paper
outputs that do not yet satisfy the product contract.

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

## Next acceptance path

For manipulation, the next useful integration is masks + rigid object/effector pose, then
canonical contact/phase extraction, target-specific retargeting and independent replay. For
locomotion and other robots, video-only reconstruction is replaceable: calibrated robot
state, teleoperation logs or simulator state should enter the generic Skill IR directly.
No motion family is accepted until its target embodiment and deterministic validation
profile pass.
