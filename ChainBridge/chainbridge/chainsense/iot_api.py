"""ChainSense IoT ingestion API + service layer."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator

from chainbridge.events.schemas import EventSource, EventType, RoutingDecision
from chainbridge.runtime import event_pipeline
from chainbridge.runtime import startup as runtime_startup

from .consistency import ConsistencyEngine
from .geofence import (
    GeofenceDefinition,
    GeofenceEngine,
    GeofenceEvent,
    GeofenceEventType,
    GeofenceKind,
)
from .normalizer import DeviceState, RawTelemetry, TelemetryRecord, normalize_telemetry
from .oc_adapter import build_oc_payload

router = APIRouter(prefix="/chainsense/iot", tags=["ChainSense"])


class TelemetryIngestRequest(BaseModel):
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
    signature: str = Field(min_length=32)
    nonce: int = Field(ge=0)

    @validator("event_time", pre=True)
    def _parse_time(cls, value):
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)


class IngestionReceipt(BaseModel):
    ingest_id: str
    device_id: str
    shipment_id: str
    accepted: bool
    milestones_generated: int
    risk_flags: List[str]
    oc_payload: Dict[str, object]


class BulkIngestionResponse(BaseModel):
    receipts: List[IngestionReceipt]


class DeviceStatus(BaseModel):
    device_id: str
    last_event_time: Optional[datetime]
    last_known_location: Optional[Dict[str, float]]
    last_risk_flags: List[str] = Field(default_factory=list)


@dataclass
class DeviceProfile:
    device_id: str
    secret: str
    owner: str


class DeviceRegistry:
    """Holds registered IoT devices and validates signatures/nonces."""

    def __init__(self) -> None:
        self._devices: Dict[str, DeviceProfile] = {}
        self._nonces: Dict[str, int] = {}

    def register(self, profile: DeviceProfile) -> None:
        self._devices[profile.device_id] = profile

    def validate(self, payload: TelemetryIngestRequest) -> DeviceProfile:
        try:
            profile = self._devices[payload.device_id]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown device") from exc
        expected = _sign_payload(profile.secret, payload)
        if not hmac.compare_digest(expected, payload.signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
        last_nonce = self._nonces.get(payload.device_id, -1)
        if payload.nonce <= last_nonce:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Replay detected")
        self._nonces[payload.device_id] = payload.nonce
        return profile


class ChainIQPublisher:
    """Async publisher stub for Maggie's risk engine."""

    async def publish(self, payload: dict) -> None:  # pragma: no cover - simple async stub
        await asyncio.sleep(0)


class ChainSenseIngestionService:
    """Coordinates normalization, geofence detection, consistency checks, and router dispatch."""

    def __init__(
        self,
        *,
        device_registry: DeviceRegistry,
        geofence_engine: GeofenceEngine,
        consistency_engine: ConsistencyEngine,
        chainiq_publisher: ChainIQPublisher,
    ) -> None:
        self._device_registry = device_registry
        self._geofence_engine = geofence_engine
        self._consistency_engine = consistency_engine
        self._chainiq_publisher = chainiq_publisher
        self._device_states: Dict[str, DeviceState] = {}
        self._last_risk_flags: Dict[str, List[str]] = {}

    async def ingest(self, payload: TelemetryIngestRequest) -> IngestionReceipt:
        self._device_registry.validate(payload)
        raw = RawTelemetry(**payload.dict(exclude={"signature", "nonce"}))
        device_state = self._device_states.get(payload.device_id) or DeviceState(device_id=payload.device_id)
        record = normalize_telemetry(raw, device_state=device_state)
        geofence_events = self._geofence_engine.evaluate(record)
        risk_flags = self._consistency_engine.evaluate(record)

        runtime_context = await runtime_startup.ensure_runtime()
        before_mt_count = len(await runtime_context.router.get_shipment_tokens(payload.shipment_id, "MT-01"))

        routing_results = [await event_pipeline.process_event(_build_telemetry_event(record=record, shipment_id=payload.shipment_id))]

        for geofence_event in geofence_events:
            geofence_payload = _build_geofence_event(
                shipment_id=payload.shipment_id,
                event=geofence_event,
                record=record,
            )
            if geofence_payload:
                routing_results.append(await event_pipeline.process_event(geofence_payload))

        mt_tokens = await runtime_context.router.get_shipment_tokens(payload.shipment_id, "MT-01")
        tokens_snapshot = await runtime_context.router.get_shipment_tokens(payload.shipment_id)
        milestones_generated = max(0, len(mt_tokens) - before_mt_count)

        oc_payload = build_oc_payload(
            record,
            milestones=tokens_snapshot,
            geofence_events=geofence_events,
            risk_flags=risk_flags,
        )
        await self._chainiq_publisher.publish(
            {
                "shipment_id": payload.shipment_id,
                "device_id": payload.device_id,
                "normalized": record.dict(),
                "milestones": [token.metadata for token in mt_tokens],
                "risk_flags": [flag.code for flag in risk_flags],
            }
        )
        self._device_states[payload.device_id] = DeviceState(
            device_id=payload.device_id,
            last_event_time=record.event_time,
            last_latitude=record.latitude,
            last_longitude=record.longitude,
        )
        self._last_risk_flags[payload.device_id] = [flag.code for flag in risk_flags]
        success_states = {
            RoutingDecision.PROCESSED,
            RoutingDecision.DEDUPED,
            RoutingDecision.QUEUED,
        }

        return IngestionReceipt(
            ingest_id=record.ingest_id,
            device_id=payload.device_id,
            shipment_id=payload.shipment_id,
            accepted=all(result.decision in success_states for result in routing_results),
            milestones_generated=milestones_generated,
            risk_flags=[flag.code for flag in risk_flags],
            oc_payload=oc_payload,
        )

    async def ingest_bulk(self, payloads: List[TelemetryIngestRequest]) -> List[IngestionReceipt]:
        receipts = []
        for payload in payloads:
            receipts.append(await self.ingest(payload))
        return receipts

    def get_status(self, device_id: str) -> DeviceStatus:
        state = self._device_states.get(device_id)
        if not state:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not seen")
        return DeviceStatus(
            device_id=device_id,
            last_event_time=state.last_event_time,
            last_known_location=(
                {
                    "lat": state.last_latitude,
                    "lng": state.last_longitude,
                }
                if state.last_latitude is not None
                else None
            ),
            last_risk_flags=self._last_risk_flags.get(device_id, []),
        )


