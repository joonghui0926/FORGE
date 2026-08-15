# FORGE Joonghui·Inseon 역할 및 실행 Handoff

> 상태: 두 사람과 각 담당 에이전트의 실행 기준
> 제품 기준: [제품·기술 아키텍처 Handoff](./HANDOFF_PRODUCT_AND_ARCHITECTURE.md)
> UI 기준: [UI 디자인 시스템 Handoff](./HANDOFF_UI_DESIGN_SYSTEM.md)

## 0. 목적

두 사람이 같은 pipeline을 기다리며 순차적으로 일하지 않도록, FORGE를 명확한 계약으로 나눈다.

- **Joonghui — GPU / Physical Data Compiler Lead**
  인간 영상을 검증된 robot-ready dataset artifact로 바꾸는 data plane의 품질과 재현성을 책임진다.
- **Inseon — Product / Platform / Data Factory Lead**
  고객 주문, Terac 수집, storage, workflow, Band 의사결정, 결제, delivery UI를 연결하는 control plane과 실제 회사 운영 경험을 책임진다.

둘의 통합점은 Python 함수나 임시 폴더가 아니라 다음의 versioned contract다.

```text
Order → Capture → GPU Job → Reconstruction → Skill IR
      → Robot Trajectory → Quality Result → Decision → Delivery
```

이 문서만 받은 에이전트는 담당자를 확인하고 아래의 소유 경로, gate, Definition of Done을 따라 작업한다. 달력이나 시간 추정으로 진척을 정의하지 않고 **검증 gate가 통과했는지**로 정의한다.

## 1. 최종 공동 목표

실제 유료 주문 하나에 대해 다음이 증명되어야 한다.

1. 고객이 task와 robot requirement를 제출하고 Stripe 결제를 완료한다.
2. Band가 구조화된 acquisition plan을 만들고 Render Workflow가 Terac 수집을 실행한다.
3. 실제 작업자가 capture UI를 통해 권리 동의와 함께 영상을 제출한다.
4. 영상이 R2에 immutable raw artifact로 저장된다.
5. RunPod GPU worker가 metric 4D reconstruction, stable contact, Skill IR, robot retarget/replay 결과를 만든다.
6. Pioneer가 learned quality verdict와 다음 촬영 예측을 만들고, Band가 deterministic evidence와 이를 결합해 recollection을 요청한다.
7. source validation을 통과한 demonstration만 증폭된다.
8. 검증된 episode, quality report, provenance, rights, checksum, 표준 export가 고객에게 전달된다.
9. UI나 발표에 표시한 숫자는 실제 DB/artifact에서 계산된다.

## 2. Code ownership

### 2.1 기본 소유 경로

| 경로 | Primary | Reviewer | 설명 |
|---|---|---|---|
| `workers/reconstruction/**` | Joonghui | Inseon | 외부 video reconstruction adapter와 GPU image |
| `workers/contact/**` | Joonghui | Inseon | C2Dex-derived stable-contact compiler |
| `workers/retarget/**` | Joonghui | Inseon | kinematic/heavy robot retargeting |
| `workers/validate/**` | Joonghui | Inseon | source physics/batch quality computation |
| `packages/quality-model/**` | Joonghui | Inseon | Pioneer feature/label 의미와 offline evaluation 기준 |
| `workers/package/**` | Joonghui | Inseon | canonical artifact에서 dataset export 생성 |
| `infra/runpod/**` | Joonghui | Inseon | endpoint image, handler, GPU class config |
| `third_party/**` | Joonghui | Inseon | commit/weight/license lock |
| `apps/web/**` | Inseon | Joonghui | customer, capture, operator, delivery UI |
| `services/api/**` | Inseon | Joonghui | auth, order, artifact metadata, signed URL, webhook |
| `services/workflows/**` | Inseon | Joonghui | Render Workflows DAG와 activity |
| `integrations/**` | Inseon | Joonghui | Terac, Band, Pioneer, R2, Stripe, Linq; RunPod client 포함 |
| `infra/render/**` | Inseon | Joonghui | web/API/workflow/Postgres deployment |
| `packages/ui/**` | Inseon | Joonghui | 디자인 token, primitive, accessibility |
| `packages/db/**` | Inseon | Joonghui | schema/migration/repository |
| `packages/contracts/**` | 공동 | 공동 | JSON Schema, OpenAPI, generated clients |
| `packages/skill-ir/**` | Joonghui | Inseon | 의미·metric은 Joonghui, API/storage compatibility는 Inseon |
| `tests/e2e/**` | 공동 | 공동 | 실제 end-to-end acceptance |
| `HANDOFF_*.md` | 공동 | 공동 | 제품 기준 변경은 두 사람 승인 |

Primary는 구현·테스트·운영 장애의 첫 책임자다. Reviewer는 이름만 올리는 사람이 아니라 자신의 downstream이 실제로 소비할 수 있는지 확인한다.

### 2.2 서로의 경로를 수정하는 규칙

