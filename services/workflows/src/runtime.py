from __future__ import annotations

from contextlib import contextmanager
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
        )
        return CollectionPlanner().compile(request).to_dict()

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
                return str(existing["id"]), str(existing["correlation_id"]), False
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
        request_id, correlation_id, should_send = self.create_provider_request(
            order_id, "terac", "create_campaign", collection_plan
        )
        if not should_send:
            return {"correlation_id": correlation_id, "deduplicated": True}
        result = client.create_campaign(correlation_id, collection_plan)
        self.complete_provider_request(request_id, result.campaign_id, result.response)
        with self.connection() as connection, connection.transaction():
            sequence = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS next FROM capture_batches WHERE order_id = %s",
                (order_id,),
            ).fetchone()["next"]
            connection.execute(
                """
                INSERT INTO capture_batches (id, order_id, sequence, terac_campaign_id)
                VALUES (%s, %s, %s, %s)
                """,
                (new_id("bat_"), order_id, sequence, result.campaign_id),
            )
        return result.response

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
                       pipeline_version, input_r2_keys, output_r2_prefix)
                    VALUES (%s, %s, %s, 'reconstruction', 'PENDING', %s, %s, %s, %s)
                    """,
                    (
                        job_id,
                        key,
                        order_id,
                        require_env("FORGE_GPU_IMAGE"),
                        os.getenv("FORGE_PIPELINE_VERSION", "forge-compiler-v1"),
                        input_keys,
                        output_prefix,
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
            config = {
                "adapter_id": "videomanip-reconstruction-v1",
                "input_kind": "source",
                "object_id": str(capture["object_id"]),
                "source_extension": ".mp4",
                "stages": ["frames", "intrinsics", "hand_mesh", "masks", "obj_mesh", "retarget"],
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
        dataset_version = os.getenv("FORGE_DATASET_VERSION", "v1")
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
                SELECT id, kind, r2_key, sha256
                FROM artifacts
                WHERE order_id = %s AND producer = 'runpod'
                  AND kind NOT IN ('delivery_package', 'delivery_manifest')
                ORDER BY created_at, id
                """,
                (order_id,),
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
                }
            )

        config = {
            "schema_version": "forge.package-job.v1",
            "order_id": order_id,
            "tenant_id": order["tenant_id"],
            "dataset_version": dataset_version,
            "rights_profile": order["contract"]["rights_profile"],
            "quality_decision": decision,
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
