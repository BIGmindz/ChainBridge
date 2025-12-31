"""
PDO Retention Policy Engine

Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-REAL-WORK-SIX-AGENT-029.
Agent: GID-07 (Dan) — Data / Storage

REAL WORK MODE — Production-grade PDO retention policies.

Features:
- Time-based retention policies (TTL)
- Policy-based pruning with configurable rules
- Hash-preserving compaction (keeps hashes, removes payloads)
- Audit trail preservation
- Tiered storage support
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class RetentionTier(Enum):
    """Storage tiers for PDO lifecycle."""
    HOT = "HOT"          # Active, full access, full data
    WARM = "WARM"        # Reduced access, full data
    COLD = "COLD"        # Archived, hash-only, payload removed
    FROZEN = "FROZEN"    # Deep archive, hash + minimal metadata
    DELETED = "DELETED"  # Marked for deletion, hash preserved in tombstone


class RetentionAction(Enum):
    """Actions that can be taken on PDOs."""
    RETAIN = "RETAIN"        # Keep in current tier
    DEMOTE = "DEMOTE"        # Move to colder tier
    COMPACT = "COMPACT"      # Remove payload, keep hash
    ARCHIVE = "ARCHIVE"      # Move to archive storage
    DELETE = "DELETE"        # Mark for deletion
    PURGE = "PURGE"          # Complete removal (compliance only)


class PolicyPriority(Enum):
    """Policy evaluation priority."""
    CRITICAL = 0    # Compliance/legal holds
    HIGH = 10       # Business-critical retention
    NORMAL = 50     # Standard policies
    LOW = 100       # Cleanup/space reclamation


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class RetentionPolicyError(Exception):
    """Base exception for retention policy errors."""
    pass


class PolicyConflictError(RetentionPolicyError):
    """Raised when policies conflict."""
    pass


class InvalidPolicyError(RetentionPolicyError):
    """Raised when policy configuration is invalid."""
    pass


class RetentionViolationError(RetentionPolicyError):
    """Raised when retention requirements are violated."""
    pass


class LegalHoldError(RetentionPolicyError):
    """Raised when attempting to modify legally-held PDO."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RetentionPolicy:
    """
    A retention policy defining how PDOs should be managed.
    
    Immutable to ensure policy integrity.
    """
    policy_id: str
    name: str
    priority: PolicyPriority
    min_retention_days: int            # Minimum days to retain
    max_retention_days: Optional[int]  # Maximum days (None = forever)
    hot_days: int = 30                 # Days in HOT tier
    warm_days: int = 90                # Days in WARM tier
    cold_days: int = 365               # Days in COLD tier (then FROZEN)
    preserve_hash: bool = True         # Always preserve hashes
    compact_after_days: int = 90       # Days before compaction
    subject_pattern: str = "*"         # Pattern for matching PDO types
    metadata_filter: Dict[str, Any] = field(default_factory=dict)
    legal_hold_override: bool = False  # Can this policy override legal holds?
    
    def __post_init__(self):
        if self.min_retention_days < 0:
            raise InvalidPolicyError("min_retention_days cannot be negative")
        if self.max_retention_days is not None and self.max_retention_days < self.min_retention_days:
            raise InvalidPolicyError("max_retention_days must be >= min_retention_days")


@dataclass
class PDOMetadata:
    """
    Metadata for a PDO subject to retention.
    """
    pdo_id: str
    pdo_hash: str
    created_at: datetime
    modified_at: datetime
    subject_type: str              # PAC, WRAP, BER, etc.
    size_bytes: int
    tier: RetentionTier = RetentionTier.HOT
    last_accessed: Optional[datetime] = None
    legal_hold: bool = False
    legal_hold_reason: Optional[str] = None
    applied_policy_id: Optional[str] = None
    compacted: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def age_days(self) -> int:
        """Get age in days from creation."""
        delta = datetime.utcnow() - self.created_at
        return delta.days
    
    def days_since_access(self) -> int:
        """Get days since last access."""
        if self.last_accessed is None:
            return self.age_days()
        delta = datetime.utcnow() - self.last_accessed
        return delta.days
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdo_id": self.pdo_id,
            "pdo_hash": self.pdo_hash,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "subject_type": self.subject_type,
            "size_bytes": self.size_bytes,
            "tier": self.tier.value,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "legal_hold": self.legal_hold,
            "legal_hold_reason": self.legal_hold_reason,
            "applied_policy_id": self.applied_policy_id,
            "compacted": self.compacted,
            "metadata": self.metadata,
        }


