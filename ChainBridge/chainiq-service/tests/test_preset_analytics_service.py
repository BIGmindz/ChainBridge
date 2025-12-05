from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models_preset import PresetAnalyticsSnapshot
from app.schemas_ai_presets import PresetAnalyticsKpis, PresetAnalyticsPayload
from app.services.preset_analytics import (
    get_preset_analytics_summary,
    ingest_preset_analytics,
)


def _fake_payload(profile: str = "moderate") -> PresetAnalyticsPayload:
    now = datetime.now(timezone.utc)
    kpis = PresetAnalyticsKpis(
        ctr=0.7,
        hit_at_1=0.5,
        hit_at_3=0.8,
        avg_time_to_preset_ms=1500.0,
    )
    return PresetAnalyticsPayload(
        generated_at=now,
        profile=profile,
        kpis=kpis,
        stats={"interactionCount": 10},
    )


def test_ingest_preset_analytics_persists_snapshot(db_session: Session) -> None:
    payload = _fake_payload()

    snapshot = ingest_preset_analytics(db_session, payload)

    assert snapshot.id is not None
    assert snapshot.profile == payload.profile
    assert snapshot.ctr == payload.kpis.ctr
    assert snapshot.hit_at_1 == payload.kpis.hit_at_1
    assert snapshot.hit_at_3 == payload.kpis.hit_at_3
    assert snapshot.avg_time_to_preset_ms == payload.kpis.avg_time_to_preset_ms
    assert snapshot.interaction_count == 10


def test_get_preset_analytics_summary_empty_returns_zeros(db_session: Session) -> None:
    summary = get_preset_analytics_summary(db_session, profile="moderate", window_days=7)

    assert summary.profile == "moderate"
    assert summary.window_days == 7
    assert summary.ctr == 0.0
    assert summary.hit_at_1 == 0.0
    assert summary.hit_at_3 == 0.0
    assert summary.avg_time_to_preset_ms is None
    assert summary.snapshots == 0


def test_get_preset_analytics_summary_with_snapshots(db_session: Session) -> None:
    now = datetime.now(timezone.utc)

    # Two snapshots with different KPIs
    snap1 = PresetAnalyticsSnapshot(
        profile="moderate",
        ctr=0.5,
        hit_at_1=0.4,
        hit_at_3=0.6,
        avg_time_to_preset_ms=1000.0,
        interaction_count=5,
        created_at=now,
    )
    snap2 = PresetAnalyticsSnapshot(
        profile="moderate",
        ctr=0.9,
        hit_at_1=0.8,
        hit_at_3=0.9,
        avg_time_to_preset_ms=2000.0,
        interaction_count=15,
        created_at=now,
    )

    db_session.add_all([snap1, snap2])
    db_session.commit()

    summary = get_preset_analytics_summary(db_session, profile="moderate", window_days=7)

    assert summary.snapshots == 2
    assert summary.ctr == pytest.approx((0.5 + 0.9) / 2)
    assert summary.hit_at_1 == pytest.approx((0.4 + 0.8) / 2)
    assert summary.hit_at_3 == pytest.approx((0.6 + 0.9) / 2)
    assert summary.avg_time_to_preset_ms == pytest.approx((1000.0 + 2000.0) / 2)
