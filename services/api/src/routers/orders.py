import json
import os
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from forge.integrations.stripe import build_order_payment_link
from pydantic import BaseModel, Field
import stripe
from typing import Literal

from ..auth import require_tenant
from ..db import get_conn
from ..models import TenantContext

router = APIRouter()

_STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
_STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
_STRIPE_PAYMENT_LINK_URL = os.environ.get("STRIPE_PAYMENT_LINK_URL", "")
_APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:3000")


def _new_id(prefix: str) -> str:
    return f"{prefix}{secrets.token_urlsafe(12)}"


class SkillSpec(BaseModel):
    name: str
    motion_family: Literal[
        "manipulation",
        "bimanual",
        "tool_use",
        "locomotion",
        "whole_body",
        "mobile_manipulation",
        "navigation",
        "articulated_machine",
        "aerial",
        "multi_robot",
    ]
    initial_state: str
    success_predicate: str
    failure_predicates: list[str]
    phases: list[str]


class EmbodimentSpec(BaseModel):
    robot_id: str
    model_uri: str  # r2://...
    model_sha256: str
    hand_type: Literal["dexterous", "parallel_gripper", "suction"]
    joint_limits_uri: str


class QualitySpec(BaseModel):
    source_replay_pass_required: bool
    max_penetration_m: float
    min_contact_phase_f1: float
    min_delivery_acceptance_rate: float


class CoverageSpec(BaseModel):
    object_ids: list[str]
    viewpoint_bins: list[str]
    grasp_variation: Literal["required", "preferred", "not_required"] = "preferred"


class CreateOrderRequest(BaseModel):
    skill: SkillSpec
    embodiment: EmbodimentSpec
    volume_validated_episodes: int
    coverage: CoverageSpec
    quality: QualitySpec
    rights_profile: Literal["customer_exclusive_derivatives", "forge_retained", "open"]


class OrderResponse(BaseModel):
    order_id: str
    state: str
    stripe_payment_link: str | None = None
    skill_name: str | None = None
    created_at: str | None = None
    volume_validated_episodes: int | None = None
    contract: dict | None = None
    pipeline: list[dict] = Field(default_factory=list)
    workspace: dict = Field(default_factory=dict)


