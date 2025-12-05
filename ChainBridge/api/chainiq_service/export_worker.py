"""Snapshot export worker helpers for downstream integrations."""

from datetime import datetime
from typing import Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from api.models.canonical import ShipmentEventType
from api.models.chainfreight import ShipmentEvent
from api.models.chainiq import DocumentHealthSnapshot, SnapshotExportEvent

MAX_RETRIES = 5
_MAX_TEXT_LENGTH = 500
CHAINIQ_SOURCE = "CHAINIQ"


class SnapshotExportEventNotFound(Exception):
    """Raised when snapshot export event does not exist."""


class SnapshotExportInvalidState(Exception):
    """Raised when callers attempt an invalid transition."""


def _truncate(value: Optional[str]) -> Optional[str]:
    return value[:_MAX_TEXT_LENGTH] if value else None


def _get_shipment_id(db: Session, snapshot_id: int) -> Optional[str]:
    return db.query(DocumentHealthSnapshot.shipment_id).filter(DocumentHealthSnapshot.id == snapshot_id).scalar()


def _record_shipment_event(
    db: Session,
    *,
    shipment_id: str,
    event_type: ShipmentEventType,
    payload: Optional[Dict[str, object]] = None,
    actor: Optional[str] = None,
    occurred_at: Optional[datetime] = None,
) -> None:
    event = ShipmentEvent(
        shipment_id=shipment_id,
        event_type=event_type.value,
        actor=actor,
        source_service=CHAINIQ_SOURCE,
        occurred_at=occurred_at or datetime.utcnow(),
        payload=payload,
    )
    db.add(event)


def _record_snapshot_event(
    db: Session,
    snapshot_id: int,
    *,
    event_type: ShipmentEventType,
    payload: Optional[Dict[str, object]] = None,
    actor: Optional[str] = None,
) -> None:
    shipment_id = _get_shipment_id(db, snapshot_id)
    if not shipment_id:
        return
    payload_data: Dict[str, object] = {"snapshot_id": snapshot_id}
    if payload:
        payload_data.update(payload)
    _record_shipment_event(
        db,
        shipment_id=shipment_id,
        event_type=event_type,
        payload=payload_data,
        actor=actor,
    )


def enqueue_snapshot_export_events(
    db: Session,
    snapshot: DocumentHealthSnapshot,
    *,
    target_systems: Sequence[str],
    reason: Optional[str] = None,
) -> List[SnapshotExportEvent]:
    """Insert snapshot export events for a snapshot and return the created rows."""
    truncated_reason = _truncate(reason)
    events: List[SnapshotExportEvent] = []
    try:
        for target in target_systems:
            event = SnapshotExportEvent(
                snapshot_id=snapshot.id,
                target_system=target,
                status="PENDING",
                reason=truncated_reason,
            )
            db.add(event)
            db.flush()
            _record_shipment_event(
                db,
                shipment_id=snapshot.shipment_id,
                event_type=ShipmentEventType.SNAPSHOT_REQUESTED,
                payload={
                    "snapshot_export_id": event.id,
                    "target_system": target,
                    "reason": truncated_reason,
                },
            )
            events.append(event)
        db.commit()
        for event in events:
            db.refresh(event)
        return events
    except Exception:
        db.rollback()
        raise


def fetch_pending_events(
    db: Session,
    *,
    target_system: Optional[str] = None,
    limit: int = 50,
) -> List[SnapshotExportEvent]:
    """Return pending export events ordered FIFO."""
    query = (
        db.query(SnapshotExportEvent).filter(SnapshotExportEvent.status == "PENDING").filter(SnapshotExportEvent.retry_count < MAX_RETRIES)
    )
    if target_system:
        query = query.filter(SnapshotExportEvent.target_system == target_system)

    return query.order_by(SnapshotExportEvent.created_at.asc(), SnapshotExportEvent.id.asc()).limit(limit).all()


