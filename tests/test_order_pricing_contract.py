from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

os.environ.setdefault("DATABASE_URL", "postgresql://forge:forge@localhost:5432/forge")

from services.api.src.routers.orders import CreateOrderRequest


def _starter_order(episodes: int) -> dict:
    return {
        "skill": {
            "name": "pick and place",
            "motion_family": "manipulation",
            "initial_state": "object on table",
            "success_predicate": "object in target bin",
            "failure_predicates": ["object dropped"],
            "phases": ["approach", "grasp", "place"],
        },
        "embodiment": {
            "robot_id": "customer-arm",
            "model_uri": "r2://forge-dev/robots/customer-arm.urdf",
            "model_sha256": "a" * 64,
            "hand_type": "parallel_gripper",
            "joint_limits_uri": "r2://forge-dev/robots/customer-arm-joints.json",
        },
        "volume_validated_episodes": episodes,
        "coverage": {
            "object_ids": ["sample-object"],
            "viewpoint_bins": ["front"],
            "grasp_variation": "preferred",
        },
        "quality": {
            "source_replay_pass_required": True,
            "max_penetration_m": 0.002,
            "min_contact_phase_f1": 0.8,
            "min_delivery_acceptance_rate": 0.9,
        },
        "rights_profile": "customer_exclusive_derivatives",
    }


@pytest.mark.parametrize("episodes", [1, 10])
def test_350_dollar_starter_accepts_one_to_ten_episodes(episodes: int) -> None:
    assert (
        CreateOrderRequest.model_validate(_starter_order(episodes)).volume_validated_episodes
        == episodes
    )


@pytest.mark.parametrize("episodes", [0, 11, 1000])
def test_350_dollar_starter_rejects_out_of_scope_volume(episodes: int) -> None:
    with pytest.raises(ValidationError):
        CreateOrderRequest.model_validate(_starter_order(episodes))
