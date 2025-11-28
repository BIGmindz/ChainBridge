"""Demo/God Mode endpoints for rapid state changes."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models.chaindocs import Shipment
from app.models.marketplace import Listing, Bid
from app.worker.functions import liquidate_asset_task

router = APIRouter(prefix="/demo", tags=["demo"])


def _session() -> Session:
    return SessionLocal()


@router.post("/reset")
def reset_state() -> dict:
    db = _session()
    try:
        db.query(Bid).delete()
        db.query(Listing).delete()
        db.query(Shipment).delete()
        db.commit()
    finally:
        db.close()
    return {"status": "reset", "scenarios": ["happy_path", "edge_case", "disaster"]}


@router.post("/warp-time")
def warp_time(minutes: int) -> dict:
    db = _session()
    try:
        listings = db.query(Listing).filter(Listing.status == "ACTIVE").all()
        for lst in listings:
            lst.start_time = (lst.start_time or lst.created_at or datetime.utcnow()) - timedelta(minutes=minutes)
            db.add(lst)
        db.commit()
    finally:
        db.close()
    return {"status": "warped", "minutes": minutes}


@router.post("/trigger-breach/{shipment_id}")
async def trigger_breach(shipment_id: str) -> dict:
    await liquidate_asset_task({"payload": {"shipment_id": shipment_id}})
    return {"status": "breach_triggered", "shipment_id": shipment_id}
