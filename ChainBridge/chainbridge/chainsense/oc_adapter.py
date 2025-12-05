"""Adapters for Sonny's OC interface."""

from __future__ import annotations

from typing import Iterable

from chainbridge.tokens.base_token import BaseToken

from .consistency import ConsistencyFlag
from .geofence import GeofenceEvent
from .normalizer import TelemetryRecord


def build_oc_payload(
    record: TelemetryRecord,
    *,
    milestones: Iterable[BaseToken],
    geofence_events: Iterable[GeofenceEvent],
    risk_flags: Iterable[ConsistencyFlag],
) -> dict:
    milestone_list = [token for token in milestones if token.token_type == "MT-01"]
    risk_list = list(risk_flags)
    geofence_list = list(geofence_events)
    return {
        "timestamp": record.event_time.isoformat(),
        "location": {"lat": record.latitude, "lng": record.longitude},
        "speed_mph": record.speed_mph,
        "heading": record.heading,
        "geofence_status": [event.event_type for event in geofence_list],
        "milestones": [token.metadata.get("milestone_type") for token in milestone_list],
        "risk_flags": [flag.code for flag in risk_list],
        "device_health": {
            "battery_voltage": record.battery_voltage,
            "ignition": record.ignition,
            "engine_state": record.engine_state,
        },
    }


__all__ = ["build_oc_payload"]
