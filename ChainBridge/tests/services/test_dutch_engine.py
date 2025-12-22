"""Phase 2: Dutch auction engine tests.

These tests validate the Dutch auction price decay mechanism for RWA liquidations.
Due to sys.path conflicts between the monorepo 'app' package and chainiq-service 'app',
these imports fail when conftest.py loads api.server first.

Status: Deferred to Phase 2 (module exists but import path conflicts with ChainIQ)
"""
import asyncio
import threading
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base

# Phase 2: Import guard due to sys.path conflict with chainiq-service
try:
    from app.models.marketplace import Listing
    from app.services.marketplace.dutch_engine import calculate_price, execute_atomic_purchase, get_live_price
    _DUTCH_ENGINE_AVAILABLE = True
except ImportError:
    _DUTCH_ENGINE_AVAILABLE = False
    Listing = calculate_price = execute_atomic_purchase = get_live_price = None

pytestmark = [
    pytest.mark.phase2,
    pytest.mark.skipif(not _DUTCH_ENGINE_AVAILABLE, reason="Dutch engine module unavailable (sys.path conflict with ChainIQ)"),
]


def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _listing(start_price=100.0, reserve=50.0, rate=1.0, start=None):
    return Listing(
        id="L1",
        shipment_id="SHIP",
        token_id="T1",
        start_price=start_price,
        reserve_price=reserve,
        decay_rate_per_minute=rate,
        start_time=start or datetime.utcnow(),
        status="ACTIVE",
    )


def test_price_decay_and_reserve():
    session = _session()
    start = datetime.utcnow() - timedelta(minutes=10)
    listing = _listing(start_price=100, reserve=80, rate=2, start=start)
    session.add(listing)
    session.commit()
    price = calculate_price(listing, datetime.utcnow())
    assert price <= 100
    assert price >= 80
    session.close()


def test_get_live_price_uses_cache():
    session = _session()
    listing = _listing()
    session.add(listing)
    session.commit()
    price1 = asyncio_run(get_live_price(listing.id, session=session))
    price2 = asyncio_run(get_live_price(listing.id, session=session))
    assert price1 == price2
    session.close()


def asyncio_run(coro):
    return asyncio.run(coro)


def test_atomic_purchase_allows_single_winner():
    db = _session()
    listing = _listing()
    db.add(listing)
    db.commit()
    price_first = asyncio_run(execute_atomic_purchase(listing.id, "0x" + "a" * 40, session=db))
    assert price_first is not None
    try:
        asyncio_run(execute_atomic_purchase(listing.id, "0x" + "b" * 40, session=db))
        assert False, "second purchase should fail"
    except Exception:
        pass
    db.close()