- 긴급하지 않다면 상대 소유 경로를 직접 수정하지 않는다.
- 필요하면 먼저 issue에 `interface mismatch`, 기대 input/output, fixture를 남긴다.
- 작은 호환 patch는 상대를 reviewer로 지정한다.
- 상대가 아직 구현하지 않은 부분은 `packages/contracts` 기반 fake server/fixture로 막지 않고 진행한다.
- mock을 production fallback으로 남기지 않는다.
- contract breaking change는 schema version과 migration plan 없이 merge하지 않는다.

## 3. 공동으로 먼저 고정할 것

### Gate C0 — Product slice

두 사람이 다음을 하나의 issue 또는 decision record에 합의한다.

- 첫 skill과 성공/실패 predicate
- 첫 대상 object instance와 정확한 scale 확보 방법
- target robot/MJCF와 joint limit
- initial coverage matrix
- delivery episode 목표와 실제 검증 threshold
- source/derivative/customer delivery 권리 문구

합의가 없으면 Joonghui는 GPU benchmark용 공개 sample만, Inseon은 synthetic fixture만 사용한다. 서로 다른 실제 task를 임의로 선택하지 않는다.

### Gate C1 — Contract freeze

다음 schema를 `packages/contracts`에 생성한다.

```text
forge.order.v1
forge.capture.v1
forge.gpu-job.v1
forge.gpu-result.v1
forge.reconstruction.v1
forge.skill-ir.v1
forge.robot-trajectory.v1
forge.quality-result.v1
forge.qc-features.v1
forge.pioneer-verdict.v1
forge.decision.v1
forge.delivery.v1
forge.error.v1
```

필수 검증:

- 동일 JSON fixture가 TypeScript와 Python validator 모두에서 통과한다.
- invalid fixture가 동일한 field path와 reason으로 실패한다.
- units, frame convention, enum, nullability가 명시된다.
- schema example이 handoff의 예시와 충돌하지 않는다.
- generated type을 hand-edit하지 않는다.

### Gate C2 — Test artifact set

공동 fixture는 최소 세 종류다.

1. `valid_sample`: 공개 논문 repository sample, 권리와 checksum 기록
2. `real_capture`: FORGE protocol로 촬영한 내부/허용된 영상
3. `known_failure`: occlusion 또는 camera motion이 있어 구조화된 reject가 나와야 하는 영상

raw video를 Git에 넣지 않는다. `tests/fixtures/manifest.json`에 public download 또는 protected R2 test URI, sha256, rights, expected stage 결과를 둔다.

## 4. Joonghui — GPU / Physical Data Compiler Lead

### 4.1 미션

Joonghui는 “논문 demo가 실행된다”에서 끝나지 않고, 임의의 허용된 capture가 **재현 가능하고 versioned된 artifact와 정직한 품질 결과**를 만들도록 책임진다.

### 4.2 책임 범위

#### A. Third-party implementation lock

- VideoManip, Do As I Do와 직접 dependency의 공식 repository를 확인한다.
- full commit SHA, submodule SHA, model weight checksum, model card, license를 lock한다.
- VideoManip에서 공개된 reconstruction과 미공개 grasp/manipulation 범위를 구분한다.
- C2Dex는 공식 code release가 확인되기 전까지 paper-derived module로 표기한다.
- MANO, SAM 계열, object mesh generator, FoundationPose, HaMeR/HaWoR, MoGe, MuJoCo 관련 상업 사용 조건을 ledger에 쓴다.
- `UNKNOWN` 또는 `pending` dependency가 production image에 들어가면 build gate를 실패시킨다.

산출물:

```text
third_party/THIRD_PARTY_LOCK.json
third_party/LICENSE_LEDGER.md
workers/<stage>/Dockerfile
workers/<stage>/README.md
```

#### B. Reproducible GPU images

각 stage image는 다음을 만족한다.

- non-interactive build
- image digest와 build source SHA 기록
- health/smoke command 제공
- input을 presigned HTTPS 또는 local test path로 받을 수 있음
- output은 지정 directory에만 쓰고 manifest를 반환
- weight와 cache가 job 사이의 결과를 오염시키지 않음
- GPU type/driver/CUDA compatibility 문서화
- SIGTERM/timeout에서 partial output을 성공으로 반환하지 않음

권장 image 분리:

```text
forge-reconstruction-videomanip
forge-reconstruction-do-as-i-do
forge-contact-compiler
forge-retarget-fast
forge-retarget-heavy
forge-validate-and-package
```

#### C. Reconstruction adapter

VideoManip official sample을 첫 baseline으로 사용한다.

입력:

- raw video artifact
- object/capture metadata
- pipeline config

출력:

- intrinsics, gravity, depth/pointmap
- hand pose and confidence
- object mesh, scale, SE(3), mask
- invalid/low-confidence frame mask
- preview evidence
- model/config/version manifest

외부 repo의 임시 filename을 계약으로 노출하지 않는다. adapter가 `reconstruction.v1`으로 변환한다.

Do As I Do reconstruction은 같은 계약의 두 번째 provider다. 두 결과를 자동으로 섞기 전에 동일 fixture에 대한 metric과 failure mode를 비교한다.

#### D. Stable-contact compiler

