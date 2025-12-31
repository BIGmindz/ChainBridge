"""Adversarial PDO Signing Tests.

PAC-SAM-PDO-EXECUTION-THREAT-VALIDATION-01
Agent: Sam (GID-06) — Security & Threat Engineer
Mode: Adversarial / Verification-Only

These tests verify fail-closed behavior for all attack vectors.
No bypass path should exist.
"""
import hashlib
import base64
import hmac
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from app.services.pdo.signing import (
    verify_pdo_signature,
    create_test_signature,
    VerificationOutcome,
    clear_nonce_registry,
    _ensure_test_key_registered,
    _TEST_HMAC_KEY,
    canonicalize_pdo,
    register_trusted_key,
    SignatureAlgorithm,
)
from app.services.pdo.validator import compute_decision_hash
from app.middleware.pdo_enforcement import SignatureEnforcementGate


@pytest.fixture(autouse=True)
def setup():
    """Reset state before each test."""
    _ensure_test_key_registered()
    clear_nonce_registry()
    yield
    clear_nonce_registry()


def _make_pdo(
    pdo_id="PDO-TEST00000001",
    outcome="APPROVED",
    nonce=None,
    expires_in=3600,
):
    """Create PDO for testing."""
    inputs_hash = "a" * 64
    policy_version = "test@v1.0.0"
    return {
        "pdo_id": pdo_id,
        "decision_hash": compute_decision_hash(inputs_hash, policy_version, outcome),
        "policy_version": policy_version,
        "agent_id": "agent::test",
        "action": "test",
        "outcome": outcome,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "nonce": nonce or f"nonce-{pdo_id}",
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
        "inputs_hash": inputs_hash,
        "signer": "agent::test",
    }


# ===========================================================================
# Category 1: Execution Bypass Analysis
# ===========================================================================


class TestExecutionBypass:
    """Verify no execution path bypasses signature enforcement."""

    def test_missing_pdo_blocked(self):
        """Missing PDO data returns UNSIGNED_PDO."""
        result = verify_pdo_signature(None)
        assert result.outcome == VerificationOutcome.UNSIGNED_PDO
        assert result.allows_execution is False

    def test_empty_pdo_blocked(self):
        """Empty PDO dict returns UNSIGNED_PDO."""
        result = verify_pdo_signature({})
        assert result.outcome == VerificationOutcome.UNSIGNED_PDO
        assert result.allows_execution is False

    def test_unsigned_pdo_blocked(self):
        """PDO without signature field returns UNSIGNED_PDO."""
        pdo = _make_pdo()
        # No signature field
        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.UNSIGNED_PDO
        assert result.allows_execution is False

    def test_invalid_signature_blocked(self):
        """PDO with tampered content blocked."""
        pdo = _make_pdo()
        pdo["signature"] = create_test_signature(pdo)
        pdo["outcome"] = "REJECTED"  # Tamper after signing

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.INVALID_SIGNATURE
        assert result.allows_execution is False

    def test_enforcement_gate_blocks_all_failures(self):
        """SignatureEnforcementGate returns 403 for all failures."""
        app = FastAPI()
        gate = SignatureEnforcementGate("test")

        @app.post("/test")
        async def test_endpoint(
            request: Request,
            _enforced: None = Depends(gate.enforce),
        ):
            return {"executed": True}

        client = TestClient(app)

        # Missing PDO
        response = client.post("/test", json={})
        assert response.status_code == 403

        # Unsigned PDO
        response = client.post("/test", json={"pdo": _make_pdo()})
        assert response.status_code == 403

        # Valid PDO passes
        valid_pdo = _make_pdo(pdo_id="PDO-VALIDGATE001")
        valid_pdo["signature"] = create_test_signature(valid_pdo)
        response = client.post("/test", json={"pdo": valid_pdo})
        assert response.status_code == 200


# ===========================================================================
# Category 2: Replay & Timing Attacks
# ===========================================================================


