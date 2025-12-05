"""Gateway tests for the ChainPay context-ledger risk feed endpoint."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.server import app
from api.routes.chainpay_context_risk import get_chainpay_db
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
def gateway_client(chainpay_session_factory):
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


def _record_entry(session_factory, *, shipment_id: str, status: str, metadata: dict | None, score: int):
    session = session_factory()
    try:
        entry = ContextLedgerEntry(
            agent_id="CODY",
            gid="GID-01",
            role_tier=2,
            gid_hgp_version="1.2.3",
            decision_type="settlement_precheck",
            decision_status=status,
            shipment_id=shipment_id,
            payer_id="payer_co",
            payee_id="carrier_inc",
            amount=125000.0,
            currency="USD",
            corridor="US-BR",
            risk_score=score,
            reason_codes=json.dumps(["REVERSAL_EVENT"]),
            policies_applied=json.dumps(["L3_SecurityOverSpeed"]),
            economic_justification="context_risk_panel",
            metadata_json=json.dumps(metadata or {}),
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
    finally:
        session.close()


def test_gateway_returns_risk_feed(gateway_client, chainpay_session_factory):
    _record_entry(
        chainpay_session_factory,
        shipment_id="SHIP-900",
        status="FREEZE",
        metadata={
            "risk_snapshot": {
                "risk_score": 0.94,
                "risk_band": "CRITICAL",
                "reason_codes": ["REVERSAL_EVENT"],
                "trace_id": "ctx-risk-900",
                "model_version": "context-ledger-risk-v1",
            }
        },
        score=95,
    )
    _record_entry(
        chainpay_session_factory,
        shipment_id="SHIP-901",
        status="APPROVE",
        metadata=None,
        score=10,
    )

    response = gateway_client.get("/api/chainpay/context-ledger/risk?limit=5")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert len(payload["items"]) == 2
    latest = payload["items"][0]
    assert latest["shipment_id"] == "SHIP-901"
    assert latest["risk"] is None

    older = payload["items"][1]
    assert older["shipment_id"] == "SHIP-900"
    assert older["risk"]["risk_band"] == "CRITICAL"
    assert older["risk"]["trace_id"] == "ctx-risk-900"


def test_gateway_respects_limit(gateway_client, chainpay_session_factory):
    for idx in range(4):
        _record_entry(
            chainpay_session_factory,
            shipment_id=f"SHIP-LIMIT-{idx}",
            status="APPROVE",
            metadata=None,
            score=idx * 5,
        )

    response = gateway_client.get("/api/chainpay/context-ledger/risk?limit=2")
    assert response.status_code == 200
    payload = response.json()
    ids = [item["shipment_id"] for item in payload["items"]]
    assert ids == ["SHIP-LIMIT-3", "SHIP-LIMIT-2"]
