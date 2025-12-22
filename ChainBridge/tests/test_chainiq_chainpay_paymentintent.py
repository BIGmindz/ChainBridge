"""End-to-end tests for ChainIQ -> ChainPay PaymentIntent autowire."""

from datetime import datetime
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.models.chaindocs import Document, Shipment
from api.models.chainiq import DocumentHealthSnapshot
from api.models.chainpay import PaymentIntent, SettlementPlan
from api.server import app


@pytest.fixture(scope="module")
def client_with_db() -> Tuple[TestClient, Any, sessionmaker]:
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

    yield client, engine, TestingSessionLocal

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def clean_database(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    """Ensure tables are reset between tests."""
    _, engine, _ = client_with_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _seed_low_risk_shipment(session: Session, shipment_id: str, amount: float = 50000.0) -> None:
    """Insert shipment, plan, and complete docs to yield a LOW/MEDIUM risk level."""
    shipment = Shipment(id=shipment_id, corridor_code="CN-US", mode="OCEAN", incoterm="FOB")
    session.add(shipment)
    plan = SettlementPlan(
        id=f"PLAN-{shipment_id}",
        shipment_id=shipment_id,
        template_id="EXPORT_STANDARD_V1",
        total_value=amount,
        float_reduction_estimate=0.99,
    )
    session.add(plan)
    session.flush()

    documents = [
        Document(
            id=f"{shipment_id}-BOL",
            shipment_id=shipment_id,
            type="BILL_OF_LADING",
            status="VERIFIED",
            current_version=1,
            hash="hash-bol",
            latest_hash="hash-bol",
            mletr=True,
        ),
        Document(
            id=f"{shipment_id}-CI",
            shipment_id=shipment_id,
            type="COMMERCIAL_INVOICE",
            status="PRESENT",
            current_version=1,
            hash="hash-ci",
            latest_hash="hash-ci",
            mletr=False,
        ),
        Document(
            id=f"{shipment_id}-PKL",
            shipment_id=shipment_id,
            type="PACKING_LIST",
            status="PRESENT",
            current_version=1,
            hash="hash-pkl",
            latest_hash="hash-pkl",
            mletr=False,
        ),
        Document(
            id=f"{shipment_id}-INS",
            shipment_id=shipment_id,
            type="INSURANCE_CERTIFICATE",
            status="PRESENT",
            current_version=1,
            hash="hash-ins",
            latest_hash="hash-ins",
            mletr=False,
        ),
    ]
    session.add_all(documents)
    session.commit()


def _seed_high_risk_shipment(session: Session, shipment_id: str) -> None:
    """Insert a shipment with no documents to force a CRITICAL risk result."""
    shipment = Shipment(id=shipment_id, corridor_code="DE-UK", mode="AIR", incoterm="CIF")
    session.add(shipment)
    session.commit()


def test_risk_approval_creates_payment_intent(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _seed_low_risk_shipment(session, "SHIP-AUTO-OK", amount=75000.0)

    resp = client.get("/chainiq/shipments/SHIP-AUTO-OK/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["risk"]["level"] in {"LOW", "MEDIUM"}

    with SessionLocal() as session:
        intent = session.query(PaymentIntent).filter_by(shipment_id="SHIP-AUTO-OK").first()
        snapshot = (
            session.query(DocumentHealthSnapshot)
            .filter_by(shipment_id="SHIP-AUTO-OK")
            .order_by(DocumentHealthSnapshot.created_at.desc(), DocumentHealthSnapshot.id.desc())
            .first()
        )

        assert intent is not None
        assert snapshot is not None
        assert intent.latest_risk_snapshot_id == snapshot.id
        assert intent.amount == pytest.approx(75000.0)
        assert intent.currency == "USD"
        assert intent.risk_level == snapshot.risk_level


def test_risk_rejection_does_not_create_payment_intent(
    client_with_db: Tuple[TestClient, Any, sessionmaker],
) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        _seed_high_risk_shipment(session, "SHIP-AUTO-NOPE")

    resp = client.get("/chainiq/shipments/SHIP-AUTO-NOPE/health")
    assert resp.status_code == 200
    assert resp.json()["risk"]["level"] in {"HIGH", "CRITICAL"}

    with SessionLocal() as session:
        count = session.query(PaymentIntent).filter_by(shipment_id="SHIP-AUTO-NOPE").count()
        assert count == 0
