from __future__ import annotations

from typing import Any

from render_sdk import Retry, Workflows

from .decision import QualityDecision, route_task_name
from .runtime import WorkflowRuntime


app = Workflows(
    default_retry=Retry(max_retries=3, wait_duration_ms=1_000, backoff_scaling=2),
    default_timeout=300,
    default_plan="starter",
)


@app.task(name="order_paid")
async def order_paid(order_id: str) -> dict[str, Any]:
    await validate_contract(order_id)
    return await request_band_collection_plan(order_id)


@app.task
def validate_contract(order_id: str) -> dict[str, Any]:
    return WorkflowRuntime().validate_contract(order_id)


@app.task
def request_band_collection_plan(order_id: str) -> dict[str, Any]:
    runtime = WorkflowRuntime()
    plan = runtime.compile_collection_plan(order_id)
    correlation_id = runtime.request_band(order_id, "collection_plan", plan)
    runtime.wait(order_id, "request_band_collection_plan", {"band_correlation_id": correlation_id})
    return {"status": "WAITING_FOR_BAND", "correlation_id": correlation_id}


@app.task
def create_terac_campaign(order_id: str, collection_plan: dict[str, Any]) -> dict[str, Any]:
    runtime = WorkflowRuntime()
    response = runtime.create_terac_campaign(order_id, collection_plan)
    runtime.transition(
        order_id, {"PLANNING", "RECOLLECTING"}, "ACQUIRING", "create_terac_campaign", response
    )
    return response


@app.task
async def fast_pre_qc(
    order_id: str, capture_ids: list[str], features: dict[str, Any]
) -> dict[str, Any]:
    runtime = WorkflowRuntime()
    features = runtime.build_capture_features(order_id, capture_ids, features)
    hard_failures = list(features.get("deterministic_hard_failures", []))
    passed = not hard_failures and float(features.get("capture_valid_ratio", 0)) >= 0.8
    payload = {"passed": passed, "hard_failures": hard_failures, "features": features}
    runtime.record_pre_qc(order_id, capture_ids, features, passed)
    runtime.transition(order_id, {"ACQUIRING", "PRE_QC"}, "PRE_QC", "fast_pre_qc", payload)
    if not passed:
        runtime.wait(order_id, "fast_pre_qc_failed", payload)
        return await request_band_quality_decision(order_id, {"pre_qc": payload})
    pioneer = await request_pioneer_pre_qc(order_id, features)
    job = await submit_runpod_gpu_job(order_id, capture_ids)
    return {"pre_qc": payload, "pioneer": pioneer, "runpod": job}


@app.task
def request_pioneer_pre_qc(order_id: str, features: dict[str, Any]) -> dict[str, Any]:
    runtime = WorkflowRuntime()
    if features.get("deterministic_hard_failures"):
        raise RuntimeError("PIONEER_CANNOT_OVERRIDE_HARD_FAILURE")
    verdict = runtime.request_pioneer(order_id, "pre_qc", features)
    runtime.transition(order_id, {"PRE_QC"}, "PROCESSING", "request_pioneer_pre_qc", verdict)
    return verdict


@app.task(timeout_seconds=900)
def submit_runpod_gpu_job(order_id: str, capture_ids: list[str]) -> dict[str, Any]:
    runtime = WorkflowRuntime()
    jobs = [runtime.submit_runpod(order_id, capture_id) for capture_id in capture_ids]
    result = {"jobs": jobs, "capture_count": len(capture_ids)}
    runtime.wait(order_id, "submit_runpod_gpu_job", result)
    return result


