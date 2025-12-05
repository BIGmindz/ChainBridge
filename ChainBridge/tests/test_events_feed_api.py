from datetime import datetime, timedelta, timezone
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.events.audit_log import audit_sink
from api.events.bus import EventType, event_bus
from api.models.chainpay import SettlementEventAudit
from api.server import app
from api.sla.metrics import update_metric


@pytest.fixture(scope="module")
def client_with_db() -> Tuple[TestClient, sessionmaker]:
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
    audit_sink.set_session_factory(TestingSessionLocal)
    client = TestClient(app)

    yield client, TestingSessionLocal

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def clean_tables(client_with_db: Tuple[TestClient, sessionmaker]):
    _, SessionLocal = client_with_db
    with SessionLocal() as session:
        session.query(SettlementEventAudit).delete()
        session.commit()
    event_bus.clear_subscribers()


def _iso_to_dt(value: str) -> datetime:
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value)


def test_settlement_feed_orders_and_paginates(
    client_with_db: Tuple[TestClient, sessionmaker],
) -> None:
    client, _ = client_with_db
    now = datetime.now(timezone.utc)
    event_bus.publish(
        EventType.PAYMENT_INTENT_CREATED,
        {
            "id": "PI-1",
            "shipment_id": "SHIP-1",
            "status": "PENDING",
            "risk_level": "LOW",
        },
        actor="api",
        occurred_at=now - timedelta(minutes=5),
    )
    event_bus.publish(
        EventType.SETTLEMENT_EVENT_APPENDED,
        {
            "payment_intent_id": "PI-2",
            "shipment_id": "SHIP-2",
            "event_type": "AUTHORIZED",
            "status": "SUCCESS",
        },
        actor="worker:sync",
        occurred_at=now - timedelta(minutes=3),
    )
    event_bus.publish(
        EventType.PAYMENT_INTENT_UPDATED,
        {
            "id": "PI-3",
            "shipment_id": "SHIP-3",
            "status": "PAID",
            "risk_level": "LOW",
            "ready_for_payment": True,
        },
        actor="worker:sync",
        occurred_at=now - timedelta(minutes=1),
    )

    first_page = client.get("/events/settlement_feed", params={"limit": 2})
    assert first_page.status_code == 200
    data = first_page.json()
    assert len(data["items"]) == 2
    timestamps = [_iso_to_dt(item["occurred_at"]) for item in data["items"]]
    assert timestamps == sorted(timestamps, reverse=True)
    cursor = data["next_cursor"]
    assert cursor

    second_page = client.get("/events/settlement_feed", params={"cursor": cursor, "limit": 2})
    assert second_page.status_code == 200
    second_data = second_page.json()
    assert len(second_data["items"]) == 1
    returned_ids = {item["id"] for item in data["items"]} | {item["id"] for item in second_data["items"]}
    assert len(returned_ids) == 3


def test_feed_filters_by_payment_intent_and_shipment(
    client_with_db: Tuple[TestClient, sessionmaker],
) -> None:
    client, _ = client_with_db
    now = datetime.now(timezone.utc)
    event_bus.publish(
        EventType.PAYMENT_INTENT_CREATED,
        {
            "id": "PI-1",
            "shipment_id": "SHIP-1",
            "status": "PENDING",
            "risk_level": "LOW",
        },
        actor="api",
        occurred_at=now - timedelta(minutes=5),
    )
    event_bus.publish(
        EventType.SETTLEMENT_EVENT_APPENDED,
        {
            "payment_intent_id": "PI-2",
            "shipment_id": "SHIP-2",
            "event_type": "AUTHORIZED",
            "status": "SUCCESS",
        },
        actor="worker:sync",
        occurred_at=now - timedelta(minutes=4),
    )
    event_bus.publish(
        EventType.PAYMENT_INTENT_UPDATED,
        {"id": "PI-1", "shipment_id": "SHIP-1", "status": "PAID", "risk_level": "LOW"},
        actor="worker:sync",
        occurred_at=now - timedelta(minutes=3),
    )

    filtered_by_intent = client.get("/events/settlement_feed", params={"payment_intent_id": "PI-1"})
    assert filtered_by_intent.status_code == 200
    items = filtered_by_intent.json()["items"]
    assert items and all(item["payment_intent_id"] == "PI-1" for item in items)

    filtered_by_shipment = client.get("/events/settlement_feed", params={"shipment_id": "SHIP-2"})
    assert filtered_by_shipment.status_code == 200
    items_by_shipment = filtered_by_shipment.json()["items"]
    assert items_by_shipment and all(item["shipment_id"] == "SHIP-2" for item in items_by_shipment)


def test_heartbeat_returns_latest_timestamps(
    client_with_db: Tuple[TestClient, sessionmaker],
) -> None:
    client, _ = client_with_db
    now = datetime.now(timezone.utc)
    event_bus.publish(
        EventType.PAYMENT_INTENT_CREATED,
        {
            "id": "PI-4",
            "shipment_id": "SHIP-4",
            "status": "PENDING",
            "risk_level": "LOW",
        },
        actor="api",
        occurred_at=now - timedelta(minutes=10),
    )
    update_metric("worker_heartbeat", when=now - timedelta(minutes=5))
    event_bus.publish(
        EventType.SETTLEMENT_EVENT_APPENDED,
        {
            "payment_intent_id": "PI-4",
            "shipment_id": "SHIP-4",
            "event_type": "CAPTURED",
            "status": "SUCCESS",
        },
        actor="worker:sync",
        occurred_at=now - timedelta(minutes=1),
    )

    heartbeat = client.get("/events/heartbeat")
    assert heartbeat.status_code == 200
    payload = heartbeat.json()
    last_event = _iso_to_dt(payload["last_event_at"])
    last_worker = _iso_to_dt(payload["last_worker_heartbeat_at"])
    assert last_event > last_worker
    assert last_worker.tzinfo is not None
