"""
ChainIQ Risk Scoring Tests

Tests for the shipment risk scoring engine and API endpoint.

Design Principles:
- Deterministic: Same input always produces same output
- No external dependencies: No network, no DB, no file I/O
- Fast: All tests run in <1s
- Comprehensive: Positive, negative, and edge cases
"""

import pytest
from fastapi.testclient import TestClient

# Import the main app
from api.server import app

client = TestClient(app)


def test_valid_request_scores_correctly() -> None:
    """
    Test that a valid shipment request returns a correct risk score.

    Business Context:
    Low-risk shipment (good route, reliable carrier, normal value, on-time, complete docs)
    should score LOW and recommend RELEASE_PAYMENT.
    """
    payload = {
        "shipment_id": "SHP-TEST-001",
        "route": "US-CA",
        "carrier_id": "CARRIER-001",
        "shipment_value_usd": 25000.00,
        "days_in_transit": 5,
        "expected_days": 7,
        "documents_complete": True,
        "shipper_payment_score": 85,
    }

    response = client.post("/api/iq/score-shipment", json=payload)

    assert response.status_code == 200

    data = response.json()
    assert data["shipment_id"] == "SHP-TEST-001"
    assert isinstance(data["risk_score"], int)
    assert 0 <= data["risk_score"] <= 100
    assert data["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert isinstance(data["reason_codes"], list)
    assert data["recommended_action"] in [
        "RELEASE_PAYMENT",
        "MANUAL_REVIEW",
        "HOLD_PAYMENT",
        "ESCALATE_COMPLIANCE",
    ]

    # This specific low-risk scenario should be LOW severity
    assert data["severity"] == "LOW"
    assert data["recommended_action"] == "RELEASE_PAYMENT"


def test_high_risk_route_scores_high() -> None:
    """
    Test that a high-risk route (sanctioned country) scores HIGH or CRITICAL.

    Business Decision:
    Shipments involving sanctioned countries should trigger holds.
    """
    payload = {
        "shipment_id": "SHP-TEST-002",
        "route": "IR-RU",  # Iran to Russia (both sanctioned)
        "carrier_id": "CARRIER-001",
        "shipment_value_usd": 50000.00,
        "days_in_transit": 5,
        "expected_days": 7,
        "documents_complete": False,
        "shipper_payment_score": 40,
    }

    response = client.post("/api/iq/score-shipment", json=payload)

    assert response.status_code == 200

    data = response.json()
    assert data["risk_score"] >= 60  # Should be HIGH or CRITICAL
    assert data["severity"] in ["HIGH", "CRITICAL"]
    assert "HIGH_RISK_ROUTE" in data["reason_codes"]
    assert data["recommended_action"] in ["HOLD_PAYMENT", "ESCALATE_COMPLIANCE"]


def test_missing_required_fields_rejected() -> None:
    """
    Test that requests missing required fields are rejected with 422.

    FastAPI's automatic validation should catch this before our code runs.
    """
    payload = {
        "shipment_id": "SHP-TEST-003",
        "route": "US-CA",
        # Missing carrier_id, shipment_value_usd, etc.
    }

    response = client.post("/api/iq/score-shipment", json=payload)

    assert response.status_code == 422  # Validation error

    data = response.json()
    assert "detail" in data


def test_invalid_field_types_rejected() -> None:
    """
    Test that invalid field types are rejected.

    Example: shipment_value_usd as string instead of float.
    """
    payload = {
        "shipment_id": "SHP-TEST-004",
        "route": "US-CA",
        "carrier_id": "CARRIER-001",
        "shipment_value_usd": "invalid",  # Should be float
        "days_in_transit": 5,
        "expected_days": 7,
        "documents_complete": True,
        "shipper_payment_score": 85,
    }

    response = client.post("/api/iq/score-shipment", json=payload)

    assert response.status_code == 422


def test_negative_values_rejected() -> None:
    """
    Test that negative values for numeric fields are rejected.

    Pydantic validation should enforce ge=0 constraints.
    """
    payload = {
        "shipment_id": "SHP-TEST-005",
        "route": "US-CA",
        "carrier_id": "CARRIER-001",
        "shipment_value_usd": -1000.00,  # Invalid: negative
        "days_in_transit": 5,
        "expected_days": 7,
        "documents_complete": True,
        "shipper_payment_score": 85,
    }

    response = client.post("/api/iq/score-shipment", json=payload)

    assert response.status_code == 422


def test_out_of_range_payment_score_rejected() -> None:
    """
    Test that payment scores outside 0-100 range are rejected.
    """
    payload = {
        "shipment_id": "SHP-TEST-006",
        "route": "US-CA",
        "carrier_id": "CARRIER-001",
        "shipment_value_usd": 25000.00,
        "days_in_transit": 5,
        "expected_days": 7,
        "documents_complete": True,
        "shipper_payment_score": 150,  # Invalid: > 100
    }

    response = client.post("/api/iq/score-shipment", json=payload)

    assert response.status_code == 422


def test_edge_case_zero_days_in_transit() -> None:
    """
    Test edge case: shipment just started (0 days in transit).

    Should still produce a valid score.
    """
    payload = {
        "shipment_id": "SHP-TEST-007",
        "route": "US-CA",
        "carrier_id": "CARRIER-001",
        "shipment_value_usd": 25000.00,
        "days_in_transit": 0,
        "expected_days": 7,
        "documents_complete": True,
        "shipper_payment_score": 85,
    }

    response = client.post("/api/iq/score-shipment", json=payload)

    assert response.status_code == 200

    data = response.json()
    assert data["risk_score"] >= 0
    assert data["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_edge_case_no_reason_codes() -> None:
    """
    Test edge case: perfect shipment with no risk factors.

    Should return LOW severity with empty or minimal reason codes.
    """
    payload = {
        "shipment_id": "SHP-TEST-008",
        "route": "US-CA",
        "carrier_id": "CARRIER-001",
        "shipment_value_usd": 5000.00,  # Low value
        "days_in_transit": 5,
        "expected_days": 7,  # On time
        "documents_complete": True,
        "shipper_payment_score": 95,  # Excellent history
    }

    response = client.post("/api/iq/score-shipment", json=payload)

    assert response.status_code == 200

    data = response.json()
    assert data["severity"] == "LOW"
    assert data["recommended_action"] == "RELEASE_PAYMENT"
    # May have zero or minimal reason codes
    assert len(data["reason_codes"]) <= 2


def test_deterministic_scoring() -> None:
    """
    Test that the same input produces the same output (deterministic).

    Critical for testing and debugging: no randomness allowed.
    """
    payload = {
        "shipment_id": "SHP-TEST-009",
        "route": "CN-US",
        "carrier_id": "CARRIER-001",
        "shipment_value_usd": 75000.00,
        "days_in_transit": 10,
        "expected_days": 7,
        "documents_complete": True,
        "shipper_payment_score": 70,
    }

    # Call endpoint twice
    response1 = client.post("/api/iq/score-shipment", json=payload)
    response2 = client.post("/api/iq/score-shipment", json=payload)

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    # Scores must be identical
    assert data1["risk_score"] == data2["risk_score"]
    assert data1["severity"] == data2["severity"]
    assert data1["reason_codes"] == data2["reason_codes"]
    assert data1["recommended_action"] == data2["recommended_action"]


def test_suspiciously_early_shipment() -> None:
    """
    Test that shipments arriving much earlier than expected are flagged.

    Business Context:
    Suspiciously early arrivals can indicate fraud or misreporting.
    """
    payload = {
        "shipment_id": "SHP-TEST-010",
        "route": "US-CA",
        "carrier_id": "CARRIER-001",
        "shipment_value_usd": 25000.00,
        "days_in_transit": 2,
        "expected_days": 10,  # Way too early
        "documents_complete": True,
        "shipper_payment_score": 85,
    }

    response = client.post("/api/iq/score-shipment", json=payload)

    assert response.status_code == 200

    data = response.json()
    assert "SUSPICIOUSLY_EARLY" in data["reason_codes"]
    # Should increase risk score
    assert data["risk_score"] > 0
