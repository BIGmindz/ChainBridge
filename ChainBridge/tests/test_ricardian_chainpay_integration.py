from datetime import datetime
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.models.chaindocs import Shipment
from api.models.chainiq import DocumentHealthSnapshot
from api.models.legal import RicardianInstrument
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


def _seed_env(session) -> str:
    shipment = Shipment(id="SHIP-FRZ", corridor_code="CN-US", mode="OCEAN", incoterm="FOB")
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
    return shipment.id


def test_payment_intent_creation_blocked_by_frozen_instrument(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        shipment_id = _seed_env(session)
        session.add(
            RicardianInstrument(
                id="RIC-1",
                instrument_type="BILL_OF_LADING",
                physical_reference=shipment_id,
                pdf_uri="https://example.com/legal.pdf",
                pdf_hash="deadbeef",
                ricardian_version="Ricardian_v1",
                governing_law="US_UCC_Article_7",
                status="FROZEN",
                created_by="tester",
            )
        )
        session.commit()
    resp = client.post(
        "/chainpay/payment_intents/from_shipment",
        json={
            "shipment_id": "SHIP-FRZ",
            "amount": 1000,
            "currency": "USD",
            "counterparty": "ACME",
            "notes": None,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "RICARDIAN_INSTRUMENT_FROZEN" in data.get("compliance_blocks", [])
    assert data["risk_gate_reason"] == "Ricardian instrument frozen"
