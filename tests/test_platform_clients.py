from __future__ import annotations

import json

import httpx
import pytest

from forge.integrations.band import BandAgentTarget, BandDecisionClient
from forge.integrations.pioneer import PioneerInferenceClient
from forge.integrations.render import RenderWorkflowClient, WorkflowDispatchError
from forge.integrations.terac import TeracCampaignClient


def client_for(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler)


def test_terac_creates_an_idempotent_campaign_first() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://terac.example/bridge"
        assert request.headers["authorization"] == "Bearer terac-secret"
        assert request.headers["idempotency-key"] == "order-001"
        assert json.loads(request.content) == {
            "action": "create_campaign",
            "correlation_id": "order-001",
            "plan": {"task": "bin picking", "accepted_take_target": 120},
        }
        return httpx.Response(200, json={"campaign_id": "terac-campaign-7"})

    with client_for(httpx.MockTransport(handle)) as http_client:
        result = TeracCampaignClient(
            bridge_url="https://terac.example/bridge",
            token="terac-secret",
            http_client=http_client,
        ).create_campaign("order-001", {"task": "bin picking", "accepted_take_target": 120})

    assert result.campaign_id == "terac-campaign-7"


def test_terac_rejects_a_response_without_campaign_id() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"status": "queued"}))
    with client_for(transport) as http_client:
        client = TeracCampaignClient(
            bridge_url="https://terac.example/bridge",
            token="terac-secret",
            http_client=http_client,
        )
        with pytest.raises(RuntimeError, match="TERAC_CAMPAIGN_ID_MISSING"):
            client.create_campaign("order-002", {"task": "walking"})


def test_band_routes_collection_planning_to_the_collection_agent() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://band.example/api/agent/chats/room-1/messages"
        assert request.headers["x-api-key"] == "band-secret"
        body = json.loads(request.content)
        assert body["message"]["mentions"] == [
            {"id": "collection-1", "name": "Collection Architect", "handle": "collector"}
        ]
        assert "correlation_id=order-003" in body["message"]["content"]
        return httpx.Response(200, json={"id": "band-message-3"})

    with client_for(httpx.MockTransport(handle)) as http_client:
        result = BandDecisionClient(
            api_key="band-secret",
            room_id="room-1",
            collection_target=BandAgentTarget(
                agent_id="collection-1", name="Collection Architect", handle="collector"
            ),
            quality_target=BandAgentTarget(
                agent_id="quality-1", name="Quality Council", handle="quality"
            ),
            api_base_url="https://band.example/api",
            http_client=http_client,
        ).request_decision("collection_plan", "order-003", {"task": "door opening"})

    assert result.external_id == "band-message-3"


def test_pioneer_returns_a_structured_pseudonymous_verdict() -> None:
    response_body = {
        "id": "pioneer-eval-4",
        "model": "forge-qc-model-v3",
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "source_usable_probability": 0.94,
                            "physics_pass_probability": 0.89,
                            "recommended_action": "CONTINUE",
                            "reason_codes": [],
                            "next_capture_instruction": None,
                        }
                    )
                }
            }
        ],
    }

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://pioneer.example/v1/chat/completions"
        assert request.headers["x-api-key"] == "pioneer-secret"
        return httpx.Response(200, json=response_body)

    with client_for(httpx.MockTransport(handle)) as http_client:
        result = PioneerInferenceClient(
            api_key="pioneer-secret",
            model_id="forge-qc-model-v3",
            api_base_url="https://pioneer.example/v1",
            http_client=http_client,
        ).infer(
            "pre_qc",
            "order-004",
            {"subject_id": "subject-pseudonym-4", "occlusion_ratio": 0.03},
        )

    assert result.external_id == "pioneer-eval-4"
    assert result.verdict["inference_stage"] == "PRE_HEAVY"
    assert result.verdict["simulation"] is False


def test_pioneer_rejects_raw_media_at_the_provider_boundary() -> None:
    client = PioneerInferenceClient(api_key="key", model_id="model")
    with pytest.raises(ValueError, match="PIONEER_MEDIA_FIELD_FORBIDDEN"):
        client.infer(
            "pre_qc",
            "order-005",
            {"subject_id": "subject-pseudonym-5", "raw_video_url": "r2://private/raw.mp4"},
        )


def test_render_dispatches_a_named_durable_task() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://render.example/v1/task-runs"
        assert request.headers["authorization"] == "Bearer render-secret"
        assert json.loads(request.content) == {
            "task": "forge-control-plane/validate_contract",
            "input": ["order-006"],
        }
        return httpx.Response(201, json={"id": "task-run-6"})

    with client_for(httpx.MockTransport(handle)) as http_client:
        run_id = RenderWorkflowClient(
            api_key="render-secret",
            workflow_slug="forge-control-plane",
            api_base_url="https://render.example/v1",
            http_client=http_client,
        ).start_task("validate_contract", ["order-006"])

    assert run_id == "task-run-6"


def test_render_fails_closed_on_provider_error() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(503, text="unavailable"))
    with client_for(transport) as http_client:
        client = RenderWorkflowClient(
            api_key="render-secret",
            workflow_slug="forge-control-plane",
            http_client=http_client,
        )
        with pytest.raises(WorkflowDispatchError, match="RENDER_TASK_DISPATCH_FAILED:503"):
            client.start_task("validate_contract", ["order-007"])
