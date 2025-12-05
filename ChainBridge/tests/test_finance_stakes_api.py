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


def test_create_stake_requires_active_instrument(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        session.add(
            RicardianInstrument(
                id="RIC-FIN2",
                instrument_type="BILL_OF_LADING",
                physical_reference="SHIP-FIN2",
                pdf_uri="https://example.com/bol.pdf",
                pdf_hash="hash",
                ricardian_version="Ricardian_v1",
                governing_law="US_UCC_Article_7",
                status="ACTIVE",
                created_by="tester",
            )
        )
        session.commit()
    resp = client.post(
        "/finance/stakes",
        json={
            "physical_reference": "SHIP-FIN2",
            "notional_value": "1000",
            "principal_amount": "600",
            "currency": "USD",
            "applied_advance_rate": 60,
            "base_apr": 12,
            "risk_adjusted_apr": 12,
            "created_by": "qa",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["physical_reference"] == "SHIP-FIN2"
    assert body["principal_amount"] == 600
    list_resp = client.get("/finance/stakes/by-physical/SHIP-FIN2")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
