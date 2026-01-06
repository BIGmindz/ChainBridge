"""
Tests for Trust Center API Endpoints — PAC-BENSON-P34

Tests public audit interface including:
- Timeline endpoint
- ProofPack verification endpoint
- ProofPack summary endpoint

Author: DAN (GID-07) — CI/Test Lead
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.server import app
from core.occ.schemas.artifact import ArtifactCreate, ArtifactStatus, ArtifactType
from core.occ.store.artifact_store import get_artifact_store


@pytest.fixture
def client():
    """Test client."""
    return TestClient(app)


@pytest.fixture
def sample_artifact():
    """Create a sample artifact for testing."""
    store = get_artifact_store()
    artifact_create = ArtifactCreate(
        name="test-trust-center-artifact",
        artifact_type=ArtifactType.DECISION,
        status=ArtifactStatus.APPROVED,
        description="Test artifact for Trust Center tests",
        owner="GID-01",
        tags=["test", "trust-center", "pac-p34"],
        payload={"test_key": "test_value"},
    )
    return store.create(artifact_create, actor="GID-01")


class TestTrustTimeline:
    """Tests for /trust/timeline endpoint."""

    def test_timeline_returns_entries(self, client):
        """Timeline endpoint returns entries."""
        response = client.get("/trust/timeline")

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total_count" in data
        assert "has_more" in data
        assert isinstance(data["entries"], list)

    def test_timeline_entries_have_required_fields(self, client):
        """Timeline entries have all required fields."""
        response = client.get("/trust/timeline")

        assert response.status_code == 200
        data = response.json()

        if data["entries"]:
            entry = data["entries"][0]
            assert "entry_id" in entry
            assert "entry_type" in entry
            assert "timestamp" in entry
            assert "description" in entry

    def test_timeline_pagination(self, client):
        """Timeline supports pagination parameters."""
        response = client.get("/trust/timeline?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) <= 2

    def test_timeline_entry_types(self, client):
        """Timeline entry types are valid."""
        valid_types = {"DECISION", "VERIFICATION", "EXPORT", "SYSTEM"}

        response = client.get("/trust/timeline")
        data = response.json()

        for entry in data["entries"]:
            assert entry["entry_type"] in valid_types


class TestProofPackVerification:
    """Tests for /api/v1/proofpack/{id}/verify endpoint."""

    def test_verify_returns_verification_result(self, client, sample_artifact):
        """Verify endpoint returns verification result."""
        response = client.get(f"/api/v1/proofpack/{sample_artifact.id}/verify")

        assert response.status_code == 200
        data = response.json()

        assert "verified" in data
        assert "status" in data
        assert "message" in data
        assert "verified_at" in data
        assert "hash_algorithm" in data

    def test_verify_status_values(self, client, sample_artifact):
        """Verify status is a valid value."""
        valid_statuses = {"VERIFIED", "PENDING", "FAILED", "EXPIRED", "UNKNOWN"}

        response = client.get(f"/api/v1/proofpack/{sample_artifact.id}/verify")

        data = response.json()
        assert data["status"] in valid_statuses

    def test_verify_not_found(self, client):
        """Verify returns 404 for non-existent ProofPack."""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/proofpack/{fake_id}/verify")

        assert response.status_code == 404


class TestProofPackSummary:
    """Tests for /api/v1/proofpack/{id} endpoint."""

    def test_summary_returns_public_safe_data(self, client, sample_artifact):
        """Summary endpoint returns public-safe data."""
        response = client.get(f"/api/v1/proofpack/{sample_artifact.id}")

        assert response.status_code == 200
        data = response.json()

        assert "proofpack_id" in data
        assert "generated_at" in data
        assert "event_count" in data
        assert "is_signed" in data
        assert "manifest_hash" in data
        assert "download_url" in data

    def test_summary_includes_download_url(self, client, sample_artifact):
        """Summary includes valid download URL."""
        response = client.get(f"/api/v1/proofpack/{sample_artifact.id}")

        data = response.json()
        assert f"/api/v1/proofpack/{sample_artifact.id}/download" in data["download_url"]

    def test_summary_not_found(self, client):
        """Summary returns 404 for non-existent ProofPack."""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/v1/proofpack/{fake_id}")

        assert response.status_code == 404

        assert response.status_code == 404


class TestTrustAPIReadOnly:
    """Tests confirming Trust Center API is read-only."""

    def test_timeline_post_not_allowed(self, client):
        """Timeline POST is not allowed."""
        response = client.post("/trust/timeline", json={})
        assert response.status_code == 405

    def test_timeline_put_not_allowed(self, client):
        """Timeline PUT is not allowed."""
        response = client.put("/trust/timeline", json={})
        assert response.status_code == 405

    def test_timeline_delete_not_allowed(self, client):
        """Timeline DELETE is not allowed."""
        response = client.delete("/trust/timeline")
        assert response.status_code == 405


class TestTrustCenterIntegration:
    """Integration tests for Trust Center components."""

    def test_existing_trust_endpoints_still_work(self, client):
        """Existing trust endpoints still work."""
        # Coverage endpoint (constant)
        response = client.get("/trust/coverage")
        assert response.status_code == 200
        data = response.json()
        assert "acm_enforced" in data

        # Gameday endpoint (constant)
        response = client.get("/trust/gameday")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios_tested" in data

    def test_trust_center_complete_flow(self, client, sample_artifact):
        """Complete Trust Center flow: lookup -> verify -> download."""
        # 1. Look up ProofPack summary
        summary_response = client.get(f"/api/v1/proofpack/{sample_artifact.id}")
        assert summary_response.status_code == 200

        # 2. Verify integrity
        verify_response = client.get(f"/api/v1/proofpack/{sample_artifact.id}/verify")
        assert verify_response.status_code == 200

        # 3. Download (manifest only for test)
        manifest_response = client.get(f"/api/v1/proofpack/{sample_artifact.id}/manifest")
        assert manifest_response.status_code == 200
