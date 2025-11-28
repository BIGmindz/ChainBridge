"""Pricing adjuster that applies fuzzy confidence to settlement payouts."""
from __future__ import annotations

from typing import Dict

from api.services.chain_audit.fuzzy_engine import get_payout_confidence


def calculate_final_settlement(invoice_amount: float, telemetry_data: dict) -> Dict[str, object]:
    max_delta = telemetry_data.get("max_temp_deviation", 0.0) or 0.0
    duration = telemetry_data.get("breach_duration_minutes", 0.0) or 0.0

    score = get_payout_confidence(max_delta, duration)

    if score >= 95:
        status = "FULL_PAYMENT"
        final = invoice_amount
        reason = "Full payout; conditions nominal"
    elif score < 40:
        status = "BLOCKED"
        final = 0.0
        reason = "Breach too severe; payout blocked"
    else:
        penalty_factor = (95 - score) * 0.5  # percent
        deduction = invoice_amount * (penalty_factor / 100.0)
        final = max(0.0, invoice_amount - deduction)
        status = "PARTIAL_SETTLEMENT"
        reason = f"Penalty {penalty_factor:.1f}% applied"

    return {
        "original_invoice": invoice_amount,
        "confidence_score": score,
        "final_payout": round(final, 2),
        "status": status,
        "adjustment_reason": reason,
    }
