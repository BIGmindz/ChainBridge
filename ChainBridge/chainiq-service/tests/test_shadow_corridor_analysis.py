"""
Tests for Shadow Mode v0.3 - Corridor Analytics

Tests corridor-level analysis functions including:
- Multi-corridor statistics aggregation
- Drift detection across corridors
- Corridor comparison
- Top discrepancy identification
- Time-series trend analysis
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.analysis.corridor_analysis import (
    analyze_all_corridors,
    compare_corridors,
    compute_corridor_trend,
    get_top_discrepancies,
    identify_drift_corridors,
)
from app.models_shadow import Base, RiskShadowEvent


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
def sample_corridor_events(test_db):
    """Create sample events across multiple corridors."""
    corridors = ["US-CN", "US-MX", "EU-IN"]
    events = []

    # US-CN: High drift corridor
    for i in range(20):
        event = RiskShadowEvent(
            shipment_id=f"SH-USCN-{i:03d}",
            dummy_score=0.50,
            real_score=0.80,  # Large delta
            delta=0.30,
            model_version="v0.2.0",
            corridor="US-CN",
            created_at=datetime.utcnow() - timedelta(hours=i),
        )
        test_db.add(event)
        events.append(event)

    # US-MX: Low drift corridor
    for i in range(15):
        event = RiskShadowEvent(
            shipment_id=f"SH-USMX-{i:03d}",
            dummy_score=0.50,
            real_score=0.55,  # Small delta
            delta=0.05,
            model_version="v0.2.0",
            corridor="US-MX",
            created_at=datetime.utcnow() - timedelta(hours=i),
        )
        test_db.add(event)
        events.append(event)

    # EU-IN: Medium drift corridor
    for i in range(10):
        event = RiskShadowEvent(
            shipment_id=f"SH-EUIN-{i:03d}",
            dummy_score=0.50,
            real_score=0.65,  # Medium delta
            delta=0.15,
            model_version="v0.2.0",
            corridor="EU-IN",
            created_at=datetime.utcnow() - timedelta(hours=i),
        )
        test_db.add(event)
        events.append(event)

    test_db.commit()
    return events


def test_analyze_all_corridors(test_db, sample_corridor_events):
    """Test multi-corridor analysis."""
    stats = analyze_all_corridors(test_db, hours=24, min_events=5)

    # Should return 3 corridors
    assert len(stats) == 3

    # Corridors should be sorted by P95 delta descending
    assert stats[0]["corridor"] == "US-CN"  # Highest drift
    assert stats[1]["corridor"] == "EU-IN"  # Medium drift
    assert stats[2]["corridor"] == "US-MX"  # Lowest drift

    # Verify US-CN stats
    us_cn_stats = stats[0]
    assert us_cn_stats["event_count"] == 20
    assert us_cn_stats["mean_delta"] == pytest.approx(0.30, abs=0.01)
    assert us_cn_stats["p95_delta"] == pytest.approx(0.30, abs=0.01)
    assert us_cn_stats["drift_flag"] is True  # P95 > 0.25

    # Verify US-MX stats
    us_mx_stats = stats[2]
    assert us_mx_stats["event_count"] == 15
    assert us_mx_stats["mean_delta"] == pytest.approx(0.05, abs=0.01)
    assert us_mx_stats["p95_delta"] == pytest.approx(0.05, abs=0.01)
    assert us_mx_stats["drift_flag"] is False  # P95 < 0.25


def test_identify_drift_corridors(test_db, sample_corridor_events):
    """Test drift detection across corridors."""
    drifting = identify_drift_corridors(test_db, hours=24, p95_threshold=0.25, min_events=5)

    # Only US-CN should show drift (P95 = 0.30 > 0.25)
    assert len(drifting) == 1
    assert drifting[0]["corridor"] == "US-CN"
    assert drifting[0]["drift_flag"] is True


def test_compare_corridors(test_db, sample_corridor_events):
    """Test corridor comparison."""
    comparison = compare_corridors(test_db, "US-CN", "US-MX", hours=24)

    # Verify structure
    assert "corridor_a" in comparison
    assert "corridor_b" in comparison
    assert "p95_delta_difference" in comparison
    assert "relative_drift_difference" in comparison

    # Verify corridor A (US-CN)
    assert comparison["corridor_a"]["corridor"] == "US-CN"
    assert comparison["corridor_a"]["event_count"] == 20
    assert comparison["corridor_a"]["p95_delta"] == pytest.approx(0.30, abs=0.01)

    # Verify corridor B (US-MX)
    assert comparison["corridor_b"]["corridor"] == "US-MX"
    assert comparison["corridor_b"]["event_count"] == 15
    assert comparison["corridor_b"]["p95_delta"] == pytest.approx(0.05, abs=0.01)

    # Verify difference metrics
    expected_diff = abs(0.30 - 0.05)
    assert comparison["p95_delta_difference"] == pytest.approx(expected_diff, abs=0.01)
    assert comparison["relative_drift_difference"] > 0.0


def test_get_top_discrepancies(test_db, sample_corridor_events):
    """Test top discrepancy identification."""
    # Get top 5 discrepancies for US-CN
    top_events = get_top_discrepancies(test_db, "US-CN", limit=5, hours=24)

    # Should return 5 events
    assert len(top_events) == 5

    # All should be from US-CN
    for event in top_events:
        assert event.corridor == "US-CN"
        assert event.shipment_id.startswith("SH-USCN-")

    # All should have delta = 0.30 (uniform in test data)
    for event in top_events:
        assert event.delta == pytest.approx(0.30, abs=0.01)


def test_compute_corridor_trend(test_db):
    """Test time-series trend computation."""
    # Create events with improving trend (decreasing deltas over time)
    for i in range(21):  # 3 weeks worth of data
        hours_ago = 24 * i  # Daily spacing
        delta = 0.40 - (i * 0.015)  # Decreasing from 0.40 to 0.10

        event = RiskShadowEvent(
            shipment_id=f"SH-TREND-{i:03d}",
            dummy_score=0.50,
            real_score=0.50 + delta,
            delta=delta,
            model_version="v0.2.0",
            corridor="US-TREND",
            created_at=datetime.utcnow() - timedelta(hours=hours_ago),
        )
        test_db.add(event)

    test_db.commit()

    # Compute trend with 24h windows x 7 periods
    trend = compute_corridor_trend(test_db, "US-TREND", window_hours=24, num_windows=7)

    # Verify structure
    assert trend["corridor"] == "US-TREND"
    assert "p95_series" in trend
    assert "trend" in trend
    assert trend["window_hours"] == 24
    assert trend["num_windows"] == 7

    # Should detect improving trend (deltas decreasing)
    # Note: With small sample size, trend might be classified as "stable"
    # We just verify it's not "degrading" or "error"
    assert trend["trend"] in ["improving", "stable"]

    # P95 series should have 7 values
    assert len(trend["p95_series"]) == 7


def test_corridor_analysis_with_no_data(test_db):
    """Test corridor analysis with empty database."""
    stats = analyze_all_corridors(test_db, hours=24, min_events=5)

    # Should return empty list
    assert stats == []

    # Drift detection should also return empty
    drifting = identify_drift_corridors(test_db, hours=24)
    assert drifting == []


def test_corridor_analysis_with_insufficient_data(test_db):
    """Test corridor analysis with insufficient events per corridor."""
    # Create only 2 events for a corridor (below min_events threshold)
    for i in range(2):
        event = RiskShadowEvent(
            shipment_id=f"SH-LOW-{i:03d}",
            dummy_score=0.50,
            real_score=0.70,
            delta=0.20,
            model_version="v0.2.0",
            corridor="LOW-DATA",
            created_at=datetime.utcnow() - timedelta(hours=i),
        )
        test_db.add(event)

    test_db.commit()

    # With min_events=5, should filter out LOW-DATA corridor
    stats = analyze_all_corridors(test_db, hours=24, min_events=5)
    assert len(stats) == 0


def test_corridor_statistics_edge_cases(test_db):
    """Test corridor statistics with edge case values."""
    # Create events with extreme delta values
    extreme_events = [
        (0.0, 0.0, 0.0),  # No delta
        (0.0, 1.0, 1.0),  # Maximum delta
        (0.5, 0.5, 0.0),  # Identical scores
    ]

    for i, (dummy, real, delta) in enumerate(extreme_events):
        event = RiskShadowEvent(
            shipment_id=f"SH-EDGE-{i:03d}",
            dummy_score=dummy,
            real_score=real,
            delta=delta,
            model_version="v0.2.0",
            corridor="EDGE-CASE",
            created_at=datetime.utcnow() - timedelta(hours=i),
        )
        test_db.add(event)

    test_db.commit()

    # Should handle edge cases without errors
    stats = analyze_all_corridors(test_db, hours=24, min_events=1)
    assert len(stats) == 1

    edge_stats = stats[0]
    assert edge_stats["corridor"] == "EDGE-CASE"
    assert edge_stats["event_count"] == 3
    assert 0.0 <= edge_stats["mean_delta"] <= 1.0
    assert 0.0 <= edge_stats["p95_delta"] <= 1.0


def test_trend_with_sparse_data(test_db):
    """Test trend computation with sparse/missing data windows."""
    # Create events only in 3 out of 7 windows
    sparse_hours = [1, 50, 100]  # Gaps between windows

    for hours_ago in sparse_hours:
        event = RiskShadowEvent(
            shipment_id=f"SH-SPARSE-{hours_ago}",
            dummy_score=0.50,
            real_score=0.70,
            delta=0.20,
            model_version="v0.2.0",
            corridor="SPARSE",
            created_at=datetime.utcnow() - timedelta(hours=hours_ago),
        )
        test_db.add(event)

    test_db.commit()

    # Should handle sparse data gracefully
    trend = compute_corridor_trend(test_db, "SPARSE", window_hours=24, num_windows=7)

    assert trend["corridor"] == "SPARSE"
    assert len(trend["p95_series"]) == 7

    # Some windows will have None values
    none_count = trend["p95_series"].count(None)
    assert none_count > 0  # At least some windows should be empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
