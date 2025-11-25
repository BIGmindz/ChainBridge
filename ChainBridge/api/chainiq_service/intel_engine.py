"""Core intelligence computations for ChainIQ shipment health."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, aliased

from api.chainiq_service.export_worker import enqueue_snapshot_export_events
from api.chainiq_service.template_resolver import resolve_required_docs_for_shipment
from api.chainiq_service.schemas import (
    DocumentHealth,
    RiskSummary,
    SettlementHealth,
    ShipmentHealthResponse,
)
from api.models.canonical import RiskLevel, ShipmentEventType
from api.models.chaindocs import Document, Shipment, ShipmentDocRequirement
from api.models.chainiq import (
    DocumentHealthSnapshot,
    RiskDecision,
    ShipmentEvent,
    SnapshotExportEvent,
)
from api.models.chainpay import SettlementMilestone, SettlementPlan
from api.services.payment_intents import ensure_payment_intent_for_snapshot, is_payment_approved

logger = logging.getLogger(__name__)
EXPORT_TARGET_SYSTEMS = ["BIS", "SXT", "ML_PIPELINE"]
RISK_DECISION_EVENT_TYPE = ShipmentEventType.RISK_DECIDED.value
RISK_MODEL_VERSION = "document-health-v1"
CHAINIQ_SOURCE = "CHAINIQ"


def _compute_document_health(
    documents: List[Document],
    requirements: List[ShipmentDocRequirement],
) -> Tuple[DocumentHealth, List[str]]:
    present_types = {document.type for document in documents if document.type}
    required_docs = [req.doc_type_code for req in requirements if req.required_flag]
    optional_docs = [req.doc_type_code for req in requirements if not req.required_flag]
    missing_required = [code for code in required_docs if code not in present_types]
    blocking_missing = [
        req.doc_type_code
        for req in requirements
        if req.required_flag and req.blocking_flag and req.doc_type_code not in present_types
    ]
    present_count = sum(
        1 for req in requirements if req.required_flag and req.doc_type_code in present_types
    )
    required_total = len(required_docs)
    optional_total = len(optional_docs)
    completeness_pct = int(round((present_count / required_total) * 100)) if required_total else 0

    document_health = DocumentHealth(
        present_count=present_count,
        missing_count=len(missing_required),
        missing_documents=missing_required,
        completeness_pct=completeness_pct,
        required_total=required_total,
        optional_total=optional_total,
        blocking_gap_count=len(blocking_missing),
        blocking_documents=blocking_missing,
    )

    return document_health, blocking_missing


def _compute_settlement_health(plan: Optional[SettlementPlan]) -> SettlementHealth:
    milestones: List[SettlementMilestone] = sorted(plan.milestones, key=lambda m: m.id) if plan else []
    milestones_total = len(milestones)
    milestones_paid = sum(1 for milestone in milestones if milestone.status == "PAID")
    milestones_pending = sum(1 for milestone in milestones if milestone.status == "PENDING")
    milestones_held = sum(1 for milestone in milestones if milestone.status == "HELD")
    completion_pct = int(round((milestones_paid / milestones_total) * 100)) if milestones_total else 0
    next_pending = next((milestone.event for milestone in milestones if milestone.status == "PENDING"), None)

    return SettlementHealth(
        milestones_total=milestones_total,
        milestones_paid=milestones_paid,
        milestones_pending=milestones_pending,
        milestones_held=milestones_held,
        completion_pct=completion_pct,
        float_reduction_estimate=plan.float_reduction_estimate if plan else None,
        next_milestone=next_pending,
    )


def _compute_risk_summary(
    document_health: DocumentHealth,
    settlement_health: SettlementHealth,
    blocking_missing: List[str],
) -> RiskSummary:
    score = 100
    drivers: List[str] = []

    if document_health.missing_count:
        doc_penalty = 15 * document_health.missing_count
        score -= doc_penalty
        drivers.append(f"{document_health.missing_count} missing required documents")

    if blocking_missing:
        blocking_penalty = 5 * len(blocking_missing)
        score -= blocking_penalty
        drivers.append(f"{len(blocking_missing)} blocking document(s) missing")

    if document_health.completeness_pct < 100:
        drivers.append("Document set incomplete")

    if settlement_health.milestones_held:
        hold_penalty = 10 * settlement_health.milestones_held
        score -= hold_penalty
        drivers.append(f"{settlement_health.milestones_held} held settlement milestones")

    float_estimate = settlement_health.float_reduction_estimate if settlement_health.float_reduction_estimate is not None else 0.0
    bounded_float = max(0.0, min(1.0, float_estimate))
    float_penalty = int((1.0 - bounded_float) * 25)
    if float_penalty:
        drivers.append(f"float reduction at {int(bounded_float * 100)}%")
    score -= float_penalty

    score = max(0, min(100, score))

    if score >= 80:
        level = RiskLevel.LOW
    elif score >= 55:
        level = RiskLevel.MEDIUM
    elif score >= 40:
        level = RiskLevel.HIGH
    else:
        level = RiskLevel.CRITICAL

    if not drivers:
        drivers.append("Docs and settlement milestones satisfied")

    return RiskSummary(score=score, level=level.value, drivers=drivers)


def _recommended_actions(
    document_health: DocumentHealth,
    settlement_health: SettlementHealth,
) -> List[str]:
    actions: List[str] = []

    for missing_doc in document_health.missing_documents:
        actions.append(f"Upload missing {missing_doc}")

    if settlement_health.milestones_held > 0:
        actions.append("Resolve issues blocking settlement milestones.")

    if document_health.completeness_pct < 100:
        actions.append("Complete document set before next sailing/payment.")

    if not actions:
        actions.append("Maintain proactive monitoring cadence.")

    return actions


def _persist_document_health_snapshot(
    db: Session,
    shipment_id: str,
    shipment: Optional[Shipment],
    template_name: Optional[str],
    document_health: DocumentHealth,
    risk: RiskSummary,
) -> Optional[DocumentHealthSnapshot]:
    """Persist a document health snapshot for telemetry purposes."""
    try:
        snapshot = DocumentHealthSnapshot(
            shipment_id=shipment_id,
            corridor_code=shipment.corridor_code if shipment else None,
            mode=shipment.mode if shipment else None,
            incoterm=shipment.incoterm if shipment else None,
            template_name=template_name,
            present_count=document_health.present_count,
            missing_count=document_health.missing_count,
            required_total=document_health.required_total,
            optional_total=document_health.optional_total,
            blocking_gap_count=document_health.blocking_gap_count,
            completeness_pct=document_health.completeness_pct,
            risk_score=risk.score,
            risk_level=risk.level,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot
    except Exception as exc:  # pragma: no cover - guardrail
        logger.warning("Failed to persist document health snapshot: %s", exc)
        db.rollback()
        return None


def _enqueue_snapshot_export_events(
    db: Session,
    snapshot: DocumentHealthSnapshot,
) -> None:
    """Insert outbox entries for downstream export workers."""
    try:
        enqueue_snapshot_export_events(
            db,
            snapshot,
            target_systems=EXPORT_TARGET_SYSTEMS,
        )
    except Exception as exc:  # pragma: no cover - guardrail
        logger.warning("Failed to enqueue snapshot export events for %s: %s", snapshot.id, exc)


def _autowire_payment_intent(
    db: Session,
    shipment: Optional[Shipment],
    snapshot: Optional[DocumentHealthSnapshot],
    risk_level: str,
    plan: Optional[SettlementPlan],
) -> None:
    """Create a PaymentIntent when risk is approved and data is available."""
    if not shipment or not snapshot:
        return
    if not is_payment_approved(risk_level):
        return
    try:
        intent = ensure_payment_intent_for_snapshot(
            db,
            shipment=shipment,
            snapshot=snapshot,
            amount=plan.total_value if plan else None,
            currency="USD",
            counterparty=None,
            notes="auto-created via ChainIQ risk approval",
        )
        logger.info(
            "chainpay.payment_intent.event",
            extra={
                "route": "payment_intents.autowire",
                "payment_intent_id": intent.id,
                "shipment_id": intent.shipment_id,
                "status": intent.status,
                "corridor_code": shipment.corridor_code,
                "risk_score": intent.risk_score,
                "risk_level": intent.risk_level,
                "has_proof": bool(intent.proof_pack_id),
                "actor": "system",
            },
        )
    except Exception as exc:  # pragma: no cover - guardrail
        logger.warning("Failed to autowire PaymentIntent for %s: %s", shipment.id, exc)


def compute_shipment_health(db: Session, shipment_id: str) -> ShipmentHealthResponse:
    """
    Compute shipment health derived from documents and settlement milestones.

    Returns a deterministic summary even when shipments are partially populated.
    """
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    requirements, template_name = resolve_required_docs_for_shipment(db, shipment)
    documents = (
        db.query(Document)
        .filter(Document.shipment_id == shipment_id)
        .all()
    )
    plan = (
        db.query(SettlementPlan)
        .filter(SettlementPlan.shipment_id == shipment_id)
        .first()
    )

    document_health, blocking_missing = _compute_document_health(documents, requirements)
    settlement_health = _compute_settlement_health(plan)
    risk = _compute_risk_summary(document_health, settlement_health, blocking_missing)
    actions = _recommended_actions(document_health, settlement_health)

    _persist_risk_decision_and_event(
        db,
        shipment_id,
        risk_score=risk.score,
        risk_level=risk.level,
        document_health=document_health,
        settlement_health=settlement_health,
    )

    if shipment or document_health.required_total or document_health.missing_count:
        snapshot = _persist_document_health_snapshot(
            db,
            shipment_id,
            shipment,
            template_name,
            document_health,
            risk,
        )
        if snapshot:
            _enqueue_snapshot_export_events(db, snapshot)
            _autowire_payment_intent(db, shipment, snapshot, risk.level, plan)

    return ShipmentHealthResponse(
        shipment_id=shipment_id,
        document_health=document_health,
        settlement_health=settlement_health,
        risk=risk,
        recommended_actions=actions,
    )


def get_at_risk_shipments(
    db: Session,
    min_risk_score: int = 70,
    max_results: int = 50,
    corridor_code: Optional[str] = None,
    mode: Optional[str] = None,
    incoterm: Optional[str] = None,
    risk_level: Optional[str] = None,
    offset: int = 0,
) -> List[Tuple[DocumentHealthSnapshot, Optional[str], Optional[datetime]]]:
    """
    Return latest snapshots for shipments exceeding risk thresholds.

    Includes shipments that either meet the risk score floor or have blocking gaps.
    """
    subquery = (
        db.query(
            DocumentHealthSnapshot.shipment_id.label("shipment_id"),
            func.max(DocumentHealthSnapshot.created_at).label("max_created_at"),
        )
        .group_by(DocumentHealthSnapshot.shipment_id)
        .subquery()
    )

    snapshot_alias = aliased(DocumentHealthSnapshot)
    event_ranked = (
        db.query(
            snapshot_alias.shipment_id.label("shipment_id"),
            SnapshotExportEvent.status.label("status"),
            SnapshotExportEvent.updated_at.label("updated_at"),
            func.row_number()
            .over(
                partition_by=snapshot_alias.shipment_id,
                order_by=SnapshotExportEvent.updated_at.desc(),
            )
            .label("event_rank"),
        )
        .join(SnapshotExportEvent, SnapshotExportEvent.snapshot_id == snapshot_alias.id)
        .subquery()
    )

    query = (
        db.query(
            DocumentHealthSnapshot,
            event_ranked.c.status,
            event_ranked.c.updated_at,
        )
        .join(
            subquery,
            (DocumentHealthSnapshot.shipment_id == subquery.c.shipment_id)
            & (DocumentHealthSnapshot.created_at == subquery.c.max_created_at),
        )
        .outerjoin(
            event_ranked,
            (DocumentHealthSnapshot.shipment_id == event_ranked.c.shipment_id)
            & (event_ranked.c.event_rank == 1),
        )
        .filter(
            or_(
                DocumentHealthSnapshot.risk_score >= min_risk_score,
                DocumentHealthSnapshot.blocking_gap_count > 0,
            )
        )
    )

    if corridor_code:
        query = query.filter(DocumentHealthSnapshot.corridor_code == corridor_code)
    if mode:
        query = query.filter(DocumentHealthSnapshot.mode == mode)
    if incoterm:
        query = query.filter(DocumentHealthSnapshot.incoterm == incoterm)
    if risk_level:
        try:
            normalized_level = RiskLevel.normalize(risk_level).value
        except ValueError:
            normalized_level = risk_level
        query = query.filter(DocumentHealthSnapshot.risk_level == normalized_level)

    query = query.order_by(
        DocumentHealthSnapshot.risk_score.desc(),
        DocumentHealthSnapshot.blocking_gap_count.desc(),
        DocumentHealthSnapshot.created_at.desc(),
    )

    if offset:
        query = query.offset(offset)

    query = query.limit(max_results)

    return query.all()


def _persist_risk_decision_and_event(
    db: Session,
    shipment_id: str,
    *,
    risk_score: int,
    risk_level: str,
    document_health: DocumentHealth,
    settlement_health: SettlementHealth,
) -> Optional[RiskDecision]:
    """Persist the latest risk decision and accompanying shipment event."""
    features: Dict[str, int] = {
        "blocking_gap_count": document_health.blocking_gap_count,
        "missing_count": document_health.missing_count,
        "completeness_pct": document_health.completeness_pct,
        "settlement_completion_pct": settlement_health.completion_pct,
        "settlement_milestones_held": settlement_health.milestones_held,
    }
    occurred_at = datetime.utcnow()
    try:
        decision = RiskDecision(
            shipment_id=shipment_id,
            risk_score=risk_score,
            risk_level=risk_level,
            model_version=RISK_MODEL_VERSION,
            features=features,
            decided_at=occurred_at,
        )
        db.add(decision)
        db.flush()

        event = ShipmentEvent(
            shipment_id=shipment_id,
            event_type=RISK_DECISION_EVENT_TYPE,
            source_service=CHAINIQ_SOURCE,
            occurred_at=occurred_at,
            payload={
                "risk_decision_id": decision.id,
                "risk_score": risk_score,
                "risk_level": risk_level,
            },
        )
        db.add(event)
        db.commit()
        db.refresh(decision)
        return decision
    except Exception as exc:  # pragma: no cover - safeguard
        logger.warning("Failed to persist risk decision for %s: %s", shipment_id, exc)
        db.rollback()
        return None
