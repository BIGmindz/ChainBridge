"""API-level tests for IoT-driven risk adjustments in ChainIQ.

These tests exercise the glass-box IoT rules via the unified
FastAPI application and the /iq/score-shipment endpoint.
"""

from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


def _base_payload() -> dict:
    """Low-risk baseline payload without IoT signals."""

    return {
        "shipment_id": "SHP-IOT-BASE",
        "route": "CN-US",
        "carrier_id": "CARRIER-TRUSTED",
        "shipment_value_usd": 100_000,
        "days_in_transit": 3,
        "expected_days": 5,
        "documents_complete": True,
        "shipper_payment_score": 90,
    }


def test_fresh_damage_rule_increases_score_via_api() -> None:
    """Critical IoT alerts in last 24h should uplift risk score by +40."""

    payload = _base_payload()

    # Baseline: no IoT
    r_base = client.post("/api/iq/score-shipment", json=payload)
    assert r_base.status_code == 200
    base = r_base.json()
    base_score = base["risk_score"]
    base_reasons = base.get("reason_codes", [])

    # With Fresh Damage IoT
    payload_iot = {**payload, "iot_signals": {"critical_count_24h": 1}}
    r_iot = client.post("/api/iq/score-shipment", json=payload_iot)
    assert r_iot.status_code == 200
    iot = r_iot.json()
    iot_score = iot["risk_score"]
    iot_reasons = iot.get("reason_codes", [])

    assert iot_score == base_score + 40
    assert "IOT_FRESH_DAMAGE" in iot_reasons
    assert "IOT_FRESH_DAMAGE" not in base_reasons


def test_ghosting_rule_24h_stronger_than_4h_via_api() -> None:
    """Silence of 24h should be scored higher risk than 4h."""

    payload = _base_payload()

    payload_4h = {**payload, "iot_signals": {"silence_hours": 4.0}}
    r_4h = client.post("/api/iq/score-shipment", json=payload_4h)
    assert r_4h.status_code == 200
    four = r_4h.json()
    four_score = four["risk_score"]
    four_reasons = four.get("reason_codes", [])

    payload_24h = {**payload, "iot_signals": {"silence_hours": 24.0}}
    r_24h = client.post("/api/iq/score-shipment", json=payload_24h)
    assert r_24h.status_code == 200
    twentyfour = r_24h.json()
    twentyfour_score = twentyfour["risk_score"]
    twentyfour_reasons = twentyfour.get("reason_codes", [])

    assert twentyfour_score > four_score
    assert (twentyfour_score - four_score) >= 30
    assert any("IOT_GHOSTING" in rc for rc in twentyfour_reasons)
    assert any("IOT_GHOSTING" in rc for rc in four_reasons)


def test_corridor_chaos_rule_applies_at_high_instability_via_api() -> None:
    """High corridor instability should add +10 risk with a reason code."""

    payload = _base_payload()

    low_payload = {**payload, "iot_signals": {"corridor_instability_index": 0.5}}
    r_low = client.post("/api/iq/score-shipment", json=low_payload)
    assert r_low.status_code == 200
    low_score = r_low.json()["risk_score"]

    high_payload = {**payload, "iot_signals": {"corridor_instability_index": 0.8}}
    r_high = client.post("/api/iq/score-shipment", json=high_payload)
    assert r_high.status_code == 200
    high_json = r_high.json()
    high_score = high_json["risk_score"]
    high_reasons = high_json.get("reason_codes", [])

    assert high_score == low_score + 10
    assert "IOT_CORRIDOR_CHAOS" in high_reasons


def test_combined_iot_effects_clamped_to_100_via_api() -> None:
    """Stacked IoT effects must be clamped to a max score of 100."""

    # High-risk baseline, similar spirit to existing IQ risk tests
    payload = {
        "shipment_id": "SHP-IOT-STACKED",
        "route": "IR-RU",
        "carrier_id": "CARRIER-999",
        "shipment_value_usd": 5_000_000,
        "days_in_transit": 30,
        "expected_days": 10,
        "documents_complete": False,
        "shipper_payment_score": 20,
    }
    r_base = client.post("/api/iq/score-shipment", json=payload)
    assert r_base.status_code == 200
    base = r_base.json()
    base_score = base["risk_score"]
    assert base_score <= 100

    stacked_payload = {
        **payload,
        "iot_signals": {
            "critical_count_24h": 3,
            "silence_hours": 48.0,
            "corridor_instability_index": 0.9,
            "battery_health_score": 0.1,
        },
    }
    r_stacked = client.post("/api/iq/score-shipment", json=stacked_payload)
    assert r_stacked.status_code == 200
    stacked = r_stacked.json()
    stacked_score = stacked["risk_score"]
    stacked_reasons = stacked.get("reason_codes", [])

    assert stacked_score == 100
    assert any(rc.startswith("IOT_") for rc in stacked_reasons)
