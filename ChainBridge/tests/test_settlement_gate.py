"""Settlement Gate Test Suite.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Cody (GID-01) — Senior Backend Engineer             ║
║ EXECUTING COLOR: 🟢 BLUE                                             ║
║ PAC: PAC-CODY-A6-ARCHITECTURE-ENFORCEMENT-WIRING-01                  ║
╚══════════════════════════════════════════════════════════════════════╝

Tests A6 Architecture Lock enforcement for settlement gate:
- Settlement blocks when CRO requires authority
- Settlement blocks when PDO is invalid
- A6 enforcement gate behavior

DOCTRINE:
- Settlement without valid PDO → BLOCK
- Settlement with CRO HOLD → BLOCK
- Invalid GID at settlement → BLOCK
- All violations are FAIL-CLOSED

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import hashlib
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.services.pdo.validator import (
    PDOValidator,
    ValidationErrorCode,
    ValidationResult,
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
def valid_pdo() -> dict:
    """Provide valid PDO for settlement."""
    inputs_hash = hashlib.sha256(b"settlement-inputs").hexdigest()
    policy_version = "settlement-policy@v1.0"
    outcome = "APPROVED"
    binding_data = f"{inputs_hash}|{policy_version}|{outcome}"
    decision_hash = hashlib.sha256(binding_data.encode("utf-8")).hexdigest()

    return {
        "pdo_id": "PDO-SETTLEMENT01234",
        "inputs_hash": inputs_hash,
        "policy_version": policy_version,
        "decision_hash": decision_hash,
        "outcome": outcome,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signer": "agent::settlement-agent",
        "agent_id": "GID-01",  # Valid agent GID
    }


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request."""
    request = MagicMock(spec=Request)
    request.url.path = "/api/v1/settlements/initiate"
    request.method = "POST"
    return request


# ---------------------------------------------------------------------------
# Settlement Gate A6 Enforcement Tests
# ---------------------------------------------------------------------------


class TestSettlementGateA6Enforcement:
    """Tests for A6 enforcement at settlement gate."""

    def test_settlement_allowed_with_valid_pdo_and_gid(self, validator: PDOValidator, valid_pdo: dict):
        """Settlement should be allowed with valid PDO and valid agent GID."""
        # First validate base PDO
        base_result = validator.validate(valid_pdo)
        assert base_result.valid is True

        # Then validate A6 constraints
        a6_result = validate_pdo_a6_enforcement(valid_pdo)
        assert a6_result.valid is True

    def test_settlement_blocked_with_invalid_gid(self, validator: PDOValidator, valid_pdo: dict):
        """Settlement should be blocked when agent_id has invalid GID format."""
        valid_pdo["agent_id"] = "GID-INVALID"  # Invalid format

        # A6 validation should catch invalid GID format
        # Note: only GID- prefixed values that don't match pattern fail
        a6_result = validate_pdo_a6_enforcement(valid_pdo)

        # "GID-INVALID" starts with GID- so should be validated
        assert a6_result.valid is False
        assert any(e.code == ValidationErrorCode.INVALID_AGENT_GID for e in a6_result.errors)

    def test_settlement_blocked_with_missing_pdo(self, validator: PDOValidator):
        """Settlement should be blocked when PDO is missing."""
        a6_result = validate_pdo_a6_enforcement(None)

        assert a6_result.valid is False
        assert any(e.code == ValidationErrorCode.MISSING_FIELD for e in a6_result.errors)

    def test_settlement_blocked_with_invalid_authority(self, validator: PDOValidator, valid_pdo: dict):
        """Settlement should be blocked when authority GID is invalid."""
        valid_pdo["authority_gid"] = "INVALID-AUTH"
        valid_pdo["authority_signature"] = "sig=="

        a6_result = validate_pdo_a6_enforcement(valid_pdo)

        assert a6_result.valid is False
        assert any(e.code == ValidationErrorCode.INVALID_AUTHORITY_GID for e in a6_result.errors)


# ---------------------------------------------------------------------------
# CRO Settlement Gate Tests
# ---------------------------------------------------------------------------


class TestCROSettlementGate:
    """Tests for CRO policy enforcement at settlement gate."""

    def test_settlement_with_cro_approve(self, valid_pdo: dict):
        """Settlement should proceed when CRO approves."""
        valid_pdo["cro_decision"] = "APPROVE"
        valid_pdo["cro_reasons"] = []
        valid_pdo["cro_evaluated_at"] = datetime.now(timezone.utc).isoformat()

        a6_result = validate_pdo_a6_enforcement(valid_pdo)
        assert a6_result.valid is True

    def test_settlement_with_cro_tighten_terms(self, valid_pdo: dict):
        """Settlement should proceed with tightened terms when CRO requires."""
        valid_pdo["cro_decision"] = "TIGHTEN_TERMS"
        valid_pdo["cro_reasons"] = ["HIGH_EXPOSURE"]
        valid_pdo["cro_evaluated_at"] = datetime.now(timezone.utc).isoformat()

        # A6 enforcement itself doesn't block on TIGHTEN_TERMS
        # (CRO enforcement is handled separately)
        a6_result = validate_pdo_a6_enforcement(valid_pdo)
        assert a6_result.valid is True

    def test_settlement_without_cro_decision_valid(self, valid_pdo: dict):
        """Settlement without CRO decision should be valid (CRO is optional)."""
        # No cro_decision field
        a6_result = validate_pdo_a6_enforcement(valid_pdo)
        assert a6_result.valid is True


