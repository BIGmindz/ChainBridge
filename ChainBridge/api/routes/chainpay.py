"""ChainPay API routes."""

import logging
import re
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session, aliased

from api.chaindocs_client import ChainDocsUnavailable, get_document as get_chaindocs_document
from api.chainiq_service.intel_engine import compute_shipment_health
from api.chainiq_service.schemas import ShipmentHealthResponse
from api.database import get_db
from api.models.chaindocs import Shipment
from api.models.legal import RicardianInstrument
from api.models.chainiq import DocumentHealthSnapshot
from api.models.chainpay import PaymentIntent, SettlementMilestone, SettlementPlan, SettlementEvent
from api.schemas.chainpay import (
    ChainPayMilestone,
    ChainPaySettlementPlan,
    ChainPaySettlementPlanCreate,
    DocRiskSnapshot,
    PaymentIntentShipmentSummary,
    PaymentIntentCreate,
    PaymentIntentListItem,
    PaymentIntentRead,
    PaymentIntentSummary,
    SettlementEventListItem,
    SettlementEventCreate,
    SettlementEventUpdate,
    ProofAttachmentRequest,
)
from api.services.payment_intents import (
    ensure_payment_intent_for_snapshot,
    get_latest_risk_snapshot,
    evaluate_readiness,
    compute_intent_hash,
)
from api.services.reconciliation import run_reconciliation_for_intent
from api.services.settlement_events import (
    EVENT_INDEX,
    append_settlement_event,
    delete_settlement_event,
    replace_settlement_event,
)
from api.chainpay_pricing import calculate_pricing_for_intent
from api.events.bus import event_bus, EventType
from api.sla.metrics import update_metric

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chainpay", tags=["ChainPay"])

PROOF_ID_PATTERN = re.compile(r"^[A-Za-z0-9\\-]{6,64}$")
READY_STATUSES = {"PENDING", "AUTHORIZED"}


def _is_valid_proof_id(proof_id: str) -> bool:
    return bool(proof_id and PROOF_ID_PATTERN.match(proof_id))


def _is_ready_for_payment(status: Optional[str], risk_level: Optional[str], has_proof: bool) -> bool:
    normalized_status = (status or "").upper()
    normalized_level = (risk_level or "").upper()
    # Rule: ready when proof is attached, status is releasable, and risk is LOW/MEDIUM.
    return has_proof and normalized_status in READY_STATUSES and normalized_level in {"LOW", "MEDIUM"}


def _log_intent_event(
    route: str,
    intent: PaymentIntent,
    shipment: Optional[Shipment],
    *,
    actor: str = "operator",
    extra: Optional[dict] = None,
) -> None:
    """Emit structured JSON-friendly log for PaymentIntent actions."""
    payload = {
        "route": route,
        "payment_intent_id": intent.id,
        "shipment_id": intent.shipment_id,
        "status": intent.status,
        "corridor_code": shipment.corridor_code if shipment else None,
        "risk_score": intent.risk_score,
        "risk_level": intent.risk_level,
        "has_proof": bool(intent.proof_pack_id),
        "actor": actor,
    }
    if extra:
        payload.update(extra)
    logger.info("chainpay.payment_intent.event", extra=payload)


def _serialize_plan(
    plan: SettlementPlan,
    doc_risk: Optional[DocRiskSnapshot] = None,
) -> ChainPaySettlementPlan:
    milestones = [
        ChainPayMilestone(
            event=milestone.event,
            payout_pct=milestone.payout_pct,
            status=milestone.status,
            paid_at=milestone.paid_at,
        )
        for milestone in sorted(plan.milestones, key=lambda m: m.id)
    ]

    return ChainPaySettlementPlan(
        shipment_id=plan.shipment_id,
        template_id=plan.template_id,
        total_value=plan.total_value,
        milestones=milestones,
        float_reduction_estimate=plan.float_reduction_estimate,
        doc_risk=doc_risk,
    )


def _create_default_plan_payload(shipment_id: str) -> ChainPaySettlementPlanCreate:
    return ChainPaySettlementPlanCreate(
        template_id="EXPORT_STANDARD_V1",
        total_value=100000.0,
        float_reduction_estimate=0.99,
        milestones=[
            ChainPayMilestone(
                event="BOL_ISSUED",
                payout_pct=0.4,
                status="PAID",
                paid_at="2025-11-17T15:00:00Z",
            ),
            ChainPayMilestone(
                event="IMPORT_CUSTOMS_CLEARED",
                payout_pct=0.4,
                status="PENDING",
                paid_at=None,
            ),
            ChainPayMilestone(
                event="PROOF_OF_DELIVERY",
                payout_pct=0.2,
                status="HELD",
                paid_at=None,
            ),
        ],
    )


