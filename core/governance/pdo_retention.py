"""
Tiered PDO Retention + Archival Policies Engine.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-031
Agent: GID-07 (Dan) — DATA
Deliverable: Tiered PDO Retention + Archival Policies

Features:
- Tiered retention policies (hot/warm/cold/archive)
- Automatic lifecycle transitions
- Compliance-aware retention rules
- Hash-verified archival integrity
- Configurable retention schedules

This module manages the lifecycle of Proof-Decision-Outcome (PDO) records
to ensure governance compliance while optimizing storage costs.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


# =============================================================================
# CONSTANTS
# =============================================================================

MODULE_VERSION = "1.0.0"

# Default retention periods (days)
DEFAULT_HOT_RETENTION_DAYS = 30
DEFAULT_WARM_RETENTION_DAYS = 90
DEFAULT_COLD_RETENTION_DAYS = 365
DEFAULT_ARCHIVE_RETENTION_DAYS = 2555  # 7 years


# =============================================================================
# ENUMS
# =============================================================================

class StorageTier(Enum):
    """Storage tier classifications."""
    HOT = "HOT"          # Active, fast access, high cost
    WARM = "WARM"        # Semi-active, medium access, medium cost
    COLD = "COLD"        # Inactive, slow access, low cost
    ARCHIVE = "ARCHIVE"  # Long-term, very slow access, minimal cost
    DELETED = "DELETED"  # Marked for deletion


class RetentionStatus(Enum):
    """Retention policy status."""
    ACTIVE = "ACTIVE"
    TRANSITIONING = "TRANSITIONING"
    EXPIRED = "EXPIRED"
    HOLD = "HOLD"  # Legal or compliance hold


class ComplianceFramework(Enum):
    """Compliance frameworks affecting retention."""
    SOC2 = "SOC2"
    GDPR = "GDPR"
    HIPAA = "HIPAA"
    PCI_DSS = "PCI_DSS"
    FINRA = "FINRA"
    SEC = "SEC"
    INTERNAL = "INTERNAL"


class PDOType(Enum):
    """Types of PDO records."""
    DECISION = "DECISION"
    PROOF = "PROOF"
    OUTCOME = "OUTCOME"
    AUDIT_LOG = "AUDIT_LOG"
    GOVERNANCE = "GOVERNANCE"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class RetentionError(Exception):
    """Base exception for retention errors."""
    pass


class PolicyNotFoundError(RetentionError):
    """Raised when policy not found."""
    
    def __init__(self, policy_id: str) -> None:
        self.policy_id = policy_id
        super().__init__(f"Policy not found: {policy_id}")


class InvalidTransitionError(RetentionError):
    """Raised when tier transition is invalid."""
    
    def __init__(self, from_tier: StorageTier, to_tier: StorageTier) -> None:
        self.from_tier = from_tier
        self.to_tier = to_tier
        super().__init__(
            f"Invalid transition from {from_tier.value} to {to_tier.value}"
        )


class HoldViolationError(RetentionError):
    """Raised when operation violates legal hold."""
    
    def __init__(self, record_id: str, hold_id: str) -> None:
        self.record_id = record_id
        self.hold_id = hold_id
        super().__init__(
            f"Record '{record_id}' is under legal hold '{hold_id}'"
        )


class IntegrityError(RetentionError):
    """Raised when archival integrity check fails."""
    
    def __init__(self, record_id: str, reason: str) -> None:
        self.record_id = record_id
        self.reason = reason
        super().__init__(f"Integrity check failed for '{record_id}': {reason}")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class RetentionPolicy:
    """Defines retention rules for a PDO category."""
    
    policy_id: str
    name: str
    pdo_types: Set[PDOType]
    hot_days: int
    warm_days: int
    cold_days: int
    archive_days: int
    compliance_frameworks: Set[ComplianceFramework] = field(default_factory=set)
    auto_transition: bool = True
    require_approval_for_deletion: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_retention_days(self) -> int:
        """Total retention period before deletion."""
        return self.hot_days + self.warm_days + self.cold_days + self.archive_days
    
    def get_tier_for_age(self, age_days: int) -> StorageTier:
        """Determine storage tier based on record age."""
        if age_days < self.hot_days:
            return StorageTier.HOT
        elif age_days < self.hot_days + self.warm_days:
            return StorageTier.WARM
        elif age_days < self.hot_days + self.warm_days + self.cold_days:
            return StorageTier.COLD
        elif age_days < self.total_retention_days:
            return StorageTier.ARCHIVE
        else:
            return StorageTier.DELETED
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize policy."""
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "pdo_types": [t.value for t in self.pdo_types],
            "hot_days": self.hot_days,
            "warm_days": self.warm_days,
            "cold_days": self.cold_days,
            "archive_days": self.archive_days,
            "compliance_frameworks": [f.value for f in self.compliance_frameworks],
            "auto_transition": self.auto_transition,
        }


