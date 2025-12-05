"""Marketplace endpoints for authoritative Dutch auction pricing and buy intents."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.database import get_db
from app.core.deps import InMemoryArq, get_arq_pool
from app.core.metrics import increment_counter
from app.models.marketplace import Listing
from app.schemas.marketplace import (
    BuyIntentCreateRequest,
    BuyIntentResponse,
    BuyIntentStatus,
    PriceQuoteResponse,
)
from app.services.marketplace.buy_intents import (
    BuyIntentValidationError,
    create_buy_intent,
)
from app.services.marketplace.dutch_engine import canonical_price
from app.services.marketplace.price_proof import PriceQuote, add_quote
from app.worker.settlement import enqueue_dutch_settlement

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marketplace/listings", tags=["marketplace"])

_PRICE_RL: dict[str, list[float]] = {}
_PRICE_RL_LOCK = threading.Lock()
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 15

# Backwards-compatible export for tests that override dependency
_InMemoryArq = InMemoryArq


def _auction_state_version(listing: Listing) -> str:
    base = listing.start_time or listing.created_at or datetime.utcnow()
    return str(int(base.timestamp()))


def _error(status_code: int, code: str, message: str, details: Optional[dict] = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "details": details},
    )


def _rate_limit_price(ip: Optional[str]) -> None:
    if not ip:
        return
    now = time.time()
    with _PRICE_RL_LOCK:
        recent = [ts for ts in _PRICE_RL.get(ip, []) if ts > now - RATE_LIMIT_WINDOW_SECONDS]
        if len(recent) >= RATE_LIMIT_MAX_REQUESTS:
            raise _error(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "RATE_LIMITED",
                "Too many price checks; slow down",
            )
        recent.append(now)
        _PRICE_RL[ip] = recent


@router.get("/{listing_id}/price", response_model=PriceQuoteResponse)
async def get_authoritative_price(listing_id: str, request: Request, db: Session = Depends(get_db)) -> PriceQuoteResponse:
    _rate_limit_price(request.client.host if request.client else None)
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise _error(status.HTTP_404_NOT_FOUND, "LISTING_NOT_FOUND", "Listing not found")
    price = canonical_price(listing)
    quote = add_quote(PriceQuote.create(listing_id, price, "USDC", _auction_state_version(listing)))
    increment_counter("marketplace.number_of_quotes", 1)
    logger.info(
        "marketplace.price.quote",
        extra={
            "event": "marketplace.price.quote",
            "listing_id": listing_id,
            "price": price,
            "currency": "USDC",
            "quoted_at": quote.quoted_at.isoformat(),
            "proof_nonce": quote.proof_nonce,
        },
    )
    return PriceQuoteResponse(
        listing_id=listing_id,
        auction_state_version=quote.auction_state_version,
        price=price,
        currency=quote.currency,
        quoted_at=quote.quoted_at,
        proof_nonce=quote.proof_nonce,
    )


@router.post(
    "/{listing_id}/buy_intents",
    response_model=BuyIntentResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_buy_intent_endpoint(
    listing_id: str,
    payload: BuyIntentCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    redis: "_InMemoryArq" = Depends(get_arq_pool),
) -> BuyIntentResponse:
    if payload.listing_id != listing_id:
        raise _error(
            status.HTTP_400_BAD_REQUEST,
            "LISTING_ID_MISMATCH",
            "listing_id in body does not match path",
        )
    client_ip: Optional[str] = request.client.host if request.client else None
    try:
        intent = create_buy_intent(
            listing_id=listing_id,
            wallet_address=payload.wallet_address,
            client_price=payload.client_price,
            proof_nonce=payload.proof_nonce,
            session=db,
            client_ip=client_ip,
        )
        increment_counter("marketplace.number_of_buy_intents", 1)
        increment_counter("marketplace.buy_intent_success", 1)
        logger.info(
            "marketplace.intent.created",
            extra={
                "event": "marketplace.intent.created",
                "listing_id": listing_id,
                "wallet": payload.wallet_address,
                "price": intent.price,
                "currency": intent.currency,
                "status": intent.status,
                "client_ip": client_ip,
            },
        )
    except BuyIntentValidationError as exc:
        increment_counter("marketplace.buy_intent_fail", 1)
        logger.warning(
            "marketplace.intent.rejected",
            extra={
                "event": "marketplace.intent.rejected",
                "listing_id": listing_id,
                "wallet": payload.wallet_address,
                "error_code": exc.code,
                "client_ip": client_ip,
            },
        )
        if exc.code == "LISTING_NOT_FOUND":
            raise _error(status.HTTP_404_NOT_FOUND, exc.code, exc.message, exc.details)
        if exc.code in {"QUOTE_MISMATCH", "NONCE_EXPIRED", "AUCTION_ENDED"}:
            raise _error(status.HTTP_400_BAD_REQUEST, exc.code, exc.message, exc.details)
        if exc.code == "RATE_LIMITED":
            raise _error(status.HTTP_429_TOO_MANY_REQUESTS, exc.code, exc.message, exc.details)
        if exc.code == "LISTING_NOT_ACTIVE":
            raise _error(status.HTTP_409_CONFLICT, exc.code, exc.message, exc.details)
        raise _error(status.HTTP_400_BAD_REQUEST, "INVALID_REQUEST", exc.message, exc.details)

    try:
        job_id = await enqueue_dutch_settlement(redis, intent.id)
        logger.info(
            "marketplace.intent.enqueued",
            extra={
                "intent_id": intent.id,
                "job_id": job_id,
                "listing_id": listing_id,
                "wallet": payload.wallet_address,
            },
        )
    except Exception as exc:  # pragma: no cover - hard failure paths exercised indirectly
        logger.warning(
            "marketplace.intent.enqueue_failed",
            extra={"intent_id": intent.id, "error": str(exc)},
        )
        raise _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "SETTLEMENT_QUEUE_UNAVAILABLE",
            "Settlement queue unavailable",
        )

    return BuyIntentResponse(
        intent_id=intent.id,
        status=BuyIntentStatus(intent.status),
        price=intent.price,
        currency=intent.currency,
        expires_at=intent.expires_at,
    )
