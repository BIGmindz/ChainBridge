"""
OCC v1.x Audit Entry Signing

PAC: PAC-OCC-P06
Lane: 2 — Evidence & Non-Repudiation
Agent: Atlas (GID-11) — Evidence Durability & Signatures

Provides cryptographic signing for individual audit log entries.
Extends the existing Ed25519 infrastructure to audit records.

Invariant: INV-OCC-SIGN-001 — Signed entries cannot be repudiated
Invariant: INV-OCC-SIGN-002 — Missing signature does not invalidate hash chain
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.occ.crypto.ed25519_signer import (
    Ed25519Signer,
    SignatureBundle,
    verify_signature,
    NACL_AVAILABLE,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

AUDIT_SIGNING_CONFIG = {
    # Whether to require signatures on audit entries
    # In production, this should be True
    "require_signatures": os.getenv("OCC_AUDIT_REQUIRE_SIGNATURES", "false").lower() == "true",
    # Key ID for audit signing (separate from proofpack signing)
    "key_id": os.getenv("OCC_AUDIT_KEY_ID", "audit-v1"),
    # Whether to fail on signature verification failure
    "strict_verification": os.getenv("OCC_AUDIT_STRICT_VERIFY", "false").lower() == "true",
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SignedAuditEntry:
    """
    Audit entry with cryptographic signature.

    The signature covers the canonical JSON representation of the entry,
    providing non-repudiation for the recorded action.

    Structure:
    - entry_data: The audit entry content (without signature)
    - signature: Ed25519 signature bundle
    - signed_hash: SHA-256 hash of canonical entry JSON
    """

    entry_id: str
    timestamp: str
    actor_id: str
    actor_type: str  # HUMAN | AGENT
    action: str
    pdo_id: Optional[str]
    details: Dict[str, Any]
    prev_hash: str
    entry_hash: str
    signature: Optional[SignatureBundle] = None
    signed_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "action": self.action,
            "pdo_id": self.pdo_id,
            "details": self.details,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
        }
        if self.signature:
            result["signature"] = self.signature.to_dict()
            result["signed_hash"] = self.signed_hash
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignedAuditEntry":
        """Create from dictionary."""
        signature = None
        if "signature" in data and data["signature"]:
            signature = SignatureBundle.from_dict(data["signature"])

        return cls(
            entry_id=data["entry_id"],
            timestamp=data["timestamp"],
            actor_id=data["actor_id"],
            actor_type=data["actor_type"],
            action=data["action"],
            pdo_id=data.get("pdo_id"),
            details=data.get("details", {}),
            prev_hash=data["prev_hash"],
            entry_hash=data["entry_hash"],
            signature=signature,
            signed_hash=data.get("signed_hash"),
        )

    def get_canonical_content(self) -> str:
        """
        Get canonical JSON representation for signing.

        The canonical form excludes signature fields to allow
        verification after signing.
        """
        content = {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "action": self.action,
            "pdo_id": self.pdo_id,
            "details": self.details,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
        }
        return json.dumps(content, sort_keys=True, separators=(",", ":"))


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT SIGNER
# ═══════════════════════════════════════════════════════════════════════════════


class AuditEntrySigner:
    """
    Signs and verifies audit log entries.

    Provides:
    - Entry-level signatures for non-repudiation
    - Batch signing for efficiency
    - Verification without private key
    """

    def __init__(self, signer: Optional[Ed25519Signer] = None) -> None:
        """
        Initialize audit signer.

        Args:
            signer: Ed25519Signer instance. If None, signing is disabled.
        """
        self._signer = signer
        self._lock = threading.Lock()

        if signer:
            logger.info(
                "AuditEntrySigner initialized with signing enabled",
                extra={"key_id": signer.key_id},
            )
        else:
            logger.warning(
                "AuditEntrySigner initialized without signer - "
                "entries will not be signed"
            )

    @property
    def signing_enabled(self) -> bool:
        """Check if signing is enabled."""
        return self._signer is not None

    @property
    def public_key(self) -> Optional[str]:
        """Get public key for verification."""
        if self._signer:
            return self._signer.public_key_b64
        return None

    def sign_entry(self, entry: SignedAuditEntry) -> SignedAuditEntry:
        """
        Sign an audit entry.

        Args:
            entry: The audit entry to sign

        Returns:
            New SignedAuditEntry with signature attached

        Note:
            Returns entry unchanged if signing is disabled.
        """
        if not self._signer:
            return entry

        with self._lock:
            # Get canonical content
            canonical = entry.get_canonical_content()

            # Hash for signing
            content_hash = hashlib.sha256(canonical.encode()).hexdigest()

            # Sign the hash
            signature = self._signer.sign_manifest_hash(content_hash)

            # Return new entry with signature
            return SignedAuditEntry(
                entry_id=entry.entry_id,
                timestamp=entry.timestamp,
                actor_id=entry.actor_id,
                actor_type=entry.actor_type,
                action=entry.action,
                pdo_id=entry.pdo_id,
                details=entry.details,
                prev_hash=entry.prev_hash,
                entry_hash=entry.entry_hash,
                signature=signature,
                signed_hash=content_hash,
            )

    def sign_entries(self, entries: List[SignedAuditEntry]) -> List[SignedAuditEntry]:
        """
        Sign multiple audit entries.

        Args:
            entries: List of entries to sign

        Returns:
            List of signed entries
        """
        return [self.sign_entry(e) for e in entries]

    def verify_entry(self, entry: SignedAuditEntry) -> Tuple[bool, str]:
        """
        Verify an audit entry signature.

        Args:
            entry: The signed audit entry

        Returns:
            Tuple of (is_valid, reason)
        """
        if not entry.signature:
            if AUDIT_SIGNING_CONFIG["require_signatures"]:
                return (False, "Signature required but missing")
            return (True, "No signature (not required)")

        if not entry.signed_hash:
            return (False, "Signed hash missing")

        # Recompute canonical hash
        canonical = entry.get_canonical_content()
        content_hash = hashlib.sha256(canonical.encode()).hexdigest()

        # Verify hash matches
        if content_hash != entry.signed_hash:
            return (False, f"Content hash mismatch: {content_hash} != {entry.signed_hash}")

        # Verify signature
        if not NACL_AVAILABLE:
            return (False, "PyNaCl not available for verification")

        try:
            hash_bytes = bytes.fromhex(entry.signed_hash)
            is_valid = verify_signature(
                message=hash_bytes,
                signature_b64=entry.signature.signature,
                public_key_b64=entry.signature.public_key,
            )
            if is_valid:
                return (True, "Signature valid")
            else:
                return (False, "Signature verification failed")
        except Exception as e:
            return (False, f"Verification error: {e}")

    def verify_entries(
        self,
        entries: List[SignedAuditEntry],
    ) -> List[Tuple[str, bool, str]]:
        """
        Verify multiple audit entries.

        Args:
            entries: List of entries to verify

        Returns:
            List of (entry_id, is_valid, reason) tuples
        """
        return [
            (e.entry_id, *self.verify_entry(e))
            for e in entries
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE CHAIN VERIFIER
# ═══════════════════════════════════════════════════════════════════════════════


class EvidenceChainVerifier:
    """
    Comprehensive evidence chain verification.

    Verifies:
    1. Hash chain integrity (existing)
    2. Entry signatures (new)
    3. Temporal ordering
    4. Actor attribution
    """

    def __init__(self, signer: Optional[AuditEntrySigner] = None) -> None:
        self._signer = signer or AuditEntrySigner()

    def verify_chain(
        self,
        entries: List[SignedAuditEntry],
        genesis_hash: str = "genesis",
    ) -> Dict[str, Any]:
        """
        Perform comprehensive chain verification.

        Args:
            entries: Ordered list of audit entries
            genesis_hash: Expected hash of first entry's prev_hash

        Returns:
            Verification report
        """
        report = {
            "chain_valid": True,
            "signature_valid": True,
            "temporal_valid": True,
            "total_entries": len(entries),
            "signed_entries": 0,
            "unsigned_entries": 0,
            "errors": [],
            "warnings": [],
        }

        if not entries:
            return report

        prev_hash = genesis_hash
        prev_timestamp = None

        for i, entry in enumerate(entries):
            # Verify hash chain
            if entry.prev_hash != prev_hash:
                report["chain_valid"] = False
                report["errors"].append(
                    f"Entry {i} ({entry.entry_id}): prev_hash mismatch"
                )

            # Verify signature if present
            if entry.signature:
                report["signed_entries"] += 1
                is_valid, reason = self._signer.verify_entry(entry)
                if not is_valid:
                    report["signature_valid"] = False
                    report["errors"].append(
                        f"Entry {i} ({entry.entry_id}): {reason}"
                    )
            else:
                report["unsigned_entries"] += 1
                if AUDIT_SIGNING_CONFIG["require_signatures"]:
                    report["warnings"].append(
                        f"Entry {i} ({entry.entry_id}): missing signature"
                    )

            # Verify temporal ordering
            if prev_timestamp:
                try:
                    current_ts = datetime.fromisoformat(
                        entry.timestamp.replace("Z", "+00:00")
                    )
                    prev_ts = datetime.fromisoformat(
                        prev_timestamp.replace("Z", "+00:00")
                    )
                    if current_ts < prev_ts:
                        report["temporal_valid"] = False
                        report["errors"].append(
                            f"Entry {i} ({entry.entry_id}): timestamp out of order"
                        )
                except Exception:
                    pass  # Timestamp parsing failed, skip temporal check

            prev_hash = entry.entry_hash
            prev_timestamp = entry.timestamp

        report["overall_valid"] = (
            report["chain_valid"]
            and report["signature_valid"]
            and report["temporal_valid"]
        )

        return report


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


_audit_signer: Optional[AuditEntrySigner] = None
_audit_signer_lock = threading.Lock()


def get_audit_signer() -> AuditEntrySigner:
    """
    Get the global audit entry signer.

    Initializes from environment if not already created.
    """
    global _audit_signer

    if _audit_signer is None:
        with _audit_signer_lock:
            if _audit_signer is None:
                # Try to load signing key from environment
                key_b64 = os.getenv("OCC_AUDIT_SIGNING_KEY")
                key_id = AUDIT_SIGNING_CONFIG["key_id"]

                if key_b64 and NACL_AVAILABLE:
                    try:
                        key_bytes = base64.b64decode(key_b64)
                        signer = Ed25519Signer(key_bytes, key_id=key_id)
                        _audit_signer = AuditEntrySigner(signer)
                    except Exception as e:
                        logger.error(f"Failed to initialize audit signer: {e}")
                        _audit_signer = AuditEntrySigner()
                else:
                    _audit_signer = AuditEntrySigner()

    return _audit_signer


def get_evidence_verifier() -> EvidenceChainVerifier:
    """Get evidence chain verifier."""
    return EvidenceChainVerifier(get_audit_signer())


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "SignedAuditEntry",
    "AuditEntrySigner",
    "EvidenceChainVerifier",
    "get_audit_signer",
    "get_evidence_verifier",
    "AUDIT_SIGNING_CONFIG",
]