@dataclass
class LegalHold:
    """Legal or compliance hold on records."""
    
    hold_id: str
    name: str
    reason: str
    created_at: str
    expires_at: Optional[str] = None
    record_ids: Set[str] = field(default_factory=set)
    active: bool = True
    
    @property
    def is_expired(self) -> bool:
        """Check if hold has expired."""
        if not self.expires_at:
            return False
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now(timezone.utc) > expires


@dataclass
class PDORecord:
    """A PDO record subject to retention policies."""
    
    record_id: str
    pdo_type: PDOType
    created_at: str
    policy_id: str
    current_tier: StorageTier = StorageTier.HOT
    status: RetentionStatus = RetentionStatus.ACTIVE
    content_hash: Optional[str] = None
    last_accessed: Optional[str] = None
    last_transitioned: Optional[str] = None
    hold_ids: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def age_days(self) -> int:
        """Record age in days."""
        created = datetime.fromisoformat(self.created_at)
        now = datetime.now(timezone.utc)
        return (now - created).days
    
    @property
    def is_under_hold(self) -> bool:
        """Check if record is under any hold."""
        return len(self.hold_ids) > 0
    
    def compute_hash(self, content: str) -> str:
        """Compute and store content hash."""
        self.content_hash = hashlib.sha256(content.encode()).hexdigest()
        return self.content_hash
    
    def verify_hash(self, content: str) -> bool:
        """Verify content matches stored hash."""
        if not self.content_hash:
            return False
        computed = hashlib.sha256(content.encode()).hexdigest()
        return computed == self.content_hash


@dataclass
class TransitionRecord:
    """Record of a tier transition."""
    
    transition_id: str
    record_id: str
    from_tier: StorageTier
    to_tier: StorageTier
    transitioned_at: str
    reason: str
    approved_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize transition record."""
        return {
            "transition_id": self.transition_id,
            "record_id": self.record_id,
            "from_tier": self.from_tier.value,
            "to_tier": self.to_tier.value,
            "transitioned_at": self.transitioned_at,
            "reason": self.reason,
        }


@dataclass
class RetentionReport:
    """Summary report of retention state."""
    
    report_id: str
    generated_at: str
    total_records: int
    records_by_tier: Dict[StorageTier, int]
    records_by_type: Dict[PDOType, int]
    records_under_hold: int
    pending_transitions: int
    expired_records: int
    storage_breakdown: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize report."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at,
            "total_records": self.total_records,
            "records_by_tier": {k.value: v for k, v in self.records_by_tier.items()},
            "records_by_type": {k.value: v for k, v in self.records_by_type.items()},
            "records_under_hold": self.records_under_hold,
            "pending_transitions": self.pending_transitions,
            "expired_records": self.expired_records,
        }


# =============================================================================
# TIER TRANSITION VALIDATOR
# =============================================================================

class TierTransitionValidator:
    """Validates tier transitions."""
    
    # Valid tier transitions (source -> allowed targets)
    VALID_TRANSITIONS = {
        StorageTier.HOT: {StorageTier.WARM, StorageTier.COLD},
        StorageTier.WARM: {StorageTier.COLD, StorageTier.ARCHIVE, StorageTier.HOT},
        StorageTier.COLD: {StorageTier.ARCHIVE, StorageTier.WARM},
        StorageTier.ARCHIVE: {StorageTier.DELETED, StorageTier.COLD},
        StorageTier.DELETED: set(),
    }
    
    def is_valid_transition(
        self,
        from_tier: StorageTier,
        to_tier: StorageTier,
    ) -> bool:
        """Check if transition is valid."""
        if from_tier == to_tier:
            return False
        return to_tier in self.VALID_TRANSITIONS.get(from_tier, set())
    
    def validate_transition(
        self,
        record: PDORecord,
        to_tier: StorageTier,
    ) -> List[str]:
        """
        Validate transition and return errors.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check valid transition path
        if not self.is_valid_transition(record.current_tier, to_tier):
            errors.append(
                f"Invalid transition from {record.current_tier.value} to {to_tier.value}"
            )
        
        # Check legal holds for deletion
        if to_tier == StorageTier.DELETED and record.is_under_hold:
            errors.append(
                f"Cannot delete record under legal hold: {record.hold_ids}"
            )
        
        return errors