C2Dex에서 가져오는 핵심을 FORGE-owned module로 구현한다.

- hand/object trajectory를 canonical object frame으로 변환
- contact proximity, relative speed, visibility로 후보 생성
- local stable segment 추출
- object-side candidate clustering
- dominant cluster, medoid/barycentric representative, support 계산
- phase segmentation 또는 external phase alignment 지원
- contact uncertainty와 observability 산출
- 2D/3D evidence overlay 생성

테스트:

- global transform을 바꿔도 canonical contact가 유지된다.
- 짧은 tracking outlier가 dominant contact를 크게 이동시키지 않는다.
- 서로 다른 실제 contact phase가 무조건 하나의 cluster로 합쳐지지 않는다.
- occluded interval에서 confidence가 올라가지 않는다.
- meter/millimeter 착오를 schema validator가 잡는다.

#### E. Canonical Skill IR

Joonghui는 다음 의미를 소유한다.

- object canonical frame
- wrist/object relative transforms
- hand configuration representation
- phase와 stable contact set
- gravity와 timing
- uncertainty와 provenance

Inseon이 R2/DB/API에서 저장·조회할 수 있도록 artifact는 JSON manifest + typed array file 조합을 쓴다. 대용량 array를 JSON response에 직접 넣지 않는다.

#### F. Robot retargeting

Fast path:

- target URDF/MJCF parse
- coordinate/scale calibration
- wrist/object/contact objective
- joint/collision/velocity constraint
- deterministic config와 seed
- fast feasibility result

Heavy path:

- Do As I Do의 MuJoCo Warp sampling-based MPC를 먼저 재현
- convex decomposition/MJCF asset generation
- warm-start와 sampling config versioning
- object motion/contact tracking reward breakdown
- perturbation replay
- output trajectory와 replay video/evidence

target hardware가 없는 경우 simulation replay까지만 `verified_simulation`이다. 실제 robot에서 실행하지 않은 결과를 `verified_real`로 표시하지 않는다.

#### G. Source validation과 amplification

Joonghui는 metric을 계산하고 threshold 제안 근거를 남긴다.

- reconstruction continuity
- contact observability/stability
- joint/velocity/collision limit
- object goal error
- penetration/contact loss
- perturbation robustness
- provenance completeness

증폭기는 source validation token 또는 accepted quality result ID를 요구해야 한다. boolean CLI flag로 gate를 우회하지 못하게 한다.

DemoGen-style SE(3) variation을 구현할 때:

- source phase/contact 관계 보존
- 허용 workspace와 object pose distribution 준수
- 모든 generated episode 재검증
- 실패 variation은 별도 reason으로 보존
- source group 단위 split으로 leakage 방지

#### H. Pioneer feature, label, evaluation ownership

Joonghui는 Pioneer API client가 아니라 **모델이 배워야 하는 품질 문제의 의미**를 소유한다.

- capture, reconstruction, contact, retarget, physics metric을 비식별 `qc-features.v1`로 정의
- usable/physics-pass/recollect/operator-review ground-truth label 규칙 정의
- 같은 source/performer/object가 train과 validation에 섞이지 않는 group split
- false accept를 우선 억제하는 offline metric과 calibration 기준 제안
- base, fine-tuned champion, challenger의 held-out 결과 비교
- 모델이 deterministic hard fail을 뒤집지 못하는 policy test
- prediction drift와 recollection lift 분석

Pioneer fine-tuning dataset에 raw video나 PII를 넣지 않는다. label과 구조화 metric은 parent quality run까지 provenance를 가진다.

#### I. RunPod handler

필수 endpoint semantics:

```text
POST async job(request: forge.gpu-job.v1)
GET provider status(provider_job_id)
FORGE callback/result: forge.gpu-result.v1
```

- idempotency key로 중복 제출을 안전하게 처리한다.
- output upload 완료와 checksum 검증 후에만 succeeded를 반환한다.
- provider status를 FORGE error taxonomy로 매핑한다.
- secrets는 environment/secret mount에서 읽는다.
- job payload에 raw API key를 넣지 않는다.

#### J. Compute profiling

fixture와 실제 capture에서 다음 표를 만든다.

| stage | GPU class | VRAM peak | GPU seconds | wall seconds | output bytes | accepted? | failure |
|---|---|---:|---:|---:|---:|---:|---|

이 자료로 여러 24GB급 GPU와 A100 80GB급 heavy pool을 비교한다. 구매 희망이 아니라 accepted source당 비용, OOM, queue throughput으로 선택한다.

### 4.3 Joonghui 우선 backlog

#### P0 — 실제 pipeline을 성립시키는 것

- third-party lock/license ledger
- `gpu-job`, `gpu-result`, `reconstruction`, `skill-ir`, `quality-result` 계약
- VideoManip sample container + adapter
- deterministic smoke fixture
- stable-contact 최소 구현과 evidence
- target MJCF fast retarget
- source quality result
- `qc-features`/`pioneer-verdict` 계약과 labeled fixture
- Pioneer base/fine-tuned model acceptance metric 정의
- RunPod async handler
- R2 input/output integration test

