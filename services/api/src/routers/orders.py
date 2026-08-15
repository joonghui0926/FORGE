import json
import os
import secrets
import stripe
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Literal

from ..auth import require_tenant
from ..db import get_conn
from ..models import TenantContext

router = APIRouter()

_STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
_STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
_APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:3000")

def _new_id(prefix: str) -> str:
    return f"{prefix}{secrets.token_urlsafe(12)}"


class SkillSpec(BaseModel):
    name: str
    initial_state: str
    success_predicate: str
    failure_predicates: list[str]
    phases: list[str]


class EmbodimentSpec(BaseModel):
    robot_id: str
    model_uri: str        # r2://...
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
                (order_id, ctx.user_id, json.dumps({"state": "DRAFT", "skill_name": body.skill.name})),
            )
    stripe_payment_link: str | None = None
    if _STRIPE_KEY and _STRIPE_PRICE_ID:
        stripe.api_key = _STRIPE_KEY
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{"price": _STRIPE_PRICE_ID, "quantity": body.volume_validated_episodes}],
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
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, ctx: TenantContext = Depends(require_tenant)) -> OrderResponse:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, state, skill_name, created_at, contract,
                   (contract->'volume'->>'validated_episodes')::int AS validated_episodes
            FROM dataset_orders
            WHERE id = %s AND tenant_id = %s
            """,
            (order_id, ctx.tenant_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse(
        order_id=row[0],
        state=row[1],
        skill_name=row[2],
        created_at=row[3].isoformat() if row[3] else None,
        contract=row[4],
        volume_validated_episodes=row[5],
        stripe_payment_link=None,
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
