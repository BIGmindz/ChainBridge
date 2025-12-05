import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Tuple

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base
from api.eventbus import dispatcher
from app.models.marketplace import BuyIntent, Listing, SettlementRecord
from app.schemas.marketplace import BuyIntentStatus
from app.worker import settlement

pytestmark = pytest.mark.phase2


@pytest.fixture(scope="module")
def db_sessionmaker() -> Tuple[Any, sessionmaker]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    Base.metadata.create_all(
        bind=engine,
        tables=[Listing.__table__, BuyIntent.__table__, SettlementRecord.__table__],
    )
    yield engine, SessionLocal
    Base.metadata.drop_all(
        bind=engine,
        tables=[Listing.__table__, BuyIntent.__table__, SettlementRecord.__table__],
    )


@pytest.fixture(autouse=True)
def clean_db(db_sessionmaker: Tuple[Any, sessionmaker]) -> None:
    engine, _ = db_sessionmaker
    Base.metadata.drop_all(
        bind=engine,
        tables=[Listing.__table__, BuyIntent.__table__, SettlementRecord.__table__],
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[Listing.__table__, BuyIntent.__table__, SettlementRecord.__table__],
    )
    dispatcher._SUBSCRIBERS.clear()


@pytest.fixture(autouse=True)
def patch_sessionmaker(db_sessionmaker: Tuple[Any, sessionmaker], monkeypatch: pytest.MonkeyPatch) -> None:
    _, SessionLocal = db_sessionmaker
    monkeypatch.setattr(settlement, "SessionLocal", SessionLocal)


def _listing(session, **kwargs) -> Listing:
    listing = Listing(
        id=kwargs.get("id", "LST-WORKER"),
        shipment_id="SHIP-WORKER",
        token_id="TOK-WORKER",
        start_price=kwargs.get("start_price", 100.0),
        reserve_price=kwargs.get("reserve_price", 50.0),
        decay_rate_per_minute=kwargs.get("decay_rate_per_minute", 1.0),
        start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
        status="ACTIVE",
    )
    session.add(listing)
    session.commit()
    return listing.id


def _intent(session, listing_id: str, status: str = BuyIntentStatus.QUEUED.value) -> BuyIntent:
    intent = BuyIntent(
        id="INT-" + listing_id,
        listing_id=listing_id,
        wallet_address="0x" + "9" * 40,
        price=42.0,
        currency="USDC",
        status=status,
        proof_nonce="nonce",
        price_proof_hash="hash",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        last_transition_at=datetime.now(timezone.utc),
    )
    session.add(intent)
    session.commit()
    return intent


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_execute_dutch_settlement_happy_path(db_sessionmaker: Tuple[Any, sessionmaker], monkeypatch: pytest.MonkeyPatch) -> None:
    _, SessionLocal = db_sessionmaker
    with SessionLocal() as session:
        listing_id = _listing(session, id="LST-HAPPY")
        intent = _intent(session, listing_id)

    class StubClient:
        async def settle_intent(self, payload):
            class Result:
                tx_hash = "0xhappy"
                status = "SUCCESS"
                adapter = "TEST"

            return Result()

    events = []
    dispatcher.subscribe(settlement.EVENT_SETTLEMENT_CONFIRMED, lambda payload: events.append(payload))
    monkeypatch.setattr(settlement, "get_web3_client", lambda: StubClient())

    result = _run(settlement.execute_dutch_settlement({"intent_id": intent.id}))
    assert result["status"] == BuyIntentStatus.CONFIRMED.value

    with SessionLocal() as session:
        refreshed = session.query(BuyIntent).filter(BuyIntent.id == intent.id).first()
        assert refreshed.status == BuyIntentStatus.CONFIRMED.value
        assert refreshed.external_tx_id == "0xhappy"
        settlement_record = session.query(SettlementRecord).filter(SettlementRecord.intent_id == intent.id).first()
        assert settlement_record is not None

    assert events and events[0]["intent_id"] == intent.id


def test_execute_dutch_settlement_idempotent(db_sessionmaker: Tuple[Any, sessionmaker], monkeypatch: pytest.MonkeyPatch) -> None:
    _, SessionLocal = db_sessionmaker
    with SessionLocal() as session:
        listing_id = _listing(session, id="LST-IDEMPOTENT")
        intent = _intent(session, listing_id)

    class StubClient:
        async def settle_intent(self, payload):
            class Result:
                tx_hash = "0xidem"
                status = "SUCCESS"
                adapter = "TEST"

            return Result()

    monkeypatch.setattr(settlement, "get_web3_client", lambda: StubClient())

    first = _run(settlement.execute_dutch_settlement({"intent_id": intent.id}))
    second = _run(settlement.execute_dutch_settlement({"intent_id": intent.id}))
    assert first["status"] == BuyIntentStatus.CONFIRMED.value
    assert second["status"] == BuyIntentStatus.CONFIRMED.value

    with SessionLocal() as session:
        records = session.query(SettlementRecord).filter(SettlementRecord.intent_id == intent.id).all()
        assert len(records) == 1


def test_execute_dutch_settlement_failure_path(db_sessionmaker: Tuple[Any, sessionmaker], monkeypatch: pytest.MonkeyPatch) -> None:
    _, SessionLocal = db_sessionmaker
    with SessionLocal() as session:
        listing_id = _listing(session, id="LST-FAIL")
        intent = _intent(session, listing_id)

    class FailingClient:
        async def settle_intent(self, payload):
            raise RuntimeError("chain_down")

    monkeypatch.setattr(settlement, "get_web3_client", lambda: FailingClient())

    result = _run(settlement.execute_dutch_settlement({"intent_id": intent.id}))
    assert result["status"] == BuyIntentStatus.FAILED.value

    with SessionLocal() as session:
        refreshed = session.query(BuyIntent).filter(BuyIntent.id == intent.id).first()
        assert refreshed.status == BuyIntentStatus.FAILED.value
        assert "chain_down" in (refreshed.error_message or "")


def test_execute_dutch_settlement_web3_not_configured(db_sessionmaker: Tuple[Any, sessionmaker], monkeypatch: pytest.MonkeyPatch) -> None:
    _, SessionLocal = db_sessionmaker
    with SessionLocal() as session:
        listing_id = _listing(session, id="LST-NO-WEB3")
        intent = _intent(session, listing_id)

    def raise_get_client():
        raise RuntimeError("web3_not_configured")

    monkeypatch.setattr(settlement, "get_web3_client", raise_get_client)

    result = _run(settlement.execute_dutch_settlement({"intent_id": intent.id}))
    assert result["status"] == BuyIntentStatus.FAILED.value
    assert result["error"] == "web3_not_configured"

    with SessionLocal() as session:
        refreshed = session.query(BuyIntent).filter(BuyIntent.id == intent.id).first()
        assert refreshed.status == BuyIntentStatus.FAILED.value
        assert refreshed.error_message == "web3_not_configured"