class TestReplayAndTiming:
    """Verify replay protection via nonce and expiry."""

    def test_nonce_reuse_blocked(self):
        """Same nonce cannot be used twice."""
        pdo1 = _make_pdo(pdo_id="PDO-REPLAY000001", nonce="SHARED_NONCE")
        pdo1["signature"] = create_test_signature(pdo1)

        # First use succeeds
        result1 = verify_pdo_signature(pdo1)
        assert result1.outcome == VerificationOutcome.VALID

        # Second use with same nonce fails
        pdo2 = _make_pdo(pdo_id="PDO-REPLAY000002", nonce="SHARED_NONCE")
        pdo2["signature"] = create_test_signature(pdo2)

        result2 = verify_pdo_signature(pdo2)
        assert result2.outcome == VerificationOutcome.REPLAY_DETECTED
        assert result2.allows_execution is False

    def test_expired_pdo_blocked(self):
        """PDO with past expires_at is rejected."""
        pdo = _make_pdo(pdo_id="PDO-EXPIRED00001", expires_in=-60)
        pdo["signature"] = create_test_signature(pdo)

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.EXPIRED_PDO
        assert result.allows_execution is False

    def test_expiry_boundary_blocked(self):
        """PDO expiring at current moment is rejected."""
        import time
        pdo = _make_pdo(pdo_id="PDO-BOUNDARY0001", expires_in=0)
        pdo["signature"] = create_test_signature(pdo)
        time.sleep(0.1)  # Ensure expiry

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.EXPIRED_PDO
        assert result.allows_execution is False

    def test_invalid_expiry_format_blocked(self):
        """Invalid expires_at format is treated as expired (fail-closed)."""
        pdo = _make_pdo(pdo_id="PDO-BADEXPIRY01")
        pdo["expires_at"] = "not-a-timestamp"
        pdo["signature"] = create_test_signature(pdo)

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.EXPIRED_PDO
        assert result.allows_execution is False


# ===========================================================================
# Category 3: Signer Confusion Attacks
# ===========================================================================


class TestSignerConfusion:
    """Verify signer identity is enforced."""

    def test_signer_mismatch_blocked(self):
        """Key bound to different agent_id blocks execution."""
        register_trusted_key(
            "bound-agent-key",
            SignatureAlgorithm.HMAC_SHA256.value,
            b"bound-secret-key",
            agent_id="agent::authorized",
        )

        pdo = _make_pdo(pdo_id="PDO-MISMATCH0001")
        pdo["agent_id"] = "agent::unauthorized"  # Different from bound key

        # Sign with bound key
        payload = canonicalize_pdo(pdo)
        sig_bytes = hmac.new(b"bound-secret-key", payload, hashlib.sha256).digest()
        pdo["signature"] = {
            "alg": "HMAC-SHA256",
            "key_id": "bound-agent-key",
            "sig": base64.b64encode(sig_bytes).decode(),
        }

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.SIGNER_MISMATCH
        assert result.allows_execution is False

    def test_unknown_key_id_blocked(self):
        """Unknown key_id is rejected."""
        pdo = _make_pdo(pdo_id="PDO-UNKNOWNKEY1")
        pdo["signature"] = {
            "alg": "HMAC-SHA256",
            "key_id": "unknown-key-xyz",
            "sig": base64.b64encode(b"fake").decode(),
        }

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.UNKNOWN_KEY_ID
        assert result.allows_execution is False

    def test_algorithm_mismatch_blocked(self):
        """Algorithm in signature must match key registration."""
        pdo = _make_pdo(pdo_id="PDO-ALGOMATCH01")
        pdo["signature"] = create_test_signature(pdo)
        pdo["signature"]["alg"] = "ED25519"  # Key registered for HMAC-SHA256

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.UNSUPPORTED_ALGORITHM
        assert result.allows_execution is False


# ===========================================================================
# Category 4: Transport & Serialization Attacks
# ===========================================================================


class TestSerializationAttacks:
    """Verify serialization and transport cannot bypass enforcement."""

    def test_empty_signature_dict_blocked(self):
        """Empty signature dict is treated as unsigned."""
        pdo = _make_pdo(pdo_id="PDO-EMPTYSIG001")
        pdo["signature"] = {}

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.UNSIGNED_PDO
        assert result.allows_execution is False

    def test_malformed_base64_blocked(self):
        """Invalid base64 in sig field is rejected."""
        pdo = _make_pdo(pdo_id="PDO-MALFORMED01")
        pdo["signature"] = {
            "alg": "HMAC-SHA256",
            "key_id": "test-key-001",
            "sig": "!!!not-valid-base64!!!",
        }

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.MALFORMED_SIGNATURE
        assert result.allows_execution is False

    def test_field_reordering_no_effect(self):
        """Field order in PDO dict does not affect verification."""
        # Original order
        pdo1 = _make_pdo(pdo_id="PDO-REORDER0001")
        pdo1["signature"] = create_test_signature(pdo1)

        # Reordered fields (same content)
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
            "inputs_hash": pdo1["inputs_hash"],
            "signer": pdo1["signer"],
            "signature": pdo1["signature"],
        }

        result = verify_pdo_signature(pdo2)
        assert result.outcome == VerificationOutcome.VALID

    def test_extra_fields_ignored(self):
        """Extra fields outside SIGNATURE_FIELDS are ignored."""
        pdo = _make_pdo(pdo_id="PDO-EXTRAFIELD1")
        pdo["signature"] = create_test_signature(pdo)
        pdo["malicious_field"] = "attacker_data"
        pdo["extra_metadata"] = {"evil": True}

        result = verify_pdo_signature(pdo)
        # Signature still valid (extra fields not in canonical form)
        assert result.outcome == VerificationOutcome.VALID

    def test_tampered_signed_field_detected(self):
        """Any change to SIGNATURE_FIELDS invalidates signature."""
        fields_to_tamper = [
            ("pdo_id", "PDO-TAMPERED0001"),
            ("decision_hash", "b" * 64),
            ("policy_version", "evil@v9.9.9"),
            ("agent_id", "agent::evil"),
            ("action", "evil_action"),
            ("outcome", "REJECTED"),
            ("timestamp", "2099-01-01T00:00:00+00:00"),
            ("nonce", "tampered-nonce"),
            ("expires_at", "2099-12-31T23:59:59+00:00"),
        ]

        for field, tampered_value in fields_to_tamper:
            clear_nonce_registry()
            pdo = _make_pdo(pdo_id=f"PDO-TAMPER{field[:8].upper()}")
            pdo["signature"] = create_test_signature(pdo)
            pdo[field] = tampered_value  # Tamper after signing

            result = verify_pdo_signature(pdo)
            assert result.allows_execution is False, f"Tampering {field} should block"


