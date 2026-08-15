from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json

from forge.contracts.models import ReplayMetrics
from forge.geometry import Pose
from forge.integrations.pioneer.provider import FixturePioneerProvider, PioneerFeatures
from forge.modules.collection.planner import CollectionPlanner, CustomerTaskRequest
from forge.modules.amplification.compiler import (
    AmplificationCompiler,
    RobotEpisode,
    RobotTrajectorySample,
    WorldTransform,
)
from forge.modules.packaging.delivery import DeliveryBuilder, DeliveryEpisode, DeliveryRequest
from forge.modules.reconstruction.robot_state import (
    RobotStateCompiler,
    RobotStateFrame,
    SourceRobotCalibration,
)
from forge.modules.retarget.planner import RetargetPlanner, RobotCapability
from forge.modules.skill_ir.models import FramePose, SkillPhase
from forge.modules.validation.quality_gate import QualityGate, ValidationInput


SHA = "f" * 64


def main() -> None:
    customer_request = CustomerTaskRequest(
        request_id="req_fixture_locomotion",
        tenant_id="tenant_fixture",
        task_name="walk forward",
        task_outcome="reach the target without a fall",
        motion_family="locomotion",
        target_robot_id="fixture_humanoid",
        target_robot_urdf_uri="r2://forge-dev/robots/fixture_humanoid.urdf",
        target_control_rate_hz=50.0,
        environment_description="flat test surface",
        counterpart_descriptions=("ground",),
        required_success_conditions=("reach target",),
        prohibited_failures=("fall", "self collision"),
        requested_accepted_demonstrations=1,
    )
    collection_plan = CollectionPlanner().compile(customer_request)
    skill_ir = RobotStateCompiler().compile(
        skill_id="skill_fixture_locomotion",
        source_demonstration_id="demo_fixture_robot_state",
        motion_family="locomotion",
        validation_profile=collection_plan.validation_profile,
        calibration=SourceRobotCalibration(
            robot_id="source_humanoid",
            model_uri="r2://forge-dev/robots/source_humanoid.urdf",
            model_sha256=SHA,
            joint_names=("hip", "knee"),
            source_frame_to_canonical_frame={"left_foot": "left_foot"},
            source_length_unit_in_meters=1.0,
            coordinate_convention="right-handed-z-up-meters",
            calibration_artifact_id="artifact_fixture_calibration",
        ),
        frames=(
            RobotStateFrame(
                frame_index=0,
                timestamp_s=0.0,
                source_world_root=Pose.identity(),
                source_frame_poses=(FramePose("left_foot", Pose.identity()),),
                joint_positions=(0.1, 0.2),
            ),
        ),
        phases=(SkillPhase("walk", "walk", 0, 0),),
        counterpart_asset_ids=("ground",),
    )
    retarget_plan = RetargetPlanner().build(
        skill_ir,
        RobotCapability(
            robot_id=customer_request.target_robot_id,
            model_uri=customer_request.target_robot_urdf_uri,
            model_sha256=SHA,
            motion_families=("locomotion",),
            joint_names=("hip", "knee"),
            controllable_frames=("left_foot",),
            supports_physics_replay=True,
        ),
    )
    replay = ReplayMetrics(
        replay_success=True,
        max_penetration_m=0.001,
        contact_phase_f1=0.96,
        joint_limit_violation_count=0,
        trajectory_duration_s=2.0,
        profile_metrics={
            "max_foot_slip_m_s": 0.02,
            "minimum_support_margin_m": 0.03,
            "root_tracking_rmse_m": 0.02,
            "fall_count": 0,
            "self_collision_count": 0,
        },
    )
    source = RobotEpisode(
        episode_id="ep_fixture_source",
        source_demonstration_id="demo_fixture_robot_state",
        motion_family="locomotion",
        validation_profile="locomotion-flat-v1",
        robot_id="fixture_humanoid",
        samples=(
            RobotTrajectorySample(
                timestamp_s=0.0,
                world_root=Pose.identity(),
                frame_poses=(FramePose("left_foot", Pose.identity()),),
                qpos=(0.1, 0.2),
                action=(0.0, 0.0),
            ),
        ),
        replay_artifact_id="artifact_fixture_replay",
    )
    quality = QualityGate().evaluate(
        ValidationInput(
            subject_id=source.episode_id,
            motion_family=source.motion_family,
            profile_id=source.validation_profile,
            replay=replay,
            rights_verified=True,
            checksums_verified=True,
            reconstruction_valid_ratio=0.99,
            contact_observability=0.95,
            evidence_artifact_ids=(source.replay_artifact_id,),
            simulation=True,
        )
    )
    pioneer = FixturePioneerProvider().infer(
        PioneerFeatures(
            subject_id=source.episode_id,
            motion_family=source.motion_family,
            validation_profile=source.validation_profile,
            reconstruction_valid_ratio=0.99,
            contact_observability=0.95,
            occlusion_ratio=0.01,
            replay_success=True,
            max_penetration_m=replay.max_penetration_m,
            contact_phase_f1=replay.contact_phase_f1,
            deterministic_hard_failures=quality.hard_failures,
            coverage_cell="flat-ground:forward",
        ),
        "POST_REPLAY",
        "development",
    )
    generated = AmplificationCompiler().amplify(
        source,
        quality,
        (
            WorldTransform(
                "translate_xy_01",
                Pose(translation_m=(0.5, 0.5, 0.0)),
                "ground_plane",
            ),
        ),
        "development",
    )[0]
    # Generated trajectories must be replayed independently. The fixture uses a
    # second explicit quality result rather than reusing the source verdict.
    generated_quality = QualityGate().evaluate(
        ValidationInput(
            subject_id=generated.episode_id,
            motion_family=source.motion_family,
            profile_id=source.validation_profile,
            replay=replay,
            rights_verified=True,
            checksums_verified=True,
            reconstruction_valid_ratio=0.99,
            contact_observability=0.95,
            evidence_artifact_ids=("artifact_fixture_generated_replay",),
            simulation=True,
        )
    )
    delivery_episode = DeliveryEpisode(
        episode_id=generated.episode_id,
        source_demonstration_id=source.source_demonstration_id,
        parent_episode_id=source.episode_id,
        motion_family=source.motion_family,
        robot_id=source.robot_id,
        trajectory_uri=f"r2://forge-dev/fixture/{generated.episode_id}.npz",
        trajectory_sha256=SHA,
        quality=generated_quality,
    )
    with TemporaryDirectory() as directory:
        target = DeliveryBuilder().build(
            DeliveryRequest(
                order_id="ord_fixture",
                tenant_id="tenant_fixture",
                rights_profile="fixture-only",
                customer_license_text="Fixture; not a customer delivery.",
                skill_ir_artifacts=(
                    {"uri": "r2://forge-dev/fixture/skill.json", "sha256": SHA},
                ),
                episodes=(delivery_episode,),
                model_versions={"forge": "0.1.0", "pioneer": pioneer.model_version},
                production=False,
            ),
            Path(directory),
        )
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        print(
            json.dumps(
                {
                    "status": "fixture_complete",
                    "simulation": True,
                    "collection_plan_id": collection_plan.plan_id,
                    "skill_ir_sha256": skill_ir.sha256,
                    "retarget_constraint_count": len(retarget_plan.constraints),
                    "source_accepted": quality.accepted,
                    "pioneer_action": pioneer.recommended_action,
                    "generated_requires_revalidation": generated.requires_revalidation,
                    "delivered_episode_count": len(manifest["episodes"]),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
