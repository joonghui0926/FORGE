from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING


MONEY = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY)


@dataclass(frozen=True)
class InfrastructureAssumptions:
    render_workspace_monthly_usd: Decimal
    render_compute_budget_monthly_usd: Decimal
    render_workflow_hours: Decimal
    render_workflow_hourly_usd: Decimal
    pioneer_seats: int
    pioneer_seat_monthly_usd: Decimal
    r2_standard_gb_month: Decimal
    r2_free_gb_month: Decimal
    r2_storage_gb_month_usd: Decimal
    runpod_gpu_hours: Decimal
    runpod_gpu_hourly_usd: Decimal

    def __post_init__(self) -> None:
        numeric = (
            self.render_workspace_monthly_usd,
            self.render_compute_budget_monthly_usd,
            self.render_workflow_hours,
            self.render_workflow_hourly_usd,
            self.pioneer_seat_monthly_usd,
            self.r2_standard_gb_month,
            self.r2_free_gb_month,
            self.r2_storage_gb_month_usd,
            self.runpod_gpu_hours,
            self.runpod_gpu_hourly_usd,
        )
        if any(value < 0 for value in numeric) or self.pioneer_seats < 0:
            raise ValueError("cost assumptions cannot be negative")


@dataclass(frozen=True)
class InfrastructureCost:
    render_usd: Decimal
    pioneer_usd: Decimal
    r2_storage_usd: Decimal
    runpod_gpu_usd: Decimal
    total_usd: Decimal


def monthly_infrastructure_cost(value: InfrastructureAssumptions) -> InfrastructureCost:
    render = _money(
        value.render_workspace_monthly_usd
        + value.render_compute_budget_monthly_usd
        + value.render_workflow_hours * value.render_workflow_hourly_usd
    )
    pioneer = _money(value.pioneer_seat_monthly_usd * value.pioneer_seats)
    billable_r2_gb = max(Decimal("0"), value.r2_standard_gb_month - value.r2_free_gb_month)
    # R2 documents billing-unit rounding, so partial billable GB is charged as a full GB.
    billable_r2_gb = billable_r2_gb.quantize(Decimal("1"), rounding=ROUND_CEILING)
    r2 = _money(billable_r2_gb * value.r2_storage_gb_month_usd)
    runpod = _money(value.runpod_gpu_hours * value.runpod_gpu_hourly_usd)
    return InfrastructureCost(
        render_usd=render,
        pioneer_usd=pioneer,
        r2_storage_usd=r2,
        runpod_gpu_usd=runpod,
        total_usd=_money(render + pioneer + r2 + runpod),
    )


def minimum_contract_price(fully_loaded_cogs_usd: Decimal, target_gross_margin: Decimal) -> Decimal:
    if fully_loaded_cogs_usd < 0:
        raise ValueError("COGS cannot be negative")
    if not Decimal("0") < target_gross_margin < Decimal("1"):
        raise ValueError("target gross margin must be between zero and one")
    return _money(fully_loaded_cogs_usd / (Decimal("1") - target_gross_margin))
