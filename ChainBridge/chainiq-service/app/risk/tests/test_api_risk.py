"""Tests for the ChainIQ risk API router (skeleton)."""

import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.risk.api import router as risk_router
from app.risk.engine import compute_risk_score
from app.risk.schemas import CarrierProfile, LaneProfile, ShipmentFeatures


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(risk_router)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_score_shipment_low_risk_returns_low_band(client: TestClient):
    payload = {
        "shipment_id": "SHP-LOW-1",
        "carrier_id": "CARR-LOW",
        "origin": "US",
        "destination": "CA",
        "value_usd": 10_000,
        "is_hazmat": False,
        "is_temp_control": False,
        "expected_transit_days": 2,
        "iot_alert_count": 0,
        "recent_delay_events": 0,
    }

    response = client.post("/risk/score", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["risk_band"] == "LOW"


def test_score_shipment_high_risk_returns_high_band(client: TestClient):
    payload = {
        "shipment_id": "SHP-HIGH-1",
        "carrier_id": "CARR-HIGH",
        "origin": "US",
        "destination": "MX",  # triggers high lane risk
        "value_usd": 200_000,
        "is_hazmat": True,
        "is_temp_control": False,
        "expected_transit_days": 5,
        "iot_alert_count": 2,
        "recent_delay_events": 1,
    }

    response = client.post("/risk/score", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["risk_band"] == "HIGH"


def test_score_shipment_emits_structured_log_event(client: TestClient, capsys):
    payload = {
        "shipment_id": "SHP-LOG-1",
        "carrier_id": "CARR-LOG",
        "origin": "US",
        "destination": "CA",
        "value_usd": 50_000,
        "is_hazmat": False,
        "is_temp_control": False,
        "expected_transit_days": 3,
        "iot_alert_count": 1,
        "recent_delay_events": 0,
    }

    response = client.post("/risk/score", json=payload)
    assert response.status_code == 200
    body = response.json()

    captured = capsys.readouterr()
    log_lines = [line for line in captured.out.splitlines() if line.startswith("LOG_EVENT: ")]
    assert log_lines, "Expected structured LOG_EVENT output"

    payload_str = log_lines[-1].split("LOG_EVENT: ", 1)[1]
    event = json.loads(payload_str)

    assert event["event_type"] == "RISK_EVALUATION"
    uuid.UUID(event["evaluation_id"])
    assert event["model_version"] == "chainiq_v1_maggie"
    assert event["shipment_id"] == payload["shipment_id"]
    assert event["carrier_id"] == payload["carrier_id"]
    assert event["risk_score"] == body["risk_score"]
    assert event["risk_band"] == body["risk_band"]

    features = event["features_snapshot"]
    required_feature_keys = [
        "value_usd",
        "is_hazmat",
        "is_temp_control",
        "expected_transit_days",
        "iot_alert_count",
        "recent_delay_events",
        "lane_risk_index",
        "border_crossing_count",
    ]
    for key in required_feature_keys:
        assert key in features


def test_boundary_low_vs_medium_band(client: TestClient):
    base_payload = {
        "shipment_id": "SHP-BOUND-LOW-MED",
        "carrier_id": "CARR-BOUND",
        "origin": "US",
        "destination": "CA",
        "is_hazmat": False,
        "is_temp_control": False,
        "expected_transit_days": 2,
        "iot_alert_count": 0,
        "recent_delay_events": 0,
    }

    low_payload = {**base_payload, "value_usd": 10_000}
    medium_payload = {**base_payload, "destination": "MX", "value_usd": 50_000}

    low_resp = client.post("/risk/score", json=low_payload)
    med_resp = client.post("/risk/score", json=medium_payload)

    assert low_resp.status_code == 200
    assert med_resp.status_code == 200

    assert low_resp.json()["risk_band"] == "LOW"
    assert med_resp.json()["risk_band"] == "MEDIUM"


def test_boundary_medium_vs_high_band(client: TestClient):
    base_payload = {
        "shipment_id": "SHP-BOUND-MED-HIGH",
        "carrier_id": "CARR-BOUND",
        "origin": "US",
        "destination": "MX",  # high lane risk
        "is_hazmat": False,
        "is_temp_control": False,
        "expected_transit_days": 5,
        "recent_delay_events": 0,
    }

    medium_payload = {**base_payload, "value_usd": 10_000, "iot_alert_count": 0}
    high_payload = {**base_payload, "value_usd": 200_000, "iot_alert_count": 2}

    med_resp = client.post("/risk/score", json=medium_payload)
    high_resp = client.post("/risk/score", json=high_payload)

    assert med_resp.status_code == 200
    assert high_resp.status_code == 200

    assert high_resp.json()["risk_band"] == "HIGH"


def test_extreme_scenario_clamped_to_100(client: TestClient):
    payload = {
        "shipment_id": "SHP-CLAMP-1",
        "carrier_id": "CARR-CLAMP",
        "origin": "US",
        "destination": "MX",
        "value_usd": 10_000_000,
        "is_hazmat": True,
        "is_temp_control": False,
        "expected_transit_days": 10,
        "iot_alert_count": 50,
        "recent_delay_events": 5,
    }

    response = client.post("/risk/score", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["risk_score"] == 100


def test_score_shipment_boundary_low_medium(client: TestClient):
    payload_low = {
        "shipment_id": "SHP-BOUND-L",
        "carrier_id": "CARR-BOUND",
        "origin": "US",
        "destination": "CA",
        "value_usd": 10_000,
        "is_hazmat": False,
        "is_temp_control": False,
        "expected_transit_days": 2,
        "iot_alert_count": 0,
        "recent_delay_events": 0,
    }

    resp_low = client.post("/risk/score", json=payload_low)
    assert resp_low.status_code == 200
    body_low = resp_low.json()
    assert body_low["risk_band"] == "LOW"

    payload_med = {
        **payload_low,
        "destination": "MX",  # raises lane risk to 0.8 -> 80 base, expect HIGH
    }

    resp_med = client.post("/risk/score", json=payload_med)
    assert resp_med.status_code == 200
    body_med = resp_med.json()
    assert body_med["risk_band"] in ("MEDIUM", "HIGH")


def test_score_shipment_boundary_medium_high(client: TestClient):
    # MEDIUM case: low-risk lane with moderate amplifiers
    payload_med = {
        "shipment_id": "SHP-BOUND-M",
        "carrier_id": "CARR-BOUND-M",
        "origin": "US",
        "destination": "CA",  # lane_risk_index = 0.1 -> base 6 (0.1*60)
        "value_usd": 120_000,  # +15
        "is_hazmat": True,  # +10
        "is_temp_control": False,
        "expected_transit_days": 12,  # +5
        "iot_alert_count": 1,  # +10
        "recent_delay_events": 0,
    }

    resp_med = client.post("/risk/score", json=payload_med)
    assert resp_med.status_code == 200
    body_med = resp_med.json()
    assert body_med["risk_band"] == "MEDIUM"

    # HIGH case: high-risk lane with added amplifiers
    payload_high = {
        **payload_med,
        "destination": "MX",  # lane_risk_index = 0.8 -> base 48
        "value_usd": 120_000,  # +15
        "is_hazmat": True,  # +10
        "iot_alert_count": 1,  # +10
        "recent_delay_events": 1,  # +5
    }

    resp_high = client.post("/risk/score", json=payload_high)
    assert resp_high.status_code == 200
    body_high = resp_high.json()
    assert body_high["risk_band"] == "HIGH"


def test_score_shipment_clamps_to_100(client: TestClient):
    payload = {
        "shipment_id": "SHP-CLAMP",
        "carrier_id": "CARR-CLAMP",
        "origin": "US",
        "destination": "MX",
        "value_usd": 1_000_000,
        "is_hazmat": True,
        "is_temp_control": False,
        "expected_transit_days": 10,
        "iot_alert_count": 5,
        "recent_delay_events": 3,
    }

    resp = client.post("/risk/score", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_band"] == "HIGH"
    assert body["risk_score"] == 100


def test_trusted_carrier_discount_engine_level():
    lane = LaneProfile(origin="US", destination="CA", lane_risk_index=0.1, border_crossing_count=1)
    shipment = ShipmentFeatures(
        value_usd=20_000,
        is_hazmat=False,
        is_temp_control=False,
        expected_transit_days=5,
        iot_alert_count=0,
        recent_delay_events=0,
    )

    neutral_carrier = CarrierProfile(carrier_id="NEUTRAL", incident_rate_90d=0.02, tenure_days=200, on_time_rate=0.95)
    trusted_carrier = CarrierProfile(carrier_id="TRUSTED", incident_rate_90d=0.005, tenure_days=730, on_time_rate=0.95)

    neutral_result = compute_risk_score(shipment=shipment, carrier_profile=neutral_carrier, lane_profile=lane)
    trusted_result = compute_risk_score(shipment=shipment, carrier_profile=trusted_carrier, lane_profile=lane)

    assert trusted_result.score < neutral_result.score
    assert any("Trusted Carrier Discount" in r for r in trusted_result.reasons)


def test_bad_carrier_penalty_engine_level():
    lane = LaneProfile(origin="US", destination="CA", lane_risk_index=0.1, border_crossing_count=1)
    shipment = ShipmentFeatures(
        value_usd=20_000,
        is_hazmat=False,
        is_temp_control=False,
        expected_transit_days=5,
        iot_alert_count=0,
        recent_delay_events=0,
    )

    neutral_carrier = CarrierProfile(carrier_id="NEUTRAL", incident_rate_90d=0.02, tenure_days=200, on_time_rate=0.95)
    bad_carrier = CarrierProfile(carrier_id="BAD", incident_rate_90d=0.10, tenure_days=200, on_time_rate=0.95)

    neutral_result = compute_risk_score(shipment=shipment, carrier_profile=neutral_carrier, lane_profile=lane)
    bad_result = compute_risk_score(shipment=shipment, carrier_profile=bad_carrier, lane_profile=lane)

    assert bad_result.score > neutral_result.score
    assert any("High Carrier Incident Rate" in r for r in bad_result.reasons)
