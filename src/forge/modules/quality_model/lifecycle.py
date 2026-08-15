from __future__ import annotations

from dataclasses import dataclass
import hashlib

from forge.integrations.pioneer.provider import PioneerFeatures


@dataclass(frozen=True)
class LabeledQualityRecord:
    features: PioneerFeatures
    accepted_label: bool
    physics_pass_label: bool
    source_group_id: str
    operator_reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_group_id or "://" in self.source_group_id:
            raise ValueError("source_group_id must be pseudonymous and non-empty")


def grouped_split(
    records: tuple[LabeledQualityRecord, ...], validation_fraction: float = 0.2
) -> tuple[tuple[LabeledQualityRecord, ...], tuple[LabeledQualityRecord, ...]]:
    """Keeps performer/source/object groups on exactly one side of the split."""
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be in (0, 1)")
    train: list[LabeledQualityRecord] = []
    validation: list[LabeledQualityRecord] = []
    cutoff = int(validation_fraction * 10_000)
    for record in records:
        digest = hashlib.sha256(record.source_group_id.encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % 10_000
        (validation if bucket < cutoff else train).append(record)
    return tuple(train), tuple(validation)


@dataclass(frozen=True)
class QualityEvaluation:
    sample_count: int
    false_accept_rate: float
    false_reject_rate: float
    physics_pass_recall: float
    calibration_error: float


@dataclass(frozen=True)
class PromotionPolicy:
    minimum_samples: int = 100
    maximum_false_accept_rate: float = 0.03
    maximum_false_reject_rate: float = 0.25
    minimum_physics_pass_recall: float = 0.85
    maximum_calibration_error: float = 0.08

    def can_promote(self, challenger: QualityEvaluation, champion: QualityEvaluation) -> bool:
        if challenger.sample_count < self.minimum_samples:
            return False
        guardrails = (
            challenger.false_accept_rate <= self.maximum_false_accept_rate,
            challenger.false_reject_rate <= self.maximum_false_reject_rate,
            challenger.physics_pass_recall >= self.minimum_physics_pass_recall,
            challenger.calibration_error <= self.maximum_calibration_error,
        )
        if not all(guardrails):
            return False
        return (
            challenger.false_accept_rate <= champion.false_accept_rate
            and challenger.physics_pass_recall >= champion.physics_pass_recall
        )
