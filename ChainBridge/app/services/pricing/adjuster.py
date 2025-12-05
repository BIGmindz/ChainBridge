"""Financial adjuster applying fuzzy scores to payouts."""

from __future__ import annotations

import logging
from typing import Dict

from app.services.chain_audit.fuzzy_engine import get_payout_confidence

logger = logging.getLogger(__name__)


def calculate_final_settlement(invoice_amount: float, telemetry: Dict[str, float]) -> Dict[str, object]:
    delta = telemetry.get("delta_temp_c", 0.0)
    duration = telemetry.get("duration_mins", 0.0)
    score = get_payout_confidence(delta, duration)

    if score >= 95:
        final = invoice_amount
        status = "FULL_PAYMENT"
        reason = "Full payout; telemetry nominal"
    elif score < 40:
        final = 0.0
        status = "BLOCKED"
        reason = "Severe breach; payout blocked"
    else:
        penalty_pct = (95 - score) * 0.5
        final = max(0.0, invoice_amount * (1 - penalty_pct / 100))
        status = "PARTIAL_SETTLEMENT"
        reason = f"Penalty {penalty_pct:.1f}% applied"
        if penalty_pct > 5:
            logger.warning(
                "fuzzy_adjustment_large",
                extra={"penalty_pct": penalty_pct, "score": score},
            )

    return {
        "confidence_score": score,
        "final_payout": round(final, 2),
        "status": status,
        "adjustment_reason": reason,
    }