def _persist_plan(
    shipment_id: str,
    payload: ChainPaySettlementPlanCreate,
    db: Session,
) -> SettlementPlan:
    plan = (
        db.query(SettlementPlan)
        .filter(SettlementPlan.shipment_id == shipment_id)
        .first()
    )

    if plan:
        plan.template_id = payload.template_id
        plan.total_value = payload.total_value
        plan.float_reduction_estimate = payload.float_reduction_estimate
        plan.milestones.clear()
    else:
        plan = SettlementPlan(
            id=f"PLAN-{shipment_id}",
            shipment_id=shipment_id,
            template_id=payload.template_id,
            total_value=payload.total_value,
            float_reduction_estimate=payload.float_reduction_estimate,
        )
        db.add(plan)
        db.flush()

    milestones: List[SettlementMilestone] = []
    for idx, milestone in enumerate(payload.milestones, start=1):
        milestones.append(
            SettlementMilestone(
                id=f"{plan.id}-MS-{idx}",
                plan_id=plan.id,
                event=milestone.event,
                payout_pct=milestone.payout_pct,
                status=milestone.status,
                paid_at=milestone.paid_at,
            )
        )

    plan.milestones.extend(milestones)

    db.add(plan)
    db.commit()
    db.refresh(plan)

    return plan


@router.get(
    "/shipments/{shipment_id}/settlement_plan",
    response_model=ChainPaySettlementPlan,
)
async def get_settlement_plan(
    shipment_id: str, db: Session = Depends(get_db)
) -> ChainPaySettlementPlan:
    """
    Return the stored settlement plan or bootstrap a default one.

    TODO: wire SettlementPlan updates to real ChainIQ risk + XRPL/HBAR executor
    TODO: support multiple templates per corridor
    TODO: replace SQLite with Postgres in production
    """
    if not shipment_id:
        raise HTTPException(status_code=400, detail="shipment_id is required")

    plan = (
        db.query(SettlementPlan)
        .filter(SettlementPlan.shipment_id == shipment_id)
        .first()
    )
    if not plan:
        payload = _create_default_plan_payload(shipment_id)
        plan = _persist_plan(shipment_id, payload, db)

    health = compute_shipment_health(db, shipment_id)
    doc_risk = _build_doc_risk_snapshot(health)

    return _serialize_plan(plan, doc_risk=doc_risk)


@router.post(
    "/shipments/{shipment_id}/settlement_plan",
    response_model=ChainPaySettlementPlan,
)
async def create_or_update_settlement_plan(
    shipment_id: str,
    payload: ChainPaySettlementPlanCreate,
    db: Session = Depends(get_db),
) -> ChainPaySettlementPlan:
    """
    Create or replace a settlement plan for a shipment.

    TODO: wire SettlementPlan updates to real ChainIQ risk + XRPL/HBAR executor
    TODO: replace SQLite with Postgres in production
    """
    if not shipment_id:
        raise HTTPException(status_code=400, detail="shipment_id is required")

    plan = _persist_plan(shipment_id, payload, db)
    health = compute_shipment_health(db, shipment_id)
    doc_risk = _build_doc_risk_snapshot(health)
    return _serialize_plan(plan, doc_risk=doc_risk)


def _build_doc_risk_snapshot(health: ShipmentHealthResponse) -> DocRiskSnapshot:
    return DocRiskSnapshot(
        score=health.risk.score,
        level=health.risk.level,
        missing_blocking_docs=health.document_health.blocking_documents,
    )


def _serialize_intent(intent: PaymentIntent) -> PaymentIntentRead:
    return PaymentIntentRead(
        id=intent.id,
        shipment_id=intent.shipment_id,
        latest_risk_snapshot_id=intent.latest_risk_snapshot_id,
        amount=intent.amount,
        currency=intent.currency,
        status=intent.status,
        has_proof=bool(intent.proof_pack_id),
        risk_score=intent.risk_score,
        risk_level=intent.risk_level,
        proof_pack_id=intent.proof_pack_id,
        counterparty=intent.counterparty,
        freight_reference=intent.freight_reference,
        notes=intent.notes,
        clearing_partner=intent.clearing_partner,
        intent_hash=intent.intent_hash,
        risk_gate_reason=intent.risk_gate_reason,
        compliance_blocks=intent.compliance_blocks,
        ready_at=intent.ready_at,
        calculated_amount=intent.calculated_amount,
        pricing_breakdown=intent.pricing_breakdown,
        created_at=intent.created_at,
        updated_at=intent.updated_at,
    )


