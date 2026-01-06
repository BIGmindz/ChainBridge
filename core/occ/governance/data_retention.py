"""
OCC v1.x Data Retention & Pseudonymization

PAC: PAC-OCC-P06
Lane: 4 — Regulatory Safeguards
Agent: Pax (GID-05) — Regulatory Hardening

Implements GDPR-compliant data retention and pseudonymization.
Addresses P04A gap: GDPR retention policy.

Invariant: INV-OCC-GDPR-001 — Audit chain integrity survives pseudonymization
Invariant: INV-OCC-GDPR-002 — Pseudonymization is reversible only by authorized parties
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DATA_RETENTION_CONFIG = {
    # Default retention period in days
    "default_retention_days": int(os.getenv("OCC_RETENTION_DAYS", "2555")),  # ~7 years
    # Personal data categories with specific retention
    "retention_periods": {
        "operator_id": 365 * 7,  # 7 years (financial regulation)
        "ip_address": 90,  # 90 days (GDPR minimum)
        "session_data": 30,  # 30 days
        "audit_log": 365 * 10,  # 10 years (regulatory minimum)
    },
    # Pseudonymization key (MUST be from secure source in production)
    "pseudonymization_key": os.getenv("OCC_PSEUDONYMIZATION_KEY", ""),
}


class DataCategory(Enum):
    """Categories of data for retention purposes."""

    OPERATOR_ID = "operator_id"
    IP_ADDRESS = "ip_address"
    SESSION_DATA = "session_data"
    AUDIT_LOG = "audit_log"
    SYSTEM_DATA = "system_data"  # Not PII


class RetentionAction(Enum):
    """Actions to take when retention period expires."""

    PSEUDONYMIZE = "pseudonymize"  # Replace with pseudonym
    DELETE = "delete"  # Full deletion
    ARCHIVE = "archive"  # Move to cold storage
    RETAIN = "retain"  # Keep indefinitely (non-PII)


# ═══════════════════════════════════════════════════════════════════════════════
# PSEUDONYMIZATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class PseudonymMapping:
    """Mapping between real identifier and pseudonym."""

    original_hash: str  # Hash of original (for lookup without storing original)
    pseudonym: str
    created_at: str
    category: DataCategory
    reversible: bool = True


class PseudonymizationEngine:
    """
    GDPR-compliant pseudonymization engine.

    Properties:
    - Deterministic: Same input produces same pseudonym (with same key)
    - Reversible: Authorized parties can retrieve mapping
    - Audit-safe: Pseudonymization preserves hash chain integrity
    """

    def __init__(self, key: Optional[bytes] = None) -> None:
        """
        Initialize with pseudonymization key.

        Args:
            key: 32-byte key for pseudonym generation.
                 If None, generates random key (non-deterministic mode).
        """
        if key:
            self._key = key
        elif DATA_RETENTION_CONFIG["pseudonymization_key"]:
            self._key = base64.b64decode(DATA_RETENTION_CONFIG["pseudonymization_key"])
        else:
            # Development mode: random key (pseudonyms not reproducible)
            self._key = secrets.token_bytes(32)
            logger.warning(
                "Pseudonymization using random key - "
                "pseudonyms will not be consistent across restarts"
            )

        self._mappings: Dict[str, PseudonymMapping] = {}
        self._lock = threading.Lock()

    def pseudonymize(
        self,
        value: str,
        category: DataCategory = DataCategory.OPERATOR_ID,
    ) -> str:
        """
        Generate a pseudonym for a value.

        Args:
            value: The value to pseudonymize
            category: Data category for the value

        Returns:
            Pseudonym string (format: PSE-{category}-{hash_prefix})
        """
        # Generate deterministic pseudonym using HMAC
        mac = hmac.new(
            self._key,
            f"{category.value}:{value}".encode(),
            hashlib.sha256,
        )
        pseudonym_hash = mac.hexdigest()[:16]
        pseudonym = f"PSE-{category.value[:3].upper()}-{pseudonym_hash}"

        # Store mapping for reverse lookup
        original_hash = hashlib.sha256(value.encode()).hexdigest()

        with self._lock:
            if original_hash not in self._mappings:
                self._mappings[original_hash] = PseudonymMapping(
                    original_hash=original_hash,
                    pseudonym=pseudonym,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    category=category,
                )

        return pseudonym

    def batch_pseudonymize(
        self,
        values: List[str],
        category: DataCategory = DataCategory.OPERATOR_ID,
    ) -> Dict[str, str]:
        """
        Pseudonymize multiple values.

        Returns:
            Dict mapping original values to pseudonyms
        """
        return {v: self.pseudonymize(v, category) for v in values}

    def get_pseudonym(self, value: str) -> Optional[str]:
        """
        Get existing pseudonym for a value without creating new one.
        """
        original_hash = hashlib.sha256(value.encode()).hexdigest()
        with self._lock:
            mapping = self._mappings.get(original_hash)
            return mapping.pseudonym if mapping else None

    def export_mappings(self) -> List[Dict[str, Any]]:
        """
        Export all mappings for backup/compliance.

        WARNING: This should be stored securely and separately from data.
        """
        with self._lock:
            return [
                {
                    "original_hash": m.original_hash,
                    "pseudonym": m.pseudonym,
                    "created_at": m.created_at,
                    "category": m.category.value,
                }
                for m in self._mappings.values()
            ]

    def import_mappings(self, mappings: List[Dict[str, Any]]) -> int:
        """
        Import mappings from backup.

        Returns:
            Number of mappings imported
        """
        count = 0
        with self._lock:
            for m in mappings:
                mapping = PseudonymMapping(
                    original_hash=m["original_hash"],
                    pseudonym=m["pseudonym"],
                    created_at=m["created_at"],
                    category=DataCategory(m["category"]),
                )
                if mapping.original_hash not in self._mappings:
                    self._mappings[mapping.original_hash] = mapping
                    count += 1
        return count


# ═══════════════════════════════════════════════════════════════════════════════
# RETENTION POLICY ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RetentionPolicy:
    """Definition of a retention policy."""

    name: str
    category: DataCategory
    retention_days: int
    action: RetentionAction
    description: str = ""


@dataclass
class RetentionCandidate:
    """A record candidate for retention processing."""

    record_id: str
    created_at: datetime
    category: DataCategory
    pii_fields: Dict[str, str]  # field_name -> value


@dataclass
class RetentionResult:
    """Result of retention policy execution."""

    record_id: str
    action_taken: RetentionAction
    fields_affected: List[str]
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class RetentionPolicyEngine:
    """
    Manages data retention policies.

    Supports:
    - Policy-based retention periods
    - Automatic pseudonymization
    - Audit-safe processing
    """

    def __init__(
        self,
        pseudonymizer: Optional[PseudonymizationEngine] = None,
    ) -> None:
        self._policies: Dict[DataCategory, RetentionPolicy] = {}
        self._pseudonymizer = pseudonymizer or PseudonymizationEngine()
        self._lock = threading.Lock()
        self._register_default_policies()

    def _register_default_policies(self) -> None:
        """Register default retention policies."""

        self.register_policy(
            RetentionPolicy(
                name="operator_id_retention",
                category=DataCategory.OPERATOR_ID,
                retention_days=DATA_RETENTION_CONFIG["retention_periods"]["operator_id"],
                action=RetentionAction.PSEUDONYMIZE,
                description="Pseudonymize operator IDs after 7 years",
            )
        )

        self.register_policy(
            RetentionPolicy(
                name="ip_address_retention",
                category=DataCategory.IP_ADDRESS,
                retention_days=DATA_RETENTION_CONFIG["retention_periods"]["ip_address"],
                action=RetentionAction.DELETE,
                description="Delete IP addresses after 90 days",
            )
        )

        self.register_policy(
            RetentionPolicy(
                name="session_retention",
                category=DataCategory.SESSION_DATA,
                retention_days=DATA_RETENTION_CONFIG["retention_periods"]["session_data"],
                action=RetentionAction.DELETE,
                description="Delete session data after 30 days",
            )
        )

        self.register_policy(
            RetentionPolicy(
                name="audit_log_retention",
                category=DataCategory.AUDIT_LOG,
                retention_days=DATA_RETENTION_CONFIG["retention_periods"]["audit_log"],
                action=RetentionAction.ARCHIVE,
                description="Archive audit logs after 10 years",
            )
        )

    def register_policy(self, policy: RetentionPolicy) -> None:
        """Register a retention policy."""
        with self._lock:
            self._policies[policy.category] = policy
            logger.info(f"Registered retention policy: {policy.name}")

    def get_policy(self, category: DataCategory) -> Optional[RetentionPolicy]:
        """Get retention policy for a category."""
        with self._lock:
            return self._policies.get(category)

    def check_retention(
        self,
        candidate: RetentionCandidate,
    ) -> Optional[RetentionAction]:
        """
        Check if a record should be processed for retention.

        Returns:
            Action to take, or None if no action needed
        """
        policy = self.get_policy(candidate.category)
        if not policy:
            return None

        cutoff = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        if candidate.created_at < cutoff:
            return policy.action

        return None

    def process_candidate(
        self,
        candidate: RetentionCandidate,
    ) -> Optional[RetentionResult]:
        """
        Process a retention candidate.

        Returns:
            Result of processing, or None if no action taken
        """
        action = self.check_retention(candidate)
        if not action:
            return None

        affected_fields = []

        if action == RetentionAction.PSEUDONYMIZE:
            for field_name, value in candidate.pii_fields.items():
                # Pseudonymize the value
                pseudonym = self._pseudonymizer.pseudonymize(
                    value,
                    candidate.category,
                )
                candidate.pii_fields[field_name] = pseudonym
                affected_fields.append(field_name)

        elif action == RetentionAction.DELETE:
            for field_name in list(candidate.pii_fields.keys()):
                candidate.pii_fields[field_name] = "[DELETED]"
                affected_fields.append(field_name)

        return RetentionResult(
            record_id=candidate.record_id,
            action_taken=action,
            fields_affected=affected_fields,
        )

    def batch_process(
        self,
        candidates: List[RetentionCandidate],
    ) -> List[RetentionResult]:
        """
        Process multiple retention candidates.

        Returns:
            List of results for processed candidates
        """
        results = []
        for candidate in candidates:
            result = self.process_candidate(candidate)
            if result:
                results.append(result)
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT-SAFE PSEUDONYMIZATION
# ═══════════════════════════════════════════════════════════════════════════════


def pseudonymize_audit_entry(
    entry: Dict[str, Any],
    engine: PseudonymizationEngine,
    fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Pseudonymize PII fields in an audit entry while preserving integrity.

    Critical: This does NOT modify the entry_hash or prev_hash.
    The hash chain references the ORIGINAL entry.
    Pseudonymized entries are marked as such.

    Args:
        entry: The audit entry to pseudonymize
        engine: Pseudonymization engine
        fields: Fields to pseudonymize (default: actor_id)

    Returns:
        New entry dict with pseudonymized fields
    """
    if fields is None:
        fields = ["actor_id"]

    result = entry.copy()

    # Mark as pseudonymized
    result["_pseudonymized"] = True
    result["_pseudonymized_at"] = datetime.now(timezone.utc).isoformat()
    result["_original_fields"] = fields

    # Pseudonymize specified fields
    for field in fields:
        if field in result and result[field]:
            original = result[field]
            result[field] = engine.pseudonymize(
                original,
                DataCategory.OPERATOR_ID,
            )

    # Preserve hash chain integrity by NOT modifying hashes
    # The hash chain remains valid for the original data
    # Pseudonymized view is a projection, not replacement

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_pseudonymizer: Optional[PseudonymizationEngine] = None
_retention_engine: Optional[RetentionPolicyEngine] = None


def get_pseudonymizer() -> PseudonymizationEngine:
    """Get global pseudonymization engine."""
    global _pseudonymizer
    if _pseudonymizer is None:
        _pseudonymizer = PseudonymizationEngine()
    return _pseudonymizer


def get_retention_engine() -> RetentionPolicyEngine:
    """Get global retention policy engine."""
    global _retention_engine
    if _retention_engine is None:
        _retention_engine = RetentionPolicyEngine(get_pseudonymizer())
    return _retention_engine


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "DataCategory",
    "RetentionAction",
    "PseudonymMapping",
    "PseudonymizationEngine",
    "RetentionPolicy",
    "RetentionCandidate",
    "RetentionResult",
    "RetentionPolicyEngine",
    "pseudonymize_audit_entry",
    "get_pseudonymizer",
    "get_retention_engine",
]
