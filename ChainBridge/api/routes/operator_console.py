"""Operator Console API surfaces combining ChainPay + ChainIQ + IoT."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.chainsense.client import IoTDataProvider, MockIoTDataProvider
from api.database import get_db
from api.models.canonical import RiskLevel
from api.models.chainiq import DocumentHealthSnapshot, RiskDecision
from api.models.chainpay import PaymentIntent, SettlementEvent
from api.models.legal import RicardianInstrument
from api.schemas.chainboard import IoTHealthSummary
from api.schemas.operator_console import (
    AuditCoreSummary,
    AuditDocumentRef,
    AuditDocuments,
    AuditEventItem,
    AuditEventTimeline,
    AuditIoTSummary,
    AuditLaneSummary,
    AuditLegalWrapper,
    AuditMetadata,
    AuditPackResponse,
    AuditProofProvider,
    AuditProofStatus,
    AuditProofSummary,
    AuditRiskSnapshot,
    AuditRiskSummary,
    AuditSLASummary,
    OperatorEvent,
    OperatorEventsResponse,
    OperatorIoTHealthSummary,
    OperatorQueueItem,
    OperatorQueueResponse,
    ReconciliationLineResult,
    ReconciliationSummary,
    RiskSnapshotResponse,
    SettlementEventItem,
)
from api.services.reconciliation import (
    get_reconciliation_result,
    run_reconciliation_for_intent,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/operator", tags=["operator_console"])


def _risk_band(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score >= 80:
        return RiskLevel.LOW.value
    if score >= 55:
        return RiskLevel.MEDIUM.value
    if score >= 40:
        return RiskLevel.HIGH.value
    return RiskLevel.CRITICAL.value


def _queue_state(intent: PaymentIntent) -> str:
    if intent.compliance_blocks:
        return "BLOCKED"
    if intent.proof_pack_id:
        return "READY"
    return "WAITING_PROOF"


@router.get("/queue", response_model=OperatorQueueResponse)
def get_operator_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    state: Optional[str] = Query(None),
    min_risk: Optional[float] = Query(None),
    max_risk: Optional[float] = Query(None),
    db: Session = Depends(get_db),
) -> OperatorQueueResponse:
    query = db.query(PaymentIntent, DocumentHealthSnapshot).outerjoin(
        DocumentHealthSnapshot,
        (DocumentHealthSnapshot.id == PaymentIntent.latest_risk_snapshot_id)
        | (
            (DocumentHealthSnapshot.shipment_id == PaymentIntent.shipment_id)
            & (
                DocumentHealthSnapshot.created_at
                == (
                    db.query(func.max(DocumentHealthSnapshot.created_at))
                    .filter(DocumentHealthSnapshot.shipment_id == PaymentIntent.shipment_id)
                    .correlate(PaymentIntent)
                )
            )
        ),
    )
    if state:
        desired = state.upper()
        if desired == "READY":
            query = query.filter(
                PaymentIntent.proof_pack_id.isnot(None),
                PaymentIntent.compliance_blocks.is_(None),
            )
        elif desired == "BLOCKED":
            query = query.filter(PaymentIntent.compliance_blocks.isnot(None))
        elif desired == "WAITING_PROOF":
            query = query.filter(PaymentIntent.proof_pack_id.is_(None))
    if min_risk is not None:
        query = query.filter(
            (DocumentHealthSnapshot.risk_score >= min_risk)
            | ((DocumentHealthSnapshot.risk_score.is_(None)) & (PaymentIntent.risk_score >= min_risk))
        )
    if max_risk is not None:
        query = query.filter(
            (DocumentHealthSnapshot.risk_score <= max_risk)
            | ((DocumentHealthSnapshot.risk_score.is_(None)) & (PaymentIntent.risk_score <= max_risk))
        )

    total = query.count()
    rows = query.order_by(PaymentIntent.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    now = datetime.now(timezone.utc)
    items: List[OperatorQueueItem] = []
    for intent, snapshot in rows:
        age_seconds = int((now - intent.created_at.replace(tzinfo=timezone.utc)).total_seconds())
        instrument = (
            db.query(RicardianInstrument)
            .filter(RicardianInstrument.physical_reference == intent.shipment_id)
            .order_by(RicardianInstrument.created_at.desc())
            .first()
        )
        items.append(
            OperatorQueueItem(
                id=intent.id,
                state=_queue_state(intent),
                amount=intent.amount,
                currency=intent.currency,
                risk_score=snapshot.risk_score if snapshot else intent.risk_score,
                readiness_reason=intent.risk_gate_reason,
                event_age_seconds=age_seconds,
                p95_seconds=None,
                intent_hash=intent.intent_hash,
                recon_state=intent.recon_state,
                recon_score=intent.recon_score,
                approved_amount=intent.approved_amount,
                held_amount=intent.held_amount,
                has_ricardian_wrapper=instrument is not None,
                ricardian_status=instrument.status if instrument else None,
            )
        )

    return OperatorQueueResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/settlements/{intent_id}/risk_snapshot", response_model=RiskSnapshotResponse)
def get_risk_snapshot(intent_id: str, db: Session = Depends(get_db)) -> RiskSnapshotResponse:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Settlement not found")
    decision = (
        db.query(RiskDecision).filter(RiskDecision.shipment_id == intent.shipment_id).order_by(RiskDecision.decided_at.desc()).first()
    )
    score = decision.risk_score if decision else intent.risk_score
    band = _risk_band(score)
    return RiskSnapshotResponse(
        settlement_id=intent_id,
        intent_id=intent_id,
        risk_score=score,
        risk_band=band,
        engine_mode="FULL",
        factors=[],
        created_at=decision.decided_at if decision else intent.created_at,
    )


@router.get("/settlements/{intent_id}/events", response_model=List[SettlementEventItem])
def get_settlement_events(
    intent_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[SettlementEventItem]:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Settlement not found")

    events = (
        db.query(SettlementEvent)
        .filter(SettlementEvent.payment_intent_id == intent_id)
        .order_by(SettlementEvent.occurred_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items: List[SettlementEventItem] = []
    for evt in events:
        items.append(
            SettlementEventItem(
                id=evt.id,
                settlement_id=evt.payment_intent_id,
                event_type=evt.event_type,
                description=None,
                metadata=evt.extra_metadata,
                created_at=evt.occurred_at,
            )
        )
    return items


@router.get("/settlements/{intent_id}/reconciliation", response_model=ReconciliationSummary)
def get_reconciliation_summary(intent_id: str, db: Session = Depends(get_db)) -> ReconciliationSummary:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == intent_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Settlement not found")

    result = get_reconciliation_result(intent_id)
    if result is None:
        result = run_reconciliation_for_intent(db, intent)
        db.commit()
        db.refresh(intent)

    return ReconciliationSummary(
        decision=(result.decision.value if hasattr(result.decision, "value") else str(result.decision)),
        approved_amount=result.approved_amount,
        held_amount=result.held_amount,
        recon_score=result.recon_score,
        policy_id=result.policy_id,
        flags=result.flags,
        lines=[
            ReconciliationLineResult(
                line_id=line.line_id,
                status=(line.status.value if hasattr(line.status, "value") else str(line.status)),
                reason_code=line.reason_code,
                contract_amount=line.contract_amount,
                billed_amount=line.billed_amount,
                approved_amount=line.approved_amount,
                held_amount=line.held_amount,
                flags=line.flags,
            )
            for line in result.lines
        ],
    )


@router.get("/iot/health/summary", response_model=OperatorIoTHealthSummary)
def get_iot_health_summary() -> OperatorIoTHealthSummary:
    provider: IoTDataProvider = MockIoTDataProvider()
    health = provider.get_global_health()
    summary = IoTHealthSummary(
        shipments_with_iot=health.shipments_with_iot,
        active_sensors=health.active_sensors,
        alerts_last_24h=health.alerts_last_24h,
        critical_alerts_last_24h=health.critical_alerts_last_24h,
        coverage_percent=health.coverage_percent,
    )
    return OperatorIoTHealthSummary(
        device_count_active=summary.active_sensors,
        device_count_offline=0,
        stale_gps_count=0,
        stale_env_count=0,
        last_ingest_age_seconds=0,
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/events/stream", response_model=OperatorEventsResponse)
def get_operator_events_stream(
    since: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> OperatorEventsResponse:
    query = db.query(SettlementEvent).order_by(SettlementEvent.occurred_at.desc())
    if since:
        query = query.filter(SettlementEvent.occurred_at > since)
    events = query.limit(limit).all()
    items: List[OperatorEvent] = []
    for evt in events:
        items.append(
            OperatorEvent(
                id=evt.id,
                kind=("payment_confirmed" if evt.event_type in {"CAPTURED", "CASH_RELEASED"} else "info"),
                settlement_id=evt.payment_intent_id,
                severity="info",
                message=evt.event_type,
                created_at=evt.occurred_at,
            )
        )
    return OperatorEventsResponse(items=items)


@router.get(
    "/settlements/{settlement_id}/auditpack",
    response_model=AuditPackResponse,
)
def get_auditpack_for_settlement(
    settlement_id: str,
    db: Session = Depends(get_db),
) -> AuditPackResponse:
    intent = db.query(PaymentIntent).filter(PaymentIntent.id == settlement_id).first()
    if not intent:
        raise HTTPException(status_code=404, detail="Settlement not found")

    lane = AuditLaneSummary(
        origin_country=None,
        origin_city=None,
        destination_country=None,
        destination_city=None,
        corridor=None,
    )
    core = AuditCoreSummary(
        amount=intent.amount,
        currency=intent.currency,
        shipper_id=None,
        carrier_id=None,
        broker_id=None,
        state=intent.status,
        lane=lane,
    )
    proof_summary = AuditProofSummary(
        intent_hash=intent.intent_hash,
        status=AuditProofStatus.NOT_AVAILABLE,
        provider=AuditProofProvider.NONE,
        last_verified_at=None,
    )

    decisions = db.query(RiskDecision).filter(RiskDecision.shipment_id == intent.shipment_id).order_by(RiskDecision.decided_at.asc()).all()
    snapshots: list[AuditRiskSnapshot] = []
    for decision in decisions:
        band = _risk_band(decision.risk_score)
        snapshots.append(
            AuditRiskSnapshot(
                score=decision.risk_score,
                band=band or "",
                created_at=decision.decided_at,
            )
        )
    latest_score = snapshots[-1].score if snapshots else intent.risk_score
    risk_summary = AuditRiskSummary(
        latest_score=latest_score,
        latest_band=_risk_band(latest_score),
        engine_mode="FULL",
        snapshots=snapshots,
    )

    events = (
        db.query(SettlementEvent)
        .filter(SettlementEvent.payment_intent_id == settlement_id)
        .order_by(SettlementEvent.occurred_at.asc())
        .all()
    )
    event_items: list[AuditEventItem] = [AuditEventItem(event_type=evt.event_type, at=evt.occurred_at, severity=None) for evt in events]
    events_timeline = AuditEventTimeline(
        count=len(event_items),
        first_at=event_items[0].at if event_items else None,
        last_at=event_items[-1].at if event_items else None,
        items=event_items,
    )

    sla_summary = AuditSLASummary(
        sla_band="ON_TIME",
        expected_p95_seconds=None,
        actual_seconds=None,
        breach=False,
    )

    iot_summary = AuditIoTSummary(
        has_iot=False,
        alerts_count=None,
        temp_excursions=None,
        gps_gaps=None,
    )

    documents = AuditDocuments(
        bol=AuditDocumentRef(external_id=None, source=None, available=False),
        customs=AuditDocumentRef(external_id=None, source=None, available=False),
        pod=AuditDocumentRef(external_id=None, source=None, available=False),
    )
    audit_metadata = AuditMetadata(triggered_by_rules=[], auto_generated=True)

    legal_wrapper = None
    instrument = (
        db.query(RicardianInstrument)
        .filter(RicardianInstrument.physical_reference == intent.shipment_id)
        .order_by(RicardianInstrument.created_at.desc())
        .first()
    )
    if instrument:
        legal_wrapper = AuditLegalWrapper(
            instrument_id=str(instrument.id),
            instrument_type=instrument.instrument_type,
            physical_reference=instrument.physical_reference,
            pdf_uri=instrument.pdf_uri,
            pdf_hash=instrument.pdf_hash,
            ricardian_version=instrument.ricardian_version,
            governing_law=instrument.governing_law,
            smart_contract_chain=instrument.smart_contract_chain,
            smart_contract_address=instrument.smart_contract_address,
            last_signed_tx_hash=instrument.last_signed_tx_hash,
            status=instrument.status,
            freeze_reason=instrument.freeze_reason,
        )

    return AuditPackResponse(
        settlement_id=settlement_id,
        generated_at=datetime.now(timezone.utc),
        source="virtual_v1",
        core=core,
        proof_summary=proof_summary,
        risk_summary=risk_summary,
        events=events_timeline,
        sla_summary=sla_summary,
        iot_summary=iot_summary,
        documents=documents,
        audit_metadata=audit_metadata,
        legal_wrapper=legal_wrapper,
    )