# =============================================================================
# RETENTION POLICY MANAGER
# =============================================================================

class RetentionPolicyManager:
    """
    Manages retention policies and record lifecycle.
    """
    
    def __init__(self) -> None:
        self._policies: Dict[str, RetentionPolicy] = {}
        self._records: Dict[str, PDORecord] = {}
        self._holds: Dict[str, LegalHold] = {}
        self._transitions: List[TransitionRecord] = []
        self._validator = TierTransitionValidator()
    
    # -------------------------------------------------------------------------
    # POLICY MANAGEMENT
    # -------------------------------------------------------------------------
    
    def create_policy(
        self,
        name: str,
        pdo_types: Set[PDOType],
        hot_days: int = DEFAULT_HOT_RETENTION_DAYS,
        warm_days: int = DEFAULT_WARM_RETENTION_DAYS,
        cold_days: int = DEFAULT_COLD_RETENTION_DAYS,
        archive_days: int = DEFAULT_ARCHIVE_RETENTION_DAYS,
        compliance_frameworks: Optional[Set[ComplianceFramework]] = None,
    ) -> RetentionPolicy:
        """Create a new retention policy."""
        policy_id = f"POL-{uuid.uuid4().hex[:8].upper()}"
        
        policy = RetentionPolicy(
            policy_id=policy_id,
            name=name,
            pdo_types=pdo_types,
            hot_days=hot_days,
            warm_days=warm_days,
            cold_days=cold_days,
            archive_days=archive_days,
            compliance_frameworks=compliance_frameworks or set(),
        )
        
        self._policies[policy_id] = policy
        return policy
    
    def get_policy(self, policy_id: str) -> RetentionPolicy:
        """Get policy by ID."""
        if policy_id not in self._policies:
            raise PolicyNotFoundError(policy_id)
        return self._policies[policy_id]
    
    def get_policy_for_type(self, pdo_type: PDOType) -> Optional[RetentionPolicy]:
        """Find policy applicable to PDO type."""
        for policy in self._policies.values():
            if pdo_type in policy.pdo_types:
                return policy
        return None
    
    def list_policies(self) -> List[RetentionPolicy]:
        """List all policies."""
        return list(self._policies.values())
    
    # -------------------------------------------------------------------------
    # RECORD MANAGEMENT
    # -------------------------------------------------------------------------
    
    def register_record(
        self,
        pdo_type: PDOType,
        content: Optional[str] = None,
        policy_id: Optional[str] = None,
    ) -> PDORecord:
        """Register a new PDO record."""
        record_id = f"PDO-{uuid.uuid4().hex[:12].upper()}"
        
        # Find applicable policy
        if policy_id:
            policy = self.get_policy(policy_id)
        else:
            policy = self.get_policy_for_type(pdo_type)
            if not policy:
                raise RetentionError(f"No policy found for type {pdo_type.value}")
            policy_id = policy.policy_id
        
        record = PDORecord(
            record_id=record_id,
            pdo_type=pdo_type,
            created_at=datetime.now(timezone.utc).isoformat(),
            policy_id=policy_id,
        )
        
        if content:
            record.compute_hash(content)
        
        self._records[record_id] = record
        return record
    
    def get_record(self, record_id: str) -> Optional[PDORecord]:
        """Get record by ID."""
        return self._records.get(record_id)
    
    def access_record(self, record_id: str) -> Optional[PDORecord]:
        """Access record and update last accessed timestamp."""
        record = self._records.get(record_id)
        if record:
            record.last_accessed = datetime.now(timezone.utc).isoformat()
        return record
    
    # -------------------------------------------------------------------------
    # TIER TRANSITIONS
    # -------------------------------------------------------------------------
    
    def transition_record(
        self,
        record_id: str,
        to_tier: StorageTier,
        reason: str,
        approved_by: Optional[str] = None,
    ) -> TransitionRecord:
        """Transition a record to a new tier."""
        record = self._records.get(record_id)
        if not record:
            raise RetentionError(f"Record not found: {record_id}")
        
        # Check legal holds FIRST (before transition validation)
        if to_tier == StorageTier.DELETED and record.is_under_hold:
            hold_id = list(record.hold_ids)[0]
            raise HoldViolationError(record_id, hold_id)
        
        # Validate transition (excluding hold check since we did it above)
        if not self._validator.is_valid_transition(record.current_tier, to_tier):
            raise InvalidTransitionError(record.current_tier, to_tier)
        
        # Record transition
        transition_id = f"TR-{uuid.uuid4().hex[:8].upper()}"
        from_tier = record.current_tier
        
        transition = TransitionRecord(
            transition_id=transition_id,
            record_id=record_id,
            from_tier=from_tier,
            to_tier=to_tier,
            transitioned_at=datetime.now(timezone.utc).isoformat(),
            reason=reason,
            approved_by=approved_by,
        )
        
        # Update record
        record.current_tier = to_tier
        record.last_transitioned = transition.transitioned_at
        if to_tier == StorageTier.DELETED:
            record.status = RetentionStatus.EXPIRED
        else:
            record.status = RetentionStatus.ACTIVE
        
        self._transitions.append(transition)
        return transition
    
    def auto_transition_records(self) -> List[TransitionRecord]:
        """
        Automatically transition records based on age and policy.
        
        Returns:
            List of transitions performed
        """
        transitions = []
        
        for record in self._records.values():
            if record.status == RetentionStatus.HOLD:
                continue
            
            policy = self._policies.get(record.policy_id)
            if not policy or not policy.auto_transition:
                continue
            
            target_tier = policy.get_tier_for_age(record.age_days)
            
            if target_tier != record.current_tier:
                try:
                    if target_tier == StorageTier.DELETED and record.is_under_hold:
                        continue
                    
                    transition = self.transition_record(
                        record.record_id,
                        target_tier,
                        reason="Automatic age-based transition",
                    )
                    transitions.append(transition)
                except (InvalidTransitionError, HoldViolationError):
                    continue
        
        return transitions
    
    # -------------------------------------------------------------------------
    # LEGAL HOLDS
    # -------------------------------------------------------------------------
    
    def create_hold(
        self,
        name: str,
        reason: str,
        record_ids: Set[str],
        expires_at: Optional[str] = None,
    ) -> LegalHold:
        """Create a legal hold on records."""
        hold_id = f"HOLD-{uuid.uuid4().hex[:8].upper()}"
        
        hold = LegalHold(
            hold_id=hold_id,
            name=name,
            reason=reason,
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=expires_at,
            record_ids=record_ids,
        )
        
        # Update records
        for record_id in record_ids:
            if record_id in self._records:
                self._records[record_id].hold_ids.add(hold_id)
                self._records[record_id].status = RetentionStatus.HOLD
        
        self._holds[hold_id] = hold
        return hold
    
    def release_hold(self, hold_id: str) -> None:
        """Release a legal hold."""
        hold = self._holds.get(hold_id)
        if not hold:
            return
        
        hold.active = False
        
        # Update records
        for record_id in hold.record_ids:
            if record_id in self._records:
                self._records[record_id].hold_ids.discard(hold_id)
                if not self._records[record_id].is_under_hold:
                    self._records[record_id].status = RetentionStatus.ACTIVE
    
    def get_records_under_hold(self) -> List[PDORecord]:
        """Get all records under legal hold."""
        return [r for r in self._records.values() if r.is_under_hold]
    
    # -------------------------------------------------------------------------
    # ARCHIVAL INTEGRITY
    # -------------------------------------------------------------------------
    
    def verify_record_integrity(
        self,
        record_id: str,
        content: str,
    ) -> bool:
        """Verify record integrity."""
        record = self._records.get(record_id)
        if not record:
            raise RetentionError(f"Record not found: {record_id}")
        
        return record.verify_hash(content)
    
    def audit_integrity(self, content_provider: Callable[[str], str]) -> Dict[str, bool]:
        """
        Audit integrity of all records.
        
        Args:
            content_provider: Function that returns content for a record ID
        
        Returns:
            Dict mapping record_id to integrity status
        """
        results = {}
        for record_id, record in self._records.items():
            if record.content_hash:
                try:
                    content = content_provider(record_id)
                    results[record_id] = record.verify_hash(content)
                except Exception:
                    results[record_id] = False
            else:
                results[record_id] = True  # No hash to verify
        return results
    
    # -------------------------------------------------------------------------
    # REPORTING
    # -------------------------------------------------------------------------
    
    def generate_report(self) -> RetentionReport:
        """Generate retention summary report."""
        records_by_tier = {tier: 0 for tier in StorageTier}
        records_by_type = {pdo_type: 0 for pdo_type in PDOType}
        
        for record in self._records.values():
            records_by_tier[record.current_tier] += 1
            records_by_type[record.pdo_type] += 1
        
        records_under_hold = len(self.get_records_under_hold())
        
        # Count pending transitions
        pending = 0
        expired = 0
        for record in self._records.values():
            policy = self._policies.get(record.policy_id)
            if policy:
                target_tier = policy.get_tier_for_age(record.age_days)
                if target_tier != record.current_tier:
                    if target_tier == StorageTier.DELETED:
                        expired += 1
                    else:
                        pending += 1
        
        # Storage breakdown (mock percentages)
        total = len(self._records) or 1
        storage_breakdown = {
            tier.value: count / total * 100
            for tier, count in records_by_tier.items()
        }
        
        return RetentionReport(
            report_id=f"RPT-{uuid.uuid4().hex[:8].upper()}",
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_records=len(self._records),
            records_by_tier=records_by_tier,
            records_by_type=records_by_type,
            records_under_hold=records_under_hold,
            pending_transitions=pending,
            expired_records=expired,
            storage_breakdown=storage_breakdown,
        )
    
    # -------------------------------------------------------------------------
    # CLEANUP
    # -------------------------------------------------------------------------
    
    def purge_expired(self) -> List[str]:
        """
        Permanently delete expired records not under hold.
        
        Returns:
            List of deleted record IDs
        """
        deleted = []
        
        to_delete = [
            record_id for record_id, record in self._records.items()
            if record.current_tier == StorageTier.DELETED
            and not record.is_under_hold
        ]
        
        for record_id in to_delete:
            del self._records[record_id]
            deleted.append(record_id)
        
        return deleted


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_retention_manager() -> RetentionPolicyManager:
    """Create a retention policy manager."""
    return RetentionPolicyManager()


