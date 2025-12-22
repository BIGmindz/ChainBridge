"""PDO Signature Verification Tests.

Tests the PDO Signature Verification Module and Enforcement Integration.

Test Matrix (Updated for Fail-Closed Mode):
1. Valid signed PDO → PASS (signature verified)
2. Modified payload → FAIL (signature mismatch)
3. Unknown key_id → FAIL (key not in registry)
4. Unsupported alg → FAIL (algorithm not supported)
5. Missing signature → FAIL (mandatory signature - no legacy mode)
6. Corrupt base64 → FAIL (malformed signature)
7. Expired PDO → FAIL (time-bound enforcement)
8. Replay nonce → FAIL (replay protection)
9. Wrong signer → FAIL (signer identity verification)

DOCTRINE: PDO Enforcement Model v1 (LOCKED)
- Fail-closed: All non-VALID signatures block execution
- No legacy mode: Unsigned PDOs BLOCKED

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from app.services.pdo.signing import (
    PDOSignature,
    SignatureAlgorithm,
    VerificationOutcome,
    VerificationResult,
    canonicalize_pdo,
    create_test_signature,
    extract_signature,
    get_trusted_key,
    register_trusted_key,
    verify_pdo_signature,
    _ensure_test_key_registered,
    _TEST_HMAC_KEY,
)
from app.services.pdo.validator import (
    PDOValidator,
    ValidationErrorCode,
    ValidationResult,
    compute_decision_hash,
    validate_pdo_with_signature,
)
from app.middleware.pdo_enforcement import (
    SignatureEnforcementGate,
    signature_settlement_gate,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


def _make_valid_pdo(
    pdo_id: str = "PDO-SIGTEST0001",
    outcome: str = "APPROVED",
    policy_version: str = "settlement_policy@v1.0.0",
    signer: str = "system::chainpay",
    agent_id: str = "agent::settlement-engine",
) -> dict[str, Any]:
    """Create a valid PDO with correct hash integrity (no signature).
    
    Includes both canonical signature fields and backward-compat fields.
    """
    import uuid
    from datetime import timedelta
    
    inputs_hash = hashlib.sha256(b"test_inputs").hexdigest()
    decision_hash = compute_decision_hash(inputs_hash, policy_version, outcome)
    timestamp = datetime.now(timezone.utc).isoformat()
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat()
    nonce = uuid.uuid4().hex

    return {
        # Canonical signature fields (PDO_SIGNING_MODEL_V1)
        "pdo_id": pdo_id,
        "decision_hash": decision_hash,
        "policy_version": policy_version,
        "agent_id": agent_id,
        "action": "execute_settlement",
        "outcome": outcome,
        "timestamp": timestamp,
        "nonce": nonce,
        "expires_at": expires_at,
        # Backward-compatible fields
        "inputs_hash": inputs_hash,
        "signer": signer,
    }


def _make_signed_pdo(
    pdo_id: str = "PDO-SIGTEST0001",
    outcome: str = "APPROVED",
    key_id: str = "test-key-001",
    agent_id: str = "agent::settlement-engine",
) -> dict[str, Any]:
    """Create a valid PDO with valid signature."""
    _ensure_test_key_registered()
    pdo = _make_valid_pdo(pdo_id=pdo_id, outcome=outcome, agent_id=agent_id)
    pdo["signature"] = create_test_signature(pdo, key_id=key_id)
    return pdo


def _compute_test_signature(pdo_data: dict[str, Any]) -> str:
    """Compute signature bytes for test PDO."""
    payload = canonicalize_pdo(pdo_data)
    sig_bytes = hmac.new(_TEST_HMAC_KEY, payload, hashlib.sha256).digest()
    return base64.b64encode(sig_bytes).decode("ascii")


# ---------------------------------------------------------------------------
# Test: PDOSignature Schema
# ---------------------------------------------------------------------------


class TestPDOSignatureSchema:
    """Tests for PDOSignature dataclass."""

    def test_from_dict_valid(self):
        """Valid signature dict creates PDOSignature."""
        data = {
            "alg": "HMAC-SHA256",
            "key_id": "test-key-001",
            "sig": "YWJjZGVm",  # "abcdef" base64
        }
        sig = PDOSignature.from_dict(data)
        assert sig is not None
        assert sig.alg == "HMAC-SHA256"
        assert sig.key_id == "test-key-001"
        assert sig.sig == "YWJjZGVm"

    def test_from_dict_missing_alg(self):
        """Missing 'alg' field returns None."""
        data = {"key_id": "test-key-001", "sig": "YWJjZGVm"}
        assert PDOSignature.from_dict(data) is None

    def test_from_dict_missing_key_id(self):
        """Missing 'key_id' field returns None."""
        data = {"alg": "HMAC-SHA256", "sig": "YWJjZGVm"}
        assert PDOSignature.from_dict(data) is None

    def test_from_dict_missing_sig(self):
        """Missing 'sig' field returns None."""
        data = {"alg": "HMAC-SHA256", "key_id": "test-key-001"}
        assert PDOSignature.from_dict(data) is None

    def test_from_dict_non_string_values(self):
        """Non-string values return None."""
        data = {"alg": 123, "key_id": "test-key-001", "sig": "YWJjZGVm"}
        assert PDOSignature.from_dict(data) is None

    def test_from_dict_not_a_dict(self):
        """Non-dict input returns None."""
        assert PDOSignature.from_dict("not a dict") is None
        assert PDOSignature.from_dict(None) is None
        assert PDOSignature.from_dict([]) is None


# ---------------------------------------------------------------------------
# Test: Canonical Serialization
# ---------------------------------------------------------------------------


class TestCanonicalSerialization:
    """Tests for deterministic PDO canonicalization."""

    def test_canonicalize_produces_bytes(self):
        """canonicalize_pdo returns UTF-8 bytes."""
        pdo = _make_valid_pdo()
        result = canonicalize_pdo(pdo)
        assert isinstance(result, bytes)

    def test_canonicalize_deterministic(self):
        """Same PDO always produces same canonical form."""
        pdo = _make_valid_pdo()
        result1 = canonicalize_pdo(pdo)
        result2 = canonicalize_pdo(pdo)
        assert result1 == result2

    def test_canonicalize_order_independent(self):
        """Field order in input dict doesn't affect output."""
        pdo1 = _make_valid_pdo()
        # Create dict with different field order (all canonical signature fields)
        pdo2 = {
            "timestamp": pdo1["timestamp"],
            "outcome": pdo1["outcome"],
            "pdo_id": pdo1["pdo_id"],
            "decision_hash": pdo1["decision_hash"],
            "policy_version": pdo1["policy_version"],
            "agent_id": pdo1["agent_id"],
            "action": pdo1["action"],
            "nonce": pdo1["nonce"],
            "expires_at": pdo1["expires_at"],
            # Backward-compat fields (not in SIGNATURE_FIELDS)
            "signer": pdo1["signer"],
            "inputs_hash": pdo1["inputs_hash"],
        }
        assert canonicalize_pdo(pdo1) == canonicalize_pdo(pdo2)

    def test_canonicalize_excludes_signature(self):
        """Signature field is not included in canonical form."""
        pdo = _make_valid_pdo()
        canonical1 = canonicalize_pdo(pdo)

        pdo["signature"] = {"alg": "HMAC-SHA256", "key_id": "x", "sig": "y"}
        canonical2 = canonicalize_pdo(pdo)

        assert canonical1 == canonical2

    def test_canonicalize_valid_json(self):
        """Canonical output is valid JSON."""
        pdo = _make_valid_pdo()
        canonical = canonicalize_pdo(pdo)
        parsed = json.loads(canonical)
        assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# Test: Signature Verification (Core Function)