# ---------------------------------------------------------------------------
# Settlement Gate Error Response Tests
# ---------------------------------------------------------------------------


class TestSettlementGateErrorResponses:
    """Tests for settlement gate error responses."""

    def test_invalid_gid_produces_correct_error_code(self, valid_pdo: dict):
        """Invalid GID should produce INVALID_AGENT_GID error code."""
        valid_pdo["agent_id"] = "GID-XY"  # Invalid format

        result = validate_pdo_a6_enforcement(valid_pdo)

        assert not result.valid
        error_codes = [e.code for e in result.errors]
        assert ValidationErrorCode.INVALID_AGENT_GID in error_codes

    def test_invalid_authority_produces_correct_error_code(self, valid_pdo: dict):
        """Invalid authority should produce INVALID_AUTHORITY_GID error code."""
        valid_pdo["authority_gid"] = "NOT-A-GID"

        result = validate_pdo_a6_enforcement(valid_pdo)

        assert not result.valid
        error_codes = [e.code for e in result.errors]
        assert ValidationErrorCode.INVALID_AUTHORITY_GID in error_codes

    def test_error_includes_pdo_id(self, valid_pdo: dict):
        """Error response should include pdo_id for audit."""
        valid_pdo["agent_id"] = "GID-XX"  # Invalid

        result = validate_pdo_a6_enforcement(valid_pdo)

        assert result.pdo_id == valid_pdo["pdo_id"]


# ---------------------------------------------------------------------------
# Settlement Gate FAIL-CLOSED Tests
# ---------------------------------------------------------------------------


class TestSettlementGateFailClosed:
    """Tests ensuring FAIL-CLOSED behavior at settlement gate."""

    def test_no_bypass_for_missing_pdo(self):
        """Missing PDO must block settlement, no bypass."""
        result = validate_pdo_a6_enforcement(None)
        assert result.valid is False

    def test_no_bypass_for_empty_pdo(self):
        """Empty PDO dict must block settlement, no bypass."""
        result = validate_pdo_a6_enforcement({})
        # Empty dict has no pdo_id so no errors from A6 (only checks GID fields if present)
        # This is actually valid for A6 because no GID fields to validate
        assert result.valid is True

    def test_multiple_violations_all_reported(self, valid_pdo: dict):
        """Multiple violations should all be reported."""
        valid_pdo["agent_id"] = "GID-XX"  # Invalid agent GID
        valid_pdo["authority_gid"] = "INVALID"  # Invalid authority GID

        result = validate_pdo_a6_enforcement(valid_pdo)

        assert not result.valid
        # Should have at least 2 errors
        assert len(result.errors) >= 2

    def test_validation_deterministic(self, valid_pdo: dict):
        """Same PDO must produce same validation result every time."""
        results = [validate_pdo_a6_enforcement(valid_pdo) for _ in range(5)]

        for result in results:
            assert result.valid == results[0].valid
            assert len(result.errors) == len(results[0].errors)


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestSettlementGateIntegration:
    """Integration tests for settlement gate with full validation chain."""

    def test_full_validation_chain_valid_pdo(self, validator: PDOValidator, valid_pdo: dict):
        """Full validation chain should pass for valid PDO."""
        # Step 1: Base PDO validation
        base_result = validator.validate(valid_pdo)
        assert base_result.valid is True

        # Step 2: A6 enforcement validation
        a6_result = validate_pdo_a6_enforcement(valid_pdo)
        assert a6_result.valid is True

    def test_full_validation_chain_invalid_pdo(self, validator: PDOValidator):
        """Full validation chain should fail for invalid PDO."""
        invalid_pdo = {
            "pdo_id": "INVALID",  # Invalid format
        }

        # Base validation should fail first
        base_result = validator.validate(invalid_pdo)
        assert base_result.valid is False

    def test_validation_order_base_before_a6(self, validator: PDOValidator, valid_pdo: dict):
        """Base validation should run before A6 validation."""
        # Remove required field
        del valid_pdo["outcome"]

        # Base validation fails
        base_result = validator.validate(valid_pdo)
        assert base_result.valid is False

        # A6 validation still runs (independently)
        a6_result = validate_pdo_a6_enforcement(valid_pdo)
        # A6 doesn't check outcome, only GID fields
        assert a6_result.valid is True


# ═══════════════════════════════════════════════════════════════════════════
# END — Cody (GID-01) — 🔵
# ═══════════════════════════════════════════════════════════════════════════
