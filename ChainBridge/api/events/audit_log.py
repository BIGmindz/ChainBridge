"""Audit sink wiring events into persistent activity feed."""
from __future__ import annotations

import json
import logging
from typing import Callable, Optional

from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.events.bus import BaseEventSink, Event, EventType, event_bus
from api.models.chainpay import PaymentIntent, SettlementEventAudit

logger = logging.getLogger(__name__)


def _json_safe(payload: dict) -> dict:
    try:
        return json.loads(json.dumps(payload, default=str))
    except Exception:  # pragma: no cover - defensive
        return {}


class AuditEventSink(BaseEventSink):
    """Persist operator-facing events in the audit log table."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def set_session_factory(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def _should_persist(self, event: Event) -> bool:
        if event.type in {
            EventType.SETTLEMENT_EVENT_APPENDED,
            EventType.PAYMENT_INTENT_UPDATED,
            EventType.PAYMENT_INTENT_CREATED,
            EventType.WORKER_HEARTBEAT,
        }:
            return True
        if event.type == EventType.WEBHOOK_RECEIVED and isinstance(event.payload, dict):
            return bool(event.payload.get("payment_intent_id"))
        return False

    @staticmethod
    def _source_from_actor(actor: str) -> str:
        if not actor:
            return "system"
        return actor.split(":", 1)[0]

    @staticmethod
    def _resolve_payment_intent_id(event: Event) -> Optional[str]:
        if isinstance(event.payload, dict):
            if event.payload.get("payment_intent_id"):
                return str(event.payload["payment_intent_id"])
            if event.payload.get("id"):
                return str(event.payload["id"])
        return event.correlation_id

    @staticmethod
    def _resolve_shipment_id(session: Session, event: Event, payment_intent_id: Optional[str]) -> Optional[str]:
        if isinstance(event.payload, dict) and event.payload.get("shipment_id"):
            return str(event.payload["shipment_id"])
        if payment_intent_id:
            intent = session.query(PaymentIntent).filter(PaymentIntent.id == payment_intent_id).first()
            return intent.shipment_id if intent else None
        return None

    def publish(self, event: Event) -> None:
        if not self._should_persist(event):
            return
        session: Session | None = None
        try:
            session = self._session_factory()
            payment_intent_id = self._resolve_payment_intent_id(event)
            shipment_id = self._resolve_shipment_id(session, event, payment_intent_id)
            occurred_at = event.occurred_at
            if occurred_at.tzinfo:
                occurred_at = occurred_at.replace(tzinfo=None)
            audit_row = SettlementEventAudit(
                event_type=event.type.value,
                source=self._source_from_actor(event.actor),
                actor=event.actor,
                payment_intent_id=payment_intent_id,
                shipment_id=shipment_id,
                occurred_at=occurred_at,
                payload_summary=_json_safe(event.payload if isinstance(event.payload, dict) else {}),
            )
            session.add(audit_row)
            session.commit()
        except Exception as exc:  # pragma: no cover - safeguard
            if session:
                session.rollback()
            logger.warning(
                "event_audit_sink_failed",
                extra={"event_type": event.type.value, "error": str(exc)},
            )
        finally:
            if session:
                session.close()


audit_sink = AuditEventSink()
event_bus.add_sink(audit_sink)
