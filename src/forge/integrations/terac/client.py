from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from forge.integrations.config import required_env


@dataclass(frozen=True)
class TeracCampaignResult:
    campaign_id: str
    response: dict[str, Any]


class TeracCampaignClient:
    """Turn an approved collection plan into a Terac workforce campaign."""

    def __init__(
        self,
        *,
        bridge_url: str,
        token: str,
        timeout_seconds: float = 30,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.bridge_url = bridge_url
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.http_client = http_client

    @classmethod
    def from_env(cls, timeout_seconds: float = 30) -> TeracCampaignClient:
        return cls(
            bridge_url=required_env("TERAC_MCP_BRIDGE_URL"),
            token=required_env("TERAC_MCP_BRIDGE_TOKEN"),
            timeout_seconds=timeout_seconds,
        )

    def create_campaign(
        self, correlation_id: str, collection_plan: dict[str, Any]
    ) -> TeracCampaignResult:
        post = self.http_client.post if self.http_client else httpx.post
        response = post(
            self.bridge_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Idempotency-Key": correlation_id,
            },
            json={
                "action": "create_campaign",
                "correlation_id": correlation_id,
                "plan": collection_plan,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        campaign_id = str(body.get("campaign_id", "")).strip()
        if not campaign_id:
            raise RuntimeError("TERAC_CAMPAIGN_ID_MISSING")
        return TeracCampaignResult(campaign_id=campaign_id, response=body)
