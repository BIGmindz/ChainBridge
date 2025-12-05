"""Deterministic ChainAudit reconciliation helper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from api.models.chainpay import PaymentIntent


@dataclass
class AuditResult:
    payout_confidence: float
    auto_adjusted_amount: float
    reconciliation_explanation: List[str]

    def to_dict(self) -> dict:
        return {
            "payout_confidence": self.payout_confidence,
            "auto_adjusted_amount": self.auto_adjusted_amount,
            "reconciliation_explanation": list(self.reconciliation_explanation),
        }


def reconcile_payment_intent(
    intent: PaymentIntent,
    *,
    issues: Sequence[str] | None = None,
    blocked: bool = False,
) -> AuditResult:
    """Deterministic ruleset; can be swapped for fuzzy engine later."""
    issues = list(issues or [])
    base_amount = intent.calculated_amount or intent.amount or 0.0
    risk_level = (intent.risk_level or "").upper()
    explanation: List[str] = []

    if blocked or risk_level == "CRITICAL" or "BLOCKED" in [i.upper() for i in issues]:
        explanation.append("blocked_or_critical_risk")
        return AuditResult(
            payout_confidence=0.0,
            auto_adjusted_amount=0.0,
            reconciliation_explanation=explanation,
        )

    if risk_level == "HIGH":
        reduction = min(0.15, 0.05 + 0.02 * len(issues))
        confidence = max(0.8, 0.95 - reduction)
        adjusted = round(base_amount * (1 - reduction), 2)
        explanation.append(f"high_risk_reduction_{int(reduction*100)}pct")
        if issues:
            explanation.append(f"issues:{','.join(sorted(issues))}")
        return AuditResult(
            payout_confidence=round(confidence, 3),
            auto_adjusted_amount=adjusted,
            reconciliation_explanation=explanation,
        )

    explanation.append("baseline_clearance")
    if issues:
        explanation.append(f"issues:{','.join(sorted(issues))}")
    return AuditResult(
        payout_confidence=1.0,
        auto_adjusted_amount=round(base_amount, 2),
        reconciliation_explanation=explanation,
    )
