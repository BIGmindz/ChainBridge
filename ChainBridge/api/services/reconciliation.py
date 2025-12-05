"""Service helpers to run reconciliation and update PaymentIntent state."""

from __future__ import annotations

from typing import Dict, Optional

from sqlalchemy.orm import Session

from api.models.chainpay import PaymentIntent
from api.reconciler import (
    DEFAULT_POLICY,
    InvoiceLine,
    PoLine,
    ReconciliationBundle,
    ReconciliationDecision,
    ReconciliationPolicy,
    ReconciliationResult,
    run_reconciliation,
)

RECON_RESULTS: Dict[str, ReconciliationResult] = {}


def _map_decision_to_state(decision: ReconciliationDecision) -> str:
    if decision == ReconciliationDecision.AUTO_APPROVE:
        return "CLEAN"
    if decision == ReconciliationDecision.PARTIAL_APPROVE:
        return "PARTIAL_ESCROW"
    return "BLOCKED_DISPUTE"


def run_reconciliation_for_intent(
    db: Session,
    intent: PaymentIntent,
    *,
    policy: Optional[ReconciliationPolicy] = None,
    temp_excursion_minutes: int = 0,
) -> ReconciliationResult:
    """Run reconciliation against a PaymentIntent using a single-line bundle for demo."""
    policy = policy or DEFAULT_POLICY
    invoice_line = InvoiceLine(
        line_id=f"{intent.id}-LINE-1",
        quantity=1.0,
        unit_price=float(intent.amount),
    )
    po_line = PoLine(
        line_id=invoice_line.line_id,
        quantity=1.0,
        unit_price=float(intent.amount),
    )
    bundle = ReconciliationBundle(
        payment_intent_id=intent.id,
        po_lines=[po_line],
        exec_lines=[],
        invoice_lines=[invoice_line],
        policy=policy,
        amount_currency=intent.currency,
        total_billed_amount=float(intent.amount),
        temp_excursion_minutes=temp_excursion_minutes,
    )
    result = run_reconciliation(bundle)
    intent.recon_state = _map_decision_to_state(result.decision)
    intent.recon_score = result.recon_score
    intent.recon_policy_id = result.policy_id
    intent.approved_amount = result.approved_amount
    intent.held_amount = result.held_amount
    RECON_RESULTS[intent.id] = result
    return result


def get_reconciliation_result(intent_id: str) -> Optional[ReconciliationResult]:
    return RECON_RESULTS.get(intent_id)
