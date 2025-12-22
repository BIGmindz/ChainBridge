"""Buy intent creation and validation for Dutch auctions."""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from api.database import SessionLocal
from app.models.marketplace import Listing, BuyIntent
from app.schemas.marketplace import BuyIntentStatus
from app.services.marketplace.dutch_engine import canonical_price
from app.services.marketplace.price_proof import PriceQuote, validate_nonce

logger = logging.getLogger(__name__)

PRICE_TOLERANCE = Decimal("0.00")
INTENT_TTL_SECONDS = 120
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 5
CURRENCY = "USDC"

_RATE_LIMIT_BUCKETS: dict[str, list[float]] = {}
_RATE_LIMIT_IP_BUCKETS: dict[str, list[float]] = {}
_RATE_LOCK = threading.Lock()


@dataclass
class BuyIntentValidationError(Exception):
    code: str
    message: str
    details: Optional[dict] = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_price_proof(listing_id: str, price: Decimal, currency: str, quote: PriceQuote) -> str:
    payload = {
        "listing_id": listing_id,
        "price": str(price),
        "currency": currency,
        "quoted_at": quote.quoted_at.isoformat(),
        "proof_nonce": quote.proof_nonce,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _check_rate_limit(wallet: str, client_ip: Optional[str]) -> None:
    with _RATE_LOCK:
        now = time.time()
        wallet_recent = [ts for ts in _RATE_LIMIT_BUCKETS.get(wallet, []) if ts > now - RATE_LIMIT_WINDOW_SECONDS]
        if len(wallet_recent) >= RATE_LIMIT_MAX_REQUESTS:
            raise BuyIntentValidationError("RATE_LIMITED", "Too many attempts; retry later")
        wallet_recent.append(now)
        _RATE_LIMIT_BUCKETS[wallet] = wallet_recent

        if client_ip:
            ip_recent = [ts for ts in _RATE_LIMIT_IP_BUCKETS.get(client_ip, []) if ts > now - RATE_LIMIT_WINDOW_SECONDS]
            if len(ip_recent) >= RATE_LIMIT_MAX_REQUESTS:
                raise BuyIntentValidationError("RATE_LIMITED", "Too many attempts; retry later")
            ip_recent.append(now)
            _RATE_LIMIT_IP_BUCKETS[client_ip] = ip_recent


def _enforce_listing_state(listing: Listing) -> None:
    now = _now()
    if listing.status != "ACTIVE":
        raise BuyIntentValidationError("LISTING_NOT_ACTIVE", "Listing is not active")
    if listing.expires_at:
        exp = listing.expires_at
        exp = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
        if exp <= now:
            raise BuyIntentValidationError("AUCTION_ENDED", "Auction has ended")


def create_buy_intent(
    listing_id: str,
    wallet_address: str,
    client_price: float,
    proof_nonce: str,
    *,
    session: Optional[Session] = None,
    client_ip: Optional[str] = None,
) -> BuyIntent:
    """Validate and persist a buy intent."""
    db = session or SessionLocal()
    managed = session is None
    try:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        if listing is None:
            raise BuyIntentValidationError("LISTING_NOT_FOUND", "Listing not found")

        _enforce_listing_state(listing)
        _check_rate_limit(wallet_address, client_ip)

        try:
            quote = validate_nonce(listing_id, proof_nonce)
        except ValueError as exc:
            if str(exc) in {"nonce_expired", "nonce_listing_mismatch"}:
                raise BuyIntentValidationError("NONCE_EXPIRED", "Quote nonce expired or invalid")
            raise
        server_price = Decimal(str(canonical_price(listing)))
        quoted_price = Decimal(str(quote.price))
        client_price_dec = Decimal(str(client_price))

        if client_price_dec != server_price or quoted_price != server_price:
            raise BuyIntentValidationError(
                "QUOTE_MISMATCH",
                "Client price does not match canonical price.",
                details={"canonical_price": float(server_price), "client_price": float(client_price_dec)},
            )

        max_allowed = listing.buy_now_price or listing.start_price or server_price
        if server_price > Decimal(str(max_allowed)):
            raise BuyIntentValidationError("QUOTE_MISMATCH", "Price exceeds maximum allowed for listing.")

        expires_at = _now() + timedelta(seconds=INTENT_TTL_SECONDS)
        proof_hash = _hash_price_proof(listing_id, server_price, CURRENCY, quote)

        intent = BuyIntent(
            listing_id=listing_id,
            wallet_address=wallet_address,
            price=float(server_price),
            currency=CURRENCY,
            status=BuyIntentStatus.QUEUED.value,
            created_at=_now(),
            expires_at=expires_at,
            proof_nonce=proof_nonce,
            price_proof_hash=proof_hash,
            last_transition_at=_now(),
        )
        db.add(intent)
        db.commit()
        db.refresh(intent)
        logger.info(
            "buy_intent.created",
            extra={
                "intent_id": intent.id,
                "listing_id": listing_id,
                "wallet": wallet_address,
                "price": float(server_price),
                "client_ip": client_ip,
            },
        )
        return intent
    finally:
        if managed:
            db.close()
