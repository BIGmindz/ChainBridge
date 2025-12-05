from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models_preset import PresetFeedbackEvent
from app.services.preset_metrics import compute_preset_metrics


def _make_session() -> Session:
    """
    Create an isolated in-memory SQLite session for metrics tests.
    Only the PresetFeedbackEvent table is created.
    """
    engine = create_engine("sqlite:///:memory:")
    # Use the model's own metadata to create the table
    PresetFeedbackEvent.metadata.create_all(bind=engine)  # type: ignore[attr-defined]
    TestingSessionLocal = sessionmaker(bind=engine)
    return TestingSessionLocal()


def test_compute_preset_metrics_empty_db_returns_zeros() -> None:
    db = _make_session()
    now = datetime.now(timezone.utc)

    metrics = compute_preset_metrics(db, since=now - timedelta(days=7), profile=None)

    assert metrics.total_sessions == 0
    assert metrics.total_ai_sessions == 0
    assert metrics.ctr == 0.0
    assert metrics.hit_at_1 == 0.0
    assert metrics.hit_at_3 == 0.0


def test_compute_preset_metrics_basic_clickthrough() -> None:
    db = _make_session()
    now = datetime.now(timezone.utc)

    # Session 1: one AI impression, chosen at rank 0 (top hit)
    evt1 = PresetFeedbackEvent(
        created_at=now - timedelta(days=1),
        preset_id="preset-a",
        profile="moderate",
        rank=0,
        chosen=True,
        explicit_feedback="none",
        session_id="s1",
        user_id="u1",
    )
    # Session 2: one AI impression, not chosen
    evt2 = PresetFeedbackEvent(
        created_at=now - timedelta(days=1),
        preset_id="preset-b",
        profile="moderate",
        rank=1,
        chosen=False,
        explicit_feedback="none",
        session_id="s2",
        user_id="u1",
    )

    db.add_all([evt1, evt2])
    db.commit()

    metrics = compute_preset_metrics(db, since=now - timedelta(days=7), profile="moderate")

    # We had 2 sessions with AI impressions, 1 of which resulted in a chosen preset.
    assert metrics.total_sessions == 2
    assert metrics.total_ai_sessions == 2

    # CTR should be > 0 and <= 1 (one chosen, two AI sessions)
    assert 0.0 < metrics.ctr <= 1.0

    # Hit@1 should be > 0 as the chosen preset was at rank 0
    assert metrics.hit_at_1 > 0.0
    # Hit@3 should be at least as high as Hit@1
    assert metrics.hit_at_3 >= metrics.hit_at_1
