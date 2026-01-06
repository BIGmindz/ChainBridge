"""
ProofPack Download API Tests — PAC-BENSON-P33

Doctrine Law 4, §4.2: ProofPack download with signed archive.

Tests for:
- GET /api/v1/proofpack/{id}/download
- GET /api/v1/proofpack/{id}/manifest

INVARIANTS TESTED:
- INV-PP-001: All archives cryptographically signed
- INV-PP-002: Hash manifest included for offline verification
- INV-OCC-005: Read-only endpoint (GET only)

Author: CODY (GID-01) — Backend Implementation
Security: SAM (GID-06) — Cryptographic verification
DAN (GID-07) — CI/Test Enforcement
"""

from __future__ import annotations

import io
import json
import zipfile
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.server import app
from core.occ.schemas.artifact import ArtifactCreate, ArtifactStatus, ArtifactType
from core.occ.store.artifact_store import get_artifact_store


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_artifact():
    """Create a sample artifact for testing."""
    store = get_artifact_store()
    artifact_create = ArtifactCreate(
        name="test-proofpack-artifact",
        artifact_type=ArtifactType.DECISION,
        status=ArtifactStatus.APPROVED,
        description="Test artifact for ProofPack download tests",
        owner="GID-01",
        tags=["test", "proofpack", "pac-p33"],
        payload={"test_key": "test_value", "amount": 1000},
    )
    return store.create(artifact_create, actor="GID-01")


# =============================================================================
# DOWNLOAD ENDPOINT TESTS
# =============================================================================


class TestProofPackDownload:
    """Tests for GET /api/v1/proofpack/{id}/download."""

    def test_download_returns_zip(self, client, sample_artifact):
        """Download endpoint returns ZIP archive."""
        response = client.get(f"/api/v1/proofpack/{sample_artifact.id}/download")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert "attachment" in response.headers.get("content-disposition", "")

    def test_download_zip_contains_required_files(self, client, sample_artifact):
        """ZIP archive contains all required files."""
        response = client.get(f"/api/v1/proofpack/{sample_artifact.id}/download")

        assert response.status_code == 200

        # Parse ZIP
        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            names = zf.namelist()
            assert "proofpack.json" in names
            assert "proofpack.txt" in names
            assert "manifest.json" in names
            assert "verification.txt" in names

    def test_download_proofpack_json_valid(self, client, sample_artifact):
        """proofpack.json is valid JSON with required fields."""
        response = client.get(f"/api/v1/proofpack/{sample_artifact.id}/download")

        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            proofpack_json = json.loads(zf.read("proofpack.json"))

        assert "schema_version" in proofpack_json
        assert "proofpack_id" in proofpack_json
        assert "generated_at" in proofpack_json
        assert "artifact" in proofpack_json
        assert "events" in proofpack_json
        assert "integrity" in proofpack_json

    def test_download_manifest_json_valid(self, client, sample_artifact):
        """manifest.json contains hash verification data."""
        response = client.get(f"/api/v1/proofpack/{sample_artifact.id}/download")

        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))

        assert "contents" in manifest
        assert "manifest_hash" in manifest
        assert len(manifest["contents"]) >= 2  # proofpack.json and proofpack.txt

    def test_download_includes_signature_header(self, client, sample_artifact):
        """Response includes signature status header."""
        response = client.get(f"/api/v1/proofpack/{sample_artifact.id}/download")

        assert "x-proofpack-signed" in response.headers
        assert "x-proofpack-manifest-hash" in response.headers

    def test_download_artifact_not_found(self, client):
        """Returns 404 for non-existent artifact."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/proofpack/{fake_id}/download")

        assert response.status_code == 404

    def test_download_without_payload(self, client, sample_artifact):
        """Download with include_payload=false excludes payload."""
        response = client.get(
            f"/api/v1/proofpack/{sample_artifact.id}/download",
            params={"include_payload": "false"},
        )

        assert response.status_code == 200

        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            proofpack_json = json.loads(zf.read("proofpack.json"))

        # Payload should not be present when excluded
        artifact_data = proofpack_json.get("artifact", {})
        assert "payload" not in artifact_data

    def test_download_verification_txt_present(self, client, sample_artifact):
        """verification.txt contains instructions."""
        response = client.get(f"/api/v1/proofpack/{sample_artifact.id}/download")

        zip_buffer = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_buffer, "r") as zf:
            verification = zf.read("verification.txt").decode("utf-8")

        assert "VERIFICATION" in verification
        assert "SHA-256" in verification
        assert "OFFLINE" in verification.upper()


# =============================================================================
# MANIFEST ENDPOINT TESTS
# =============================================================================


class TestProofPackManifest:
    """Tests for GET /api/v1/proofpack/{id}/manifest."""

    def test_manifest_returns_json(self, client, sample_artifact):
        """Manifest endpoint returns JSON."""
        response = client.get(f"/api/v1/proofpack/{sample_artifact.id}/manifest")

        assert response.status_code == 200
        data = response.json()
        assert "artifact_id" in data
        assert "manifest_hash" in data

    def test_manifest_includes_download_url(self, client, sample_artifact):
        """Manifest includes download URL."""
        response = client.get(f"/api/v1/proofpack/{sample_artifact.id}/manifest")

        data = response.json()
        assert "download_url" in data
        assert f"/api/v1/proofpack/{sample_artifact.id}/download" in data["download_url"]

    def test_manifest_artifact_not_found(self, client):
        """Returns 404 for non-existent artifact."""
        fake_id = uuid4()
        response = client.get(f"/api/v1/proofpack/{fake_id}/manifest")

        assert response.status_code == 404


# =============================================================================
# INVARIANT TESTS (INV-OCC-005: Read-only)
# =============================================================================


class TestReadOnlyInvariant:
    """Tests that endpoints are read-only (INV-OCC-005)."""

    def test_no_post_on_download(self, client, sample_artifact):
        """POST not allowed on download endpoint."""
        response = client.post(f"/api/v1/proofpack/{sample_artifact.id}/download")
        assert response.status_code == 405

    def test_no_put_on_download(self, client, sample_artifact):
        """PUT not allowed on download endpoint."""
        response = client.put(f"/api/v1/proofpack/{sample_artifact.id}/download")
        assert response.status_code == 405

    def test_no_delete_on_download(self, client, sample_artifact):
        """DELETE not allowed on download endpoint."""
        response = client.delete(f"/api/v1/proofpack/{sample_artifact.id}/download")
        assert response.status_code == 405

    def test_no_post_on_manifest(self, client, sample_artifact):
        """POST not allowed on manifest endpoint."""
        response = client.post(f"/api/v1/proofpack/{sample_artifact.id}/manifest")
        assert response.status_code == 405
