"""
ChainIQ ProofPack Tests

Tests for the /iq/proofpack/{shipment_id} endpoint.

The ProofPack endpoint bundles all ChainIQ/ChainPay state into a single
verifiable package for Space and Time integration and on-chain attestation.

Coverage:
- Happy path with risk + history data
- Graceful handling of shipments with no data (returns 200 with nulls)
- Respect for history_limit parameter
- Structural validation of ProofPackResponse
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile

# Import the main app
from api.server import app

client = TestClient(app)

# Set up test database
TEST_DB_PATH = Path(tempfile.mkdtemp()) / "test_chainiq_proofpack.db"


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


def _seed_risk_decisions(shipment_id: str, count: int) -> None:
    """
    Helper to seed multiple risk decisions for a shipment.

    This follows the same pattern as existing tests: score the shipment
    via the API endpoint multiple times to build up history.

    Args:
        shipment_id: Shipment identifier
        count: Number of risk decisions to create
    """
    for i in range(count):
        # Vary the payload slightly to create different scores
        payload = {
            "shipment_id": shipment_id,
            "route": "CN-US" if i % 2 == 0 else "DE-UK",
            "carrier_id": f"CARRIER-{i % 3 + 1:03d}",
            "shipment_value_usd": 10000.00 + (i * 5000.00),
            "days_in_transit": 5 + i,
            "expected_days": 7,
            "documents_complete": i % 2 == 0,
            "shipper_payment_score": 85 - (i * 5)
        }

        response = client.post("/iq/score-shipment", json=payload)
        assert response.status_code == 200


def test_proofpack_returns_bundle_with_risk_and_history() -> None:
    """
    Test that ProofPack returns a complete bundle with risk snapshot and history.

    Business Purpose:
    ProofPack must aggregate all available ChainIQ state for Space and Time
    verifiable analytics and on-chain attestation.

    Test Strategy:
    - Seed a shipment with multiple risk decisions
    - Verify ProofPack contains risk_snapshot and history
    - Do NOT require payment_queue_entry or options_advisor (may be None)
    """
    shipment_id = "PROOF-BUNDLE-001"

    # Seed 3 risk decisions to build history
    _seed_risk_decisions(shipment_id, 3)

    # Get ProofPack
    response = client.get(f"/iq/proofpack/{shipment_id}")
    assert response.status_code == 200

    data = response.json()

    # Validate top-level structure
    assert data["shipment_id"] == shipment_id
    assert data["version"] == "proofpack-v1"
    assert "generated_at" in data
    assert data["generated_at"] != ""

    # Validate risk_snapshot (latest risk)
    assert data["risk_snapshot"] is not None
    risk_snapshot = data["risk_snapshot"]
    assert "risk_score" in risk_snapshot
    assert isinstance(risk_snapshot["risk_score"], int)
    assert 0 <= risk_snapshot["risk_score"] <= 100
    assert "severity" in risk_snapshot
    assert risk_snapshot["severity"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert "recommended_action" in risk_snapshot
    assert "reason_codes" in risk_snapshot
    assert isinstance(risk_snapshot["reason_codes"], list)
    assert "last_scored_at" in risk_snapshot
    assert risk_snapshot["last_scored_at"] != ""

    # Validate history
    assert data["history"] is not None
    history = data["history"]
    assert history["entity_id"] == shipment_id
    assert history["total_records"] >= 3
    assert len(history["history"]) >= 3

    # Validate first history record structure
    first_record = history["history"][0]
    assert "timestamp" in first_record
    assert "score" in first_record
    assert "severity" in first_record
    assert "recommended_action" in first_record
    assert "payload" in first_record

    # payment_queue_entry and options_advisor may be None (not seeded)
    # This is expected behavior - graceful degradation


def test_proofpack_handles_shipment_with_no_data() -> None:
    """
    Test that ProofPack gracefully handles shipments with no data.

    Business Purpose:
    ProofPack should always return 200 (never 404) to support verifiable
    attestation even when data is unavailable. Empty ProofPack is valid.

    Test Strategy:
    - Request ProofPack for a shipment that has never been scored
    - Verify 200 status (not 404 or 500)
    - Verify ProofPack structure is valid but with null/empty fields
    """
    shipment_id = "PROOF-NO-DATA-001"

    # Do NOT seed any data - this shipment has never been scored

    # Get ProofPack
    response = client.get(f"/iq/proofpack/{shipment_id}")

    # Should still return 200 (graceful degradation)
    assert response.status_code == 200

    data = response.json()

    # Validate top-level structure
    assert data["shipment_id"] == shipment_id
    assert data["version"] == "proofpack-v1"
    assert "generated_at" in data
    assert data["generated_at"] != ""

    # All data components should be None or missing
    assert data.get("risk_snapshot") is None
    assert data.get("history") is None
    assert data.get("payment_queue_entry") is None
    assert data.get("options_advisor") is None


def test_proofpack_respects_history_limit() -> None:
    """
    Test that ProofPack respects the history_limit query parameter.

    Business Purpose:
    ProofPack must allow callers to control the amount of history returned
    to manage payload size for blockchain attestation.

    Test Strategy:
    - Seed a shipment with 5 risk decisions
    - Request ProofPack with history_limit=2
    - Verify history contains at most 2 records
    """
    shipment_id = "PROOF-LIMIT-001"

    # Seed 5 risk decisions
    _seed_risk_decisions(shipment_id, 5)

    # Get ProofPack with history_limit=2
    response = client.get(f"/iq/proofpack/{shipment_id}?history_limit=2")
    assert response.status_code == 200

    data = response.json()

    # Validate history respects limit
    assert data["history"] is not None
    history = data["history"]
    assert len(history["history"]) <= 2

    # Risk snapshot should still be present (not affected by history_limit)
    assert data["risk_snapshot"] is not None


def test_proofpack_invalid_history_limit() -> None:
    """
    Test that ProofPack validates history_limit parameter bounds.

    Business Purpose:
    Parameter validation prevents abuse and ensures reasonable payload sizes.

    Test Strategy:
    - Request ProofPack with history_limit=0 (below minimum)
    - Verify 400 Bad Request
    - Request ProofPack with history_limit=1000 (above maximum)
    - Verify 400 Bad Request
    """
    shipment_id = "PROOF-INVALID-LIMIT-001"

    # Seed one risk decision
    _seed_risk_decisions(shipment_id, 1)

    # Test history_limit too low
    response = client.get(f"/iq/proofpack/{shipment_id}?history_limit=0")
    assert response.status_code == 400
    assert "history_limit must be 1-500" in response.json()["detail"]

    # Test history_limit too high
    response = client.get(f"/iq/proofpack/{shipment_id}?history_limit=1000")
    assert response.status_code == 400
    assert "history_limit must be 1-500" in response.json()["detail"]


def test_proofpack_invalid_options_limit() -> None:
    """
    Test that ProofPack validates options_limit parameter bounds.

    Business Purpose:
    Parameter validation prevents abuse and ensures reasonable payload sizes.

    Test Strategy:
    - Request ProofPack with options_limit=0 (below minimum)
    - Verify 400 Bad Request
    - Request ProofPack with options_limit=20 (above maximum)
    - Verify 400 Bad Request
    """
    shipment_id = "PROOF-INVALID-OPT-LIMIT-001"

    # Seed one risk decision
    _seed_risk_decisions(shipment_id, 1)

    # Test options_limit too low
    response = client.get(f"/iq/proofpack/{shipment_id}?options_limit=0")
    assert response.status_code == 400
    assert "options_limit must be 1-10" in response.json()["detail"]

    # Test options_limit too high
    response = client.get(f"/iq/proofpack/{shipment_id}?options_limit=20")
    assert response.status_code == 400
    assert "options_limit must be 1-10" in response.json()["detail"]


def test_proofpack_with_default_parameters() -> None:
    """
    Test that ProofPack works with all default parameters.

    Business Purpose:
    Default parameters should provide sensible behavior without requiring
    callers to specify every parameter.

    Test Strategy:
    - Seed a shipment with risk decisions
    - Request ProofPack with no query parameters
    - Verify it returns valid data with defaults (history_limit=100, etc.)
    """
    shipment_id = "PROOF-DEFAULTS-001"

    # Seed 3 risk decisions
    _seed_risk_decisions(shipment_id, 3)

    # Get ProofPack with no parameters (should use defaults)
    response = client.get(f"/iq/proofpack/{shipment_id}")
    assert response.status_code == 200

    data = response.json()

    # Should have risk_snapshot and history with defaults
    assert data["risk_snapshot"] is not None
    assert data["history"] is not None
    assert data["history"]["total_records"] == 3
    assert len(data["history"]["history"]) == 3


def test_proofpack_timestamp_format() -> None:
    """
    Test that ProofPack generated_at timestamp is in ISO-8601 format.

    Business Purpose:
    Timestamps must be in a standard format for verifiable attestation
    and integration with Space and Time.

    Test Strategy:
    - Request ProofPack
    - Verify generated_at can be parsed as ISO-8601
    - Verify last_scored_at in risk_snapshot is ISO-8601
    """
    from datetime import datetime

    shipment_id = "PROOF-TIMESTAMP-001"

    # Seed one risk decision
    _seed_risk_decisions(shipment_id, 1)

    # Get ProofPack
    response = client.get(f"/iq/proofpack/{shipment_id}")
    assert response.status_code == 200

    data = response.json()

    # Validate generated_at is ISO-8601
    generated_at = data["generated_at"]
    try:
        # Should be parseable as ISO-8601
        datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
    except ValueError:
        pytest.fail(f"generated_at is not valid ISO-8601: {generated_at}")

    # Validate last_scored_at in risk_snapshot is ISO-8601
    risk_snapshot = data["risk_snapshot"]
    last_scored_at = risk_snapshot["last_scored_at"]
    try:
        # Should be parseable as ISO-8601 or SQL timestamp
        # Storage returns SQL TIMESTAMP format, which is ISO-8601 compatible
        datetime.fromisoformat(last_scored_at.replace('Z', '+00:00'))
    except ValueError:
        pytest.fail(f"last_scored_at is not valid ISO-8601: {last_scored_at}")
