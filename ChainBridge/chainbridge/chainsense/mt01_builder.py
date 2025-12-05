"""MT-01 token generation from IoT events."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from chainbridge.tokens.mt01 import MT01Token

from .geofence import GeofenceEvent, GeofenceEventType, GeofenceKind
from .normalizer import TelemetryRecord


class MilestoneType(str, Enum):
    IN_TRANSIT = "IN_TRANSIT"
    TERMINAL_ARRIVED = "TERMINAL_ARRIVED"
    TERMINAL_DEPARTED = "TERMINAL_DEPARTED"
    DELIVERED = "DELIVERED"


@dataclass
class MT01Context:
    st01_id: str


class MT01Builder:
    """Derives milestone tokens from normalized telemetry signals."""

    def build(
        self,
        context: MT01Context,
        record: TelemetryRecord,
        geofence_events: List[GeofenceEvent],
    ) -> List[MT01Token]:
        tokens: List[MT01Token] = []
        milestone = self._determine_milestone(record, geofence_events)
        if milestone:
            tokens.append(self._to_token(context, record, milestone))
        return tokens

    def _determine_milestone(self, record: TelemetryRecord, geofence_events: List[GeofenceEvent]) -> Optional[MilestoneType]:
        for event in geofence_events:
            if (
                event.event_type == GeofenceEventType.EXIT
                and event.kind == GeofenceKind.SHIPPER_PICKUP
                and record.speed_mps >= 0.9
                and record.engine_state.lower() == "on"
            ):
                return MilestoneType.IN_TRANSIT
            if event.event_type == GeofenceEventType.TERMINAL_ARRIVED:
                return MilestoneType.TERMINAL_ARRIVED
            if event.event_type == GeofenceEventType.EXIT and event.kind == GeofenceKind.TERMINAL and record.speed_mps >= 0.9:
                return MilestoneType.TERMINAL_DEPARTED
            if (
                event.event_type == GeofenceEventType.ENTER
                and event.kind == GeofenceKind.CONSIGNEE
                and not record.ignition
                and record.idle_time_seconds >= 300
            ):
                return MilestoneType.DELIVERED
        return None

    def _to_token(
        self,
        context: MT01Context,
        record: TelemetryRecord,
        milestone: MilestoneType,
    ) -> MT01Token:
        metadata = {
            "milestone_type": milestone.value,
            "timestamp": record.event_time.isoformat(),
            "location": {"lat": record.latitude, "lon": record.longitude},
            "telemetry_snapshot": {
                "speed_mph": record.speed_mph,
                "speed_mps": record.speed_mps,
                "heading": record.heading,
                "engine_state": record.engine_state,
                "idle_time_seconds": record.idle_time_seconds,
                "battery_voltage": record.battery_voltage,
            },
        }
        relations = {
            "st01_id": context.st01_id,
            "iot_event_id": record.ingest_id,
        }
        return MT01Token(
            parent_shipment_id=context.st01_id,
            metadata=metadata,
            relations=relations,
        )


__all__ = ["MT01Builder", "MT01Context", "MilestoneType"]