#### P1 — 품질을 올리는 것

- Do As I Do reconstruction comparison
- Do As I Do heavy retarget/replay
- contact-consistent refinement
- perturbation robustness
- object asset/scale cache
- generated SE(3) variants와 batch validation
- LeRobot/RLDS exporter

#### P2 — 근거가 생긴 뒤 확장

- 추가 robot embodiment adapters
- full C2Dex official code 비교 또는 residual policy 연구
- expert task와 multi-object scene
- real robot deployment connector

### 4.4 Joonghui가 책임지지 않는 것

- Terac worker 모집/보상/운영 UI
- Stripe webhook과 결제 UX
- customer auth/tenant management
- Render Workflow 전체 state orchestration
- domain/DNS와 marketing page
- 근거 없는 경쟁사 가격 또는 판매 약속

Joonghui는 필요한 input/output 요구를 contract로 제공하고, Inseon의 구현을 직접 대체하지 않는다.

### 4.5 Joonghui Definition of Done

- fresh GPU worker가 README 명령으로 fixture를 처리한다.
- 동일 digest/config/input은 동일한 schema와 허용 오차 내 결과를 낸다.
- sample뿐 아니라 실제 capture가 success 또는 구조화된 quality rejection을 낸다.
- output artifact마다 checksum, parent, version, unit/frame metadata가 있다.
- 논문 code와 FORGE 독립 구현의 경계가 명확하다.
- 외부 dependency license ledger가 production gate를 통과한다.
- Inseon의 mock 대신 실제 RunPod/R2 path로 한 e2e job이 완료된다.
- GPU profile로 capacity 선택 근거가 있다.

## 5. Inseon — Product / Platform / Data Factory Lead

### 5.1 미션

Inseon은 GPU code를 감싼 데모 사이트가 아니라, 사람이 데이터를 생산하고 품질 실패가 다시 수집으로 연결되며 고객이 결제하고 결과를 받는 **운영 가능한 회사 control plane**을 책임진다.

### 5.2 책임 범위

#### A. Product surface

필수 route:

```text
/
/order/new
/orders/:orderId
/capture/:captureToken
/operator/orders
/operator/orders/:orderId
/operator/review/:qcRunId
/delivery/:deliveryToken
/legal/worker-consent
/legal/dataset-rights
```

필수 사용자 여정:

- 고객: 가치 이해 → task 요구 입력 → quote/pilot 결제 → 진행 상태 → 품질/coverage → delivery
- 작업자: task 이해 → consent → camera/upload 검사 → submission receipt
- operator: queue/실패/비용 확인 → evidence review → 승인/재수집/중단

모든 UI는 [UI 디자인 시스템 Handoff](./HANDOFF_UI_DESIGN_SYSTEM.md)의 색상, typography, layout, card/HR 금지, accessibility 기준을 따른다.

#### B. API와 Postgres

FastAPI는 다음을 제공한다.

- tenant-aware auth와 authorization
- order CRUD와 state transition
- upload/download presigned URL
- capture completion/checksum confirmation
- GPU job submission/result callback
- Stripe webhook
- Terac event/poll result ingestion
- Band decision request/result persistence
- delivery version과 signed access
- metric aggregation endpoint

DB mutation은 append-only event/audit와 함께 transaction으로 처리한다. 브라우저가 원하는 상태로 직접 update하지 못하게 한다.

#### C. Cloudflare R2

- raw, artifacts, private consent, delivery prefix를 분리한다.
- browser direct multipart upload를 지원한다.
- allowed content type, maximum bytes, tenant prefix를 signed policy에 제한한다.
- upload 완료 후 server가 size/checksum을 확인한다.
- CORS는 정확한 app origin과 method/header만 허용한다.
- public bucket으로 고객 원본을 노출하지 않는다.
- delivery download는 만료되는 signed URL을 사용한다.

#### D. Terac integration

Terac MCP/API 실제 capability를 먼저 inventory한다.

- campaign/task 생성
- worker qualification
- instruction와 capture URL 전달
- submission callback 또는 polling
- reject/rework/compensation
- rights/consent metadata

불명확한 부분은 추정 SDK를 만들지 않고 adapter interface + mock server + `ASSUMPTIONS.md`로 격리한다.

Terac task payload는 다음을 포함한다.

- task/phase의 plain-language 설명
- object와 viewpoint bin
- general/expert qualification
- 촬영 전 체크리스트
- secure capture URL/token
- 성공/실패 예시
- 보상/rework/rights 고지

#### E. Render Workflows

핵심 workflow:

```text
order_paid
  → validate_contract
  → request_band_plan
  → create_terac_batch
  → await_or_poll_submissions
  → fan_out_pre_qc
  → fan_out_gpu_reconstruction
  → fan_out_contact_and_fast_retarget
  → fan_out_pioneer_pre_heavy_inference
  → fan_out_heavy_retarget_validate
  → fan_out_pioneer_post_replay_inference
  → aggregate_coverage_and_quality
  → request_band_decision
      ├─ recollect → create_terac_batch
      ├─ review → operator_queue
      ├─ stop → failed_with_evidence
      └─ amplify → fan_out_generation
  → batch_qc
  → package
  → ready
```

