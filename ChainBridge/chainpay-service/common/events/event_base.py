from pydantic import BaseModel, Field
from typing import Any, Dict
from datetime import datetime

class EventBase(BaseModel):
    canonical_shipment_id: str = Field(..., description="Canonical shipment ID")
    event_type: str = Field(..., description="Type of event (enum)")
    timestamp: datetime = Field(..., description="Event timestamp (UTC)")
    source: str = Field(..., description="Source system or agent")
    payload: Dict[str, Any] = Field(..., description="Event payload")
    trace_id: str = Field(..., description="Event trace ID for observability")
