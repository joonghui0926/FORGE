from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


QualityRoute = Literal["ACCEPT", "RECOLLECT", "REVIEW", "BLOCK"]


@dataclass(frozen=True)
class QualityDecision:
    route: QualityRoute
    reason_codes: tuple[str, ...]
    evidence_artifact_ids: tuple[str, ...]
    requested_captures: tuple[dict[str, Any], ...] = ()
    operator_summary: str = ""
    confidence: float = 0.0

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "QualityDecision":
        route = str(payload.get("route", "")).upper()
        if route not in {"ACCEPT", "RECOLLECT", "REVIEW", "BLOCK"}:
            raise ValueError("BAND_DECISION_ROUTE_INVALID")
        confidence = float(payload.get("confidence", 0.0))
        if not 0 <= confidence <= 1:
            raise ValueError("BAND_DECISION_CONFIDENCE_INVALID")
        reason_codes = tuple(str(value) for value in payload.get("reason_codes", ()))
        if route != "ACCEPT" and not reason_codes:
            raise ValueError("BAND_DECISION_REASON_REQUIRED")
        requested = tuple(payload.get("requested_captures", ()))
        if route == "RECOLLECT" and not requested:
            raise ValueError("BAND_RECOLLECT_CAPTURE_PLAN_REQUIRED")
        return cls(
            route=route,  # type: ignore[arg-type]
            reason_codes=reason_codes,
            evidence_artifact_ids=tuple(
                str(value) for value in payload.get("evidence_artifact_ids", ())
            ),
            requested_captures=requested,
            operator_summary=str(payload.get("operator_summary", "")),
            confidence=confidence,
        )


def route_task_name(decision: QualityDecision) -> str:
    return {
        "ACCEPT": "package_dataset",
        "RECOLLECT": "create_terac_campaign",
        # Zero-human operations: ambiguous evidence closes safely instead of creating QA labor.
        "REVIEW": "close_with_evidence",
        "BLOCK": "close_with_evidence",
    }[decision.route]
