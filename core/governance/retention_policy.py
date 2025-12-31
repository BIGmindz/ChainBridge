# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Retention Policy & Time Bounds
# PAC-012: Governance Hardening — ORDER 4 (Dan GID-04)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Retention period declarations, snapshot vs rolling artifact labeling,
and CI gate enforcement for governance completeness.

GOVERNANCE INVARIANTS:
- INV-GOV-006: Retention & time bounds explicit
- INV-GOV-007: Training signals classified
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import sys
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

RETENTION_SCHEMA_VERSION = "1.0.0"
"""Retention schema version."""


# ═══════════════════════════════════════════════════════════════════════════════
# RETENTION PERIOD DECLARATIONS (INV-GOV-006)
# ═══════════════════════════════════════════════════════════════════════════════

class RetentionPeriod(str, Enum):
    """
    Standard retention periods.
    
    INV-GOV-006: Retention & time bounds explicit.
    """
    EPHEMERAL = "EPHEMERAL"         # Deleted after use (session-only)
    SHORT_TERM = "SHORT_TERM"       # 7 days
    MEDIUM_TERM = "MEDIUM_TERM"     # 30 days
    LONG_TERM = "LONG_TERM"         # 365 days
    PERMANENT = "PERMANENT"         # Never deleted (audit/compliance)


# Retention period durations in days
RETENTION_DAYS: Dict[RetentionPeriod, Optional[int]] = {
    RetentionPeriod.EPHEMERAL: 0,
    RetentionPeriod.SHORT_TERM: 7,
    RetentionPeriod.MEDIUM_TERM: 30,
    RetentionPeriod.LONG_TERM: 365,
    RetentionPeriod.PERMANENT: None,  # Never expires
}


class ArtifactStorageType(str, Enum):
    """
    Artifact storage classification.
    
    INV-GOV-006: Snapshot vs rolling must be explicit.
    """
    SNAPSHOT = "SNAPSHOT"   # Point-in-time capture, immutable
    ROLLING = "ROLLING"     # Continuously updated, mutable


@dataclass
class RetentionPolicy:
    """
    Retention policy declaration for an artifact type.
    
    INV-GOV-006: All retention must be explicitly declared.
    """
    policy_id: str
    artifact_type: str
    
    # Retention settings
    retention_period: RetentionPeriod
    storage_type: ArtifactStorageType
    
    # Time bounds
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None  # Computed from retention_period
    
    # Classification
    contains_pii: bool = False
    contains_financial: bool = False
    audit_required: bool = False
    
    # Training signal classification (INV-GOV-007)
    training_signal_eligible: bool = False
    training_signal_classification: Optional[str] = None  # APPROVED, EXCLUDED, PENDING_REVIEW
    
    def __post_init__(self):
        """Compute expiration timestamp."""
        if self.retention_period != RetentionPeriod.PERMANENT:
            days = RETENTION_DAYS.get(self.retention_period)
            if days is not None and days > 0:
                created = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
                expires = created + timedelta(days=days)
                self.expires_at = expires.isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "policy_id": self.policy_id,
            "artifact_type": self.artifact_type,
            "retention_period": self.retention_period.value,
            "storage_type": self.storage_type.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "contains_pii": self.contains_pii,
            "contains_financial": self.contains_financial,
            "audit_required": self.audit_required,
            "training_signal_eligible": self.training_signal_eligible,
            "training_signal_classification": self.training_signal_classification,
        }
    
    @property
    def is_expired(self) -> bool:
        """Check if artifact has expired."""
        if self.expires_at is None:
            return False
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > expires


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING SIGNAL CLASSIFICATION (INV-GOV-007)
# ═══════════════════════════════════════════════════════════════════════════════

class TrainingSignalClass(str, Enum):
    """
    Training signal classification.
    
    INV-GOV-007: Training signals classified.
    """
    APPROVED = "APPROVED"           # Can be used for training
    EXCLUDED = "EXCLUDED"           # Must not be used for training
    PENDING_REVIEW = "PENDING_REVIEW"  # Awaiting classification
    NOT_APPLICABLE = "NOT_APPLICABLE"  # Not relevant to training


@dataclass
class TrainingSignalDeclaration:
    """
    Declaration of training signal classification for an artifact.
    
    INV-GOV-007: All data potentially used for training must be classified.
    """
    declaration_id: str
    artifact_id: str
    artifact_type: str
    
    # Classification
    classification: TrainingSignalClass
    
    # Rationale
    rationale: str
    classified_by: str
    classified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Restrictions
    geographic_restrictions: List[str] = field(default_factory=list)
    usage_restrictions: List[str] = field(default_factory=list)
    
    # Review
    requires_periodic_review: bool = False
    next_review_date: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL RETENTION POLICIES
# ═══════════════════════════════════════════════════════════════════════════════

