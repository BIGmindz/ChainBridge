"""Seeburger EDI ingestion helpers feeding the GlobalEventRouter."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator

from chainbridge.events.schemas import EventSource, EventType
from chainbridge.runtime import event_pipeline


class EDI214Request(BaseModel):
    shipment_id: str = Field(min_length=3)
    actor_id: str = Field(min_length=3)
    status_code: str = Field(min_length=2, max_length=3)
    status_reason: Optional[str] = None
    location_code: Optional[str] = None
    location_name: Optional[str] = None
    appointment_time: Optional[datetime] = None
    actual_time: Optional[datetime] = None
    equipment_number: Optional[str] = None
    driver_name: Optional[str] = None
    raw_segments: List[str] = Field(default_factory=list)

    @validator("appointment_time", "actual_time", pre=True)
    def _parse_times(cls, value):
        if value is None or isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)


class EDI204Request(BaseModel):
    shipment_id: str = Field(min_length=3)
    actor_id: str = Field(min_length=3)
    shipper_id: str
    carrier_id: str
    origin: Dict[str, str]
    destination: Dict[str, str]
    pickup_date: datetime
    delivery_date: datetime
    weight_lbs: Optional[float] = None
    equipment_type: Optional[str] = None
    rate_amount: Optional[float] = None
    rate_currency: str = "USD"

    @validator("pickup_date", "delivery_date", pre=True)
    def _parse_date(cls, value):
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)


class SeeburgerIngestionService:
    """Maps EDI payloads into canonical events."""

    async def ingest_status(self, payload: EDI214Request):
        event = {
            "event_type": EventType.EDI_STATUS_UPDATE.value,
            "source": EventSource.SEEBURGER_EDI.value,
            "timestamp": (payload.actual_time or datetime.utcnow()).isoformat(),
            "parent_shipment_id": payload.shipment_id,
            "actor_id": payload.actor_id,
            "payload": {
                "edi_type": "214",
                "status_code": payload.status_code,
                "status_reason": payload.status_reason,
                "location_code": payload.location_code,
                "location_name": payload.location_name,
                "appointment_time": payload.appointment_time.isoformat() if payload.appointment_time else None,
                "actual_time": payload.actual_time.isoformat() if payload.actual_time else None,
                "equipment_number": payload.equipment_number,
                "driver_name": payload.driver_name,
                "raw_segments": payload.raw_segments,
                "edi_version": "X12_4010",
                "interchange_control_number": payload.shipment_id,
                "sender_id": "SEEBURGER",
                "receiver_id": "CHAINBRIDGE",
            },
        }
        return await event_pipeline.process_event(event)

    async def ingest_tender(self, payload: EDI204Request):
        event = {
            "event_type": EventType.EDI_TENDER_REQUEST.value,
            "source": EventSource.SEEBURGER_EDI.value,
            "timestamp": payload.pickup_date.isoformat(),
            "parent_shipment_id": payload.shipment_id,
            "actor_id": payload.actor_id,
            "payload": {
                "edi_type": "204",
                "shipper_id": payload.shipper_id,
                "carrier_id": payload.carrier_id,
                "origin": payload.origin,
                "destination": payload.destination,
                "pickup_date": payload.pickup_date.isoformat(),
                "delivery_date": payload.delivery_date.isoformat(),
                "weight_lbs": payload.weight_lbs,
                "equipment_type": payload.equipment_type,
                "rate_amount": payload.rate_amount,
                "rate_currency": payload.rate_currency,
                "edi_version": "X12_4010",
                "interchange_control_number": payload.shipment_id,
                "sender_id": "SEEBURGER",
                "receiver_id": "CHAINBRIDGE",
            },
        }
        return await event_pipeline.process_event(event)

    async def ingest_batch(self, payloads: List[BaseModel]):
        results = []
        for payload in payloads:
            if isinstance(payload, EDI214Request):
                results.append(await self.ingest_status(payload))
            elif isinstance(payload, EDI204Request):
                results.append(await self.ingest_tender(payload))
            else:
                raise ValueError("Unsupported payload type")
        return results


__all__ = ["SeeburgerIngestionService", "EDI214Request", "EDI204Request"]
