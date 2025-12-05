from .event_base import EventBase
from .event_types import EventType
from typing import Dict, Any
from pydantic import Field

class RiskEvent(EventBase):
    event_type: EventType = Field(default=EventType.RISK_OK)
    payload: Dict[str, Any] = Field(..., description="Risk event details")
