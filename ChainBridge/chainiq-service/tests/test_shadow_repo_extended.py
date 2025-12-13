"""
Tests for Shadow Mode v0.3 - Extended Repository

Tests extended ShadowRepo functionality including:
- Corridor filtering
- Model version tracking
- High delta event queries
- Corridor statistics computation
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models_shadow import Base, RiskShadowEvent
from app.repositories.shadow_repo import ShadowRepo


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def shadow_repo(test_db):
    """Create ShadowRepo instance with test database."""
    return ShadowRepo(test_db)


@pytest.fixture
def multi_corridor_events(test_db):
    """Create events across multiple corridors with varying deltas."""
    events = []

    # US-CN corridor with high deltas
    for i in range(10):
        event = RiskShadowEvent(
            shipment_id=f"SH-USCN-{i:03d}",
            dummy_score=0.40,
            real_score=0.70,
            delta=0.30,
            model_version="v0.2.0",
            corridor="US-CN",
            created_at=datetime.utcnow() - timedelta(hours=i),
        )
        test_db.add(event)
        events.append(event)

    # US-MX corridor with low deltas
    for i in range(15):
        event = RiskShadowEvent(
            shipment_id=f"SH-USMX-{i:03d}",
            dummy_score=0.50,
            real_score=0.52,
            delta=0.02,
            model_version="v0.2.0",
            corridor="US-MX",
            created_at=datetime.utcnow() - timedelta(hours=i),
        )
        test_db.add(event)
        events.append(event)

    # EU-IN corridor with medium deltas (old model version)
    for i in range(8):
        event = RiskShadowEvent(
            shipment_id=f"SH-EUIN-{i:03d}",
            dummy_score=0.60,
            real_score=0.75,
            delta=0.15,
            model_version="v0.1.0",
            corridor="EU-IN",
            created_at=datetime.utcnow() - timedelta(hours=i),
        )
        test_db.add(event)
        events.append(event)

    test_db.commit()
    return events


def test_get_by_corridor(shadow_repo, multi_corridor_events):
    """Test filtering events by corridor."""
    # Get US-CN events
    us_cn_events = shadow_repo.get_by_corridor("US-CN", limit=100, hours=24)

    assert len(us_cn_events) == 10
    for event in us_cn_events:
        assert event.corridor == "US-CN"
        assert event.shipment_id.startswith("SH-USCN-")
        assert event.delta == pytest.approx(0.30, abs=0.01)

    # Get US-MX events
    us_mx_events = shadow_repo.get_by_corridor("US-MX", limit=100, hours=24)

    assert len(us_mx_events) == 15
    for event in us_mx_events:
        assert event.corridor == "US-MX"
        assert event.shipment_id.startswith("SH-USMX-")


def test_get_by_corridor_with_limit(shadow_repo, multi_corridor_events):
    """Test corridor filtering with limit."""
    # Request only 5 events
    us_mx_events = shadow_repo.get_by_corridor("US-MX", limit=5, hours=24)

    assert len(us_mx_events) == 5

    # Should be most recent events (ordered by created_at DESC)
    for i in range(4):
        assert us_mx_events[i].created_at >= us_mx_events[i + 1].created_at


def test_get_by_corridor_with_time_window(shadow_repo, test_db):
    """Test corridor filtering with time window."""
    # Create events at different times
    recent_event = RiskShadowEvent(
        shipment_id="SH-RECENT",
        dummy_score=0.5,
        real_score=0.6,
        delta=0.1,
        model_version="v0.2.0",
        corridor="TEST",
        created_at=datetime.utcnow() - timedelta(hours=1),
    )

    old_event = RiskShadowEvent(
        shipment_id="SH-OLD",
        dummy_score=0.5,
        real_score=0.6,
        delta=0.1,
        model_version="v0.2.0",
        corridor="TEST",
        created_at=datetime.utcnow() - timedelta(hours=48),
    )

    test_db.add(recent_event)
    test_db.add(old_event)
    test_db.commit()

    # Query with 24h window - should only get recent event
    events_24h = shadow_repo.get_by_corridor("TEST", hours=24)
    assert len(events_24h) == 1
    assert events_24h[0].shipment_id == "SH-RECENT"

    # Query with 72h window - should get both
    events_72h = shadow_repo.get_by_corridor("TEST", hours=72)
    assert len(events_72h) == 2


def test_get_by_model_version(shadow_repo, multi_corridor_events):
    """Test filtering events by model version."""
    # Get v0.2.0 events
    v02_events = shadow_repo.get_by_model_version("v0.2.0", limit=100, hours=24)

    # Should get US-CN (10) + US-MX (15) = 25 events
    assert len(v02_events) == 25
    for event in v02_events:
        assert event.model_version == "v0.2.0"

    # Get v0.1.0 events
    v01_events = shadow_repo.get_by_model_version("v0.1.0", limit=100, hours=24)

    # Should get only EU-IN (8) events
    assert len(v01_events) == 8
    for event in v01_events:
        assert event.model_version == "v0.1.0"
        assert event.corridor == "EU-IN"


def test_get_high_delta_events(shadow_repo, multi_corridor_events):
    """Test getting events with high deltas."""
    # Get events with delta >= 0.15
    high_delta_events = shadow_repo.get_high_delta_events(threshold=0.15, limit=100, hours=24)

    # Should get US-CN (delta=0.30) and EU-IN (delta=0.15)
    # Total: 10 + 8 = 18 events
    assert len(high_delta_events) == 18

    # All should have delta >= 0.15
    for event in high_delta_events:
        assert event.delta >= 0.15

    # Should be ordered by delta descending
    for i in range(len(high_delta_events) - 1):
        assert high_delta_events[i].delta >= high_delta_events[i + 1].delta

    # Top events should be from US-CN (delta=0.30)
    assert high_delta_events[0].corridor == "US-CN"


def test_get_high_delta_events_with_corridor_filter(shadow_repo, multi_corridor_events):
    """Test high delta events with corridor filter."""
    # Get high delta events only for US-CN
    us_cn_high = shadow_repo.get_high_delta_events(threshold=0.15, corridor="US-CN", limit=100, hours=24)

    # Should only get US-CN events
    assert len(us_cn_high) == 10
    for event in us_cn_high:
        assert event.corridor == "US-CN"
        assert event.delta >= 0.15


def test_get_high_delta_events_with_strict_threshold(shadow_repo, multi_corridor_events):
    """Test high delta events with strict threshold."""
    # Set threshold = 0.25 (only US-CN with delta=0.30 qualifies)
    strict_high = shadow_repo.get_high_delta_events(threshold=0.25, limit=100, hours=24)

    assert len(strict_high) == 10
    for event in strict_high:
        assert event.corridor == "US-CN"
        assert event.delta >= 0.25


def test_get_corridor_statistics(shadow_repo, multi_corridor_events):
    """Test corridor statistics computation."""
    # Get stats for US-CN (high delta corridor)
    us_cn_stats = shadow_repo.get_corridor_statistics("US-CN", hours=24)

    assert us_cn_stats["corridor"] == "US-CN"
    assert us_cn_stats["event_count"] == 10
    assert us_cn_stats["mean_delta"] == pytest.approx(0.30, abs=0.01)
    assert us_cn_stats["median_delta"] == pytest.approx(0.30, abs=0.01)
    assert us_cn_stats["p95_delta"] == pytest.approx(0.30, abs=0.01)
    assert us_cn_stats["max_delta"] == pytest.approx(0.30, abs=0.01)
    assert us_cn_stats["drift_flag"] is True  # P95 > 0.25
    assert us_cn_stats["time_window_hours"] == 24

    # Get stats for US-MX (low delta corridor)
    us_mx_stats = shadow_repo.get_corridor_statistics("US-MX", hours=24)

    assert us_mx_stats["corridor"] == "US-MX"
    assert us_mx_stats["event_count"] == 15
    assert us_mx_stats["mean_delta"] == pytest.approx(0.02, abs=0.01)
    assert us_mx_stats["drift_flag"] is False  # P95 < 0.25


def test_get_corridor_statistics_no_data(shadow_repo):
    """Test corridor statistics with no data."""
    stats = shadow_repo.get_corridor_statistics("NONEXISTENT", hours=24)

    # Should return zero stats without errors
    assert stats["corridor"] == "NONEXISTENT"
    assert stats["event_count"] == 0
    assert stats["mean_delta"] == 0.0
    assert stats["median_delta"] == 0.0
    assert stats["p95_delta"] == 0.0
    assert stats["max_delta"] == 0.0
    assert stats["drift_flag"] is False


def test_count_events_by_corridor(shadow_repo, multi_corridor_events):
    """Test counting events by corridor."""
    # Count all events
    total_count = shadow_repo.count_events()
    assert total_count == 33  # 10 + 15 + 8

    # Count US-CN events
    us_cn_count = shadow_repo.count_events(corridor="US-CN")
    assert us_cn_count == 10

    # Count US-MX events
    us_mx_count = shadow_repo.count_events(corridor="US-MX")
    assert us_mx_count == 15


def test_extended_repo_with_empty_database(shadow_repo):
    """Test extended repo methods with empty database."""
    # All queries should return empty/zero results without errors

    corridor_events = shadow_repo.get_by_corridor("US-CN", hours=24)
    assert corridor_events == []

    version_events = shadow_repo.get_by_model_version("v0.2.0", hours=24)
    assert version_events == []

    high_delta = shadow_repo.get_high_delta_events(threshold=0.15, hours=24)
    assert high_delta == []

    stats = shadow_repo.get_corridor_statistics("US-CN", hours=24)
    assert stats["event_count"] == 0


def test_repo_error_handling(test_db):
    """Test repository error handling."""
    # Close the session to simulate database errors
    test_db.close()

    repo = ShadowRepo(test_db)

    # All methods should handle errors gracefully
    events = repo.get_by_corridor("US-CN")
    assert events == []

    high_delta = repo.get_high_delta_events(threshold=0.15)
    assert high_delta == []

    count = repo.count_events()
    assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
