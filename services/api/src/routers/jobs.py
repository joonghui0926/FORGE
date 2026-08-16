from __future__ import annotations

import json
import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status

from ..auth import require_tenant, require_worker_callback_token
from ..db import get_conn
from ..models import GPUResultPayload, TenantContext
from ..workflow_client import start_workflow_task


router = APIRouter()


def _new_id(prefix: str) -> str:
    return f"{prefix}{secrets.token_urlsafe(12)}"


@router.post("/callback", status_code=status.HTTP_200_OK)
def gpu_job_callback(
    result: GPUResultPayload,
    x_forge_job_id: str = Header(...),
    _: None = Depends(require_worker_callback_token),
) -> dict:
    if result.job_id != x_forge_job_id:
        raise HTTPException(status_code=422, detail="Job header and payload mismatch")
    with get_conn() as connection, connection.transaction():
        row = connection.execute(
            """
            SELECT j.order_id, j.status::text, o.tenant_id, j.stage,
                   j.output_r2_prefix, o.contract, o.state::text
            FROM gpu_jobs j JOIN dataset_orders o ON o.id = j.order_id
            WHERE j.id = %s FOR UPDATE
            """,
            (result.job_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="GPU job not found")
        order_id, current_status, tenant_id = str(row[0]), str(row[1]), str(row[2])
        stage, output_prefix, contract, order_state = (
            str(row[3]),
            str(row[4]),
            dict(row[5]),
            str(row[6]),
        )
        if os.getenv("FORGE_ENV", "development") == "production" and result.simulation:
            raise HTTPException(status_code=422, detail="Simulation result cannot enter production")
        target_status = {
            "succeeded": "SUCCEEDED",
            "failed": "FAILED",
            "retryable": "FAILED",
            "quality_insufficient": "QUALITY_INSUFFICIENT",
        }.get(result.status)
        if target_status is None:
            raise HTTPException(status_code=422, detail="Unsupported GPU status")
        if current_status not in {"SUCCEEDED", "FAILED", "QUALITY_INSUFFICIENT"}:
            connection.execute(
                """
                UPDATE gpu_jobs SET status = %s, gpu_seconds = %s,
                  error_code = %s, error_message = %s, result_metrics = %s::jsonb,
                  completed_at = NOW()
                WHERE id = %s
                """,
                (
                    target_status,
                    result.metrics.gpu_seconds,
                    result.error.code if result.error else result.error_code,
                    result.error.message if result.error else result.error_message,
                    json.dumps(result.metrics.model_dump(exclude_none=True)),
                    result.job_id,
                ),
            )
            for artifact in result.artifacts:
                if not artifact.uri.startswith("r2://"):
                    raise HTTPException(status_code=422, detail="GPU artifact must use R2")
                r2_key = artifact.uri.split("/", 3)[-1]
                connection.execute(
                    """
                    INSERT INTO artifacts
                      (id, tenant_id, order_id, kind, r2_key, sha256, schema_version, producer)
                    VALUES (%s, %s, %s, %s, %s, %s, 'forge.gpu-result.v1', 'runpod')
                    ON CONFLICT (tenant_id, sha256, kind) DO NOTHING
                    """,
                    (_new_id("art_"), tenant_id, order_id, artifact.kind, r2_key, artifact.sha256),
                )
        package_response: dict | None = None
        if stage == "package":
            if target_status != "SUCCEEDED":
                connection.execute(
                    "UPDATE dataset_orders SET state = 'FAILED', updated_at = NOW() WHERE id = %s",
                    (order_id,),
                )
                package_response = {"received": True, "status": target_status}
            else:
                artifact_by_kind = {artifact.kind: artifact for artifact in result.artifacts}
                package = artifact_by_kind.get("delivery_package")
                manifest = artifact_by_kind.get("delivery_manifest")
                if package is None or manifest is None:
                    raise HTTPException(status_code=422, detail="Delivery artifacts incomplete")
                if order_state not in {"PACKAGING", "READY"}:
                    raise HTTPException(status_code=409, detail="Order is not packaging")
                dataset_version = output_prefix.rstrip("/").rsplit("/", 1)[-1]
                delivery_id = _new_id("del_")
                delivery_manifest = {
                    "schema_version": "forge.delivery.v1",
                    "order_id": order_id,
                    "dataset_version": dataset_version,
                    "package_key": package.uri.split("/", 3)[-1],
                    "package_sha256": package.sha256,
                    "manifest_key": manifest.uri.split("/", 3)[-1],
                    "manifest_sha256": manifest.sha256,
                }
                delivery_row = connection.execute(
                    """
                    INSERT INTO deliveries
                      (id, order_id, dataset_version, rights_profile, manifest, r2_prefix)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (order_id, dataset_version) DO UPDATE SET
                      manifest = EXCLUDED.manifest,
                      r2_prefix = EXCLUDED.r2_prefix
                    RETURNING id
                    """,
                    (
                        delivery_id,
                        order_id,
                        dataset_version,
                        str(contract["rights_profile"]),
                        json.dumps(delivery_manifest),
                        output_prefix,
                    ),
                ).fetchone()
                delivery_id = str(delivery_row[0])
                connection.execute(
                    "UPDATE dataset_orders SET state = 'READY', updated_at = NOW() WHERE id = %s",
                    (order_id,),
                )
                connection.execute(
                    """
                    UPDATE workflow_runs
                    SET status = 'COMPLETED', current_step = 'package_dataset', updated_at = NOW()
                    WHERE order_id = %s
                    """,
                    (order_id,),
                )
                connection.execute(
                    """
                    INSERT INTO audit_events
                      (entity_type, entity_id, action, actor, before_val, after_val, evidence)
                    VALUES ('dataset_order', %s, 'package_dataset', 'runpod',
                            '{"state":"PACKAGING"}'::jsonb, '{"state":"READY"}'::jsonb,
                            %s::jsonb)
                    """,
                    (
                        order_id,
                        json.dumps(
                            {
                                "delivery_id": delivery_id,
                                "dataset_version": dataset_version,
                                "manifest_sha256": manifest.sha256,
                            }
                        ),
                    ),
                )
                package_response = {
                    "received": True,
                    "status": "READY",
                    "delivery_id": delivery_id,
                }
        if package_response is not None:
            return package_response
        batch = connection.execute(
            """
            SELECT id, status::text, result_metrics
            FROM gpu_jobs
            WHERE order_id = %s AND stage = 'reconstruction'
            ORDER BY created_at
            """,
            (order_id,),
        ).fetchall()
    if any(str(job[1]) in {"PENDING", "RUNNING"} for job in batch):
        return {"received": True, "status": target_status, "waiting_for_batch": True}

    metric_documents = [dict(job[2] or {}) for job in batch]
    failed = any(str(job[1]) != "SUCCEEDED" for job in batch)
    metrics = {
        "frames_total": sum(int(item.get("frames_total", 0)) for item in metric_documents),
        "frames_valid": sum(int(item.get("frames_valid", 0)) for item in metric_documents),
        "gpu_seconds": sum(float(item.get("gpu_seconds", 0)) for item in metric_documents),
        "replay_success": not failed
        and all(bool(item.get("replay_success")) for item in metric_documents),
        "max_penetration_m": max(
            (float(item.get("max_penetration_m", 1)) for item in metric_documents), default=1
        ),
        "contact_phase_f1": min(
            (float(item.get("contact_phase_f1", 0)) for item in metric_documents), default=0
        ),
        "joint_limit_violation_count": sum(
            int(item.get("joint_limit_violation_count", 1)) for item in metric_documents
        ),
        "trajectory_duration_s": sum(
            float(item.get("trajectory_duration_s", 0)) for item in metric_documents
        ),
    }
    batch_subject_id = "batch_" + order_id.removeprefix("ord_")
    run_id = start_workflow_task("deterministic_validation", [order_id, batch_subject_id, metrics])
    return {"received": True, "task_run_id": run_id}


@router.get("/{job_id}")
def get_job(
    job_id: str,
    ctx: TenantContext = Depends(require_tenant),
) -> dict:
    with get_conn() as connection:
        row = connection.execute(
            """
            SELECT j.id, j.order_id, j.stage, j.attempt, j.status::text, j.provider_job_id,
                   j.error_code, j.error_message, j.gpu_seconds, j.created_at, j.completed_at
            FROM gpu_jobs j
            JOIN dataset_orders o ON o.id = j.order_id
            WHERE j.id = %s AND o.tenant_id = %s
            """,
            (job_id, ctx.tenant_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": row[0],
        "order_id": row[1],
        "stage": row[2],
        "attempt": row[3],
        "status": row[4],
        "provider_job_id": row[5],
        "error_code": row[6],
        "error_message": row[7],
        "gpu_seconds": float(row[8]) if row[8] else None,
        "created_at": row[9].isoformat(),
        "completed_at": row[10].isoformat() if row[10] else None,
    }
