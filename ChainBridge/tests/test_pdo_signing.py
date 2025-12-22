"""PDO Cryptographic Signing Tests.

Tests the PDO Signing implementation per PDO_SIGNING_MODEL_V1.md specification.

Test Matrix (MANDATORY):
1. Unsigned PDO → FAIL
2. Modified field after signing → FAIL
3. Wrong signer (key/agent mismatch) → FAIL
4. Expired PDO → FAIL
5. Replay nonce → FAIL
6. Valid signed PDO → PASS

DOCTRINE: PDO Enforcement Model v1 (LOCKED)
- Fail-closed: ALL invalid signatures block execution
- Signature is MANDATORY (no legacy unsigned mode)
- Replay protection via nonce + expires_at

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from app.services.pdo.signing import (
    PDOSignature,
    SignatureAlgorithm,
    VerificationOutcome,
    VerificationResult,
    SIGNATURE_FIELDS,
    canonicalize_pdo,
    create_test_signature,
    extract_signature,
    verify_pdo_signature,
    register_trusted_key,
    clear_nonce_registry,
    _ensure_test_key_registered,
    _TEST_HMAC_KEY,
)
from app.services.pdo.validator import (
    PDOValidator,
    ValidationErrorCode,
    validate_pdo_with_signature,
    compute_decision_hash,
)
from app.middleware.pdo_enforcement import (
    SignatureEnforcementGate,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_nonce_registry():
    """Reset nonce registry before each test to prevent cross-test pollution."""
    clear_nonce_registry()
    yield
    clear_nonce_registry()


def _make_valid_signed_pdo(
    pdo_id: str = None,
    outcome: str = "APPROVED",
    agent_id: str = "agent::settlement-engine",
    expires_in_seconds: int = 300,
    key_id: str = "test-key-001",
) -> dict[str, Any]:
    """Create a valid PDO with signature per PDO_SIGNING_MODEL_V1.md.

    Canonical fields for signature (in order):
    - pdo_id
    - decision_hash
    - policy_version
    - agent_id
    - action
    - outcome
    - timestamp
    - nonce
    - expires_at

    Also includes backward-compatible fields for schema validation:
    - inputs_hash, signer (mapped from new fields)
    """
    _ensure_test_key_registered()

    if pdo_id is None:
        pdo_id = f"PDO-{uuid.uuid4().hex[:12].upper()}"

    timestamp = datetime.now(timezone.utc).isoformat()
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)).isoformat()
    nonce = uuid.uuid4().hex
    inputs_hash = hashlib.sha256(b"test_inputs").hexdigest()
    policy_version = "settlement_policy@v1.0.0"

    # Compute decision_hash correctly for existing validator
    decision_hash = compute_decision_hash(inputs_hash, policy_version, outcome)

    pdo = {
        # New canonical fields (for signature)
        "pdo_id": pdo_id,
        "decision_hash": decision_hash,
        "policy_version": policy_version,
        "agent_id": agent_id,
        "action": "execute_settlement",
        "outcome": outcome,
        "timestamp": timestamp,
        "nonce": nonce,
        "expires_at": expires_at,
        # Backward-compatible fields (for schema validation)
        "inputs_hash": inputs_hash,
        "signer": agent_id,  # Map agent_id to signer for compat
    }

    # Add signature
    pdo["signature"] = create_test_signature(pdo, key_id=key_id)
    return pdo


def _make_unsigned_pdo() -> dict[str, Any]:
    """Create a PDO without signature (should FAIL)."""
    agent_id = "agent::settlement-engine"
    inputs_hash = hashlib.sha256(b"test_inputs").hexdigest()
    policy_version = "settlement_policy@v1.0.0"
    outcome = "APPROVED"
    decision_hash = compute_decision_hash(inputs_hash, policy_version, outcome)

    return {
        # New canonical fields
        "pdo_id": f"PDO-{uuid.uuid4().hex[:12].upper()}",
        "decision_hash": decision_hash,
        "policy_version": policy_version,
        "agent_id": agent_id,
        "action": "execute_settlement",
        "outcome": outcome,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nonce": uuid.uuid4().hex,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat(),
        # Backward-compatible fields
        "inputs_hash": inputs_hash,
        "signer": agent_id,
    }


# ---------------------------------------------------------------------------
# Test 1: Unsigned PDO → FAIL
# ---------------------------------------------------------------------------


class TestUnsignedPDOBlocked:
    """Verify that unsigned PDOs are REJECTED (fail-closed)."""

    def test_unsigned_pdo_verification_fails(self):
        """Unsigned PDO returns UNSIGNED_PDO outcome."""
        pdo = _make_unsigned_pdo()
        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.UNSIGNED_PDO
        assert result.is_valid is False
        assert result.allows_execution is False

    def test_unsigned_pdo_validation_fails(self):
        """Unsigned PDO fails full validation."""
        pdo = _make_unsigned_pdo()
        result = validate_pdo_with_signature(pdo)

        assert result.valid is False
        assert any(e.code == ValidationErrorCode.UNSIGNED_PDO for e in result.errors)

    def test_unsigned_pdo_blocked_at_gate(self):
        """Unsigned PDO blocked by enforcement gate."""
        app = FastAPI()
        gate = SignatureEnforcementGate("test_endpoint")

        @app.post("/test")
        async def test_endpoint(
            request: Request,
            _enforced: None = Depends(gate.enforce),
        ):
            return {"status": "executed"}

        client = TestClient(app)
        pdo = _make_unsigned_pdo()
        response = client.post("/test", json={"pdo": pdo})

        assert response.status_code == 403
        detail = response.json()["detail"]
        assert any(e["code"] == "UNSIGNED_PDO" for e in detail["errors"])


# ---------------------------------------------------------------------------
# Test 2: Modified Field After Signing → FAIL
# ---------------------------------------------------------------------------


class TestModifiedFieldBlocked:
    """Verify that tampering with PDO after signing is detected."""

    def test_tampered_outcome_fails(self):
        """Changing outcome after signing fails verification."""
        pdo = _make_valid_signed_pdo(outcome="APPROVED")
        pdo["outcome"] = "REJECTED"  # Tamper

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.INVALID_SIGNATURE
        assert result.allows_execution is False

    def test_tampered_agent_id_fails(self):
        """Changing agent_id after signing fails verification."""
        pdo = _make_valid_signed_pdo(agent_id="agent::legitimate")
        pdo["agent_id"] = "agent::attacker"  # Tamper

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.INVALID_SIGNATURE
        assert result.allows_execution is False

    def test_tampered_decision_hash_fails(self):
        """Changing decision_hash after signing fails verification."""
        pdo = _make_valid_signed_pdo()
        pdo["decision_hash"] = hashlib.sha256(b"tampered").hexdigest()  # Tamper

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.INVALID_SIGNATURE
        assert result.allows_execution is False

    def test_tampered_timestamp_fails(self):
        """Changing timestamp after signing fails verification."""
        pdo = _make_valid_signed_pdo()
        pdo["timestamp"] = "2099-12-31T23:59:59+00:00"  # Tamper

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.INVALID_SIGNATURE
        assert result.allows_execution is False

    def test_tampered_nonce_fails(self):
        """Changing nonce after signing fails verification."""
        pdo = _make_valid_signed_pdo()
        pdo["nonce"] = "tampered-nonce-value"  # Tamper

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.INVALID_SIGNATURE
        assert result.allows_execution is False

    def test_tampered_policy_version_fails(self):
        """Changing policy_version after signing fails verification."""
        pdo = _make_valid_signed_pdo()
        pdo["policy_version"] = "malicious_policy@v9.9.9"  # Tamper

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.INVALID_SIGNATURE
        assert result.allows_execution is False


# ---------------------------------------------------------------------------
# Test 3: Wrong Signer → FAIL
# ---------------------------------------------------------------------------


class TestWrongSignerBlocked:
    """Verify that signer mismatch is detected."""

    def test_signer_mismatch_fails(self):
        """Key bound to different agent_id fails verification."""
        # Register a key bound to specific agent
        register_trusted_key(
            "bound-agent-key",
            SignatureAlgorithm.HMAC_SHA256.value,
            b"bound-agent-secret",
            agent_id="agent::authorized-agent",
        )

        # Create PDO for different agent but signed with bound key
        pdo = _make_valid_signed_pdo(
            agent_id="agent::unauthorized-agent",
            key_id="bound-agent-key",
        )

        # Re-sign with the bound key
        payload = canonicalize_pdo(pdo)
        sig_bytes = hmac.new(b"bound-agent-secret", payload, hashlib.sha256).digest()
        pdo["signature"] = {
            "alg": "HMAC-SHA256",
            "key_id": "bound-agent-key",
            "sig": base64.b64encode(sig_bytes).decode("ascii"),
        }

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.SIGNER_MISMATCH
        assert result.allows_execution is False

    def test_unknown_key_id_fails(self):
        """Unknown key_id fails verification."""
        pdo = _make_valid_signed_pdo()
        pdo["signature"]["key_id"] = "unknown-key-xyz"

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.UNKNOWN_KEY_ID
        assert result.allows_execution is False


# ---------------------------------------------------------------------------
# Test 4: Expired PDO → FAIL
# ---------------------------------------------------------------------------


class TestExpiredPDOBlocked:
    """Verify that expired PDOs are rejected."""

    def test_expired_pdo_fails(self):
        """PDO with expires_at in past fails verification."""
        pdo = _make_valid_signed_pdo(expires_in_seconds=-60)  # Expired 1 minute ago

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.EXPIRED_PDO
        assert result.allows_execution is False

    def test_expires_at_exactly_now_fails(self):
        """PDO expiring at current moment fails (boundary case)."""
        # Create PDO that expires immediately
        pdo = _make_valid_signed_pdo(expires_in_seconds=0)
        # Small sleep to ensure expiry
        import time
        time.sleep(0.1)

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.EXPIRED_PDO
        assert result.allows_execution is False

    def test_invalid_expires_at_format_fails(self):
        """Invalid expires_at format is treated as expired (fail-closed)."""
        pdo = _make_valid_signed_pdo()
        pdo["expires_at"] = "not-a-valid-timestamp"
        # Re-sign with invalid timestamp
        pdo["signature"] = create_test_signature(pdo)

        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.EXPIRED_PDO
        assert result.allows_execution is False


# ---------------------------------------------------------------------------
# Test 5: Replay Nonce → FAIL
# ---------------------------------------------------------------------------


class TestReplayBlocked:
    """Verify that replay attacks are prevented via nonce tracking."""

    def test_duplicate_nonce_fails(self):
        """Using same nonce twice fails second verification."""
        pdo1 = _make_valid_signed_pdo()
        nonce = pdo1["nonce"]

        # First use should pass
        result1 = verify_pdo_signature(pdo1)
        assert result1.outcome == VerificationOutcome.VALID

        # Create new PDO with same nonce
        pdo2 = _make_valid_signed_pdo()
        pdo2["nonce"] = nonce
        pdo2["signature"] = create_test_signature(pdo2)

        # Second use should fail
        result2 = verify_pdo_signature(pdo2)

        assert result2.outcome == VerificationOutcome.REPLAY_DETECTED
        assert result2.allows_execution is False

    def test_replay_with_different_pdo_fails(self):
        """Replaying signature from one PDO on another fails."""
        pdo1 = _make_valid_signed_pdo(pdo_id="PDO-ORIGINAL0001")
        pdo2 = _make_valid_signed_pdo(pdo_id="PDO-REPLAYED0002")

        # Use nonce and signature from pdo1 on pdo2
        pdo2["nonce"] = pdo1["nonce"]
        pdo2["signature"] = pdo1["signature"]

        # First verify pdo1 to register nonce
        result1 = verify_pdo_signature(pdo1)
        assert result1.outcome == VerificationOutcome.VALID

        # pdo2 should fail (signature mismatch AND replay)
        result2 = verify_pdo_signature(pdo2)
        # Will fail on replay before signature check
        assert result2.outcome == VerificationOutcome.REPLAY_DETECTED


# ---------------------------------------------------------------------------
# Test 6: Valid Signed PDO → PASS
# ---------------------------------------------------------------------------


class TestValidSignedPDOPasses:
    """Verify that properly signed PDOs pass verification."""

    def test_valid_pdo_passes_verification(self):
        """Valid signed PDO returns VALID outcome."""
        pdo = _make_valid_signed_pdo()
        result = verify_pdo_signature(pdo)

        assert result.outcome == VerificationOutcome.VALID
        assert result.is_valid is True
        assert result.allows_execution is True

    def test_valid_pdo_passes_full_validation(self):
        """Valid signed PDO passes validate_pdo_with_signature."""
        pdo = _make_valid_signed_pdo()
        result = validate_pdo_with_signature(pdo)

        assert result.valid is True
        assert len(result.errors) == 0
        assert result.signature_result is not None
        assert result.signature_result.verified is True

    def test_valid_pdo_allowed_at_gate(self):
        """Valid signed PDO allowed through enforcement gate."""
        app = FastAPI()
        gate = SignatureEnforcementGate("test_endpoint")

        @app.post("/test")
        async def test_endpoint(
            request: Request,
            _enforced: None = Depends(gate.enforce),
        ):
            return {"status": "executed"}

        client = TestClient(app)
        pdo = _make_valid_signed_pdo()
        response = client.post("/test", json={"pdo": pdo})

        assert response.status_code == 200
        assert response.json() == {"status": "executed"}

    def test_different_valid_pdos_both_pass(self):
        """Multiple different valid PDOs all pass (unique nonces)."""
        for i in range(5):
            pdo = _make_valid_signed_pdo(pdo_id=f"PDO-VALID{i:08d}")
            result = verify_pdo_signature(pdo)
            assert result.outcome == VerificationOutcome.VALID, f"PDO {i} failed"


# ---------------------------------------------------------------------------
# Test: Canonical Serialization
# ---------------------------------------------------------------------------


class TestCanonicalSerialization:
    """Verify canonical serialization follows spec."""

    def test_canonical_field_order(self):
        """Verify SIGNATURE_FIELDS matches PDO_SIGNING_MODEL_V1.md."""
        expected_fields = (
            "pdo_id",
            "decision_hash",
            "policy_version",
            "agent_id",
            "action",
            "outcome",
            "timestamp",
            "nonce",
            "expires_at",
        )
        assert SIGNATURE_FIELDS == expected_fields

    def test_canonicalize_deterministic(self):
        """Same PDO always produces same canonical form."""
        pdo = _make_valid_signed_pdo()
        canonical1 = canonicalize_pdo(pdo)
        canonical2 = canonicalize_pdo(pdo)
        assert canonical1 == canonical2

    def test_canonicalize_excludes_signature(self):
        """Signature field is not in canonical form."""
        pdo = _make_valid_signed_pdo()
        canonical = canonicalize_pdo(pdo)
        assert b"signature" not in canonical


# ---------------------------------------------------------------------------
# Test: Enforcement Gate Integration
# ---------------------------------------------------------------------------


class TestEnforcementGateIntegration:
    """Verify enforcement gate properly blocks invalid PDOs."""

    @pytest.fixture
    def app_and_client(self):
        """Create test app with signature enforcement."""
        app = FastAPI()
        gate = SignatureEnforcementGate("test_enforcement")

        @app.post("/execute")
        async def execute(
            request: Request,
            _enforced: None = Depends(gate.enforce),
        ):
            return {"status": "executed", "blocked": False}

        return app, TestClient(app)

    def test_all_failure_modes_blocked(self, app_and_client):
        """All failure modes result in HTTP 403."""
        _, client = app_and_client

        # Unsigned
        response = client.post("/execute", json={"pdo": _make_unsigned_pdo()})
        assert response.status_code == 403

        # Missing PDO
        response = client.post("/execute", json={})
        assert response.status_code == 403

        # Tampered
        pdo = _make_valid_signed_pdo()
        pdo["outcome"] = "TAMPERED"
        response = client.post("/execute", json={"pdo": pdo})
        assert response.status_code == 403

    def test_no_bypass_path(self, app_and_client):
        """There is no way to bypass signature enforcement."""
        _, client = app_and_client

        # Try various bypass attempts
        bypass_attempts = [
            {},  # Empty body
            {"pdo": None},  # Null PDO
            {"pdo": {}},  # Empty PDO
            {"pdo": {"signature": {}}},  # Empty signature
            {"pdo": {"signature": {"alg": "x", "key_id": "y", "sig": "z"}}},  # Minimal
        ]

        for attempt in bypass_attempts:
            response = client.post("/execute", json=attempt)
            assert response.status_code == 403, f"Bypass succeeded with: {attempt}"


# ---------------------------------------------------------------------------
# Test: Error Code Mapping
# ---------------------------------------------------------------------------


class TestErrorCodeMapping:
    """Verify all verification outcomes map to validation error codes."""

    def test_all_failure_outcomes_have_error_codes(self):
        """Every non-VALID outcome maps to a ValidationErrorCode."""
        failure_outcomes = [
            VerificationOutcome.INVALID_SIGNATURE,
            VerificationOutcome.UNSUPPORTED_ALGORITHM,
            VerificationOutcome.UNKNOWN_KEY_ID,
            VerificationOutcome.MALFORMED_SIGNATURE,
            VerificationOutcome.UNSIGNED_PDO,
            VerificationOutcome.EXPIRED_PDO,
            VerificationOutcome.REPLAY_DETECTED,
            VerificationOutcome.SIGNER_MISMATCH,
        ]

        expected_error_codes = [
            ValidationErrorCode.INVALID_SIGNATURE,
            ValidationErrorCode.UNSUPPORTED_ALGORITHM,
            ValidationErrorCode.UNKNOWN_KEY_ID,
            ValidationErrorCode.MALFORMED_SIGNATURE,
            ValidationErrorCode.UNSIGNED_PDO,
            ValidationErrorCode.EXPIRED_PDO,
            ValidationErrorCode.REPLAY_DETECTED,
            ValidationErrorCode.SIGNER_MISMATCH,
        ]

        # Verify 1:1 mapping
        for outcome, expected_code in zip(failure_outcomes, expected_error_codes):
            assert outcome.value == expected_code.value


# ---------------------------------------------------------------------------
# Test: Signature Envelope Schema
# ---------------------------------------------------------------------------


class TestSignatureEnvelopeSchema:
    """Verify signature envelope validation."""

    def test_valid_envelope_parsed(self):
        """Valid signature envelope parses correctly."""
        data = {
            "alg": "HMAC-SHA256",
            "key_id": "test-key-001",
            "sig": base64.b64encode(b"test").decode("ascii"),
        }
        sig = PDOSignature.from_dict(data)
        assert sig is not None
        assert sig.alg == "HMAC-SHA256"
        assert sig.key_id == "test-key-001"

    def test_missing_alg_returns_none(self):
        """Missing 'alg' field returns None."""
        data = {"key_id": "x", "sig": "y"}
        assert PDOSignature.from_dict(data) is None

    def test_missing_key_id_returns_none(self):
        """Missing 'key_id' field returns None."""
        data = {"alg": "x", "sig": "y"}
        assert PDOSignature.from_dict(data) is None

    def test_missing_sig_returns_none(self):
        """Missing 'sig' field returns None."""
        data = {"alg": "x", "key_id": "y"}
        assert PDOSignature.from_dict(data) is None
