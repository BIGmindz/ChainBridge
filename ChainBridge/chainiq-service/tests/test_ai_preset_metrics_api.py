from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models_preset import PresetFeedbackEvent

client = TestClient(app)


def test_metrics_api_happy_path(db_session: Session) -> None:
    now = datetime.now(timezone.utc)

    event = PresetFeedbackEvent(
        preset_id="p1",
        profile="moderate",
        session_id="s1",
        rank=0,
        chosen=True,
        created_at=now,
    )
    db_session.add(event)
    db_session.commit()

    response = client.get("/api/ai/presets/metrics", params={"since_days": 30})
    assert response.status_code == 200

    data = response.json()
    for key in [
        "ctr",
        "hit_at_1",
        "hit_at_3",
        "total_sessions",
        "total_ai_sessions",
    ]:
        assert key in data

    assert isinstance(data["ctr"], (int, float))
    assert isinstance(data["hit_at_1"], (int, float))
    assert isinstance(data["hit_at_3"], (int, float))


def test_metrics_api_bad_since_days_returns_400() -> None:
    response = client.get("/api/ai/presets/metrics", params={"since_days": 0})
    assert response.status_code == 400


def test_metrics_api_profile_specific(db_session: Session) -> None:
    now = datetime.now(timezone.utc)

    # moderate profile: one chosen
    m_event = PresetFeedbackEvent(
        preset_id="p1",
        profile="moderate",
        session_id="sm",
        rank=0,
        chosen=True,
        created_at=now,
    )

    # aggressive profile: AI shown but not chosen
    a_event = PresetFeedbackEvent(
        preset_id="p2",
        profile="aggressive",
        session_id="sa",
        rank=0,
        chosen=False,
        created_at=now,
    )

    db_session.add_all([m_event, a_event])
    db_session.commit()

    response = client.get(
        "/api/ai/presets/metrics",
        params={"since_days": 30, "profile": "moderate"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["total_sessions"] == 1
    assert data["total_ai_sessions"] == 1
    assert data["ctr"] == 1.0
