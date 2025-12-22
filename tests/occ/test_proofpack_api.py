"""
ProofPack API Tests — PROOFPACK_SPEC_v1.md Implementation

PAC-CODY-PROOFPACK-IMPL-01: ProofPack Generation & Offline Verification

Tests for API endpoints.

Author: CODY (GID-01) - Backend
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.server import app
from core.occ.proofpack import reset_proofpack_generator
from core.occ.schemas.pdo import PDOCreate, PDOOutcome, PDOSourceSystem
from core.occ.store.pdo_store import get_pdo_store, reset_pdo_store

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def clean_singletons(monkeypatch):
    """Reset singleton stores before each test."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        temp_path = f.name
    monkeypatch.setenv("CHAINBRIDGE_PDO_STORE_PATH", temp_path)
    reset_pdo_store()
    reset_proofpack_generator()
    yield
    reset_pdo_store()
    reset_proofpack_generator()
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_pdo():
    """Create a sample PDO for testing."""
    store = get_pdo_store()
    create = PDOCreate(
        source_system=PDOSourceSystem.OCC,
        outcome=PDOOutcome.APPROVED,
        actor="test-api-agent",
        input_refs=["input:api_abc", "input:api_def"],
        decision_ref="decision:api_xyz",
        outcome_ref="outcome:api_qrs",
    )
    return store.create(create)


# =============================================================================
# GENERATION ENDPOINT TESTS
# =============================================================================


class TestGenerateProofPackEndpoint:
    """Tests for GET /proofpack/{pdo_id}."""

    def test_generate_proofpack_success(self, client, sample_pdo):
        """Successfully generate ProofPack."""
        response = client.get(f"/proofpack/{sample_pdo.pdo_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["pdo_id"] == str(sample_pdo.pdo_id)
        assert "files" in data
        assert "manifest" in data

    def test_generate_proofpack_has_manifest_json(self, client, sample_pdo):
        """Generated ProofPack includes manifest.json file."""
        response = client.get(f"/proofpack/{sample_pdo.pdo_id}")

        assert response.status_code == 200
        data = response.json()
        assert "manifest.json" in data["files"]

    def test_generate_proofpack_has_pdo_record(self, client, sample_pdo):
        """Generated ProofPack includes PDO record file."""
        response = client.get(f"/proofpack/{sample_pdo.pdo_id}")

        assert response.status_code == 200
        data = response.json()
        assert "pdo/record.json" in data["files"]

    def test_generate_proofpack_not_found(self, client):
        """404 for non-existent PDO."""
        fake_id = uuid4()
        response = client.get(f"/proofpack/{fake_id}")

        assert response.status_code == 404

    def test_generate_proofpack_invalid_uuid(self, client):
        """422 for invalid UUID format."""
        response = client.get("/proofpack/not-a-uuid")

        assert response.status_code == 422


class TestGenerateProofPackZip:
    """Tests for GET /proofpack/{pdo_id}?format=zip."""

    def test_generate_zip_format(self, client, sample_pdo):
        """Generate ProofPack as ZIP archive."""
        response = client.get(f"/proofpack/{sample_pdo.pdo_id}?format=zip")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers.get("content-disposition", "")

    def test_zip_has_content(self, client, sample_pdo):
        """ZIP archive has content."""
        response = client.get(f"/proofpack/{sample_pdo.pdo_id}?format=zip")

        assert response.status_code == 200
        assert len(response.content) > 0


# =============================================================================
# VERIFICATION ENDPOINT TESTS
# =============================================================================


class TestGenerateAndVerifyEndpoint:
    """Tests for GET /proofpack/{pdo_id}/verify."""

    def test_generate_and_verify_success(self, client, sample_pdo):
        """Generate and verify succeeds for valid PDO."""
        response = client.get(f"/proofpack/{sample_pdo.pdo_id}/verify")

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["outcome"] == "VALID"
        assert "steps" in data

    def test_generate_and_verify_has_steps(self, client, sample_pdo):
        """Verification result includes step details."""
        response = client.get(f"/proofpack/{sample_pdo.pdo_id}/verify")

        assert response.status_code == 200
        data = response.json()
        assert len(data["steps"]) >= 3

    def test_generate_and_verify_not_found(self, client):
        """404 for non-existent PDO."""
        fake_id = uuid4()
        response = client.get(f"/proofpack/{fake_id}/verify")

        assert response.status_code == 404


class TestVerifyUploadedEndpoint:
    """Tests for POST /proofpack/verify."""

    def test_verify_valid_proofpack(self, client, sample_pdo):
        """Verify valid uploaded ProofPack."""
        gen_response = client.get(f"/proofpack/{sample_pdo.pdo_id}")
        assert gen_response.status_code == 200
        proofpack = gen_response.json()

        verify_response = client.post("/proofpack/verify", json=proofpack)

        assert verify_response.status_code == 200
        data = verify_response.json()
        assert data["is_valid"] is True

    def test_verify_tampered_proofpack(self, client, sample_pdo):
        """Verify tampered ProofPack fails."""
        gen_response = client.get(f"/proofpack/{sample_pdo.pdo_id}")
        assert gen_response.status_code == 200
        proofpack = gen_response.json()

        pdo_data = json.loads(proofpack["files"]["pdo/record.json"])
        pdo_data["TAMPERED"] = True
        proofpack["files"]["pdo/record.json"] = json.dumps(pdo_data, sort_keys=True, separators=(",", ":"))

        verify_response = client.post("/proofpack/verify", json=proofpack)

        assert verify_response.status_code == 200
        data = verify_response.json()
        assert data["is_valid"] is False

    def test_verify_empty_proofpack(self, client):
        """Verify empty ProofPack fails."""
        verify_response = client.post("/proofpack/verify", json={})

        assert verify_response.status_code == 200
        data = verify_response.json()
        assert data["is_valid"] is False


# =============================================================================
# ROUND-TRIP TESTS
# =============================================================================


class TestRoundTrip:
    """Tests for generate → verify round trip via API."""

    def test_generate_then_verify_via_api(self, client, sample_pdo):
        """Generate via API, verify via API."""
        gen_response = client.get(f"/proofpack/{sample_pdo.pdo_id}")
        assert gen_response.status_code == 200
        proofpack = gen_response.json()

        verify_response = client.post("/proofpack/verify", json=proofpack)
        assert verify_response.status_code == 200
        assert verify_response.json()["is_valid"] is True
