"""Integration tests for the ChainPay API endpoints."""

from datetime import datetime
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.chaindocs_client import ChainDocsUnavailable
from api.database import Base, get_db
from api.models.chaindocs import Shipment
from api.models.chainiq import DocumentHealthSnapshot
from api.models.chainpay import PaymentIntent, SettlementEvent
from api.schemas.chaindocs import ChainDocsDocument
from api.server import app


@pytest.fixture(scope="module")
def client_with_db() -> Tuple[TestClient, Any, sessionmaker]:
    """Provide a TestClient wired to an in-memory SQLite database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
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
def clean_database(client_with_db: Tuple[TestClient, Any, sessionmaker]):
    """Ensure tables are reset between tests."""
    _, engine, _ = client_with_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _seed_shipment_with_risk(
    session: Session,
    shipment_id: str,
    *,
    corridor_code: str = "CN-US",
    mode: str = "OCEAN",
    risk_score: int = 80,
    risk_level: str = "MEDIUM",
) -> None:
    shipment = Shipment(id=shipment_id, corridor_code=corridor_code, mode=mode)
    session.add(shipment)
    session.flush()

    snapshot = DocumentHealthSnapshot(
        shipment_id=shipment_id,
        corridor_code=corridor_code,
        mode=mode,
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
    session.commit()


def _chaindocs_stub(proof_id: str) -> ChainDocsDocument:
    return ChainDocsDocument(
        document_id=proof_id,
        type="PROOF_PACK",
        status="PRESENT",
        version=1,
        hash="hash",
        mletr=False,
    )


def test_get_settlement_plan_bootstraps_default(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, _ = client_with_db

    response = client.get("/chainpay/shipments/SHIP-555/settlement_plan")

    assert response.status_code == 200
    data = response.json()
    assert data["shipment_id"] == "SHIP-555"
    assert len(data["milestones"]) == 3
    assert data["template_id"] == "EXPORT_STANDARD_V1"
    assert "doc_risk" in data
    assert isinstance(data["doc_risk"], dict)
    assert "missing_blocking_docs" in data["doc_risk"]


def test_post_settlement_plan_persists_data(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, _ = client_with_db

    payload = {
        "template_id": "CUSTOM_TEMPLATE",
        "total_value": 250000.0,
        "float_reduction_estimate": 0.95,
        "milestones": [
            {
                "event": "BOL_ISSUED",
                "payout_pct": 0.5,
                "status": "PAID",
                "paid_at": "2025-01-01T00:00:00Z",
            },
            {
                "event": "DELIVERED",
                "payout_pct": 0.5,
                "status": "PENDING",
                "paid_at": None,
            },
        ],
    }

    post_response = client.post("/chainpay/shipments/SHIP-777/settlement_plan", json=payload)
    assert post_response.status_code == 200
    post_data = post_response.json()
    assert post_data["template_id"] == "CUSTOM_TEMPLATE"
    assert post_data["total_value"] == 250000.0
    assert len(post_data["milestones"]) == 2
    assert post_data["doc_risk"]["level"]
    assert isinstance(post_data["doc_risk"]["missing_blocking_docs"], list)

    get_response = client.get("/chainpay/shipments/SHIP-777/settlement_plan")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["template_id"] == "CUSTOM_TEMPLATE"
    assert len(get_data["milestones"]) == 2
    assert get_data["milestones"][0]["event"] == "BOL_ISSUED"
    assert get_data["doc_risk"]["score"] <= 100
    assert "missing_blocking_docs" in get_data["doc_risk"]


def test_create_payment_intent_from_shipment(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _seed_shipment_with_risk(session, "SHIP-PAY-1", risk_score=72, risk_level="HIGH")

    payload = {
        "shipment_id": "SHIP-PAY-1",
        "amount": 125000.5,
        "currency": "USD",
        "counterparty": "ACME LOGISTICS",
    }

    response = client.post("/chainpay/payment_intents/from_shipment", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["shipment_id"] == "SHIP-PAY-1"
    assert data["currency"] == "USD"
    assert data["risk_level"] == "HIGH"
    assert data["status"] == "PENDING"
    assert data["counterparty"] == "ACME LOGISTICS"
    assert data["intent_hash"]
    assert abs(data["amount"] - 1286.4) < 0.01
    assert "pricing_breakdown" in data


def test_create_payment_intent_requires_existing_shipment_and_risk(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    payload = {
        "shipment_id": "SHIP-MISSING",
        "amount": 5000.0,
        "currency": "USD",
        "counterparty": "Missing Co",
    }

    missing_response = client.post("/chainpay/payment_intents/from_shipment", json=payload)
    assert missing_response.status_code == 404

    # Create shipment without risk snapshot to trigger 400
    with SessionLocal() as session:
        session.add(Shipment(id="SHIP-NO-RISK"))
        session.commit()

    bad_risk = client.post(
        "/chainpay/payment_intents/from_shipment",
        json={**payload, "shipment_id": "SHIP-NO-RISK"},
    )
    assert bad_risk.status_code == 400
    assert "risk snapshot" in bad_risk.json()["detail"].lower()


def test_attach_proof_pack_is_idempotent(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _seed_shipment_with_risk(session, "SHIP-PROOF-1")

    monkeypatch.setattr(
        "api.routes.chainpay.get_chaindocs_document",
        lambda proof_id, db=None: _chaindocs_stub(proof_id),
    )

    create_payload = {
        "shipment_id": "SHIP-PROOF-1",
        "amount": 5000.0,
        "currency": "USD",
        "counterparty": "Widgets Inc",
    }
    create_resp = client.post("/chainpay/payment_intents/from_shipment", json=create_payload)
    intent_id = create_resp.json()["id"]

    attach_payload = {"proof_pack_id": "PROOF-123"}
    first_attach = client.post(f"/chainpay/payment_intents/{intent_id}/attach_proof", json=attach_payload)
    assert first_attach.status_code == 200
    assert first_attach.json()["proof_pack_id"] == "PROOF-123"

    second_attach = client.post(f"/chainpay/payment_intents/{intent_id}/attach_proof", json=attach_payload)
    assert second_attach.status_code == 200
    assert second_attach.json()["proof_pack_id"] == "PROOF-123"

    conflicting = client.post(
        f"/chainpay/payment_intents/{intent_id}/attach_proof",
        json={"proof_pack_id": "PROOF-456"},
    )
    assert conflicting.status_code == 409


def test_attach_proof_conflict_across_intents(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _seed_shipment_with_risk(session, "SHIP-PROOF-A")
        _seed_shipment_with_risk(session, "SHIP-PROOF-B")

    monkeypatch.setattr(
        "api.routes.chainpay.get_chaindocs_document",
        lambda proof_id, db=None: _chaindocs_stub(proof_id),
    )

    def create_intent(shipment_id: str) -> str:
        resp = client.post(
            "/chainpay/payment_intents/from_shipment",
            json={
                "shipment_id": shipment_id,
                "amount": 5000.0,
                "currency": "USD",
                "counterparty": f"CP-{shipment_id}",
            },
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    primary = create_intent("SHIP-PROOF-A")
    secondary = create_intent("SHIP-PROOF-B")

    ok_attach = client.post(
        f"/chainpay/payment_intents/{primary}/attach_proof",
        json={"proof_pack_id": "PROOF-SHARED"},
    )
    assert ok_attach.status_code == 200

    conflict = client.post(
        f"/chainpay/payment_intents/{secondary}/attach_proof",
        json={"proof_pack_id": "PROOF-SHARED"},
    )
    assert conflict.status_code == 409


def test_attach_proof_handles_missing_and_upstream_errors(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _seed_shipment_with_risk(session, "SHIP-PROOF-ERR")

    missing_intent = client.post(
        "/chainpay/payment_intents/from_shipment",
        json={
            "shipment_id": "SHIP-PROOF-ERR",
            "amount": 1000.0,
            "currency": "USD",
            "counterparty": "Widgets Inc",
        },
    )
    assert missing_intent.status_code == 201
    intent_id = missing_intent.json()["id"]

    # 404 when ChainDocs cannot find proof
    monkeypatch.setattr("api.routes.chainpay.get_chaindocs_document", lambda proof_id, db=None: None)
    missing = client.post(
        f"/chainpay/payment_intents/{intent_id}/attach_proof",
        json={"proof_pack_id": "UNKNOWN-PROOF"},
    )
    assert missing.status_code == 404

    # 503 when ChainDocs is unavailable
    def _boom(_, db=None):
        raise ChainDocsUnavailable("unavailable")

    monkeypatch.setattr("api.routes.chainpay.get_chaindocs_document", _boom)
    upstream = client.post(
        f"/chainpay/payment_intents/{intent_id}/attach_proof",
        json={"proof_pack_id": "ANY-PROOF"},
    )
    assert upstream.status_code == 503


def test_list_payment_intents_filters_and_flags(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, SessionLocal = client_with_db
    monkeypatch.setattr(
        "api.routes.chainpay.get_chaindocs_document",
        lambda proof_id, db=None: _chaindocs_stub(proof_id),
    )
    with SessionLocal() as session:
        _seed_shipment_with_risk(
            session,
            "SHIP-LIST-1",
            corridor_code="CN-US",
            mode="OCEAN",
            risk_level="LOW",
        )
        _seed_shipment_with_risk(
            session,
            "SHIP-LIST-2",
            corridor_code="DE-UK",
            mode="AIR",
            risk_level="MEDIUM",
        )

    def create_intent(shipment_id: str, proof: bool = False, status: str = "PENDING") -> str:
        resp = client.post(
            "/chainpay/payment_intents/from_shipment",
            json={
                "shipment_id": shipment_id,
                "amount": 10000.0,
                "currency": "USD",
                "counterparty": f"CP-{shipment_id}",
            },
        )
        assert resp.status_code == 201
        intent_id = resp.json()["id"]
        if proof:
            attach = client.post(
                f"/chainpay/payment_intents/{intent_id}/attach_proof",
                json={"proof_pack_id": f"PROOF-{shipment_id}"},
            )
            assert attach.status_code == 200
        if status != "PENDING":
            with SessionLocal() as session_local:
                intent = session_local.query(PaymentIntent).filter_by(id=intent_id).first()
                intent.status = status
                session_local.commit()
        return intent_id

    intent_with_proof = create_intent("SHIP-LIST-1", proof=True)
    _ = create_intent("SHIP-LIST-2", proof=False, status="AUTHORIZED")

    list_resp = client.get("/chainpay/payment_intents")
    assert list_resp.status_code == 200
    payloads = list_resp.json()
    assert any(item["id"] == intent_with_proof and item["proof_attached"] for item in payloads)
    ready_items = {item["id"]: item for item in payloads}
    assert ready_items[intent_with_proof]["ready_for_payment"] is True
    assert ready_items[intent_with_proof]["has_proof"] is True

    filtered = client.get("/chainpay/payment_intents", params={"corridor_code": "CN-US"})
    assert filtered.status_code == 200
    filtered_items = filtered.json()
    assert all(item["corridor_code"] == "CN-US" for item in filtered_items)

    has_proof_filtered = client.get("/chainpay/payment_intents", params={"has_proof": True})
    assert has_proof_filtered.status_code == 200
    assert all(item["has_proof"] is True for item in has_proof_filtered.json())

    ready_filtered = client.get("/chainpay/payment_intents", params={"ready_for_payment": True})
    assert ready_filtered.status_code == 200
    assert all(item["ready_for_payment"] is True for item in ready_filtered.json())


def test_intent_hash_changes_on_amount(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _seed_shipment_with_risk(session, "SHIP-HASH", risk_score=60, risk_level="LOW")
        _seed_shipment_with_risk(session, "SHIP-HASH-2", risk_score=60, risk_level="LOW")

    payload1 = {
        "shipment_id": "SHIP-HASH",
        "amount": 1000.0,
        "currency": "USD",
        "counterparty": "Hash Co",
    }
    resp1 = client.post("/chainpay/payment_intents/from_shipment", json=payload1)
    assert resp1.status_code == 201
    hash1 = resp1.json()["intent_hash"]

    payload2 = {**payload1, "shipment_id": "SHIP-HASH-2", "amount": 2000.0}
    resp2 = client.post("/chainpay/payment_intents/from_shipment", json=payload2)
    assert resp2.status_code == 201
    hash2 = resp2.json()["intent_hash"]
    assert hash1 != hash2


def test_payment_intent_summary_counts(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _seed_shipment_with_risk(session, "SHIP-SUM-READY", risk_level="LOW")
        _seed_shipment_with_risk(session, "SHIP-SUM-BLOCK", risk_level="HIGH")

    monkeypatch.setattr(
        "api.routes.chainpay.get_chaindocs_document",
        lambda proof_id, db=None: _chaindocs_stub(proof_id),
    )

    ready_resp = client.post(
        "/chainpay/payment_intents/from_shipment",
        json={
            "shipment_id": "SHIP-SUM-READY",
            "amount": 1000.0,
            "currency": "USD",
            "counterparty": "Ready Co",
        },
    )
    blocked_resp = client.post(
        "/chainpay/payment_intents/from_shipment",
        json={
            "shipment_id": "SHIP-SUM-BLOCK",
            "amount": 2000.0,
            "currency": "USD",
            "counterparty": "Block Co",
        },
    )
    assert ready_resp.status_code == 201
    assert blocked_resp.status_code == 201

    ready_id = ready_resp.json()["id"]
    attach = client.post(
        f"/chainpay/payment_intents/{ready_id}/attach_proof",
        json={"proof_pack_id": "PROOF-READY"},
    )
    assert attach.status_code == 200

    summary = client.get("/chainpay/payment_intents/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert data["total"] == 2
    assert data["awaiting_proof"] == 1
    assert data["ready_for_payment"] == 1
    assert data["blocked_by_risk"] == 1
