"""Gateway tests for the ChainPay settlement endpoints."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.routes.chainpay_context_risk import get_chainpay_db
from api.server import app
from chainpay_service.app.models import Base as ChainPayBase
from chainpay_service.app.models_context_ledger import ContextLedgerEntry


@pytest.fixture
def chainpay_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    ChainPayBase.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield TestingSession
    ChainPayBase.metadata.drop_all(bind=engine)


@pytest.fixture
def settlement_client(chainpay_session_factory):
    def override_get_chainpay_db():
        db = chainpay_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_chainpay_db] = override_get_chainpay_db
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        app.dependency_overrides.pop(get_chainpay_db, None)


def _insert_settlement_entry(session_factory, *, settlement_id: str, amount: float = 1000.0):
    session = session_factory()
    try:
        metadata = {
            "settlement": {
                "settlement_id": settlement_id,
                "amount": amount,
                "asset": "CB-USDx",
                "status": "PENDING",
            }
        }
        entry = ContextLedgerEntry(
            agent_id="CODY",
            gid="GID-01",
            role_tier=2,
            gid_hgp_version="1.1",
            decision_type="settlement_released",
            decision_status="APPROVE",
            shipment_id=f"SHIP-{settlement_id}",
            payer_id="payer",
            payee_id="carrier",
            amount=amount,
            currency="USD",
            corridor="US-MX",
            risk_score=55,
            reason_codes=json.dumps(["SETTLEMENT_RELEASED"]),
            policies_applied=json.dumps(["L1_CodeEqualsCash"]),
            economic_justification="auto_release",
            metadata_json=json.dumps(metadata),
        )
        session.add(entry)
        session.commit()
    finally:
        session.close()


def test_settle_onchain_endpoint_updates_metadata(settlement_client, chainpay_session_factory):
    _insert_settlement_entry(chainpay_session_factory, settlement_id="SET-GW-1", amount=1500.0)
    payload = {
        "settlement_id": "SET-GW-1",
        "carrier_wallet": "rCHAINPAY",
        "amount": 1500.0,
        "asset": "CB-USDx",
        "risk_band": "LOW",
        "trace_id": "ctx-trace-1",
        "memo": "daily-window",
    }

    response = settlement_client.post("/api/chainpay/settle-onchain", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["settlement_id"] == "SET-GW-1"
    assert body["status"] in {"SUBMITTED", "CONFIRMED"}

    session = chainpay_session_factory()
    try:
        entry = session.query(ContextLedgerEntry).filter(ContextLedgerEntry.shipment_id == "SHIP-SET-GW-1").first()
        metadata = json.loads(entry.metadata_json)
        block = metadata.get("settlement")
        assert block["carrier_wallet"] == "rCHAINPAY"
        assert block["tx_hash"] == body["tx_hash"]
    finally:
        session.close()


def test_get_settlement_endpoint_returns_snapshot(settlement_client, chainpay_session_factory):
    _insert_settlement_entry(chainpay_session_factory, settlement_id="SET-GW-DETAIL", amount=640.0)

    response = settlement_client.get("/api/chainpay/settlements/SET-GW-DETAIL")
    assert response.status_code == 200
    data = response.json()
    assert data["settlement_id"] == "SET-GW-DETAIL"
    assert data["amount"] == 640.0
    assert data["status"] in {"PENDING", "RELEASED", "ONCHAIN_CONFIRMED"}


def test_ack_endpoint_is_idempotent(settlement_client, chainpay_session_factory):
    _insert_settlement_entry(chainpay_session_factory, settlement_id="SET-GW-ACK", amount=220.0)
    payload = {"trace_id": "trace-ack", "consumer_id": "chainboard-ui", "notes": "first"}

    first = settlement_client.post("/api/chainpay/settlements/SET-GW-ACK/ack", json=payload)
    assert first.status_code == 200
    assert first.json()["ack_count"] == 1

    repeat = settlement_client.post("/api/chainpay/settlements/SET-GW-ACK/ack", json=payload)
    assert repeat.status_code == 200
    assert repeat.json()["ack_count"] == 1

    session = chainpay_session_factory()
    try:
        entry = session.query(ContextLedgerEntry).filter(ContextLedgerEntry.shipment_id == "SHIP-SET-GW-ACK").first()
        metadata = json.loads(entry.metadata_json)
        acks = metadata.get("acks")
        assert isinstance(acks, list)
        assert len(acks) == 1
        assert acks[0]["notes"] == "first"
    finally:
        session.close()