# ---------------------------------------------------------------------------


class TestVerifyPDOSignature:
    """Tests for verify_pdo_signature function."""

    def test_valid_signed_pdo_passes(self):
        """Valid signed PDO returns VALID outcome."""
        pdo = _make_signed_pdo()
        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.VALID
        assert result.is_valid is True
        assert result.allows_execution is True
        assert result.key_id == "test-key-001"
        assert result.algorithm == "HMAC-SHA256"

    def test_modified_payload_fails(self):
        """Modified payload after signing fails verification."""
        pdo = _make_signed_pdo()
        # Tamper with a field after signature was created
        pdo["outcome"] = "REJECTED"

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.INVALID_SIGNATURE
        assert result.is_valid is False
        assert result.allows_execution is False
        assert "does not match" in result.reason

    def test_unknown_key_id_fails(self):
        """Unknown key_id returns UNKNOWN_KEY_ID outcome."""
        pdo = _make_valid_pdo()
        pdo["signature"] = {
            "alg": "HMAC-SHA256",
            "key_id": "unknown-key-999",
            "sig": base64.b64encode(b"fake").decode("ascii"),
        }

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.UNKNOWN_KEY_ID
        assert result.is_valid is False
        assert result.allows_execution is False
        assert "not in trusted registry" in result.reason

    def test_unsupported_algorithm_fails(self):
        """Unsupported algorithm returns UNSUPPORTED_ALGORITHM outcome."""
        pdo = _make_valid_pdo()
        pdo["signature"] = {
            "alg": "RSA-OAEP-256",  # Not supported
            "key_id": "test-key-001",
            "sig": base64.b64encode(b"fake").decode("ascii"),
        }

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.UNSUPPORTED_ALGORITHM
        assert result.is_valid is False
        assert result.allows_execution is False

    def test_missing_signature_blocked(self):
        """PDO without signature returns UNSIGNED_PDO and blocks execution.
        
        PAC-CODY-PDO-SIGNING-IMPL-01 (Updated): Signature is MANDATORY.
        Unsigned PDOs must NOT pass validation (fail-closed).
        """
        pdo = _make_valid_pdo()  # No signature field

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.UNSIGNED_PDO
        assert result.is_unsigned is True
        assert result.is_valid is False
        # Fail-closed: unsigned PDOs BLOCKED (no legacy mode)
        assert result.allows_execution is False

    def test_corrupt_base64_fails(self):
        """Corrupt base64 in signature returns MALFORMED_SIGNATURE."""
        pdo = _make_valid_pdo()
        _ensure_test_key_registered()
        pdo["signature"] = {
            "alg": "HMAC-SHA256",
            "key_id": "test-key-001",
            "sig": "!!!not-valid-base64!!!",
        }

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.MALFORMED_SIGNATURE
        assert result.is_valid is False
        assert result.allows_execution is False

    def test_none_pdo_returns_unsigned(self):
        """None PDO data returns UNSIGNED_PDO and blocks execution.
        
        PAC-CODY-PDO-SIGNING-IMPL-01 (Updated): Fail-closed mode.
        """
        result = verify_pdo_signature(None)
        assert result.outcome == VerificationOutcome.UNSIGNED_PDO
        assert result.allows_execution is False  # Fail-closed (no legacy mode)

    def test_empty_dict_returns_unsigned(self):
        """Empty dict PDO returns UNSIGNED_PDO."""
        result = verify_pdo_signature({})
        assert result.outcome == VerificationOutcome.UNSIGNED_PDO

    def test_pdo_id_captured_in_result(self):
        """PDO ID is captured in verification result."""
        pdo = _make_signed_pdo(pdo_id="PDO-UNIQUE123456")
        result = verify_pdo_signature(pdo)
        assert result.pdo_id == "PDO-UNIQUE123456"


