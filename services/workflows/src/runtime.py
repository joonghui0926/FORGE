from __future__ import annotations

from contextlib import contextmanager
from collections import Counter, defaultdict
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
from typing import Any, Iterator

import httpx
from jsonschema import Draft7Validator
import psycopg
from psycopg.rows import dict_row

from forge.modules.collection.planner import CollectionPlanner, CustomerTaskRequest
from forge.contracts.models import ArtifactRef, GPUJobRequest
from forge.integrations.band import BandDecisionClient
from forge.integrations.pioneer import PioneerInferenceClient
from forge.integrations.r2.store import R2ObjectStore
from forge.integrations.terac import TeracCampaignClient


REPO_ROOT = Path(__file__).resolve().parents[3]


def new_id(prefix: str) -> str:
    return f"{prefix}{secrets.token_urlsafe(12)}"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def idempotency_key(*values: Any) -> str:
    return sha256(canonical_json(values).encode("utf-8")).hexdigest()


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name}_NOT_CONFIGURED")
    return value


class WorkflowRuntime:
    def __init__(self) -> None:
        self.database_url = require_env("DATABASE_URL")
        self.environment = os.getenv("FORGE_ENV", "development")
        self.http_timeout = float(os.getenv("PROVIDER_HTTP_TIMEOUT_SECONDS", "30"))

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[dict[str, Any]]]:
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            yield connection

    def load_order(self, order_id: str) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT id, tenant_id, state::text, contract FROM dataset_orders WHERE id = %s",
                (order_id,),
            ).fetchone()
        if row is None:
            raise ValueError("ORDER_NOT_FOUND")
        return dict(row)

    def validate_contract(self, order_id: str) -> dict[str, Any]:
        order = self.load_order(order_id)
        schema = json.loads(
            (REPO_ROOT / "packages/contracts/schemas/forge.order.v1.json").read_text("utf-8")
        )
        errors = sorted(
            Draft7Validator(schema).iter_errors(order["contract"]), key=lambda e: e.path
        )
        if errors:
            details = [f"{'/'.join(map(str, error.path))}: {error.message}" for error in errors]
            self.fail(order_id, "CONTRACT_INVALID", "; ".join(details))
            raise ValueError("CONTRACT_INVALID")
        self.transition(order_id, {"PAID", "PLANNING"}, "PLANNING", "validate_contract")
        return order["contract"]

    def transition(
        self,
        order_id: str,
        allowed_from: set[str],
        target_state: str,
        step: str,
        context_patch: dict[str, Any] | None = None,
        workflow_status: str = "RUNNING",
    ) -> None:
        patch = context_patch or {}
        with self.connection() as connection, connection.transaction():
            order = connection.execute(
                "SELECT state::text FROM dataset_orders WHERE id = %s FOR UPDATE", (order_id,)
            ).fetchone()
            if order is None:
                raise ValueError("ORDER_NOT_FOUND")
            current = str(order["state"])
            if current != target_state and current not in allowed_from:
                raise RuntimeError(f"ORDER_TRANSITION_INVALID:{current}->{target_state}")
            connection.execute(
                "UPDATE dataset_orders SET state = %s, updated_at = NOW() WHERE id = %s",
                (target_state, order_id),
            )
            connection.execute(
                """
                INSERT INTO workflow_runs (id, order_id, status, current_step, context)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (order_id) DO UPDATE SET
                  status = EXCLUDED.status,
                  current_step = EXCLUDED.current_step,
                  context = workflow_runs.context || EXCLUDED.context,
                  last_error_code = NULL,
                  last_error_message = NULL,
                  updated_at = NOW()
                """,
                (new_id("wfr_"), order_id, workflow_status, step, canonical_json(patch)),
            )
            connection.execute(
                """
                INSERT INTO audit_events
                  (entity_type, entity_id, action, actor, before_val, after_val, evidence)
                VALUES ('dataset_order', %s, %s, 'render-workflows', %s::jsonb, %s::jsonb, %s::jsonb)
                """,
                (
                    order_id,
                    step,
                    canonical_json({"state": current}),
                    canonical_json({"state": target_state}),
                    canonical_json(patch),
                ),
            )

    def wait(self, order_id: str, step: str, context_patch: dict[str, Any]) -> None:
        order = self.load_order(order_id)
        self.transition(
            order_id,
            {str(order["state"])},
            str(order["state"]),
            step,
            context_patch,
            workflow_status="WAITING",
        )

    def fail(self, order_id: str, code: str, message: str) -> None:
        with self.connection() as connection, connection.transaction():
            connection.execute(
                "UPDATE dataset_orders SET state = 'FAILED', updated_at = NOW() WHERE id = %s",
                (order_id,),
            )
            connection.execute(
                """
                INSERT INTO workflow_runs
                  (id, order_id, status, current_step, last_error_code, last_error_message)
                VALUES (%s, %s, 'FAILED', 'failed', %s, %s)
                ON CONFLICT (order_id) DO UPDATE SET
                  status = 'FAILED', current_step = 'failed',
                  last_error_code = EXCLUDED.last_error_code,
                  last_error_message = EXCLUDED.last_error_message,
                  updated_at = NOW()
                """,
                (new_id("wfr_"), order_id, code, message[:2000]),
            )

    def enqueue_operator_review(self, order_id: str, decision: dict[str, Any]) -> None:
        with self.connection() as connection, connection.transaction():
            connection.execute(
                """
                INSERT INTO operator_queue (id, order_id, reason_codes, evidence)
                VALUES (%s, %s, %s, %s::jsonb)
                ON CONFLICT (order_id) WHERE status = 'OPEN' DO UPDATE SET
                  reason_codes = EXCLUDED.reason_codes,
                  evidence = EXCLUDED.evidence
                """,
                (
                    new_id("opq_"),
                    order_id,
                    list(decision.get("reason_codes", [])),
                    canonical_json(decision),
                ),
            )

    def compile_collection_plan(self, order_id: str) -> dict[str, Any]:
        order = self.load_order(order_id)
        contract = order["contract"]
        skill = contract["skill"]
        robot = contract["embodiment"]
        acquisition = contract.get("acquisition") or {
            "participant_count": 3,
            "clips_per_participant": 6,
            "minimum_unique_environments": 2,
            "expertise": "general_contributor",
            "capture_mode": "mixed_views",
            "take_mix": {"success": 4, "failure": 1, "recovery": 1},
        }
        take_mix = acquisition["take_mix"]
        request = CustomerTaskRequest(
            request_id=f"req_{order_id.removeprefix('ord_')}",
            tenant_id=order["tenant_id"],
            task_name=skill["name"],
            task_outcome=skill["success_predicate"],
            motion_family=skill.get("motion_family", "whole_body"),
            target_robot_id=robot["robot_id"],
            target_robot_urdf_uri=robot["model_uri"],
            target_control_rate_hz=float(robot.get("control_rate_hz", 50)),
            environment_description=contract.get(
                "environment_description", "customer task environment"
            ),
            counterpart_descriptions=tuple(contract["coverage"]["object_ids"]),
            required_success_conditions=(skill["success_predicate"],),
            prohibited_failures=tuple(skill["failure_predicates"]),
            hazardous=bool(contract.get("hazardous", False)),
            regulated=bool(contract.get("regulated", False)),
            specialized_equipment=bool(contract.get("specialized_equipment", False)),
            requested_accepted_demonstrations=int(contract["volume"]["validated_episodes"]),
            participant_count=int(acquisition["participant_count"]),
            clips_per_participant=int(acquisition["clips_per_participant"]),
            minimum_unique_environments=int(acquisition["minimum_unique_environments"]),
            participant_expertise=str(acquisition["expertise"]),
            capture_mode=str(acquisition["capture_mode"]),
            success_takes_per_participant=int(take_mix["success"]),
            failure_takes_per_participant=int(take_mix["failure"]),
            recovery_takes_per_participant=int(take_mix["recovery"]),
        )
        return CollectionPlanner().compile(request).to_dict()

    def build_capture_features(
        self,
        order_id: str,
        capture_ids: list[str],
        provider_features: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build trusted collection evidence from FORGE records, not webhook claims."""
        order = self.load_order(order_id)
        contract = order["contract"]
        acquisition = contract.get("acquisition") or {
            "participant_count": 3,
            "clips_per_participant": 6,
            "minimum_unique_environments": 2,
            "take_mix": {"success": 4, "failure": 1, "recovery": 1},
        }
        unique_capture_ids = list(dict.fromkeys(capture_ids))
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, batch_id, worker_subject_id, environment_id, take_kind, take_index,
                       viewpoint_bin, object_id, declared_rights, state::text
                FROM demonstrations
                WHERE order_id = %s AND id = ANY(%s)
                ORDER BY id
                """,
                (order_id, unique_capture_ids),
            ).fetchall()

        worker_takes: dict[str, Counter[str]] = defaultdict(Counter)
        worker_environments: dict[str, set[str]] = defaultdict(set)
        viewpoints: set[str] = set()
        object_ids: set[str] = set()
        missing_rights: list[str] = []
        batch_ids: set[str] = set()
        for row in rows:
            batch_ids.add(str(row["batch_id"]))
            worker = str(row["worker_subject_id"])
            take_kind = str(row["take_kind"] or "")
            if take_kind:
                worker_takes[worker][take_kind] += 1
            if row["environment_id"]:
                worker_environments[worker].add(str(row["environment_id"]))
            viewpoints.add(str(row["viewpoint_bin"]))
            object_ids.add(str(row["object_id"]))
            if not row["declared_rights"]:
                missing_rights.append(str(row["id"]))

        required_mix = {key: int(value) for key, value in acquisition["take_mix"].items()}
        clips_per_participant = int(acquisition["clips_per_participant"])
        qualified_workers = [
            worker
            for worker, mix in worker_takes.items()
            if sum(mix.values()) >= clips_per_participant
            and all(mix[kind] >= required for kind, required in required_mix.items())
        ]
        qualified_environments = {
            environment
            for worker in qualified_workers
            for environment in worker_environments[worker]
        }
        participant_count = int(acquisition["participant_count"])
        minimum_environments = int(acquisition["minimum_unique_environments"])
        required_viewpoints = set(contract["coverage"]["viewpoint_bins"])
        required_objects = set(contract["coverage"]["object_ids"])

        hard_failures = list((provider_features or {}).get("deterministic_hard_failures", []))
        if len(rows) != len(unique_capture_ids):
            hard_failures.append("CAPTURE_NOT_FOUND_OR_WRONG_ORDER")
        if len(batch_ids) != 1:
            hard_failures.append("CAPTURES_MUST_BELONG_TO_ONE_BATCH")
        if len(qualified_workers) < participant_count:
            hard_failures.append("PARTICIPANT_OR_TAKE_MIX_COVERAGE_INSUFFICIENT")
        if len(qualified_environments) < minimum_environments:
            hard_failures.append("ENVIRONMENT_DIVERSITY_INSUFFICIENT")
        if not required_viewpoints.issubset(viewpoints):
            hard_failures.append("VIEWPOINT_COVERAGE_INSUFFICIENT")
        if not required_objects.issubset(object_ids):
            hard_failures.append("OBJECT_COVERAGE_INSUFFICIENT")
        if missing_rights:
            hard_failures.append("RIGHTS_METADATA_MISSING")

        provider_ratio = float(
            (provider_features or {}).get(
                "capture_valid_ratio",
                (provider_features or {}).get("reconstruction_valid_ratio", 1.0),
            )
        )
        return {
            **(provider_features or {}),
            "subject_id": (
                "batch_" + next(iter(batch_ids)).removeprefix("bat_")
                if len(batch_ids) == 1
                else f"batch_mixed_{order_id.removeprefix('ord_')}"
            ),
            "capture_ids": unique_capture_ids,
            "capture_count": len(rows),
            "capture_valid_ratio": provider_ratio,
            "participant_count": len(worker_takes),
            "qualified_participant_count": len(qualified_workers),
            "required_participant_count": participant_count,
            "qualified_environment_count": len(qualified_environments),
            "required_environment_count": minimum_environments,
            "participant_take_counts": {
                worker: dict(counts) for worker, counts in sorted(worker_takes.items())
            },
            "required_take_mix": required_mix,
            "viewpoints_observed": sorted(viewpoints),
            "objects_observed": sorted(object_ids),
            "deterministic_hard_failures": sorted(set(hard_failures)),
            "evidence_source": "forge_database_plus_signed_provider_features",
        }

    def record_pre_qc(
        self, order_id: str, capture_ids: list[str], features: dict[str, Any], passed: bool
    ) -> None:
        with self.connection() as connection, connection.transaction():
            connection.execute(
                """
                INSERT INTO qc_runs
                  (id, order_id, subject_type, subject_id, stage, passed, reason_codes,
                   metrics, thresholds, config_hash, simulation)
                VALUES (%s, %s, 'capture_batch', %s, 'pre_qc', %s, %s,
                        %s::jsonb, %s::jsonb, %s, FALSE)
                ON CONFLICT (subject_id, stage, config_hash) DO UPDATE SET
                  passed = EXCLUDED.passed,
                  reason_codes = EXCLUDED.reason_codes,
                  metrics = EXCLUDED.metrics,
                  thresholds = EXCLUDED.thresholds
                """,
                (
                    new_id("qc_"),
                    order_id,
                    str(features["subject_id"]),
                    passed,
                    list(features.get("deterministic_hard_failures", [])),
                    canonical_json(features),
                    canonical_json(
                        {
                            "capture_valid_ratio": 0.8,
                            "participant_count": features["required_participant_count"],
                            "environment_count": features["required_environment_count"],
                            "take_mix": features["required_take_mix"],
                        }
                    ),
                    idempotency_key("forge-collection-gate-v2", features),
                ),
            )
            if passed:
                connection.execute(
                    """
                    UPDATE demonstrations SET state = 'PRE_QC_PASSED'
                    WHERE order_id = %s AND id = ANY(%s) AND state = 'SUBMITTED'
                    """,
                    (order_id, capture_ids),
                )

    def record_validation_qc(self, order_id: str, subject_id: str, result: dict[str, Any]) -> None:
        order = self.load_order(order_id)
        thresholds = order["contract"]["quality"]
        passed = bool(result["passed"])
        batch_id = "bat_" + subject_id.removeprefix("batch_")
        with self.connection() as connection, connection.transaction():
            connection.execute(
                """
                INSERT INTO qc_runs
                  (id, order_id, subject_type, subject_id, stage, passed, reason_codes,
                   metrics, thresholds, config_hash, simulation)
                VALUES (%s, %s, 'delivery_batch', %s, 'final_validation', %s, %s,
                        %s::jsonb, %s::jsonb, %s, FALSE)
                ON CONFLICT (subject_id, stage, config_hash) DO UPDATE SET
                  passed = EXCLUDED.passed,
                  reason_codes = EXCLUDED.reason_codes,
                  metrics = EXCLUDED.metrics,
                  thresholds = EXCLUDED.thresholds
                """,
                (
                    new_id("qc_"),
                    order_id,
                    subject_id,
                    passed,
                    list(result.get("hard_failures", [])),
                    canonical_json(result),
                    canonical_json(thresholds),
                    idempotency_key("forge-final-validation-v2", result, thresholds),
                ),
            )
            connection.execute(
                """
                UPDATE demonstrations
                SET state = %s
                WHERE order_id = %s AND batch_id = %s AND state = 'RECONSTRUCTION_COMPLETE'
                """,
                (
                    "VALIDATION_PASSED" if passed else "VALIDATION_FAILED",
                    order_id,
                    batch_id,
                ),
            )

    def latest_hard_failures(self, order_id: str) -> list[str]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT ON (stage) stage, passed, reason_codes
                FROM qc_runs
                WHERE order_id = %s AND stage IN ('pre_qc', 'final_validation')
                ORDER BY stage, created_at DESC
                """,
                (order_id,),
            ).fetchall()
        failures: list[str] = []
        for row in rows:
            if not bool(row["passed"]):
                failures.extend(str(code) for code in row["reason_codes"])
        return sorted(set(failures))

    def create_provider_request(
        self, order_id: str, provider: str, purpose: str, payload: dict[str, Any]
    ) -> tuple[str, str, bool]:
        key = idempotency_key(order_id, provider, purpose, payload)
        correlation_id = f"{provider}_{key[:24]}"
        request_id = new_id("prv_")
        with self.connection() as connection, connection.transaction():
            existing = connection.execute(
                """
                SELECT id, correlation_id, state FROM provider_requests
                WHERE provider = %s AND idempotency_key = %s
                """,
                (provider, key),
            ).fetchone()
            if existing:
                retry = str(existing["state"]) == "FAILED"
                if retry:
                    connection.execute(
                        """
                        UPDATE provider_requests
                        SET state = 'PENDING', response_payload = NULL, completed_at = NULL
                        WHERE id = %s
                        """,
                        (existing["id"],),
                    )
                return str(existing["id"]), str(existing["correlation_id"]), retry
            connection.execute(
                """
                INSERT INTO provider_requests
                  (id, order_id, provider, purpose, idempotency_key, correlation_id, state, request_payload)
                VALUES (%s, %s, %s, %s, %s, %s, 'PENDING', %s::jsonb)
                """,
                (
                    request_id,
                    order_id,
                    provider,
                    purpose,
                    key,
                    correlation_id,
                    canonical_json(payload),
                ),
            )
        return request_id, correlation_id, True

    def complete_provider_request(
        self,
        request_id: str,
        external_id: str | None,
        response: dict[str, Any],
        state: str = "SUCCEEDED",
    ) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE provider_requests
                SET state = %s, external_id = %s, response_payload = %s::jsonb,
                    completed_at = CASE WHEN %s IN ('SUCCEEDED', 'FAILED') THEN NOW() ELSE NULL END
                WHERE id = %s
                """,
                (state, external_id, canonical_json(response), state, request_id),
            )

    def request_band(self, order_id: str, purpose: str, payload: dict[str, Any]) -> str:
        client = BandDecisionClient.from_env(self.http_timeout)
        request_id, correlation_id, should_send = self.create_provider_request(
            order_id, "band", purpose, payload
        )
        if not should_send:
            return correlation_id
        dispatch = client.request_decision(purpose, correlation_id, payload)
        self.complete_provider_request(
            request_id, dispatch.external_id, dispatch.response, state="SENT"
        )
        return correlation_id

    def request_pioneer(
        self, order_id: str, purpose: str, features: dict[str, Any]
    ) -> dict[str, Any]:
        request_id, correlation_id, should_send = self.create_provider_request(
            order_id, "pioneer", purpose, features
        )
        if not should_send:
            with self.connection() as connection:
                row = connection.execute(
                    "SELECT response_payload FROM provider_requests WHERE id = %s", (request_id,)
                ).fetchone()
            if row and row["response_payload"]:
                return dict(row["response_payload"])
            raise RuntimeError("PIONEER_REQUEST_ALREADY_PENDING")
        result = PioneerInferenceClient.from_env(self.http_timeout).infer(
            purpose, correlation_id, features
        )
        self.complete_provider_request(request_id, result.external_id, result.verdict)
        return result.verdict

    def create_terac_campaign(
        self, order_id: str, collection_plan: dict[str, Any]
    ) -> dict[str, Any]:
        client = TeracCampaignClient.from_env(self.http_timeout)
        api_base = require_env("API_BASE_URL").rstrip("/")
        collection_plan = {
            **collection_plan,
            "submission_contract": {
                "schema_version": "forge.terac-submission-contract.v1",
                "request_upload_url": f"{api_base}/captures/provider/terac/upload-url",
                "complete_capture": f"{api_base}/captures/provider/terac/complete",
                "batch_ready_webhook": f"{api_base}/webhooks/terac",
                "provider_auth_header": "X-Forge-Provider-Token",
                "original_media_required": True,
                "one_capture_per_take": True,
            },
        }
        request_id, correlation_id, should_send = self.create_provider_request(
            order_id, "terac", "create_campaign", collection_plan
        )
        if not should_send:
            return {"correlation_id": correlation_id, "deduplicated": True}
        batch_id = "bat_" + sha256(correlation_id.encode("utf-8")).hexdigest()[:20]
        with self.connection() as connection, connection.transaction():
            sequence = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS next FROM capture_batches WHERE order_id = %s",
                (order_id,),
            ).fetchone()["next"]
            connection.execute(
                """
                INSERT INTO capture_batches
                  (id, order_id, sequence, terac_campaign_id, collection_plan,
                   target_participant_count, target_source_clips)
                VALUES (%s, %s, %s, NULL, %s::jsonb, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    batch_id,
                    order_id,
                    sequence,
                    canonical_json(collection_plan),
                    int(collection_plan["target_participant_count"]),
                    int(collection_plan["target_source_clips"]),
                ),
            )
        dispatch_plan = {**collection_plan, "order_id": order_id, "batch_id": batch_id}
        try:
            result = client.create_campaign(correlation_id, dispatch_plan)
        except Exception as error:
            self.complete_provider_request(
                request_id,
                None,
                {"error_code": type(error).__name__, "message": str(error)[:500]},
                state="FAILED",
            )
            raise
        self.complete_provider_request(request_id, result.campaign_id, result.response)
        with self.connection() as connection:
            connection.execute(
                "UPDATE capture_batches SET terac_campaign_id = %s WHERE id = %s",
                (result.campaign_id, batch_id),
            )
        return {**result.response, "batch_id": batch_id}

    def submit_runpod(self, order_id: str, capture_id: str) -> dict[str, Any]:
        api_key = require_env("RUNPOD_API_KEY")
        endpoint_id = require_env("RUNPOD_RECONSTRUCTION_ENDPOINT_ID")
        order = self.load_order(order_id)
        key = idempotency_key(order_id, "compile", capture_id, order["contract"])
        with self.connection() as connection, connection.transaction():
            existing = connection.execute(
                "SELECT id, provider_job_id, status::text FROM gpu_jobs WHERE idempotency_key = %s",
                (key,),
            ).fetchone()
            if existing and existing["provider_job_id"]:
                return {
                    "job_id": str(existing["id"]),
                    "provider_job_id": str(existing["provider_job_id"]),
                    "status": str(existing["status"]),
                    "deduplicated": True,
                }
            capture = connection.execute(
                """
                SELECT id, video_r2_key, sha256, mime_type, object_id
                FROM demonstrations WHERE order_id = %s AND id = %s
                """,
                (order_id, capture_id),
            ).fetchone()
            if capture is None:
                raise ValueError("CAPTURE_NOT_FOUND")
            job_id = str(existing["id"]) if existing else new_id("job_")
            output_prefix = f"tenants/{order['tenant_id']}/compiler/{order_id}/{job_id}"
            input_keys = [str(capture["video_r2_key"])]
            if not existing:
                connection.execute(
                    """
                    INSERT INTO gpu_jobs
                      (id, idempotency_key, order_id, stage, status, container_image,
                       pipeline_version, input_r2_keys, output_r2_prefix, capture_id)
                    VALUES (%s, %s, %s, 'reconstruction', 'PENDING', %s, %s, %s, %s, %s)
                    """,
                    (
                        job_id,
                        key,
                        order_id,
                        require_env("FORGE_GPU_IMAGE"),
                        os.getenv("FORGE_PIPELINE_VERSION", "forge-compiler-v1"),
                        input_keys,
                        output_prefix,
                        capture_id,
                    ),
                )

        bucket = require_env("R2_BUCKET_NAME")
        mime_type = str(capture["mime_type"])
        if mime_type in {"application/bvh", "text/bvh"}:
            config = {
                "adapter_id": "gmr-xsens-headless-v1",
                "input_kind": "source",
                "source_extension": ".bvh",
                "robot_id": order["contract"]["embodiment"]["robot_id"],
                "scale": 0.01,
                "reset_to_zero": True,
            }
        elif mime_type.startswith("video/"):
            claim_level = (order["contract"].get("output") or {}).get(
                "claim_level", "sim_validated_robot_trajectory"
            )
            if claim_level == "human_video_training":
                config = {
                    "adapter_id": "forge-video-qc-v1",
                    "input_kind": "source",
                    "minimum_width_px": 1920,
                    "minimum_height_px": 1080,
                    "minimum_frame_rate_hz": 30,
                    "timeout_s": 900,
                }
            elif self.environment == "production":
                raise PermissionError("VIDEO_TO_ROBOT_TRAJECTORY_NOT_PRODUCTION_APPROVED")
            else:
                config = {
                    "adapter_id": "videomanip-reconstruction-v1",
                    "input_kind": "source",
                    "object_id": str(capture["object_id"]),
                    "source_extension": ".mp4",
                    "stages": [
                        "frames",
                        "intrinsics",
                        "hand_mesh",
                        "masks",
                        "obj_mesh",
                        "retarget",
                    ],
                    "timeout_s": 7200,
                }
        else:
            raise ValueError(f"CAPTURE_MIME_TYPE_UNSUPPORTED:{mime_type}")

        config_uri = f"r2://{bucket}/{output_prefix}/job-config.json"
        R2ObjectStore.from_env().put_bytes(
            config_uri,
            (canonical_json(config) + "\n").encode("utf-8"),
            "application/json",
        )
        request = GPUJobRequest(
            job_id=job_id,
            idempotency_key=key,
            stage="reconstruction",
            input_artifacts=(
                ArtifactRef(
                    kind="source",
                    uri=f"r2://{bucket}/{capture['video_r2_key']}",
                    sha256=str(capture["sha256"]),
                    media_type=mime_type,
                ),
            ),
            config_uri=config_uri,
            container_image=require_env("FORGE_GPU_IMAGE"),
            pipeline_version=os.getenv("FORGE_PIPELINE_VERSION", "forge-compiler-v1"),
            output_prefix=f"r2://{bucket}/{output_prefix}",
        )
        callback_base = require_env("API_BASE_URL").rstrip("/")
        callback_token = require_env("FORGE_CALLBACK_TOKEN")
        response = httpx.post(
            f"https://api.runpod.ai/v2/{endpoint_id}/run",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "input": {
                    "request": asdict(request),
                    "callback_url": f"{callback_base}/jobs/callback",
                    "callback_token": callback_token,
                }
            },
            timeout=self.http_timeout,
        )
        response.raise_for_status()
        body = response.json()
        provider_job_id = str(body.get("id", ""))
        if not provider_job_id:
            raise RuntimeError("RUNPOD_JOB_ID_MISSING")
        with self.connection() as connection:
            connection.execute(
                "UPDATE gpu_jobs SET provider_job_id = %s, status = 'RUNNING' WHERE id = %s",
                (provider_job_id, job_id),
            )
        return {"job_id": job_id, "provider_job_id": provider_job_id, "status": "RUNNING"}

    def submit_package(self, order_id: str, decision: dict[str, Any]) -> dict[str, Any]:
        api_key = require_env("RUNPOD_API_KEY")
        endpoint_id = os.getenv("RUNPOD_PACKAGE_ENDPOINT_ID") or require_env(
            "RUNPOD_RECONSTRUCTION_ENDPOINT_ID"
        )
        order = self.load_order(order_id)
        dataset_version = os.getenv("FORGE_DATASET_VERSION", "1.0.0")
        key = idempotency_key(order_id, "package", dataset_version, decision)
        with self.connection() as connection, connection.transaction():
            existing = connection.execute(
                "SELECT id, provider_job_id, status::text FROM gpu_jobs WHERE idempotency_key = %s",
                (key,),
            ).fetchone()
            if existing and existing["provider_job_id"]:
                return {
                    "job_id": str(existing["id"]),
                    "provider_job_id": str(existing["provider_job_id"]),
                    "status": str(existing["status"]),
                    "deduplicated": True,
                }
            artifacts = connection.execute(
                """
                SELECT id, kind, r2_key, sha256, demonstration_id
                FROM artifacts
                WHERE order_id = %s AND producer IN ('runpod', 'browser_upload')
                  AND kind NOT IN ('delivery_package', 'delivery_manifest')
                  AND demonstration_id IN (
                    SELECT id FROM demonstrations
                    WHERE order_id = %s AND state = 'VALIDATION_PASSED'
                  )
                ORDER BY created_at, id
                """,
                (order_id, order_id),
            ).fetchall()
            if not artifacts:
                raise RuntimeError("DELIVERY_ARTIFACTS_MISSING")
            job_id = str(existing["id"]) if existing else new_id("job_")
            output_prefix = f"tenants/{order['tenant_id']}/deliveries/{order_id}/{dataset_version}"
            if not existing:
                connection.execute(
                    """
                    INSERT INTO gpu_jobs
                      (id, idempotency_key, order_id, stage, status, container_image,
                       pipeline_version, input_r2_keys, output_r2_prefix)
                    VALUES (%s, %s, %s, 'package', 'PENDING', %s, %s, %s, %s)
                    """,
                    (
                        job_id,
                        key,
                        order_id,
                        require_env("FORGE_GPU_IMAGE"),
                        os.getenv("FORGE_PIPELINE_VERSION", "forge-compiler-v1"),
                        [str(item["r2_key"]) for item in artifacts],
                        output_prefix,
                    ),
                )

        bucket = require_env("R2_BUCKET_NAME")
        input_artifacts: list[ArtifactRef] = []
        manifest_artifacts: list[dict[str, Any]] = []
        for index, artifact in enumerate(artifacts):
            input_kind = f"artifact_{index:05d}"
            filename = f"{index:05d}_{Path(str(artifact['r2_key'])).name}"
            uri = f"r2://{bucket}/{artifact['r2_key']}"
            input_artifacts.append(
                ArtifactRef(
                    kind=input_kind,
                    uri=uri,
                    sha256=str(artifact["sha256"]),
                    media_type="application/octet-stream",
                )
            )
            manifest_artifacts.append(
                {
                    "input_kind": input_kind,
                    "kind": str(artifact["kind"]),
                    "filename": filename,
                    "uri": uri,
                    "sha256": str(artifact["sha256"]),
                    "demonstration_id": (
                        str(artifact["demonstration_id"]) if artifact["demonstration_id"] else None
                    ),
                }
            )

        config = {
            "schema_version": "forge.package-job.v1",
            "order_id": order_id,
            "tenant_id": order["tenant_id"],
            "dataset_version": dataset_version,
            "rights_profile": order["contract"]["rights_profile"],
            "quality_decision": decision,
            "output": order["contract"].get(
                "output",
                {
                    "claim_level": "sim_validated_robot_trajectory",
                    "formats": ["forge_canonical"],
                    "augmentation": "none",
                },
            ),
            "skill": order["contract"]["skill"],
            "acquisition": order["contract"].get("acquisition", {}),
            "known_limitations": (
                [
                    "Training data only; no robot hardware validation is included.",
                    "LeRobot, RLDS, and robomimic exports require accepted action/state signals.",
                ]
                if (order["contract"].get("output") or {}).get("claim_level")
                == "human_video_training"
                else ["Simulation validation does not constitute hardware validation."]
            ),
            "output_prefix": f"r2://{bucket}/{output_prefix}",
            "pipeline_release": os.getenv("FORGE_PIPELINE_VERSION", "forge-compiler-v2"),
            "artifacts": manifest_artifacts,
        }
        config_uri = f"r2://{bucket}/{output_prefix}/package-config.json"
        R2ObjectStore.from_env().put_bytes(
            config_uri,
            (canonical_json(config) + "\n").encode("utf-8"),
            "application/json",
        )
        request = GPUJobRequest(
            job_id=job_id,
            idempotency_key=key,
            stage="package",
            input_artifacts=tuple(input_artifacts),
            config_uri=config_uri,
            container_image=require_env("FORGE_GPU_IMAGE"),
            pipeline_version=os.getenv("FORGE_PIPELINE_VERSION", "forge-compiler-v1"),
            output_prefix=f"r2://{bucket}/{output_prefix}",
        )
        callback_base = require_env("API_BASE_URL").rstrip("/")
        response = httpx.post(
            f"https://api.runpod.ai/v2/{endpoint_id}/run",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "input": {
                    "request": asdict(request),
                    "callback_url": f"{callback_base}/jobs/callback",
                    "callback_token": require_env("FORGE_CALLBACK_TOKEN"),
                }
            },
            timeout=self.http_timeout,
        )
        response.raise_for_status()
        body = response.json()
        provider_job_id = str(body.get("id", ""))
        if not provider_job_id:
            raise RuntimeError("RUNPOD_JOB_ID_MISSING")
        with self.connection() as connection:
            connection.execute(
                "UPDATE gpu_jobs SET provider_job_id = %s, status = 'RUNNING' WHERE id = %s",
                (provider_job_id, job_id),
            )
        return {"job_id": job_id, "provider_job_id": provider_job_id, "status": "RUNNING"}
