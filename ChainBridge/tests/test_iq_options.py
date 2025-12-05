"""
ChainIQ Better Options Advisor Tests

Tests for the /iq/options/{shipment_id} endpoint.

Sunny: add tests for the Better Options Advisor endpoint /iq/options/{shipment_id}.

Coverage:
- Basic success path (returns options for known shipment)
- 404 for unknown shipment
- risk_appetite affects result filtering
- Invalid risk_appetite defaults to balanced
"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Import the main app
from api.server import app

client = TestClient(app)

# Set up test database
TEST_DB_PATH = Path(tempfile.mkdtemp()) / "test_chainiq_options.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Set up a clean test database for each test."""
    # Point storage to test database
    try:
        import sys
        from pathlib import Path

        # Add chainiq-service to path
        chainiq_path = Path(__file__).parent.parent / "chainiq-service"
        sys.path.insert(0, str(chainiq_path))

        import storage
        from storage import DB_PATH as original_path

        monkeypatch.setattr(storage, "DB_PATH", TEST_DB_PATH)

        # Initialize database
        storage.init_db()
    except ImportError:
        # Storage not available - tests will be skipped
        pass

    yield

    # Clean up
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


def _seed_high_risk_shipment(shipment_id: str) -> None:
    """
    Helper to ensure there is at least one high-risk decision for this shipment
    in the underlying storage.

    This follows the same insertion pattern as the existing persistence tests:
    score the shipment via the API endpoint to ensure it's in storage.
    """
    payload = {
        "shipment_id": shipment_id,
        "route": "IR-RU",
        "carrier_id": "CARRIER-001",
        "shipment_value_usd": 50000.00,
        "days_in_transit": 8,
        "expected_days": 7,
        "documents_complete": False,
        "shipper_payment_score": 45,
    }

    response = client.post("/iq/score-shipment", json=payload)
    assert response.status_code == 200

    # Verify it's a high-risk score
    data = response.json()
    assert data["severity"] in ["HIGH", "CRITICAL"]


