from api.reconciler.engine import run_reconciliation
from api.reconciler.models import InvoiceLine, PoLine, ExecLine, ReconciliationBundle, ReconciliationLineStatus, ReconciliationDecision
from api.reconciler.policies import DEFAULT_POLICY


def _bundle(invoice_qty: float, po_qty: float, unit_price: float, temp_minutes: int = 0) -> ReconciliationBundle:
    invoice = InvoiceLine(line_id="LINE-1", quantity=invoice_qty, unit_price=unit_price)
    po = PoLine(line_id="LINE-1", quantity=po_qty, unit_price=unit_price)
    return ReconciliationBundle(
        payment_intent_id="PAY-1",
        po_lines=[po],
        exec_lines=[ExecLine(line_id="LINE-1", quantity=po_qty, unit_price=unit_price)],
        invoice_lines=[invoice],
        policy=DEFAULT_POLICY,
        amount_currency="USD",
        total_billed_amount=invoice_qty * unit_price,
        temp_excursion_minutes=temp_minutes,
    )


def test_reconciliation_perfect_match() -> None:
    result = run_reconciliation(_bundle(invoice_qty=10, po_qty=10, unit_price=100))
    assert result.decision == ReconciliationDecision.AUTO_APPROVE
    assert result.approved_amount == 1000
    assert result.held_amount == 0
    assert result.recon_score == 100
    assert result.lines[0].status == ReconciliationLineStatus.MATCHED


def test_reconciliation_qty_outside_tolerance() -> None:
    result = run_reconciliation(_bundle(invoice_qty=15, po_qty=10, unit_price=100))
    assert result.decision == ReconciliationDecision.PARTIAL_APPROVE
    assert result.lines[0].status in {ReconciliationLineStatus.OVER_DELIVERED, ReconciliationLineStatus.UNDER_DELIVERED}
    assert result.approved_amount == 1350
    assert result.held_amount == 150


def test_reconciliation_iot_discount_applied() -> None:
    result = run_reconciliation(_bundle(invoice_qty=10, po_qty=10, unit_price=100, temp_minutes=5))
    assert result.decision == ReconciliationDecision.PARTIAL_APPROVE
    assert result.flags == ["TEMP_EXCURSION_DISCOUNT_APPLIED"]
    assert result.lines[0].status == ReconciliationLineStatus.QUALITY_VIOLATION
    assert result.lines[0].approved_amount == 900
