"""
API Health Endpoint Smoke Tests

Minimal smoke tests to verify the ChainBridge API server boots and responds correctly.
Uses FastAPI TestClient for deterministic, side-effect-free testing.
"""

from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def test_health_endpoint_returns_200() -> None:
    """Verify health endpoint returns HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_returns_json() -> None:
    """Verify health endpoint returns valid JSON."""
    response = client.get("/health")
    data = response.json()
    assert isinstance(data, dict)


def test_health_endpoint_has_status_field() -> None:
    """Verify health endpoint includes status field."""
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_health_endpoint_has_required_fields() -> None:
    """Verify health endpoint includes all required fields."""
    response = client.get("/health")
    data = response.json()

    # Required fields from HealthResponse model
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data
    assert "modules_loaded" in data
    assert "active_pipelines" in data

    # Type checks
    assert isinstance(data["status"], str)
    assert isinstance(data["timestamp"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["modules_loaded"], int)
    assert isinstance(data["active_pipelines"], int)


def test_root_endpoint_returns_200() -> None:
    """Verify root endpoint returns HTTP 200."""
    response = client.get("/")
    assert response.status_code == 200


def test_root_endpoint_returns_api_info() -> None:
    """Verify root endpoint returns API information."""
    response = client.get("/")
    data = response.json()

    assert isinstance(data, dict)
    assert "message" in data
    assert "version" in data
    assert "health" in data
    assert data["health"] == "/health"
