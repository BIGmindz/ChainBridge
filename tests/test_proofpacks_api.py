"""
Tests for src/api/proofpacks_api.py
"""
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Set up test environment
os.environ["APP_ENV"] = "dev"
os.environ["SIGNING_SECRET"] = "test-secret-key-for-testing-only"

# Create temporary runtime directory for tests
TEST_RUNTIME_DIR = tempfile.mkdtemp(prefix="test_proofpacks_")
os.environ["PROOFPACK_RUNTIME_DIR"] = TEST_RUNTIME_DIR

from main import app
from src.api.proofpacks_api import (
    compute_manifest_hash,
    normalize_events,
    validate_pack_id,
)
from src.security.signing import canonical_json_bytes

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_test_dir():
    """Clean up test directory after each test."""
    yield
    # Clean up files in test directory
    if Path(TEST_RUNTIME_DIR).exists():
        for file in Path(TEST_RUNTIME_DIR).glob("*.json"):
            file.unlink()


@pytest.fixture
def sample_proofpack_request():
    """Sample valid ProofPack request."""
    return {
        "shipment_id": "XPO-12345",
        "events": [
            {
                "event_type": "pickup",
                "timestamp": "2025-01-15T10:00:00Z",
                "details": {"location": "Erie, PA"}
            },
            {
                "event_type": "in_transit",
                "timestamp": "2025-01-15T12:00:00Z",
                "details": {"checkpoint": "Border"}
            }
        ],
        "risk_score": 25.5,
        "policy_version": "1.0"
    }


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self):
        """Test that health check returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "chainbridge-proofpacks"


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root(self):
        """Test that root returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert data["api_prefix"] == "/v1/proofpacks"


class TestProofPackCreation:
    """Tests for ProofPack creation endpoint."""

    def test_create_proofpack_success(self, sample_proofpack_request):
        """Test successful ProofPack creation."""
        response = client.post("/v1/proofpacks/run", json=sample_proofpack_request)
        assert response.status_code == 201

        data = response.json()
        assert data["status"] == "SUCCESS"
        assert "pack_id" in data
        assert data["shipment_id"] == "XPO-12345"
        assert "manifest_hash" in data
        assert "generated_at" in data

        # Verify response is signed
        assert "X-Signature" in response.headers
        assert "X-Signature-Timestamp" in response.headers
        assert response.headers["X-Signature-Alg"] == "HMAC-SHA256"

    def test_create_proofpack_invalid_shipment_id(self):
        """Test that invalid shipment_id is rejected."""
        payload = {
            "shipment_id": "invalid/../path",  # Path traversal attempt
            "events": [
                {"event_type": "pickup", "timestamp": "2025-01-15T10:00:00Z"}
            ]
        }
        response = client.post("/v1/proofpacks/run", json=payload)
        assert response.status_code == 422  # Validation error

    def test_create_proofpack_empty_events(self):
        """Test that empty events list is rejected."""
        payload = {
            "shipment_id": "XPO-12345",
            "events": []
        }
        response = client.post("/v1/proofpacks/run", json=payload)
        assert response.status_code == 422

    def test_create_proofpack_too_many_events(self):
        """Test that too many events are rejected."""
        payload = {
            "shipment_id": "XPO-12345",
            "events": [
                {"event_type": f"event_{i}", "timestamp": "2025-01-15T10:00:00Z"}
                for i in range(101)  # More than MAX_EVENTS_PER_PACK
            ]
        }
        response = client.post("/v1/proofpacks/run", json=payload)
        assert response.status_code == 422

    def test_create_proofpack_invalid_risk_score(self):
        """Test that invalid risk score is rejected."""
        payload = {
            "shipment_id": "XPO-12345",
            "events": [
                {"event_type": "pickup", "timestamp": "2025-01-15T10:00:00Z"}
            ],
            "risk_score": 150  # Out of range
        }
        response = client.post("/v1/proofpacks/run", json=payload)
        assert response.status_code == 422

    def test_create_proofpack_invalid_timestamp(self):
        """Test that invalid timestamp is rejected."""
        payload = {
            "shipment_id": "XPO-12345",
            "events": [
                {"event_type": "pickup", "timestamp": "not-a-timestamp"}
            ]
        }
        response = client.post("/v1/proofpacks/run", json=payload)
        assert response.status_code == 422

    def test_create_proofpack_invalid_event_type(self):
        """Test that invalid event type is rejected."""
        payload = {
            "shipment_id": "XPO-12345",
            "events": [
                {"event_type": "pickup; DROP TABLE", "timestamp": "2025-01-15T10:00:00Z"}
            ]
        }
        response = client.post("/v1/proofpacks/run", json=payload)
        assert response.status_code == 422

    def test_create_proofpack_invalid_policy_version(self):
        """Test that invalid policy version is rejected."""
        payload = {
            "shipment_id": "XPO-12345",
            "events": [
                {"event_type": "pickup", "timestamp": "2025-01-15T10:00:00Z"}
            ],
            "policy_version": "invalid"
        }
        response = client.post("/v1/proofpacks/run", json=payload)
        assert response.status_code == 422


