"""Universal ingestion pipeline entrypoint (Refinery)."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.core.config import settings
from api.database import get_db
from api.events.bus import EventType, event_bus
from app.schemas.normalized_logistics import StandardShipment
from app.services.data.sxt_client import archive_shipment_plan
from app.services.ingest.factory import get_ingestor
from app.services.ingest.repository import persist_standard_shipment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["refinery"])
get_db_session = get_db


def _publish_redis_event(channel: str, payload: dict) -> None:
    """Best-effort fan-out to Redis if available."""
    try:
        import redis  # type: ignore

        client = redis.from_url(settings.REDIS_URL)
        client.publish(channel, json.dumps(payload, default=str))
    except Exception:
        logger.debug("ingest.redis.publish_skipped", extra={"channel": channel})


@router.post(
    "/{source}",
    response_model=StandardShipment,
    status_code=status.HTTP_200_OK,
    summary="Ingest raw payload and emit Golden Record",
)
async def ingest_payload(source: str, payload: dict[str, Any], db: Session = Depends(get_db_session)) -> StandardShipment:
    try:
        ingestor = get_ingestor(source)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="unknown_ingestion_source",
        ) from exc

    shipment = ingestor.parse(payload)
    persist_standard_shipment(shipment, payload, session=db)
    sxt_ack = archive_shipment_plan(shipment)

    event_payload = {
        "shipment": shipment.model_dump(mode="json"),
        "archive_status": sxt_ack.get("status"),
        "source": source,
    }
    event_bus.publish(
        EventType.SHIPMENT_INGESTED,
        event_payload,
        correlation_id=shipment.shipment_id,
        actor="api:ingest",
    )
    _publish_redis_event(EventType.SHIPMENT_INGESTED.value, event_payload)
    logger.info(
        "ingest.refinery.completed",
        extra={
            "source": source,
            "shipment_id": shipment.shipment_id,
            "external_id": shipment.external_id,
            "archive_status": sxt_ack.get("status"),
        },
    )
    return shipment
