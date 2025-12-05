"""Integration tests for the ChainDocs API endpoints."""

from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.server import app


@pytest.fixture(scope="module")
def client_with_db() -> Tuple[TestClient, Any]:
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

    yield client, engine

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def clean_database(client_with_db: Tuple[TestClient, Any]):
    """Ensure tables are reset between tests."""
    _, engine = client_with_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_get_dossier_returns_missing_when_no_shipment(
    client_with_db: Tuple[TestClient, Any],
) -> None:
    client, _ = client_with_db

    response = client.get("/chaindocs/shipments/SHIP-123/dossier")

    assert response.status_code == 200
    data = response.json()
    assert data["shipment_id"] == "SHIP-123"
    assert data["documents"] == []
    assert len(data["missing_documents"]) == 4


def test_post_document_then_get_dossier(client_with_db: Tuple[TestClient, Any]) -> None:
    client, _ = client_with_db

    payload = {
        "document_id": "DOC-1",
        "type": "BILL_OF_LADING",
        "status": "VERIFIED",
        "version": 2,
        "hash": "hash123",
        "mletr": True,
    }

    post_response = client.post("/chaindocs/shipments/SHIP-321/documents", json=payload)
    assert post_response.status_code == 200
    post_data = post_response.json()
    assert post_data["document_id"] == "DOC-1"
    assert post_data["status"] == "VERIFIED"

    dossier_response = client.get("/chaindocs/shipments/SHIP-321/dossier")
    assert dossier_response.status_code == 200
    dossier = dossier_response.json()
    assert dossier["shipment_id"] == "SHIP-321"
    assert len(dossier["documents"]) == 1
    assert dossier["documents"][0]["type"] == "BILL_OF_LADING"
    assert "PACKING_LIST" in dossier["missing_documents"]
