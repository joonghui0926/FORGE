from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from forge.contracts.models import content_hash


MOTION_PROFILES: dict[str, dict[str, object]] = {
    "manipulation": {
        "validation_profile": "manipulation-rigid-v1",
        "views": ("task-wide", "active-effector-and-counterpart"),
        "visibility": ("active_effector", "counterpart", "contact_transition"),
    },
    "bimanual": {
        "validation_profile": "manipulation-rigid-v1",
        "views": ("task-wide", "both-effectors-and-counterpart"),
        "visibility": ("both_effectors", "counterpart", "contact_transition"),
    },
    "tool_use": {
        "validation_profile": "manipulation-rigid-v1",
        "views": ("task-wide", "tool-tip-and-workpiece"),
        "visibility": ("tool", "workpiece", "tool_contact"),
    },
    "locomotion": {
        "validation_profile": "locomotion-flat-v1",
        "views": ("full-path-wide", "support-contact"),
        "visibility": ("root", "support_contacts", "terrain"),
    },
    "whole_body": {
        "validation_profile": "locomotion-flat-v1",
        "views": ("full-body-wide", "support-and-object"),
        "visibility": ("whole_actor", "support_contacts", "counterpart"),
    },
    "mobile_manipulation": {
        "validation_profile": "mobile-manipulation-v1",
        "views": ("full-base-path", "effector-and-counterpart"),
        "visibility": ("mobile_base", "active_effector", "counterpart"),
    },
    "navigation": {
        "validation_profile": "navigation-ground-v1",
        "views": ("route-wide", "clearance-critical-zones"),
        "visibility": ("platform", "route", "obstacles"),
    },
    "articulated_machine": {
        "validation_profile": "navigation-ground-v1",
        "views": ("machine-wide", "control-and-work-zone"),
        "visibility": ("machine_links", "work_zone", "obstacles"),
    },
    "aerial": {
        "validation_profile": "aerial-flight-v1",
        "views": ("flight-volume-wide", "takeoff-and-landing"),
        "visibility": ("airframe", "flight_volume", "obstacles"),
    },
    "multi_robot": {
        "validation_profile": "multi-robot-coordination-v1",
        "views": ("shared-workspace-wide", "handoff-or-conflict-zone"),
        "visibility": ("all_actors", "shared_workspace", "synchronization_event"),
    },
}


@dataclass(frozen=True)
class CustomerTaskRequest:
    request_id: str
    tenant_id: str
    task_name: str
    task_outcome: str
    motion_family: str
    target_robot_id: str
    target_robot_urdf_uri: str
    target_control_rate_hz: float
    environment_description: str
    counterpart_descriptions: tuple[str, ...]
    required_success_conditions: tuple[str, ...]
    prohibited_failures: tuple[str, ...]
    source_preferences: tuple[str, ...] = ("human_video", "robot_state", "teleop_log")
    hazardous: bool = False
    regulated: bool = False
    specialized_equipment: bool = False
    requested_accepted_demonstrations: int = 20
    participant_count: int = 3
    clips_per_participant: int = 6
    minimum_unique_environments: int = 2
    participant_expertise: str = "general_contributor"
    capture_mode: str = "mixed_views"
    success_takes_per_participant: int = 4
    failure_takes_per_participant: int = 1
    recovery_takes_per_participant: int = 1

    def __post_init__(self) -> None:
        if not self.request_id.startswith("req_"):
            raise ValueError("request_id must start with req_")
        if self.motion_family not in MOTION_PROFILES:
            raise ValueError("motion family has no production validation profile")
        if not self.target_robot_urdf_uri.startswith(("r2://", "https://", "file://")):
            raise ValueError("target robot description must be an immutable artifact or URL")
        if self.target_control_rate_hz <= 0:
            raise ValueError("target_control_rate_hz must be positive")
        if self.requested_accepted_demonstrations < 1:
            raise ValueError("requested demonstrations must be positive")
        if self.participant_count < 2:
            raise ValueError("production collection requires at least two participants")
        if self.clips_per_participant < 2:
            raise ValueError("each participant must record at least two clips")
        if self.minimum_unique_environments < 1:
            raise ValueError("minimum_unique_environments must be positive")
        if self.minimum_unique_environments > self.participant_count:
            raise ValueError("unique environments cannot exceed participants")
        if self.participant_expertise not in {
            "general_contributor",
            "experienced_practitioner",
            "verified_domain_expert",
        }:
            raise ValueError("unsupported participant expertise")
        if self.capture_mode not in {
            "egocentric",
            "third_person",
            "mixed_views",
            "synchronized_multiview",
        }:
            raise ValueError("unsupported capture mode")
        take_count = (
            self.success_takes_per_participant
            + self.failure_takes_per_participant
            + self.recovery_takes_per_participant
        )
        if take_count != self.clips_per_participant:
            raise ValueError(
                "success, failure, and recovery takes must equal clips_per_participant"
            )
        if not self.required_success_conditions or not self.prohibited_failures:
            raise ValueError("success and prohibited-failure criteria are required")


@dataclass(frozen=True)
class CaptureRequirement:
    requirement_id: str
    view: str
    description: str
    minimum_frame_rate_hz: int
    minimum_resolution: str
    continuous_recording: bool
    required_visible_entities: tuple[str, ...]


