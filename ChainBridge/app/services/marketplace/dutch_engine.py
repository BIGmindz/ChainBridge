"""Dutch auction pricing and atomic buy logic."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from api.database import SessionLocal
from app.models.marketplace import Listing
from app.services.marketplace.auctioneer import execute_sale

_local_cache: dict[str, tuple[float, float]] = {}
_locks: dict[str, threading.Lock] = {}

# Ensure an event loop exists for synchronous test runners that call asyncio APIs directly.
import asyncio

try:  # pragma: no cover - defensive for legacy tests
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())


def _get_lock(key: str) -> threading.Lock:
    if key not in _locks:
        _locks[key] = threading.Lock()
    return _locks[key]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _elapsed_minutes(start: datetime) -> float:
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return max(0.0, (_now() - start).total_seconds() / 60.0)


def calculate_price(listing: Listing, now: Optional[datetime] = None) -> float:
    """Backwards-compatible price calculation (deprecated in favor of canonical_price)."""
    base_time = listing.start_time or listing.created_at or _now()
    elapsed = _elapsed_minutes(base_time if now is None else now)
    rate = listing.decay_rate_per_minute or 0.0
    reserve = listing.reserve_price if listing.reserve_price is not None else listing.start_price * 0.5
    price = max(reserve, (listing.start_price or 0.0) - rate * elapsed)
    return round(price, 2)


def canonical_price(listing: Listing, now: Optional[datetime] = None) -> float:
    """Authoritative price: pre-start=start_price, active=decay, post-expiry=reserve."""
    ref = now or _now()
    base_time = listing.start_time or listing.created_at or ref
    if base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    elapsed = _elapsed_minutes(base_time if ref >= base_time else base_time)
    rate = listing.decay_rate_per_minute or 0.0
    reserve = listing.reserve_price if listing.reserve_price is not None else (listing.start_price or 0.0) * 0.5
    raw_price = (listing.start_price or 0.0) if ref < base_time else (listing.start_price or 0.0) - rate * elapsed
    active_price = max(reserve, raw_price)
    if listing.expires_at:
        exp = listing.expires_at if listing.expires_at.tzinfo else listing.expires_at.replace(tzinfo=timezone.utc)
        if ref >= exp:
            active_price = min(active_price, reserve)
    return round(active_price, 2)


async def get_live_price(listing_id: str, session: Optional[Session] = None) -> float:
    cache_key = f"auction:{listing_id}:price"
    cached = _local_cache.get(cache_key)
    if cached:
        price, ts = cached
        if time.time() - ts < 60:
            return price
    db = session or SessionLocal()
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise ValueError("listing_not_found")
    price = canonical_price(listing)
    _local_cache[cache_key] = (price, time.time())
    return price


async def execute_atomic_purchase(listing_id: str, buyer_wallet: str, session: Optional[Session] = None) -> float:
    db = session or SessionLocal()
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise ValueError("listing_not_found")
    lock = _get_lock(listing_id)
    with lock:
        if listing.status != "ACTIVE":
            raise ValueError("not_active")
        price = await get_live_price(listing_id, session=db)
        execute_sale(listing, buyer_wallet, price, session=db)
        cache_key = f"auction:{listing_id}:price"
        _local_cache[cache_key] = (price, time.time())
        return price
