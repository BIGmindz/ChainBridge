#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦
BSRG-01 Gate Validation Tests
PAC-ATLAS-P21-BSRG-PARSER-AND-LEDGER-IMMUTABILITY-01
🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦
═══════════════════════════════════════════════════════════════════════════════

This module contains tests for Benson Self-Review Gate (BSRG-01) enforcement.

Test Coverage:
- test_gate_pack_rejects_missing_bsrg
- test_gate_pack_rejects_invalid_bsrg_fields
- test_gate_pack_enforces_bsrg_ordering
- test_gate_pack_accepts_valid_bsrg
- test_ledger_records_bsrg_and_hash_chain_validates
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add tools directory to path for imports
REPO_ROOT = Path(__file__).parent.parent.parent
TOOLS_DIR = REPO_ROOT / "tools" / "governance"
sys.path.insert(0, str(TOOLS_DIR))

# Now import from the modules
import gate_pack
from gate_pack import (
    validate_benson_self_review_gate,
    is_pac_artifact,
    extract_bsrg_block,
    validate_bsrg_ordering,
    ErrorCode,
    ValidationError,
)
import ledger_writer
from ledger_writer import GovernanceLedger, EntryType


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

FIXTURE_DIR = Path(__file__).parent / "bsrg"


@pytest.fixture
def pac_missing_bsrg():
    """Load PAC fixture missing BSRG."""
    return (FIXTURE_DIR / "pac_missing_bsrg.md").read_text()


@pytest.fixture
def pac_wrong_reviewer_gid():
    """Load PAC fixture with wrong reviewer_gid."""
    return (FIXTURE_DIR / "pac_wrong_reviewer_gid.md").read_text()


@pytest.fixture
def pac_checklist_not_pass():
    """Load PAC fixture with checklist item not PASS."""
    return (FIXTURE_DIR / "pac_checklist_not_pass.md").read_text()


@pytest.fixture
def pac_bsrg_wrong_order():
    """Load PAC fixture with BSRG in wrong order."""
    return (FIXTURE_DIR / "pac_bsrg_wrong_order.md").read_text()


@pytest.fixture
def pac_valid_bsrg():
    """Load valid PAC fixture with perfect BSRG."""
    return (FIXTURE_DIR / "pac_valid_bsrg.md").read_text()


