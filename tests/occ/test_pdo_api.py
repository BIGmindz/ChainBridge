"""
PDO API Endpoint Tests — PAC-CODY-PDO-HARDEN-01

Tests that verify:
1. POST /pdo creates PDOs (append-only)
2. GET /pdo/{id} reads PDOs with integrity check
3. PUT /pdo/{id} returns 405 Method Not Allowed
4. PATCH /pdo/{id} returns 405 Method Not Allowed
5. DELETE /pdo/{id} returns 405 Method Not Allowed

These tests ensure API-level rejection of mutation requests.

Author: CODY (GID-01) - Backend
"""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.server import app
from core.occ.schemas.pdo import PDOOutcome, PDOSourceSystem
from core.occ.store.pdo_store import PDOStore, get_pdo_store, reset_pdo_store


@pytest.fixture(autouse=True)
def reset_store(tmp_path, monkeypatch):
    """Reset PDO store before each test with isolated storage."""
    reset_pdo_store()
    # Use a unique temp file for each test
    temp_file = tmp_path / "test_pdos.json"
    monkeypatch.setenv("CHAINBRIDGE_PDO_STORE_PATH", str(temp_file))
    reset_pdo_store()  # Reset again to pick up new env var
    yield
    reset_pdo_store()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_pdo_payload():
    """Valid PDO creation payload."""
    return {
        "input_refs": ["artifact-123", "data-456"],
        "decision_ref": "decision-789",
        "outcome_ref": "outcome-abc",
        "outcome": "approved",
        "source_system": "gateway",
        "actor": "CODY-GID-01",
        "actor_type": "agent",
        "correlation_id": "corr-test-001",
        "metadata": {"test": True},
        "tags": ["test", "api-test"],
    }


# =============================================================================
# CREATE ENDPOINT TESTS (APPEND-ONLY)
# =============================================================================


class TestPDOCreateEndpoint:
    """Tests for POST /pdo endpoint."""

    def test_create_pdo_success(self, client, valid_pdo_payload):
        """POST /pdo creates a new PDO."""
        response = client.post("/pdo", json=valid_pdo_payload)

        assert response.status_code == 201
        data = response.json()

        assert "pdo_id" in data
        assert data["decision_ref"] == valid_pdo_payload["decision_ref"]
        assert data["outcome"] == valid_pdo_payload["outcome"]
        assert data["hash"] is not None
        assert len(data["hash"]) == 64  # SHA-256 hex

    def test_create_pdo_generates_hash(self, client, valid_pdo_payload):
        """Created PDO has a valid hash seal."""
        response = client.post("/pdo", json=valid_pdo_payload)

        assert response.status_code == 201
        data = response.json()

        assert data["hash_algorithm"] == "sha256"
        assert data["hash"] is not None

    def test_create_pdo_sets_timestamp(self, client, valid_pdo_payload):
        """Created PDO has recorded_at timestamp."""
        response = client.post("/pdo", json=valid_pdo_payload)

        assert response.status_code == 201
        data = response.json()

        assert "recorded_at" in data
        assert data["recorded_at"] is not None

    def test_create_pdo_validation_error(self, client):
        """POST /pdo returns 422 for invalid payload."""
        invalid_payload = {
            "input_refs": ["input"],
            # Missing required fields
        }

        response = client.post("/pdo", json=invalid_payload)

        assert response.status_code == 422


# =============================================================================
# READ ENDPOINT TESTS
# =============================================================================


