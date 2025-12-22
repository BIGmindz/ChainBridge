import asyncio
from pathlib import Path
from typing import Any, Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.jobs.shadow_pilot_jobs import run_shadow_pilot_job
from api.models.shadow_pilot import ShadowPilotRun, ShadowPilotShipment
from api.server import app


@pytest.fixture()
def client_with_db(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch):
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
    data_dir = tmp_path_factory.mktemp("shadow_data")
    monkeypatch.setenv("SHADOW_PILOT_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SHADOW_PILOT_ANNUAL_RATE_DEFAULT", "0.06")
    monkeypatch.setenv("SHADOW_PILOT_ADVANCE_RATE_DEFAULT", "0.7")
    monkeypatch.setenv("SHADOW_PILOT_TAKE_RATE_DEFAULT", "0.01")

    client = TestClient(app)
    yield client, engine, TestingSessionLocal, data_dir
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def clean_db(client_with_db) -> None:
    _, engine, _, _ = client_with_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _sample_csv() -> bytes:
    return b"""shipment_id,cargo_value_usd,delivery_timestamp,planned_delivery_timestamp,pickup_timestamp,exception_flag,loss_flag,loss_amount_usd,days_to_payment
S1,100000,2024-01-10,2024-01-12,2024-01-05,0,0,0,45
S2,20000,2024-02-15,2024-02-10,,1,1,1000,30
"""


def test_ingest_and_job_persists_results(client_with_db) -> None:
    client, _, SessionLocal, data_dir = client_with_db
    csv_bytes = _sample_csv()
    resp = client.post(
        "/shadow-pilot/ingest",
        data={"prospect_name": "ACME", "period_months": 6, "run_id": "testrun"},
        files={"file": ("shipments.csv", csv_bytes, "text/csv")},
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["run_id"] == "testrun"

    csv_path = data_dir / "testrun_shipments.csv"
    assert csv_path.exists()

    asyncio.run(
        run_shadow_pilot_job(
            {"SessionLocal": SessionLocal},
            "testrun",
            str(csv_path),
            {
                "prospect_name": "ACME",
                "period_months": 6,
                "input_filename": "shipments.csv",
                "notes": None,
                "annual_rate": 0.06,
                "advance_rate": 0.7,
                "take_rate": 0.01,
                "min_value": 50000,
                "min_truth": 0.7,
            },
        )
    )

    with SessionLocal() as session:
        run = session.query(ShadowPilotRun).filter(ShadowPilotRun.run_id == "testrun").first()
        assert run is not None
        assert run.shipments_evaluated == 2
        assert float(run.total_gmv_usd) == pytest.approx(120000.0)
        shipments = session.query(ShadowPilotShipment).filter(ShadowPilotShipment.run_id == "testrun").all()
        assert len(shipments) == 2
        financeable = [s for s in shipments if s.eligible_for_finance]
        assert len(financeable) == 1


def test_list_and_get_summaries(client_with_db) -> None:
    client, _, SessionLocal, _ = client_with_db
    with SessionLocal() as session:
        session.add_all(
            [
                ShadowPilotRun(run_id="run_a", prospect_name="A", period_months=3, shipments_evaluated=1, shipments_financeable=0),
                ShadowPilotRun(run_id="run_b", prospect_name="B", period_months=6, shipments_evaluated=2, shipments_financeable=1),
            ]
        )
        session.commit()

    resp = client.get("/shadow-pilot/summaries")
    assert resp.status_code == 200
    runs = resp.json()
    assert {r["run_id"] for r in runs} == {"run_a", "run_b"}

    detail = client.get("/shadow-pilot/summaries/run_b")
    assert detail.status_code == 200
    assert detail.json()["run_id"] == "run_b"

    not_found = client.get("/shadow-pilot/summaries/nope")
    assert not_found.status_code == 404


def test_paginated_shipments(client_with_db) -> None:
    client, _, SessionLocal, _ = client_with_db
    with SessionLocal() as session:
        run = ShadowPilotRun(run_id="run_ship", prospect_name="ShipCo", period_months=12, shipments_evaluated=3, shipments_financeable=2)
        session.add(run)
        session.add_all(
            [
                ShadowPilotShipment(run_id="run_ship", shipment_id="S1", cargo_value_usd=1000, event_truth_score=0.8, eligible_for_finance=True, financed_amount_usd=700, days_pulled_forward=45, wc_saved_usd=1, protocol_revenue_usd=2, avoided_loss_usd=0, salvage_revenue_usd=0, exception_flag=False, loss_flag=False),
                ShadowPilotShipment(run_id="run_ship", shipment_id="S2", cargo_value_usd=2000, event_truth_score=0.5, eligible_for_finance=False, financed_amount_usd=0, days_pulled_forward=30, wc_saved_usd=0, protocol_revenue_usd=0, avoided_loss_usd=0, salvage_revenue_usd=0, exception_flag=True, loss_flag=False),
                ShadowPilotShipment(run_id="run_ship", shipment_id="S3", cargo_value_usd=3000, event_truth_score=0.9, eligible_for_finance=True, financed_amount_usd=2100, days_pulled_forward=60, wc_saved_usd=5, protocol_revenue_usd=6, avoided_loss_usd=0, salvage_revenue_usd=0, exception_flag=False, loss_flag=False),
            ]
        )
        session.commit()

    first_page = client.get("/shadow-pilot/runs/run_ship/shipments?limit=2")
    assert first_page.status_code == 200
    data = first_page.json()
    assert len(data["items"]) == 2
    assert data["next_cursor"] is not None

    next_cursor = data["next_cursor"]
    second_page = client.get(f"/shadow-pilot/runs/run_ship/shipments?cursor={next_cursor}&limit=2")
    assert second_page.status_code == 200
    data2 = second_page.json()
    assert len(data2["items"]) == 1
    assert data2["items"][0]["shipment_id"] == "S3"
