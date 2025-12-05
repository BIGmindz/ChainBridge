"""Audit endpoints for fuzzy evaluation."""

from __future__ import annotations

from fastapi import APIRouter
from app.schemas.audit import AuditVector, ReconciliationResult
from app.services.pricing.adjuster import calculate_final_settlement
# TODO: The following import is invalid or missing
# from app.models import PaymentIntent, MilestoneSettlement
# TODO: The following import is invalid or missing
# from app.db import get_db

router = APIRouter(prefix="/audit", tags=["audit"])

@router.post("/evaluate")
async def evaluate(payload: AuditVector):
    settlement = calculate_final_settlement(
        payload.invoice_amount,
        {"delta_temp_c": payload.delta_temp_c, "duration_mins": payload.duration_mins},
    )
    return ReconciliationResult(**settlement)

# --- NEW ENDPOINTS FOR TESTS ---

# @router.get("/shipments/{shipment_id}")
# def get_audit_shipment(shipment_id: int, db: Session = None):
#     # intent = db.query(PaymentIntent).filter_by(freight_token_id=shipment_id).first()
#     if not intent:
#         raise HTTPException(status_code=404, detail="Shipment not found")
#     # milestones = db.query(MilestoneSettlement).filter_by(payment_intent_id=intent.id).all()
#     summary = {
#         "total_approved_amount": sum(m.amount for m in milestones if m.status.name == "APPROVED"),
#         "total_settled_amount": sum(m.amount for m in milestones if m.status.name == "SETTLED"),
#         "total_milestones": len(milestones),
#     }
#     return {
#         "shipment_id": intent.freight_token_id,
#         "milestones": [
#             {
#                 "id": m.id,
#                 "event_type": m.event_type,
#                 "amount": m.amount,
#                 "currency": m.currency,
#                 "status": m.status.name,
#             }
#             for m in milestones
#         ],
#         "summary": summary,
#     }


# @router.get("/payment_intents/{payment_id}/milestones")
# def get_audit_payment_intent(payment_id: int, db: Session = None):
#     # intent = db.query(PaymentIntent).filter_by(id=payment_id).first()
#     if not intent:
#         raise HTTPException(status_code=404, detail="Payment intent not found")
#     # milestones = db.query(MilestoneSettlement).filter_by(payment_intent_id=payment_id).all()
#     summary = {
#         "total_approved_amount": sum(m.amount for m in milestones if m.status.name == "APPROVED"),
#         "total_settled_amount": sum(m.amount for m in milestones if m.status.name == "SETTLED"),
#         "total_milestones": len(milestones),
#     }
#     return {
#         "payment_intent": {
#             "id": intent.id,
#             "freight_token_id": intent.freight_token_id,
#             "amount": intent.amount,
#             "currency": intent.currency,
#             "risk_tier": intent.risk_tier.name if intent.risk_tier else None,
#             "status": intent.status.name if intent.status else None,
#         },
#         "milestones": [
#             {
#                 "id": m.id,
#                 "event_type": m.event_type,
#                 "amount": m.amount,
#                 "currency": m.currency,
#                 "status": m.status.name,
#             }
#             for m in milestones
#         ],
#         "summary": summary,
#     }
