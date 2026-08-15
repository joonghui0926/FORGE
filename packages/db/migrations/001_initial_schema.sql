-- FORGE initial schema
-- All IDs are application-generated prefixed strings (e.g. ord_, cap_)
-- R2 URIs are storage locations only — never used as primary keys
-- All state changes append to audit_events in the same transaction

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Tenants ──────────────────────────────────────────────────────────────────

CREATE TABLE tenants (
  id          TEXT PRIMARY KEY,              -- ten_...
  slug        TEXT NOT NULL UNIQUE,
  name        TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Orders ───────────────────────────────────────────────────────────────────

CREATE TYPE order_state AS ENUM (
  'DRAFT', 'PAID', 'PLANNING', 'ACQUIRING', 'PRE_QC',
  'PROCESSING', 'CONTACTING', 'RETARGETING', 'VALIDATING',
  'RECOLLECTING', 'AMPLIFYING', 'BATCH_QC', 'PACKAGING',
  'READY', 'CANCELLED', 'FAILED'
);

CREATE TABLE dataset_orders (
  id                    TEXT PRIMARY KEY,   -- ord_...
  tenant_id             TEXT NOT NULL REFERENCES tenants(id),
  state                 order_state NOT NULL DEFAULT 'DRAFT',
  skill_name            TEXT NOT NULL,
  contract              JSONB NOT NULL,     -- forge.order.v1
  stripe_payment_intent TEXT UNIQUE,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_tenant ON dataset_orders(tenant_id);
CREATE INDEX idx_orders_state  ON dataset_orders(state);

-- ─── Capture Batches ──────────────────────────────────────────────────────────

CREATE TABLE capture_batches (
  id           TEXT PRIMARY KEY,            -- bat_...
  order_id     TEXT NOT NULL REFERENCES dataset_orders(id),
  sequence     INTEGER NOT NULL,
  decision_id  TEXT,                        -- dec_... reference (nullable for first batch)
  terac_campaign_id TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (order_id, sequence)
);

-- ─── Demonstrations ───────────────────────────────────────────────────────────

CREATE TYPE demonstration_state AS ENUM (
  'SUBMITTED', 'PRE_QC_PASSED', 'PRE_QC_FAILED',
  'RECONSTRUCTION_QUEUED', 'RECONSTRUCTION_COMPLETE',
  'VALIDATION_PASSED', 'VALIDATION_FAILED'
);

CREATE TABLE demonstrations (
  id                  TEXT PRIMARY KEY,     -- cap_...
  order_id            TEXT NOT NULL REFERENCES dataset_orders(id),
  batch_id            TEXT NOT NULL REFERENCES capture_batches(id),
  worker_subject_id   TEXT NOT NULL,        -- pseudonymous sub_...
  state               demonstration_state NOT NULL DEFAULT 'SUBMITTED',
  video_r2_key        TEXT NOT NULL,
  sha256              TEXT NOT NULL,
  mime_type           TEXT NOT NULL,
  object_id           TEXT NOT NULL,
  viewpoint_bin       TEXT NOT NULL,
  consent_r2_key      TEXT NOT NULL,
  declared_rights     TEXT[] NOT NULL,
  submitted_at        TIMESTAMPTZ NOT NULL,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_demo_sha256_tenant ON demonstrations(sha256, order_id);
CREATE INDEX idx_demo_order ON demonstrations(order_id);
CREATE INDEX idx_demo_batch ON demonstrations(batch_id);

-- ─── QC Runs ──────────────────────────────────────────────────────────────────

CREATE TABLE qc_runs (
  id              TEXT PRIMARY KEY,         -- qc_...
  order_id        TEXT NOT NULL REFERENCES dataset_orders(id),
  subject_id      TEXT NOT NULL,
  subject_type    TEXT NOT NULL,
  stage           TEXT NOT NULL,
  passed          BOOLEAN NOT NULL,
  reason_codes    TEXT[] NOT NULL DEFAULT '{}',
  metrics         JSONB NOT NULL DEFAULT '{}',
  thresholds      JSONB NOT NULL DEFAULT '{}',
  evidence_r2_keys TEXT[] NOT NULL DEFAULT '{}',
  config_hash     TEXT NOT NULL,
  simulation      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_qc_subject_stage_config ON qc_runs(subject_id, stage, config_hash);
CREATE INDEX idx_qc_order ON qc_runs(order_id);

-- ─── GPU Jobs ─────────────────────────────────────────────────────────────────

CREATE TYPE gpu_job_status AS ENUM (
  'PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'QUALITY_INSUFFICIENT'
);

CREATE TABLE gpu_jobs (
  id               TEXT PRIMARY KEY,        -- job_...
  idempotency_key  TEXT NOT NULL UNIQUE,
  order_id         TEXT NOT NULL REFERENCES dataset_orders(id),
  stage            TEXT NOT NULL,
  attempt          INTEGER NOT NULL DEFAULT 1,
  status           gpu_job_status NOT NULL DEFAULT 'PENDING',
  container_image  TEXT NOT NULL,
  pipeline_version TEXT NOT NULL,
  input_r2_keys    TEXT[] NOT NULL,
  output_r2_prefix TEXT NOT NULL,
  provider_job_id  TEXT,
  error_code       TEXT,
  error_message    TEXT,
  gpu_seconds      NUMERIC,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at     TIMESTAMPTZ
);

CREATE INDEX idx_gpu_jobs_order ON gpu_jobs(order_id);
CREATE INDEX idx_gpu_jobs_status ON gpu_jobs(status);

-- ─── Artifacts ────────────────────────────────────────────────────────────────

CREATE TABLE artifacts (
  id              TEXT PRIMARY KEY,         -- art_...
  tenant_id       TEXT NOT NULL REFERENCES tenants(id),
  order_id        TEXT REFERENCES dataset_orders(id),
  kind            TEXT NOT NULL,
  r2_key          TEXT NOT NULL,
  sha256          TEXT NOT NULL,
  size_bytes      BIGINT,
  schema_version  TEXT,
  producer        TEXT,
  simulation      BOOLEAN NOT NULL DEFAULT FALSE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, sha256, kind)
);

CREATE INDEX idx_artifacts_order ON artifacts(order_id);

-- ─── Provenance Edges ─────────────────────────────────────────────────────────

CREATE TABLE provenance_edges (
  parent_id  TEXT NOT NULL,
  child_id   TEXT NOT NULL,
  relation   TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (parent_id, child_id, relation)
);

-- ─── Reconstructions ──────────────────────────────────────────────────────────

CREATE TABLE reconstructions (
  id                   TEXT PRIMARY KEY,    -- rec_...
  demonstration_id     TEXT NOT NULL REFERENCES demonstrations(id),
  job_id               TEXT NOT NULL REFERENCES gpu_jobs(id),
  pipeline_version     TEXT NOT NULL,
  frame_count          INTEGER NOT NULL,
  artifact_id          TEXT NOT NULL REFERENCES artifacts(id),
  simulation           BOOLEAN NOT NULL DEFAULT FALSE,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (demonstration_id, pipeline_version)
);

-- ─── Skill IRs ────────────────────────────────────────────────────────────────

CREATE TABLE skill_irs (
  id                    TEXT PRIMARY KEY,   -- sir_...
  reconstruction_id     TEXT NOT NULL REFERENCES reconstructions(id),
  compiler_version      TEXT NOT NULL,
  artifact_id           TEXT NOT NULL REFERENCES artifacts(id),
  contact_observability NUMERIC,
  accepted              BOOLEAN NOT NULL DEFAULT FALSE,
  simulation            BOOLEAN NOT NULL DEFAULT FALSE,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (reconstruction_id, compiler_version)
);

-- ─── Robot Trajectories ───────────────────────────────────────────────────────

CREATE TABLE robot_trajectories (
  id               TEXT PRIMARY KEY,        -- traj_...
  skill_ir_id      TEXT NOT NULL REFERENCES skill_irs(id),
  robot_id         TEXT NOT NULL,
  retarget_path    TEXT NOT NULL CHECK (retarget_path IN ('fast', 'heavy')),
  verified_level   TEXT NOT NULL CHECK (verified_level IN ('verified_simulation', 'verified_real')),
  config_hash      TEXT NOT NULL,
  artifact_id      TEXT NOT NULL REFERENCES artifacts(id),
  simulation       BOOLEAN NOT NULL DEFAULT FALSE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (skill_ir_id, robot_id, config_hash)
);

-- ─── Episodes ─────────────────────────────────────────────────────────────────

CREATE TYPE episode_kind AS ENUM ('source', 'generated');

CREATE TABLE episodes (
  id               TEXT PRIMARY KEY,        -- ep_...
  order_id         TEXT NOT NULL REFERENCES dataset_orders(id),
  kind             episode_kind NOT NULL,
  source_id        TEXT,                    -- robot_trajectory_id for source; parent episode for generated
  lineage_group_id TEXT NOT NULL,           -- all episodes from same source share this for split safety
  artifact_id      TEXT REFERENCES artifacts(id),
  batch_qc_passed  BOOLEAN,
  delivered        BOOLEAN NOT NULL DEFAULT FALSE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_episodes_order ON episodes(order_id);
CREATE INDEX idx_episodes_lineage ON episodes(lineage_group_id);

-- ─── Decisions ────────────────────────────────────────────────────────────────

CREATE TABLE decisions (
  id                     TEXT PRIMARY KEY, -- dec_...
  order_id               TEXT NOT NULL REFERENCES dataset_orders(id),
  decision_type          TEXT NOT NULL,
  reason_codes           TEXT[] NOT NULL DEFAULT '{}',
  evidence_artifact_ids  TEXT[] NOT NULL DEFAULT '{}',
  payload                JSONB NOT NULL,   -- forge.decision.v1
  confidence             NUMERIC,
  policy_version         TEXT NOT NULL,
  requires_human_approval BOOLEAN NOT NULL DEFAULT FALSE,
  approved_by            TEXT,
  approved_at            TIMESTAMPTZ,
  created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_decisions_order ON decisions(order_id);

-- ─── Webhook Events ───────────────────────────────────────────────────────────

CREATE TABLE webhook_events (
  id                TEXT PRIMARY KEY,       -- wh_...
  provider          TEXT NOT NULL,
  provider_event_id TEXT NOT NULL,
  payload           JSONB NOT NULL,
  processed_at      TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (provider, provider_event_id)
);

-- ─── Deliveries ───────────────────────────────────────────────────────────────

CREATE TABLE deliveries (
  id                TEXT PRIMARY KEY,       -- del_...
  order_id          TEXT NOT NULL REFERENCES dataset_orders(id),
  dataset_version   TEXT NOT NULL,
  rights_profile    TEXT NOT NULL,
  manifest          JSONB NOT NULL,         -- forge.delivery.v1
  r2_prefix         TEXT NOT NULL,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (order_id, dataset_version)
);

-- ─── Audit Log ────────────────────────────────────────────────────────────────

CREATE TABLE audit_events (
  id          BIGSERIAL PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id   TEXT NOT NULL,
  action      TEXT NOT NULL,
  actor       TEXT NOT NULL,
  before_val  JSONB,
  after_val   JSONB,
  evidence    JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_entity ON audit_events(entity_type, entity_id);
