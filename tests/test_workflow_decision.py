from services.workflows.src.decision import QualityDecision, route_task_name


def test_quality_decision_routes_are_exhaustive() -> None:
    expected = {
        "ACCEPT": "package_dataset",
        "RECOLLECT": "create_terac_campaign",
        "REVIEW": "operator_queue",
        "BLOCK": "close_with_evidence",
    }
    for route, task in expected.items():
        payload = {
            "route": route,
            "reason_codes": [] if route == "ACCEPT" else ["TEST_REASON"],
            "requested_captures": [{"count": 1}] if route == "RECOLLECT" else [],
            "confidence": 0.9,
        }
        assert route_task_name(QualityDecision.from_payload(payload)) == task


def test_recollect_requires_capture_plan() -> None:
    try:
        QualityDecision.from_payload(
            {"route": "RECOLLECT", "reason_codes": ["COVERAGE_GAP"], "confidence": 0.7}
        )
    except ValueError as error:
        assert str(error) == "BAND_RECOLLECT_CAPTURE_PLAN_REQUIRED"
    else:
        raise AssertionError("recollection without a capture plan must fail closed")