activity는 idempotent하고 provider event ID/job ID를 보존한다. Workflow runtime memory에만 상태를 두지 않는다. Render Workflow가 incoming web server라는 전제를 만들지 않는다.

#### F. Band agents

Band에 네 role을 구현한다.

- Dataset Architect
- Collection Controller
- QC Diagnostician
- Delivery Analyst

각 role은 JSON Schema output, policy version, evidence IDs, confidence를 가진다. 자유로운 자연어는 operator summary일 뿐 실제 state transition은 validated enum과 policy guard가 결정한다.

Band가 `RECOLLECT`를 결정할 때 Inseon은 다음을 검증한다.

- 부족한 coverage cell이 실제로 존재하는가
- reason code가 수집으로 해결 가능한가
- budget/worker qualification 경계 안인가
- 동일한 실패 지시를 무한 반복하지 않는가
- 필요한 human approval flag가 있는가

#### G. Pioneer core integration

Pioneer는 초기부터 모든 production capture/source가 거치는 필수 quality specialist다. Inseon은 다음 runtime과 learning lifecycle을 소유한다.

- `integrations/pioneer`의 authenticated API client와 retry/error mapping
- base/open-weight model을 이용한 schema-constrained `pioneer-verdict.v1` inference
- prediction에 project/model/training-job/evaluation/deployment version 저장
- Joonghui가 정의한 label을 JSONL dataset으로 만들고 Pioneer upload flow 실행
- fine-tuning job 생성·상태 polling·checkpoint/deployment 기록
- held-out evaluation 결과를 model registry에 저장
- 합의된 acceptance 기준을 통과한 model만 champion으로 승격
- Band가 deterministic result와 Pioneer verdict를 모두 받도록 workflow 연결

Pioneer가 unavailable이거나 schema-invalid output을 반환하면 workflow는 `LEARNED_QC_PENDING`에 머문다. production에서 base model, 이전 model 또는 rule-only path로 조용히 fallback하지 않는다. manual override는 명시적 operator action과 audit evidence가 있어야 한다.

Pioneer API에는 pseudonymous ID와 구조화 metric/label만 전송한다. raw capture, 얼굴, worker identity, consent 원문, signed R2 URL은 전송하지 않는다.

#### H. Stripe와 BM surface

- pilot Payment Link 또는 Checkout을 order와 연결한다.
- verified webhook만 payment state의 권위로 사용한다.
- webhook replay를 dedupe한다.
- cancellation/refund가 acquisition 시작 전후에 어떤 상태를 만드는지 정의한다.
- UI에서 영상 개수가 아닌 validated output과 권리/provenance의 가치를 설명한다.
- quote field는 source 수, target embodiment, validated episode, custom export, exception review를 분리한다.

live payment, 법인/세금, 환불 문구는 owner 승인 없이 임의 활성화하지 않는다.

#### I. Operator console

operator가 한 화면에서 다음을 판단할 수 있어야 한다.

- 주문 상태와 누가/무엇이 기다리는지
- coverage matrix
- funnel count와 비용
- capture/reconstruction/contact/replay evidence
- quality reason code와 confidence
- Pioneer usable/physics-pass score, model version, calibration/evaluation 상태
- Band 결정과 근거
- retry/reprocess/recollect/stop/approve action
- 모든 manual action의 audit trail

검토 UI는 예쁜 video player만 만들지 않는다. 원본/overlay/replay, phase, metric, threshold, lineage를 함께 보여준다.

#### J. Delivery와 고객 소유권

- immutable delivery version 생성
- checksum과 loader smoke test 표시
- rights profile과 dataset card 표시
- standard/custom export 선택
- 만료되는 download link
- known limitation과 rejected count 공개
- 재생성 시 새 semantic version과 lineage 연결

#### K. Domain, security, observability

- Cloudflare DNS와 TLS
- production/staging 분리
- secrets를 Render/RunPod/Cloudflare secret store에 주입
- tenant authorization tests
- structured logs와 request/job correlation ID
- error/queue/payment/GPU cost dashboard
- media/PII를 telemetry에 넣지 않음

### 5.3 Inseon 우선 backlog

#### P0 — 실제 회사 loop를 성립시키는 것

- repository web/API/workflow skeleton
- order/capture/job/quality/delivery DB schema
- R2 presigned direct upload
- capture UI와 consent
- GPU mock server와 contract test
- Render Workflow state machine
- Terac adapter + 실제 capability inventory
- Band schema-valid acquisition/recollection decision
- Pioneer base-model inference, verdict schema validation, model registry
- Stripe test payment/webhook
- operator order/coverage/quality view

#### P1 — production 품질

- 실제 RunPod adapter swap
- Terac real campaign/submission
- replay evidence review UI
- recollection loop
- labeled QC dataset → Pioneer fine-tuning → held-out evaluation → champion promotion
- signed delivery portal
- domain/TLS/staging-production setup
- audit/security/tenant isolation tests
- funnel/cost/quality dashboard
- cohort A/B before-after view

#### P2 — 근거가 생긴 뒤 확장

