from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.chaindocs_hashing import compute_sha256, store_document
from api.database import Base, get_db
from api.events.bus import EventType, event_bus
from api.models.chaindocs import Document, Shipment
from api.models.chainpay import PaymentIntent
from api.server import app


@pytest.fixture(scope="module")
def client_with_db():
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
def clean_db(client_with_db):
    _, engine, _ = client_with_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    event_bus.clear_subscribers()


def test_compute_sha256():
    data = b"hello world"
    assert compute_sha256(data) == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_verify_document_success(client_with_db):
    client, _, SessionLocal = client_with_db
    content = b"signed document bytes"
    sha = compute_sha256(content)
    backend, ref = store_document(content, "doc1.bin")
    with SessionLocal() as session:
        shipment = Shipment(id="SHIP-HASH", corridor_code="CN-US", mode="OCEAN")
        session.add(shipment)
        session.flush()
        intent = PaymentIntent(
            id="PAY-HASH",
            shipment_id=shipment.id,
            amount=100.0,
            currency="USD",
            status="PENDING",
            risk_level="LOW",
            risk_score=10,
            proof_hash=sha,
        )
        session.add(intent)
        doc = Document(
            id="DOC-1",
            shipment_id=shipment.id,
            type="PROOF_PACK",
            status="PRESENT",
            current_version=1,
            hash=sha,
            latest_hash=sha,
            sha256_hex=sha,
            storage_backend=backend,
            storage_ref=ref,
        )
        session.add(doc)
        session.commit()

    resp = client.post("/chaindocs/documents/DOC-1/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["linked_payment_intents"][0]["id"] == "PAY-HASH"


def test_verify_document_detects_tamper(client_with_db, tmp_path: Path):
    client, _, SessionLocal = client_with_db
    content = b"immutable doc"
    sha = compute_sha256(content)
    backend, ref = store_document(content, "doc2.bin")
    # Tamper file
    Path(ref).write_bytes(b"tampered")
    with SessionLocal() as session:
        shipment = Shipment(id="SHIP-TAMPER", corridor_code="CN-US", mode="OCEAN")
        session.add(shipment)
        session.flush()
        doc = Document(
            id="DOC-2",
            shipment_id=shipment.id,
            type="PROOF_PACK",
            status="PRESENT",
            current_version=1,
            hash=sha,
            latest_hash=sha,
            sha256_hex=sha,
            storage_backend=backend,
            storage_ref=ref,
        )
        session.add(doc)
        session.commit()

    events = []
    event_bus.subscribe(EventType.DOCUMENT_VERIFIED, lambda payload: events.append(payload))
    resp = client.post("/chaindocs/documents/DOC-2/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert events and events[-1]["valid"] is False