class TestProofPackRetrieval:
    """Tests for ProofPack retrieval endpoint."""

    def test_get_proofpack_success(self, sample_proofpack_request):
        """Test successful ProofPack retrieval."""
        # First create a ProofPack
        create_response = client.post("/v1/proofpacks/run", json=sample_proofpack_request)
        assert create_response.status_code == 201
        pack_id = create_response.json()["pack_id"]
        original_hash = create_response.json()["manifest_hash"]

        # Now retrieve it
        get_response = client.get(f"/v1/proofpacks/{pack_id}")
        assert get_response.status_code == 200

        data = get_response.json()
        assert data["status"] == "SUCCESS"
        assert data["pack_id"] == pack_id
        assert data["shipment_id"] == "XPO-12345"
        assert data["manifest_hash"] == original_hash

        # Verify response is signed
        assert "X-Signature" in get_response.headers

    def test_get_proofpack_not_found(self):
        """Test that non-existent ProofPack returns 404."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/v1/proofpacks/{fake_uuid}")
        assert response.status_code == 404

    def test_get_proofpack_invalid_id_format(self):
        """Test that invalid pack_id format is rejected."""
        response = client.get("/v1/proofpacks/not-a-uuid")
        assert response.status_code == 400

    def test_get_proofpack_path_traversal_attempt(self):
        """Test that path traversal is blocked."""
        response = client.get("/v1/proofpacks/../../../etc/passwd")
        assert response.status_code == 400


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_validate_pack_id_valid(self):
        """Test that valid UUID passes validation."""
        valid_uuid = "12345678-1234-1234-1234-123456789abc"
        assert validate_pack_id(valid_uuid) == valid_uuid

    def test_validate_pack_id_invalid(self):
        """Test that invalid UUID fails validation."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_pack_id("not-a-uuid")

    def test_validate_pack_id_path_traversal(self):
        """Test that path traversal attempt fails validation."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_pack_id("../../../etc/passwd")

    def test_compute_manifest_hash_deterministic(self):
        """Test that manifest hash is deterministic."""
        manifest = {
            "shipment_id": "XPO-12345",
            "events": [],
            "risk_score": 10.0,
            "policy_version": "1.0",
            "generated_at": "2025-01-15T10:00:00Z"
        }
        hash1 = compute_manifest_hash(manifest)
        hash2 = compute_manifest_hash(manifest)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_compute_manifest_hash_different_data(self):
        """Test that different manifests have different hashes."""
        manifest1 = {
            "shipment_id": "XPO-12345",
            "events": [],
            "risk_score": 10.0,
            "policy_version": "1.0",
            "generated_at": "2025-01-15T10:00:00Z"
        }
        manifest2 = {
            "shipment_id": "XPO-99999",
            "events": [],
            "risk_score": 10.0,
            "policy_version": "1.0",
            "generated_at": "2025-01-15T10:00:00Z"
        }
        hash1 = compute_manifest_hash(manifest1)
        hash2 = compute_manifest_hash(manifest2)
        assert hash1 != hash2


class TestSignatureVerification:
    """Tests for response signature verification."""

    def test_response_signature_valid(self, sample_proofpack_request):
        """Test that response signature can be verified."""
        from src.security.signing import compute_sig

        response = client.post("/v1/proofpacks/run", json=sample_proofpack_request)
        assert response.status_code == 201

        # Extract signature components
        signature = response.headers["X-Signature"]
        timestamp = response.headers["X-Signature-Timestamp"]

        # Recompute signature
        body_bytes = canonical_json_bytes(response.json())
        expected_sig = compute_sig(timestamp, body_bytes)

        assert signature == expected_sig


# Clean up test directory when tests complete
def teardown_module(module):
    """Clean up test runtime directory."""
    if Path(TEST_RUNTIME_DIR).exists():
        shutil.rmtree(TEST_RUNTIME_DIR)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
