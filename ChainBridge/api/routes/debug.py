"""Debug routes for inspecting backend state."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.chainfreight import ShipmentEvent

router = APIRouter(prefix="/debug", tags=["debug"])


class ShipmentEventResponse(BaseModel):
    event_id: str
    shipment_id: str
    shipment_leg_id: Optional[str] = None
    actor: Optional[str] = None
    source_service: Optional[str] = None
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    payload: Optional[dict] = None


@router.get("/shipments/{shipment_id}/events", response_model=List[ShipmentEventResponse])
def get_shipment_events(
    shipment_id: str,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[ShipmentEventResponse]:
    """Return recorded shipment events ordered by occurrence."""
    events = (
        db.query(ShipmentEvent)
        .filter(ShipmentEvent.shipment_id == shipment_id)
        .order_by(ShipmentEvent.occurred_at.asc(), ShipmentEvent.recorded_at.asc())
        .limit(limit)
        .all()
    )
    return [
        ShipmentEventResponse(
            event_id=event.event_id,
            shipment_id=event.shipment_id,
            shipment_leg_id=event.shipment_leg_id,
            actor=event.actor,
            source_service=event.source_service,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            recorded_at=event.recorded_at,
            payload=event.payload,
        )
        for event in events
    ]
