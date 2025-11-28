"""Shared helpers for creating and querying PaymentIntents."""

from __future__ import annotations

import logging
import json
import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.models.chaindocs import Shipment
from api.models.chainiq import DocumentHealthSnapshot
from api.models.chainpay import PaymentIntent, SettlementPlan, SettlementEvent

logger = logging.getLogger(__name__)


def get_latest_risk_snapshot(db: Session, shipment_id: str) -> Optional[DocumentHealthSnapshot]:
    """Return the newest document health snapshot for a shipment."""
    return (
        db.query(DocumentHealthSnapshot)
        .filter(DocumentHealthSnapshot.shipment_id == shipment_id)
        .order_by(
            DocumentHealthSnapshot.created_at.desc(),
            DocumentHealthSnapshot.id.desc(),
        )
        .first()
    )


def is_payment_approved(risk_level: Optional[str]) -> bool:
    """Simple approval heuristic: LOW or MEDIUM risk qualifies for payment."""
    if not risk_level:
        return False
    normalized = (risk_level or "").upper()
    return normalized in {"LOW", "MEDIUM"}


def _resolve_amount_and_currency(
    db: Session,
    amount: Optional[float],
    currency: Optional[str],
    shipment_id: str,
) -> tuple[float, str]:
    """
    Determine amount and currency with sensible fallbacks.

    Falls back to the settlement plan total value when explicit values are missing.
    """
    resolved_currency = currency or "USD"
    if amount is not None:
        return amount, resolved_currency

    plan = (
        db.query(SettlementPlan)
        .filter(SettlementPlan.shipment_id == shipment_id)
        .first()
    )
    if plan and plan.total_value is not None:
        return float(plan.total_value), resolved_currency

    # Last resort to avoid blowing up the pipeline; callers can update later.
    logger.warning("Missing amount for PaymentIntent on %s; defaulting to 0.0", shipment_id)
    return 0.0, resolved_currency


def ensure_payment_intent_for_snapshot(
    db: Session,
    *,
    shipment: Shipment,
    snapshot: DocumentHealthSnapshot,
    amount: Optional[float],
    currency: Optional[str],
    counterparty: Optional[str] = None,
    notes: Optional[str] = None,
    freight_reference: Optional[str] = None,
) -> PaymentIntent:
    """
    Idempotently create or return a PaymentIntent for a shipment + risk snapshot.

    Strategy: uniqueness enforced on (shipment_id, latest_risk_snapshot_id). If a record
    already exists for that pair, it is returned as-is.
    """
    existing = (
        db.query(PaymentIntent)
        .filter(
            PaymentIntent.shipment_id == shipment.id,
            PaymentIntent.latest_risk_snapshot_id == snapshot.id,
        )
        .first()
    )
    if existing:
        return existing

    resolved_amount, resolved_currency = _resolve_amount_and_currency(
        db,
        amount,
        currency,
        shipment.id,
    )
    intent = PaymentIntent(
        shipment_id=shipment.id,
        latest_risk_snapshot_id=snapshot.id,
        freight_reference=freight_reference,
        amount=resolved_amount,
        currency=resolved_currency,
        status="PENDING",
        risk_score=float(snapshot.risk_score) if snapshot.risk_score is not None else None,
        risk_level=snapshot.risk_level,
        counterparty=counterparty,
        notes=notes,
    )
    db.add(intent)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(PaymentIntent)
            .filter(
                PaymentIntent.shipment_id == shipment.id,
                PaymentIntent.latest_risk_snapshot_id == snapshot.id,
            )
            .first()
        )
        if existing:
            return existing
        raise

    db.refresh(intent)
    return intent


def compute_intent_hash(intent: PaymentIntent) -> str:
    payload = {
        "id": intent.id,
        "shipment_id": intent.shipment_id,
        "amount": intent.amount,
        "currency": intent.currency,
        "status": intent.status,
        "risk_score": intent.risk_score,
        "risk_level": intent.risk_level,
        "proof_pack_id": intent.proof_pack_id,
        "clearing_partner": intent.clearing_partner,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def evaluate_readiness(
    intent: PaymentIntent,
    *,
    latest_snapshot: Optional[DocumentHealthSnapshot],
    settlement_events: Optional[list[SettlementEvent]] = None,
    ricardian_status: Optional[str] = None,
) -> tuple[bool, str, list[str], Optional[datetime]]:
    """
    Determine readiness for payment.

    Simple rule: proof attached AND risk LOW/MEDIUM AND no compliance blocks.
    """
    compliance_blocks: list[str] = []
    risk_reason = "OK"
    ready_at = intent.ready_at

    risk_level = (latest_snapshot.risk_level if latest_snapshot else intent.risk_level or "").upper()
    if risk_level in {"HIGH", "CRITICAL"}:
        compliance_blocks.append("RISK_TOO_HIGH")
        risk_reason = "Risk level too high"
    if not intent.proof_pack_id:
        compliance_blocks.append("PROOF_MISSING")
        risk_reason = "Proof missing"

    if ricardian_status and ricardian_status.upper() == "FROZEN":
        compliance_blocks.append("RICARDIAN_INSTRUMENT_FROZEN")
        risk_reason = "Ricardian instrument frozen"

    if settlement_events:
        failure = next(
            (evt for evt in settlement_events if evt.event_type in {"FAILED", "FAILED_CLEARINGHOUSE", "FAILED_COMPLIANCE_CHECK"}),
            None,
        )
        if failure:
            compliance_blocks.append("SETTLEMENT_FAILED")
            risk_reason = "Settlement failure"

    is_ready = len(compliance_blocks) == 0
    if is_ready and not ready_at:
        ready_at = datetime.utcnow()
    return is_ready, risk_reason, compliance_blocks, ready_at
    return intent
