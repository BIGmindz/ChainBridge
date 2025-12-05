"""
API Health and Echo Endpoint Tests

Tests for visual heartbeat endpoints: GET /health and POST /events/echo.
Uses FastAPI TestClient for deterministic, side-effect-free testing.
"""

from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    """Verify health endpoint returns HTTP 200 and status."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)
    assert "status" in data
    assert data["status"] == "healthy"


def test_health_has_service_metadata() -> None:
    """Verify health endpoint includes service metadata."""
    response = client.get("/health")
    data = response.json()

    # Check for required fields
    assert "status" in data
    assert "version" in data
    assert "timestamp" in data

    # Verify types
    assert isinstance(data["status"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["timestamp"], str)


def test_echo_round_trip() -> None:
    """Verify echo endpoint returns the payload back."""
    payload = {"shipment_id": "ABC123", "amount": 100, "status": "pending"}

    response = client.post("/events/echo", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)

    # The DataProcessor.process() wraps the payload
    assert "original" in data
    assert data["original"] == payload
    assert "processed_at" in data


def test_echo_with_complex_payload() -> None:
    """Verify echo handles complex nested payloads."""
    payload = {
        "event_type": "shipment.updated",
        "data": {
            "id": "SHIP-001",
            "items": [
                {"sku": "ITEM-1", "quantity": 5},
                {"sku": "ITEM-2", "quantity": 3},
            ],
            "metadata": {"source": "warehouse-a", "priority": "high"},
        },
        "timestamp": "2025-11-15T10:00:00Z",
    }

    response = client.post("/events/echo", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "original" in data
    assert data["original"] == payload
    assert data["original"]["event_type"] == "shipment.updated"


def test_echo_empty_payload() -> None:
    """Verify echo handles empty JSON object."""
    payload = {}

    response = client.post("/events/echo", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "original" in data
    assert data["original"] == {}


def test_health_endpoint_is_deterministic() -> None:
    """Verify health endpoint returns consistent structure across calls."""
    response1 = client.get("/health")
    response2 = client.get("/health")

    data1 = response1.json()
    data2 = response2.json()

    # Same keys should exist
    assert set(data1.keys()) == set(data2.keys())

    # Status and version should be consistent
    assert data1["status"] == data2["status"]
    assert data1["version"] == data2["version"]


def test_echo_rejects_missing_body() -> None:
    """
    /events/echo should return 422 when the JSON body is missing.

    FastAPI's automatic validation returns 422 Unprocessable Entity
    for missing required request bodies.
    """
    response = client.post("/events/echo")
    assert response.status_code == 422

    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data

    # FastAPI returns a list of validation errors
    assert isinstance(data["detail"], list)
    assert len(data["detail"]) > 0

    # First error should indicate missing body
    error = data["detail"][0]
    assert "body" in error.get("loc", [])


def test_echo_rejects_invalid_json() -> None:
    """
    /events/echo should return 400 or 422 when invalid JSON is sent.

    FastAPI may return 400 (Bad Request) or 422 (Unprocessable Entity)
    depending on how the malformed JSON is detected.
    """
    response = client.post(
        "/events/echo",
        data="{not: 'json'}",
        headers={"Content-Type": "application/json"},
    )

    # Accept either 400 or 422
    assert response.status_code in [400, 422]

    data = response.json()
    assert isinstance(data, dict)
    assert "detail" in data