@dataclass
class RetentionDecision:
    """
    A decision made by the retention engine.
    """
    pdo_id: str
    action: RetentionAction
    reason: str
    policy_id: str
    source_tier: RetentionTier
    target_tier: Optional[RetentionTier]
    decided_at: datetime = field(default_factory=datetime.utcnow)
    execute_after: Optional[datetime] = None  # Delayed execution
    preserves_hash: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdo_id": self.pdo_id,
            "action": self.action.value,
            "reason": self.reason,
            "policy_id": self.policy_id,
            "source_tier": self.source_tier.value,
            "target_tier": self.target_tier.value if self.target_tier else None,
            "decided_at": self.decided_at.isoformat(),
            "execute_after": self.execute_after.isoformat() if self.execute_after else None,
            "preserves_hash": self.preserves_hash,
        }


@dataclass
class CompactedPDO:
    """
    A compacted PDO with payload removed but hash preserved.
    """
    pdo_id: str
    pdo_hash: str
    original_size: int
    created_at: datetime
    compacted_at: datetime
    subject_type: str
    summary_metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdo_id": self.pdo_id,
            "pdo_hash": self.pdo_hash,
            "original_size": self.original_size,
            "created_at": self.created_at.isoformat(),
            "compacted_at": self.compacted_at.isoformat(),
            "subject_type": self.subject_type,
            "summary_metadata": self.summary_metadata,
        }


@dataclass
class Tombstone:
    """
    A tombstone record preserving hash after deletion.
    """
    pdo_id: str
    pdo_hash: str
    deleted_at: datetime
    reason: str
    deleted_by_policy: str
    original_created_at: datetime
    original_subject_type: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdo_id": self.pdo_id,
            "pdo_hash": self.pdo_hash,
            "deleted_at": self.deleted_at.isoformat(),
            "reason": self.reason,
            "deleted_by_policy": self.deleted_by_policy,
            "original_created_at": self.original_created_at.isoformat(),
            "original_subject_type": self.original_subject_type,
        }


@dataclass
class RetentionStats:
    """
    Statistics about retention operations.
    """
    total_pdos: int = 0
    hot_count: int = 0
    warm_count: int = 0
    cold_count: int = 0
    frozen_count: int = 0
    compacted_count: int = 0
    tombstone_count: int = 0
    legal_hold_count: int = 0
    total_size_bytes: int = 0
    compacted_size_bytes: int = 0  # Size saved by compaction
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_pdos": self.total_pdos,
            "hot_count": self.hot_count,
            "warm_count": self.warm_count,
            "cold_count": self.cold_count,
            "frozen_count": self.frozen_count,
            "compacted_count": self.compacted_count,
            "tombstone_count": self.tombstone_count,
            "legal_hold_count": self.legal_hold_count,
            "total_size_bytes": self.total_size_bytes,
            "compacted_size_bytes": self.compacted_size_bytes,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY MATCHER
# ═══════════════════════════════════════════════════════════════════════════════