# ===========================================================================
# Category 5: Audit Integrity
# ===========================================================================


class TestAuditIntegrity:
    """Verify all failures are properly logged and classified."""

    def test_all_failure_outcomes_block_execution(self):
        """Every non-VALID outcome has allows_execution=False."""
        blocked_outcomes = [
            VerificationOutcome.INVALID_SIGNATURE,
            VerificationOutcome.UNSUPPORTED_ALGORITHM,
            VerificationOutcome.UNKNOWN_KEY_ID,
            VerificationOutcome.MALFORMED_SIGNATURE,
            VerificationOutcome.UNSIGNED_PDO,
            VerificationOutcome.EXPIRED_PDO,
            VerificationOutcome.REPLAY_DETECTED,
            VerificationOutcome.SIGNER_MISMATCH,
        ]

        for outcome in blocked_outcomes:
            from app.services.pdo.signing import VerificationResult
            result = VerificationResult(
                outcome=outcome,
                pdo_id="PDO-TEST",
                reason="test",
            )
            assert result.allows_execution is False, f"{outcome} should block"

    def test_only_valid_allows_execution(self):
        """Only VALID outcome allows execution."""
        from app.services.pdo.signing import VerificationResult

        valid_result = VerificationResult(
            outcome=VerificationOutcome.VALID,
            pdo_id="PDO-TEST",
            reason="test",
        )
        assert valid_result.allows_execution is True

    def test_enforcement_error_includes_details(self):
        """Enforcement errors include deterministic classification."""
        app = FastAPI()
        gate = SignatureEnforcementGate("audit_test")

        @app.post("/test")
        async def test_endpoint(
            request: Request,
            _enforced: None = Depends(gate.enforce),
        ):
            return {"executed": True}

        client = TestClient(app)

        # Submit unsigned PDO
        pdo = _make_pdo(pdo_id="PDO-AUDITTEST01")
        response = client.post("/test", json={"pdo": pdo})

        assert response.status_code == 403
        detail = response.json()["detail"]
        assert detail["error"] == "PDO_ENFORCEMENT_FAILED"
        assert "errors" in detail
        assert len(detail["errors"]) > 0
        assert any(e["code"] == "UNSIGNED_PDO" for e in detail["errors"])


# ===========================================================================
# Category 6: Valid PDO (Control Test)
# ===========================================================================


class TestValidPDOPasses:
    """Confirm valid signed PDOs pass verification."""

    def test_valid_pdo_passes(self):
        """Properly signed PDO with valid fields passes."""
        pdo = _make_pdo(pdo_id="PDO-VALID0000001")
        pdo["signature"] = create_test_signature(pdo)

        result = verify_pdo_signature(pdo)
        assert result.outcome == VerificationOutcome.VALID
        assert result.allows_execution is True

    def test_valid_pdo_at_gate(self):
        """Valid PDO passes enforcement gate."""
        app = FastAPI()
        gate = SignatureEnforcementGate("valid_test")

        @app.post("/test")
        async def test_endpoint(
            request: Request,
            _enforced: None = Depends(gate.enforce),
        ):
            return {"executed": True}

        client = TestClient(app)

        pdo = _make_pdo(pdo_id="PDO-VALIDGATE001")
        pdo["signature"] = create_test_signature(pdo)
        response = client.post("/test", json={"pdo": pdo})

        assert response.status_code == 200
        assert response.json()["executed"] is True