def _workspace_data(connection, order_id: str, payment_reference: str | None) -> dict:
    batches = connection.execute(
        """
        SELECT b.id, b.sequence, b.terac_campaign_id, b.created_at,
               COUNT(d.id) AS submitted,
               COUNT(d.id) FILTER (WHERE d.state IN ('PRE_QC_PASSED', 'VALIDATION_PASSED'))
                 AS accepted
        FROM capture_batches b
        LEFT JOIN demonstrations d ON d.batch_id = b.id
        WHERE b.order_id = %s
        GROUP BY b.id, b.sequence, b.terac_campaign_id, b.created_at
        ORDER BY b.sequence ASC
        """,
        (order_id,),
    ).fetchall()
    captures = connection.execute(
        """
        SELECT id, state::text, object_id, viewpoint_bin, submitted_at
        FROM demonstrations
        WHERE order_id = %s
        ORDER BY submitted_at DESC
        LIMIT 200
        """,
        (order_id,),
    ).fetchall()
    provider_requests = connection.execute(
        """
        SELECT provider, purpose, state, external_id, correlation_id, created_at, completed_at
        FROM provider_requests
        WHERE order_id = %s
        ORDER BY created_at DESC
        LIMIT 100
        """,
        (order_id,),
    ).fetchall()
    jobs = connection.execute(
        """
        SELECT id, stage, attempt, status::text, pipeline_version, provider_job_id,
               gpu_seconds, result_metrics, error_code, created_at, completed_at
        FROM gpu_jobs
        WHERE order_id = %s
        ORDER BY created_at DESC
        LIMIT 100
        """,
        (order_id,),
    ).fetchall()
    qc_runs = connection.execute(
        """
        SELECT id, subject_type, stage, passed, reason_codes, metrics, thresholds,
               simulation, created_at
        FROM qc_runs
        WHERE order_id = %s
        ORDER BY created_at DESC
        LIMIT 100
        """,
        (order_id,),
    ).fetchall()
    decisions = connection.execute(
        """
        SELECT id, decision_type, reason_codes, confidence, policy_version,
               requires_human_approval, approved_by, created_at
        FROM decisions
        WHERE order_id = %s
        ORDER BY created_at DESC
        LIMIT 100
        """,
        (order_id,),
    ).fetchall()
    episodes = connection.execute(
        """
        SELECT id, kind::text, source_id, lineage_group_id, batch_qc_passed,
               delivered, created_at
        FROM episodes
        WHERE order_id = %s
        ORDER BY created_at DESC
        LIMIT 500
        """,
        (order_id,),
    ).fetchall()
    delivery = connection.execute(
        """
        SELECT id, dataset_version, rights_profile, manifest, created_at
        FROM deliveries
        WHERE order_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (order_id,),
    ).fetchone()
    workflow = connection.execute(
        """
        SELECT status, current_step, render_root_run_id, last_error_code,
               last_error_message, updated_at
        FROM workflow_runs
        WHERE order_id = %s
        """,
        (order_id,),
    ).fetchone()

    providers = [
        {
            "provider": row[0],
            "purpose": row[1],
            "state": row[2],
            "external_id": row[3],
            "correlation_id": row[4],
            "created_at": row[5].isoformat(),
            "completed_at": row[6].isoformat() if row[6] else None,
        }
        for row in provider_requests
    ]
    delivery_summary = None
    if delivery:
        manifest = dict(delivery[3] or {})
        delivery_summary = {
            "delivery_id": delivery[0],
            "dataset_version": delivery[1],
            "rights_profile": delivery[2],
            "schema_version": manifest.get("schema_version"),
            "episode_count": manifest.get("episode_count"),
            "artifact_count": len(manifest.get("artifacts", [])),
            "created_at": delivery[4].isoformat(),
        }

    return {
        "acquisition": {
            "batches": [
                {
                    "batch_id": row[0],
                    "sequence": row[1],
                    "terac_campaign_id": row[2],
                    "created_at": row[3].isoformat(),
                    "submitted": row[4],
                    "accepted": row[5],
                }
                for row in batches
            ],
            "captures": [
                {
                    "capture_id": row[0],
                    "state": row[1],
                    "object_id": row[2],
                    "viewpoint_bin": row[3],
                    "submitted_at": row[4].isoformat(),
                }
                for row in captures
            ],
            "provider_requests": [
                item
                for item in providers
                if item["provider"] == "terac"
                or (item["provider"] == "band" and item["purpose"] == "collection_plan")
            ],
        },
        "processing": {
            "workflow": (
                {
                    "status": workflow[0],
                    "current_step": workflow[1],
                    "render_root_run_id": workflow[2],
                    "last_error_code": workflow[3],
                    "last_error_message": workflow[4],
                    "updated_at": workflow[5].isoformat(),
                }
                if workflow
                else None
            ),
            "jobs": [
                {
                    "job_id": row[0],
                    "stage": row[1],
                    "attempt": row[2],
                    "status": row[3],
                    "pipeline_version": row[4],
                    "provider_job_id": row[5],
                    "gpu_seconds": float(row[6]) if row[6] is not None else None,
                    "metrics": row[7] or {},
                    "error_code": row[8],
                    "created_at": row[9].isoformat(),
                    "completed_at": row[10].isoformat() if row[10] else None,
                }
                for row in jobs
            ],
        },
        "quality": {
            "runs": [
                {
                    "qc_run_id": row[0],
                    "subject_type": row[1],
                    "stage": row[2],
                    "passed": row[3],
                    "reason_codes": list(row[4] or []),
                    "metrics": row[5] or {},
                    "thresholds": row[6] or {},
                    "simulation": row[7],
                    "created_at": row[8].isoformat(),
                }
                for row in qc_runs
            ],
            "decisions": [
                {
                    "decision_id": row[0],
                    "decision_type": row[1],
                    "reason_codes": list(row[2] or []),
                    "confidence": float(row[3]) if row[3] is not None else None,
                    "policy_version": row[4],
                    "requires_human_approval": row[5],
                    "approved_by": row[6],
                    "created_at": row[7].isoformat(),
                }
                for row in decisions
            ],
            "provider_requests": [
                item
                for item in providers
                if item["provider"] == "pioneer"
                or (item["provider"] == "band" and item["purpose"] == "quality_decision")
            ],
        },
        "episodes": [
            {
                "episode_id": row[0],
                "kind": row[1],
                "source_id": row[2],
                "lineage_group_id": row[3],
                "batch_qc_passed": row[4],
                "delivered": row[5],
                "created_at": row[6].isoformat(),
            }
            for row in episodes
        ],
        "delivery": delivery_summary,
        "billing": {
            "payment_status": "paid" if payment_reference else "awaiting_payment",
            "payment_reference": (f"...{payment_reference[-8:]}" if payment_reference else None),
        },
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=OrderResponse)
def create_order(
    body: CreateOrderRequest,
    ctx: TenantContext = Depends(require_tenant),
) -> OrderResponse:
    order_id = _new_id("ord_")
    contract = {
        "schema_version": "forge.order.v1",
        "order_id": order_id,
        "tenant_id": ctx.tenant_id,
        "skill": body.skill.model_dump(),
        "embodiment": body.embodiment.model_dump(),
        "volume": {"validated_episodes": body.volume_validated_episodes},
        "coverage": body.coverage.model_dump(),
        "quality": body.quality.model_dump(),
        "rights_profile": body.rights_profile,
    }
    with get_conn() as conn:
        with conn.transaction():
            conn.execute(
                """
                INSERT INTO tenants (id, slug, name)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (ctx.tenant_id, ctx.tenant_id, ctx.user_id),
            )
            conn.execute(
                """
                INSERT INTO dataset_orders
                  (id, tenant_id, state, skill_name, contract)
                VALUES (%s, %s, 'DRAFT', %s, %s::jsonb)
                """,
                (order_id, ctx.tenant_id, body.skill.name, json.dumps(contract)),
            )
            conn.execute(
                """
                INSERT INTO audit_events
                  (entity_type, entity_id, action, actor, after_val)
                VALUES ('dataset_order', %s, 'created', %s, %s::jsonb)
                """,
                (
                    order_id,
                    ctx.user_id,
                    json.dumps({"state": "DRAFT", "skill_name": body.skill.name}),
                ),
            )
    stripe_payment_link: str | None = None
    if _STRIPE_PAYMENT_LINK_URL:
        stripe_payment_link = build_order_payment_link(_STRIPE_PAYMENT_LINK_URL, order_id)
    elif _STRIPE_KEY and _STRIPE_PRICE_ID:
        stripe.api_key = _STRIPE_KEY
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{"price": _STRIPE_PRICE_ID, "quantity": 1}],
                metadata={"order_id": order_id, "tenant_id": ctx.tenant_id},
                success_url=f"{_APP_BASE_URL}/orders/{order_id}?payment=success",
                cancel_url=f"{_APP_BASE_URL}/orders/{order_id}?payment=cancelled",
            )
            stripe_payment_link = session.url
        except stripe.StripeError as exc:
            raise HTTPException(status_code=502, detail=f"Stripe error: {exc.user_message}")
    return OrderResponse(
        order_id=order_id,
        state="DRAFT",
        stripe_payment_link=stripe_payment_link,
        skill_name=body.skill.name,
        volume_validated_episodes=body.volume_validated_episodes,
        contract=contract,
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, ctx: TenantContext = Depends(require_tenant)) -> OrderResponse:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, state, skill_name, created_at, contract,
                   stripe_payment_intent,
                   (contract->'volume'->>'validated_episodes')::int AS validated_episodes
            FROM dataset_orders
            WHERE id = %s AND tenant_id = %s
            """,
            (order_id, ctx.tenant_id),
        ).fetchone()
        pipeline_rows = conn.execute(
            """
            SELECT action, actor, after_val, evidence, created_at
            FROM audit_events
            WHERE entity_type = 'dataset_order' AND entity_id = %s
            ORDER BY created_at ASC, id ASC
            """,
            (order_id,),
        ).fetchall()
        workspace = _workspace_data(conn, order_id, row[5] if row else None) if row else {}
    if row is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse(
        order_id=row[0],
        state=row[1],
        skill_name=row[2],
        created_at=row[3].isoformat() if row[3] else None,
        contract=row[4],
        volume_validated_episodes=row[6],
        stripe_payment_link=None,
        pipeline=[
            {
                "step": event[0],
                "actor": event[1],
                "state": (event[2] or {}).get("state"),
                "evidence": event[3] or {},
                "created_at": event[4].isoformat(),
            }
            for event in pipeline_rows
        ],
        workspace=workspace,
    )


@router.get("", response_model=list[OrderResponse])
def list_orders(ctx: TenantContext = Depends(require_tenant)) -> list[OrderResponse]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, state, skill_name, created_at,
                   (contract->'volume'->>'validated_episodes')::int AS validated_episodes
            FROM dataset_orders
            WHERE tenant_id = %s
            ORDER BY created_at DESC
            """,
            (ctx.tenant_id,),
        ).fetchall()
    return [
        OrderResponse(
            order_id=row[0],
            state=row[1],
            skill_name=row[2],
            created_at=row[3].isoformat() if row[3] else None,
            volume_validated_episodes=row[4],
            stripe_payment_link=None,
        )
        for row in rows
    ]
