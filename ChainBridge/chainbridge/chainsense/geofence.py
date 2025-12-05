"""Geofence detection for ChainSense."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Iterable, List, Sequence, Tuple

from .normalizer import TelemetryRecord


class GeofenceEventType(str, Enum):
    ENTER = "GEOFENCE_ENTER"
    EXIT = "GEOFENCE_EXIT"
    DOCKED = "DOCKED"
    TERMINAL_ARRIVED = "TERMINAL_ARRIVED"


class GeofenceKind(str, Enum):
    SHIPPER_PICKUP = "shipper_pickup"
    TERMINAL = "terminal"
    CONSIGNEE = "consignee"
    DEPOT = "depot"


@dataclass
class GeofenceDefinition:
    geofence_id: str
    name: str
    kind: GeofenceKind
    polygons: Sequence[Sequence[Tuple[float, float]]]
    buffer_m: float = 10.0


@dataclass
class GeofenceEvent:
    geofence_id: str
    kind: GeofenceKind
    event_type: GeofenceEventType
    timestamp: datetime


class GeofenceEngine:
    """Evaluates device positions against registered geofences."""

    def __init__(self, definitions: Iterable[GeofenceDefinition] | None = None):
        self._definitions: Dict[str, GeofenceDefinition] = {}
        self._device_state: Dict[str, set[str]] = {}
        if definitions:
            for definition in definitions:
                self.register(definition)

    def register(self, definition: GeofenceDefinition) -> None:
        self._definitions[definition.geofence_id] = definition

    def evaluate(self, record: TelemetryRecord) -> List[GeofenceEvent]:
        results: List[GeofenceEvent] = []
        inside = self._device_state.setdefault(record.device_id, set())
        currently_inside: set[str] = set()

        for definition in self._definitions.values():
            if _contains(definition, record.latitude, record.longitude):
                currently_inside.add(definition.geofence_id)
                if definition.geofence_id not in inside:
                    results.append(
                        GeofenceEvent(
                            geofence_id=definition.geofence_id,
                            kind=definition.kind,
                            event_type=GeofenceEventType.ENTER,
                            timestamp=record.event_time,
                        )
                    )
                    if definition.kind == GeofenceKind.TERMINAL:
                        results.append(
                            GeofenceEvent(
                                geofence_id=definition.geofence_id,
                                kind=definition.kind,
                                event_type=GeofenceEventType.TERMINAL_ARRIVED,
                                timestamp=record.event_time,
                            )
                        )
                    if _is_docked(record):
                        results.append(
                            GeofenceEvent(
                                geofence_id=definition.geofence_id,
                                kind=definition.kind,
                                event_type=GeofenceEventType.DOCKED,
                                timestamp=record.event_time,
                            )
                        )
            else:
                if definition.geofence_id in inside:
                    results.append(
                        GeofenceEvent(
                            geofence_id=definition.geofence_id,
                            kind=definition.kind,
                            event_type=GeofenceEventType.EXIT,
                            timestamp=record.event_time,
                        )
                    )

        self._device_state[record.device_id] = currently_inside
        return results


def _contains(definition: GeofenceDefinition, lat: float, lon: float) -> bool:
    for polygon in definition.polygons:
        if _point_in_polygon(lat, lon, polygon, definition.buffer_m):
            return True
    return False


def _point_in_polygon(lat: float, lon: float, polygon: Sequence[Tuple[float, float]], buffer_m: float) -> bool:
    adjusted_polygon = _apply_buffer(polygon, buffer_m)
    inside = False
    j = len(adjusted_polygon) - 1
    for i, (lat_i, lon_i) in enumerate(adjusted_polygon):
        lat_j, lon_j = adjusted_polygon[j]
        if ((lon_i > lon) != (lon_j > lon)) and (lat < (lat_j - lat_i) * (lon - lon_i) / (lon_j - lon_i + 1e-9) + lat_i):
            inside = not inside
        j = i
    return inside


def _apply_buffer(polygon: Sequence[Tuple[float, float]], buffer_m: float) -> List[Tuple[float, float]]:
    # Rough conversion: 1 degree latitude ≈ 111_000 meters
    delta = buffer_m / 111_000
    return [(lat + _sign(lat) * delta, lon + _sign(lon) * delta) for lat, lon in polygon]


def _sign(value: float) -> float:
    if value == 0:
        return 1.0
    return 1.0 if value > 0 else -1.0


def _is_docked(record: TelemetryRecord) -> bool:
    return record.speed_mps < 0.5 and record.idle_time_seconds >= 300 and not record.ignition


__all__ = [
    "GeofenceDefinition",
    "GeofenceEngine",
    "GeofenceEvent",
    "GeofenceEventType",
    "GeofenceKind",
]
