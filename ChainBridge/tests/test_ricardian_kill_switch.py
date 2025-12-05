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


def test_kill_switch_sets_override(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, _ = client_with_db
    create_resp = client.post(
        "/legal/ricardian/instruments",
        json={
            "instrument_type": "BILL_OF_LADING",
            "physical_reference": "SHIP-KILL",
            "pdf_uri": "https://example.com/kill.pdf",
            "pdf_hash": "hashkill",
            "governing_law": "US_UCC_Article_7",
            "created_by": "tester",
        },
    )
    inst_id = create_resp.json()["id"]
    kill_resp = client.post(
        f"/legal/ricardian/instruments/{inst_id}/kill_switch",
        params={"event": "contract_hacked"},
    )
    assert kill_resp.status_code == 200
    body = kill_resp.json()
    assert body["status"] == "FROZEN"
    assert body["material_adverse_override"] is True
    assert "contract_hacked" in body["freeze_reason"]
