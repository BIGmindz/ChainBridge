"""Tests for SettlementEvent API and demo generator."""

from datetime import datetime
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.models.chainpay import PaymentIntent, SettlementEvent
from api.server import app
from scripts import generate_demo_settlement_events


@pytest.fixture(scope="module")
def client_with_db() -> Tuple[TestClient, Any, sessionmaker]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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


def _seed_intent(session: Session, risk_level: str = "LOW") -> str:
    intent_id = f"PAY-TEST-{risk_level}-{datetime.utcnow().timestamp()}"
    intent = PaymentIntent(
        id=intent_id,
        shipment_id="SHIP-SET",
        amount=1000.0,
        currency="USD",
        status="PENDING",
        risk_level=risk_level,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(intent)
    session.commit()
    return intent.id


def test_list_settlement_events_empty(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session)
    resp = client.get(f"/chainpay/payment_intents/{intent_id}/settlement_events")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_settlement_events_not_found(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, _ = client_with_db
    resp = client.get("/chainpay/payment_intents/DOES-NOT-EXIST/settlement_events")
    assert resp.status_code == 404


def test_list_settlement_events_sorted(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session)
        earlier = SettlementEvent(
            payment_intent_id=intent_id,
            event_type="CREATED",
            status="PENDING",
            amount=1000.0,
            currency="USD",
            occurred_at=datetime(2024, 1, 1, 0, 0, 0),
            sequence=1,
        )
        later = SettlementEvent(
            payment_intent_id=intent_id,
            event_type="AUTHORIZED",
            status="SUCCESS",
            amount=1000.0,
            currency="USD",
            occurred_at=datetime(2024, 1, 1, 1, 0, 0),
            sequence=2,
        )
        session.add_all([later, earlier])
        session.commit()

    resp = client.get(f"/chainpay/payment_intents/{intent_id}/settlement_events")
    assert resp.status_code == 200
    events = resp.json()
    assert [e["event_type"] for e in events] == ["CREATED", "AUTHORIZED"]
    assert [e["sequence"] for e in events] == [1, 2]


def test_demo_generator_paths(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        low_id = _seed_intent(session, risk_level="LOW")
        high_id = _seed_intent(session, risk_level="HIGH")
        generate_demo_settlement_events.generate(session=session, skip_init=True)

    low_events = client.get(f"/chainpay/payment_intents/{low_id}/settlement_events").json()
    assert [e["event_type"] for e in low_events][-1] == "CAPTURED"
    high_events = client.get(f"/chainpay/payment_intents/{high_id}/settlement_events").json()
    assert [e["event_type"] for e in high_events][-1] == "FAILED"


def test_append_settlement_event_and_idempotent(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session)

    payload = {
        "event_type": "CREATED",
        "status": "PENDING",
        "amount": 1000.0,
        "currency": "USD",
    }
    first = client.post(f"/chainpay/payment_intents/{intent_id}/settlement_events", json=payload)
    assert first.status_code == 201
    event_id = first.json()["id"]
    second = client.post(f"/chainpay/payment_intents/{intent_id}/settlement_events", json=payload)
    assert second.status_code == 201
    assert second.json()["id"] == event_id


def test_append_settlement_event_regression_rejected(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session)
        session.add(
            SettlementEvent(
                payment_intent_id=intent_id,
                event_type="AUTHORIZED",
                status="SUCCESS",
                amount=1000.0,
                currency="USD",
                occurred_at=datetime(2024, 1, 1, 1, 0, 0),
                sequence=2,
            )
        )
        session.commit()

    payload = {
        "event_type": "CREATED",
        "status": "PENDING",
        "amount": 1000.0,
        "currency": "USD",
        "occurred_at": "2024-01-01T02:00:00Z",
    }
    resp = client.post(f"/chainpay/payment_intents/{intent_id}/settlement_events", json=payload)
    assert resp.status_code == 400


def test_double_terminal_event_rejected(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session)
        session.add(
            SettlementEvent(
                payment_intent_id=intent_id,
                event_type="CASH_RELEASED",
                status="SUCCESS",
                amount=1000.0,
                currency="USD",
                occurred_at=datetime(2024, 1, 1, 1, 0, 0),
                sequence=3,
            )
        )
        session.commit()

    payload = {
        "event_type": "CASH_RELEASED",
        "status": "SUCCESS",
        "amount": 1000.0,
        "currency": "USD",
        "occurred_at": "2024-01-01T02:00:00Z",
    }
    resp = client.post(f"/chainpay/payment_intents/{intent_id}/settlement_events", json=payload)
    assert resp.status_code in (400, 409)


def test_replace_and_delete_event(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session)

    create_payload = {
        "event_type": "CREATED",
        "status": "PENDING",
        "amount": 1000.0,
        "currency": "USD",
    }
    created = client.post(f"/chainpay/payment_intents/{intent_id}/settlement_events", json=create_payload)
    assert created.status_code == 201
    event_id = created.json()["id"]

    update_payload = {
        "status": "SUCCESS",
        "metadata": {"note": "updated"},
    }
    updated = client.put(
        f"/chainpay/payment_intents/{intent_id}/settlement_events/{event_id}",
        json=update_payload,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "SUCCESS"
    assert updated.json()["metadata"] == {"note": "updated"}

    deleted = client.delete(
        f"/chainpay/payment_intents/{intent_id}/settlement_events/{event_id}",
    )
    assert deleted.status_code == 204
    remaining = client.get(f"/chainpay/payment_intents/{intent_id}/settlement_events")
    assert remaining.json() == []
