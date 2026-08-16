ALTER TYPE order_state ADD VALUE IF NOT EXISTS 'REVIEW';
ALTER TYPE order_state ADD VALUE IF NOT EXISTS 'BLOCKED';

ALTER TABLE gpu_jobs ADD COLUMN IF NOT EXISTS result_metrics JSONB NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS workflow_runs (
  id                TEXT PRIMARY KEY,
  order_id          TEXT NOT NULL UNIQUE REFERENCES dataset_orders(id),
  status            TEXT NOT NULL CHECK (status IN ('RUNNING', 'WAITING', 'COMPLETED', 'FAILED')),
  current_step      TEXT NOT NULL,
  render_root_run_id TEXT,
  context           JSONB NOT NULL DEFAULT '{}',
  last_error_code   TEXT,
  last_error_message TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS provider_requests (
  id                TEXT PRIMARY KEY,
  order_id          TEXT NOT NULL REFERENCES dataset_orders(id),
  provider          TEXT NOT NULL,
  purpose           TEXT NOT NULL,
  idempotency_key   TEXT NOT NULL,
  correlation_id    TEXT NOT NULL,
  external_id       TEXT,
  state             TEXT NOT NULL CHECK (state IN ('PENDING', 'SENT', 'SUCCEEDED', 'FAILED')),
  request_payload   JSONB NOT NULL,
  response_payload  JSONB,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at      TIMESTAMPTZ,
  UNIQUE (provider, idempotency_key),
  UNIQUE (provider, correlation_id)
);

CREATE INDEX IF NOT EXISTS idx_provider_requests_order ON provider_requests(order_id);
CREATE INDEX IF NOT EXISTS idx_provider_requests_state ON provider_requests(provider, state);

CREATE TABLE IF NOT EXISTS operator_queue (
  id                TEXT PRIMARY KEY,
  order_id          TEXT NOT NULL REFERENCES dataset_orders(id),
  reason_codes      TEXT[] NOT NULL DEFAULT '{}',
  evidence          JSONB NOT NULL DEFAULT '{}',
  status            TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'RESOLVED')),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at       TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_operator_queue_open_order
  ON operator_queue(order_id) WHERE status = 'OPEN';