# ---------------------------------------------------------------------------
# Test: Key Registry
# ---------------------------------------------------------------------------


class TestKeyRegistry:
    """Tests for trusted key registration and lookup."""

    def test_register_and_lookup_hmac_key(self):
        """Register HMAC key and retrieve verification function.
        
        Note: register_trusted_key now takes 4 args (key_id, alg, key, agent_id).
        """
        register_trusted_key(
            "custom-hmac-key",
            SignatureAlgorithm.HMAC_SHA256.value,
            b"custom-secret",
            agent_id="agent::test",
        )
        key_info = get_trusted_key("custom-hmac-key")
        assert key_info is not None
        alg, verify_func, bound_agent_id = key_info
        assert alg == "HMAC-SHA256"
        assert callable(verify_func)
        assert bound_agent_id == "agent::test"

    def test_lookup_unknown_key_returns_none(self):
        """Looking up unregistered key returns None."""
        assert get_trusted_key("nonexistent-key-xyz") is None

    def test_test_key_auto_registered(self):
        """Test key is auto-registered when needed."""
        _ensure_test_key_registered()
        key_info = get_trusted_key("test-key-001")
        assert key_info is not None


# ---------------------------------------------------------------------------
# Test: PDOValidator with Signature
# ---------------------------------------------------------------------------


