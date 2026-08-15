from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Literal

from ..auth import require_tenant
from ..db import get_conn
from ..models import TenantContext

router = APIRouter()


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
    # TODO: persist to DB, create Stripe payment intent
    raise HTTPException(status_code=501, detail="Not implemented")


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