- Linq expert recollection
- Replay richer visual QA
- Superserve custom transformation sandbox
- self-serve quote 범위 확대
- CRM/contract automation
- multi-tenant enterprise admin

### 5.4 Inseon이 책임지지 않는 것

- model architecture와 weight 선택
- hand/object reconstruction metric의 과학적 타당성
- stable-contact algorithm implementation
- MuJoCo retarget reward와 GPU performance kernel
- quality threshold를 통과시키기 위한 metric 조작
- 공개되지 않은 논문 code를 임의로 재구성해 공식 구현이라고 주장하는 것

Inseon은 제품 요구와 evidence 소비 형식을 contract로 제공하고 Joonghui의 quality result를 임의로 성공 처리하지 않는다.

### 5.5 Inseon Definition of Done

- 고객/작업자/operator 세 journey가 실제 환경에서 이어진다.
- raw media가 API server를 통과하지 않고 R2에 안전하게 올라간다.
- workflow retry가 주문, 결제, Terac task, GPU job을 중복 생성하지 않는다.
- Band output이 schema-invalid이면 state가 바뀌지 않는다.
- Pioneer는 모든 production source에 versioned verdict를 만들고, unavailable/schema-invalid이면 fail-closed한다.
- fine-tuned model은 held-out evaluation과 promotion audit를 가진다.
- actual Terac submission 또는 명확히 표기된 provider limitation evidence가 있다.
- Stripe verified webhook이 paid order를 만든다.
- 실제 Joonghui worker를 mock 변경 없이 호출한다.
- failure/recollection/ready 상태를 UI에서 정확히 설명한다.
- delivery가 권리, checksum, metric, provenance를 포함한다.
- UI가 디자인 handoff와 접근성 QA를 통과한다.

## 6. 의존성 매트릭스와 mock contract

| Consumer | Provider | 필요한 것 | 기다리지 않고 쓰는 대체물 | 대체물 제거 gate |
|---|---|---|---|---|
| Joonghui | Inseon | R2 signed GET/PUT | local file adapter + MinIO/recorded HTTP fixture | RunPod-R2 integration 통과 |
| Joonghui | Inseon | target order/capture metadata | versioned JSON fixture | actual paid order artifact 통과 |
| Joonghui | Inseon | target robot asset | agreed public/test MJCF | customer asset review 완료 |
| Inseon | Joonghui | GPU job result | schema-valid fake GPU server | actual RunPod job 통과 |
| Inseon | Joonghui | evidence previews | golden PNG/MP4 fixture | actual reconstruction evidence 통과 |
| Inseon | Joonghui | quality/reason codes | fixed pass/fail/occlusion fixtures | real capture results 통과 |
| Inseon | Joonghui | Pioneer feature/label/evaluation semantics | versioned labeled QC fixture | real physics/operator labels 통과 |
| Inseon | Terac | campaign/submission API | mock provider adapter | real task submission 통과 |
| Inseon | Pioneer | inference/training/evaluation API | schema-valid simulated provider | actual Pioneer base-model verdict 통과 |
| Inseon | Band | structured decision | deterministic rule fixture | live schema-valid decision 통과 |

Mock 규칙:

- fixture에는 `simulation: true`와 producer `forge-fixture`가 있다.
- UI에서 fixture metric은 실제 결과와 같은 색/라벨로 보이지 않는다.
- production environment에서 fixture provider가 선택되면 startup 또는 deployment가 실패한다.
- e2e suite는 mock path와 actual sandbox path를 별도 test로 가진다.

## 7. 공동 의사결정 권한

| 결정 | DRI | 필수 승인/협의 |
|---|---|---|
| GPU/model/reconstruction 선택 | Joonghui | Inseon이 비용·제품 영향 review |
| Skill IR/contact 의미 | Joonghui | Inseon이 storage/API compatibility review |
| 고객 flow/capture UX | Inseon | Joonghui가 technical observability review |
| Terac/Band/Pioneer/Render integration | Inseon | Joonghui가 input·label·quality contract review |
| DB와 state machine | Inseon | Joonghui가 GPU retry/idempotency review |
| quality metric 계산 | Joonghui | Inseon이 고객 설명과 사업 영향 review |
| Pioneer feature/label/evaluation 기준 | Joonghui | Inseon이 API·운영·비용 영향 review |
| Pioneer model deployment/promotion | 공동 | held-out evaluation과 rollback evidence 필요 |
| delivery acceptance threshold | 공동 | calibration evidence 필요 |
| schema breaking change | 공동 | version/migration/fixtures 필요 |
| budget/GPU class/live spend | 공동 | profile과 guardrail 필요 |
| rights/privacy/customer claim | 공동 | 필요 시 법률 검토 issue |
| UI token/layout | Inseon | Joonghui가 operator technical readability review |

둘이 합의하지 못했을 때 quality gate를 낮춰 진행하지 않는다. 가장 작은 reversible experiment와 decision record로 판단 근거를 만든다.

## 8. GitHub 작업 규칙

### 8.1 Branch와 PR