@app.task
async def deterministic_validation(
    order_id: str, job_id: str, metrics: dict[str, Any]
) -> dict[str, Any]:
    runtime = WorkflowRuntime()
    order = runtime.load_order(order_id)
    quality = order["contract"]["quality"]
    expected_claim = (order["contract"].get("output") or {}).get(
        "claim_level", "sim_validated_robot_trajectory"
    )
    motion_family = order["contract"]["skill"].get("motion_family", "whole_body")
    failures: list[str] = []
    if metrics.get("claim_level") != expected_claim:
        failures.append("OUTPUT_CLAIM_MISMATCH")
    frames_total = int(metrics.get("frames_total", 0))
    frames_valid = int(metrics.get("frames_valid", 0))
    if frames_total <= 0 or frames_valid / frames_total < 0.8:
        failures.append("VALID_FRAME_RATIO_LOW")
    if expected_claim == "sim_validated_robot_trajectory":
        if not bool(metrics.get("replay_success", False)):
            failures.append("REPLAY_FAILED")
        if float(metrics.get("max_penetration_m", 1)) > float(quality["max_penetration_m"]):
            failures.append("PENETRATION_LIMIT_EXCEEDED")
        if int(metrics.get("joint_limit_violation_count", 1)) > 0:
            failures.append("JOINT_LIMIT_VIOLATION")
        if motion_family in {"manipulation", "bimanual", "tool_use", "mobile_manipulation"}:
            if float(metrics.get("contact_phase_f1", 0)) < float(quality["min_contact_phase_f1"]):
                failures.append("CONTACT_PHASE_F1_LOW")
    result = {"subject_id": job_id, "passed": not failures, "hard_failures": failures, **metrics}
    runtime.record_validation_qc(order_id, job_id, result)
    runtime.transition(
        order_id, {"PROCESSING", "VALIDATING"}, "VALIDATING", "deterministic_validation", result
    )
    pioneer = await request_pioneer_final_verdict(order_id, result)
    return await request_band_quality_decision(
        order_id,
        {"deterministic_validation": result, "pioneer_verdict": pioneer},
    )


@app.task
def request_pioneer_final_verdict(order_id: str, features: dict[str, Any]) -> dict[str, Any]:
    runtime = WorkflowRuntime()
    if features.get("hard_failures"):
        return {
            "recommended_action": "REJECT_HARD_GATE",
            "reason_codes": list(features["hard_failures"]),
            "subject_id": features["subject_id"],
        }
    verdict = runtime.request_pioneer(order_id, "final_qc", features)
    runtime.transition(
        order_id, {"VALIDATING"}, "BATCH_QC", "request_pioneer_final_verdict", verdict
    )
    return verdict


@app.task
def request_band_quality_decision(order_id: str, evidence: dict[str, Any]) -> dict[str, Any]:
    runtime = WorkflowRuntime()
    correlation_id = runtime.request_band(order_id, "quality_decision", evidence)
    runtime.wait(order_id, "request_band_quality_decision", {"band_correlation_id": correlation_id})
    return {"status": "WAITING_FOR_BAND", "correlation_id": correlation_id}


@app.task
async def apply_band_quality_decision(order_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    runtime = WorkflowRuntime()
    decision = QualityDecision.from_payload(payload)
    active_hard_failures = runtime.latest_hard_failures(order_id)
    if decision.route == "ACCEPT" and active_hard_failures:
        return await close_with_evidence(
            order_id,
            {
                "route": "BLOCK",
                "reason_codes": ["BAND_HARD_GATE_OVERRIDE_REJECTED", *active_hard_failures],
                "evidence_artifact_ids": list(decision.evidence_artifact_ids),
                "policy_version": "forge-hard-gate-v2",
            },
        )
    task = route_task_name(decision)
    if task == "package_dataset":
        return await package_dataset(order_id, payload)
    if task == "create_terac_campaign":
        runtime.transition(
            order_id,
            {"PRE_QC", "BATCH_QC", "VALIDATING"},
            "RECOLLECTING",
            task,
            payload,
        )
        plan = runtime.compile_collection_plan(order_id)
        plan["recollection_request"] = {
            "reason_codes": list(decision.reason_codes),
            "requested_captures": list(decision.requested_captures),
        }
        return await create_terac_campaign(order_id, plan)
    if task == "operator_queue":
        return await operator_queue(order_id, payload)
    return await close_with_evidence(order_id, payload)


@app.task
def package_dataset(order_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    runtime = WorkflowRuntime()
    runtime.transition(
        order_id, {"BATCH_QC", "PACKAGING"}, "PACKAGING", "package_dataset", decision
    )
    job = runtime.submit_package(order_id, decision)
    runtime.wait(order_id, "package_dataset_waiting_for_artifact", {"package_job": job})
    return {"status": "PACKAGING", "order_id": order_id, "job": job}


@app.task
def operator_queue(order_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    runtime = WorkflowRuntime()
    runtime.enqueue_operator_review(order_id, decision)
    runtime.transition(
        order_id,
        {"PRE_QC", "BATCH_QC", "VALIDATING"},
        "REVIEW",
        "operator_queue",
        decision,
        "WAITING",
    )
    return {"status": "REVIEW", "order_id": order_id}


@app.task
def close_with_evidence(order_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    runtime = WorkflowRuntime()
    runtime.transition(
        order_id,
        {"PRE_QC", "BATCH_QC", "VALIDATING"},
        "BLOCKED",
        "close_with_evidence",
        decision,
        "COMPLETED",
    )
    return {"status": "BLOCKED", "order_id": order_id}
