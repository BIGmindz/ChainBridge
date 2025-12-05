from datetime import datetime, timedelta
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.models.chaindocs import Shipment
from api.models.chainiq import DocumentHealthSnapshot
from api.models.chainpay import PaymentIntent
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


def test_auditpack_includes_legal_wrapper(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        shipment = Shipment(id="SHIP-AUD", corridor_code="US-MX", mode="TRUCK", incoterm="DAP")
        session.add(shipment)
        session.flush()
        snapshot = DocumentHealthSnapshot(
            shipment_id=shipment.id,
            corridor_code="US-MX",
            mode="TRUCK",
            incoterm="DAP",
            template_name="DEFAULT",
            present_count=1,
            missing_count=0,
            required_total=1,
            optional_total=0,
            blocking_gap_count=0,
            completeness_pct=100,
            risk_score=70,
            risk_level="MEDIUM",
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
        session.add(snapshot)
        intent = PaymentIntent(
            id="PAY-AUD",
            shipment_id=shipment.id,
            amount=5000.0,
            currency="USD",
            status="PENDING",
            risk_score=snapshot.risk_score,
            risk_level=snapshot.risk_level,
            latest_risk_snapshot_id=snapshot.id,
            intent_hash="hash",
        )
        session.add(intent)
        session.add(
            RicardianInstrument(
                id="RIC-AUD",
                instrument_type="BILL_OF_LADING",
                physical_reference=shipment.id,
                pdf_uri="https://example.com/bol.pdf",
                pdf_hash="deadbeef",
                ricardian_version="Ricardian_v1",
                governing_law="US_UCC_Article_7",
                status="ACTIVE",
                created_by="tester",
            )
        )
        session.commit()

    resp = client.get("/operator/settlements/PAY-AUD/auditpack")
    assert resp.status_code == 200
    data = resp.json()
    assert data["legal_wrapper"]["instrument_id"] == "RIC-AUD"
    assert data["legal_wrapper"]["physical_reference"] == "SHIP-AUD"
