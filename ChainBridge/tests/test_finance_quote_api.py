from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
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


def test_financing_quote_not_found_without_instrument(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, _ = client_with_db
    resp = client.post("/finance/quote", json={"physical_reference": "SHIP-NO", "notional_value": "1000", "currency": "USD"})
    assert resp.status_code == 404


def test_financing_quote_active_instrument(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        session.add(
            RicardianInstrument(
                id="RIC-FIN",
                instrument_type="BILL_OF_LADING",
                physical_reference="SHIP-YES",
                pdf_uri="https://example.com/bol.pdf",
                pdf_hash="hash",
                ricardian_version="Ricardian_v1",
                governing_law="US_UCC_Article_7",
                status="ACTIVE",
                created_by="tester",
            )
        )
        session.commit()
    resp = client.post("/finance/quote", json={"physical_reference": "SHIP-YES", "notional_value": "1000", "currency": "USD"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["instrument_id"] == "RIC-FIN"
    assert body["max_advance_rate"] == 70
    assert body["max_advance_amount"] == 700
    assert "RICARDIAN_ACTIVE" in body["reason_codes"]


def test_financing_quote_low_band(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        session.add(
            RicardianInstrument(
                id="RIC-FIN-LOW",
                instrument_type="BILL_OF_LADING",
                physical_reference="SHIP-LOW",
                pdf_uri="https://example.com/bol.pdf",
                pdf_hash="hash",
                ricardian_version="v1.1",
                governing_law="US_UCC_Article_7",
                status="ACTIVE",
                created_by="tester",
            )
        )
        session.commit()
    resp = client.post(
        "/finance/quote",
        json={"physical_reference": "SHIP-LOW", "notional_value": "1000", "currency": "USD", "risk_band": "LOW"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["max_advance_rate"] == 80
    assert body["base_apr"] == 12


def test_financing_quote_high_band(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        session.add(
            RicardianInstrument(
                id="RIC-FIN-HIGH",
                instrument_type="BILL_OF_LADING",
                physical_reference="SHIP-HIGH",
                pdf_uri="https://example.com/bol.pdf",
                pdf_hash="hash",
                ricardian_version="v1.1",
                governing_law="US_UCC_Article_7",
                status="ACTIVE",
                created_by="tester",
            )
        )
        session.commit()
    resp = client.post(
        "/finance/quote",
        json={"physical_reference": "SHIP-HIGH", "notional_value": "1000", "currency": "USD", "risk_band": "HIGH"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["max_advance_rate"] == 50
    assert body["base_apr"] == 20
