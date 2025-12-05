"""Normalization utilities for ChainSense telemetry."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, validator


class TelemetryNormalizationError(ValueError):
    """Raised when telemetry payloads fail validation."""


class RawTelemetry(BaseModel):
    """Inbound telemetry payload prior to normalization."""

    device_id: str = Field(min_length=3)
    shipment_id: str = Field(min_length=3)
    event_time: datetime
    latitude: float
    longitude: float
    speed_mph: float = Field(ge=0)
    heading: Optional[float] = Field(default=None)
    engine_state: str
    idle_time_seconds: int = Field(default=0, ge=0)
    ignition: bool
    battery_voltage: Optional[float] = Field(default=None, ge=0)
    raw_metadata: Dict[str, object] = Field(default_factory=dict)

    @validator("event_time", pre=True)
    def _coerce_datetime(cls, value):
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)


class TelemetryRecord(RawTelemetry):
    """Normalized telemetry information consumed by downstream services."""

    ingest_id: str
    normalized_at: datetime
    position_accuracy_m: float
    speed_mps: float
    heading: float = Field(default=0)
    engine_state: str

    class Config:
        frozen = True


class DeviceState(BaseModel):
    """Mutable device metadata tracked across events."""

    device_id: str
    last_event_time: Optional[datetime] = None
    last_latitude: Optional[float] = None
    last_longitude: Optional[float] = None


def normalize_telemetry(
    payload: RawTelemetry,
    *,
    device_state: Optional[DeviceState] = None,
    max_speed_mph: float = 120.0,
) -> TelemetryRecord:
    """Normalize and validate telemetry payloads."""

    if not -90 <= payload.latitude <= 90:
        raise TelemetryNormalizationError("Latitude out of range")
    if not -180 <= payload.longitude <= 180:
        raise TelemetryNormalizationError("Longitude out of range")
    if payload.speed_mph > max_speed_mph:
        raise TelemetryNormalizationError("Speed exceeds sanity threshold")
    if payload.heading is not None and not 0 <= payload.heading <= 360:
        raise TelemetryNormalizationError("Heading must be between 0 and 360 degrees")

    event_time = payload.event_time.astimezone(timezone.utc)
    if device_state and device_state.last_event_time:
        if event_time <= device_state.last_event_time:
            raise TelemetryNormalizationError("Out-of-order telemetry timestamp detected")
        # time delta sanity (avoid teleporter jumps)
        _enforce_motion_sanity(payload, device_state)

    heading = payload.heading if payload.heading is not None else 0.0
    payload_dict = payload.dict()
    payload_dict.pop('heading', None)
    normalized = TelemetryRecord(
        **payload_dict,
        ingest_id=str(uuid4()),
        normalized_at=datetime.now(timezone.utc),
        position_accuracy_m=_estimate_accuracy(payload),
        speed_mps=_mph_to_mps(payload.speed_mph),
        heading=float(round(heading, 3)),
    )
    return normalized


def _estimate_accuracy(payload: RawTelemetry) -> float:
    accuracy = payload.raw_metadata.get("accuracy_m") if payload.raw_metadata else None
    if isinstance(accuracy, (int, float)) and accuracy > 0:
        return float(accuracy)
    return 10.0  # default 10m precision buffer


def _mph_to_mps(value: float) -> float:
    return round(value * 0.44704, 3)


def _enforce_motion_sanity(payload: RawTelemetry, device_state: DeviceState) -> None:
    previous_time = device_state.last_event_time
    if previous_time is None or device_state.last_latitude is None:
        return
    time_delta = (payload.event_time.astimezone(timezone.utc) - previous_time).total_seconds()
    if time_delta <= 0:
        raise TelemetryNormalizationError("Non-positive time delta")
    distance = _haversine(
        device_state.last_latitude,
        device_state.last_longitude or 0,
        payload.latitude,
        payload.longitude,
    )
    if distance / time_delta > 120:  # > 432 km/h impossible for trucks
        raise TelemetryNormalizationError("Teleportation anomaly detected")


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000  # meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


__all__ = [
    "RawTelemetry",
    "TelemetryRecord",
    "TelemetryNormalizationError",
    "DeviceState",
    "normalize_telemetry",
]
