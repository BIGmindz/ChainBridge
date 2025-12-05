from datetime import datetime, timedelta
from typing import Any, Tuple

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


def _seed(session):
    shipment = Shipment(id="SHIP-OC2", corridor_code="CN-US", mode="OCEAN", incoterm="FOB")
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
        risk_score=65,
        risk_level="MEDIUM",
        created_at=datetime.utcnow(),
    )
    session.add(snapshot)
    intent = PaymentIntent(
        id="PAY-OC2",
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
    event = SettlementEvent(
        payment_intent_id=intent.id,
        event_type="CREATED",
        status="PENDING",
        amount=1000.0,
        currency="USD",
        occurred_at=datetime.utcnow() - timedelta(hours=1),
        sequence=1,
    )
    session.add(event)
    session.commit()
    return intent.id


def test_operator_queue_endpoint(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _seed(session)
    resp = client.get("/operator/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "PAY-OC2"
    assert data["items"][0]["has_ricardian_wrapper"] is False
    assert "recon_state" in data["items"][0]


def test_risk_snapshot_endpoint(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed(session)
    resp = client.get(f"/operator/settlements/{intent_id}/risk_snapshot")
    assert resp.status_code == 200
    data = resp.json()
    assert data["settlement_id"] == intent_id
    assert data["risk_band"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_settlement_events_timeline(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed(session)
    resp = client.get(f"/operator/settlements/{intent_id}/events")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["event_type"] == "CREATED"


def test_iot_health_summary(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, _ = client_with_db
    resp = client.get("/operator/iot/health/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "device_count_active" in body


def test_operator_events_stream_since(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed(session)
    since = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    resp = client.get(f"/operator/events/stream?since={since}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"]


def test_reconciliation_summary_endpoint(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed(session)
    resp = client.get(f"/operator/settlements/{intent_id}/reconciliation")
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] in {"AUTO_APPROVE", "PARTIAL_APPROVE", "BLOCK"}
    assert body["approved_amount"] > 0
    assert body["policy_id"]


def test_auditpack_missing_returns_404(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, _ = client_with_db
    resp = client.get("/operator/settlements/NOPE/auditpack")
    assert resp.status_code == 404


def test_auditpack_returns_data(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed(session)
    resp = client.get(f"/operator/settlements/{intent_id}/auditpack")
    assert resp.status_code == 200
    data = resp.json()
    assert data["settlement_id"] == intent_id
    assert data["core"]["amount"] == 1000.0
    assert data["source"] == "virtual_v1"