- Joonghui: `joonghui/gpu-<scope>`
- Inseon: `inseon/platform-<scope>`
- 공동 schema: `contracts/<scope>`
- 긴급 수정: `fix/<scope>`

PR은 하나의 검증 가능한 변화만 담는다. 큰 vendor repository dump와 FORGE adapter를 같은 diff에 섞지 않는다.

### 8.2 PR 본문 필수 항목

```markdown
## Outcome
사용자/파이프라인에서 무엇이 가능해졌는가

## Contract impact
추가/변경된 schema와 backward compatibility

## Evidence
실행 명령, test 결과, artifact ID, screenshot 또는 metric

## Production truth
actual / sandbox / simulated 중 무엇인가

## Cost and security
GPU/API 비용 변화, secret/PII/license 영향

## Failure behavior
실패가 어떤 code/state/evidence로 나타나는가

## Handoff dependency
상대 담당자가 다음으로 연결할 정확한 input/output
```

### 8.3 Commit과 review

- commit은 의도를 설명한다. `update`, `fix stuff`를 쓰지 않는다.
- generated file은 source schema와 함께 commit한다.
- raw video, model weight, secret, presigned URL을 commit하지 않는다.
- test를 실행하지 못했으면 이유와 대체 evidence를 적는다.
- contract, state machine, quality threshold, third-party license, payment/rights 변경은 상대 review 없이 merge하지 않는다.
- branch 보호와 CODEOWNERS를 repository skeleton gate에서 추가한다.

권장 CODEOWNERS 의도:

```text
/workers/                 @Joonghui-reviewer
/infra/runpod/            @Joonghui-reviewer
/third_party/             @Joonghui-reviewer
/apps/web/                @Inseon-reviewer
/services/                @Inseon-reviewer
/integrations/            @Inseon-reviewer
/infra/render/            @Inseon-reviewer
/packages/contracts/      @Joonghui-reviewer @Inseon-reviewer
/HANDOFF_*.md             @Joonghui-reviewer @Inseon-reviewer
```

실제 GitHub username을 확인한 뒤 placeholder를 교체한다.

## 9. Integration gate

### Gate I0 — Skeleton and contracts

- 목표 directory와 package tooling 존재
- schema/generator/fixture tests 통과
- web과 GPU fake server가 같은 `gpu-job/result`로 통신
- CI가 lint/type/test/schema drift를 검사

### Gate I1 — Ingestion

- capture UI → R2 → DB artifact
- consent/rights/checksum 검증
- 실제 또는 sandbox Terac submission이 capture record로 변환
- known-failure capture가 GPU 이전에 reason code를 가짐

### Gate I2 — GPU sample

- Render Workflow → actual RunPod reconstruction → R2 artifact → DB callback
- sample output의 schema, checksum, provenance 통과
- operator UI가 evidence를 표시
- retry가 중복 reconstruction을 만들지 않음

### Gate I3 — Real source

- FORGE protocol real capture가 Skill IR과 target robot trajectory 생성
- source validation pass 또는 evidence 있는 fail
- actual Pioneer endpoint가 versioned `pioneer-verdict`를 생성
- deterministic hard gate와 Pioneer verdict가 충돌해도 hard gate가 유지됨
- failure는 infrastructure failure와 quality failure로 구분
- 실제 measured funnel에 반영

### Gate I4 — Recollection

- Band가 deterministic metric과 Pioneer verdict를 받아 결손 cell/reason을 구조화된 decision으로 반환
- Render가 Terac에 새로운 capture instruction을 발행
- original fail → decision → new capture → new result lineage 완전
- 실제 label dataset, Pioneer fine-tuning job, held-out evaluation과 champion promotion audit 존재
- cohort A/B 개선 metric 계산

### Gate I5 — Paid delivery

- verified Stripe payment
- source-approved amplification
- batch QC와 coverage
- rights/checksum/provenance/export loader
- signed customer download와 immutable version
- 실제 결과 기반 product/pitch 화면

한 gate가 실패하면 뒤 stage를 demo용 hard-code로 성공시키지 않는다. 사용할 수 있는 앞 gate의 실제 결과와 다음 blocker를 명확히 보여준다.

## 10. Handoff 보고 형식

상대에게 넘길 때 다음 형식을 그대로 사용한다.

```markdown
# Handoff: <component>

## Status
ready | partial | blocked | failed

## Production truth
actual | sandbox | simulated

## Input contract
schema version, fixture/artifact ID, required env vars

## Output contract
schema version, artifact kinds, example IDs

## How to run
exact commands and expected terminal result

## Evidence
tests, metrics, screenshots, checksum, provider job ID

## Failure behavior
error/reason codes and retryability

## Known limitations
license, data, model, provider, security boundaries

## Required action from recipient
one concrete integration action and acceptance condition
```

“끝났음” 또는 chat 설명만으로 handoff하지 않는다. repository artifact, contract, command, evidence가 있어야 한다.

## 11. Blocker 처리

### Joonghui blocker 예시

- 공식 repository/weight 접근 불가
- license pending
- GPU OOM 또는 provider capacity
- target robot asset/scale 부재
- 실제 capture가 논문 가정을 반복적으로 위반

