from typing import Any, Tuple
from datetime import datetime
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.models.chaindocs import Shipment
from api.models.chainiq import DocumentHealthSnapshot
from api.models.chainpay import PaymentIntent
from api.server import app
from api.webhooks import security
from api.webhooks.security import reset_rate_limits


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
    reset_rate_limits()


def _seed_intent(session, risk: str = "LOW") -> str:
    shipment = Shipment(id="SHIP-WH", corridor_code="CN-US", mode="OCEAN")
    session.add(shipment)
    session.flush()
    snap = DocumentHealthSnapshot(
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
        risk_score=80,
        risk_level=risk,
    )
    session.add(snap)
    intent = PaymentIntent(
        id=f"PAY-WH-{risk}",
        shipment_id=shipment.id,
        amount=1000.0,
        currency="USD",
        status="PENDING",
        risk_level=risk,
        latest_risk_snapshot_id=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(intent)
    session.commit()
    return intent.id


def _signed_headers(payload: dict, secret: str) -> dict:
    body = json.dumps(payload)
    signature = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "X-ChainBridge-Signature": signature,
        "Content-Type": "application/json",
    }


def test_payment_status_webhook_creates_events(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session)

    resp = client.post(
        "/webhooks/settlement/payment_status",
        json={"payment_intent_id": intent_id, "external_status": "AUTHORIZED", "provider": "demo", "raw_payload": {}},
    )
    assert resp.status_code == 200
    events = client.get(f"/chainpay/payment_intents/{intent_id}/settlement_events").json()
    assert any(evt["event_type"] == "AUTHORIZED" for evt in events)


def test_payment_status_failed_path(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session, risk="HIGH")

    resp = client.post(
        "/webhooks/settlement/payment_status",
        json={"payment_intent_id": intent_id, "external_status": "FAILED", "provider": "demo", "raw_payload": {}},
    )
    assert resp.status_code == 200
    events = client.get(f"/chainpay/payment_intents/{intent_id}/settlement_events").json()
    assert events[-1]["event_type"] == "FAILED"


def test_proof_attached_webhook(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session)

    resp = client.post(
        "/webhooks/settlement/proof_attached",
        json={"payment_intent_id": intent_id, "proof_id": "PROOF-1", "provider": "demo"},
    )
    assert resp.status_code == 200
    events = client.get(f"/chainpay/payment_intents/{intent_id}/settlement_events").json()
    assert events[-1]["event_type"] == "PROOF_ATTACHED"


def test_webhook_missing_intent_returns_404(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, _ = client_with_db
    resp = client.post(
        "/webhooks/settlement/payment_status",
        json={"payment_intent_id": "NOPE", "external_status": "AUTHORIZED", "provider": "demo", "raw_payload": {}},
    )
    assert resp.status_code == 404


def test_webhook_signature_enforced_when_secret(client_with_db: Tuple[TestClient, Any, sessionmaker], monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session)

    secret = "supersecret"
    monkeypatch.setenv("CHAINBRIDGE_WEBHOOK_SECRET", secret)
    payload = {"payment_intent_id": intent_id, "external_status": "AUTHORIZED", "provider": "demo", "raw_payload": {}}
    headers = _signed_headers(payload, secret)

    ok = client.post("/webhooks/settlement/payment_status", data=json.dumps(payload), headers=headers)
    assert ok.status_code == 200

    missing = client.post("/webhooks/settlement/payment_status", data=json.dumps(payload))
    assert missing.status_code == 401
    monkeypatch.delenv("CHAINBRIDGE_WEBHOOK_SECRET", raising=False)


def test_webhook_rate_limit_blocks_repeats(client_with_db: Tuple[TestClient, Any, sessionmaker], monkeypatch: pytest.MonkeyPatch) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        intent_id = _seed_intent(session)

    monkeypatch.setattr(security, "RATE_LIMIT_COUNT", 2)
    monkeypatch.setattr(security, "RATE_LIMIT_WINDOW", 60)
    reset_rate_limits()
    payload = {"payment_intent_id": intent_id, "external_status": "AUTHORIZED", "provider": "demo", "raw_payload": {}}

    assert client.post("/webhooks/settlement/payment_status", json=payload).status_code == 200
    assert client.post("/webhooks/settlement/payment_status", json=payload).status_code == 200
    third = client.post("/webhooks/settlement/payment_status", json=payload)
    assert third.status_code == 429
