from typing import Any, Tuple
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.models.chaindocs import Shipment
from api.models.chainiq import DocumentHealthSnapshot
from api.models.chainpay import PaymentIntent, SettlementEvent
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


def _seed(session) -> str:
    shipment = Shipment(id="SHIP-OC", corridor_code="CN-US", mode="OCEAN", incoterm="FOB")
    session.add(shipment)
    session.flush()
    snapshot = DocumentHealthSnapshot(
        shipment_id=shipment.id,
        corridor_code="CN-US",
        mode="OCEAN",
        incoterm="FOB",
        template_name="DEFAULT",
        present_count=1,
        missing_count=0,
        required_total=1,
        optional_total=0,
        blocking_gap_count=0,
        completeness_pct=100,
        risk_score=70,
        risk_level="MEDIUM",
        created_at=datetime.utcnow(),
    )
    session.add(snapshot)
    intent = PaymentIntent(
        id="PAY-OC",
        shipment_id=shipment.id,
        amount=1000.0,
        currency="USD",
        status="PENDING",
        risk_score=snapshot.risk_score,
        risk_level=snapshot.risk_level,
        latest_risk_snapshot_id=snapshot.id,
        intent_hash="hash",
    )
    session.add(intent)
    session.commit()
    return intent.id


def test_operator_queue(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _seed(session)
    resp = client.get("/operator/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["state"] in {"READY", "WAITING_PROOF", "BLOCKED"}


def test_risk_snapshot_endpoint(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed(session)
    resp = client.get(f"/operator/settlements/{intent_id}/risk_snapshot")
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent_id"] == intent_id
    assert data["risk_score"] == 70


def test_settlement_events_endpoint(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed(session)
        session.add(
            SettlementEvent(
                payment_intent_id=intent_id,
                event_type="CREATED",
                status="PENDING",
                amount=1000.0,
                currency="USD",
                occurred_at=datetime.utcnow(),
                sequence=1,
            )
        )
        session.commit()
    resp = client.get(f"/operator/settlements/{intent_id}/events")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "CREATED"