def create_default_policies(manager: RetentionPolicyManager) -> List[RetentionPolicy]:
    """Create default retention policies."""
    policies = []
    
    # Governance records - longest retention
    policies.append(manager.create_policy(
        name="Governance Records",
        pdo_types={PDOType.GOVERNANCE, PDOType.AUDIT_LOG},
        hot_days=90,
        warm_days=365,
        cold_days=730,
        archive_days=2555,  # 7 years
        compliance_frameworks={ComplianceFramework.SOC2, ComplianceFramework.SEC},
    ))
    
    # Decision records
    policies.append(manager.create_policy(
        name="Decision Records",
        pdo_types={PDOType.DECISION},
        hot_days=30,
        warm_days=90,
        cold_days=365,
        archive_days=1825,  # 5 years
        compliance_frameworks={ComplianceFramework.SOC2},
    ))
    
    # Proof records
    policies.append(manager.create_policy(
        name="Proof Records",
        pdo_types={PDOType.PROOF, PDOType.OUTCOME},
        hot_days=30,
        warm_days=60,
        cold_days=180,
        archive_days=730,  # 2 years
        compliance_frameworks={ComplianceFramework.INTERNAL},
    ))
    
    return policies


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Version
    "MODULE_VERSION",
    # Constants
    "DEFAULT_HOT_RETENTION_DAYS",
    "DEFAULT_WARM_RETENTION_DAYS",
    "DEFAULT_COLD_RETENTION_DAYS",
    "DEFAULT_ARCHIVE_RETENTION_DAYS",
    # Enums
    "StorageTier",
    "RetentionStatus",
    "ComplianceFramework",
    "PDOType",
    # Exceptions
    "RetentionError",
    "PolicyNotFoundError",
    "InvalidTransitionError",
    "HoldViolationError",
    "IntegrityError",
    # Data Classes
    "RetentionPolicy",
    "LegalHold",
    "PDORecord",
    "TransitionRecord",
    "RetentionReport",
    # Core Classes
    "TierTransitionValidator",
    "RetentionPolicyManager",
    # Factory Functions
    "create_retention_manager",
    "create_default_policies",
]
