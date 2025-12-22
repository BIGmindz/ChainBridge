"""Phase 2: Marketplace buy intents API tests.

These tests validate the marketplace API endpoints for buy intent management.
Due to sys.path conflicts between the monorepo 'app' package and chainiq-service 'app',
these imports fail when conftest.py loads api.server first.

Status: Deferred to Phase 2 (module exists but import path conflicts with ChainIQ)
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db

# Phase 2: Import guard due to sys.path conflict with chainiq-service
try:
    from app.api import app
    from app.api.endpoints import marketplace as marketplace_api
    from app.models.marketplace import BuyIntent, Listing
    from app.services.marketplace import buy_intents, price_proof
    _MARKETPLACE_AVAILABLE = True
except ImportError:
    _MARKETPLACE_AVAILABLE = False
    app = marketplace_api = BuyIntent = Listing = buy_intents = price_proof = None

pytestmark = [
    pytest.mark.phase2,
    pytest.mark.skipif(not _MARKETPLACE_AVAILABLE, reason="Marketplace module unavailable (sys.path conflict with ChainIQ)"),
]


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
def clean_state(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    _, engine, _ = client_with_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    price_proof._QUOTE_CACHE.clear()
    buy_intents._RATE_LIMIT_BUCKETS.clear()
    buy_intents._RATE_LIMIT_IP_BUCKETS.clear()


def _listing(session, **kwargs) -> Listing:
    listing = Listing(
        id=kwargs.get("id", "LST-1"),
        shipment_id=kwargs.get("shipment_id", "SHIP-1"),
        token_id=kwargs.get("token_id", "TOK-1"),
        start_price=kwargs.get("start_price", 100.0),
        reserve_price=kwargs.get("reserve_price", 80.0),
        decay_rate_per_minute=kwargs.get("decay_rate_per_minute", 0.5),
        start_time=kwargs.get("start_time", datetime.now(timezone.utc) - timedelta(minutes=5)),
        status="ACTIVE",
    )
    session.add(listing)
    session.commit()
    return listing.id


def test_quote_mismatch_rejected(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        listing_id = _listing(session, id="LST-MISMATCH")
    quote = client.get(f"/marketplace/listings/{listing_id}/price").json()

    resp = client.post(
        f"/marketplace/listings/{listing_id}/buy_intents",
        json={
            "wallet_address": "0x" + "1" * 40,
            "client_price": quote["price"] + 5.0,
            "proof_nonce": quote["proof_nonce"],
            "listing_id": listing_id,
        },
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "QUOTE_MISMATCH"


def test_expired_nonce_rejected(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        listing_id = _listing(session, id="LST-EXPIRED")
    expired_quote = price_proof.PriceQuote(
        listing_id=listing_id,
        price=95.0,
        currency="USDC",
        quoted_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        proof_nonce="expired-nonce",
        auction_state_version="v1",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    price_proof.add_quote(expired_quote)

    resp = client.post(
        f"/marketplace/listings/{listing_id}/buy_intents",
        json={
            "wallet_address": "0x" + "2" * 40,
            "client_price": 95.0,
            "proof_nonce": expired_quote.proof_nonce,
            "listing_id": listing_id,
        },
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "NONCE_EXPIRED"


def test_buy_intent_happy_path_enqueues_worker(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    stub = marketplace_api._InMemoryArq()
    app.dependency_overrides[marketplace_api.get_arq_pool] = lambda: stub

    with SessionLocal() as session:
        listing_id = _listing(session, id="LST-HAPPY")
    quote = client.get(f"/marketplace/listings/{listing_id}/price").json()

    resp = client.post(
        f"/marketplace/listings/{listing_id}/buy_intents",
        json={
            "wallet_address": "0x" + "3" * 40,
            "client_price": quote["price"],
            "proof_nonce": quote["proof_nonce"],
            "listing_id": listing_id,
        },
    )
    app.dependency_overrides.pop(marketplace_api.get_arq_pool, None)

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "QUEUED"
    assert stub.jobs
    job_name, payload = stub.jobs[0]
    assert job_name == "execute_dutch_settlement"
    assert payload["intent_id"]

    with SessionLocal() as session:
        intent = session.query(BuyIntent).filter(BuyIntent.id == body["intent_id"]).first()
        assert intent is not None
        assert intent.price_proof_hash


def test_rate_limit_blocks_repeated_attempts(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        listing_id = _listing(session, id="LST-RATE")
    quote = client.get(f"/marketplace/listings/{listing_id}/price").json()
    payload = {
        "wallet_address": "0x" + "4" * 40,
        "client_price": quote["price"],
        "proof_nonce": quote["proof_nonce"],
        "listing_id": listing_id,
    }
    for _ in range(buy_intents.RATE_LIMIT_MAX_REQUESTS):
        resp = client.post(f"/marketplace/listings/{listing_id}/buy_intents", json=payload)
        if resp.status_code != 202:
            break
    resp = client.post(f"/marketplace/listings/{listing_id}/buy_intents", json=payload)
    assert resp.status_code == 429
    detail = resp.json()["detail"]
    assert detail["code"] == "RATE_LIMITED"


def test_auction_expired_rejected(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
    with SessionLocal() as session:
        listing_id = _listing(session, id="LST-END", start_time=expired_time - timedelta(minutes=10))
        listing = session.get(Listing, listing_id)
        listing.expires_at = expired_time
        session.add(listing)
        session.commit()
    quote = client.get(f"/marketplace/listings/{listing_id}/price").json()
    resp = client.post(
        f"/marketplace/listings/{listing_id}/buy_intents",
        json={
            "wallet_address": "0x" + "5" * 40,
            "client_price": quote["price"],
            "proof_nonce": quote["proof_nonce"],
            "listing_id": listing_id,
        },
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "AUCTION_ENDED"
