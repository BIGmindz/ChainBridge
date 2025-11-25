from datetime import datetime
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.events.bus import EventType, event_bus
from api.models.chaindocs import Shipment
from api.models.chainiq import DocumentHealthSnapshot
from api.models.chainpay import PaymentIntent, StakeJob
from api.models.chainstake import StakePosition
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
    event_bus.clear_subscribers()
    reset_rate_limits = None


def _seed_intent(session, shipment_id: str) -> str:
    intent = PaymentIntent(
        id=f"PAY-STAKE-{shipment_id}",
        shipment_id=shipment_id,
        amount=100.0,
        currency="USD",
        status="PENDING",
        risk_level="LOW",
        risk_score=10,
        latest_risk_snapshot_id=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(intent)
    session.commit()
    return intent.id


def _seed_shipment(session) -> str:
    shipment = Shipment(id="SHIP-STAKE", corridor_code="CN-US", mode="OCEAN")
    session.add(shipment)
    session.flush()
    snapshot = DocumentHealthSnapshot(
        shipment_id=shipment.id,
        corridor_code="CN-US",
        mode="OCEAN",
        incoterm=None,
        template_name="DEFAULT",
        present_count=1,
        missing_count=0,
        required_total=1,
        optional_total=0,
        blocking_gap_count=0,
        completeness_pct=100,
        risk_score=10,
        risk_level="LOW",
        created_at=datetime.utcnow(),
    )
    session.add(snapshot)
    session.commit()
    return shipment.id


def test_create_and_complete_stake_job(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        shipment_id = _seed_shipment(session)
        intent_id = _seed_intent(session, shipment_id)

    events: list[dict] = []
    event_bus.subscribe(EventType.STAKE_CREATED, lambda payload: events.append({"created": payload}))
    event_bus.subscribe(EventType.STAKE_COMPLETED, lambda payload: events.append({"completed": payload}))

    resp = client.post(f"/stake/shipments/{shipment_id}", json={"requested_amount": 50.0, "payment_intent_id": intent_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["settled_amount"] == 50.0
    assert events, "stake events should be emitted"
    events_resp = client.get(f"/chainpay/payment_intents/{intent_id}/settlement_events")
    assert events_resp.status_code == 200
    assert any(evt["event_type"] == "STAKE_COMPLETED" for evt in events_resp.json())


def test_list_and_get_jobs(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        shipment_id = _seed_shipment(session)
    resp = client.post(f"/stake/shipments/{shipment_id}", json={"requested_amount": 75.0, "auto_execute": False})
    assert resp.status_code == 200
    job_id = resp.json()["id"]

    list_resp = client.get("/stake/jobs")
    assert list_resp.status_code == 200
    assert any(job["id"] == job_id for job in list_resp.json())

    detail = client.get(f"/stake/jobs/{job_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == job_id


def test_chainstake_analytics_endpoints(client_with_db: Tuple[TestClient, Any, sessionmaker]) -> None:
    client, _, SessionLocal = client_with_db
    with SessionLocal() as session:
        now = datetime.utcnow()
        session.add_all(
            [
                StakePosition(
                    id="POS-1",
                    shipment_id="SHIP-A",
                    payment_intent_id="PAY-A",
                    pool_id="POOL-X",
                    corridor="CN-US",
                    notional_usd=1000.0,
                    staked_at=now,
                    expected_maturity_at=now,
                    realized_apy=9.0,
                    status="STAKING_IN_POOL",
                    risk_level="LOW",
                ),
                StakePosition(
                    id="POS-2",
                    shipment_id="SHIP-B",
                    payment_intent_id="PAY-B",
                    pool_id="POOL-Y",
                    corridor="EU-UK",
                    notional_usd=500.0,
                    staked_at=now,
                    expected_maturity_at=now,
                    realized_apy=8.0,
                    status="FAILED",
                    risk_level="HIGH",
                ),
            ]
        )
        session.commit()

    ov = client.get("/stake/overview")
    assert ov.status_code == 200
    overview = ov.json()
    assert overview["total_tvl_usd"] >= overview["total_utilized_usd"]

    pools_resp = client.get("/stake/pools")
    assert pools_resp.status_code == 200
    pools = pools_resp.json()
    assert len(pools) == 2

    positions_resp = client.get("/stake/pools/POOL-X/positions")
    assert positions_resp.status_code == 200
    assert positions_resp.json()
