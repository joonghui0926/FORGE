from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Literal

from ..auth import require_tenant
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
    stripe_payment_link: str | None


@router.post("", status_code=status.HTTP_201_CREATED, response_model=OrderResponse)
def create_order(
    body: CreateOrderRequest,
    ctx: TenantContext = Depends(require_tenant),
) -> OrderResponse:
    # TODO: persist to DB, create Stripe payment intent
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    ctx: TenantContext = Depends(require_tenant),
) -> OrderResponse:
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("", response_model=list[OrderResponse])
def list_orders(
    ctx: TenantContext = Depends(require_tenant),
) -> list[OrderResponse]:
    raise HTTPException(status_code=501, detail="Not implemented")