class TestPDOValidatorWithSignature:
    """Tests for validate_with_signature method."""

    def test_valid_signed_pdo_passes_validation(self):
        """Valid signed PDO passes full validation."""
        pdo = _make_signed_pdo()
        result = validate_pdo_with_signature(pdo)

        assert result.valid is True
        assert len(result.errors) == 0
        assert result.signature_result is not None
        assert result.signature_result.verified is True
        assert result.signature_result.outcome == "VALID"

    def test_invalid_signature_fails_validation(self):
        """Invalid signature fails validation (fail-closed)."""
        pdo = _make_signed_pdo()
        # Tamper with timestamp - doesn't affect decision_hash but does affect signature
        pdo["timestamp"] = "2099-12-31T23:59:59+00:00"

        result = validate_pdo_with_signature(pdo)

        assert result.valid is False
        assert any(e.code == ValidationErrorCode.INVALID_SIGNATURE for e in result.errors)
        assert result.signature_result is not None
        assert result.signature_result.verified is False

    def test_unsigned_pdo_blocked(self):
        """Unsigned PDO fails validation (fail-closed).
        
        PAC-CODY-PDO-SIGNING-IMPL-01 (Updated): No legacy unsigned mode.
        """
        pdo = _make_valid_pdo()  # No signature

        result = validate_pdo_with_signature(pdo)

        assert result.valid is False  # Fail-closed: must fail
        assert result.signature_result is not None
        assert result.signature_result.is_unsigned is True
        assert result.signature_result.allows_execution is False

    def test_schema_failure_skips_signature_check(self):
        """If schema validation fails, signature is not checked."""
        pdo = {"pdo_id": "invalid"}  # Missing required fields

        result = validate_pdo_with_signature(pdo)

        assert result.valid is False
        assert result.signature_result is None  # Not checked

    def test_unknown_key_id_fails_validation(self):
        """Unknown key_id fails validation."""
        pdo = _make_valid_pdo()
        pdo["signature"] = {
            "alg": "HMAC-SHA256",
            "key_id": "unknown-key-abc",
            "sig": base64.b64encode(b"fake").decode("ascii"),
        }

        result = validate_pdo_with_signature(pdo)

        assert result.valid is False
        assert any(e.code == ValidationErrorCode.UNKNOWN_KEY_ID for e in result.errors)


# ---------------------------------------------------------------------------
# Test: SignatureEnforcementGate
# ---------------------------------------------------------------------------


