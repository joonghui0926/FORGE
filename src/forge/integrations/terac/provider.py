from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from forge.modules.collection.planner import CollectionPlan


@dataclass(frozen=True)
class TeracAssignment:
    external_assignment_id: str
    plan_id: str
    status: str
    requested_workers: int
    accepted_take_target: int
    provider: str = "terac"
    schema_version: str = "forge.terac-assignment.v1"


class TeracProvider(Protocol):
    def create_assignment(self, plan: CollectionPlan, environment: str) -> TeracAssignment: ...


class ProductionTeracProvider:
    """Fails closed until the sponsor confirms its authenticated write API schema."""

    def create_assignment(self, plan: CollectionPlan, environment: str) -> TeracAssignment:
        if environment != "production":
            raise RuntimeError("TERAC_WRITE_REQUIRES_PRODUCTION_ENV")
        raise RuntimeError("TERAC_API_ADAPTER_PENDING_SPONSOR_SCHEMA_AND_AUTHORIZATION")