처리:

1. exact command/error와 최소 reproduction을 남긴다.
2. infra, input, model, quality, license 중 하나로 분류한다.
3. 같은 계약을 지키는 허용된 대체 baseline을 제안한다.
4. quality claim을 낮추거나 fake pass로 진행하지 않는다.

### Inseon blocker 예시

- Terac 외부 upload/event API 불명확
- Band output retention/schema 불명확
- Pioneer model catalog/inference/training/evaluation API 또는 account access 불명확
- Stripe live/legal account 미승인
- Cloudflare domain/account access 부재
- actual GPU endpoint 미준비

처리:

1. provider capability evidence와 미확정 가정을 기록한다.
2. adapter interface와 deterministic sandbox를 만든다.
3. UI에 `simulated` truth를 유지한다.
4. 실제 provider gate의 acceptance test를 미리 작성한다.

공통으로 외부 계정 권한이나 live spend가 필요하면 작업 범위를 몰래 확장하지 않고 owner 승인 issue로 올린다.

## 12. 에이전트별 시작 프롬프트

### Joonghui 역할을 맡은 에이전트

```text
당신은 FORGE의 Joonghui 역할, GPU / Physical Data Compiler Lead다.
HANDOFF_PRODUCT_AND_ARCHITECTURE.md, HANDOFF_TEAM_OWNERSHIP.md,
HANDOFF_UI_DESIGN_SYSTEM.md와 현재 repository/issue/PR을 먼저 읽어라.

workers/**, infra/runpod/**, third_party/**, packages/skill-ir/**와
packages/quality-model/**의 기술 의미를
소유한다. 가장 앞의 미통과 integration gate를 찾고, 먼저 계약과 fixture를
검증한 뒤 하나의 end-to-end vertical을 완성하라.

논문 기술은 공식 repository/commit/license를 확인해 pin하고, 공개되지 않은
부분은 FORGE paper-derived 구현으로 표시하라. 실제로 실행하지 않은 stage를
passed로 기록하지 마라. 모든 output에 unit, frame, checksum, parent provenance,
model/config/container version을 넣어라.

작업 완료 시 exact command, test result, artifact 종류, metric, production truth,
failure behavior, Inseon이 연결할 input/output을 PR과 handoff 형식으로 남겨라.
```

### Inseon 역할을 맡은 에이전트

```text
당신은 FORGE의 Inseon 역할, Product / Platform / Data Factory Lead다.
HANDOFF_PRODUCT_AND_ARCHITECTURE.md, HANDOFF_TEAM_OWNERSHIP.md,
HANDOFF_UI_DESIGN_SYSTEM.md와 현재 repository/issue/PR을 먼저 읽어라.

apps/web/**, services/**, integrations/**, infra/render/**, packages/db/**,
packages/ui/**를 소유한다. 고객 주문부터 Terac capture, R2, Render Workflow,
Pioneer learned-quality verdict, Band decision, RunPod, Stripe, delivery까지 가장
앞의 미통과 gate를 완성하라.

GPU가 준비되지 않았으면 versioned fake server로 계약을 구현하되 모든 화면과
event에 simulated를 표시하고 실제 provider gate가 통과하면 제거하라. UI는
#F8F5EB 배경, #00ABC2 primary, 14–16px 이상의 읽기 쉬운 본문, 과도한 card/HR
금지를 포함한 UI handoff를 그대로 지켜라.

작업 완료 시 exact command, test result, 실제/sandbox/simulated 구분, state와
idempotency evidence, 보안·비용 영향, Joonghui가 제공하거나 소비할 정확한
input/output을 PR과 handoff 형식으로 남겨라.
```

## 13. 공동 최종 체크리스트

- [ ] 첫 skill contract와 target robot가 확정되었다.
- [ ] 모든 schema가 TS/Python에서 검증된다.
- [ ] third-party commit/weight/license가 lock되었다.
- [ ] Terac에서 실제 사람 submission이 들어왔다.
- [ ] R2 direct upload와 checksum이 검증되었다.
- [ ] Render Workflow가 actual RunPod job을 orchestration했다.
- [ ] reconstruction → stable contact → Skill IR이 실제 artifact를 만들었다.
- [ ] retarget/replay가 pass 또는 증거 있는 fail을 냈다.
- [ ] 모든 production source에 actual Pioneer model/evaluation lineage가 있는 verdict가 있다.
- [ ] 실제 label로 Pioneer fine-tuning/evaluation/promotion loop가 실행되었다.
- [ ] quality fail이 Pioneer verdict, Band decision과 Terac recollection으로 연결되었다.
- [ ] accepted source만 증폭되었다.
- [ ] generated episode가 batch QC를 다시 통과했다.
- [ ] Stripe verified payment와 order가 연결되었다.
- [ ] delivery에 rights, quality, provenance, checksum, loader test가 있다.
- [ ] UI가 지정 색상·typography·layout·접근성 기준을 통과했다.
- [ ] demo의 모든 수치가 실제 query/artifact에서 계산된다.
- [ ] secret, customer media, weight가 Git history에 없다.
