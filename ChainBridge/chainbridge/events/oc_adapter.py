"""Operator Console adapter for live intelligence stream."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OCEvent:
    shipment_id: str
    tokens: List[Dict[str, Any]]
    risk: Dict[str, Any]
    anomalies: List[str]
    timeline: List[Dict[str, Any]]
    proofs: List[Dict[str, Any]]
    settlement: Dict[str, Any]
    actor: str
    event_type: str
    updated_at: datetime
    change_from: Optional[str] = None
    change_to: Optional[str] = None
    eta_adjustment_minutes: Optional[int] = None
    active_anomalies: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shipment_id": self.shipment_id,
            "tokens": self.tokens,
            "risk": self.risk,
            "anomalies": self.anomalies,
            "timeline": self.timeline,
            "proofs": self.proofs,
            "settlement": self.settlement,
            "actor": self.actor,
            "event_type": self.event_type,
            "updated_at": self.updated_at.isoformat(),
            "change_from": self.change_from,
            "change_to": self.change_to,
            "eta_adjustment_minutes": self.eta_adjustment_minutes,
            "active_anomalies": self.active_anomalies or self.anomalies,
        }


class OCAdapter:
    """Publishes deterministic OC events.

    In production this would push to Kafka/WebSocket. Here we log JSON so tests
    can assert on the payloads.
    """

    def __init__(
        self,
        publisher: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ) -> None:
        self._history: List[OCEvent] = []
        self._publisher = publisher

    async def emit(self, event: OCEvent) -> None:
        self._history.append(event)
        payload = event.to_dict()
        logger.info("OC event %s => %s", event.event_type, json.dumps(payload))
        if self._publisher:
            await self._publisher(payload)

    def drain(self) -> List[OCEvent]:
        history = list(self._history)
        self._history.clear()
        return history


__all__ = ["OCAdapter", "OCEvent"]
