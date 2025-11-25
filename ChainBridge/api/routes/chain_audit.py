"""ChainAudit v1 reconciliation endpoints."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.chain_audit_service import run_audit_for_payment_intent
from api.database import get_db
from api.models.chainpay import PaymentIntent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


class TelemetryPayload(BaseModel):
    max_temp_deviation: float
    breach_duration_minutes: float


class ReconcileRequest(BaseModel):
    telemetry_data: Optional[TelemetryPayload] = None


class ReconcileResponse(BaseModel):
    payment_intent_id: str
    payout_confidence: float
    final_payout_amount: float
    adjustment_reason: str
    status: str
    last_reconciled_at: Optional[str] = None


def _get_intent(db: Session, payment_intent_id: str) -> PaymentIntent:
    intent = (
        db.query(PaymentIntent)
        .filter(PaymentIntent.id == payment_intent_id)
        .first()
    )
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")
    return intent


@router.post("/payment_intents/{payment_intent_id}/reconcile", response_model=ReconcileResponse)
def reconcile(payment_intent_id: str, payload: ReconcileRequest, db: Session = Depends(get_db)) -> ReconcileResponse:
    telemetry_override = payload.telemetry_data.model_dump() if payload.telemetry_data else None
    intent = run_audit_for_payment_intent(payment_intent_id, telemetry_override=telemetry_override, db=db)
    baseline = intent.calculated_amount or intent.amount or intent.final_payout_amount or 0.0
    status = "FULL_PAYMENT"
    if (intent.final_payout_amount or 0.0) == 0:
        status = "BLOCKED"
    elif intent.final_payout_amount is not None and intent.final_payout_amount < baseline:
        status = "PARTIAL_SETTLEMENT"
    return ReconcileResponse(
        payment_intent_id=intent.id,
        payout_confidence=float(intent.payout_confidence or 0.0),
        final_payout_amount=float(intent.final_payout_amount or 0.0),
        adjustment_reason=intent.adjustment_reason or "",
        status=status,
        last_reconciled_at=intent.updated_at.isoformat() if intent.updated_at else None,
    )


@router.get("/payment_intents/{payment_intent_id}", response_model=ReconcileResponse)
def get_reconciliation(payment_intent_id: str, db: Session = Depends(get_db)) -> ReconcileResponse:
    intent = _get_intent(db, payment_intent_id)
    if intent.payout_confidence is None or intent.final_payout_amount is None:
        raise HTTPException(status_code=404, detail="No reconciliation available")
    baseline = intent.calculated_amount or intent.amount or intent.final_payout_amount or 0.0
    status = "FULL_PAYMENT"
    if (intent.final_payout_amount or 0.0) == 0:
        status = "BLOCKED"
    elif intent.final_payout_amount is not None and intent.final_payout_amount < baseline:
        status = "PARTIAL_SETTLEMENT"
    return ReconcileResponse(
        payment_intent_id=intent.id,
        payout_confidence=float(intent.payout_confidence),
        final_payout_amount=float(intent.final_payout_amount),
        adjustment_reason=intent.adjustment_reason or "",
        status=status,
        last_reconciled_at=intent.updated_at.isoformat() if intent.updated_at else None,
    )
