-- Production acquisition provenance and deterministic diversity gates.

ALTER TABLE capture_batches
  ADD COLUMN IF NOT EXISTS collection_plan JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS target_participant_count INTEGER,
  ADD COLUMN IF NOT EXISTS target_source_clips INTEGER;

ALTER TABLE demonstrations
  ADD COLUMN IF NOT EXISTS environment_id TEXT,
  ADD COLUMN IF NOT EXISTS take_kind TEXT,
  ADD COLUMN IF NOT EXISTS take_index INTEGER,
  ADD COLUMN IF NOT EXISTS capture_requirement_id TEXT,
  ADD COLUMN IF NOT EXISTS session_id TEXT,
  ADD COLUMN IF NOT EXISTS device_orientation TEXT,
  ADD COLUMN IF NOT EXISTS device_camera_facing TEXT;

ALTER TABLE demonstrations
  DROP CONSTRAINT IF EXISTS demonstrations_take_kind_check;
ALTER TABLE demonstrations
  ADD CONSTRAINT demonstrations_take_kind_check
  CHECK (take_kind IS NULL OR take_kind IN ('success', 'failure', 'recovery'));

CREATE INDEX IF NOT EXISTS idx_demo_order_worker
  ON demonstrations(order_id, worker_subject_id);
CREATE INDEX IF NOT EXISTS idx_demo_order_environment
  ON demonstrations(order_id, environment_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_demo_order_worker_take
  ON demonstrations(batch_id, worker_subject_id, take_index);

ALTER TABLE artifacts
  ADD COLUMN IF NOT EXISTS job_id TEXT REFERENCES gpu_jobs(id),
  ADD COLUMN IF NOT EXISTS demonstration_id TEXT REFERENCES demonstrations(id);

CREATE INDEX IF NOT EXISTS idx_artifacts_job ON artifacts(job_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_demonstration ON artifacts(demonstration_id);

ALTER TABLE gpu_jobs
  ADD COLUMN IF NOT EXISTS capture_id TEXT REFERENCES demonstrations(id);
CREATE INDEX IF NOT EXISTS idx_gpu_jobs_capture ON gpu_jobs(capture_id);