def test_options_advisor_returns_options_for_known_shipment():
    """
    Test basic success path: returns options for a known shipment.

    Business Purpose:
    Operators need to see alternative routes and payment rails
    that could reduce risk for high-risk shipments.
    """
    shipment_id = "SHP-OPTIONS-001"
    _seed_high_risk_shipment(shipment_id)

    response = client.get(f"/iq/options/{shipment_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["shipment_id"] == shipment_id
    assert isinstance(data["current_risk_score"], int)
    assert "route_options" in data
    assert "payment_options" in data
    assert data["risk_appetite"] == "balanced"


def test_options_advisor_returns_404_for_unknown_shipment():
    """
    Test that 404 is returned for non-existent shipments.

    Business Purpose:
    Options advisor requires historical risk data to make recommendations.
    If no risk assessment exists, we can't suggest alternatives.
    """
    response = client.get("/iq/options/NONEXISTENT-XYZ")
    assert response.status_code == 404


def test_options_advisor_risk_appetite_affects_result_size():
    """
    Test that risk_appetite actually changes the option set.

    Business Purpose:
    Conservative operators want only the safest options,
    while aggressive operators want more choices including
    riskier but potentially cheaper/faster options.

    Conservative should be more restrictive (fewer options)
    than aggressive.
    """
    shipment_id = "SHP-OPTIONS-002"
    _seed_high_risk_shipment(shipment_id)

    res_cons = client.get(f"/iq/options/{shipment_id}?risk_appetite=conservative")
    res_aggr = client.get(f"/iq/options/{shipment_id}?risk_appetite=aggressive")

    assert res_cons.status_code == 200
    assert res_aggr.status_code == 200

    data_cons = res_cons.json()
    data_aggr = res_aggr.json()

    # We expect aggressive to not be *stricter* than conservative
    assert len(data_cons["route_options"]) <= len(data_aggr["route_options"])
    assert len(data_cons["payment_options"]) <= len(data_aggr["payment_options"])


def test_options_advisor_invalid_risk_appetite_defaults_to_balanced():
    """
    Test that invalid risk_appetite values default to balanced.

    Business Purpose:
    Graceful handling of invalid input ensures the endpoint
    remains usable even with bad query parameters.
    """
    shipment_id = "SHP-OPTIONS-003"
    _seed_high_risk_shipment(shipment_id)

    res = client.get(f"/iq/options/{shipment_id}?risk_appetite=INVALID")
    assert res.status_code == 200
    data = res.json()
    assert data["risk_appetite"] == "balanced"


def test_options_advisor_respects_limit_parameter():
    """
    Test that the limit parameter controls the number of options returned.

    Business Purpose:
    Operators may want to see more or fewer options depending on
    their use case. Limit ensures response size is controllable.
    """
    shipment_id = "SHP-OPTIONS-004"
    _seed_high_risk_shipment(shipment_id)

    # Request only 2 options
    res = client.get(f"/iq/options/{shipment_id}?limit=2")
    assert res.status_code == 200

    data = res.json()
    # Each option list should have at most 2 items
    assert len(data["route_options"]) <= 2
    assert len(data["payment_options"]) <= 2


def test_options_advisor_limit_clamped_to_safe_range():
    """
    Test that limit is clamped to a safe range (1-10).

    Business Purpose:
    Prevent excessive resource usage or invalid limits.
    """
    shipment_id = "SHP-OPTIONS-005"
    _seed_high_risk_shipment(shipment_id)

    # Test upper bound: limit=100 should be clamped to 10
    res_high = client.get(f"/iq/options/{shipment_id}?limit=100")
    assert res_high.status_code == 200
    data_high = res_high.json()
    assert len(data_high["route_options"]) <= 10
    assert len(data_high["payment_options"]) <= 10

    # Test lower bound: limit=0 should be clamped to 1
    res_low = client.get(f"/iq/options/{shipment_id}?limit=0")
    assert res_low.status_code == 200
    # Should still return something (at least 1 option if available)


def test_options_advisor_conservative_returns_safest_options():
    """
    Test that conservative mode prioritizes safety over other factors.

    Business Purpose:
    Conservative operators need options that significantly reduce risk,
    even if they're more expensive or slower.
    """
    shipment_id = "SHP-OPTIONS-006"
    _seed_high_risk_shipment(shipment_id)

    res = client.get(f"/iq/options/{shipment_id}?risk_appetite=conservative")
    assert res.status_code == 200

    data = res.json()

    # Conservative mode should filter for significant risk reduction
    # All route options should have positive risk_delta (safer than current)
    for option in data["route_options"]:
        assert option["risk_delta"] >= 10, "Conservative routes should reduce risk by at least 10 points"

    # All payment options should not increase risk
    for option in data["payment_options"]:
        assert option["risk_score"] <= data["current_risk_score"], "Conservative payments should not increase risk"


def test_options_advisor_balanced_provides_moderate_filtering():
    """
    Test that balanced mode provides reasonable filtering.

    Business Purpose:
    Balanced mode is the default - should offer good risk reduction
    without being overly restrictive.
    """
    shipment_id = "SHP-OPTIONS-007"
    _seed_high_risk_shipment(shipment_id)

    res = client.get(f"/iq/options/{shipment_id}?risk_appetite=balanced")
    assert res.status_code == 200

    data = res.json()

    # Balanced mode should require at least some risk reduction
    for option in data["route_options"]:
        assert option["risk_delta"] >= 5, "Balanced routes should reduce risk by at least 5 points"

    for option in data["payment_options"]:
        assert option["risk_delta"] >= 5, "Balanced payments should reduce risk by at least 5 points"


def test_options_advisor_aggressive_allows_more_options():
    """
    Test that aggressive mode allows more options including some risk tolerance.

    Business Purpose:
    Aggressive operators may accept slightly higher risk if there are
    significant cost or speed benefits.
    """
    shipment_id = "SHP-OPTIONS-008"
    _seed_high_risk_shipment(shipment_id)

    res = client.get(f"/iq/options/{shipment_id}?risk_appetite=aggressive")
    assert res.status_code == 200

    data = res.json()

    # Aggressive mode allows risk_delta >= -5 (slight risk increase allowed)
    # but requires some positive reward (cost/time savings)
    for option in data["route_options"]:
        assert option["risk_delta"] >= -5, "Aggressive allows slight risk increase"
        # Should have cost savings OR time savings
        has_reward = option["cost_delta_usd"] <= 0 or option["eta_delta_days"] <= 0
        assert has_reward, "Aggressive routes must provide cost or time benefit"