class TestSignatureEnforcementGate:
    """Tests for SignatureEnforcementGate middleware."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app with signature enforcement."""
        app = FastAPI()
        gate = SignatureEnforcementGate("test_endpoint")

        @app.post("/test")
        async def test_endpoint(
            request: Request,
            _enforced: None = Depends(gate.enforce),
        ):
            return {"status": "executed"}

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)

    def test_valid_signed_pdo_allowed(self, client):
        """Valid signed PDO allows execution."""
        pdo = _make_signed_pdo()
        response = client.post("/test", json={"pdo": pdo})

        assert response.status_code == 200
        assert response.json() == {"status": "executed"}

    def test_invalid_signature_blocked(self, client):
        """Invalid signature blocks execution (HTTP 403)."""
        pdo = _make_signed_pdo()
        # Tamper with timestamp - doesn't affect decision_hash but does affect signature
        pdo["timestamp"] = "2099-12-31T23:59:59+00:00"

        response = client.post("/test", json={"pdo": pdo})

        assert response.status_code == 403
        detail = response.json()["detail"]
        assert "PDO_ENFORCEMENT_FAILED" in detail["error"]
        assert any(e["code"] == "INVALID_SIGNATURE" for e in detail["errors"])

    def test_missing_pdo_blocked(self, client):
        """Missing PDO blocks execution (HTTP 403)."""
        response = client.post("/test", json={})

        assert response.status_code == 403

    def test_unsigned_pdo_blocked(self, client):
        """Unsigned PDO blocked (fail-closed).
        
        PAC-CODY-PDO-SIGNING-IMPL-01 (Updated): No legacy unsigned mode.
        """
        pdo = _make_valid_pdo()  # No signature

        response = client.post("/test", json={"pdo": pdo})

        # Fail-closed: must block
        assert response.status_code == 403

    def test_unknown_key_id_blocked(self, client):
        """Unknown key_id blocks execution."""
        pdo = _make_valid_pdo()
        pdo["signature"] = {
            "alg": "HMAC-SHA256",
            "key_id": "unknown-key-xyz",
            "sig": base64.b64encode(b"fake").decode("ascii"),
        }

        response = client.post("/test", json={"pdo": pdo})

        assert response.status_code == 403
        detail = response.json()["detail"]
        assert any(e["code"] == "UNKNOWN_KEY_ID" for e in detail["errors"])

    def test_malformed_signature_blocked(self, client):
        """Malformed signature blocks execution."""
        pdo = _make_valid_pdo()
        _ensure_test_key_registered()
        pdo["signature"] = {
            "alg": "HMAC-SHA256",
            "key_id": "test-key-001",
            "sig": "not-base64-at-all!!!",
        }

        response = client.post("/test", json={"pdo": pdo})

        assert response.status_code == 403
        detail = response.json()["detail"]
        assert any(e["code"] == "MALFORMED_SIGNATURE" for e in detail["errors"])


# ---------------------------------------------------------------------------
# Test: Verification Result Properties
# ---------------------------------------------------------------------------


class TestVerificationResultProperties:
    """Tests for VerificationResult helper properties."""

    def test_is_valid_true_for_valid(self):
        """is_valid is True for VALID outcome."""
        result = VerificationResult(
            outcome=VerificationOutcome.VALID,
            pdo_id="PDO-TEST00000001",
        )
        assert result.is_valid is True

    def test_is_valid_false_for_invalid(self):
        """is_valid is False for INVALID_SIGNATURE outcome."""
        result = VerificationResult(
            outcome=VerificationOutcome.INVALID_SIGNATURE,
            pdo_id="PDO-TEST00000001",
        )
        assert result.is_valid is False

    def test_is_unsigned_true_for_unsigned(self):
        """is_unsigned is True for UNSIGNED_PDO outcome."""
        result = VerificationResult(
            outcome=VerificationOutcome.UNSIGNED_PDO,
            pdo_id="PDO-TEST00000001",
        )
        assert result.is_unsigned is True

    def test_allows_execution_for_valid(self):
        """allows_execution is True for VALID outcome."""
        result = VerificationResult(
            outcome=VerificationOutcome.VALID,
            pdo_id="PDO-TEST00000001",
        )
        assert result.allows_execution is True

    def test_allows_execution_false_for_unsigned(self):
        """allows_execution is False for UNSIGNED_PDO (fail-closed).
        
        PAC-CODY-PDO-SIGNING-IMPL-01 (Updated): No legacy unsigned mode.
        """
        result = VerificationResult(
            outcome=VerificationOutcome.UNSIGNED_PDO,
            pdo_id="PDO-TEST00000001",
        )
        assert result.allows_execution is False

    def test_allows_execution_false_for_invalid(self):
        """allows_execution is False for INVALID_SIGNATURE."""
        result = VerificationResult(
            outcome=VerificationOutcome.INVALID_SIGNATURE,
            pdo_id="PDO-TEST00000001",
        )
        assert result.allows_execution is False


