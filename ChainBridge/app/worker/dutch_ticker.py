"""ARQ cron task to update dutch auction prices."""
from __future__ import annotations

import asyncio
import time

from api.database import SessionLocal
from app.models.marketplace import Listing
from app.services.marketplace.dutch_engine import calculate_price


async def tick_active_auctions(ctx) -> None:
    db = SessionLocal()
    try:
        listings = (
            db.query(Listing)
            .filter(Listing.status == "ACTIVE")
            .all()
        )
        now = time.time()
        for listing in listings:
            price = calculate_price(listing)
            # best-effort cache update using local cache in dutch_engine
            from app.services.marketplace import dutch_engine
            dutch_engine._local_cache[f"auction:{listing.id}:price"] = (price, now)
            if listing.reserve_price and price <= listing.reserve_price:
                listing.status = "EXPIRED"
                db.add(listing)
        db.commit()
    finally:
        db.close()
    await asyncio.sleep(0)
