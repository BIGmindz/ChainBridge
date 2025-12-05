"""ChainAudit service wrapper for running payout audits."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.events.bus import EventType, event_bus
from api.models.chainpay import PaymentIntent
from api.services.pricing.adjuster import calculate_final_settlement
from api.services.settlement_events import append_settlement_event

logger = logging.getLogger(__name__)


def _load_intent(db: Session, payment_intent_id: str) -> PaymentIntent:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == payment_intent_id).first()
    if not intent:
        raise ValueError("PaymentIntent not found")
    return intent


def _default_telemetry(intent: PaymentIntent) -> dict:
    # Placeholder until real IoT wiring; tie to corridor/mode if needed.
    return {
        "max_temp_deviation": 2.0,
        "breach_duration_minutes": 15.0,
    }


def run_audit_for_payment_intent(
    payment_intent_id: str,
    *,
    telemetry_override: Optional[dict] = None,
    db: Optional[Session] = None,
) -> PaymentIntent:
    managed = False
    if db is None:
        db = SessionLocal()
        managed = True
    try:
        intent = _load_intent(db, payment_intent_id)
        invoice_amount = intent.calculated_amount or intent.amount or 0.0
        telemetry = telemetry_override or _default_telemetry(intent)

        settlement = calculate_final_settlement(invoice_amount, telemetry)

        intent.payout_confidence = settlement["confidence_score"]
        intent.final_payout_amount = settlement["final_payout"]
        intent.adjustment_reason = settlement["adjustment_reason"]
        intent.auto_adjusted_amount = settlement["final_payout"]
        intent.reconciliation_explanation = [settlement["adjustment_reason"]]
        db.add(intent)
        db.commit()
        db.refresh(intent)

        event = append_settlement_event(
            db,
            intent,
            event_type="RECONCILED",
            status="SUCCESS",
            amount=settlement["final_payout"],
            currency=intent.currency,
            occurred_at=None,
            metadata={
                "confidence_score": settlement["confidence_score"],
                "final_payout_amount": settlement["final_payout"],
                "adjustment_reason": settlement["adjustment_reason"],
                "telemetry": telemetry,
            },
            actor="system:audit",
        )

        event_bus.publish(
            EventType.PAYMENT_INTENT_RECONCILED,
            {
                "payment_intent_id": intent.id,
                "shipment_id": intent.shipment_id,
                "confidence_score": settlement["confidence_score"],
                "final_payout_amount": settlement["final_payout"],
                "adjustment_reason": settlement["adjustment_reason"],
            },
            correlation_id=intent.id,
            actor="system:audit",
            occurred_at=event.occurred_at,
        )
        logger.info(
            "chain_audit_run",
            extra={
                "payment_intent_id": intent.id,
                "confidence_score": settlement["confidence_score"],
                "final_payout_amount": settlement["final_payout"],
                "status": settlement["status"],
            },
        )
        return intent
    finally:
        if managed:
            db.close()