class TestPDOReadEndpoints:
    """Tests for GET /pdo endpoints."""

    def test_get_pdo_by_id(self, client, valid_pdo_payload):
        """GET /pdo/{id} returns the PDO."""
        # Create first
        create_response = client.post("/pdo", json=valid_pdo_payload)
        pdo_id = create_response.json()["pdo_id"]

        # Get by ID
        response = client.get(f"/pdo/{pdo_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["pdo_id"] == pdo_id

    def test_get_pdo_not_found(self, client):
        """GET /pdo/{id} returns 404 for nonexistent PDO."""
        fake_id = "00000000-0000-0000-0000-000000000001"

        response = client.get(f"/pdo/{fake_id}")

        assert response.status_code == 404

    def test_get_pdo_with_verification(self, client, valid_pdo_payload):
        """GET /pdo/{id}?verify=true performs integrity check."""
        create_response = client.post("/pdo", json=valid_pdo_payload)
        pdo_id = create_response.json()["pdo_id"]

        response = client.get(f"/pdo/{pdo_id}?verify=true")

        assert response.status_code == 200

    def test_list_pdos(self, client, valid_pdo_payload):
        """GET /pdo returns list of PDOs."""
        # Create multiple
        client.post("/pdo", json=valid_pdo_payload)
        client.post("/pdo", json=valid_pdo_payload)

        response = client.get("/pdo")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["count"] == 2

    def test_list_pdos_with_filter(self, client):
        """GET /pdo?outcome=approved filters results."""
        approved = {
            "input_refs": ["input"],
            "decision_ref": "approved",
            "outcome_ref": "outcome",
            "outcome": "approved",
            "source_system": "gateway",
            "actor": "actor",
        }
        rejected = {
            "input_refs": ["input"],
            "decision_ref": "rejected",
            "outcome_ref": "outcome",
            "outcome": "rejected",
            "source_system": "gateway",
            "actor": "actor",
        }

        client.post("/pdo", json=approved)
        client.post("/pdo", json=approved)
        client.post("/pdo", json=rejected)

        response = client.get("/pdo?outcome=approved")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    def test_verify_pdo_endpoint(self, client, valid_pdo_payload):
        """GET /pdo/{id}/verify returns integrity status."""
        create_response = client.post("/pdo", json=valid_pdo_payload)
        pdo_id = create_response.json()["pdo_id"]

        response = client.get(f"/pdo/{pdo_id}/verify")

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["pdo_id"] == pdo_id


# =============================================================================
# BLOCKED ENDPOINT TESTS (IMMUTABILITY ENFORCEMENT)
# =============================================================================


class TestPDOBlockedEndpoints:
    """Tests that verify mutation endpoints are blocked."""

    def test_put_returns_405(self, client, valid_pdo_payload):
        """PUT /pdo/{id} returns 405 Method Not Allowed."""
        # Create first
        create_response = client.post("/pdo", json=valid_pdo_payload)
        pdo_id = create_response.json()["pdo_id"]

        # Attempt update
        response = client.put(f"/pdo/{pdo_id}", json={"outcome": "rejected"})

        assert response.status_code == 405
        data = response.json()
        assert data["error"] == "PDO_IMMUTABILITY_VIOLATION"
        assert "cannot be updated" in data["message"]

    def test_patch_returns_405(self, client, valid_pdo_payload):
        """PATCH /pdo/{id} returns 405 Method Not Allowed."""
        create_response = client.post("/pdo", json=valid_pdo_payload)
        pdo_id = create_response.json()["pdo_id"]

        response = client.patch(f"/pdo/{pdo_id}", json={"outcome": "rejected"})

        assert response.status_code == 405
        data = response.json()
        assert data["error"] == "PDO_IMMUTABILITY_VIOLATION"

    def test_delete_returns_405(self, client, valid_pdo_payload):
        """DELETE /pdo/{id} returns 405 Method Not Allowed."""
        create_response = client.post("/pdo", json=valid_pdo_payload)
        pdo_id = create_response.json()["pdo_id"]

        response = client.delete(f"/pdo/{pdo_id}")

        assert response.status_code == 405
        data = response.json()
        assert data["error"] == "PDO_IMMUTABILITY_VIOLATION"
        assert "cannot be deleted" in data["message"]

    def test_overwrite_returns_405(self, client, valid_pdo_payload):
        """POST /pdo/{id}/overwrite returns 405."""
        create_response = client.post("/pdo", json=valid_pdo_payload)
        pdo_id = create_response.json()["pdo_id"]

        response = client.post(f"/pdo/{pdo_id}/overwrite", json=valid_pdo_payload)

        assert response.status_code == 405
        data = response.json()
        assert "cannot be overwritten" in data["message"]

    def test_rehash_returns_405(self, client, valid_pdo_payload):
        """POST /pdo/{id}/rehash returns 405."""
        create_response = client.post("/pdo", json=valid_pdo_payload)
        pdo_id = create_response.json()["pdo_id"]

        response = client.post(f"/pdo/{pdo_id}/rehash")

        assert response.status_code == 405
        data = response.json()
        assert "cannot be recomputed" in data["message"]

    def test_pdo_still_exists_after_failed_mutations(self, client, valid_pdo_payload):
        """PDO remains unchanged after blocked mutation attempts."""
        create_response = client.post("/pdo", json=valid_pdo_payload)
        pdo_id = create_response.json()["pdo_id"]
        original_hash = create_response.json()["hash"]

        # Attempt various mutations
        client.put(f"/pdo/{pdo_id}", json={"outcome": "rejected"})
        client.patch(f"/pdo/{pdo_id}", json={"outcome": "rejected"})
        client.delete(f"/pdo/{pdo_id}")

        # PDO should still exist with original hash
        response = client.get(f"/pdo/{pdo_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["hash"] == original_hash
        assert data["outcome"] == "approved"  # Original value


# =============================================================================
# CHAIN ENDPOINT TESTS
# =============================================================================


class TestPDOChainEndpoint:
    """Tests for PDO chain retrieval."""

    def test_get_pdo_chain(self, client):
        """GET /pdo/{id}/chain returns linked PDOs."""
        # Create chain
        first = client.post(
            "/pdo",
            json={
                "input_refs": ["input"],
                "decision_ref": "first",
                "outcome_ref": "outcome",
                "outcome": "approved",
                "source_system": "gateway",
                "actor": "actor",
            },
        ).json()

        second = client.post(
            "/pdo",
            json={
                "input_refs": ["input"],
                "decision_ref": "second",
                "outcome_ref": "outcome",
                "outcome": "approved",
                "source_system": "gateway",
                "actor": "actor",
                "previous_pdo_id": first["pdo_id"],
            },
        ).json()

        # Get chain from second
        response = client.get(f"/pdo/{second['pdo_id']}/chain")

        assert response.status_code == 200
        chain = response.json()
        assert len(chain) == 2
        assert chain[0]["pdo_id"] == first["pdo_id"]
        assert chain[1]["pdo_id"] == second["pdo_id"]
