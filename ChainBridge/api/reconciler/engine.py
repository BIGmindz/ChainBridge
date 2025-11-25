"""Reconciliation engine applying tolerance, IoT discounts, and micro-settlement."""
from __future__ import annotations

from typing import Dict, List, Tuple

from .models import (
    InvoiceLine,
    PoLine,
    ExecLine,
    ReconciliationBundle,
    ReconciliationDecision,
    ReconciliationLineResult,
    ReconciliationLineStatus,
    ReconciliationResult,
)
from .policies import ReconciliationPolicy


def _line_by_id(lines: List[InvoiceLine | PoLine | ExecLine]) -> Dict[str, InvoiceLine | PoLine | ExecLine]:
    return {line.line_id: line for line in lines}


def _pct_delta(numerator: float | None, denominator: float | None) -> float:
    if numerator is None or denominator in (None, 0):
        return 0.0
    return (numerator / denominator) * 100.0


def _determine_status_and_reason(
    qty_delta_percent: float,
    price_delta_percent: float,
    policy: ReconciliationPolicy,
) -> Tuple[ReconciliationLineStatus, str]:
    if abs(qty_delta_percent) <= policy.qty_tolerance_percent and abs(price_delta_percent) <= policy.price_tolerance_percent:
        return ReconciliationLineStatus.MATCHED, "WITHIN_TOLERANCE"

    if abs(price_delta_percent) > policy.price_tolerance_percent:
        return ReconciliationLineStatus.PRICE_DELTA, (
            "PRICE_OUTSIDE_TOLERANCE_OVER"
            if price_delta_percent > 0
            else "PRICE_OUTSIDE_TOLERANCE_UNDER"
        )

    if qty_delta_percent > policy.qty_tolerance_percent:
        return ReconciliationLineStatus.OVER_DELIVERED, "QTY_OUTSIDE_TOLERANCE_OVER"
    if qty_delta_percent < -policy.qty_tolerance_percent:
        return ReconciliationLineStatus.UNDER_DELIVERED, "QTY_OUTSIDE_TOLERANCE_UNDER"
    return ReconciliationLineStatus.MATCHED, "WITHIN_TOLERANCE"


def run_reconciliation(bundle: ReconciliationBundle) -> ReconciliationResult:
    """Reconcile invoice vs PO/exec lines applying tolerances and IoT discounts."""
    policy = bundle.policy
    po_index = _line_by_id(bundle.po_lines)
    exec_index = _line_by_id(bundle.exec_lines)

    line_results: List[ReconciliationLineResult] = []
    flags: List[str] = []
    quality_violation = bundle.temp_excursion_minutes > policy.max_temp_excursion_minutes
    iot_discount_factor = policy.temp_discount_percent / 100.0 if quality_violation else 0.0

    for invoice in bundle.invoice_lines:
        po_line = po_index.get(invoice.line_id, PoLine(line_id=invoice.line_id, quantity=invoice.quantity, unit_price=invoice.unit_price))
        exec_line = exec_index.get(invoice.line_id, ExecLine(line_id=invoice.line_id, quantity=invoice.quantity, unit_price=invoice.unit_price))
        qty_delta = (invoice.quantity or 0) - (po_line.quantity or exec_line.quantity or 0)
        price_delta = (invoice.unit_price or 0) - (po_line.unit_price or exec_line.unit_price or 0)
        qty_delta_percent = _pct_delta(qty_delta, po_line.quantity or exec_line.quantity or invoice.quantity or 0)
        price_delta_percent = _pct_delta(price_delta, po_line.unit_price or exec_line.unit_price or invoice.unit_price or 0)

        status, reason = _determine_status_and_reason(qty_delta_percent, price_delta_percent, policy)

        contract_qty = po_line.quantity or invoice.quantity or 0
        contract_price = po_line.unit_price or invoice.unit_price or 0
        contract_amount = (contract_qty or 0) * (contract_price or 0)
        billed_amount = (invoice.quantity or 0) * (invoice.unit_price or 0)

        approved_amount = 0.0
        held_amount = billed_amount
        if status == ReconciliationLineStatus.MATCHED:
            approved_amount = billed_amount
            held_amount = 0.0
        else:
            approved_amount = billed_amount * policy.auto_partial_pay_percent_for_minor_issues
            held_amount = billed_amount - approved_amount
            reason = f"{reason}_PARTIAL_AUTO_PAY"

        if quality_violation:
            discounted = approved_amount * (1.0 - iot_discount_factor)
            discount_delta = approved_amount - discounted
            if discount_delta > 0:
                flags.append("TEMP_EXCURSION_DISCOUNT_APPLIED")
            approved_amount = discounted
            if status == ReconciliationLineStatus.MATCHED:
                status = ReconciliationLineStatus.QUALITY_VIOLATION
                reason = "TEMP_EXCURSION_DISCOUNT"
            else:
                reason = f"{reason}_TEMP_EXCURSION_DISCOUNT"

        line_results.append(
            ReconciliationLineResult(
                line_id=invoice.line_id,
                status=status,
                reason_code=reason,
                contract_amount=contract_amount,
                billed_amount=billed_amount,
                approved_amount=round(approved_amount, 2),
                held_amount=round(held_amount, 2),
                flags=[],
            )
        )

    total_approved = sum(line.approved_amount for line in line_results)
    total_held = sum(line.held_amount for line in line_results)
    total_value = total_approved + total_held
    recon_score = (total_approved / total_value * 100.0) if total_value else 0.0

    has_issue = any(line.status != ReconciliationLineStatus.MATCHED for line in line_results) or quality_violation
    decision = ReconciliationDecision.AUTO_APPROVE
    if has_issue:
        decision = ReconciliationDecision.PARTIAL_APPROVE if recon_score >= 80 else ReconciliationDecision.BLOCK

    if decision == ReconciliationDecision.AUTO_APPROVE and not policy.allow_auto_pay_above_amount:
        cap = policy.auto_pay_cap_amount or 0
        if cap and total_approved > cap:
            flags.append("AUTO_PAY_CAP_REACHED")
            excessive = total_approved - cap
            total_approved = cap
            total_held += excessive
            recon_score = (total_approved / (total_approved + total_held) * 100.0) if (total_approved + total_held) else 0.0
            decision = ReconciliationDecision.PARTIAL_APPROVE

    return ReconciliationResult(
        decision=decision,
        approved_amount=round(total_approved, 2),
        held_amount=round(total_held, 2),
        recon_score=round(recon_score, 2),
        policy_id=policy.id,
        flags=list(dict.fromkeys(flags)),
        lines=line_results,
    )
