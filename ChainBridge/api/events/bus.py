"""Pluggable, structured event bus."""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Awaitable, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    PAYMENT_INTENT_CREATED = "payment_intent.created"
    PAYMENT_INTENT_UPDATED = "payment_intent.updated"
    PAYMENT_INTENT_RECONCILED = "payment_intent.reconciled"
    STAKE_CREATED = "stake.created"
    STAKE_COMPLETED = "stake.completed"
    DOCUMENT_VERIFIED = "document.verified"
    SETTLEMENT_EVENT_APPENDED = "settlement_event.appended"
    WEBHOOK_RECEIVED = "webhook.received"
    WORKER_HEARTBEAT = "worker.heartbeat"
    SHIPMENT_INGESTED = "shipment.ingested"
    SHIPMENT_RISK_FLAGGED = "shipment.risk_flagged"


@dataclass
class Event:
    type: EventType
    payload: dict
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None
    actor: str = "system"


Handler = Union[Callable[[dict], Awaitable[None]], Callable[[dict], None]]


class BaseEventSink(ABC):
    @abstractmethod
    def publish(self, event: Event) -> None: ...


class InProcessHandlerSink(BaseEventSink):
    """Backward-compatible in-process callback sink."""

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[Handler]] = {}

    def subscribe(self, event_type: EventType, handler: Handler) -> None:
        self._subscribers.setdefault(event_type, []).append(handler)

    def clear_subscribers(self) -> None:
        self._subscribers = {}

    def publish(self, event: Event) -> None:
        handlers = list(self._subscribers.get(event.type, []))
        for handler in handlers:
            try:
                result = handler(event.payload)
                if asyncio.iscoroutine(result):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(result)
                        else:
                            loop.run_until_complete(result)
                    except RuntimeError:
                        asyncio.run(result)
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "event_bus_handler_failed",
                    extra={
                        "event_type": event.type.value,
                        "error": str(exc),
                        "sink": "InProcessHandlerSink",
                    },
                )
        logger.info(
            "event_bus_publish",
            extra={"event_type": event.type.value, "handlers": len(handlers)},
        )


class StructuredLogSink(BaseEventSink):
    """Emit structured JSON-friendly logs for every event."""

    def __init__(self, logger_: logging.Logger | None = None) -> None:
        self._logger = logger_ or logger

    @staticmethod
    def _json_safe(value: dict) -> dict:
        try:
            return json.loads(json.dumps(value, default=str))
        except Exception:  # pragma: no cover
            return {}

    def publish(self, event: Event) -> None:
        payload = {
            "event_id": str(event.event_id),
            "event_type": event.type.value,
            "occurred_at": event.occurred_at.isoformat(),
            "correlation_id": event.correlation_id,
            "actor": event.actor,
            "payload": self._json_safe(event.payload),
        }
        self._logger.info("event_bus_structured_event", extra={"event": payload})


class EventBus:
    """Minimal in-memory event bus."""

    def __init__(self, sinks: Optional[List[BaseEventSink]] = None) -> None:
        self._in_process_sink = InProcessHandlerSink()
        self._sinks: List[BaseEventSink] = [self._in_process_sink, StructuredLogSink()]
        if sinks:
            for sink in sinks:
                self.add_sink(sink)

    def add_sink(self, sink: BaseEventSink) -> None:
        self._sinks.append(sink)
        if isinstance(sink, InProcessHandlerSink):
            self._in_process_sink = sink

    def subscribe(self, event_type: EventType, handler: Handler) -> None:
        self._in_process_sink.subscribe(event_type, handler)

    def clear_subscribers(self) -> None:
        self._in_process_sink.clear_subscribers()

    @staticmethod
    def _derive_correlation_id(payload: dict, provided: Optional[str]) -> Optional[str]:
        if provided:
            return provided
        for key in ("payment_intent_id", "payment_intent", "id", "shipment_id"):
            val = payload.get(key) if isinstance(payload, dict) else None
            if val:
                return str(val)
        return None

    def publish(
        self,
        event_type: EventType,
        payload: dict,
        *,
        correlation_id: Optional[str] = None,
        actor: str = "system",
        occurred_at: Optional[datetime] = None,
    ) -> Event:
        event = Event(
            type=event_type,
            payload=payload,
            correlation_id=self._derive_correlation_id(payload, correlation_id),
            actor=actor or "system",
            occurred_at=occurred_at or datetime.now(timezone.utc),
        )
        for sink in list(self._sinks):
            try:
                sink.publish(event)
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "event_bus_sink_failed",
                    extra={
                        "event_type": event_type.value,
                        "sink": sink.__class__.__name__,
                        "error": str(exc),
                    },
                )
        return event


event_bus = EventBus()
