from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from typing import Any

import httpx

from forge.integrations.config import required_env
from forge.integrations.pioneer.provider import PioneerVerdict


@dataclass(frozen=True)
class PioneerCallResult:
    external_id: str | None
    verdict: dict[str, Any]


class PioneerInferenceClient:
    """Serve learned QC on pseudonymous metrics; raw media is rejected at the boundary."""

    def __init__(
        self,
        *,
        api_key: str,
        model_id: str,
        timeout_seconds: float = 30,
        api_base_url: str = "https://api.pioneer.ai/v1",
        threshold_version: str = "forge-quality-thresholds-v1",
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.api_base_url = api_base_url.rstrip("/")
        self.threshold_version = threshold_version
        self.http_client = http_client

    @classmethod
    def from_env(cls, timeout_seconds: float = 30) -> PioneerInferenceClient:
        return cls(
            api_key=required_env("PIONEER_API_KEY"),
            model_id=os.getenv("PIONEER_MODEL_ID", "Qwen/Qwen3-8B"),
            timeout_seconds=timeout_seconds,
            api_base_url=os.getenv("PIONEER_API_BASE_URL", "https://api.pioneer.ai/v1"),
            threshold_version=os.getenv("PIONEER_THRESHOLD_VERSION", "forge-quality-thresholds-v1"),
        )

    def infer(
        self, purpose: str, correlation_id: str, features: dict[str, Any]
    ) -> PioneerCallResult:
        stage_by_purpose = {"pre_qc": "PRE_HEAVY", "final_qc": "POST_REPLAY"}
        if purpose not in stage_by_purpose:
            raise ValueError(f"PIONEER_PURPOSE_UNSUPPORTED:{purpose}")
        self._reject_media(features)
        subject_id = str(features.get("subject_id", "")).strip()
        if not subject_id:
            raise ValueError("PIONEER_SUBJECT_ID_MISSING")

        prompt = (
            "You are FORGE's conservative robot-dataset quality classifier. "
            "Never override deterministic failures. Return JSON only with keys "
            "source_usable_probability, physics_pass_probability, recommended_action, "
            "reason_codes, next_capture_instruction. Input features: "
            + json.dumps(features, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        )
        post = self.http_client.post if self.http_client else httpx.post
        response = post(
            f"{self.api_base_url}/chat/completions",
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            json={
                "model": self.model_id,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        raw = response.json()
        try:
            content = raw["choices"][0]["message"]["content"]
            parsed = json.loads(content) if isinstance(content, str) else dict(content)
            verdict = PioneerVerdict(
                verdict_id=f"pio_{correlation_id}",
                subject_id=subject_id,
                inference_stage=stage_by_purpose[purpose],
                source_usable_probability=float(parsed["source_usable_probability"]),
                physics_pass_probability=float(parsed["physics_pass_probability"]),
                recommended_action=str(parsed["recommended_action"]),
                reason_codes=tuple(str(item) for item in parsed.get("reason_codes", [])),
                next_capture_instruction=(
                    str(parsed["next_capture_instruction"])
                    if parsed.get("next_capture_instruction")
                    else None
                ),
                provider="pioneer",
                model_id=self.model_id,
                model_version=str(raw.get("model", self.model_id)),
                evaluation_id=str(raw.get("id", correlation_id)),
                threshold_version=self.threshold_version,
                simulation=False,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError("PIONEER_VERDICT_INVALID") from error

        encoded = asdict(verdict)
        encoded["reason_codes"] = list(verdict.reason_codes)
        external_id = str(raw.get("id", "")) or None
        return PioneerCallResult(external_id=external_id, verdict=encoded)

    @classmethod
    def _reject_media(cls, value: Any, path: str = "features") -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                lowered = str(key).lower()
                if any(token in lowered for token in ("video", "image", "media", "signed_url")):
                    raise ValueError(f"PIONEER_MEDIA_FIELD_FORBIDDEN:{path}.{key}")
                cls._reject_media(item, f"{path}.{key}")
        elif isinstance(value, (list, tuple)):
            for index, item in enumerate(value):
                cls._reject_media(item, f"{path}[{index}]")
        elif isinstance(value, str) and value.lower().startswith(("http://", "https://", "r2://")):
            raise ValueError(f"PIONEER_MEDIA_REFERENCE_FORBIDDEN:{path}")
