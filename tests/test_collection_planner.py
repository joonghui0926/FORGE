from __future__ import annotations

import unittest

from forge.modules.collection.planner import CollectionPlanner, CustomerTaskRequest


class CollectionPlannerTest(unittest.TestCase):
    def test_aerial_task_requires_expert_and_full_flight_observability(self) -> None:
        request = CustomerTaskRequest(
            request_id="req_drone_inspection",
            tenant_id="tenant_customer",
            task_name="inspect rack",
            task_outcome="visit every inspection waypoint and land",
            motion_family="aerial",
            target_robot_id="customer_quadrotor",
            target_robot_urdf_uri="r2://forge-dev/robots/quadrotor.urdf",
            target_control_rate_hz=100.0,
            environment_description="indoor warehouse",
            counterpart_descriptions=("rack", "landing pad"),
            required_success_conditions=("all waypoints visited", "stable landing"),
            prohibited_failures=("collision", "unstable flight"),
            hazardous=True,
            specialized_equipment=True,
            requested_accepted_demonstrations=10,
        )

        plan = CollectionPlanner().compile(request)

        self.assertEqual(plan.validation_profile, "aerial-flight-v1")
        self.assertEqual(plan.worker_requirement.expertise, "verified_domain_expert")
        self.assertEqual(plan.worker_requirement.minimum_workers, 2)
        self.assertEqual(plan.capture_requirements[0].minimum_frame_rate_hz, 60)
        self.assertIn("airframe", plan.capture_requirements[0].required_visible_entities)
        self.assertGreater(plan.initial_assignment_count, plan.target_accepted_demonstrations)

    def test_non_hazardous_manipulation_can_use_general_contributor(self) -> None:
        request = CustomerTaskRequest(
            request_id="req_pack_box",
            tenant_id="tenant_customer",
            task_name="pack carton",
            task_outcome="place item and close carton",
            motion_family="manipulation",
            target_robot_id="customer_arm",
            target_robot_urdf_uri="https://customer.example/arm.urdf",
            target_control_rate_hz=20.0,
            environment_description="tabletop",
            counterpart_descriptions=("carton", "item"),
            required_success_conditions=("item in carton",),
            prohibited_failures=("drop item",),
        )

        plan = CollectionPlanner().compile(request)

        self.assertEqual(plan.worker_requirement.expertise, "general_contributor")
        self.assertEqual(plan.validation_profile, "manipulation-rigid-v1")
        self.assertEqual(len(plan.sha256), 64)
