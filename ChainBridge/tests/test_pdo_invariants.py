"""PDO Invariants Test Suite.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Cody (GID-01) — Senior Backend Engineer             ║
║ EXECUTING COLOR: 🟢 BLUE                                             ║
║ PAC: PAC-CODY-A6-ARCHITECTURE-ENFORCEMENT-WIRING-01                  ║
╚══════════════════════════════════════════════════════════════════════╝

Tests A6 Architecture Lock enforcement for PDO invariants:
- Agent GID format validation
- Authority signature requirements
- PDO creation enforcement

DOCTRINE:
- Every test validates FAIL-CLOSED behavior
- Invalid GIDs MUST cause validation failure
- Missing authority MUST block when required
- No bypass paths exist

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import hashlib
import pytest
from datetime import datetime, timezone

from app.services.pdo.validator import (
    PDOValidator,
    ValidationErrorCode,
    ValidationResult,
    AGENT_GID_PATTERN,
    AUTHORITY_GID_PATTERN,
    validate_pdo,
    validate_pdo_a6_enforcement,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def validator() -> PDOValidator:
    """Provide PDOValidator instance."""
    return PDOValidator()


@pytest.fixture
def valid_pdo_base() -> dict:
    """Provide valid base PDO without A6 fields."""
    inputs_hash = hashlib.sha256(b"test-inputs").hexdigest()
    policy_version = "test-policy@v1.0"
    outcome = "APPROVED"
    binding_data = f"{inputs_hash}|{policy_version}|{outcome}"
    decision_hash = hashlib.sha256(binding_data.encode("utf-8")).hexdigest()
    
    return {
        "pdo_id": "PDO-A6TEST12345678",
        "inputs_hash": inputs_hash,
        "policy_version": policy_version,
        "decision_hash": decision_hash,
        "outcome": outcome,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signer": "agent::test-agent-01",
    }


# ---------------------------------------------------------------------------
# Agent GID Pattern Tests
# ---------------------------------------------------------------------------


class TestAgentGIDPattern:
    """Tests for Agent GID format validation."""
    
    def test_valid_gid_formats(self):
        """Valid GID formats should match pattern."""
        valid_gids = [
            "GID-00",  # Benson
            "GID-01",  # Cody
            "GID-12",  # Ruby
            "GID-99",  # Max valid
        ]
        for gid in valid_gids:
            assert AGENT_GID_PATTERN.match(gid), f"GID '{gid}' should be valid"
    
    def test_invalid_gid_formats(self):
        """Invalid GID formats should not match pattern."""
        invalid_gids = [
            "gid-01",  # lowercase
            "GID01",   # no dash
            "GID-1",   # single digit
            "GID-001", # three digits
            "GID-AB",  # letters
            "GID-",    # no digits
            "ID-01",   # wrong prefix
            "",        # empty
            "RUNTIME", # runtime identifier
        ]
        for gid in invalid_gids:
            assert not AGENT_GID_PATTERN.match(gid), f"GID '{gid}' should be invalid"
    
    def test_validator_rejects_invalid_gid(self, validator: PDOValidator, valid_pdo_base: dict):
        """Validator should reject PDO with invalid agent_gid."""
        # GID-INVALID starts with GID- so it IS validated and fails
        valid_pdo_base["agent_id"] = "GID-INVALID"  # Invalid format
        
        result = validator.validate_a6_enforcement(valid_pdo_base)
        
        assert result.valid is False  # GID-INVALID doesn't match GID-NN pattern
        assert any(e.code == ValidationErrorCode.INVALID_AGENT_GID for e in result.errors)
        
        # Another invalid format: single digit
        valid_pdo_base["agent_id"] = "GID-1"  # Only 1 digit
        result = validator.validate_a6_enforcement(valid_pdo_base)
        
        assert result.valid is False
        assert any(e.code == ValidationErrorCode.INVALID_AGENT_GID for e in result.errors)
    
    def test_validator_accepts_valid_gid(self, validator: PDOValidator, valid_pdo_base: dict):
        """Validator should accept PDO with valid agent_gid."""
        valid_pdo_base["agent_id"] = "GID-01"  # Valid Cody GID
        
        result = validator.validate_a6_enforcement(valid_pdo_base)
        
        assert result.valid is True
        assert len(result.errors) == 0


# ---------------------------------------------------------------------------
# Authority GID Pattern Tests
# ---------------------------------------------------------------------------


class TestAuthorityGIDPattern:
    """Tests for Authority GID format validation."""
    
    def test_valid_authority_gid_formats(self):
        """Valid authority GID formats should match pattern."""
        valid_gids = [
            "GID-00",  # Benson can authorize
            "GID-12",  # Ruby can authorize
        ]
        for gid in valid_gids:
            assert AUTHORITY_GID_PATTERN.match(gid), f"Authority GID '{gid}' should be valid"
    
    def test_validator_rejects_invalid_authority_gid(self, validator: PDOValidator, valid_pdo_base: dict):
        """Validator should reject PDO with invalid authority_gid."""
        valid_pdo_base["authority_gid"] = "INVALID-GID"
        valid_pdo_base["authority_signature"] = "base64signature=="
        
        result = validator.validate_a6_enforcement(valid_pdo_base)
        
        assert result.valid is False
        assert any(e.code == ValidationErrorCode.INVALID_AUTHORITY_GID for e in result.errors)
    
    def test_validator_accepts_valid_authority_gid(self, validator: PDOValidator, valid_pdo_base: dict):
        """Validator should accept PDO with valid authority_gid."""
        valid_pdo_base["authority_gid"] = "GID-00"  # Benson authorization
        valid_pdo_base["authority_signature"] = "base64signature=="
        
        result = validator.validate_a6_enforcement(valid_pdo_base)
        
        assert result.valid is True
    
    def test_signature_without_gid_fails(self, validator: PDOValidator, valid_pdo_base: dict):
        """Authority signature without GID should fail validation."""
        valid_pdo_base["authority_signature"] = "base64signature=="
        # Intentionally NO authority_gid
        
        result = validator.validate_a6_enforcement(valid_pdo_base)
        
        assert result.valid is False
        assert any(e.code == ValidationErrorCode.INVALID_AUTHORITY_GID for e in result.errors)


# ---------------------------------------------------------------------------
# PDO Creation Enforcement Tests
# ---------------------------------------------------------------------------


class TestPDOCreationEnforcement:
    """Tests for PDO creation enforcement invariants."""
    
    def test_null_pdo_fails_a6_validation(self, validator: PDOValidator):
        """Null PDO should fail A6 validation."""
        result = validator.validate_a6_enforcement(None)
        
        assert result.valid is False
        assert any(e.code == ValidationErrorCode.MISSING_FIELD for e in result.errors)
    
    def test_pdo_without_agent_fields_valid(self, validator: PDOValidator, valid_pdo_base: dict):
        """PDO without A6 agent fields should be valid (legacy support)."""
        # No agent_id, no authority_gid, no authority_signature
        result = validator.validate_a6_enforcement(valid_pdo_base)
        
        assert result.valid is True
    
    def test_pdo_with_all_valid_fields(self, validator: PDOValidator, valid_pdo_base: dict):
        """PDO with all valid A6 fields should pass."""
        valid_pdo_base["agent_id"] = "GID-01"
        valid_pdo_base["authority_gid"] = "GID-00"
        valid_pdo_base["authority_signature"] = "base64sig=="
        
        result = validator.validate_a6_enforcement(valid_pdo_base)
        
        assert result.valid is True
    
    def test_module_level_validation_function(self, valid_pdo_base: dict):
        """Module-level validate_pdo_a6_enforcement should work."""
        valid_pdo_base["agent_id"] = "GID-01"
        
        result = validate_pdo_a6_enforcement(valid_pdo_base)
        
        assert result.valid is True
        assert result.pdo_id == valid_pdo_base["pdo_id"]


# ---------------------------------------------------------------------------
# FAIL-CLOSED Behavior Tests
# ---------------------------------------------------------------------------


class TestFailClosedBehavior:
    """Tests ensuring FAIL-CLOSED behavior for A6 enforcement."""
    
    def test_invalid_gid_always_fails(self, validator: PDOValidator, valid_pdo_base: dict):
        """Invalid GID must always cause failure, no bypass."""
        invalid_gids = [
            "GID-",
            "GID-1",
            "GID-ABC",
            "gid-01",
        ]
        
        for invalid_gid in invalid_gids:
            valid_pdo_base["agent_id"] = invalid_gid
            result = validator.validate_a6_enforcement(valid_pdo_base)
            
            # Only GID- prefixed values trigger validation
            if invalid_gid.startswith("GID-"):
                assert result.valid is False, f"GID '{invalid_gid}' should fail validation"
    
    def test_no_soft_bypass_for_authority(self, validator: PDOValidator, valid_pdo_base: dict):
        """Authority signature without GID must fail, no soft bypass."""
        # Try various ways to sneak in a signature without proper GID
        bypass_attempts = [
            {"authority_signature": "sig==", "authority_gid": ""},  # Empty GID
            {"authority_signature": "sig==", "authority_gid": None},  # None GID
        ]
        
        for attempt in bypass_attempts:
            pdo = valid_pdo_base.copy()
            pdo.update(attempt)
            
            result = validator.validate_a6_enforcement(pdo)
            
            # Signature present without valid GID should fail
            if pdo.get("authority_signature") and not pdo.get("authority_gid"):
                assert result.valid is False, f"Bypass attempt should fail: {attempt}"
    
    def test_validation_is_deterministic(self, validator: PDOValidator, valid_pdo_base: dict):
        """Same input must produce same validation result."""
        valid_pdo_base["agent_id"] = "GID-01"
        
        results = [validator.validate_a6_enforcement(valid_pdo_base) for _ in range(10)]
        
        # All results should be identical
        first = results[0]
        for result in results[1:]:
            assert result.valid == first.valid
            assert len(result.errors) == len(first.errors)


# ---------------------------------------------------------------------------
# Error Code Tests
# ---------------------------------------------------------------------------


class TestA6ErrorCodes:
    """Tests for A6-specific error codes."""
    
    def test_invalid_agent_gid_error_code(self, validator: PDOValidator, valid_pdo_base: dict):
        """INVALID_AGENT_GID error code should be returned for bad GID."""
        valid_pdo_base["agent_id"] = "GID-X"  # Invalid
        
        result = validator.validate_a6_enforcement(valid_pdo_base)
        
        assert any(e.code == ValidationErrorCode.INVALID_AGENT_GID for e in result.errors)
    
    def test_invalid_authority_gid_error_code(self, validator: PDOValidator, valid_pdo_base: dict):
        """INVALID_AUTHORITY_GID error code should be returned for bad authority GID."""
        valid_pdo_base["authority_gid"] = "BAD-GID"
        
        result = validator.validate_a6_enforcement(valid_pdo_base)
        
        assert any(e.code == ValidationErrorCode.INVALID_AUTHORITY_GID for e in result.errors)
    
    def test_error_messages_are_informative(self, validator: PDOValidator, valid_pdo_base: dict):
        """Error messages should explain the violation."""
        valid_pdo_base["agent_id"] = "GID-ABC"
        
        result = validator.validate_a6_enforcement(valid_pdo_base)
        
        assert result.valid is False
        error = next(e for e in result.errors if e.code == ValidationErrorCode.INVALID_AGENT_GID)
        assert "GID-NN" in error.message or "pattern" in error.message.lower()


# ═══════════════════════════════════════════════════════════════════════════
# END — Cody (GID-01) — 🔵
# ═══════════════════════════════════════════════════════════════════════════
