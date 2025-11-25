"""
ChainBoard Payments Router
-------------------------

Provides ChainPay-specific APIs such as ProofPack retrieval.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from api.mock.chainboard_fixtures import mock_shipments
from api.schemas.chainboard import ProofPack
from chainpay_service.app.database import SessionLocal as ChainpaySession, init_db as chainpay_init_db
from chainpay_service.app.proofpack_helper import (
    MilestoneSnapshot,
    get_milestone_snapshot,
)
from core.payments.identity import infer_freight_token_id, parse_milestone_identifier

router = APIRouter(prefix="/chainboard/payments", tags=["ChainPay"])
chainpay_init_db()


def _find_milestone(shipment_reference: str, milestone_id: str):
    shipment = next((s for s in mock_shipments if s.id == shipment_reference), None)
    if not shipment:
        return None, None
    milestone = next(
        (m for m in shipment.payment.milestones if m.milestone_id == milestone_id),
        None,
    )
    return shipment, milestone


def _resolve_chainpay_snapshot(milestone_id: str) -> Optional[MilestoneSnapshot]:
    """Fetch milestone snapshot from ChainPay database."""
    session = ChainpaySession()
    try:
        return get_milestone_snapshot(session, milestone_id)
    finally:
        session.close()


@router.get("/proofpack/{milestone_id}", response_model=ProofPack)
async def get_proofpack(milestone_id: str) -> ProofPack:
    """
    Retrieve ProofPack payload for a milestone, backed by ChainPay data.
    """
    try:
        shipment_reference, _ = parse_milestone_identifier(milestone_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    snapshot = _resolve_chainpay_snapshot(milestone_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Milestone {milestone_id} not found in ChainPay")

    shipment, milestone = _find_milestone(shipment_reference, milestone_id)
    corridor = shipment.corridor if shipment else "UNKNOWN"
    customer_name = shipment.customer if shipment else "Unknown Customer"

    fallback_freight_token = (
        milestone.freight_token_id
        if milestone and milestone.freight_token_id is not None
        else infer_freight_token_id(snapshot.shipment_reference)
    )
    freight_token_id = snapshot.freight_token_id or fallback_freight_token
    last_updated = snapshot.last_updated

    documents: List[dict] = [
        {
            "type": "mock_document",
            "status": "placeholder",
            "source": "mock",
            "note": "TODO-chainfreight",
        },
        {
            "type": "mock_pod",
            "status": "placeholder",
            "source": "mock",
            "note": "TODO-chainfreight",
        },
    ]

    iot_signals: List[dict] = [
        {
            "sensor": "temperature",
            "value": "22.0C",
            "status": "stable",
            "source": "mock",
            "note": "TODO-chainiq",
        },
        {
            "sensor": "gps",
            "value": shipment.freight.lane if shipment else "UNKNOWN",
            "status": "placeholder",
            "source": "mock",
            "note": "TODO-chainiq",
        },
    ]

    risk_assessment = {
        "source": "mock",
        "confidence": "unknown",
        "note": "TODO-chainiq",
    }

    audit_trail: List[dict] = [
        {
            "event": "milestone_recorded",
            "state": snapshot.state,
            "timestamp": last_updated,
            "source": "mock",
            "note": "TODO-ledger",
        },
        {
            "event": "proofpack_snapshot",
            "state": snapshot.state,
            "timestamp": datetime.utcnow(),
            "note": "Placeholder audit entry until ledger integration is wired",
            "source": "mock",
        },
    ]

    return ProofPack(
        milestone_id=snapshot.milestone_id,
        shipment_reference=snapshot.shipment_reference,
        corridor=corridor,
        customer_name=customer_name,
        amount=snapshot.amount,
        currency=snapshot.currency,
        state=snapshot.state,
        freight_token_id=freight_token_id,
        last_updated=last_updated,
        documents=documents,
        iot_signals=iot_signals,
        risk_assessment=risk_assessment,
        audit_trail=audit_trail,
    )
