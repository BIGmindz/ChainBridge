"""
ChainIQ Option Simulation Tests

Tests for the /iq/options/{shipment_id}/simulate endpoint.

The simulation endpoint provides sandbox "what-if" risk analysis for
route and payment rail options without persisting any results.

Coverage:
- Happy path with known shipment
- 404 for unknown shipment
- No persistence side effects
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile

# Import the main app
from api.server import app

client = TestClient(app)

# Set up test database
TEST_DB_PATH = Path(tempfile.mkdtemp()) / "test_chainiq_simulation.db"


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

        from storage import DB_PATH as original_path
        import storage

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
    Helper to seed a high-risk shipment with scoring history.

    This ensures we have baseline context for simulation.
    """
    payload = {
        "shipment_id": shipment_id,
        "route": "IR-RU",
        "carrier_id": "CARRIER-001",
        "shipment_value_usd": 50000.00,
        "days_in_transit": 8,
        "expected_days": 7,
        "documents_complete": False,
        "shipper_payment_score": 45
    }

    response = client.post("/iq/score-shipment", json=payload)
    assert response.status_code == 200


def test_simulation_returns_result_for_known_shipment() -> None:
    """
    Test that simulation returns valid result for a shipment with history.

    Business Purpose:
    Operators need to test route/payment options safely before committing.
    """
    shipment_id = "SIM-TEST-001"

    # Seed a high-risk shipment
    _seed_high_risk_shipment(shipment_id)

    # Simulate a safer route option
    simulation_request = {
        "option_type": "route",
        "option_id": "ROUTE-US-CA-CARRIER-002"
    }

    response = client.post(
        f"/iq/options/{shipment_id}/simulate",
        json=simulation_request
    )

    assert response.status_code == 200

    data = response.json()

    # Validate response structure
    assert data["shipment_id"] == shipment_id
    assert data["option_type"] == "route"
    assert data["option_id"] == "ROUTE-US-CA-CARRIER-002"

    # Validate risk scores
    assert "baseline_risk_score" in data
    assert isinstance(data["baseline_risk_score"], int)
    assert 0 <= data["baseline_risk_score"] <= 100

    assert "simulated_risk_score" in data
    assert isinstance(data["simulated_risk_score"], int)
    assert 0 <= data["simulated_risk_score"] <= 100

    # Validate severity
    assert "baseline_severity" in data
    assert data["baseline_severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    assert "simulated_severity" in data
    assert data["simulated_severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    # Validate risk delta
    assert "risk_delta" in data
    assert isinstance(data["risk_delta"], int)
    assert data["risk_delta"] == data["baseline_risk_score"] - data["simulated_risk_score"]

    # Validate notes
    assert "notes" in data
    assert isinstance(data["notes"], list)
    assert len(data["notes"]) > 0
    assert any("Sandbox simulation" in note for note in data["notes"])


def test_simulation_returns_404_for_unknown_shipment() -> None:
    """
    Test that simulation returns 404 for shipments with no history.

    Business Purpose:
    Can't simulate options for shipments that haven't been scored yet.
    """
    shipment_id = "SIM-UNKNOWN-001"

    # Do NOT seed - this shipment has never been scored

    simulation_request = {
        "option_type": "route",
        "option_id": "ROUTE-US-CA-CARRIER-002"
    }

    response = client.post(
        f"/iq/options/{shipment_id}/simulate",
        json=simulation_request
    )

    assert response.status_code == 404
    assert "No scoring history" in response.json()["detail"]


def test_simulation_does_not_persist_new_history() -> None:
    """
    Test that simulation does NOT create new history records.

    Business Purpose:
    Simulation is sandbox-only. It must not pollute production data.
    This is the critical test for read-only guarantee.
    """
    shipment_id = "SIM-NO-PERSIST-001"

    # Seed initial shipment
    _seed_high_risk_shipment(shipment_id)

    # Get initial history count
    history_response = client.get(f"/iq/history/{shipment_id}")
    assert history_response.status_code == 200
    initial_count = history_response.json()["total_records"]

    # Run simulation 3 times
    for i in range(3):
        simulation_request = {
            "option_type": "route",
            "option_id": f"ROUTE-TEST-{i}"
        }

        sim_response = client.post(
            f"/iq/options/{shipment_id}/simulate",
            json=simulation_request
        )
        assert sim_response.status_code == 200

    # Get history count after simulations
    history_response_after = client.get(f"/iq/history/{shipment_id}")
    assert history_response_after.status_code == 200
    final_count = history_response_after.json()["total_records"]

    # CRITICAL: History count must NOT have changed
    assert final_count == initial_count, (
        f"Simulation created new history! "
        f"Before: {initial_count}, After: {final_count}"
    )


def test_simulation_with_payment_rail_option() -> None:
    """
    Test simulation with payment rail option.

    Business Purpose:
    Operators should be able to test payment rail changes.

    Note:
        For v0, payment rail doesn't affect risk score (not in risk model yet).
        This test validates the endpoint works without crashing.
    """
    shipment_id = "SIM-PAYMENT-001"

    # Seed shipment
    _seed_high_risk_shipment(shipment_id)

    # Simulate payment rail change
    simulation_request = {
        "option_type": "payment_rail",
        "option_id": "RAIL-XRPL-INSTANT"
    }

    response = client.post(
        f"/iq/options/{shipment_id}/simulate",
        json=simulation_request
    )

    assert response.status_code == 200

    data = response.json()
    assert data["option_type"] == "payment_rail"
    assert data["option_id"] == "RAIL-XRPL-INSTANT"

    # For v0, payment rail doesn't change risk
    # Risk delta should be 0 or baseline == simulated
    assert data["baseline_risk_score"] == data["simulated_risk_score"]


def test_simulation_with_invalid_option_type() -> None:
    """
    Test that invalid option_type is rejected by Pydantic validation.

    Business Purpose:
    API should reject malformed requests early.
    """
    shipment_id = "SIM-INVALID-001"

    # Seed shipment
    _seed_high_risk_shipment(shipment_id)

    # Try invalid option_type
    simulation_request = {
        "option_type": "invalid_type",
        "option_id": "TEST-001"
    }

    response = client.post(
        f"/iq/options/{shipment_id}/simulate",
        json=simulation_request
    )

    # Pydantic validation should reject this
    assert response.status_code == 422


def test_simulation_safer_route_reduces_risk() -> None:
    """
    Test that simulating a safer route reduces risk score.

    Business Purpose:
    Validate that the simulation logic correctly applies route changes.
    """
    shipment_id = "SIM-SAFER-001"

    # Seed a high-risk shipment (IR-RU route)
    _seed_high_risk_shipment(shipment_id)

    # Simulate a much safer route (US-CA)
    simulation_request = {
        "option_type": "route",
        "option_id": "ROUTE-US-CA-CARRIER-001"
    }

    response = client.post(
        f"/iq/options/{shipment_id}/simulate",
        json=simulation_request
    )

    assert response.status_code == 200

    data = response.json()

    # US-CA should be significantly safer than IR-RU
    # risk_delta should be positive (baseline higher than simulated)
    assert data["risk_delta"] > 0, (
        f"Expected safer route to reduce risk. "
        f"Baseline: {data['baseline_risk_score']}, "
        f"Simulated: {data['simulated_risk_score']}, "
        f"Delta: {data['risk_delta']}"
    )

    # Simulated severity should be better than baseline
    severity_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    baseline_severity_idx = severity_order[data["baseline_severity"]]
    simulated_severity_idx = severity_order[data["simulated_severity"]]

    assert simulated_severity_idx <= baseline_severity_idx, (
        f"Expected safer severity. "
        f"Baseline: {data['baseline_severity']}, "
        f"Simulated: {data['simulated_severity']}"
    )
