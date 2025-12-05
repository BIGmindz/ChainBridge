"""Runtime dispatcher that normalizes inbound events for the router."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Mapping, MutableMapping, Type

from pydantic import ValidationError

from chainbridge.events.schemas import (
    BaseEvent,
    EDITenderEvent,
    EDIStatusEvent,
    EventSource,
    EventType,
    GovernanceApprovalEvent,
    IoTAlertEvent,
    IoTGeofenceEvent,
    IoTTelemetryEvent,
    ProofComputedEvent,
    ProofValidatedEvent,
    SettlementCompleteEvent,
    SettlementInitiatedEvent,
    TokenCreatedEvent,
    TokenProofAttachedEvent,
    TokenTransitionEvent,
)

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from chainbridge.events.router import GlobalEventRouter

SCHEMA_MAP: Mapping[EventType, Type[BaseEvent]] = {
    EventType.IOT_TELEMETRY: IoTTelemetryEvent,
    EventType.IOT_GEOFENCE_ENTER: IoTGeofenceEvent,
    EventType.IOT_GEOFENCE_EXIT: IoTGeofenceEvent,
    EventType.IOT_ALERT_CRITICAL: IoTAlertEvent,
    EventType.IOT_ALERT_WARNING: IoTAlertEvent,
    EventType.EDI_TENDER_REQUEST: EDITenderEvent,
    EventType.EDI_STATUS_UPDATE: EDIStatusEvent,
    EventType.TOKEN_CREATED: TokenCreatedEvent,
    EventType.TOKEN_TRANSITION: TokenTransitionEvent,
    EventType.TOKEN_PROOF_ATTACHED: TokenProofAttachedEvent,
    EventType.PROOF_COMPUTED: ProofComputedEvent,
    EventType.PROOF_VALIDATED: ProofValidatedEvent,
    EventType.SETTLEMENT_INITIATED: SettlementInitiatedEvent,
    EventType.SETTLEMENT_COMPLETE: SettlementCompleteEvent,
    EventType.GOVERNANCE_APPROVAL: GovernanceApprovalEvent,
}


class DispatchError(RuntimeError):
    """Raised when incoming events cannot be normalised."""


class EventDispatcher:
    """Normalizes inbound payloads and submits them to the router."""

    def __init__(self, *, schema_map: Mapping[EventType, Type[BaseEvent]] | None = None) -> None:
        self._schema_map = schema_map or SCHEMA_MAP

    async def dispatch(self, router: GlobalEventRouter, payload: Dict[str, Any]):
        event = self.normalize(payload)
        return await router.submit(event)

    def normalize(self, payload: Dict[str, Any]) -> BaseEvent:
        event_type = self._detect_event_type(payload)
        schema = self._schema_map.get(event_type)
        if not schema:
            raise DispatchError(f"Unsupported event type: {event_type}")

        normalised = dict(payload)
        if "event_type" not in normalised:
            normalised["event_type"] = event_type.value
        if "source" not in normalised:
            normalised["source"] = self._default_source_for(event_type).value
        if "timestamp" not in normalised:
            normalised["timestamp"] = datetime.now(timezone.utc).isoformat()
        normalised.setdefault("actor_id", "system")
        normalised.setdefault("parent_shipment_id", normalised.get("shipment_id", "UNKNOWN"))
        normalised.setdefault("payload", {})

        try:
            return schema.parse_obj(normalised)
        except ValidationError as exc:
            raise DispatchError(f"Invalid payload for {event_type}: {exc}") from exc

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------

    def _detect_event_type(self, payload: Mapping[str, Any]) -> EventType:
        if "event_type" in payload:
            raw_type = payload["event_type"]
            if isinstance(raw_type, EventType):
                return raw_type
            return EventType(str(raw_type))

        body = payload.get("payload", {})
        if isinstance(body, MutableMapping):
            if body.get("edi_type") == "204":
                return EventType.EDI_TENDER_REQUEST
            if body.get("edi_type") == "214":
                return EventType.EDI_STATUS_UPDATE
        if payload.get("source") == EventSource.IOT_CHAINSENSE.value:
            if body.get("event_type") == "GEOFENCE_ENTER":
                return EventType.IOT_GEOFENCE_ENTER
            if body.get("event_type") == "GEOFENCE_EXIT":
                return EventType.IOT_GEOFENCE_EXIT
            return EventType.IOT_TELEMETRY

        raise DispatchError("event_type missing and could not be inferred")

    @staticmethod
    def _default_source_for(event_type: EventType) -> EventSource:
        if event_type in {
            EventType.IOT_TELEMETRY,
            EventType.IOT_GEOFENCE_ENTER,
            EventType.IOT_GEOFENCE_EXIT,
            EventType.IOT_ALERT_CRITICAL,
            EventType.IOT_ALERT_WARNING,
        }:
            return EventSource.IOT_CHAINSENSE
        if event_type in {EventType.EDI_TENDER_REQUEST, EventType.EDI_STATUS_UPDATE}:
            return EventSource.SEEBURGER_EDI
        if event_type in {
            EventType.TOKEN_CREATED,
            EventType.TOKEN_TRANSITION,
            EventType.TOKEN_PROOF_ATTACHED,
        }:
            return EventSource.TOKEN_ENGINE
        if event_type in {
            EventType.PROOF_COMPUTED,
            EventType.PROOF_VALIDATED,
        }:
            return EventSource.SXT_PROOF
        if event_type in {EventType.SETTLEMENT_INITIATED, EventType.SETTLEMENT_COMPLETE}:
            return EventSource.CHAINPAY_SETTLEMENT
        return EventSource.ALEX_GOVERNANCE


__all__ = ["EventDispatcher", "DispatchError"]
