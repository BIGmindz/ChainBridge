"""Price quote proof cache for Dutch auctions."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from uuid import uuid4

QUOTE_TTL_SECONDS = 60
_QUOTE_CACHE: Dict[str, "PriceQuote"] = {}
_LOCK = threading.Lock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PriceQuote:
    listing_id: str
    price: float
    currency: str
    quoted_at: datetime
    proof_nonce: str
    auction_state_version: str
    expires_at: datetime

    @classmethod
    def create(cls, listing_id: str, price: float, currency: str, auction_state_version: str) -> "PriceQuote":
        quoted_at = _now()
        return cls(
            listing_id=listing_id,
            price=price,
            currency=currency,
            quoted_at=quoted_at,
            proof_nonce=str(uuid4()),
            auction_state_version=auction_state_version,
            expires_at=quoted_at + timedelta(seconds=QUOTE_TTL_SECONDS),
        )


def add_quote(quote: PriceQuote) -> PriceQuote:
    """Persist a quote to the in-memory cache with TTL."""
    with _LOCK:
        _cleanup_expired()
        _QUOTE_CACHE[quote.proof_nonce] = quote
    return quote


def _cleanup_expired() -> None:
    now = _now()
    expired = [nonce for nonce, quote in _QUOTE_CACHE.items() if quote.expires_at <= now]
    for nonce in expired:
        _QUOTE_CACHE.pop(nonce, None)


def get_quote(nonce: str) -> Optional[PriceQuote]:
    with _LOCK:
        _cleanup_expired()
        return _QUOTE_CACHE.get(nonce)


def validate_nonce(listing_id: str, nonce: str) -> PriceQuote:
    quote = get_quote(nonce)
    if quote is None:
        raise ValueError("nonce_expired")
    if quote.listing_id != listing_id:
        raise ValueError("nonce_listing_mismatch")
    if quote.expires_at <= _now():
        raise ValueError("nonce_expired")
    return quote
