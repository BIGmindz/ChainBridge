"""Policies controlling reconciliation tolerances and auto-pay rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReconciliationPolicy:
    id: str
    qty_tolerance_percent: float
    price_tolerance_percent: float
    max_temp_excursion_minutes: int
    temp_discount_percent: float
    allow_auto_pay_above_amount: bool
    auto_pay_cap_amount: float | None
    auto_partial_pay_percent_for_minor_issues: float


DEFAULT_POLICY = ReconciliationPolicy(
    id="global_default_r01",
    qty_tolerance_percent=2.0,
    price_tolerance_percent=1.0,
    max_temp_excursion_minutes=0,
    temp_discount_percent=10.0,
    allow_auto_pay_above_amount=False,
    auto_pay_cap_amount=50_000.0,
    auto_partial_pay_percent_for_minor_issues=0.9,
)
