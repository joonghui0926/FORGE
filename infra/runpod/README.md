# RunPod execution handoff

The current Dockerfile is the FORGE worker envelope. It deliberately does not copy licensed
MANO files, model weights or external paper repositories into Git. Mount or bake an approved
vendor environment, then pin the resulting image by digest in every `GPUJobRequest`.

## Evaluation pod

Use one A40 48 GB for the first benchmark. Ten FORGE users share an asynchronous queue; GPU
count is driven by queued GPU-seconds and delivery deadline, not web-user count. An A40 at
$0.44/hour is $3.52 for eight GPU hours; the console's attached-disk charges are additional.
Use an A100 80 GB only when A40 profiling shows out-of-memory or misses the required
turnaround. Stop the Pod at the end of the benchmark and delete only disposable container
disk; keep approved model cache/results on the intended volume or R2.

Required runtime environment:

```text
FORGE_ENV=production
R2_BUCKET_NAME
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
R2_ENDPOINT
VIDEOMANIP_CHECKOUT=/opt/vendor/VideoManip
DO_AS_I_DO_CHECKOUT=/opt/vendor/do-as-i-do
GMR_CHECKOUT=/opt/vendor/GMR
MANO_MODEL_DIR=/run/secrets/mano/models
HF_TOKEN
```

Never put credentials or MANO assets in the image layer. Run the container with the exact
external revisions in `third_party/THIRD_PARTY_LOCK.json`. The paper runners reject a
checkout whose Git HEAD does not match the lock.

## Job contract

Upload source/config artifacts to R2, compute their SHA-256, then submit a
`forge.gpu-job.v1` document from `packages/contracts/schemas/gpu-job.v1.schema.json`.
The image must be an OCI digest (`...@sha256:...`). Successful artifacts are written only
under `output_prefix`; the final result is also stored at
`r2://<bucket>/_forge/idempotency/<idempotency_key>.json`.

VideoManip adapter configuration example:

```json
{
  "adapter_id": "videomanip-reconstruction-v1",
  "input_kind": "source",
  "object_id": "customer_take_0001",
  "source_extension": ".mp4",
  "stages": ["frames", "intrinsics", "hand_mesh", "masks", "obj_mesh", "retarget"],
  "timeout_s": 7200
}
```

Interactive click collection is not allowed in a headless job. Generate and validate the
click artifact before dispatch or run an approved automatic point-selection stage. Object
pose additionally needs the pinned FoundationPose environment. Do As I Do consumes a safe
tar archive of reconstruction artifacts and must emit `scene.xml`,
`trajectory_mjwp*.npz`, and `config.yaml` or the job fails.

GMR headless Xsens BVH configuration example:

```json
{
  "adapter_id": "gmr-xsens-headless-v1",
  "input_kind": "source",
  "source_extension": ".bvh",
  "robot_id": "unitree_g1",
  "start_frame": 0,
  "end_frame": 240,
  "scale": 0.01,
  "reset_to_zero": true
}
```

The output is a candidate NPZ with root pose and robot DoF positions. It is never an
accepted episode until the target-specific FORGE simulator replay passes the locomotion or
whole-body quality profile.

The `do-as-i-do-mujoco-replay-v1` validation adapter consumes a safe tar containing the
scene, referenced meshes and `trajectory_mjwp.npz`. Its output remains a diagnostic; missing
contact metrics or an unapproved target profile fail closed at the deterministic quality
gate.

## Benchmark acceptance

Record for every source and stage: image digest, GPU type, driver/CUDA, input frame count and
duration, peak VRAM/RAM/disk, wall/GPU seconds, output hashes, reconstruction valid ratio,
replay profile, pass/fail reasons and dollar cost. Never convert a successful process exit
into an accepted episode without the independent FORGE quality gate.

The first bounded A40 evidence is tracked under `benchmarks/evidence/`. These records prove
execution and pin the inputs/revisions; they do not constitute customer acceptance tests.
