from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from forge.contracts.models import ArtifactRef, GPUJobRequest, content_hash


@dataclass(frozen=True)
class ReconstructionRecipe:
    recipe_id: str
    motion_families: tuple[str, ...]
    source_actor_types: tuple[str, ...]
    observation_types: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    expected_artifact_kinds: tuple[str, ...]
    paper_lineage: tuple[str, ...]
    camera_requirements: tuple[str, ...]


RECIPES: dict[str, ReconstructionRecipe] = {
    "manipulation-metric-v1": ReconstructionRecipe(
        recipe_id="manipulation-metric-v1",
        motion_families=("manipulation", "bimanual", "tool_use", "mobile_manipulation"),
        source_actor_types=("human", "robot", "mixed", "unknown"),
        observation_types=("monocular_video", "multiview_video", "multimodal"),
        required_capabilities=(
            "metric_depth_and_intrinsics",
            "active_region_segmentation",
            "rigid_counterpart_pose",
            "hand_or_effector_kinematics",
            "gravity_estimation",
        ),
        expected_artifact_kinds=(
            "camera_metric",
            "scene_geometry",
            "counterpart_poses",
            "actor_kinematics",
            "contact_candidates",
        ),
        paper_lineage=("VideoManip", "C2Dex", "Do As I Do"),
        camera_requirements=("metric_calibratable", "contact_visible"),
    ),
    "whole-body-metric-v1": ReconstructionRecipe(
        recipe_id="whole-body-metric-v1",
        motion_families=(
            "locomotion",
            "whole_body",
            "mobile_manipulation",
            "navigation",
            "articulated_machine",
        ),
        source_actor_types=("human", "robot", "mixed", "unknown"),
        observation_types=("monocular_video", "multiview_video", "multimodal"),
        required_capabilities=(
            "metric_depth_and_intrinsics",
            "dynamic_camera_estimation",
            "whole_body_kinematics",
            "scene_geometry",
            "environment_contact_candidates",
            "gravity_estimation",
        ),
        expected_artifact_kinds=(
            "camera_metric",
            "scene_geometry",
            "root_trajectory",
            "actor_kinematics",
            "environment_contacts",
        ),
        paper_lineage=("FORGE generalized reconstruction profile",),
        camera_requirements=("full_body_visible", "ground_plane_observable"),
    ),
    "robot-state-direct-v1": ReconstructionRecipe(
        recipe_id="robot-state-direct-v1",
        motion_families=(
            "manipulation",
            "bimanual",
            "locomotion",
            "whole_body",
            "mobile_manipulation",
            "tool_use",
            "navigation",
            "aerial",
            "articulated_machine",
            "multi_robot",
            "custom",
        ),
        source_actor_types=("robot", "mixed", "simulation"),
        observation_types=("robot_state", "teleop_log", "simulation_trace", "multimodal"),
        required_capabilities=(
            "robot_state_normalization",
            "clock_synchronization",
            "source_kinematic_calibration",
        ),
        expected_artifact_kinds=(
            "root_trajectory",
            "actor_kinematics",
            "counterpart_poses",
            "contact_candidates",
        ),
        paper_lineage=("FORGE direct robot-state compiler",),
        camera_requirements=(),
    ),
    "aerial-metric-v1": ReconstructionRecipe(
        recipe_id="aerial-metric-v1",
        motion_families=("aerial",),
        source_actor_types=("robot", "simulation", "unknown"),
        observation_types=(
            "monocular_video",
            "multiview_video",
            "robot_state",
            "teleop_log",
            "simulation_trace",
            "multimodal",
        ),
        required_capabilities=(
            "six_dof_state_estimation",
            "clock_synchronization",
            "source_kinematic_calibration",
        ),
        expected_artifact_kinds=("root_trajectory", "actor_kinematics", "scene_geometry"),
        paper_lineage=("FORGE aerial source adapter",),
        camera_requirements=("scale_observable_or_telemetry",),
    ),
}


@dataclass(frozen=True)
class ReconstructionRequest:
    job_id: str
    source_artifact: ArtifactRef
    source_actor_type: str
    source_observation_type: str
    motion_family: str
    recipe_id: str
    config_uri: str
    output_prefix: str
    pipeline_version: str


class ExternalReconstructionAdapter:
    """Converts a typed request into a pinned RunPod job.

    Third-party weights and repositories are never vendored into FORGE. Production
    job creation checks that every recipe capability has an approved, digest-pinned
    implementation in the third-party lock.
    """

    def __init__(
        self,
        container_image: str,
        third_party_lock_path: Path,
        environment: str,
    ) -> None:
        self.container_image = container_image
        self.third_party_lock_path = third_party_lock_path
        self.environment = environment

    def build_job(self, request: ReconstructionRequest) -> GPUJobRequest:
        recipe = RECIPES.get(request.recipe_id)
        if recipe is None:
            raise ValueError("RECONSTRUCTION_RECIPE_UNSUPPORTED")
        if request.motion_family not in recipe.motion_families:
            raise ValueError("RECONSTRUCTION_RECIPE_MOTION_MISMATCH")
        if request.source_actor_type not in recipe.source_actor_types:
            raise ValueError("RECONSTRUCTION_RECIPE_SOURCE_ACTOR_MISMATCH")
        if request.source_observation_type not in recipe.observation_types:
            raise ValueError("RECONSTRUCTION_RECIPE_OBSERVATION_MISMATCH")
        self._assert_capabilities_licensed(recipe)
        key_payload = {
            "stage": "reconstruction",
            "input": request.source_artifact.sha256,
            "config": request.config_uri,
            "container": self.container_image,
            "pipeline": request.pipeline_version,
            "recipe": request.recipe_id,
            "source_actor_type": request.source_actor_type,
            "source_observation_type": request.source_observation_type,
        }
        return GPUJobRequest(
            job_id=request.job_id,
            idempotency_key=content_hash(key_payload),
            stage="reconstruction",
            input_artifacts=(request.source_artifact,),
            config_uri=request.config_uri,
            container_image=self.container_image,
            pipeline_version=request.pipeline_version,
            output_prefix=request.output_prefix,
        )

    def _assert_capabilities_licensed(self, recipe: ReconstructionRecipe) -> None:
        if not self.third_party_lock_path.exists():
            raise RuntimeError("THIRD_PARTY_LOCK_MISSING")
        document = json.loads(self.third_party_lock_path.read_text(encoding="utf-8"))
        capability_status: dict[str, str] = {}
        for dependency in document.get("dependencies", []):
            for capability in dependency.get("capabilities", []):
                status = dependency.get("production_status", "blocked")
                if status == "approved":
                    capability_status[capability] = status
                else:
                    capability_status.setdefault(capability, status)
        missing = [
            capability
            for capability in recipe.required_capabilities
            if capability not in capability_status
        ]
        blocked = [
            capability
            for capability in recipe.required_capabilities
            if capability_status.get(capability) != "approved"
        ]
        if missing:
            raise RuntimeError(f"RECONSTRUCTION_CAPABILITY_UNRESOLVED:{','.join(missing)}")
        if self.environment == "production" and blocked:
            raise RuntimeError(f"RECONSTRUCTION_LICENSE_BLOCKED:{','.join(blocked)}")
