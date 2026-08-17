from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any

import httpx

from forge.integrations.config import required_env


@dataclass(frozen=True)
class BandAgentTarget:
    agent_id: str
    name: str
    handle: str


@dataclass(frozen=True)
class BandDispatch:
    external_id: str | None
    response: dict[str, Any]


class BandDecisionClient:
    """Ask Band for schema-constrained operating decisions; never execute effects here."""

    def __init__(
        self,
        *,
        api_key: str,
        room_id: str,
        collection_target: BandAgentTarget,
        quality_target: BandAgentTarget,
        timeout_seconds: float = 30,
        api_base_url: str = "https://app.band.ai/api/v1",
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.room_id = room_id
        self.collection_target = collection_target
        self.quality_target = quality_target
        self.timeout_seconds = timeout_seconds
        self.api_base_url = api_base_url.rstrip("/")
        self.http_client = http_client

    @classmethod
    def from_env(cls, timeout_seconds: float = 30) -> BandDecisionClient:
        return cls(
            api_key=required_env("BAND_API_KEY"),
            room_id=required_env("BAND_ROOM_ID"),
            collection_target=BandAgentTarget(
                agent_id=required_env("BAND_COLLECTION_AGENT_ID"),
                name=os.getenv("BAND_COLLECTION_AGENT_NAME", "Collection Architect"),
                handle=required_env("BAND_COLLECTION_AGENT_HANDLE"),
            ),
            quality_target=BandAgentTarget(
                agent_id=required_env("BAND_QUALITY_AGENT_ID"),
                name=os.getenv("BAND_QUALITY_AGENT_NAME", "Quality Council"),
                handle=required_env("BAND_QUALITY_AGENT_HANDLE"),
            ),
            timeout_seconds=timeout_seconds,
            api_base_url=os.getenv("BAND_API_BASE_URL", "https://app.band.ai/api/v1"),
        )

    def request_decision(
        self, purpose: str, correlation_id: str, payload: dict[str, Any]
    ) -> BandDispatch:
        if purpose == "collection_plan":
            target = self.collection_target
        elif purpose == "quality_decision":
            target = self.quality_target
        else:
            raise ValueError(f"BAND_PURPOSE_UNSUPPORTED:{purpose}")

        content = (
            f"@{target.handle.lstrip('@')} FORGE {purpose} decision required. "
            "Operate without manual QA: deterministic hard gates are not overridable; "
            "choose RECOLLECT for remediable evidence gaps and BLOCK for unsafe or ambiguous evidence. "
            f"Return only signed decision JSON containing correlation_id={correlation_id}.\n"
            + json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        )
        request = {
            "message": {
                "content": content,
                "mentions": [{"id": target.agent_id, "name": target.name, "handle": target.handle}],
            }
        }
        post = self.http_client.post if self.http_client else httpx.post
        response = post(
            f"{self.api_base_url}/agent/chats/{self.room_id}/messages",
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            json=request,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        external_id = str(body.get("id") or body.get("message", {}).get("id") or "") or None
        return BandDispatch(external_id=external_id, response=body)
