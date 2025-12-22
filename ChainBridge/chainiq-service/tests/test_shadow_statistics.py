"""Tests for shadow statistics computation."""

from unittest.mock import MagicMock

from app.analysis.shadow_diff import compute_shadow_statistics, get_high_delta_events
from app.models_shadow import RiskShadowEvent


def test_compute_shadow_statistics_basic():
    """Test basic statistics computation."""
    mock_session = MagicMock()

    # Create mock events
    mock_events = [
        RiskShadowEvent(
            id=1,
            shipment_id=f"SH-{i:03d}",
            dummy_score=0.70,
            real_score=0.70 + i * 0.01,
            delta=i * 0.01,
            model_version="v0.2.0",
            corridor="US-MX",
        )
        for i in range(10)
    ]

    # Mock query chain
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.all.return_value = mock_events

    stats = compute_shadow_statistics(mock_session)

    assert stats is not None
    assert stats["count"] == 10
    assert "mean_delta" in stats
    assert "p95_delta" in stats
    assert "drift_flag" in stats


def test_compute_shadow_statistics_no_data():
    """Test statistics with no data."""
    mock_session = MagicMock()

    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.all.return_value = []

    stats = compute_shadow_statistics(mock_session)

    assert stats is None


def test_compute_shadow_statistics_high_drift():
    """Test that high drift is detected."""
    mock_session = MagicMock()

    # Create events with high deltas
    mock_events = [
        RiskShadowEvent(
            id=i,
            shipment_id=f"SH-{i:03d}",
            dummy_score=0.50,
            real_score=0.80,  # Large delta
            delta=0.30,
            model_version="v0.2.0",
            corridor="US-MX",
        )
        for i in range(100)
    ]

    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.all.return_value = mock_events

    stats = compute_shadow_statistics(mock_session)

    assert stats is not None
    assert bool(stats["drift_flag"]) is True  # P95 > 0.25, convert numpy bool


def test_get_high_delta_events():
    """Test retrieving high delta events."""
    mock_session = MagicMock()

    # Mock query chain
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = [
        RiskShadowEvent(
            id=1,
            shipment_id="SH-HIGH-001",
            dummy_score=0.40,
            real_score=0.85,
            delta=0.45,
            model_version="v0.2.0",
        )
    ]

    events = get_high_delta_events(mock_session, threshold=0.30, limit=10)

    assert len(events) == 1
    assert events[0].delta >= 0.30


def test_statistics_with_corridor_filter():
    """Test statistics filtered by corridor."""
    mock_session = MagicMock()

    mock_events = [
        RiskShadowEvent(
            id=i,
            shipment_id=f"SH-{i:03d}",
            dummy_score=0.70,
            real_score=0.72,
            delta=0.02,
            model_version="v0.2.0",
            corridor="US-MX",
        )
        for i in range(5)
    ]

    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = mock_events

    stats = compute_shadow_statistics(mock_session, corridor="US-MX")

    assert stats is not None
    assert stats["count"] == 5
    assert stats["corridor"] == "US-MX"