def claim_next_pending_event(
    db: Session,
    worker_id: str,
    *,
    target_system: Optional[str] = None,
) -> Optional[SnapshotExportEvent]:
    """
    Atomically claim the oldest pending event for a worker.

    Returns None when no events are available.
    """
    try:
        while True:
            query = (
                db.query(SnapshotExportEvent)
                .filter(SnapshotExportEvent.status == "PENDING")
                .filter(SnapshotExportEvent.retry_count < MAX_RETRIES)
                .order_by(SnapshotExportEvent.created_at.asc(), SnapshotExportEvent.id.asc())
            )
            if target_system:
                query = query.filter(SnapshotExportEvent.target_system == target_system)

            candidate = query.first()
            if not candidate:
                db.rollback()
                return None

            now = datetime.utcnow()
            updated = (
                db.query(SnapshotExportEvent)
                .filter(
                    SnapshotExportEvent.id == candidate.id,
                    SnapshotExportEvent.status == "PENDING",
                )
                .update(
                    {
                        SnapshotExportEvent.status: "IN_PROGRESS",
                        SnapshotExportEvent.claimed_by: worker_id,
                        SnapshotExportEvent.claimed_at: now,
                        SnapshotExportEvent.updated_at: now,
                    },
                    synchronize_session=False,
                )
            )
            if updated:
                db.commit()
                claimed = db.query(SnapshotExportEvent).filter(SnapshotExportEvent.id == candidate.id).first()
                if claimed:
                    _record_snapshot_event(
                        db,
                        claimed.snapshot_id,
                        event_type=ShipmentEventType.SNAPSHOT_CLAIMED,
                        payload={
                            "snapshot_export_id": claimed.id,
                            "target_system": claimed.target_system,
                            "worker_id": worker_id,
                        },
                        actor=worker_id,
                    )
                    db.commit()
                    db.refresh(claimed)
                return claimed
            db.rollback()
    except Exception:
        db.rollback()
        raise


def _get_event_for_update(db: Session, event_id: int) -> SnapshotExportEvent:
    event = db.query(SnapshotExportEvent).filter(SnapshotExportEvent.id == event_id).with_for_update().first()
    if not event:
        raise SnapshotExportEventNotFound(f"SnapshotExportEvent {event_id} not found")
    return event


def mark_event_success(db: Session, event_id: int) -> SnapshotExportEvent:
    """Mark an export event as successfully processed."""
    try:
        event = _get_event_for_update(db, event_id)
        if event.status == "SUCCESS":
            db.commit()
            return event
        if event.status != "IN_PROGRESS":
            db.rollback()
            raise SnapshotExportInvalidState(f"Cannot mark {event.status} event success")

        event.status = "SUCCESS"
        event.last_error = None
        event.updated_at = datetime.utcnow()
        db.add(event)
        _record_snapshot_event(
            db,
            event.snapshot_id,
            event_type=ShipmentEventType.SNAPSHOT_COMPLETED,
            payload={
                "snapshot_export_id": event.id,
                "worker_id": event.claimed_by,
            },
            actor=event.claimed_by,
        )
        db.commit()
        db.refresh(event)
        return event
    except SnapshotExportEventNotFound:
        db.rollback()
        raise
    except SnapshotExportInvalidState:
        raise
    except Exception:
        db.rollback()
        raise


def mark_event_failed(
    db: Session,
    event_id: int,
    reason: Optional[str] = None,
    retryable: bool = True,
) -> SnapshotExportEvent:
    """
    Mark an export event failure, optionally requeueing it when retries remain.
    """
    truncated_reason = _truncate(reason)

    try:
        event = _get_event_for_update(db, event_id)
        if event.status == "FAILED":
            db.commit()
            return event
        if event.status != "IN_PROGRESS":
            db.rollback()
            raise SnapshotExportInvalidState(f"Cannot mark {event.status} event failed")

        event.retry_count = min(event.retry_count + 1, MAX_RETRIES)
        event.last_error = truncated_reason
        event.updated_at = datetime.utcnow()

        should_retry = retryable and event.retry_count < MAX_RETRIES
        if should_retry:
            event.status = "PENDING"
            event.claimed_by = None
            event.claimed_at = None
        else:
            event.status = "FAILED"

        db.add(event)
        _record_snapshot_event(
            db,
            event.snapshot_id,
            event_type=ShipmentEventType.SNAPSHOT_FAILED,
            payload={
                "snapshot_export_id": event.id,
                "worker_id": event.claimed_by,
                "error_message": truncated_reason,
                "retry_count": event.retry_count,
                "will_retry": should_retry,
            },
            actor=event.claimed_by,
        )
        db.commit()
        db.refresh(event)
        return event
    except SnapshotExportEventNotFound:
        db.rollback()
        raise
    except SnapshotExportInvalidState:
        raise
    except Exception:
        db.rollback()
        raise


def get_snapshot_payload(
    db: Session,
    event: SnapshotExportEvent,
) -> Dict[str, object]:
    """Return a neutral payload for downstream adapters."""
    snapshot = db.query(DocumentHealthSnapshot).filter(DocumentHealthSnapshot.id == event.snapshot_id).first()
    if not snapshot:
        raise ValueError(f"Snapshot {event.snapshot_id} not found")

    return {
        "snapshot_id": snapshot.id,
        "shipment_id": snapshot.shipment_id,
        "corridor_code": snapshot.corridor_code,
        "mode": snapshot.mode,
        "incoterm": snapshot.incoterm,
        "template_name": snapshot.template_name,
        "completeness_pct": snapshot.completeness_pct,
        "blocking_gap_count": snapshot.blocking_gap_count,
        "risk_score": snapshot.risk_score,
        "risk_level": snapshot.risk_level,
        "created_at": snapshot.created_at.isoformat(),
    }
