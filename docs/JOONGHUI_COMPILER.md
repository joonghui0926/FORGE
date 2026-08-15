# Joonghui compiler handoff

This document is the executable boundary for Joonghui's work. It distinguishes code that
exists now from research integrations that still need a licensed dependency and a GPU run.

## Product contract

FORGE accepts a signed task definition and target robot description. It returns only
customer-owned, robot-ready episodes that contain target-robot state/action trajectories,
motion-specific replay evidence, source lineage, artifact hashes, compiler/model versions,
rights metadata, rejection reasons and a dataset card. Raw video is an input artifact, not
the product.

The source actor is intentionally generic. A demonstration may come from a person, another
robot, teleoperation, a simulator or mixed sensors. Supported motion families are rigid and
bimanual manipulation, tool use, locomotion, whole-body motion, mobile manipulation,
navigation, aerial motion, articulated machines and multi-robot coordination. A motion
family is not sellable until its validation profile and target simulator adapter exist.

## Authoritative pipeline

1. `modules/collection` compiles the customer request into capture views, observability
   requirements, expert/general-worker selection, safety requirements, rejection codes and
   a rights packet. Terac is a worker execution provider; it never defines dataset quality.
2. Original source bytes and metadata enter R2 under immutable, checksummed artifact IDs.
3. `modules/reconstruction` normalizes source observations. Robot/teleop state uses the
   FORGE-owned direct state compiler. Video paths are isolated behind pinned paper adapters.
4. Every valid observation becomes `CanonicalSkillIR`: metric SE(3), named frames, joint
   state, phases, contacts, source actor/model, counterpart assets and reconstruction proof.
5. `stable_contact` implements a generalized C2Dex-derived constraint compiler: candidates
   must be slow, close, visible and normal-consistent; points are transformed into the
   moving counterpart's canonical frame, segmented in time, clustered and represented by a
   medoid with uncertainty. This applies to feet/terrain, tools/workpieces, wheels/ground,
   grippers/objects and robot/robot contacts—not only hands.
6. `retarget` creates the target capability/constraint plan. Pinned external solvers execute
   in their own environment and their output is normalized back to Skill IR/trajectory
   contracts. Solver success is never a quality pass.
7. `validation` replays each target episode with a profile for its motion family. Missing
   required metrics fail closed. Learned Pioneer QC may prioritize review or recollection,
   but cannot override rights, checksum, collision, penetration, joint-limit or replay gates.
8. `amplification` can transform only independently accepted source episodes. Relative
   actor/counterpart geometry is preserved. Every generated child is marked unvalidated and
   must pass a new replay; it cannot inherit its parent's acceptance.
9. `packaging` emits the manifest, raw index/Parquet, trajectories, replay evidence,
   rejection reasons, source-to-child graph, hashes, model versions, rights file and exports.

## Paper/code mapping

| Research/code | FORGE use | Boundary and current truth |
| --- | --- | --- |
| VideoManip, commit `9d0f286...` | monocular manipulation reconstruction: metric camera/depth, masks, rigid object pose, MANO hand estimate and optional retarget stages | adapter and exact output checks exist; the A40 evaluation extracted all 148 frames of the pinned example, while later model stages and transitive commercial licenses remain evaluation-only |
| C2Dex paper | stable object-side contact in a moving canonical frame, temporal local segments, density clustering/medoid and contact-driven retarget constraints | FORGE-owned generalized implementation exists; residual RL from the paper is not claimed |
| Do As I Do, commit `824591b...` | high-quality manipulation fallback using preprocessing, scene generation, IK and MuJoCo Warp physics optimization | pinned A40 Stage-5 run reached 92% GPU utilization and generated a real Sharpa candidate; independent replay remains mandatory and unapproved metrics fail closed |
| GMR, commit `bb1bbe4...` | whole-body SMPL-X/BVH/GVHMR motion retargeting to supported humanoids | FORGE's headless Xsens BVH adapter converted all 4,249 frames to Unitree G1 in 18.93 s; kinematic diagnostics rejected the candidate for penetration/self-collision, proving target-specific dynamic replay is still required |
| ASAP, commit `df5320c...` | candidate whole-body physics alignment and sim-to-real policy path | locked as evaluation-only; not wired into a production output |
| InterMimic, commit `60d6d6e...` | candidate whole-body human-object interaction benchmark and G1 policy route | locked as evaluation-only; not wired into a production output |

Do not merge paper repositories into `src/forge`. Keep them pinned in an image or mounted
volume. The lock and commercial review live in `third_party/`.

## Platform ownership

- **Render** hosts customer API/UI, order state, workflow orchestration and Postgres. It does
  not run CUDA reconstruction.
- **Cloudflare R2** is the immutable artifact system for raw sources, configs, models,
  intermediate proof and delivery bundles. Signed URLs are short-lived; customer and worker
  access are tenant-scoped.
- **RunPod** executes digest-pinned GPU jobs. Requests/results follow `packages/contracts`;
  results are cached by idempotency key in R2 so a restarted worker does not duplicate work.
- **Terac** receives machine-actionable collection plans, selects authorized expert or
  general workers, returns source artifacts and receives structured rejection/recollection
  instructions. The production write adapter remains disabled until the sponsor provides
  its authenticated schema.
- **Pioneer** learns source-usability and replay-pass predictors from non-PII features and
  rejection outcomes. It saves GPU/review time; deterministic gates stay authoritative.
- **Band** is the company operating and knowledge layer: customer conversation, decisions,
  task templates, incident notes and skill catalog. Store references and decisions there,
  not raw customer media or secret keys.

## Joonghui's responsibility

Joonghui owns the compiler and evidence boundary: schemas, coordinate/calibration contracts,
paper adapters, Skill IR, stable-contact constraints, embodiment retargeting, simulator
profiles, RunPod images/jobs, R2 artifact integrity, Pioneer QC lifecycle, augmentation
authorization, dataset packaging and GPU benchmarking. He approves no dataset without a
reproducible replay report.

Inseon owns customer intake/product/API/UI, auth/tenancy, Render/Postgres/workflow state,
Terac operations, worker instructions, notifications, billing/Stripe and delivery UX. The
shared boundary is versioned JSON schema plus immutable R2 artifact references; neither side
passes ad-hoc paths or database rows across the boundary.

## Completion and production gates

Implemented and locally verified: generalized contracts, customer-to-collection planner,
direct robot-state normalization, stable-contact compiler, constraint planner,
motion-specific deterministic quality gates, safe amplification, Pioneer fixture/provider
boundary, R2 adapter, durable RunPod idempotency, delivery builder, pinned paper runners and
fixture tests. Live A40 evaluation additionally verified CUDA execution, lossless frame
extraction on the pinned VideoManip example, and headless GMR Xsens-to-Unitree-G1 trajectory
generation. A pinned Do As I Do MuJoCo Warp run reached 92% A40 utilization for 1,024-way
rollout optimization, and generated candidates were checksum-verified in R2. Independent
replay rejected the evaluated candidates for physical-quality reasons, which is the intended
fail-closed behavior. These are compiler-stage proofs, not customer acceptance.

Still required before a real customer promise: build/push a digest-pinned GPU image with all
licensed weights; benchmark customer sources and exact target simulators (use A100 only when
A40 profiling requires it); add closed-loop target robot controllers; get Terac/Pioneer
production API schemas; obtain legal approval for dependencies and collection rights;
measure rejection/labor/GPU distributions; and run a customer acceptance test on the target
embodiment. Development fixtures are always marked `simulation=true` and production rejects
them.
