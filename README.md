# FORGE Physical Data Compiler

FORGE turns a customer task contract and purpose-built physical-behavior observations
into a versioned, robot-ready dataset. Sources can be human video, another robot's state,
teleoperation, multimodal capture, or simulation. The product is not a raw-video
marketplace: it plans collection, reconstructs metric actor/counterpart interaction,
compiles stable counterpart-side contacts, retargets them to a customer embodiment,
validates replay, and only then amplifies and packages accepted sources.

The Python package in `src/forge` is the Joonghui-owned compiler boundary. Paper and
vendor repositories remain external, pinned adapters. FORGE owns the contracts,
stable-contact compiler, Canonical Skill IR, quality gates, augmentation authorization,
provenance, and delivery format.

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