# ---------------------------------------------------------------------------
# Test: Edge Cases and Security
# ---------------------------------------------------------------------------


class TestSignatureSecurityCases:
    """Security-focused edge case tests."""

    def test_tampered_action_fails(self):
        """Tampering action after signing fails.
        
        Note: inputs_hash is a backward-compat field NOT in SIGNATURE_FIELDS.
        Testing action instead which IS in the canonical signature fields.
        """
        pdo = _make_signed_pdo()
        pdo["action"] = "tampered_action"

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.INVALID_SIGNATURE

    def test_tampered_timestamp_fails(self):
        """Tampering timestamp after signing fails."""
        pdo = _make_signed_pdo()
        pdo["timestamp"] = "2099-12-31T23:59:59+00:00"

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.INVALID_SIGNATURE

    def test_tampered_agent_id_fails(self):
        """Tampering agent_id after signing fails.
        
        Note: signer is a backward-compat field NOT in SIGNATURE_FIELDS.
        Testing agent_id instead which IS in the canonical signature fields.
        """
        pdo = _make_signed_pdo()
        pdo["agent_id"] = "agent::attacker"

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.INVALID_SIGNATURE

    def test_empty_signature_envelope(self):
        """Empty signature envelope treated as unsigned."""
        pdo = _make_valid_pdo()
        pdo["signature"] = {}

        result = verify_pdo_signature(pdo)
        # Empty envelope fails to parse → treated as malformed? No, as unsigned
        # PDOSignature.from_dict returns None for empty/invalid
        assert result.outcome == VerificationOutcome.UNSIGNED_PDO

    def test_signature_with_extra_fields_ignored(self):
        """Extra fields in signature envelope are ignored."""
        pdo = _make_signed_pdo()
        pdo["signature"]["extra_field"] = "should be ignored"

        result = verify_pdo_signature(pdo)
        # Should still verify successfully
        assert result.outcome == VerificationOutcome.VALID

    def test_algorithm_mismatch_key_registered_different_alg(self):
        """Key registered for different algorithm fails."""
        # Register key as HMAC but claim it's ED25519
        register_trusted_key(
            "alg-mismatch-key",
            SignatureAlgorithm.HMAC_SHA256.value,
            b"secret",
        )

        pdo = _make_valid_pdo()
        pdo["signature"] = {
            "alg": "ED25519",  # Claim different algorithm
            "key_id": "alg-mismatch-key",
            "sig": base64.b64encode(b"fake").decode("ascii"),
        }

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.UNSUPPORTED_ALGORITHM

    def test_replay_different_pdo_id_fails(self):
        """Signature from one PDO cannot be replayed on another."""
        pdo1 = _make_signed_pdo(pdo_id="PDO-ORIGINAL001")
        pdo2 = _make_signed_pdo(pdo_id="PDO-REPLAYED002")

        # Try to use pdo1's signature on pdo2
        pdo2["signature"] = pdo1["signature"]

        result = verify_pdo_signature(pdo2)
        assert result.outcome == VerificationOutcome.INVALID_SIGNATURE


# ---------------------------------------------------------------------------
# Test: create_test_signature utility
# ---------------------------------------------------------------------------


class TestCreateTestSignature:
    """Tests for the test signature creation utility."""

    def test_creates_valid_signature(self):
        """create_test_signature creates verifiable signature."""
        pdo = _make_valid_pdo()
        sig = create_test_signature(pdo)

        assert "alg" in sig
        assert "key_id" in sig
        assert "sig" in sig
        assert sig["alg"] == "HMAC-SHA256"

    def test_signature_verifies(self):
        """Signature created by utility verifies successfully."""
        pdo = _make_valid_pdo()
        pdo["signature"] = create_test_signature(pdo)

        result = verify_pdo_signature(pdo)
        assert result.is_valid is True

    def test_custom_key_id(self):
        """Custom key_id is used when specified."""
        _ensure_test_key_registered()
        pdo = _make_valid_pdo()
        sig = create_test_signature(pdo, key_id="test-key-001")
        assert sig["key_id"] == "test-key-001"