def _serialize_settlement_event(event: SettlementEvent) -> SettlementEventListItem:
    return SettlementEventListItem(
        id=event.id,
        payment_intent_id=event.payment_intent_id,
        event_type=event.event_type,
        status=event.status,
        amount=event.amount,
        currency=event.currency,
        occurred_at=event.occurred_at,
        metadata=event.extra_metadata,
        sequence=event.sequence,
    )


def _validate_event_type(event_type: str) -> str:
    normalized = (event_type or "").upper()
    if normalized not in EVENT_INDEX:
        raise HTTPException(status_code=400, detail="Unsupported event_type")
    return normalized


@router.post(
    "/payment_intents/from_shipment",
    response_model=PaymentIntentRead,
    status_code=201,
)
def create_payment_intent_from_shipment(
    payload: PaymentIntentCreate,
    db: Session = Depends(get_db),
) -> PaymentIntentRead:
    """Create a PaymentIntent linked to a shipment and its latest risk snapshot."""
    start = time.perf_counter()
    shipment = db.query(Shipment).filter(Shipment.id == payload.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    snapshot = get_latest_risk_snapshot(db, payload.shipment_id)
    if not snapshot:
        raise HTTPException(status_code=400, detail="No risk snapshot found for shipment")

    pricing_components = calculate_pricing_for_intent(shipment, snapshot)

    intent = ensure_payment_intent_for_snapshot(
        db,
        shipment=shipment,
        snapshot=snapshot,
        amount=pricing_components.get("total_price") or payload.amount,
        currency=payload.currency,
        counterparty=payload.counterparty,
        notes=payload.notes,
    )
    intent.calculated_amount = pricing_components.get("total_price")
    intent.pricing_breakdown = pricing_components

    instrument = (
        db.query(RicardianInstrument)
        .filter(RicardianInstrument.physical_reference == shipment.id)
        .order_by(RicardianInstrument.created_at.desc())
        .first()
    )
    ready, reason, blocks, ready_at = evaluate_readiness(
        intent,
        latest_snapshot=snapshot,
        settlement_events=None,
        ricardian_status=instrument.status if instrument else None,
    )
    intent.risk_gate_reason = reason
    intent.compliance_blocks = blocks
    intent.ready_at = ready_at
    intent.intent_hash = compute_intent_hash(intent)
    run_reconciliation_for_intent(db, intent)
    db.add(intent)
    db.commit()
    db.refresh(intent)
    event_bus.publish(
        EventType.PAYMENT_INTENT_CREATED,
        {
            "id": intent.id,
            "shipment_id": intent.shipment_id,
            "status": intent.status,
            "risk_level": intent.risk_level,
        },
        correlation_id=intent.id,
        actor="api",
    )

    duration_ms = (time.perf_counter() - start) * 1000
    _log_intent_event(
        "payment_intents.from_shipment",
        intent,
        shipment,
        actor="operator",
        extra={
            "duration_ms": round(duration_ms, 2),
            "ready_for_payment": _is_ready_for_payment(intent.status, intent.risk_level, bool(intent.proof_pack_id)),
        },
    )
    return _serialize_intent(intent)


@router.post(
    "/payment_intents/{intent_id}/attach_proof",
    response_model=PaymentIntentRead,
)
def attach_proof_to_intent(
    intent_id: str,
    payload: ProofAttachmentRequest,
    db: Session = Depends(get_db),
) -> PaymentIntentRead:
    """Attach a proof pack to a PaymentIntent; idempotent for the same proof id."""
    start = time.perf_counter()
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")

    if not _is_valid_proof_id(payload.proof_pack_id):
        raise HTTPException(status_code=400, detail={"error": "invalid_proof_id"})

    try:
        proof_doc = get_chaindocs_document(payload.proof_pack_id, db)
    except ChainDocsUnavailable:
        raise HTTPException(status_code=503, detail={"error": "chaindocs_unavailable"}) from None

    if proof_doc is None:
        raise HTTPException(status_code=404, detail={"error": "proof_not_found"})

    conflicting = (
        db.query(PaymentIntent)
        .filter(
            PaymentIntent.proof_pack_id == payload.proof_pack_id,
            PaymentIntent.id != intent_id,
        )
        .first()
    )
    if conflicting:
        raise HTTPException(status_code=409, detail={"error": "proof_conflict"})

    if intent.proof_pack_id and intent.proof_pack_id != payload.proof_pack_id:
        raise HTTPException(status_code=409, detail={"error": "proof_conflict"})

    if not intent.proof_pack_id:
        intent.proof_pack_id = payload.proof_pack_id
        intent.proof_hash = getattr(proof_doc, "hash", None)
        instrument = (
            db.query(RicardianInstrument)
            .filter(RicardianInstrument.physical_reference == intent.shipment_id)
            .order_by(RicardianInstrument.created_at.desc())
            .first()
        )
        ready, reason, blocks, ready_at = evaluate_readiness(
            intent,
            latest_snapshot=None,
            settlement_events=intent.settlement_events,
            ricardian_status=instrument.status if instrument else None,
        )
        intent.risk_gate_reason = reason
        intent.compliance_blocks = blocks
        intent.ready_at = ready_at
        intent.intent_hash = compute_intent_hash(intent)
        db.commit()
        db.refresh(intent)

    duration_ms = (time.perf_counter() - start) * 1000
    shipment = db.query(Shipment).filter(Shipment.id == intent.shipment_id).first()
    ready_flag = _is_ready_for_payment(intent.status, intent.risk_level, bool(intent.proof_pack_id))
    _log_intent_event(
        "payment_intents.attach_proof",
        intent,
        shipment,
        actor="operator",
        extra={
            "duration_ms": round(duration_ms, 2),
            "proof_id": payload.proof_pack_id,
            "doc_type": proof_doc.type,
            "ready_for_payment": ready_flag,
        },
    )
    return _serialize_intent(intent)


@router.get(
    "/payment_intents",
    response_model=List[PaymentIntentListItem],
)
def list_payment_intents(
    status: Optional[List[str]] = Query(None),
    corridor_code: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    has_proof: Optional[bool] = Query(None),
    ready_for_payment: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[PaymentIntentListItem]:
    """List PaymentIntents for operator workflows with basic filters."""
    start = time.perf_counter()
    update_metric("payment_intents")
    normalized_statuses = [s.upper() for s in status] if status else list(READY_STATUSES)

    latest_snapshot = (
        db.query(
            DocumentHealthSnapshot.shipment_id.label("shipment_id"),
            func.max(DocumentHealthSnapshot.created_at).label("max_created_at"),
        )
        .group_by(DocumentHealthSnapshot.shipment_id)
        .subquery()
    )

    fallback_risk = (
        db.query(
            DocumentHealthSnapshot.shipment_id.label("shipment_id"),
            DocumentHealthSnapshot.risk_score.label("risk_score"),
            DocumentHealthSnapshot.risk_level.label("risk_level"),
        )
        .join(
            latest_snapshot,
            (DocumentHealthSnapshot.shipment_id == latest_snapshot.c.shipment_id)
            & (DocumentHealthSnapshot.created_at == latest_snapshot.c.max_created_at),
        )
        .subquery()
    )

    intent_snapshot = aliased(DocumentHealthSnapshot)
    risk_level_expr = func.coalesce(intent_snapshot.risk_level, fallback_risk.c.risk_level, PaymentIntent.risk_level)
    risk_score_expr = func.coalesce(intent_snapshot.risk_score, fallback_risk.c.risk_score, PaymentIntent.risk_score)
    has_proof_expr = PaymentIntent.proof_pack_id.isnot(None)
    ready_expr = has_proof_expr & PaymentIntent.status.in_(READY_STATUSES) & risk_level_expr.in_(["LOW", "MEDIUM"])

    query = (
        db.query(
            PaymentIntent,
            Shipment,
            intent_snapshot,
            risk_score_expr.label("resolved_risk_score"),
            risk_level_expr.label("resolved_risk_level"),
            has_proof_expr.label("has_proof"),
            ready_expr.label("ready_for_payment"),
        )
        .outerjoin(Shipment, Shipment.id == PaymentIntent.shipment_id)
        .outerjoin(intent_snapshot, intent_snapshot.id == PaymentIntent.latest_risk_snapshot_id)
        .outerjoin(
            fallback_risk,
            fallback_risk.c.shipment_id == PaymentIntent.shipment_id,
        )
        .filter(PaymentIntent.status.in_(normalized_statuses))
        .order_by(PaymentIntent.created_at.desc())
    )

    if corridor_code:
        query = query.filter(Shipment.corridor_code == corridor_code)
    if mode:
        query = query.filter(Shipment.mode == mode)
    if has_proof is not None:
        query = query.filter(has_proof_expr == has_proof)
    if ready_for_payment is not None:
        query = query.filter(ready_expr == ready_for_payment)

    results = query.offset(offset).limit(limit).all()
    items: List[PaymentIntentListItem] = []
    for intent, shipment_obj, stored_snapshot, resolved_risk_score, resolved_risk_level, proof_flag, ready_flag in results:
        shipment_summary = None
        if shipment_obj:
            shipment_summary = PaymentIntentShipmentSummary(
                corridor_code=shipment_obj.corridor_code,
                mode=shipment_obj.mode,
                incoterm=shipment_obj.incoterm,
            )

        items.append(
            PaymentIntentListItem(
                id=intent.id,
                shipment_id=intent.shipment_id,
                amount=intent.amount,
                currency=intent.currency,
                status=intent.status,
                ready_for_payment=bool(ready_flag),
                has_proof=bool(proof_flag),
                risk_score=resolved_risk_score,
                risk_level=resolved_risk_level,
                proof_attached=bool(proof_flag),
                corridor_code=shipment_summary.corridor_code if shipment_summary else None,
                mode=shipment_summary.mode if shipment_summary else None,
                incoterm=shipment_summary.incoterm if shipment_summary else None,
                counterparty=intent.counterparty,
                shipment_summary=shipment_summary,
                created_at=intent.created_at,
                updated_at=intent.updated_at,
            )
        )

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "chainpay.payment_intents.list",
        extra={
            "route": "payment_intents.list",
            "actor": "operator",
            "count": len(items),
            "status_filter": normalized_statuses,
            "has_proof": has_proof,
            "ready_for_payment": ready_for_payment,
            "duration_ms": round(duration_ms, 2),
        },
    )
    return items


@router.get(
    "/payment_intents/{payment_intent_id}/settlement_events",
    response_model=List[SettlementEventListItem],
)
def list_settlement_events(
    payment_intent_id: str,
    db: Session = Depends(get_db),
) -> List[SettlementEventListItem]:
    """List settlement events for a payment intent ordered by occurred_at ascending."""
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == payment_intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")

    events = (
        db.query(SettlementEvent)
        .filter(SettlementEvent.payment_intent_id == payment_intent_id)
        .order_by(SettlementEvent.occurred_at.asc())
        .all()
    )
    logger.info(
        "chainpay_settlement_events_list",
        extra={"payment_intent_id": payment_intent_id, "count": len(events)},
    )
    return [_serialize_settlement_event(event) for event in events]


@router.post(
    "/payment_intents/{payment_intent_id}/settlement_events",
    response_model=SettlementEventListItem,
    status_code=201,
)
def append_settlement_event_route(
    payment_intent_id: str,
    payload: SettlementEventCreate,
    db: Session = Depends(get_db),
) -> SettlementEventListItem:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == payment_intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")
    event_type = _validate_event_type(payload.event_type)
    try:
        event = append_settlement_event(
            db,
            intent,
            event_type=event_type,
            status=payload.status.upper(),
            amount=payload.amount,
            currency=payload.currency,
            occurred_at=payload.occurred_at,
            metadata=payload.metadata,
            actor=payload.actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_settlement_event(event)


@router.put(
    "/payment_intents/{payment_intent_id}/settlement_events/{event_id}",
    response_model=SettlementEventListItem,
)
def replace_settlement_event_route(
    payment_intent_id: str,
    event_id: str,
    payload: SettlementEventUpdate,
    db: Session = Depends(get_db),
) -> SettlementEventListItem:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == payment_intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")
    event = (
        db.query(SettlementEvent)
        .filter(SettlementEvent.id == event_id, SettlementEvent.payment_intent_id == payment_intent_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="SettlementEvent not found")
    event_type = _validate_event_type(payload.event_type) if payload.event_type else event.event_type
    try:
        updated = replace_settlement_event(
            db,
            event,
            event_type=event_type,
            status=payload.status.upper() if payload.status else None,
            amount=payload.amount,
            currency=payload.currency,
            occurred_at=payload.occurred_at,
            metadata=payload.metadata,
            actor=payload.actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_settlement_event(updated)


@router.put(
    "/settlement_events/{event_id}",
    response_model=SettlementEventListItem,
)
def replace_settlement_event_direct(
    event_id: str,
    payload: SettlementEventUpdate,
    db: Session = Depends(get_db),
) -> SettlementEventListItem:
    event = db.query(SettlementEvent).filter(SettlementEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="SettlementEvent not found")
    event_type = _validate_event_type(payload.event_type) if payload.event_type else event.event_type
    try:
        updated = replace_settlement_event(
            db,
            event,
            event_type=event_type,
            status=payload.status.upper() if payload.status else None,
            amount=payload.amount,
            currency=payload.currency,
            occurred_at=payload.occurred_at,
            metadata=payload.metadata,
            actor=payload.actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_settlement_event(updated)


@router.delete(
    "/payment_intents/{payment_intent_id}/settlement_events/{event_id}",
    status_code=204,
)
def delete_settlement_event_route(
    payment_intent_id: str,
    event_id: str,
    db: Session = Depends(get_db),
) -> None:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == payment_intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")
    event = (
        db.query(SettlementEvent)
        .filter(SettlementEvent.id == event_id, SettlementEvent.payment_intent_id == payment_intent_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="SettlementEvent not found")
    delete_settlement_event(db, event, actor="operator")
    return None


@router.delete(
    "/settlement_events/{event_id}",
    status_code=204,
)
def delete_settlement_event_direct(
    event_id: str,
    db: Session = Depends(get_db),
) -> None:
    event = db.query(SettlementEvent).filter(SettlementEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="SettlementEvent not found")
    delete_settlement_event(db, event, actor="operator")
    return None


@router.get(
    "/payment_intents/summary",
    response_model=PaymentIntentSummary,
)
def summarize_payment_intents(
    db: Session = Depends(get_db),
) -> PaymentIntentSummary:
    """Aggregate PaymentIntent state for operator KPIs."""
    latest_snapshot = (
        db.query(
            DocumentHealthSnapshot.shipment_id.label("shipment_id"),
            func.max(DocumentHealthSnapshot.created_at).label("max_created_at"),
        )
        .group_by(DocumentHealthSnapshot.shipment_id)
        .subquery()
    )
    fallback_risk = (
        db.query(
            DocumentHealthSnapshot.shipment_id.label("shipment_id"),
            DocumentHealthSnapshot.risk_level.label("risk_level"),
        )
        .join(
            latest_snapshot,
            (DocumentHealthSnapshot.shipment_id == latest_snapshot.c.shipment_id)
            & (DocumentHealthSnapshot.created_at == latest_snapshot.c.max_created_at),
        )
        .subquery()
    )
    intent_snapshot = aliased(DocumentHealthSnapshot)
    risk_level_expr = func.coalesce(intent_snapshot.risk_level, fallback_risk.c.risk_level, PaymentIntent.risk_level)
    has_proof_expr = PaymentIntent.proof_pack_id.isnot(None)
    ready_expr = has_proof_expr & PaymentIntent.status.in_(READY_STATUSES) & risk_level_expr.in_(["LOW", "MEDIUM"])
    awaiting_expr = (~has_proof_expr) & PaymentIntent.status.in_(READY_STATUSES)
    blocked_expr = risk_level_expr.in_(["HIGH", "CRITICAL"])

    query = (
        db.query(
            func.count(PaymentIntent.id),
            func.sum(case((ready_expr, 1), else_=0)),
            func.sum(case((awaiting_expr, 1), else_=0)),
            func.sum(case((blocked_expr, 1), else_=0)),
        )
        .outerjoin(intent_snapshot, intent_snapshot.id == PaymentIntent.latest_risk_snapshot_id)
        .outerjoin(fallback_risk, fallback_risk.c.shipment_id == PaymentIntent.shipment_id)
    ).one()

    total, ready_for_payment_count, awaiting_proof, blocked_by_risk = query
    ready_for_payment_count = int(ready_for_payment_count or 0)
    awaiting_proof = int(awaiting_proof or 0)
    blocked_by_risk = int(blocked_by_risk or 0)

    logger.info(
        "chainpay.payment_intents.summary",
        extra={
            "route": "payment_intents.summary",
            "actor": "operator",
            "total": total,
            "awaiting_proof": awaiting_proof,
            "ready_for_payment": ready_for_payment_count,
            "blocked_by_risk": blocked_by_risk,
        },
    )
    return PaymentIntentSummary(
        total=total,
        awaiting_proof=awaiting_proof,
        ready_for_payment=ready_for_payment_count,
        blocked_by_risk=blocked_by_risk,
    )
