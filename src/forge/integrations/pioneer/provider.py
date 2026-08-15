from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
import os


@dataclass(frozen=True)
class PioneerFeatures:
    subject_id: str
    motion_family: str
    validation_profile: str
    reconstruction_valid_ratio: float
    contact_observability: float
    occlusion_ratio: float
    replay_success: bool | None
    max_penetration_m: float | None
    contact_phase_f1: float | None
    deterministic_hard_failures: tuple[str, ...]
    coverage_cell: str
    feature_version: str = "forge-qc-features-v1"

    def __post_init__(self) -> None:
        for field_name in ("reconstruction_valid_ratio", "contact_observability", "occlusion_ratio"):
            value = float(getattr(self, field_name))
            if not 0 <= value <= 1:
                raise ValueError(f"{field_name} must be in [0, 1]")
        if "://" in self.coverage_cell:
            raise ValueError("Pioneer features cannot contain media URLs")


@dataclass(frozen=True)
class PioneerVerdict:
    verdict_id: str
    subject_id: str
    inference_stage: str
    source_usable_probability: float
    physics_pass_probability: float
    recommended_action: str
    reason_codes: tuple[str, ...]
    next_capture_instruction: str | None
    provider: str
    model_id: str
    model_version: str
    evaluation_id: str
    threshold_version: str
    simulation: bool
    schema_version: str = "forge.pioneer-verdict.v1"

    def __post_init__(self) -> None:
        for probability in (self.source_usable_probability, self.physics_pass_probability):
            if not 0 <= probability <= 1:
                raise ValueError("Pioneer probabilities must be in [0, 1]")
        if not self.simulation and self.provider == "forge-fixture":
            raise ValueError("fixture provider must be marked simulation")


class PioneerProvider(Protocol):
    def infer(
        self, features: PioneerFeatures, inference_stage: str, environment: str
    ) -> PioneerVerdict: ...


class FixturePioneerProvider:
    """Deterministic local feature, never a production substitute."""

    def infer(
        self, features: PioneerFeatures, inference_stage: str, environment: str
    ) -> PioneerVerdict:
        if environment == "production":
            raise RuntimeError("PIONEER_FIXTURE_FORBIDDEN_IN_PRODUCTION")
        if inference_stage not in {"PRE_HEAVY", "POST_REPLAY"}:
            raise ValueError("unsupported Pioneer inference stage")

        usable = max(
            0.0,
            min(
                1.0,
                0.55 * features.reconstruction_valid_ratio
                + 0.35 * features.contact_observability
                + 0.10 * (1.0 - features.occlusion_ratio),
            ),
        )
        if features.deterministic_hard_failures:
            usable = min(usable, 0.05)
        physics = (
            0.5 * usable
            + 0.3 * (1.0 if features.replay_success else 0.0)
            + 0.2 * (features.contact_phase_f1 or 0.0)
        )
        physics = max(0.0, min(1.0, physics))

        if features.deterministic_hard_failures:
            action = "REJECT_HARD_GATE"
            reasons = features.deterministic_hard_failures
            instruction = None
        elif features.occlusion_ratio > 0.35:
            action = "RECOLLECT_GENERAL"
            reasons = ("CONTACT_OCCLUDED",)
            instruction = "Keep the active body region and its counterpart visible through contact."
        elif inference_stage == "PRE_HEAVY" and usable < 0.65:
            action = "REVIEW_BEFORE_GPU"
            reasons = ("SOURCE_USABILITY_LOW",)
            instruction = "Repeat the motion with a stable camera and full-body visibility."
        elif inference_stage == "POST_REPLAY" and physics < 0.65:
            action = "RECOLLECT_OR_RETARGET"
            reasons = ("PHYSICS_PASS_PROBABILITY_LOW",)
            instruction = "Capture a slower execution with clearer support and contact transitions."
        else:
            action = "CONTINUE"
            reasons = ()
            instruction = None

        return PioneerVerdict(
            verdict_id=f"fixture_{features.subject_id}_{inference_stage.lower()}",
            subject_id=features.subject_id,
            inference_stage=inference_stage,
            source_usable_probability=usable,
            physics_pass_probability=physics,
            recommended_action=action,
            reason_codes=tuple(reasons),
            next_capture_instruction=instruction,
            provider="forge-fixture",
            model_id="deterministic-fixture",
            model_version="v1",
            evaluation_id="fixture-eval-v1",
            threshold_version="fixture-threshold-v1",
            simulation=True,
        )


class ProductionPioneerProvider:
    """Fail-closed boundary until the authenticated Pioneer API adapter is configured."""

    def __init__(self, api_key: str | None = None, project_id: str | None = None) -> None:
        self.api_key = api_key or os.getenv("PIONEER_API_KEY")
        self.project_id = project_id or os.getenv("PIONEER_PROJECT_ID")

    def infer(
        self, features: PioneerFeatures, inference_stage: str, environment: str
    ) -> PioneerVerdict:
        if environment != "production":
            raise RuntimeError("PRODUCTION_PIONEER_PROVIDER_REQUIRES_PRODUCTION_ENV")
        if not self.api_key or not self.project_id:
            raise RuntimeError("PIONEER_NOT_CONFIGURED")
        raise RuntimeError("PIONEER_API_ADAPTER_PENDING_ACCOUNT_SCHEMA_CONFIRMATION")
