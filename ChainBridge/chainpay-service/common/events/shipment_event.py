from .event_base import EventBase
from .event_types import EventType
from typing import Dict, Any
from pydantic import Field

class ShipmentEvent(EventBase):
    event_type: EventType = Field(default=EventType.SHIPMENT_UPDATE)
    payload: Dict[str, Any] = Field(..., description="Shipment event details")