@dataclass(frozen=True)
class WorkerRequirement:
    expertise: str
    minimum_workers: int
    reason_codes: tuple[str, ...]
    requires_site_authorization: bool
    requires_safety_briefing: bool


@dataclass(frozen=True)
class CollectionPlan:
    plan_id: str
    request_id: str
    motion_family: str
    validation_profile: str
    target_accepted_demonstrations: int
    target_source_clips: int
    target_participant_count: int
    clips_per_participant: int
    minimum_unique_environments: int
    capture_mode: str
    per_participant_take_mix: dict[str, int]
    initial_assignment_count: int
    reserve_assignment_count: int
    capture_requirements: tuple[CaptureRequirement, ...]
    worker_requirement: WorkerRequirement
    per_take_protocol: tuple[str, ...]
    rejection_codes: tuple[str, ...]
    rights_requirements: tuple[str, ...]
    compiler_version: str = "forge-collection-planner-v1"
    schema_version: str = "forge.collection-plan.v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def sha256(self) -> str:
        return content_hash(self.to_dict())


class CollectionPlanner:
    """Deterministically compiles a signed customer task into a worker-ready packet."""

    version = "forge-collection-planner-v1"

    def compile(self, request: CustomerTaskRequest) -> CollectionPlan:
        profile = MOTION_PROFILES[request.motion_family]
        expert_reasons: list[str] = []
        if request.hazardous:
            expert_reasons.append("HAZARDOUS_TASK")
        if request.regulated:
            expert_reasons.append("REGULATED_TASK")
        if request.specialized_equipment:
            expert_reasons.append("SPECIALIZED_EQUIPMENT")
        if request.motion_family in {"aerial", "articulated_machine"}:
            expert_reasons.append("LICENSE_OR_PLATFORM_COMPETENCE_REQUIRED")

        required_expertise = (
            "verified_domain_expert" if expert_reasons else request.participant_expertise
        )
        worker = WorkerRequirement(
            expertise=required_expertise,
            minimum_workers=request.participant_count,
            reason_codes=tuple(expert_reasons) or ("NO_SPECIALIST_CONSTRAINT_IDENTIFIED",),
            requires_site_authorization=request.regulated or request.specialized_equipment,
            requires_safety_briefing=request.hazardous or request.specialized_equipment,
        )

        views = tuple(str(view) for view in profile["views"])  # type: ignore[arg-type]
        visible = tuple(str(entity) for entity in profile["visibility"])  # type: ignore[arg-type]
        capture = tuple(
            CaptureRequirement(
                requirement_id=f"capture_{index:02d}",
                view=view,
                description=f"Keep {', '.join(visible)} observable for the entire take.",
                minimum_frame_rate_hz=60 if request.motion_family == "aerial" else 30,
                minimum_resolution="1920x1080",
                continuous_recording=True,
                required_visible_entities=visible,
            )
            for index, view in enumerate(views, start=1)
        )

        # One assignment is one participant session containing multiple immutable source clips.
        # Reserve participants protect demographic/environment diversity when a full session fails.
        reserve = max(1, (request.participant_count + 4) // 5)
        initial = request.participant_count + reserve
        plan_seed = {
            "request_id": request.request_id,
            "version": self.version,
            "motion_family": request.motion_family,
            "target_robot_id": request.target_robot_id,
        }
        return CollectionPlan(
            plan_id=f"plan_{content_hash(plan_seed)[:20]}",
            request_id=request.request_id,
            motion_family=request.motion_family,
            validation_profile=str(profile["validation_profile"]),
            target_accepted_demonstrations=request.requested_accepted_demonstrations,
            target_source_clips=request.participant_count * request.clips_per_participant,
            target_participant_count=request.participant_count,
            clips_per_participant=request.clips_per_participant,
            minimum_unique_environments=request.minimum_unique_environments,
            capture_mode=request.capture_mode,
            per_participant_take_mix={
                "success": request.success_takes_per_participant,
                "failure": request.failure_takes_per_participant,
                "recovery": request.recovery_takes_per_participant,
            },
            initial_assignment_count=initial,
            reserve_assignment_count=reserve,
            capture_requirements=capture,
            worker_requirement=worker,
            per_take_protocol=(
                "Record calibration reference and environment before motion.",
                "Record a neutral start state, one continuous execution, and a neutral end state.",
                "Do not cut, zoom, apply stabilization, or alter frame rate.",
                "Upload the declared number of success, failure, and recovery takes separately.",
                "A recovery take must begin from a declared failed or perturbed state.",
                "Never replace or edit a failed source; its relationship to recovery is metadata.",
                "Upload original media plus device metadata and signed rights receipt.",
            ),
            rejection_codes=(
                "MISSING_RIGHTS_RECEIPT",
                "EDITED_OR_TRANSCODED_SOURCE",
                "CRITICAL_ENTITY_OCCLUDED",
                "INCOMPLETE_START_OR_END_STATE",
                "UNSAFE_EXECUTION",
                "TASK_OUTCOME_NOT_OBSERVED",
            ),
            rights_requirements=(
                "worker_consent",
                "location_release",
                "customer_training_and_evaluation_license",
                "retention_and_deletion_policy_acknowledgement",
            ),
        )
