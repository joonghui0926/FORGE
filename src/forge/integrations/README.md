# External platform boundaries

These adapters are narrow I/O boundaries. They do not own FORGE order state, physics
truth, rights policy, or delivery acceptance. Every outbound request is persisted by the
Render workflow runtime with an idempotency key and correlation ID before effects are
applied.

| Order | Platform package | Accepts | Returns | Must never do |
| --- | --- | --- | --- | --- |
| 1 | `terac/` | Approved collection plan | Campaign and submission identifiers | Define quality or become the raw-data source of truth |
| 2 | `band/` | Order/coverage evidence | Schema-constrained operating decision | Call Terac/RunPod directly or mutate order state |
| 3 | `pioneer/` | Pseudonymous structured QC features | Versioned learned-quality verdict | Receive raw media or override a deterministic hard failure |
| 4 | `render/` | Task name and versioned input contract | Durable task-run identifier | Contain provider-specific business policy |

Supporting boundaries:

- `runpod/`: executes FORGE compiler stages against R2 artifacts.
- `r2/`: private immutable object storage and artifact integrity.
- `papers/`: pinned adapters around research code; FORGE contracts remain stable.

## Runtime ownership

- `services/api/` receives authenticated customer/provider callbacks and dispatches tasks.
- `services/workflows/` is the Render workflow DAG and durable effect coordinator.
- `src/forge/modules/` contains platform-independent FORGE compiler and quality logic.
- `packages/contracts/` is the language-neutral contract boundary.

Provider credentials are read only by the matching adapter. Tests inject an `httpx`
client, so no test silently reaches a live sponsor API.