def _build_default_service() -> ChainSenseIngestionService:
    device_registry = DeviceRegistry()
    device_registry.register(DeviceProfile(device_id="DEV-001", secret="dev-secret", owner="LAB"))

    geofence_engine = GeofenceEngine(
        definitions=[
            GeofenceDefinition(
                geofence_id="SHIPPER-DOCK",
                name="Origin Dock",
                kind=GeofenceKind.SHIPPER_PICKUP,
                polygons=[[(33.0, -96.0), (33.0, -96.01), (33.01, -96.01), (33.01, -96.0)]],
            )
        ]
    )
    consistency_engine = ConsistencyEngine()
    return ChainSenseIngestionService(
        device_registry=device_registry,
        geofence_engine=geofence_engine,
        consistency_engine=consistency_engine,
        chainiq_publisher=ChainIQPublisher(),
    )


_service = _build_default_service()


def get_service() -> ChainSenseIngestionService:
    return _service


@router.post("/telemetry", response_model=IngestionReceipt, status_code=status.HTTP_202_ACCEPTED)
async def ingest_telemetry(
    payload: TelemetryIngestRequest,
    service: ChainSenseIngestionService = Depends(get_service),
) -> IngestionReceipt:
    return await service.ingest(payload)


@router.post("/bulk", response_model=BulkIngestionResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_bulk(
    payload: List[TelemetryIngestRequest],
    service: ChainSenseIngestionService = Depends(get_service),
) -> BulkIngestionResponse:
    receipts = await service.ingest_bulk(payload)
    return BulkIngestionResponse(receipts=receipts)


@router.get("/device/{device_id}/status", response_model=DeviceStatus)
async def device_status(
    device_id: str,
    service: ChainSenseIngestionService = Depends(get_service),
) -> DeviceStatus:
    return service.get_status(device_id)


def _build_telemetry_event(*, record: TelemetryRecord, shipment_id: str) -> Dict[str, object]:
    return {
        "event_type": EventType.IOT_TELEMETRY.value,
        "source": EventSource.IOT_CHAINSENSE.value,
        "timestamp": record.event_time.isoformat(),
        "parent_shipment_id": shipment_id,
        "actor_id": record.device_id,
        "device_id": record.device_id,
        "payload": {
            "latitude": record.latitude,
            "longitude": record.longitude,
            "speed_mph": record.speed_mph,
            "speed_mps": record.speed_mps,
            "heading": record.heading,
            "engine_state": record.engine_state,
            "ignition": record.ignition,
            "idle_time_seconds": record.idle_time_seconds,
            "battery_voltage": record.battery_voltage,
            "telemetry_snapshot": record.raw_metadata,
        },
    }


def _build_geofence_event(
    *,
    shipment_id: str,
    event: GeofenceEvent,
    record: TelemetryRecord,
) -> Optional[Dict[str, object]]:
    event_type = _map_geofence_event(event.event_type)
    if not event_type:
        return None
    geofence_type = _map_geofence_kind(event.kind)
    action = "ENTER" if event_type == EventType.IOT_GEOFENCE_ENTER else "EXIT"
    return {
        "event_type": event_type.value,
        "source": EventSource.IOT_CHAINSENSE.value,
        "timestamp": event.timestamp.isoformat(),
        "parent_shipment_id": shipment_id,
        "actor_id": record.device_id,
        "device_id": record.device_id,
        "payload": {
            "geofence_id": event.geofence_id,
            "geofence_name": event.geofence_id,
            "geofence_type": geofence_type,
            "action": action,
            "location": {"lat": record.latitude, "lon": record.longitude},
        },
    }


def _map_geofence_event(event_type: GeofenceEventType) -> Optional[EventType]:
    if event_type in {GeofenceEventType.ENTER, GeofenceEventType.TERMINAL_ARRIVED, GeofenceEventType.DOCKED}:
        return EventType.IOT_GEOFENCE_ENTER
    if event_type == GeofenceEventType.EXIT:
        return EventType.IOT_GEOFENCE_EXIT
    return None


def _map_geofence_kind(kind: GeofenceKind) -> str:
    mapping = {
        GeofenceKind.SHIPPER_PICKUP: "SHIPPER_PICKUP",
        GeofenceKind.CONSIGNEE: "CONSIGNEE",
        GeofenceKind.TERMINAL: "TERMINAL",
        GeofenceKind.DEPOT: "CUSTOM",
    }
    return mapping.get(kind, "CUSTOM")


def _sign_payload(secret: str, payload: TelemetryIngestRequest) -> str:
    body = f"{payload.device_id}:{payload.shipment_id}:{payload.nonce}:{payload.event_time.isoformat()}"
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


__all__ = [
    "router",
    "ChainSenseIngestionService",
    "DeviceRegistry",
    "TelemetryIngestRequest",
    "IngestionReceipt",
]
