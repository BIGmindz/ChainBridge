from datetime import datetime
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.events.bus import EventType, event_bus
from api.models.chaindocs import Shipment
from api.models.chainiq import DocumentHealthSnapshot
from api.models.chainpay import PaymentIntent
from api.server import app


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
    event_bus.clear_subscribers()


def _seed_intent(session, *, risk_level: str = "LOW", risk_score: int = 20, amount: float = 100.0) -> str:
    shipment = Shipment(id=f"SHIP-AUD-{risk_level}", corridor_code="CN-US", mode="OCEAN")
    session.add(shipment)
    session.flush()
    snapshot = DocumentHealthSnapshot(
        shipment_id=shipment.id,
        corridor_code="CN-US",
        mode="OCEAN",
        incoterm=None,
        template_name="DEFAULT",
        present_count=1,
        missing_count=0,
        required_total=1,
        optional_total=0,
        blocking_gap_count=0,
        completeness_pct=100,
        risk_score=risk_score,
        risk_level=risk_level,
        created_at=datetime.utcnow(),
    )
    session.add(snapshot)
    intent = PaymentIntent(
        id=f"PAY-AUD-{risk_level}",
        shipment_id=shipment.id,
        amount=amount,
        calculated_amount=amount,
        currency="USD",
        status="PENDING",
        risk_level=risk_level,
        risk_score=risk_score,
        latest_risk_snapshot_id=None,
    )
    session.add(intent)
    session.commit()
    return intent.id


def test_reconcile_low_risk_full_payout(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session, risk_level="LOW", amount=120.0)

    resp = client.post(
        f"/audit/payment_intents/{intent_id}/reconcile",
        json={"telemetry_data": {"max_temp_deviation": 1.0, "breach_duration_minutes": 5}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "FULL_PAYMENT"
    assert data["final_payout_amount"] == 120.0
    events = client.get(f"/chainpay/payment_intents/{intent_id}/settlement_events").json()
    assert events[-1]["event_type"] == "RECONCILED"

    get_resp = client.get(f"/audit/payment_intents/{intent_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["payout_confidence"] >= 95


def test_reconcile_high_risk_haircut(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session, risk_level="HIGH", amount=200.0)

    resp = client.post(
        f"/audit/payment_intents/{intent_id}/reconcile",
        json={"telemetry_data": {"max_temp_deviation": 3.0, "breach_duration_minutes": 120}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PARTIAL_SETTLEMENT"
    assert data["final_payout_amount"] < 200.0
    events = client.get(f"/chainpay/payment_intents/{intent_id}/settlement_events").json()
    assert events[-1]["event_type"] == "RECONCILED"


def test_reconcile_blocked_zero_payout(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session, risk_level="CRITICAL", amount=500.0)

    resp = client.post(
        f"/audit/payment_intents/{intent_id}/reconcile",
        json={"telemetry_data": {"max_temp_deviation": 10.0, "breach_duration_minutes": 300}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["final_payout_amount"] == 0.0
    assert data["status"] == "BLOCKED"


def test_event_bus_publishes_reconciled(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    events: list[dict] = []

    def handler(payload):
        events.append(payload)

    event_bus.subscribe(EventType.PAYMENT_INTENT_RECONCILED, handler)
    with SessionLocal() as session:
        intent_id = _seed_intent(session, risk_level="MEDIUM", amount=150.0)

    resp = client.post(
        f"/audit/payment_intents/{intent_id}/reconcile",
        json={"telemetry_data": {"max_temp_deviation": 2.0, "breach_duration_minutes": 60}},
    )
    assert resp.status_code == 200
    assert events, "reconciled event should be published"
    assert events[-1]["payment_intent_id"] == intent_id
