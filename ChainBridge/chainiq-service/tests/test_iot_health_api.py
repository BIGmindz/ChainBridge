"""Tests for the ChainSense IoT health facade endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_iot_health_endpoint_returns_200() -> None:
    response = client.get("/iot/health")
    assert response.status_code == 200


def test_iot_health_response_shape() -> None:
    response = client.get("/iot/health")
    payload = response.json()

    assert "devices" in payload
    assert isinstance(payload["devices"], list)
    assert payload["devices"], "Expected at least one IoT device in payload"

    device = payload["devices"][0]
    expected_keys = {"id", "name", "status", "last_heartbeat", "risk_score"}
    assert expected_keys.issubset(device.keys())

    assert device["status"] in {"online", "offline", "degraded"}
    # Should be ISO-8601 compatible so Sonny can parse easily in the UI.
    datetime.fromisoformat(device["last_heartbeat"].replace("Z", "+00:00"))
    assert isinstance(device["risk_score"], (int, float))
