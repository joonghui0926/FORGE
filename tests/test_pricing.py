from __future__ import annotations

from decimal import Decimal
import unittest

from forge.business.pricing import (
    InfrastructureAssumptions,
    minimum_contract_price,
    monthly_infrastructure_cost,
)


class PricingTest(unittest.TestCase):
    def test_recommended_ten_user_infrastructure_scenario(self) -> None:
        cost = monthly_infrastructure_cost(
            InfrastructureAssumptions(
                render_workspace_monthly_usd=Decimal("25"),
                render_compute_budget_monthly_usd=Decimal("100"),
                render_workflow_hours=Decimal("20"),
                render_workflow_hourly_usd=Decimal("0.20"),
                pioneer_seats=2,
                pioneer_seat_monthly_usd=Decimal("20"),
                r2_standard_gb_month=Decimal("200"),
                r2_free_gb_month=Decimal("10"),
                r2_storage_gb_month_usd=Decimal("0.015"),
                runpod_gpu_hours=Decimal("176"),
                runpod_gpu_hourly_usd=Decimal("0.44"),
            )
        )

        self.assertEqual(cost.render_usd, Decimal("129.00"))
        self.assertEqual(cost.pioneer_usd, Decimal("40.00"))
        self.assertEqual(cost.r2_storage_usd, Decimal("2.85"))
        self.assertEqual(cost.runpod_gpu_usd, Decimal("77.44"))
        self.assertEqual(cost.total_usd, Decimal("249.29"))

    def test_price_floor_hits_target_margin(self) -> None:
        self.assertEqual(
            minimum_contract_price(Decimal("5000"), Decimal("0.67")), Decimal("15151.52")
        )
