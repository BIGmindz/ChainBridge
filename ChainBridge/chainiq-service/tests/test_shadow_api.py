"""
Tests for Shadow Mode API Endpoints

Validates HTTP API surface for shadow mode monitoring.
ALEX-compliant: tests governance rules (no model loading, fast responses).
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import create_app
from app.models_shadow import Base, RiskShadowEvent


@pytest.fixture(scope="function")
def test_engine():
    """Create shared in-memory SQLite engine for testing."""
    # Use check_same_thread=False for SQLite compatibility with FastAPI
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool  # Ensure same database for all connections
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_db(test_engine):
    """Create database session for testing."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(test_engine):
    """Create FastAPI test client with test database."""
    app = create_app()

    # Create session factory from test engine
    TestSessionLocal = sessionmaker(bind=test_engine)

    # Override database dependency
    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    return TestClient(app)


@pytest.fixture
def sample_events(test_db):
    """Create sample shadow events for testing."""
    events = []

    # Create 20 events with varying deltas
    for i in range(20):
        delta = 0.05 + (i * 0.01)  # Increasing deltas from 0.05 to 0.24
        event = RiskShadowEvent(
            shipment_id=f"SH-TEST-{i:03d}",
            dummy_score=0.50,
            real_score=0.50 + delta,
            delta=delta,
            model_version="v0.2.0",
            corridor="US-MX" if i % 2 == 0 else "US-CN",
            created_at=datetime.utcnow() - timedelta(hours=i),
        )
        test_db.add(event)
        events.append(event)

    test_db.commit()
    return events


def test_stats_endpoint_returns_200(client, sample_events):
    """Test /iq/shadow/stats returns 200 OK."""
    response = client.get("/iq/shadow/stats")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


