"""ARQ worker hooks for Dutch auction settlements."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session, selectinload

from api.database import SessionLocal
from api.eventbus.dispatcher import publish
from app.models.marketplace import BuyIntent, SettlementRecord
from app.schemas.marketplace import BuyIntentStatus
from app.services.marketplace.settlement_client import (
    SettlementIntentData,
    get_web3_client,
)
from app.core.metrics import increment_counter
from app.core.config import settings

# Ensure an event loop exists for synchronous test runners invoking async tasks.
import asyncio
try:  # pragma: no cover - defensive compatibility
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

logger = logging.getLogger(__name__)

EVENT_SETTLEMENT_CONFIRMED = "MARKETPLACE_SETTLEMENT_CONFIRMED"
EVENT_SETTLEMENT_COMPLETE = "SETTLEMENT_COMPLETE"
CHAIN_SETTLEMENT_CHANNEL = "chainbridge.settlements"
EVENT_SETTLEMENT_COMPLETE = "SETTLEMENT_COMPLETE"


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def enqueue_dutch_settlement(redis: Any, intent_id: str) -> str:
    """Enqueue settlement execution."""
    job = await redis.enqueue_job("execute_dutch_settlement", {"intent_id": intent_id})
    return str(job)


async def execute_dutch_settlement(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """ARQ worker entrypoint for settling a Dutch auction intent."""
    payload = ctx.get("payload") or ctx
    intent_id = payload.get("intent_id")
    if not intent_id:
        return {"status": "error", "error": "missing_intent_id"}
    db = SessionLocal()
    try:
        intent = (
            db.query(BuyIntent)
            .options(selectinload(BuyIntent.listing))
            .filter(BuyIntent.id == intent_id)
            .first()
        )
        if intent is None:
            return {"status": "not_found"}

        if intent.status in {BuyIntentStatus.CONFIRMED.value, BuyIntentStatus.FAILED.value}:
            record = _ensure_settlement_record(db, intent)
            logger.info(
                "settlement.idempotent.skip",
                extra={
                    "event": "settlement.idempotent.skip",
                    "intent_id": intent_id,
                    "status": intent.status,
                    "listing_id": intent.listing_id,
                },
            )
            _emit_settlement_event(intent, record, status=intent.status, failure_reason=intent.error_message)
            return {"status": intent.status, "tx": intent.external_tx_id}

        if intent.expires_at and intent.expires_at.replace(tzinfo=timezone.utc) <= _now():
            intent.status = BuyIntentStatus.FAILED.value
            intent.error_message = "intent_expired"
            intent.last_transition_at = _now()
            db.add(intent)
            db.commit()
            record = _persist_settlement(db, intent, tx_hash="expired")
            increment_counter("marketplace.settlement_failed", 1)
            _emit_settlement_event(intent, record, status=BuyIntentStatus.FAILED.value, failure_reason="intent_expired")
            logger.warning(
                "settlement.failed",
                extra={
                    "event": "settlement.failed",
                    "intent_id": intent.id,
                    "listing_id": intent.listing_id,
                    "error": "intent_expired",
                },
            )
            return {"status": intent.status, "error": "intent_expired"}

        try:
            web3 = get_web3_client()
        except Exception as exc:
            intent.status = BuyIntentStatus.FAILED.value
            intent.error_message = str(exc)
            intent.last_transition_at = _now()
            db.add(intent)
            db.commit()
            record = _persist_settlement(db, intent, tx_hash="failed")
            increment_counter("marketplace.settlement_failed", 1)
            _emit_settlement_event(intent, record, status=BuyIntentStatus.FAILED.value, failure_reason=str(exc))
            logger.warning(
                "settlement.failed",
                extra={
                    "event": "settlement.failed",
                    "intent_id": intent.id,
                    "listing_id": intent.listing_id,
                    "error": str(exc),
                },
            )
            return {"status": intent.status, "error": str(exc)}

        intent.status = BuyIntentStatus.SUBMITTED.value
        intent.last_transition_at = _now()
        db.add(intent)
        db.commit()
        db.refresh(intent)

        try:
            settlement_input = SettlementIntentData(
                intent_id=intent.id,
                listing_id=intent.listing_id,
                wallet=intent.wallet_address,
                amount=Decimal(str(intent.price)),
                currency=intent.currency,
            )
            result = await web3.settle_intent(settlement_input)
            intent.status = BuyIntentStatus.CONFIRMED.value if result.status == "SUCCESS" else BuyIntentStatus.FAILED.value
            intent.external_tx_id = result.tx_hash
            intent.last_transition_at = _now()
            db.add(intent)
            record = _persist_settlement(db, intent, result.tx_hash)
            db.commit()
            if intent.status == BuyIntentStatus.FAILED.value:
                increment_counter("marketplace.settlement_failed", 1)
                _emit_settlement_event(
                    intent,
                    record,
                    status=BuyIntentStatus.FAILED.value,
                    failure_reason=result.failure_reason or "unknown",
                )
                logger.warning(
                    "settlement.failed",
                    extra={
                        "event": "settlement.failed",
                        "intent_id": intent.id,
                        "listing_id": intent.listing_id,
                        "error": result.failure_reason or "unknown",
                    },
                )
                return {"status": intent.status, "error": result.failure_reason or "unknown"}
            increment_counter("marketplace.settlement_confirmed", 1)
            _emit_settlement_event(intent, record, status=BuyIntentStatus.CONFIRMED.value, failure_reason=None)
            publish(
                EVENT_SETTLEMENT_CONFIRMED,
                {
                    "listing_id": intent.listing_id,
                    "wallet_address": intent.wallet_address,
                    "intent_id": intent.id,
                    "amount": intent.price,
                    "currency": intent.currency,
                    "tx_hash": result.tx_hash,
                },
            )
            logger.info(
                "settlement.confirmed",
                extra={
                    "event": "settlement.confirmed",
                    "intent_id": intent.id,
                    "listing_id": intent.listing_id,
                    "tx_hash": result.tx_hash,
                    "status": intent.status,
                    "adapter": getattr(result, "adapter", "unknown"),
                },
            )
            return {"status": intent.status, "tx": result.tx_hash}
        except Exception as exc:  # pragma: no cover - error handling path deterministic in tests
            intent.status = BuyIntentStatus.FAILED.value
            intent.error_message = str(exc)
            intent.last_transition_at = _now()
            db.add(intent)
            db.commit()
            record = _persist_settlement(db, intent, tx_hash="failed")
            increment_counter("marketplace.settlement_failed", 1)
            _emit_settlement_event(intent, record, status=BuyIntentStatus.FAILED.value, failure_reason=str(exc))
            logger.warning(
                "settlement.failed",
                extra={
                    "event": "settlement.failed",
                    "intent_id": intent.id,
                    "listing_id": intent.listing_id,
                    "error": str(exc),
                },
            )
            return {"status": intent.status, "error": str(exc)}
    finally:
        db.close()


def _persist_settlement(db: Session, intent: BuyIntent, tx_hash: str) -> SettlementRecord:
    existing = (
        db.query(SettlementRecord)
        .filter(SettlementRecord.intent_id == intent.id)
        .first()
    )
    if existing:
        return existing
    record = SettlementRecord(
        intent_id=intent.id,
        listing_id=intent.listing_id,
        wallet_address=intent.wallet_address,
        settlement_amount=intent.price,
        currency=intent.currency,
        external_tx_id=tx_hash,
        auction_reference=intent.listing_id,
        # payment_intent_id kept empty for Phase 7 ChainPay linkage
        created_at=_now(),
    )
    db.add(record)
    return record


def _ensure_settlement_record(db: Session, intent: BuyIntent) -> SettlementRecord:
    existing = (
        db.query(SettlementRecord)
        .filter(SettlementRecord.intent_id == intent.id)
        .first()
    )
    if existing:
        return existing
    record = SettlementRecord(
        intent_id=intent.id,
        listing_id=intent.listing_id,
        wallet_address=intent.wallet_address,
        settlement_amount=intent.price,
        currency=intent.currency,
        external_tx_id=intent.external_tx_id or "n/a",
        auction_reference=intent.listing_id,
        created_at=_now(),
    )
    db.add(record)
    db.commit()
    return record


def _publish_redis_event(intent_id: str, payload: dict) -> None:
    """Emit a lightweight redis notification if Redis is reachable."""
    try:
        import redis  # type: ignore

        client = redis.from_url(settings.REDIS_URL)
        client.publish(f"SETTLEMENT:COMPLETE:{intent_id}", json.dumps(payload))
    except Exception:
        logger.debug("settlement.redis.publish_failed", extra={"intent_id": intent_id})


def _emit_settlement_event(intent: BuyIntent, record: SettlementRecord, *, status: str, failure_reason: Optional[str]) -> None:
    status_map = {
        BuyIntentStatus.CONFIRMED.value: "SETTLED",
        BuyIntentStatus.FAILED.value: "FAILED",
        BuyIntentStatus.SUBMITTED.value: "SETTLING",
        BuyIntentStatus.QUEUED.value: "PENDING",
    }
    public_status = status_map.get(status, "UNKNOWN")
    payload = {
        "type": EVENT_SETTLEMENT_COMPLETE,
        "intent_id": intent.id,
        "listing_id": intent.listing_id,
        "status": public_status,
        "tx_hash": intent.external_tx_id or record.external_tx_id,
        "final_price": intent.price,
        "currency": intent.currency,
        "failure_reason": failure_reason,
    }
    publish(EVENT_SETTLEMENT_COMPLETE, payload)
    publish(f"{EVENT_SETTLEMENT_COMPLETE}:{intent.id}", payload)
    publish(CHAIN_SETTLEMENT_CHANNEL, json.dumps(payload))
    _publish_redis_event(intent.id, payload)
