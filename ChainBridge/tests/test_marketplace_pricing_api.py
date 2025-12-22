"""Phase 2: Marketplace pricing API tests.

These tests validate Dutch auction pricing mechanisms via API.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db

# Namespace isolation: import from app.api.api (module) to avoid collision
# with chainiq-service's app.api (which is a file, not a package)
from app.api.api import app
from app.models.marketplace import Listing

pytestmark = pytest.mark.phase2


@pytest.fixture(scope="module")
def client_with_db() -> Tuple[TestClient, Any, sessionmaker]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client, engine, TestingSessionLocal
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def clean_db(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    _, engine, _ = client_with_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _listing(session, **kwargs) -> Listing:
    listing = Listing(
        id=kwargs.get("id", "LST-1"),
        shipment_id=kwargs.get("shipment_id", "SHIP-1"),
        token_id=kwargs.get("token_id", "TOK-1"),
        start_price=kwargs.get("start_price", 100.0),
        reserve_price=kwargs.get("reserve_price", 50.0),
        decay_rate_per_minute=kwargs.get("decay_rate_per_minute", 1.0),
        start_time=kwargs.get("start_time", datetime.now(timezone.utc) - timedelta(minutes=5)),
        expires_at=kwargs.get("expires_at"),
        status="ACTIVE",
    )
    session.add(listing)
    session.commit()
    return listing.id


def test_price_pre_start_uses_start_price(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    start_time = datetime.now(timezone.utc) + timedelta(minutes=10)
    with SessionLocal() as session:
        listing_id = _listing(
            session, id="LST-PRE", start_time=start_time, start_price=120.0, reserve_price=90.0, decay_rate_per_minute=1.5
        )
    resp = client.get(f"/marketplace/listings/{listing_id}/price")
    assert resp.status_code == 200
    body = resp.json()
    assert body["price"] == 120.0
    assert body["proof_nonce"]


def test_price_active_decays_but_above_reserve(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    with SessionLocal() as session:
        listing_id = _listing(
            session, id="LST-ACTIVE", start_time=start_time, start_price=100.0, reserve_price=80.0, decay_rate_per_minute=1.5
        )
    resp = client.get(f"/marketplace/listings/{listing_id}/price")
    assert resp.status_code == 200
    body = resp.json()
    assert 80.0 <= body["price"] <= 100.0


def test_price_at_reserve_after_long_decay(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    start_time = datetime.now(timezone.utc) - timedelta(minutes=90)
    with SessionLocal() as session:
        listing_id = _listing(
            session, id="LST-RESERVE", start_time=start_time, start_price=150.0, reserve_price=60.0, decay_rate_per_minute=2.0
        )
    resp = client.get(f"/marketplace/listings/{listing_id}/price")
    assert resp.status_code == 200
    body = resp.json()
    assert body["price"] == pytest.approx(60.0)


def test_price_after_expiry_still_returns_authoritative_value(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    start_time = datetime.now(timezone.utc) - timedelta(minutes=120)
    expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    with SessionLocal() as session:
        listing_id = _listing(
            session,
            id="LST-EXPIRED",
            start_time=start_time,
            start_price=200.0,
            reserve_price=70.0,
            decay_rate_per_minute=5.0,
            expires_at=expires_at,
        )
    resp = client.get(f"/marketplace/listings/{listing_id}/price")
    assert resp.status_code == 200
    body = resp.json()
    assert body["price"] == pytest.approx(70.0)


def test_price_rounding_and_decay_boundary(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    with SessionLocal() as session:
        listing_id = _listing(
            session, id="LST-ROUND", start_time=start_time, start_price=100.01, reserve_price=40.0, decay_rate_per_minute=1.0
        )
    resp = client.get(f"/marketplace/listings/{listing_id}/price")
    assert resp.status_code == 200
    body = resp.json()
    # 100.01 - (1 * 10) = 90.01 exactly after rounding
    assert body["price"] == pytest.approx(90.01, rel=1e-3)
