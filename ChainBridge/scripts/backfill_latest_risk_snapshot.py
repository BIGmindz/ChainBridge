"""Backfill latest_risk_snapshot_id for payment intents."""
from __future__ import annotations

import logging

from api.database import SessionLocal, init_db
from api.models.chainpay import PaymentIntent
from api.services.payment_intents import get_latest_risk_snapshot

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def backfill() -> None:
    init_db()
    session = SessionLocal()
    try:
        intents = session.query(PaymentIntent).all()
        updated = 0
        for intent in intents:
            snapshot = get_latest_risk_snapshot(session, intent.shipment_id)
            if snapshot and intent.latest_risk_snapshot_id != snapshot.id:
                intent.latest_risk_snapshot_id = snapshot.id
                session.add(intent)
                updated += 1
        session.commit()
        logger.info("backfill_complete", extra={"updated": updated})
    finally:
        session.close()


if __name__ == "__main__":
    backfill()
