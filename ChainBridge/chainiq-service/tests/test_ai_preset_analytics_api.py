from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models_preset import PresetAnalyticsSnapshot

client = TestClient(app)


def test_analytics_ingest_endpoint_creates_snapshot(db_session: Session) -> None:
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "profile": "moderate",
        "kpis": {
            "ctr": 0.7,
            "hitAt1": 0.5,
            "hitAt3": 0.8,
            "avgTimeToPresetMs": 1500.0,
        },
        "stats": {"interactionCount": 10},
    }

    response = client.post("/api/ai/presets/analytics/ingest", json=payload)
    assert response.status_code == 204

    # Ensure snapshot exists
    snap = db_session.query(PresetAnalyticsSnapshot).filter_by(profile="moderate").one()
    assert snap.ctr == 0.7
    assert snap.hit_at_1 == 0.5
    assert snap.hit_at_3 == 0.8


def test_analytics_summary_endpoint_returns_expected_averages(db_session: Session) -> None:
    now = datetime.now(timezone.utc)

    snap1 = PresetAnalyticsSnapshot(
        profile="moderate",
        ctr=0.4,
        hit_at_1=0.3,
        hit_at_3=0.6,
        avg_time_to_preset_ms=1000.0,
        interaction_count=5,
        created_at=now,
    )
    snap2 = PresetAnalyticsSnapshot(
        profile="moderate",
        ctr=0.8,
        hit_at_1=0.7,
        hit_at_3=0.9,
        avg_time_to_preset_ms=2000.0,
        interaction_count=15,
        created_at=now,
    )

    db_session.add_all([snap1, snap2])
    db_session.commit()

    response = client.get(
        "/api/ai/presets/analytics/summary",
        params={"profile": "moderate", "window_days": 30},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["snapshots"] == 2
    assert data["ctr"] == pytest.approx((0.4 + 0.8) / 2)
    assert data["hit_at_1"] == pytest.approx((0.3 + 0.7) / 2)
    assert data["hit_at_3"] == pytest.approx((0.6 + 0.9) / 2)


def test_analytics_summary_endpoint_empty_returns_zeros() -> None:
    response = client.get(
        "/api/ai/presets/analytics/summary",
        params={"profile": "no-data", "window_days": 7},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["snapshots"] == 0
    assert data["ctr"] == 0.0
    assert data["hit_at_1"] == 0.0
    assert data["hit_at_3"] == 0.0
