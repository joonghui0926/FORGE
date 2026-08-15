# Third-party license ledger

This ledger is an execution gate, not a bibliography. A paper result is not permission
to redistribute its code, weights, models, or datasets.

| Dependency | Intended use | Current truth | Production gate |
|---|---|---|---|
| VideoManip and transitive models | Manipulation reconstruction adapter | Evaluation only; exact commit and all transitive terms unresolved | Legal/technical review and digest-pinned image |
| MoGe 2 + ViT-L checkpoint | Monocular metric depth and camera intrinsics | Official Microsoft source, HF revision, 1.323 GB model and SHA-256 pinned; code/model chain remains evaluation only | Validate metric scale on calibrated FORGE scenes and approve DINOv2/model-card terms |
| C2Dex | Algorithmic reference for stable contact | FORGE reimplements the described geometry; no C2Dex code is vendored | Benchmark FORGE implementation on held-out tasks |
| Do As I Do / HaWoR path | Heavy-retarget comparison | Evaluation only; redistribution/commercial terms unresolved | Replace or obtain written commercial rights |
| MANO v1.2 | Hand model asset loaded from `MANO_MODEL_DIR` | Local licensed asset; not committed | Confirm commercial terms and inject as a runtime secret volume |
| GMR | Whole-body human/humanoid motion retargeting | MIT top-level repository pinned; dependent robot assets/datasets separate | Per-target asset review and held-out retarget/replay benchmark |
| ASAP | Whole-body physics alignment and sim-to-real candidate | Evaluation only | Dependency/weight/robot SDK review and real-robot evidence |
| InterMimic | Whole-body object-interaction benchmark/candidate | Evaluation only | Dependency review and FORGE profile benchmark |
| Pioneer | Structured learned QC | Fixture only in this repository | Authenticated provider schema, evaluation, and champion promotion |
| Whole-body reconstruction | Locomotion/general motion input | Capability slot exists, provider unresolved | Pin commercially usable implementation and pass profile benchmarks |

Production must fail closed when `THIRD_PARTY_LOCK.json` does not mark every required
capability `approved`. Never put weights, `.pkl` model files, raw customer media,
presigned URLs, or tokens in Git.
