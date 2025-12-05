"""IoT health facade endpoints for ChainIQ."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter

from .schemas_iot import IoTDeviceHealth, IoTDeviceStatus, IoTHealthResponse

router = APIRouter(prefix="/iot", tags=["IoT Health"])


def _build_mock_devices(now: datetime) -> List[IoTDeviceHealth]:
    """Create deterministic mock IoT health data until real telemetry is wired."""

    return [
        IoTDeviceHealth(
            id="truck-001",
            name="Reefer Truck 001",
            status=IoTDeviceStatus.ONLINE,
            last_heartbeat=now - timedelta(minutes=2),
            risk_score=12.5,
            signal_confidence=0.92,
        ),
        IoTDeviceHealth(
            id="warehouse-sensor-042",
            name="Warehouse Sensor 42",
            status=IoTDeviceStatus.DEGRADED,
            last_heartbeat=now - timedelta(minutes=9),
            risk_score=41.0,
            signal_confidence=0.65,
        ),
        IoTDeviceHealth(
            id="truck-015",
            name="Trailer Sensor 15",
            status=IoTDeviceStatus.OFFLINE,
            last_heartbeat=now - timedelta(minutes=27),
            risk_score=73.4,
            signal_confidence=0.18,
        ),
    ]


@router.get("/health", response_model=IoTHealthResponse, summary="List IoT device health snapshots")
async def get_iot_health() -> IoTHealthResponse:
    """Return mock IoT device health data for the ChainSense vertical slice."""

    # TODO(GID-01): Source this from ChainSense/ChainIQ signals once telemetry ingestion lands.
    now = datetime.now(timezone.utc)
    devices = _build_mock_devices(now)
    return IoTHealthResponse(devices=devices)
