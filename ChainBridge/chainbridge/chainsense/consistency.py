"""Multi-device consistency + anomaly detection."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List

from .normalizer import TelemetryRecord


class ConsistencySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ConsistencyFlag:
    code: str
    description: str
    severity: ConsistencySeverity
    timestamp: datetime
    device_id: str


class ConsistencyEngine:
    """Tracks per-device telemetry to flag anomalies."""

    def __init__(self):
        self._state: Dict[str, TelemetryRecord] = {}

    def evaluate(self, record: TelemetryRecord) -> List[ConsistencyFlag]:
        flags: List[ConsistencyFlag] = []
        last = self._state.get(record.device_id)
        if last:
            if record.shipment_id != last.shipment_id:
                flags.append(
                    ConsistencyFlag(
                        code="DEVICE_REBOUND",
                        description="Device switched shipments without release",
                        severity=ConsistencySeverity.WARNING,
                        timestamp=record.event_time,
                        device_id=record.device_id,
                    )
                )
            if record.event_time == last.event_time:
                flags.append(
                    ConsistencyFlag(
                        code="TIMESTAMP_DUPLICATE",
                        description="Duplicate timestamps detected",
                        severity=ConsistencySeverity.WARNING,
                        timestamp=record.event_time,
                        device_id=record.device_id,
                    )
                )
            distance = _haversine(
                last.latitude,
                last.longitude,
                record.latitude,
                record.longitude,
            )
            time_delta = (record.event_time - last.event_time).total_seconds()
            if time_delta > 0 and distance / time_delta > 90:
                flags.append(
                    ConsistencyFlag(
                        code="IMPOSSIBLE_SPEED",
                        description="Movement exceeds realistic velocity",
                        severity=ConsistencySeverity.CRITICAL,
                        timestamp=record.event_time,
                        device_id=record.device_id,
                    )
                )
            if record.speed_mps == 0 and distance > 50:
                flags.append(
                    ConsistencyFlag(
                        code="DRIFT_WITHOUT_SPEED",
                        description="Device location jumped while reporting 0 speed",
                        severity=ConsistencySeverity.WARNING,
                        timestamp=record.event_time,
                        device_id=record.device_id,
                    )
                )
        self._state[record.device_id] = record
        return flags


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


__all__ = [
    "ConsistencyEngine",
    "ConsistencyFlag",
    "ConsistencySeverity",
]