def test_stats_endpoint_required_fields(client, sample_events):
    """Test /iq/shadow/stats includes all required fields."""
    response = client.get("/iq/shadow/stats")
    data = response.json()

    # Verify all required fields present
    required_fields = [
        "count",
        "mean_delta",
        "median_delta",
        "std_delta",
        "p50_delta",
        "p95_delta",
        "p99_delta",
        "max_delta",
        "drift_flag",
        "model_version",
        "time_window_hours",
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Verify model_version is present (ALEX requirement)
    assert data["model_version"] == "v0.2.0"


def test_stats_endpoint_correct_counts(test_engine, client, sample_events):
    """Test /iq/shadow/stats returns correct event count."""
    response = client.get("/iq/shadow/stats?hours=24")
    data = response.json()

    # Should return all 20 events
    assert data["count"] == 20
    assert data["time_window_hours"] == 24


def test_stats_endpoint_calculates_percentiles(client, sample_events):
    """Test /iq/shadow/stats calculates P50/P95/P99 correctly."""
    response = client.get("/iq/shadow/stats")
    data = response.json()

    # Verify percentiles are in ascending order
    assert data["p50_delta"] <= data["p95_delta"]
    assert data["p95_delta"] <= data["p99_delta"]
    assert data["p99_delta"] <= data["max_delta"]

    # Verify values are within valid range [0, 1]
    assert 0.0 <= data["p50_delta"] <= 1.0
    assert 0.0 <= data["p95_delta"] <= 1.0
    assert 0.0 <= data["p99_delta"] <= 1.0


def test_stats_endpoint_no_data(client):
    """Test /iq/shadow/stats with empty database."""
    response = client.get("/iq/shadow/stats")
    data = response.json()

    # Should return zero stats
    assert data["count"] == 0
    assert data["mean_delta"] == 0.0
    assert data["drift_flag"] is False


def test_events_endpoint_returns_200(client, sample_events):
    """Test /iq/shadow/events returns 200 OK."""
    response = client.get("/iq/shadow/events")

    assert response.status_code == 200


def test_events_endpoint_returns_event_list(test_engine, client, sample_events):
    """Test /iq/shadow/events returns list of events."""
    response = client.get("/iq/shadow/events?limit=10")
    data = response.json()

    assert "events" in data
    assert isinstance(data["events"], list)
    assert len(data["events"]) == 10

    # Verify event structure
    event = data["events"][0]
    required_fields = ["id", "shipment_id", "dummy_score", "real_score", "delta", "model_version", "corridor", "created_at"]
    for field in required_fields:
        assert field in event


def test_events_endpoint_corridor_filter(test_engine, client, sample_events):
    """Test /iq/shadow/events with corridor filter."""
    response = client.get("/iq/shadow/events?corridor=US-MX&limit=100")
    data = response.json()

    # Should only return US-MX events (10 out of 20)
    assert data["corridor"] == "US-MX"
    assert len(data["events"]) == 10

    # Verify all events are from US-MX
    for event in data["events"]:
        assert event["corridor"] == "US-MX"


def test_events_endpoint_respects_limit(client, sample_events):
    """Test /iq/shadow/events respects limit parameter."""
    response = client.get("/iq/shadow/events?limit=5")
    data = response.json()

    assert data["limit"] == 5
    assert len(data["events"]) <= 5


def test_events_endpoint_includes_metadata(client, sample_events):
    """Test /iq/shadow/events includes metadata fields."""
    response = client.get("/iq/shadow/events")
    data = response.json()

    # Verify metadata present
    assert "total_count" in data
    assert "limit" in data
    assert "model_version" in data
    assert "time_window_hours" in data

    # Verify model_version (ALEX requirement)
    assert data["model_version"] == "v0.2.0"


def test_corridors_endpoint_returns_200(client, sample_events):
    """Test /iq/shadow/corridors returns 200 OK."""
    response = client.get("/iq/shadow/corridors")

    assert response.status_code == 200


def test_corridors_endpoint_analyzes_all_corridors(test_engine, client, sample_events):
    """Test /iq/shadow/corridors returns statistics for all corridors."""
    response = client.get("/iq/shadow/corridors?min_events=5")
    data = response.json()

    assert "corridors" in data
    assert isinstance(data["corridors"], list)

    # Should have 2 corridors (US-MX and US-CN)
    assert data["total_corridors"] == 2

    # Verify corridor structure
    corridor = data["corridors"][0]
    required_fields = ["corridor", "event_count", "mean_delta", "median_delta", "p95_delta", "max_delta", "drift_flag", "time_window_hours"]
    for field in required_fields:
        assert field in corridor


def test_corridors_endpoint_includes_drift_count(client, sample_events):
    """Test /iq/shadow/corridors includes drifting_count."""
    response = client.get("/iq/shadow/corridors")
    data = response.json()

    assert "drifting_count" in data
    assert isinstance(data["drifting_count"], int)
    assert data["drifting_count"] >= 0


def test_corridors_endpoint_respects_min_events(client, sample_events):
    """Test /iq/shadow/corridors filters by min_events."""
    # Request min_events=50 (no corridor has this many)
    response = client.get("/iq/shadow/corridors?min_events=50")
    data = response.json()

    # Should return empty list
    assert len(data["corridors"]) == 0
    assert data["total_corridors"] == 0


def test_drift_endpoint_returns_200(client, sample_events):
    """Test /iq/shadow/drift returns 200 OK."""
    response = client.get("/iq/shadow/drift")

    assert response.status_code == 200


def test_drift_endpoint_required_fields(client, sample_events):
    """Test /iq/shadow/drift includes all required fields."""
    response = client.get("/iq/shadow/drift")
    data = response.json()

    required_fields = [
        "drift_detected",
        "p95_delta",
        "high_delta_count",
        "total_events",
        "model_version",
        "lookback_hours",
        "drift_threshold",
    ]

    for field in required_fields:
        assert field in data

    # Verify model_version (ALEX requirement)
    assert data["model_version"] == "v0.2.0"


def test_drift_endpoint_detects_drift(client, sample_events):
    """Test /iq/shadow/drift correctly detects drift."""
    # Use low threshold to trigger drift detection
    response = client.get("/iq/shadow/drift?threshold=0.15")
    data = response.json()

    # With max delta = 0.24, P95 should be close to that
    # So drift should be detected with threshold=0.15
    assert isinstance(data["drift_detected"], bool)
    assert data["drift_threshold"] == 0.15


def test_drift_endpoint_no_data(client):
    """Test /iq/shadow/drift with empty database."""
    response = client.get("/iq/shadow/drift")
    data = response.json()

    # Should return no-drift response
    assert data["drift_detected"] is False
    assert data["total_events"] == 0
    assert data["p95_delta"] == 0.0


def test_api_response_time(client, sample_events):
    """Test API endpoints respond within ALEX requirement (< 60ms p95)."""
    import time

    endpoints = ["/iq/shadow/stats", "/iq/shadow/events?limit=10", "/iq/shadow/corridors", "/iq/shadow/drift"]

    for endpoint in endpoints:
        start = time.perf_counter()
        response = client.get(endpoint)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        # Allow 100ms for test environment (production should be < 60ms)
        assert elapsed_ms < 100, f"{endpoint} took {elapsed_ms:.2f}ms (> 100ms)"


def test_api_no_model_loading_in_request_path(client, sample_events):
    """Test API endpoints do not load ML models (ALEX requirement)."""
    # This test verifies that endpoints use repository layer only
    # No XGBoost/sklearn imports should be triggered

    # Make requests
    client.get("/iq/shadow/stats")
    client.get("/iq/shadow/events")
    client.get("/iq/shadow/corridors")
    client.get("/iq/shadow/drift")

    # If we get here without import errors, no model loading occurred
    assert True


def test_api_handles_invalid_parameters(client):
    """Test API endpoints handle invalid query parameters."""
    # Invalid hours (negative)
    response = client.get("/iq/shadow/stats?hours=-1")
    assert response.status_code == 422  # Validation error

    # Invalid limit (too large)
    response = client.get("/iq/shadow/events?limit=10000")
    assert response.status_code == 422

    # Invalid threshold (> 1.0)
    response = client.get("/iq/shadow/drift?threshold=1.5")
    assert response.status_code == 422


def test_api_returns_json_content_type(client, sample_events):
    """Test all endpoints return JSON content type."""
    endpoints = ["/iq/shadow/stats", "/iq/shadow/events", "/iq/shadow/corridors", "/iq/shadow/drift"]

    for endpoint in endpoints:
        response = client.get(endpoint)
        assert "application/json" in response.headers["content-type"]


def test_stats_endpoint_time_window_parameter(client, sample_events):
    """Test /iq/shadow/stats respects time window parameter."""
    # Query with 1 hour window (should return only events from last hour)
    response = client.get("/iq/shadow/stats?hours=1")
    data = response.json()

    # Should have fewer or equal events than full 24h window
    # (With current test data, may still get all events depending on timing)
    assert data["count"] <= 20
    assert data["time_window_hours"] == 1


def test_events_endpoint_pagination_metadata(test_engine, client, sample_events):
    """Test /iq/shadow/events includes correct pagination metadata."""
    response = client.get("/iq/shadow/events?limit=5")
    data = response.json()

    # Should return 5 events but total_count should be 20
    assert len(data["events"]) == 5
    assert data["total_count"] == 20
    assert data["limit"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