@pytest.fixture
def temp_ledger():
    """Create a temporary ledger for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=True) as f:
        ledger_path = Path(f.name)
    
    # File is now deleted, so GovernanceLedger will create a fresh one
    ledger = GovernanceLedger(ledger_path)
    yield ledger
    
    # Cleanup
    if ledger_path.exists():
        ledger_path.unlink()


# ═══════════════════════════════════════════════════════════════════════════════
# PAC DETECTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPacDetection:
    """Tests for PAC artifact detection."""
    
    def test_is_pac_artifact_detects_valid_pac(self, pac_valid_bsrg):
        """Test that valid PAC is detected as PAC artifact."""
        assert is_pac_artifact(pac_valid_bsrg) is True
    
    def test_is_pac_artifact_requires_multiple_markers(self):
        """Test that PAC detection requires multiple structural markers."""
        # Just one marker is not enough
        content = "PAC-TEST-01"
        assert is_pac_artifact(content) is False
        
        # Two markers still not enough
        content = "PAC-TEST-01\nRUNTIME_ACTIVATION_ACK"
        assert is_pac_artifact(content) is False


# ═══════════════════════════════════════════════════════════════════════════════
# BSRG VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBsrgValidation:
    """Tests for BSRG-01 validation logic."""
    
    def test_gate_pack_rejects_missing_bsrg(self, pac_missing_bsrg):
        """Test that PAC without BSRG is rejected."""
        errors, bsrg_data = validate_benson_self_review_gate(pac_missing_bsrg)
        
        # Should have at least one error
        assert len(errors) > 0
        
        # Should have BSRG_001 error code
        error_codes = [e.code for e in errors]
        assert ErrorCode.BSRG_001 in error_codes
        
        # BSRG data should indicate not found
        assert bsrg_data["found"] is False
        assert bsrg_data["status"] == "FAIL"
    
    def test_gate_pack_rejects_invalid_bsrg_fields_reviewer_gid(self, pac_wrong_reviewer_gid):
        """Test that PAC with wrong reviewer_gid is rejected."""
        errors, bsrg_data = validate_benson_self_review_gate(pac_wrong_reviewer_gid)
        
        # Should have at least one error
        assert len(errors) > 0
        
        # Should have BSRG_004 error code (wrong reviewer_gid)
        error_codes = [e.code for e in errors]
        assert ErrorCode.BSRG_004 in error_codes
        
        # BSRG data should show the wrong GID
        assert bsrg_data["reviewer_gid"] == "GID-05"
        assert bsrg_data["status"] == "FAIL"
    
    def test_gate_pack_rejects_checklist_not_pass(self, pac_checklist_not_pass):
        """Test that PAC with checklist item not PASS is rejected."""
        errors, bsrg_data = validate_benson_self_review_gate(pac_checklist_not_pass)
        
        # Should have at least one error
        assert len(errors) > 0
        
        # Should have BSRG_007 error code (checklist item not PASS)
        error_codes = [e.code for e in errors]
        assert ErrorCode.BSRG_007 in error_codes
        
        # Failed items should contain the failing item
        assert any("execution_lane_correct" in str(item) for item in bsrg_data["failed_items"])
    
    def test_gate_pack_enforces_bsrg_ordering(self, pac_bsrg_wrong_order):
        """Test that BSRG must appear before GOLD_STANDARD_CHECKLIST."""
        errors, bsrg_data = validate_benson_self_review_gate(pac_bsrg_wrong_order)
        
        # Should have ordering error
        assert len(errors) > 0
        
        # Should have BSRG_010 error code (wrong order)
        error_codes = [e.code for e in errors]
        assert ErrorCode.BSRG_010 in error_codes
    
    def test_gate_pack_accepts_valid_bsrg(self, pac_valid_bsrg):
        """Test that valid PAC with perfect BSRG is accepted."""
        errors, bsrg_data = validate_benson_self_review_gate(pac_valid_bsrg)
        
        # Should have no errors
        assert len(errors) == 0
        
        # BSRG data should indicate success
        assert bsrg_data["found"] is True
        assert bsrg_data["status"] == "PASS"
        assert bsrg_data["gate_id"] == "BSRG-01"
        assert bsrg_data["reviewer"] == "BENSON"
        assert bsrg_data["reviewer_gid"] == "GID-00"
        assert len(bsrg_data["failed_items"]) == 0


class TestBsrgExtraction:
    """Tests for BSRG block extraction."""
    
    def test_extract_bsrg_block_valid(self, pac_valid_bsrg):
        """Test extraction of valid BSRG block."""
        bsrg = extract_bsrg_block(pac_valid_bsrg)
        
        assert bsrg is not None
        assert bsrg.get("gate_id") == "BSRG-01"
        assert bsrg.get("reviewer") == "BENSON"
        assert bsrg.get("reviewer_gid") == "GID-00"
        assert bsrg.get("issuance_policy") == "FAIL_CLOSED"
        assert isinstance(bsrg.get("checklist_results"), dict)
        assert bsrg.get("failed_items") == []
        assert bsrg.get("override_used") is False
    
    def test_extract_bsrg_block_missing(self, pac_missing_bsrg):
        """Test extraction returns None for missing BSRG."""
        bsrg = extract_bsrg_block(pac_missing_bsrg)
        assert bsrg is None


# ═══════════════════════════════════════════════════════════════════════════════
# LEDGER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestLedgerBsrgRecording:
    """Tests for BSRG recording in governance ledger."""
    
    def test_ledger_records_bsrg_pass(self, temp_ledger):
        """Test that BSRG PASS is recorded in ledger."""
        entry = temp_ledger.record_bsrg_review(
            artifact_id="PAC-TEST-01",
            artifact_sha256="abc123",
            reviewer="BENSON",
            reviewer_gid="GID-00",
            bsrg_gate_id="BSRG-01",
            status="PASS",
            failed_items=[],
            checklist_results={"identity_correct": "PASS"},
        )
        
        assert entry.sequence == 1
        assert entry.entry_type == EntryType.BSRG_REVIEW.value
        assert entry.validation_result == "PASS"
        assert entry.artifact_id == "PAC-TEST-01"
    
    def test_ledger_records_bsrg_fail(self, temp_ledger):
        """Test that BSRG FAIL is recorded in ledger."""
        entry = temp_ledger.record_bsrg_review(
            artifact_id="PAC-TEST-02",
            artifact_sha256="def456",
            reviewer="BENSON",
            reviewer_gid="GID-00",
            bsrg_gate_id="BSRG-01",
            status="FAIL",
            failed_items=["missing_bsrg"],
            checklist_results={},
        )
        
        assert entry.sequence == 1
        assert entry.entry_type == EntryType.BSRG_REVIEW.value
        assert entry.validation_result == "FAIL"
        assert entry.error_codes == ["missing_bsrg"]
    
    def test_ledger_hash_chain_validates(self, temp_ledger):
        """Test that ledger hash chain is valid after BSRG entries."""
        # Record multiple entries
        temp_ledger.record_bsrg_review(
            artifact_id="PAC-TEST-01",
            artifact_sha256="abc123",
            reviewer="BENSON",
            reviewer_gid="GID-00",
            bsrg_gate_id="BSRG-01",
            status="PASS",
            failed_items=[],
        )
        
        temp_ledger.record_bsrg_review(
            artifact_id="PAC-TEST-02",
            artifact_sha256="def456",
            reviewer="BENSON",
            reviewer_gid="GID-00",
            bsrg_gate_id="BSRG-01",
            status="FAIL",
            failed_items=["test_failure"],
        )
        
        # Validate hash chain
        result = temp_ledger.validate_hash_chain()
        
        assert result["valid"] is True
        assert result["chain_intact"] is True
        assert result["no_tampering_detected"] is True
        assert result["entries_with_hashes"] == 2
    
    def test_ledger_detects_tampering(self, temp_ledger):
        """Test that ledger detects tampered entries."""
        # Record an entry
        temp_ledger.record_bsrg_review(
            artifact_id="PAC-TEST-01",
            artifact_sha256="abc123",
            reviewer="BENSON",
            reviewer_gid="GID-00",
            bsrg_gate_id="BSRG-01",
            status="PASS",
            failed_items=[],
        )
        
        # Tamper with the entry (simulate modification)
        temp_ledger.ledger_data["entries"][0]["artifact_id"] = "TAMPERED-ID"
        
        # Validate hash chain - should detect tampering
        result = temp_ledger.validate_hash_chain()
        
        assert result["valid"] is False
        assert result["no_tampering_detected"] is False
        assert len(result["issues"]) > 0
        assert result["issues"][0]["type"] == "HASH_MISMATCH"
    
    def test_get_bsrg_reviews(self, temp_ledger):
        """Test querying BSRG reviews from ledger."""
        # Record entries
        temp_ledger.record_bsrg_review(
            artifact_id="PAC-TEST-01",
            artifact_sha256="abc123",
            reviewer="BENSON",
            reviewer_gid="GID-00",
            bsrg_gate_id="BSRG-01",
            status="PASS",
            failed_items=[],
        )
        
        temp_ledger.record_bsrg_review(
            artifact_id="PAC-TEST-02",
            artifact_sha256="def456",
            reviewer="BENSON",
            reviewer_gid="GID-00",
            bsrg_gate_id="BSRG-01",
            status="FAIL",
            failed_items=["test"],
        )
        
        # Query all BSRG reviews
        reviews = temp_ledger.get_bsrg_reviews()
        assert len(reviews) == 2
        
        # Query by artifact
        reviews = temp_ledger.get_bsrg_reviews(artifact_id="PAC-TEST-01")
        assert len(reviews) == 1
        assert reviews[0]["artifact_id"] == "PAC-TEST-01"


class TestLedgerIntegrity:
    """Tests for comprehensive ledger integrity validation."""
    
    def test_validate_ledger_integrity_empty(self, temp_ledger):
        """Test integrity validation on empty ledger."""
        result = temp_ledger.validate_ledger_integrity()
        
        assert result["valid"] is True
        assert result["summary"]["verdict"] == "INTEGRITY_VERIFIED"
    
    def test_validate_ledger_integrity_with_entries(self, temp_ledger):
        """Test integrity validation with entries."""
        # Add some entries
        temp_ledger.record_bsrg_review(
            artifact_id="PAC-TEST-01",
            artifact_sha256="abc123",
            reviewer="BENSON",
            reviewer_gid="GID-00",
            bsrg_gate_id="BSRG-01",
            status="PASS",
            failed_items=[],
        )
        
        result = temp_ledger.validate_ledger_integrity()
        
        assert result["valid"] is True
        assert result["summary"]["total_entries"] == 1
        assert result["summary"]["sequence_issues"] == 0
        assert result["summary"]["hash_issues"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR CODE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBsrgErrorCodes:
    """Tests for BSRG error code definitions."""
    
    def test_bsrg_error_codes_exist(self):
        """Test that all BSRG error codes are defined."""
        expected_codes = [
            "BSRG_001", "BSRG_002", "BSRG_003", "BSRG_004",
            "BSRG_005", "BSRG_006", "BSRG_007", "BSRG_008",
            "BSRG_009", "BSRG_010", "BSRG_011", "BSRG_012",
        ]
        
        for code in expected_codes:
            assert hasattr(ErrorCode, code), f"Missing error code: {code}"
    
    def test_bsrg_error_codes_have_descriptions(self):
        """Test that BSRG error codes have non-empty descriptions."""
        bsrg_codes = [e for e in ErrorCode if e.name.startswith("BSRG")]
        
        for code in bsrg_codes:
            assert code.value, f"Error code {code.name} has no description"
            assert len(code.value) > 5, f"Error code {code.name} description too short"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
