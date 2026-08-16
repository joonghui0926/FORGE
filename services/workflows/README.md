# FORGE Render workflow service

Render is the durable coordinator, not the business-decision engine. The workflow records
every transition and provider request in Postgres, invokes the matching adapter, waits for
signed callbacks, and resumes from durable state.

```text
order_paid
  -> validate_contract
  -> request_band_collection_plan
  -> create_terac_campaign
  -> fast_pre_qc
  -> request_pioneer_pre_qc
  -> submit_runpod_gpu_job
  -> deterministic_validation
  -> request_pioneer_final_verdict
  -> request_band_quality_decision
     -> package_dataset | create_terac_campaign | operator_queue | close_with_evidence
```

Code map:

- `src/tasks.py`: visible DAG and state-routing policy.
- `src/runtime.py`: durable state, idempotency, and effect coordination.
- `src/decision.py`: schema-constrained Band action routing.
- `src/forge/integrations/{terac,band,pioneer,render}`: provider HTTP boundaries.

Render Workflows are created separately from the Blueprint because Render currently does
not support Workflow resources in `render.yaml`. The web, API, and Postgres resources stay
Blueprint-managed; this workflow service is linked to the same repository and branch from
the Render Workflows dashboard or CLI.
