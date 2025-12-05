from .event_base import EventBase
from .event_types import EventType
from typing import Dict, Any
from pydantic import Field

class PaymentEvent(EventBase):
    event_type: EventType = Field(default=EventType.PAYMENT_TRIGGER)
    payload: Dict[str, Any] = Field(..., description="Payment event details")
