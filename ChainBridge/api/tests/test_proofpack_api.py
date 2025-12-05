"""
Tests for the ProofPack API endpoint.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from api.server import app
from chainpay_service.app.database import SessionLocal, init_db
from chainpay_service.app.models import (
    MilestoneSettlement,
    PaymentIntent,
    PaymentStatus,
    RiskTier,
)
from core.payments.identity import canonical_milestone_id, canonical_shipment_reference

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_chainpay_db():
    """Ensure ChainPay tables exist and are cleared for each test."""
    init_db()
    db = SessionLocal()
    try:
        db.query(MilestoneSettlement).delete()
        db.query(PaymentIntent).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def chainpay_milestone():
    """Seed a real milestone in the ChainPay database."""
    db = SessionLocal()
    try:
        intent = PaymentIntent(
            freight_token_id=1001,
            amount=100000.0,
            currency="USD",
            description="Acme Electronics",
            risk_score=0.1,
            risk_category="low",
            risk_tier=RiskTier.LOW,
            status=PaymentStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db.add(intent)
        db.commit()
        db.refresh(intent)

        shipment_ref = canonical_shipment_reference(shipment_reference=None, freight_token_id=intent.freight_token_id)
        milestone_id = canonical_milestone_id(shipment_ref, 1)
        milestone = MilestoneSettlement(
            payment_intent_id=intent.id,
            event_type="POD_CONFIRMED",
            amount=50000.0,
            currency=intent.currency,
            status=PaymentStatus.APPROVED,
            provider="INTERNAL_LEDGER",
            milestone_identifier=milestone_id,
            shipment_reference=shipment_ref,
            freight_token_id=intent.freight_token_id,
        )
        db.add(milestone)
        db.commit()
        yield milestone_id
    finally:
        db.close()


def test_proofpack_known_milestone_uses_real_fields(chainpay_milestone):
    response = client.get(f"/api/chainboard/payments/proofpack/{chainpay_milestone}")
    assert response.status_code == 200

    data = response.json()
    assert data["milestone_id"] == chainpay_milestone
    assert data["shipment_reference"] == "SHP-1001"
    assert data["amount"] == 50000.0
    assert data["currency"] == "USD"
    assert data["state"] == "approved"
    assert data["freight_token_id"] == 1001
    assert data["documents"] and data["documents"][0]["source"] == "mock"
    assert data["iot_signals"] and data["iot_signals"][0]["source"] == "mock"
    assert data["risk_assessment"]["source"] == "mock"
    assert data["audit_trail"][0]["source"] == "mock"


def test_get_proofpack_not_found():
    response = client.get("/api/chainboard/payments/proofpack/SHP-9999-M1")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_proofpack_bad_format():
    response = client.get("/api/chainboard/payments/proofpack/invalid-id")
    assert response.status_code == 400
    assert "<shipment_reference>-M<index>" in response.json()["detail"]
