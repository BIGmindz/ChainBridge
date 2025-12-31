# ═══════════════════════════════════════════════════════════════════════════════
# OCC Diff API Tests — PAC-BENSON-P22-C
#
# Tests for decision diff/comparison endpoints.
# READ-ONLY verification and invariant compliance.
#
# Authors:
# - CODY (GID-01) — Backend Lead
# - DAN (GID-07) — CI/Testing Lead
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from fastapi.testclient import TestClient

from api.server import app

client = TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════════
# GET /occ/diff/{left_id}/{right_id} - Generic Diff
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetDiff:
    """Test generic diff retrieval."""

    def test_get_diff_success(self):
        """GET /occ/diff/{left}/{right} returns diff data."""
        response = client.get("/occ/diff/item-001/item-002")
        assert response.status_code == 200
        data = response.json()
        
        assert data["left_id"] == "item-001"
        assert data["right_id"] == "item-002"
        assert "sections" in data
        assert "summary" in data

    def test_diff_has_evidence_hashes(self):
        """Diff response includes evidence hashes (INV-OCC-005)."""
        response = client.get("/occ/diff/item-001/item-002")
        assert response.status_code == 200
        data = response.json()
        
        assert "left_evidence_hash" in data
        assert "right_evidence_hash" in data

    def test_diff_summary_counts(self):
        """Diff summary includes change counts (INV-OCC-006)."""
        response = client.get("/occ/diff/item-001/item-002")
        assert response.status_code == 200
        data = response.json()
        
        summary = data["summary"]
        assert "total_changes" in summary
        assert "added_count" in summary
        assert "removed_count" in summary
        assert "modified_count" in summary

    def test_diff_with_entity_type(self):
        """Diff supports entity_type parameter."""
        response = client.get("/occ/diff/item-001/item-002?entity_type=decision")
        assert response.status_code == 200
        data = response.json()
        
        assert data["entity_type"] == "decision"


# ═══════════════════════════════════════════════════════════════════════════════
# GET /occ/diff/ber/{ber_a}/{ber_b} - BER Diff
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetBERDiff:
    """Test BER diff retrieval."""

    def test_get_ber_diff_success(self):
        """GET /occ/diff/ber/{a}/{b} returns BER diff."""
        response = client.get("/occ/diff/ber/BER-001/BER-002")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ber_a_id"] == "BER-001"
        assert data["ber_b_id"] == "BER-002"
        assert "sections" in data
        assert "summary" in data

    def test_ber_diff_has_evidence_hashes(self):
        """BER diff includes evidence hashes."""
        response = client.get("/occ/diff/ber/BER-001/BER-002")
        assert response.status_code == 200
        data = response.json()
        
        assert "ber_a_evidence_hash" in data
        assert "ber_b_evidence_hash" in data

    def test_ber_diff_has_pac_id(self):
        """BER diff includes PAC ID."""
        response = client.get("/occ/diff/ber/BER-001/BER-002")
        assert response.status_code == 200
        data = response.json()
        
        assert "pac_id" in data


# ═══════════════════════════════════════════════════════════════════════════════
# GET /occ/diff/pdo/{pdo_a}/{pdo_b} - PDO Diff
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetPDODiff:
    """Test PDO diff retrieval."""

    def test_get_pdo_diff_success(self):
        """GET /occ/diff/pdo/{a}/{b} returns PDO diff."""
        response = client.get("/occ/diff/pdo/PDO-001/PDO-002")
        assert response.status_code == 200
        data = response.json()
        
        assert data["pdo_a_id"] == "PDO-001"
        assert data["pdo_b_id"] == "PDO-002"
        assert "sections" in data
        assert "summary" in data

    def test_pdo_diff_has_evidence_hashes(self):
        """PDO diff includes evidence hashes."""
        response = client.get("/occ/diff/pdo/PDO-001/PDO-002")
        assert response.status_code == 200
        data = response.json()
        
        assert "pdo_a_evidence_hash" in data
        assert "pdo_b_evidence_hash" in data


# ═══════════════════════════════════════════════════════════════════════════════
# DIFF SECTION STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

class TestDiffSections:
    """Test diff section structure."""

    def test_sections_have_required_fields(self):
        """Diff sections have required fields."""
        response = client.get("/occ/diff/item-001/item-002")
        assert response.status_code == 200
        data = response.json()
        
        for section in data["sections"]:
            assert "section_id" in section
            assert "section_name" in section
            assert "change_type" in section
            assert "changes" in section

    def test_changes_have_required_fields(self):
        """Diff changes have required fields."""
        response = client.get("/occ/diff/item-001/item-002")
        assert response.status_code == 200
        data = response.json()
        
        for section in data["sections"]:
            for change in section["changes"]:
                assert "field_path" in change
                assert "change_type" in change

    def test_change_types_valid(self):
        """Change types are valid values."""
        valid_types = {"added", "removed", "modified", "unchanged"}
        
        response = client.get("/occ/diff/item-001/item-002")
        assert response.status_code == 200
        data = response.json()
        
        for section in data["sections"]:
            assert section["change_type"] in valid_types
            for change in section["changes"]:
                assert change["change_type"] in valid_types


# ═══════════════════════════════════════════════════════════════════════════════
# READ-ONLY VERIFICATION (INV-OCC-005)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDiffReadOnly:
    """Verify diff endpoints are read-only."""

    def test_post_rejected(self):
        """POST mutations are rejected."""
        response = client.post("/occ/diff/item-001/item-002", json={})
        assert response.status_code == 405
        assert "READ-ONLY" in response.json()["detail"]

    def test_put_rejected(self):
        """PUT mutations are rejected."""
        response = client.put("/occ/diff/item-001/item-002", json={})
        assert response.status_code == 405

    def test_patch_rejected(self):
        """PATCH mutations are rejected."""
        response = client.patch("/occ/diff/item-001/item-002", json={})
        assert response.status_code == 405

    def test_delete_rejected(self):
        """DELETE mutations are rejected."""
        response = client.delete("/occ/diff/item-001/item-002")
        assert response.status_code == 405

    def test_inv_occ_005_in_rejection(self):
        """Mutation rejections cite INV-OCC-005."""
        response = client.post("/occ/diff/item-001/item-002", json={})
        assert "INV-OCC-005" in response.json()["detail"]
