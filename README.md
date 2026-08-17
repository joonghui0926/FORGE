# FORGE Physical Data Compiler

FORGE turns a customer task contract and purpose-built physical-behavior observations
into a versioned, claim-scoped robotics training dataset. Sources can be human video, another robot's state,
teleoperation, multimodal capture, or simulation. The product is not a raw-video
marketplace: it plans collection, reconstructs metric actor/counterpart interaction,
compiles stable counterpart-side contacts, retargets them to a customer embodiment,
validates replay, and only then amplifies and packages accepted sources.

## Four core operating platforms

Terac, Band, Pioneer, and Render are not sponsor badges around the product. Together they
form the operating loop that lets a two-person company deliver production-grade physical
AI data. FORGE owns the contracts, compiler, deterministic gates, provenance, and customer
dataset; each platform owns one deliberately narrow part of the business.

| Platform | Core role in FORGE | Why it is business-critical | Canonical code boundary |
| --- | --- | --- | --- |
| **Terac** | Recruits qualified experts or general workers and executes an approved capture campaign. | It converts a robot-skill specification into new, rights-cleared physical evidence. Without Terac, FORGE has a compiler but no scalable acquisition engine. | `src/forge/integrations/terac/` |
| **Band** | Produces structured collection plans and diagnoses quality failures into recollect, review, accept, or block decisions. | It is the operating intelligence that closes coverage gaps without making every order a manual consulting project. | `src/forge/integrations/band/` |
| **Pioneer** | Predicts source usability and replay quality from pseudonymous structured metrics, then learns from validated outcomes. | It turns accumulated labels into FORGE's compounding quality moat while deterministic safety and physics gates remain authoritative. | `src/forge/integrations/pioneer/` |
| **Render** | Hosts the customer control plane, Postgres system of record, audit trail, and durable task orchestration. | It makes the company reliable: retries, state transitions, callbacks, and evidence survive process restarts and provider delays. | `src/forge/integrations/render/`, `services/workflows/` |

The production loop is intentionally explicit:

```text
customer contract
  -> Band collection plan
  -> Terac acquisition campaign
  -> RunPod FORGE compiler + deterministic validation
  -> Pioneer learned quality verdict
  -> Band final operating decision
  -> Render durable state, audit, retry, and delivery orchestration
```

RunPod and Cloudflare R2 are the GPU and object-storage data plane. They are essential
infrastructure, but they do not decide what to collect or what is safe to deliver.

The Python package in `src/forge` is the core compiler boundary. Paper and
vendor repositories remain external, pinned adapters. FORGE owns the contracts,
stable-contact compiler, Canonical Skill IR, quality gates, augmentation authorization,
provenance, and delivery format.

## Customer workspace

The authenticated order workspace is backed by the Postgres system of record rather than
demo placeholders. It exposes Terac campaign batches and capture progress, Render and
RunPod execution, deterministic and Pioneer/Band quality evidence, lineage-safe episodes,
the immutable delivery manifest, expiring R2 dataset downloads, the audit timeline, and
payment/rights status. Empty views describe the next production gate; no tab is marked
"coming soon."

## Repository layout

```
FORGE/
├── apps/
│   └── web/                    # Next.js customer-facing app (TypeScript)
│       ├── app/                # App Router pages: landing, orders, pricing, auth
│       ├── components/         # UI components: layout, orders, shared primitives
│       ├── lib/                # API client, server utilities, shared types
│       └── __tests__/          # Vitest unit and component tests
│
├── packages/                   # Shared TypeScript packages (pnpm workspaces)
│   ├── contracts/              # JSON Schema definitions + validator for all Forge contracts
│   ├── db/                     # Postgres client and SQL migration files
│   ├── ui/                     # Design tokens, primitives, pattern components (in progress)
│   ├── observability/          # Shared logging/tracing helpers (in progress)
│   └── skill-ir/               # Canonical Skill IR TypeScript types (in progress)
│
├── services/                   # Backend services
│   ├── api/                    # FastAPI Python REST service (orders, captures, deliveries)
│   └── workflows/              # Durable task orchestration worker (Band/Pioneer decisions)
│
├── src/forge/                  # Python compiler boundary (contracts, stages, integrations)
│   ├── modules/                # Pipeline stages: collection, reconstruction, retarget,
│   │                           #   stable_contact, amplification, validation, packaging
│   ├── adapters/papers/        # Pinned external paper adapters (GMR, DoAsIDo, TWIST, etc.)
│   ├── integrations/           # Platform clients: Terac, Band, Pioneer, Render, RunPod, R2
│   ├── contracts/              # Python codec and models for Forge JSON contracts
│   └── business/               # Pricing and business logic
│
├── workers/                    # RunPod GPU worker entrypoints and per-stage handlers
│
├── scripts/                    # One-off operational scripts (benchmarks, R2 checks, replays)
│
├── tests/                      # Python unit tests for the compiler and pipeline
│
├── benchmarks/                 # Benchmark run evidence (JSON) and benchmark README
│
├── infra/                      # Infrastructure config: R2 CORS, Render YAML, RunPod Dockerfile
│
├── docs/                       # Architecture docs, pricing model, integration notes
│   └── superpowers/            # AI-generated specs and implementation plans
│
└── third_party/                # License ledger and upstream patch files
```

**Monorepo tooling:** TypeScript apps and packages use pnpm workspaces with a shared
`tsconfig.base.json`. Python code uses a `pyproject.toml`-managed package (`src/forge`) with
per-service virtual environments under `services/api/.venv`.

## Local verification

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python scripts/run_fixture_pipeline.py
```

The fixture is deliberately marked `simulation=true`. Production mode rejects fixture
Pioneer verdicts, unvalidated replay, missing rights, and unapproved third-party
dependencies.

Read these before changing the product contract:

- `HANDOFF_PRODUCT_AND_ARCHITECTURE.md`
- `HANDOFF_TEAM_OWNERSHIP.md`
- `docs/JOONGHUI_COMPILER.md` — compiler architecture and design decisions
- `docs/PRICING_AND_UNIT_ECONOMICS.md`
- `third_party/LICENSE_LEDGER.md`

Provider-specific code and ownership rules are summarized in
`src/forge/integrations/README.md`.