class PolicyMatcher:
    """
    Matches PDOs to applicable retention policies.
    """

    @staticmethod
    def matches_pattern(subject_type: str, pattern: str) -> bool:
        """Check if subject type matches pattern."""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return subject_type.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return subject_type.endswith(pattern[1:])
        return subject_type == pattern

    @staticmethod
    def matches_metadata(pdo_metadata: Dict[str, Any], filter_spec: Dict[str, Any]) -> bool:
        """Check if PDO metadata matches filter specification."""
        if not filter_spec:
            return True
        
        for key, expected in filter_spec.items():
            actual = pdo_metadata.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# RETENTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class PDORetentionEngine:
    """
    Production-grade PDO retention policy engine.
    
    Manages PDO lifecycle with configurable policies,
    hash-preserving compaction, and legal hold support.
    """

    def __init__(self):
        """Initialize retention engine."""
        self._policies: Dict[str, RetentionPolicy] = {}
        self._pdos: Dict[str, PDOMetadata] = {}
        self._compacted: Dict[str, CompactedPDO] = {}
        self._tombstones: Dict[str, Tombstone] = {}
        self._lock = threading.RLock()
        self._audit_log: List[Dict[str, Any]] = []

    # ─────────────────────────────────────────────────────────────────────────
    # Policy Management
    # ─────────────────────────────────────────────────────────────────────────

    def register_policy(self, policy: RetentionPolicy) -> None:
        """Register a retention policy."""
        with self._lock:
            if policy.policy_id in self._policies:
                raise PolicyConflictError(f"Policy {policy.policy_id} already exists")
            self._policies[policy.policy_id] = policy
            self._log_audit("POLICY_REGISTERED", policy.policy_id)

    def unregister_policy(self, policy_id: str) -> bool:
        """Unregister a retention policy."""
        with self._lock:
            if policy_id in self._policies:
                del self._policies[policy_id]
                self._log_audit("POLICY_UNREGISTERED", policy_id)
                return True
            return False

    def get_policy(self, policy_id: str) -> Optional[RetentionPolicy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    def list_policies(self) -> List[RetentionPolicy]:
        """List all registered policies."""
        return list(self._policies.values())

    # ─────────────────────────────────────────────────────────────────────────
    # PDO Management
    # ─────────────────────────────────────────────────────────────────────────

    def register_pdo(self, metadata: PDOMetadata) -> None:
        """Register a PDO for retention management."""
        with self._lock:
            self._pdos[metadata.pdo_id] = metadata
            self._log_audit("PDO_REGISTERED", metadata.pdo_id)

    def get_pdo(self, pdo_id: str) -> Optional[PDOMetadata]:
        """Get PDO metadata."""
        return self._pdos.get(pdo_id)

    def update_access(self, pdo_id: str) -> bool:
        """Update last access time for PDO."""
        with self._lock:
            if pdo_id in self._pdos:
                pdo = self._pdos[pdo_id]
                # Create new instance with updated access time
                self._pdos[pdo_id] = PDOMetadata(
                    pdo_id=pdo.pdo_id,
                    pdo_hash=pdo.pdo_hash,
                    created_at=pdo.created_at,
                    modified_at=pdo.modified_at,
                    subject_type=pdo.subject_type,
                    size_bytes=pdo.size_bytes,
                    tier=pdo.tier,
                    last_accessed=datetime.utcnow(),
                    legal_hold=pdo.legal_hold,
                    legal_hold_reason=pdo.legal_hold_reason,
                    applied_policy_id=pdo.applied_policy_id,
                    compacted=pdo.compacted,
                    metadata=pdo.metadata,
                )
                return True
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Legal Holds
    # ─────────────────────────────────────────────────────────────────────────

    def apply_legal_hold(self, pdo_id: str, reason: str) -> bool:
        """Apply legal hold to prevent modification/deletion."""
        with self._lock:
            if pdo_id not in self._pdos:
                return False
            pdo = self._pdos[pdo_id]
            self._pdos[pdo_id] = PDOMetadata(
                pdo_id=pdo.pdo_id,
                pdo_hash=pdo.pdo_hash,
                created_at=pdo.created_at,
                modified_at=pdo.modified_at,
                subject_type=pdo.subject_type,
                size_bytes=pdo.size_bytes,
                tier=pdo.tier,
                last_accessed=pdo.last_accessed,
                legal_hold=True,
                legal_hold_reason=reason,
                applied_policy_id=pdo.applied_policy_id,
                compacted=pdo.compacted,
                metadata=pdo.metadata,
            )
            self._log_audit("LEGAL_HOLD_APPLIED", pdo_id, {"reason": reason})
            return True

    def release_legal_hold(self, pdo_id: str) -> bool:
        """Release legal hold."""
        with self._lock:
            if pdo_id not in self._pdos:
                return False
            pdo = self._pdos[pdo_id]
            if not pdo.legal_hold:
                return False
            self._pdos[pdo_id] = PDOMetadata(
                pdo_id=pdo.pdo_id,
                pdo_hash=pdo.pdo_hash,
                created_at=pdo.created_at,
                modified_at=pdo.modified_at,
                subject_type=pdo.subject_type,
                size_bytes=pdo.size_bytes,
                tier=pdo.tier,
                last_accessed=pdo.last_accessed,
                legal_hold=False,
                legal_hold_reason=None,
                applied_policy_id=pdo.applied_policy_id,
                compacted=pdo.compacted,
                metadata=pdo.metadata,
            )
            self._log_audit("LEGAL_HOLD_RELEASED", pdo_id)
            return True

    # ─────────────────────────────────────────────────────────────────────────
    # Policy Evaluation
    # ─────────────────────────────────────────────────────────────────────────

    def find_applicable_policy(self, pdo: PDOMetadata) -> Optional[RetentionPolicy]:
        """Find the highest priority applicable policy for a PDO."""
        applicable: List[RetentionPolicy] = []
        
        for policy in self._policies.values():
            if PolicyMatcher.matches_pattern(pdo.subject_type, policy.subject_pattern):
                if PolicyMatcher.matches_metadata(pdo.metadata, policy.metadata_filter):
                    applicable.append(policy)
        
        if not applicable:
            return None
        
        # Sort by priority (lower number = higher priority)
        applicable.sort(key=lambda p: p.priority.value)
        return applicable[0]

    def evaluate(self, pdo: PDOMetadata) -> RetentionDecision:
        """
        Evaluate retention policy for a PDO and return decision.
        """
        policy = self.find_applicable_policy(pdo)
        
        if policy is None:
            # No policy - retain by default
            return RetentionDecision(
                pdo_id=pdo.pdo_id,
                action=RetentionAction.RETAIN,
                reason="No applicable policy",
                policy_id="NONE",
                source_tier=pdo.tier,
                target_tier=pdo.tier,
            )
        
        # Check legal hold
        if pdo.legal_hold and not policy.legal_hold_override:
            return RetentionDecision(
                pdo_id=pdo.pdo_id,
                action=RetentionAction.RETAIN,
                reason=f"Legal hold: {pdo.legal_hold_reason}",
                policy_id=policy.policy_id,
                source_tier=pdo.tier,
                target_tier=pdo.tier,
            )
        
        age_days = pdo.age_days()
        
        # Check if past max retention
        if policy.max_retention_days and age_days > policy.max_retention_days:
            return RetentionDecision(
                pdo_id=pdo.pdo_id,
                action=RetentionAction.DELETE,
                reason=f"Exceeded max retention ({policy.max_retention_days} days)",
                policy_id=policy.policy_id,
                source_tier=pdo.tier,
                target_tier=RetentionTier.DELETED,
                preserves_hash=policy.preserve_hash,
            )
        
        # Check compaction eligibility
        if not pdo.compacted and age_days > policy.compact_after_days:
            return RetentionDecision(
                pdo_id=pdo.pdo_id,
                action=RetentionAction.COMPACT,
                reason=f"Age ({age_days}) exceeds compact threshold ({policy.compact_after_days})",
                policy_id=policy.policy_id,
                source_tier=pdo.tier,
                target_tier=pdo.tier,
                preserves_hash=True,
            )
        
        # Determine tier based on age
        target_tier = self._determine_tier(age_days, policy)
        
        if target_tier != pdo.tier:
            return RetentionDecision(
                pdo_id=pdo.pdo_id,
                action=RetentionAction.DEMOTE,
                reason=f"Age ({age_days}) requires tier change",
                policy_id=policy.policy_id,
                source_tier=pdo.tier,
                target_tier=target_tier,
                preserves_hash=True,
            )
        
        # No action needed
        return RetentionDecision(
            pdo_id=pdo.pdo_id,
            action=RetentionAction.RETAIN,
            reason="Within policy parameters",
            policy_id=policy.policy_id,
            source_tier=pdo.tier,
            target_tier=pdo.tier,
        )

    def _determine_tier(self, age_days: int, policy: RetentionPolicy) -> RetentionTier:
        """Determine appropriate tier based on age and policy."""
        if age_days <= policy.hot_days:
            return RetentionTier.HOT
        elif age_days <= policy.hot_days + policy.warm_days:
            return RetentionTier.WARM
        elif age_days <= policy.hot_days + policy.warm_days + policy.cold_days:
            return RetentionTier.COLD
        else:
            return RetentionTier.FROZEN

    # ─────────────────────────────────────────────────────────────────────────
    # Action Execution
    # ─────────────────────────────────────────────────────────────────────────

    def execute_decision(self, decision: RetentionDecision) -> bool:
        """Execute a retention decision."""
        with self._lock:
            if decision.pdo_id not in self._pdos:
                return False
            
            pdo = self._pdos[decision.pdo_id]
            
            # Re-check legal hold
            if pdo.legal_hold and decision.action in [
                RetentionAction.DELETE, RetentionAction.PURGE, RetentionAction.COMPACT
            ]:
                raise LegalHoldError(f"Cannot {decision.action.value} PDO under legal hold")
            
            if decision.action == RetentionAction.RETAIN:
                return True
            
            elif decision.action == RetentionAction.DEMOTE:
                return self._execute_demote(pdo, decision)
            
            elif decision.action == RetentionAction.COMPACT:
                return self._execute_compact(pdo, decision)
            
            elif decision.action == RetentionAction.DELETE:
                return self._execute_delete(pdo, decision)
            
            elif decision.action == RetentionAction.PURGE:
                return self._execute_purge(pdo, decision)
            
            return False

    def _execute_demote(self, pdo: PDOMetadata, decision: RetentionDecision) -> bool:
        """Execute tier demotion."""
        self._pdos[pdo.pdo_id] = PDOMetadata(
            pdo_id=pdo.pdo_id,
            pdo_hash=pdo.pdo_hash,
            created_at=pdo.created_at,
            modified_at=datetime.utcnow(),
            subject_type=pdo.subject_type,
            size_bytes=pdo.size_bytes,
            tier=decision.target_tier,
            last_accessed=pdo.last_accessed,
            legal_hold=pdo.legal_hold,
            legal_hold_reason=pdo.legal_hold_reason,
            applied_policy_id=decision.policy_id,
            compacted=pdo.compacted,
            metadata=pdo.metadata,
        )
        self._log_audit("PDO_DEMOTED", pdo.pdo_id, {
            "from_tier": decision.source_tier.value,
            "to_tier": decision.target_tier.value,
        })
        return True

    def _execute_compact(self, pdo: PDOMetadata, decision: RetentionDecision) -> bool:
        """Execute compaction (remove payload, keep hash)."""
        # Create compacted record
        compacted = CompactedPDO(
            pdo_id=pdo.pdo_id,
            pdo_hash=pdo.pdo_hash,
            original_size=pdo.size_bytes,
            created_at=pdo.created_at,
            compacted_at=datetime.utcnow(),
            subject_type=pdo.subject_type,
            summary_metadata={
                "age_days": pdo.age_days(),
                "policy_id": decision.policy_id,
            },
        )
        self._compacted[pdo.pdo_id] = compacted
        
        # Update PDO metadata
        self._pdos[pdo.pdo_id] = PDOMetadata(
            pdo_id=pdo.pdo_id,
            pdo_hash=pdo.pdo_hash,
            created_at=pdo.created_at,
            modified_at=datetime.utcnow(),
            subject_type=pdo.subject_type,
            size_bytes=0,  # Payload removed
            tier=pdo.tier,
            last_accessed=pdo.last_accessed,
            legal_hold=pdo.legal_hold,
            legal_hold_reason=pdo.legal_hold_reason,
            applied_policy_id=decision.policy_id,
            compacted=True,
            metadata=pdo.metadata,
        )
        
        self._log_audit("PDO_COMPACTED", pdo.pdo_id, {
            "original_size": pdo.size_bytes,
            "hash_preserved": pdo.pdo_hash,
        })
        return True

    def _execute_delete(self, pdo: PDOMetadata, decision: RetentionDecision) -> bool:
        """Execute deletion (creates tombstone with hash)."""
        if decision.preserves_hash:
            tombstone = Tombstone(
                pdo_id=pdo.pdo_id,
                pdo_hash=pdo.pdo_hash,
                deleted_at=datetime.utcnow(),
                reason=decision.reason,
                deleted_by_policy=decision.policy_id,
                original_created_at=pdo.created_at,
                original_subject_type=pdo.subject_type,
            )
            self._tombstones[pdo.pdo_id] = tombstone
        
        del self._pdos[pdo.pdo_id]
        if pdo.pdo_id in self._compacted:
            del self._compacted[pdo.pdo_id]
        
        self._log_audit("PDO_DELETED", pdo.pdo_id, {
            "hash_preserved": decision.preserves_hash,
            "tombstone_created": decision.preserves_hash,
        })
        return True

    def _execute_purge(self, pdo: PDOMetadata, decision: RetentionDecision) -> bool:
        """Execute purge (complete removal, no tombstone)."""
        del self._pdos[pdo.pdo_id]
        if pdo.pdo_id in self._compacted:
            del self._compacted[pdo.pdo_id]
        if pdo.pdo_id in self._tombstones:
            del self._tombstones[pdo.pdo_id]
        
        self._log_audit("PDO_PURGED", pdo.pdo_id, {
            "complete_removal": True,
        })
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Batch Operations
    # ─────────────────────────────────────────────────────────────────────────

    def evaluate_all(self) -> List[RetentionDecision]:
        """Evaluate all PDOs and return decisions."""
        decisions = []
        with self._lock:
            for pdo in self._pdos.values():
                decision = self.evaluate(pdo)
                decisions.append(decision)
        return decisions

    def execute_all_pending(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Execute all pending retention decisions.
        
        Returns count of each action taken.
        """
        decisions = self.evaluate_all()
        action_counts: Dict[str, int] = defaultdict(int)
        
        for decision in decisions:
            if decision.action != RetentionAction.RETAIN:
                if not dry_run:
                    try:
                        self.execute_decision(decision)
                    except LegalHoldError:
                        action_counts["BLOCKED_BY_LEGAL_HOLD"] += 1
                        continue
                action_counts[decision.action.value] += 1
        
        return dict(action_counts)

    # ─────────────────────────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────────────────────────

    def get_statistics(self) -> RetentionStats:
        """Get current retention statistics."""
        stats = RetentionStats()
        
        with self._lock:
            stats.total_pdos = len(self._pdos)
            stats.tombstone_count = len(self._tombstones)
            stats.compacted_count = len(self._compacted)
            
            for pdo in self._pdos.values():
                stats.total_size_bytes += pdo.size_bytes
                
                if pdo.legal_hold:
                    stats.legal_hold_count += 1
                
                if pdo.tier == RetentionTier.HOT:
                    stats.hot_count += 1
                elif pdo.tier == RetentionTier.WARM:
                    stats.warm_count += 1
                elif pdo.tier == RetentionTier.COLD:
                    stats.cold_count += 1
                elif pdo.tier == RetentionTier.FROZEN:
                    stats.frozen_count += 1
            
            for compacted in self._compacted.values():
                stats.compacted_size_bytes += compacted.original_size
        
        return stats

    # ─────────────────────────────────────────────────────────────────────────
    # Tombstone Operations
    # ─────────────────────────────────────────────────────────────────────────

    def get_tombstone(self, pdo_id: str) -> Optional[Tombstone]:
        """Get tombstone for deleted PDO."""
        return self._tombstones.get(pdo_id)

    def verify_hash_existed(self, pdo_hash: str) -> bool:
        """Verify a hash existed (checks active PDOs and tombstones)."""
        # Check active PDOs
        for pdo in self._pdos.values():
            if pdo.pdo_hash == pdo_hash:
                return True
        
        # Check tombstones
        for tombstone in self._tombstones.values():
            if tombstone.pdo_hash == pdo_hash:
                return True
        
        # Check compacted
        for compacted in self._compacted.values():
            if compacted.pdo_hash == pdo_hash:
                return True
        
        return False

    def list_tombstones(self) -> List[Tombstone]:
        """List all tombstones."""
        return list(self._tombstones.values())

    # ─────────────────────────────────────────────────────────────────────────
    # Audit
    # ─────────────────────────────────────────────────────────────────────────

    def _log_audit(
        self,
        action: str,
        subject_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log audit entry."""
        self._audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "subject_id": subject_id,
            "details": details or {},
        })

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit log entries."""
        return self._audit_log[-limit:]

    def clear_audit_log(self) -> int:
        """Clear audit log and return count of cleared entries."""
        count = len(self._audit_log)
        self._audit_log.clear()
        return count


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT POLICIES
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_PAC_POLICY = RetentionPolicy(
    policy_id="default-pac",
    name="Default PAC Retention",
    priority=PolicyPriority.NORMAL,
    min_retention_days=365,
    max_retention_days=365 * 7,  # 7 years
    hot_days=30,
    warm_days=90,
    cold_days=365,
    compact_after_days=180,
    subject_pattern="PAC*",
)

DEFAULT_WRAP_POLICY = RetentionPolicy(
    policy_id="default-wrap",
    name="Default WRAP Retention",
    priority=PolicyPriority.NORMAL,
    min_retention_days=365,
    max_retention_days=365 * 7,
    hot_days=7,
    warm_days=30,
    cold_days=180,
    compact_after_days=90,
    subject_pattern="WRAP*",
)

DEFAULT_BER_POLICY = RetentionPolicy(
    policy_id="default-ber",
    name="Default BER Retention",
    priority=PolicyPriority.HIGH,
    min_retention_days=365 * 2,  # 2 years minimum
    max_retention_days=None,      # Never auto-delete
    hot_days=90,
    warm_days=365,
    cold_days=365 * 3,
    compact_after_days=365,
    subject_pattern="BER*",
)

DEFAULT_PDO_POLICY = RetentionPolicy(
    policy_id="default-pdo",
    name="Default PDO Retention",
    priority=PolicyPriority.NORMAL,
    min_retention_days=365,
    max_retention_days=365 * 5,
    hot_days=30,
    warm_days=90,
    cold_days=365,
    compact_after_days=120,
    subject_pattern="PDO*",
)


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

_engine: Optional[PDORetentionEngine] = None


def get_retention_engine(with_defaults: bool = True) -> PDORetentionEngine:
    """Get or create global retention engine."""
    global _engine
    if _engine is None:
        _engine = PDORetentionEngine()
        if with_defaults:
            _engine.register_policy(DEFAULT_PAC_POLICY)
            _engine.register_policy(DEFAULT_WRAP_POLICY)
            _engine.register_policy(DEFAULT_BER_POLICY)
            _engine.register_policy(DEFAULT_PDO_POLICY)
    return _engine


def reset_retention_engine() -> None:
    """Reset global engine."""
    global _engine
    _engine = None
