from datetime import datetime
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
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


def _create_payload() -> dict:
    return {
        "instrument_type": "BILL_OF_LADING",
        "physical_reference": "SHIP-LEGAL",
        "pdf_uri": "https://example.com/doc.pdf",
        "pdf_hash": "abc123hash",
        "governing_law": "US_UCC_Article_7",
        "created_by": "tester@example.com",
    }


def test_create_and_get_instrument(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, _ = client_with_db
    resp = client.post("/legal/ricardian/instruments", json=_create_payload())
    assert resp.status_code == 201
    body = resp.json()
    instrument_id = body["id"]
    assert body["status"] == "ACTIVE"
    get_resp = client.get(f"/legal/ricardian/instruments/{instrument_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == instrument_id
    by_physical = client.get(f"/legal/ricardian/instruments/by-physical/{body['physical_reference']}")
    assert by_physical.status_code == 200
    assert by_physical.json()["id"] == instrument_id


def test_update_and_freeze_flow(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, _ = client_with_db
    create_resp = client.post("/legal/ricardian/instruments", json=_create_payload())
    instrument_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/legal/ricardian/instruments/{instrument_id}",
        json={"smart_contract_address": "0xabc", "status": "TERMINATED"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["smart_contract_address"] == "0xabc"
    assert patch_resp.json()["status"] == "TERMINATED"

    freeze_resp = client.post(
        f"/legal/ricardian/instruments/{instrument_id}/freeze",
        params={"reason": "Court order"},
    )
    assert freeze_resp.status_code == 200
    assert freeze_resp.json()["status"] == "FROZEN"
    assert freeze_resp.json()["freeze_reason"] == "Court order"

    unfreeze_resp = client.post(f"/legal/ricardian/instruments/{instrument_id}/unfreeze")
    assert unfreeze_resp.status_code == 200
    assert unfreeze_resp.json()["status"] == "ACTIVE"