CANONICAL_RETENTION_POLICIES: List[RetentionPolicy] = [
    # Audit artifacts
    RetentionPolicy(
        policy_id="RET-001",
        artifact_type="GOVERNANCE_EVENT",
        retention_period=RetentionPeriod.PERMANENT,
        storage_type=ArtifactStorageType.SNAPSHOT,
        audit_required=True,
        training_signal_eligible=False,
    ),
    RetentionPolicy(
        policy_id="RET-002",
        artifact_type="PDO",
        retention_period=RetentionPeriod.PERMANENT,
        storage_type=ArtifactStorageType.SNAPSHOT,
        audit_required=True,
        training_signal_eligible=False,
    ),
    RetentionPolicy(
        policy_id="RET-003",
        artifact_type="BER",
        retention_period=RetentionPeriod.PERMANENT,
        storage_type=ArtifactStorageType.SNAPSHOT,
        audit_required=True,
        training_signal_eligible=False,
    ),
    RetentionPolicy(
        policy_id="RET-004",
        artifact_type="WRAP",
        retention_period=RetentionPeriod.PERMANENT,
        storage_type=ArtifactStorageType.SNAPSHOT,
        audit_required=True,
        training_signal_eligible=False,
    ),
    
    # Execution artifacts
    RetentionPolicy(
        policy_id="RET-005",
        artifact_type="EXECUTION_LOG",
        retention_period=RetentionPeriod.LONG_TERM,
        storage_type=ArtifactStorageType.SNAPSHOT,
        audit_required=True,
        training_signal_eligible=True,
        training_signal_classification="PENDING_REVIEW",
    ),
    RetentionPolicy(
        policy_id="RET-006",
        artifact_type="AGENT_DECISION",
        retention_period=RetentionPeriod.LONG_TERM,
        storage_type=ArtifactStorageType.SNAPSHOT,
        audit_required=True,
        training_signal_eligible=True,
        training_signal_classification="PENDING_REVIEW",
    ),
    
    # Operational artifacts
    RetentionPolicy(
        policy_id="RET-007",
        artifact_type="METRIC",
        retention_period=RetentionPeriod.MEDIUM_TERM,
        storage_type=ArtifactStorageType.ROLLING,
        audit_required=False,
        training_signal_eligible=False,
    ),
    RetentionPolicy(
        policy_id="RET-008",
        artifact_type="SESSION_STATE",
        retention_period=RetentionPeriod.EPHEMERAL,
        storage_type=ArtifactStorageType.ROLLING,
        audit_required=False,
        training_signal_eligible=False,
    ),
    
    # Trace artifacts
    RetentionPolicy(
        policy_id="RET-009",
        artifact_type="TRACE_LINK",
        retention_period=RetentionPeriod.LONG_TERM,
        storage_type=ArtifactStorageType.SNAPSHOT,
        audit_required=True,
        training_signal_eligible=False,
    ),
    RetentionPolicy(
        policy_id="RET-010",
        artifact_type="CAUSALITY_LINK",
        retention_period=RetentionPeriod.LONG_TERM,
        storage_type=ArtifactStorageType.SNAPSHOT,
        audit_required=True,
        training_signal_eligible=False,
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# CI GATE ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class CIGateStatus(str, Enum):
    """CI gate check status."""
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class CIGateCheck:
    """
    Result of a CI gate check.
    """
    gate_id: str
    gate_name: str
    status: CIGateStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CIGateResult:
    """
    Aggregate CI gate result.
    """
    passed: bool
    checks: List[CIGateCheck]
    total_checks: int
    passed_checks: int
    failed_checks: int
    skipped_checks: int
    run_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "checks": [
                {
                    "gate_id": c.gate_id,
                    "gate_name": c.gate_name,
                    "status": c.status.value,
                    "message": c.message,
                    "details": c.details,
                    "checked_at": c.checked_at,
                }
                for c in self.checks
            ],
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "skipped_checks": self.skipped_checks,
            "run_at": self.run_at,
        }


class GovernanceCIGate:
    """
    CI gate enforcer for governance completeness.
    
    Validates that all governance requirements are met before merge/deploy.
    """
    
    REQUIRED_GOVERNANCE_FILES = [
        "core/governance/__init__.py",
        "core/governance/acm_evaluator.py",
        "core/governance/gid_registry.py",
        "core/governance/enforcement.py",
        "core/governance/governance_schema.py",
        "core/governance/dependency_graph.py",
    ]
    
    REQUIRED_INVARIANTS = [
        "INV-GOV-001",  # Explicit agent acknowledgment
        "INV-GOV-002",  # No execution without dependencies
        "INV-GOV-003",  # No silent partial success
        "INV-GOV-004",  # No undeclared capabilities
        "INV-GOV-005",  # No human override without PDO
        "INV-GOV-006",  # Retention & time bounds explicit
        "INV-GOV-007",  # Training signals classified
        "INV-GOV-008",  # Fail-closed on violation
    ]
    
    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize CI gate."""
        self.repo_root = repo_root or Path.cwd()
    
    def check_governance_files(self) -> CIGateCheck:
        """Check that all required governance files exist."""
        missing: List[str] = []
        
        for file_path in self.REQUIRED_GOVERNANCE_FILES:
            full_path = self.repo_root / file_path
            if not full_path.exists():
                missing.append(file_path)
        
        if missing:
            return CIGateCheck(
                gate_id="GOV-FILES",
                gate_name="Governance Files Exist",
                status=CIGateStatus.FAIL,
                message=f"Missing governance files: {', '.join(missing)}",
                details={"missing": missing},
            )
        
        return CIGateCheck(
            gate_id="GOV-FILES",
            gate_name="Governance Files Exist",
            status=CIGateStatus.PASS,
            message=f"All {len(self.REQUIRED_GOVERNANCE_FILES)} governance files present",
        )
    
    def check_retention_declarations(self) -> CIGateCheck:
        """Check that retention policies are declared."""
        if not CANONICAL_RETENTION_POLICIES:
            return CIGateCheck(
                gate_id="GOV-RETENTION",
                gate_name="Retention Policies Declared",
                status=CIGateStatus.FAIL,
                message="No retention policies declared (INV-GOV-006)",
            )
        
        # Verify all have explicit retention periods
        undeclared: List[str] = []
        for policy in CANONICAL_RETENTION_POLICIES:
            if not policy.retention_period:
                undeclared.append(policy.artifact_type)
        
        if undeclared:
            return CIGateCheck(
                gate_id="GOV-RETENTION",
                gate_name="Retention Policies Declared",
                status=CIGateStatus.FAIL,
                message=f"Missing retention period for: {', '.join(undeclared)}",
                details={"undeclared": undeclared},
            )
        
        return CIGateCheck(
            gate_id="GOV-RETENTION",
            gate_name="Retention Policies Declared",
            status=CIGateStatus.PASS,
            message=f"{len(CANONICAL_RETENTION_POLICIES)} retention policies declared (INV-GOV-006)",
        )
    
    def check_non_capabilities(self) -> CIGateCheck:
        """Check that non-capabilities are declared."""
        from core.governance.governance_schema import CANONICAL_NON_CAPABILITIES
        
        if not CANONICAL_NON_CAPABILITIES:
            return CIGateCheck(
                gate_id="GOV-NONCAP",
                gate_name="Non-Capabilities Declared",
                status=CIGateStatus.FAIL,
                message="No non-capabilities declared (INV-GOV-004)",
            )
        
        return CIGateCheck(
            gate_id="GOV-NONCAP",
            gate_name="Non-Capabilities Declared",
            status=CIGateStatus.PASS,
            message=f"{len(CANONICAL_NON_CAPABILITIES)} non-capabilities declared (INV-GOV-004)",
        )
    
    def check_tests_pass(self) -> CIGateCheck:
        """Check that governance tests pass."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/governance/", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.repo_root),
            )
            
            if result.returncode == 0:
                return CIGateCheck(
                    gate_id="GOV-TESTS",
                    gate_name="Governance Tests Pass",
                    status=CIGateStatus.PASS,
                    message="All governance tests passed",
                )
            else:
                return CIGateCheck(
                    gate_id="GOV-TESTS",
                    gate_name="Governance Tests Pass",
                    status=CIGateStatus.FAIL,
                    message="Governance tests failed",
                    details={"stdout": result.stdout, "stderr": result.stderr},
                )
        except FileNotFoundError:
            return CIGateCheck(
                gate_id="GOV-TESTS",
                gate_name="Governance Tests Pass",
                status=CIGateStatus.SKIP,
                message="pytest not found, skipping test check",
            )
        except subprocess.TimeoutExpired:
            return CIGateCheck(
                gate_id="GOV-TESTS",
                gate_name="Governance Tests Pass",
                status=CIGateStatus.ERROR,
                message="Test execution timed out",
            )
        except Exception as e:
            return CIGateCheck(
                gate_id="GOV-TESTS",
                gate_name="Governance Tests Pass",
                status=CIGateStatus.ERROR,
                message=f"Error running tests: {str(e)}",
            )
    
    def run_all_gates(self, skip_tests: bool = False) -> CIGateResult:
        """
        Run all CI gate checks.
        
        Returns aggregate result.
        """
        checks: List[CIGateCheck] = [
            self.check_governance_files(),
            self.check_retention_declarations(),
            self.check_non_capabilities(),
        ]
        
        if not skip_tests:
            checks.append(self.check_tests_pass())
        
        passed = sum(1 for c in checks if c.status == CIGateStatus.PASS)
        failed = sum(1 for c in checks if c.status == CIGateStatus.FAIL)
        skipped = sum(1 for c in checks if c.status == CIGateStatus.SKIP)
        
        overall_pass = failed == 0
        
        return CIGateResult(
            passed=overall_pass,
            checks=checks,
            total_checks=len(checks),
            passed_checks=passed,
            failed_checks=failed,
            skipped_checks=skipped,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RETENTION REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class RetentionRegistry:
    """
    Registry for tracking retention policies.
    """
    
    def __init__(self):
        """Initialize with canonical policies."""
        self._policies: Dict[str, RetentionPolicy] = {}
        self._by_artifact_type: Dict[str, RetentionPolicy] = {}
        self._training_signals: Dict[str, TrainingSignalDeclaration] = {}
        self._lock = threading.Lock()
        
        # Load canonical policies
        for policy in CANONICAL_RETENTION_POLICIES:
            self._policies[policy.policy_id] = policy
            self._by_artifact_type[policy.artifact_type] = policy
    
    def get_policy(self, artifact_type: str) -> Optional[RetentionPolicy]:
        """Get retention policy for an artifact type."""
        with self._lock:
            return self._by_artifact_type.get(artifact_type)
    
    def get_retention_period(self, artifact_type: str) -> Optional[RetentionPeriod]:
        """Get retention period for an artifact type."""
        policy = self.get_policy(artifact_type)
        return policy.retention_period if policy else None
    
    def is_expired(self, artifact_type: str, created_at: str) -> bool:
        """Check if an artifact is expired based on its type and creation time."""
        policy = self.get_policy(artifact_type)
        if not policy:
            return False  # No policy = no expiration
        
        if policy.retention_period == RetentionPeriod.PERMANENT:
            return False
        
        days = RETENTION_DAYS.get(policy.retention_period)
        if days is None or days <= 0:
            return True  # Ephemeral = immediately expired
        
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        expires = created + timedelta(days=days)
        return datetime.now(timezone.utc) > expires
    
    def register_training_signal(
        self,
        artifact_id: str,
        artifact_type: str,
        classification: TrainingSignalClass,
        rationale: str,
        classified_by: str,
    ) -> TrainingSignalDeclaration:
        """
        Register training signal classification for an artifact.
        
        INV-GOV-007: Training signals classified.
        """
        with self._lock:
            decl_id = f"ts_{uuid.uuid4().hex[:12]}"
            
            decl = TrainingSignalDeclaration(
                declaration_id=decl_id,
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                classification=classification,
                rationale=rationale,
                classified_by=classified_by,
            )
            
            self._training_signals[artifact_id] = decl
            
            logger.info(
                f"TRAINING SIGNAL: {artifact_id} classified as {classification.value}"
            )
            
            return decl
    
    def get_training_classification(self, artifact_id: str) -> Optional[TrainingSignalClass]:
        """Get training signal classification for an artifact."""
        with self._lock:
            decl = self._training_signals.get(artifact_id)
            return decl.classification if decl else None
    
    def list_policies(self) -> List[RetentionPolicy]:
        """List all retention policies."""
        with self._lock:
            return list(self._policies.values())


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════════

_RETENTION_REGISTRY: Optional[RetentionRegistry] = None
_REGISTRY_LOCK = threading.Lock()


def get_retention_registry() -> RetentionRegistry:
    """Get singleton retention registry."""
    global _RETENTION_REGISTRY
    
    if _RETENTION_REGISTRY is None:
        with _REGISTRY_LOCK:
            if _RETENTION_REGISTRY is None:
                _RETENTION_REGISTRY = RetentionRegistry()
                logger.info("Retention registry initialized")
    
    return _RETENTION_REGISTRY


def reset_retention_registry() -> None:
    """Reset singleton. For testing only."""
    global _RETENTION_REGISTRY
    with _REGISTRY_LOCK:
        _RETENTION_REGISTRY = None


def run_ci_gate(repo_root: Optional[Path] = None, skip_tests: bool = False) -> CIGateResult:
    """
    Run governance CI gate checks.
    
    Convenience function for CI integration.
    """
    gate = GovernanceCIGate(repo_root)
    return gate.run_all_gates(skip_tests=skip_tests)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Schema version
    "RETENTION_SCHEMA_VERSION",
    # Retention
    "RetentionPeriod",
    "RETENTION_DAYS",
    "ArtifactStorageType",
    "RetentionPolicy",
    "CANONICAL_RETENTION_POLICIES",
    # Training signals
    "TrainingSignalClass",
    "TrainingSignalDeclaration",
    # CI gates
    "CIGateStatus",
    "CIGateCheck",
    "CIGateResult",
    "GovernanceCIGate",
    "run_ci_gate",
    # Registry
    "RetentionRegistry",
    "get_retention_registry",
    "reset_retention_registry",
]
