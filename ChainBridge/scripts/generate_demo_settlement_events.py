"""Generate demo settlement events for PaymentIntents.

Usage:
    python -m scripts.generate_demo_settlement_events [--rewrite]

Idempotent by default: skips intents that already have settlement events unless --rewrite is provided.
"""

import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from api.database import SessionLocal, init_db
from api.models.chainpay import PaymentIntent, SettlementEvent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

HAPPY_PATH = [
    ("CREATED", "PENDING", 0),
    ("AUTHORIZED", "SUCCESS", 5),
    ("CAPTURED", "SUCCESS", 15),
]
BLOCKED_PATH = [
    ("CREATED", "PENDING", 0),
    ("AUTHORIZED", "FAILED", 5),
    ("FAILED", "FAILED", 15),
]


def _clear_events(session: Session, intent_id: str) -> None:
    session.query(SettlementEvent).filter(SettlementEvent.payment_intent_id == intent_id).delete()


def _build_events(intent: PaymentIntent, path: List[tuple]) -> List[SettlementEvent]:
    base_time = intent.created_at or datetime.utcnow()
    events: List[SettlementEvent] = []
    for event_type, status, minutes_offset in path:
        events.append(
            SettlementEvent(
                payment_intent_id=intent.id,
                event_type=event_type,
                status=status,
                amount=float(intent.amount),
                currency=intent.currency,
                occurred_at=base_time + timedelta(minutes=minutes_offset),
                metadata={"risk_level": intent.risk_level},
            )
        )
    return events


def generate(
    rewrite: bool = False,
    session: Optional[SessionLocal] = None,
    skip_init: bool = False,
) -> None:
    managed_session = session is None
    if managed_session:
        if not skip_init:
            init_db()
        session = SessionLocal()
    try:
        intents = session.query(PaymentIntent).all()
        for intent in intents:
            existing = session.query(SettlementEvent).filter(SettlementEvent.payment_intent_id == intent.id).count()
            if existing and not rewrite:
                continue
            if existing:
                _clear_events(session, intent.id)
            is_blocked = (intent.risk_level or "").upper() in {"HIGH", "CRITICAL"}
            path = BLOCKED_PATH if is_blocked else HAPPY_PATH
            events = _build_events(intent, path)
            session.add_all(events)
            session.commit()
            logger.info(
                "chainpay_demo_settlement_generated",
                extra={
                    "payment_intent_id": intent.id,
                    "path": "BLOCKED" if is_blocked else "HAPPY",
                },
            )
    finally:
        if managed_session and session is not None:
            session.close()


def main():
    parser = argparse.ArgumentParser(description="Generate demo settlement events")
    parser.add_argument("--rewrite", action="store_true", help="Rewrite existing events")
    args = parser.parse_args()
    generate(rewrite=args.rewrite)


if __name__ == "__main__":
    main()
