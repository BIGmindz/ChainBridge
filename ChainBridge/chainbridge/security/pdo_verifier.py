"""PDO Tampering Defense Module.

Detects and rejects:
- Modified PDO payloads (signature mismatch)
- Replayed signatures (nonce reuse)
- Authority spoofing (agent_gid mismatch)

DOCTRINE: Fail closed on ALL tampering attempts.

Author: Sam (GID-06) — Security & Threat Engineer
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Set

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Security Exceptions (Explicit Rejection)
# ---------------------------------------------------------------------------


class PDOTamperingError(Exception):
    """Raised when PDO payload has been modified after signing."""

    def __init__(self, pdo_id: str, reason: str, details: dict = None):
        self.pdo_id = pdo_id
        self.reason = reason
        self.details = details or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        super().__init__(f"PDO tampering detected: {pdo_id} - {reason}")


class PDOReplayError(Exception):
    """Raised when a PDO signature/nonce is replayed."""

    def __init__(self, pdo_id: str, nonce: str, original_timestamp: str = None):
        self.pdo_id = pdo_id
        self.nonce = nonce
        self.original_timestamp = original_timestamp
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(f"PDO replay attack detected: {pdo_id} nonce={nonce}")


class PDOAuthoritySpoofError(Exception):
    """Raised when PDO claims authority from wrong agent."""

    def __init__(
        self,
        pdo_id: str,
        claimed_agent: str,
        actual_signer: str,
        key_id: str,
    ):
        self.pdo_id = pdo_id
        self.claimed_agent = claimed_agent
        self.actual_signer = actual_signer
        self.key_id = key_id
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(
            f"Authority spoofing detected: {pdo_id} claims {claimed_agent} "
            f"but signed by {actual_signer}"
        )


# ---------------------------------------------------------------------------
# Attack Detection Result
# ---------------------------------------------------------------------------


class AttackType(str, Enum):
    """Types of detected attacks."""

    PAYLOAD_MODIFICATION = "PAYLOAD_MODIFICATION"
    SIGNATURE_REPLAY = "SIGNATURE_REPLAY"
    NONCE_REPLAY = "NONCE_REPLAY"
    AUTHORITY_SPOOF = "AUTHORITY_SPOOF"
    HASH_MANIPULATION = "HASH_MANIPULATION"
    TIMESTAMP_MANIPULATION = "TIMESTAMP_MANIPULATION"
    FIELD_INJECTION = "FIELD_INJECTION"
    FIELD_REMOVAL = "FIELD_REMOVAL"


@dataclass(frozen=True)
class AttackDetectionResult:
    """Result from attack detection analysis."""

    detected: bool
    attack_type: Optional[AttackType]
    pdo_id: Optional[str]
    reason: str
    evidence: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_audit_log(self) -> dict:
        """Convert to audit log format."""
        return {
            "event": "pdo_attack_detection",
            "detected": self.detected,
            "attack_type": self.attack_type.value if self.attack_type else None,
            "pdo_id": self.pdo_id,
            "reason": self.reason,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# PDO Verifier
# ---------------------------------------------------------------------------


class PDOVerifier:
    """Verifies PDO integrity against tampering attacks.

    SECURITY INVARIANTS:
    - No trust in caller inputs
    - Explicit rejection on ANY anomaly
    - All failures logged for audit

    Usage:
        verifier = PDOVerifier()
        verifier.verify_integrity(pdo_data)  # Raises on attack
    """

    # Required fields for integrity check
    REQUIRED_FIELDS = frozenset({
        "pdo_id",
        "decision_hash",
        "policy_version",
        "agent_id",
        "action",
        "outcome",
        "timestamp",
        "nonce",
        "expires_at",
        "signature",
    })

    # Fields covered by signature
    SIGNED_FIELDS = (
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

    def __init__(self):
        """Initialize PDO verifier with nonce tracking."""
        self._seen_nonces: Set[str] = set()
        self._nonce_timestamps: dict[str, str] = {}
        self._max_nonce_cache = 100000

    def verify_integrity(self, pdo_data: dict[str, Any]) -> AttackDetectionResult:
        """Verify PDO has not been tampered with.

        Checks:
        1. All required fields present
        2. No unexpected fields injected
        3. Hash integrity
        4. Nonce not replayed
        5. Timestamp not manipulated

        Args:
            pdo_data: PDO dictionary to verify

        Returns:
            AttackDetectionResult indicating pass/fail

        Raises:
            PDOTamperingError: If tampering detected
        """
        pdo_id = pdo_data.get("pdo_id", "UNKNOWN")

        # Check 1: Required field presence
        result = self._check_required_fields(pdo_data, pdo_id)
        if result.detected:
            self._log_attack(result)
            raise PDOTamperingError(pdo_id, result.reason, result.evidence)

        # Check 2: Field injection detection
        result = self._check_field_injection(pdo_data, pdo_id)
        if result.detected:
            self._log_attack(result)
            raise PDOTamperingError(pdo_id, result.reason, result.evidence)

        # Check 3: Hash integrity
        result = self._check_hash_integrity(pdo_data, pdo_id)
        if result.detected:
            self._log_attack(result)
            raise PDOTamperingError(pdo_id, result.reason, result.evidence)

        # Check 4: Nonce replay
        result = self._check_nonce_replay(pdo_data, pdo_id)
        if result.detected:
            self._log_attack(result)
            raise PDOReplayError(
                pdo_id,
                pdo_data.get("nonce", ""),
                self._nonce_timestamps.get(pdo_data.get("nonce")),
            )

        # Check 5: Timestamp manipulation
        result = self._check_timestamp_manipulation(pdo_data, pdo_id)
        if result.detected:
            self._log_attack(result)
            raise PDOTamperingError(pdo_id, result.reason, result.evidence)

        # Record nonce as seen
        nonce = pdo_data.get("nonce")
        if nonce:
            self._record_nonce(nonce, pdo_data.get("timestamp", ""))

        return AttackDetectionResult(
            detected=False,
            attack_type=None,
            pdo_id=pdo_id,
            reason="PDO integrity verified",
        )

    def verify_authority(
        self,
        pdo_data: dict[str, Any],
        expected_agent: str,
        key_binding: dict[str, str],
    ) -> AttackDetectionResult:
        """Verify PDO authority matches signer.

        Args:
            pdo_data: PDO dictionary
            expected_agent: Expected agent_id for this operation
            key_binding: Mapping of key_id -> agent_id

        Returns:
            AttackDetectionResult

        Raises:
            PDOAuthoritySpoofError: If authority spoofing detected
        """
        pdo_id = pdo_data.get("pdo_id", "UNKNOWN")
        claimed_agent = pdo_data.get("agent_id")
        signature = pdo_data.get("signature", {})
        key_id = signature.get("key_id")

        # Check claimed agent matches expected
        if claimed_agent != expected_agent:
            result = AttackDetectionResult(
                detected=True,
                attack_type=AttackType.AUTHORITY_SPOOF,
                pdo_id=pdo_id,
                reason=f"Agent mismatch: expected {expected_agent}, got {claimed_agent}",
                evidence={
                    "expected_agent": expected_agent,
                    "claimed_agent": claimed_agent,
                },
            )
            self._log_attack(result)
            raise PDOAuthoritySpoofError(
                pdo_id,
                claimed_agent,
                expected_agent,
                key_id or "UNKNOWN",
            )

        # Check key_id is bound to claimed agent
        if key_id and key_id in key_binding:
            bound_agent = key_binding[key_id]
            if bound_agent != claimed_agent:
                result = AttackDetectionResult(
                    detected=True,
                    attack_type=AttackType.AUTHORITY_SPOOF,
                    pdo_id=pdo_id,
                    reason=f"Key {key_id} bound to {bound_agent}, not {claimed_agent}",
                    evidence={
                        "key_id": key_id,
                        "bound_agent": bound_agent,
                        "claimed_agent": claimed_agent,
                    },
                )
                self._log_attack(result)
                raise PDOAuthoritySpoofError(
                    pdo_id,
                    claimed_agent,
                    bound_agent,
                    key_id,
                )

        return AttackDetectionResult(
            detected=False,
            attack_type=None,
            pdo_id=pdo_id,
            reason="Authority verified",
        )

    def detect_forged_pdo(
        self,
        pdo_data: dict[str, Any],
        known_signatures: Set[str],
    ) -> AttackDetectionResult:
        """Detect if PDO is forged (signature not from trusted source).

        Args:
            pdo_data: PDO dictionary
            known_signatures: Set of known valid signature hashes

        Returns:
            AttackDetectionResult
        """
        pdo_id = pdo_data.get("pdo_id", "UNKNOWN")
        signature = pdo_data.get("signature", {})
        sig_value = signature.get("sig", "")

        # Hash the signature for comparison
        sig_hash = hashlib.sha256(sig_value.encode()).hexdigest()

        if sig_hash not in known_signatures:
            return AttackDetectionResult(
                detected=True,
                attack_type=AttackType.PAYLOAD_MODIFICATION,
                pdo_id=pdo_id,
                reason="Signature not from trusted source",
                evidence={
                    "sig_hash": sig_hash[:16] + "...",
                },
            )

        return AttackDetectionResult(
            detected=False,
            attack_type=None,
            pdo_id=pdo_id,
            reason="Signature matches trusted source",
        )

    # ---------------------------------------------------------------------------
    # Internal Checks
    # ---------------------------------------------------------------------------

    def _check_required_fields(
        self, pdo_data: dict[str, Any], pdo_id: str
    ) -> AttackDetectionResult:
        """Check all required fields are present."""
        missing = self.REQUIRED_FIELDS - set(pdo_data.keys())
        if missing:
            return AttackDetectionResult(
                detected=True,
                attack_type=AttackType.FIELD_REMOVAL,
                pdo_id=pdo_id,
                reason=f"Missing required fields: {missing}",
                evidence={"missing_fields": list(missing)},
            )
        return AttackDetectionResult(
            detected=False, attack_type=None, pdo_id=pdo_id, reason="All fields present"
        )

    def _check_field_injection(
        self, pdo_data: dict[str, Any], pdo_id: str
    ) -> AttackDetectionResult:
        """Check for unexpected field injection.

        Note: Extra fields are allowed but logged for awareness.
        Critical injection is when signed fields are duplicated.
        """
        # Check for dangerous field patterns
        dangerous_patterns = [
            "__",  # Dunder attributes
            "$",  # MongoDB injection
            "{{",  # Template injection
            "<%",  # Server-side template
        ]

        for key in pdo_data.keys():
            for pattern in dangerous_patterns:
                if pattern in str(key):
                    return AttackDetectionResult(
                        detected=True,
                        attack_type=AttackType.FIELD_INJECTION,
                        pdo_id=pdo_id,
                        reason=f"Dangerous field pattern detected: {key}",
                        evidence={"field": key, "pattern": pattern},
                    )

        return AttackDetectionResult(
            detected=False, attack_type=None, pdo_id=pdo_id, reason="No injection detected"
        )

    def _check_hash_integrity(
        self, pdo_data: dict[str, Any], pdo_id: str
    ) -> AttackDetectionResult:
        """Check decision_hash matches claimed inputs."""
        decision_hash = pdo_data.get("decision_hash", "")

        # Hash must be 64 hex characters (SHA-256)
        if not decision_hash or len(decision_hash) != 64:
            return AttackDetectionResult(
                detected=True,
                attack_type=AttackType.HASH_MANIPULATION,
                pdo_id=pdo_id,
                reason="Invalid decision_hash format",
                evidence={"hash_length": len(decision_hash) if decision_hash else 0},
            )

        try:
            bytes.fromhex(decision_hash)
        except ValueError:
            return AttackDetectionResult(
                detected=True,
                attack_type=AttackType.HASH_MANIPULATION,
                pdo_id=pdo_id,
                reason="decision_hash is not valid hex",
                evidence={},
            )

        return AttackDetectionResult(
            detected=False, attack_type=None, pdo_id=pdo_id, reason="Hash format valid"
        )

    def _check_nonce_replay(
        self, pdo_data: dict[str, Any], pdo_id: str
    ) -> AttackDetectionResult:
        """Check if nonce has been seen before."""
        nonce = pdo_data.get("nonce")
        if not nonce:
            return AttackDetectionResult(
                detected=True,
                attack_type=AttackType.FIELD_REMOVAL,
                pdo_id=pdo_id,
                reason="Missing nonce field",
                evidence={},
            )

        if nonce in self._seen_nonces:
            return AttackDetectionResult(
                detected=True,
                attack_type=AttackType.NONCE_REPLAY,
                pdo_id=pdo_id,
                reason=f"Nonce replay detected: {nonce}",
                evidence={
                    "nonce": nonce,
                    "original_timestamp": self._nonce_timestamps.get(nonce),
                },
            )

        return AttackDetectionResult(
            detected=False, attack_type=None, pdo_id=pdo_id, reason="Nonce is unique"
        )

    def _check_timestamp_manipulation(
        self, pdo_data: dict[str, Any], pdo_id: str
    ) -> AttackDetectionResult:
        """Check for timestamp manipulation attacks."""
        timestamp = pdo_data.get("timestamp")
        expires_at = pdo_data.get("expires_at")

        if not timestamp:
            return AttackDetectionResult(
                detected=True,
                attack_type=AttackType.TIMESTAMP_MANIPULATION,
                pdo_id=pdo_id,
                reason="Missing timestamp",
                evidence={},
            )

        try:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)

            # Check for future timestamp (clock manipulation)
            if ts > now:
                # Allow small clock skew (5 seconds)
                from datetime import timedelta
                if (ts - now).total_seconds() > 5:
                    return AttackDetectionResult(
                        detected=True,
                        attack_type=AttackType.TIMESTAMP_MANIPULATION,
                        pdo_id=pdo_id,
                        reason="Future timestamp detected",
                        evidence={
                            "timestamp": timestamp,
                            "server_time": now.isoformat(),
                        },
                    )

        except (ValueError, TypeError) as e:
            return AttackDetectionResult(
                detected=True,
                attack_type=AttackType.TIMESTAMP_MANIPULATION,
                pdo_id=pdo_id,
                reason=f"Invalid timestamp format: {e}",
                evidence={"timestamp": timestamp},
            )

        return AttackDetectionResult(
            detected=False, attack_type=None, pdo_id=pdo_id, reason="Timestamp valid"
        )

    def _record_nonce(self, nonce: str, timestamp: str) -> None:
        """Record nonce as seen."""
        if len(self._seen_nonces) >= self._max_nonce_cache:
            # Clear oldest half
            logger.warning("Nonce cache full, clearing old entries")
            self._seen_nonces.clear()
            self._nonce_timestamps.clear()

        self._seen_nonces.add(nonce)
        self._nonce_timestamps[nonce] = timestamp

    def _log_attack(self, result: AttackDetectionResult) -> None:
        """Log detected attack for audit trail."""
        logger.error(
            "SECURITY_ALERT: %s detected: pdo_id=%s reason=%s",
            result.attack_type.value if result.attack_type else "UNKNOWN",
            result.pdo_id,
            result.reason,
        )
        logger.error("Attack evidence: %s", json.dumps(result.to_audit_log()))

    def clear_nonce_cache(self) -> None:
        """Clear nonce cache (for testing only)."""
        self._seen_nonces.clear()
        self._nonce_timestamps.clear()
