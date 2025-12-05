"""Schemas for the ChainSense IoT health facade."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class IoTDeviceStatus(str, Enum):
    """Lifecycle/health state for a monitored IoT device."""

    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


class IoTDeviceHealth(BaseModel):
    """Represents the health snapshot for a single IoT device."""

    id: str = Field(..., description="Stable device identifier (truck, warehouse sensor, etc.)")
    name: str = Field(..., description="Human-friendly device label")
    status: IoTDeviceStatus = Field(..., description="Current health status derived from telemetry")
    last_heartbeat: datetime = Field(..., description="UTC timestamp of the latest heartbeat we ingested")
    risk_score: float = Field(..., ge=0, le=100, description="0-100 risk score (higher = riskier)")
    signal_confidence: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Optional signal strength/confidence for the reading",
    )


class IoTHealthResponse(BaseModel):
    """Envelope for IoT health listings consumed by ChainBoard panels."""

    devices: List[IoTDeviceHealth]


__all__ = [
    "IoTDeviceStatus",
    "IoTDeviceHealth",
    "IoTHealthResponse",
]
