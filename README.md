# FORGE Physical Data Compiler

FORGE turns a customer task contract and purpose-built physical-behavior observations
into a versioned, robot-ready dataset. Sources can be human video, another robot's state,
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

The Python package in `src/forge` is the Joonghui-owned compiler boundary. Paper and
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
- `docs/JOONGHUI_COMPILER.md`
- `docs/PRICING_AND_UNIT_ECONOMICS.md`
- `third_party/LICENSE_LEDGER.md`

Provider-specific code and ownership rules are summarized in
`src/forge/integrations/README.md`.
