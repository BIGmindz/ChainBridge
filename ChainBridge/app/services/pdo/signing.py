"""PDO Signature Verification Module.

Implements cryptographic signature verification for Proof Decision Outcomes (PDOs)
per PDO Signing Model v1 specification.

DOCTRINE COMPLIANCE:
- PDO Enforcement Model v1 (LOCKED)
- Fail-closed: Invalid signatures block execution
- Verify-only: No signing operations in this module

SUPPORTED ALGORITHMS:
- ED25519: EdDSA with Ed25519 curve
- HMAC-SHA256: HMAC with SHA-256 (for testing/legacy)

VERIFICATION OUTCOMES:
- VALID: Signature is cryptographically valid
- INVALID_SIGNATURE: Signature does not match payload
- UNSUPPORTED_ALGORITHM: Algorithm not recognized
- UNKNOWN_KEY_ID: Key ID not in trusted registry
- MALFORMED_SIGNATURE: Cannot decode signature bytes
- UNSIGNED_PDO: No signature present (legacy, WARN only)

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signature Schema
# ---------------------------------------------------------------------------


class SignatureAlgorithm(str, Enum):
    """Supported signature algorithms."""

    ED25519 = "ED25519"
    HMAC_SHA256 = "HMAC-SHA256"


class VerificationOutcome(str, Enum):
    """Possible outcomes from signature verification."""

    VALID = "VALID"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    UNSUPPORTED_ALGORITHM = "UNSUPPORTED_ALGORITHM"
    UNKNOWN_KEY_ID = "UNKNOWN_KEY_ID"
    MALFORMED_SIGNATURE = "MALFORMED_SIGNATURE"
    UNSIGNED_PDO = "UNSIGNED_PDO"


@dataclass(frozen=True)
class PDOSignature:
    """Signature envelope attached to PDO.

    Attributes:
        alg: Signature algorithm (ED25519, HMAC-SHA256)
        key_id: Identifier of the signing key in trusted registry
        sig: Base64-encoded signature bytes
    """

    alg: str
    key_id: str
    sig: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Optional["PDOSignature"]:
        """Parse signature from dictionary.

        Returns None if data is missing required fields.
        """
        if not isinstance(data, dict):
            return None

        alg = data.get("alg")
        key_id = data.get("key_id")
        sig = data.get("sig")

        if not all(isinstance(v, str) for v in [alg, key_id, sig]):
            return None

        return cls(alg=alg, key_id=key_id, sig=sig)


@dataclass(frozen=True)
class VerificationResult:
    """Result from PDO signature verification.

    Attributes:
        outcome: Verification outcome (VALID, INVALID_SIGNATURE, etc.)
        pdo_id: The PDO ID that was verified
        key_id: Key ID used for verification (if present)
        algorithm: Algorithm used (if present)
        reason: Human-readable explanation
        verified_at: Timestamp of verification
    """

    outcome: VerificationOutcome
    pdo_id: Optional[str]
    key_id: Optional[str] = None
    algorithm: Optional[str] = None
    reason: str = ""
    verified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_valid(self) -> bool:
        """Check if signature is cryptographically valid."""
        return self.outcome == VerificationOutcome.VALID

    @property
    def is_unsigned(self) -> bool:
        """Check if PDO is unsigned (legacy mode)."""
        return self.outcome == VerificationOutcome.UNSIGNED_PDO

    @property
    def allows_execution(self) -> bool:
        """Check if this result allows execution.

        DOCTRINE: Unsigned PDOs are TEMPORARILY allowed (legacy mode).
        TODO: Remove legacy allowance in deprecation PAC.
        """
        return self.outcome in {
            VerificationOutcome.VALID,
            VerificationOutcome.UNSIGNED_PDO,  # TEMPORARY: Legacy compatibility
        }


# ---------------------------------------------------------------------------
# Canonical Payload Serialization
# ---------------------------------------------------------------------------

# Fields included in signature (in canonical order)
SIGNATURE_FIELDS = (
    "pdo_id",
    "inputs_hash",
    "policy_version",
    "decision_hash",
    "outcome",
    "timestamp",
    "signer",
)


def canonicalize_pdo(pdo_data: dict[str, Any]) -> bytes:
    """Create canonical byte representation of PDO for signing/verification.

    INVARIANTS:
    - Deterministic: Same PDO always produces same bytes
    - Order-independent: Field order in input dict doesn't matter
    - Excludes signature: 'signature' field is not part of signed data

    Args:
        pdo_data: PDO dictionary (may contain signature field)

    Returns:
        UTF-8 encoded JSON bytes in canonical form
    """
    # Extract only signature-covered fields in canonical order
    canonical_data = {}
    for field_name in SIGNATURE_FIELDS:
        if field_name in pdo_data:
            value = pdo_data[field_name]
            # Normalize strings
            if isinstance(value, str):
                canonical_data[field_name] = value
            elif isinstance(value, datetime):
                canonical_data[field_name] = value.isoformat()
            else:
                canonical_data[field_name] = str(value)

    # Serialize with sorted keys and no whitespace (canonical JSON)
    return json.dumps(canonical_data, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------------------
# Key Registry (Trusted Public Keys)
# ---------------------------------------------------------------------------
# In production, this would be loaded from secure storage.
# For implementation, we use a static registry with test keys.
# ---------------------------------------------------------------------------

# Test HMAC key for unit tests (NEVER use in production)
_TEST_HMAC_KEY = b"test-secret-key-for-unit-tests-only"

# Registry of trusted key IDs to verification functions
_KEY_REGISTRY: dict[str, tuple[str, Callable[[bytes, bytes], bool]]] = {}


def _hmac_sha256_verify(key: bytes) -> Callable[[bytes, bytes], bool]:
    """Create HMAC-SHA256 verification function for a key."""

    def verify(payload: bytes, signature: bytes) -> bool:
        expected = hmac.new(key, payload, hashlib.sha256).digest()
        return hmac.compare_digest(expected, signature)

    return verify


def register_trusted_key(key_id: str, algorithm: str, key_material: bytes) -> None:
    """Register a trusted key for signature verification.

    Args:
        key_id: Unique identifier for the key
        algorithm: Signature algorithm (ED25519, HMAC-SHA256)
        key_material: Key bytes (public key for ED25519, secret for HMAC)
    """
    if algorithm == SignatureAlgorithm.HMAC_SHA256.value:
        _KEY_REGISTRY[key_id] = (algorithm, _hmac_sha256_verify(key_material))
    elif algorithm == SignatureAlgorithm.ED25519.value:
        # ED25519 verification would require cryptography library
        # For now, we don't have production ED25519 keys
        logger.warning("ED25519 key registration not yet implemented: %s", key_id)
    else:
        logger.warning("Unknown algorithm for key registration: %s", algorithm)


def get_trusted_key(key_id: str) -> Optional[tuple[str, Callable[[bytes, bytes], bool]]]:
    """Get verification function for a trusted key.

    Returns:
        Tuple of (algorithm, verify_function) or None if key not found
    """
    return _KEY_REGISTRY.get(key_id)


def _ensure_test_key_registered() -> None:
    """Ensure test key is registered (for unit tests)."""
    if "test-key-001" not in _KEY_REGISTRY:
        register_trusted_key(
            "test-key-001",
            SignatureAlgorithm.HMAC_SHA256.value,
            _TEST_HMAC_KEY,
        )


# ---------------------------------------------------------------------------
# Signature Verification Implementation
# ---------------------------------------------------------------------------


def extract_signature(pdo_data: Optional[dict]) -> Optional[PDOSignature]:
    """Extract signature envelope from PDO if present.

    Args:
        pdo_data: PDO dictionary (may contain 'signature' field)

    Returns:
        PDOSignature if valid signature envelope found, None otherwise
    """
    if not pdo_data or not isinstance(pdo_data, dict):
        return None

    sig_data = pdo_data.get("signature")
    if not sig_data:
        return None

    return PDOSignature.from_dict(sig_data)


def verify_pdo_signature(pdo_data: Optional[dict]) -> VerificationResult:
    """Verify PDO signature.

    This is the main verification entry point. Handles all failure modes
    deterministically and returns structured result.

    DOCTRINE:
    - Fail-closed: Invalid signatures block execution
    - Unsigned PDOs: WARN but allow (legacy compatibility, TEMPORARY)
    - No exceptions: All failures return VerificationResult

    Args:
        pdo_data: PDO dictionary (must include 'signature' for signed PDOs)

    Returns:
        VerificationResult with outcome and details
    """
    pdo_id = None
    if pdo_data and isinstance(pdo_data, dict):
        pdo_id = pdo_data.get("pdo_id")
        if not isinstance(pdo_id, str):
            pdo_id = None

    # No PDO data at all
    if not pdo_data or not isinstance(pdo_data, dict):
        return VerificationResult(
            outcome=VerificationOutcome.UNSIGNED_PDO,
            pdo_id=pdo_id,
            reason="PDO data is missing or invalid",
        )

    # Extract signature envelope
    signature = extract_signature(pdo_data)

    # No signature → UNSIGNED_PDO (legacy, warn)
    if signature is None:
        logger.warning(
            "PDO without signature detected (legacy mode): pdo_id=%s",
            pdo_id,
        )
        return VerificationResult(
            outcome=VerificationOutcome.UNSIGNED_PDO,
            pdo_id=pdo_id,
            reason="PDO has no signature (legacy unsigned PDO)",
        )

    # Check algorithm support
    try:
        SignatureAlgorithm(signature.alg)
    except ValueError:
        return VerificationResult(
            outcome=VerificationOutcome.UNSUPPORTED_ALGORITHM,
            pdo_id=pdo_id,
            key_id=signature.key_id,
            algorithm=signature.alg,
            reason=f"Unsupported signature algorithm: {signature.alg}",
        )

    # Look up trusted key
    key_info = get_trusted_key(signature.key_id)
    if key_info is None:
        return VerificationResult(
            outcome=VerificationOutcome.UNKNOWN_KEY_ID,
            pdo_id=pdo_id,
            key_id=signature.key_id,
            algorithm=signature.alg,
            reason=f"Key ID not in trusted registry: {signature.key_id}",
        )

    registered_alg, verify_func = key_info

    # Algorithm mismatch (key registered for different algorithm)
    if registered_alg != signature.alg:
        return VerificationResult(
            outcome=VerificationOutcome.UNSUPPORTED_ALGORITHM,
            pdo_id=pdo_id,
            key_id=signature.key_id,
            algorithm=signature.alg,
            reason=f"Key {signature.key_id} registered for {registered_alg}, not {signature.alg}",
        )

    # Decode signature bytes
    try:
        sig_bytes = base64.b64decode(signature.sig)
    except Exception as e:
        return VerificationResult(
            outcome=VerificationOutcome.MALFORMED_SIGNATURE,
            pdo_id=pdo_id,
            key_id=signature.key_id,
            algorithm=signature.alg,
            reason=f"Cannot decode signature: {e}",
        )

    # Create canonical payload
    payload = canonicalize_pdo(pdo_data)

    # Verify signature
    try:
        is_valid = verify_func(payload, sig_bytes)
    except Exception as e:
        logger.exception("Signature verification error: %s", e)
        return VerificationResult(
            outcome=VerificationOutcome.INVALID_SIGNATURE,
            pdo_id=pdo_id,
            key_id=signature.key_id,
            algorithm=signature.alg,
            reason=f"Verification error: {e}",
        )

    if is_valid:
        return VerificationResult(
            outcome=VerificationOutcome.VALID,
            pdo_id=pdo_id,
            key_id=signature.key_id,
            algorithm=signature.alg,
            reason="Signature verified successfully",
        )
    else:
        return VerificationResult(
            outcome=VerificationOutcome.INVALID_SIGNATURE,
            pdo_id=pdo_id,
            key_id=signature.key_id,
            algorithm=signature.alg,
            reason="Signature does not match payload",
        )


# ---------------------------------------------------------------------------
# Audit Logging
# ---------------------------------------------------------------------------


def log_verification_result(result: VerificationResult, context: str = "") -> None:
    """Log signature verification result for audit trail.

    Args:
        result: Verification result to log
        context: Optional context string (e.g., "settlement_initiation")
    """
    log_data = {
        "event": "pdo_signature_verification",
        "pdo_id": result.pdo_id,
        "outcome": result.outcome.value,
        "key_id": result.key_id,
        "algorithm": result.algorithm,
        "reason": result.reason,
        "allows_execution": result.allows_execution,
        "context": context,
        "verified_at": result.verified_at,
    }

    if result.is_valid:
        logger.info("PDO signature verified: %s", json.dumps(log_data))
    elif result.is_unsigned:
        logger.warning("Unsigned PDO detected (legacy): %s", json.dumps(log_data))
    else:
        logger.error("PDO signature verification failed: %s", json.dumps(log_data))


# ---------------------------------------------------------------------------
# Test Utilities (for unit tests only)
# ---------------------------------------------------------------------------


def create_test_signature(pdo_data: dict[str, Any], key_id: str = "test-key-001") -> dict[str, str]:
    """Create a valid test signature for unit tests.

    WARNING: This function is for TESTING ONLY. Never use for production signing.

    Args:
        pdo_data: PDO data to sign
        key_id: Test key ID to use

    Returns:
        Signature envelope dict with alg, key_id, sig
    """
    _ensure_test_key_registered()

    payload = canonicalize_pdo(pdo_data)
    sig_bytes = hmac.new(_TEST_HMAC_KEY, payload, hashlib.sha256).digest()

    return {
        "alg": SignatureAlgorithm.HMAC_SHA256.value,
        "key_id": key_id,
        "sig": base64.b64encode(sig_bytes).decode("ascii"),
    }
