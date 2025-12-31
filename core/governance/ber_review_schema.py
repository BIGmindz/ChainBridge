"""
BER Review Schema v1

Typed schema definitions for BER review checklist execution.
Per PAC-BENSON-EXEC-GOVERNANCE-JEFFREY-REVIEW-LAW-022.

This module defines the data structures for:
- Individual check results
- Review outcomes
- Training signals
- Failure modes
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class CheckID(str, Enum):
    """Canonical check identifiers per BER_REVIEW_CHECKLIST_v1."""
    
    CHK_001 = "CHK-001"  # Authority Verification
    CHK_002 = "CHK-002"  # Loop Closure Verification
    CHK_003 = "CHK-003"  # PDO Chain Verification
    CHK_004 = "CHK-004"  # Emission Verification
    CHK_005 = "CHK-005"  # Decision Validity
    CHK_006 = "CHK-006"  # Training Signal Presence
    CHK_007 = "CHK-007"  # Artifact Integrity
    CHK_008 = "CHK-008"  # Temporal Ordering


class FailureMode(str, Enum):
    """Failure mode classifications per JEFFREY_REVIEW_LAW_v1."""
    
    # Authority failures
    AUTHORITY_VIOLATION = "AUTHORITY_VIOLATION"
    
    # Loop failures
    ORPHAN_BER = "ORPHAN_BER"
    MISSING_WRAP = "MISSING_WRAP"
    
    # PDO failures
    PDO_MISSING = "PDO_MISSING"
    PDO_INCOMPLETE = "PDO_INCOMPLETE"
    PDO_HASH_MISMATCH = "PDO_HASH_MISMATCH"
    
    # Emission failures
    EMISSION_VIOLATION = "EMISSION_VIOLATION"
    
    # Decision failures
    INVALID_DECISION = "INVALID_DECISION"
    
    # Training signal failures
    MISSING_TRAINING_SIGNAL = "MISSING_TRAINING_SIGNAL"
    
    # Integrity failures
    ARTIFACT_TAMPERED = "ARTIFACT_TAMPERED"
    
    # Temporal failures
    TEMPORAL_VIOLATION = "TEMPORAL_VIOLATION"
    
    # Jeffrey-specific violations
    NARRATIVE_APPROVAL = "NARRATIVE_APPROVAL"
    PARTIAL_ACCEPTANCE = "PARTIAL_ACCEPTANCE"
    CONVERSATIONAL_DRIFT = "CONVERSATIONAL_DRIFT"
    EXECUTION_BREACH = "EXECUTION_BREACH"
    SILENT_STATE = "SILENT_STATE"
    ARTIFACT_MUTATION = "ARTIFACT_MUTATION"
    ROLE_VIOLATION = "ROLE_VIOLATION"


class ReviewOutcome(str, Enum):
    """Binary review outcomes only."""
    
    PASS = "PASS"
    FAIL = "FAIL"


class JeffreyAction(str, Enum):
    """Actions Jeffrey may take after BER review."""
    
    NEXT_PAC = "NEXT_PAC"
    CORRECTIVE_PAC = "CORRECTIVE_PAC"


class CheckSeverity(str, Enum):
    """Severity levels for check failures."""
    
    CRITICAL = "CRITICAL"  # Blocks progression
    WARNING = "WARNING"    # Alerts but may not block in v1


# ═══════════════════════════════════════════════════════════════════════════════
# CHECK RESULT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class CheckResult:
    """
    Result of a single checklist item.
    
    Immutable to prevent post-review modification.
    """
    
    check_id: str
    passed: bool
    reason: str = ""
    failure_mode: Optional[FailureMode] = None
    severity: CheckSeverity = CheckSeverity.CRITICAL
    
    def __post_init__(self) -> None:
        """Validate check result consistency."""
        if not self.passed and not self.reason:
            object.__setattr__(
                self, 'reason', 
                f"Check {self.check_id} failed without reason"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# REVIEW RESULT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class BERReviewResult:
    """
    Complete result of BER review checklist execution.
    
    Immutable to prevent post-review modification.
    Binary outcome only per JEFFREY_REVIEW_LAW_v1.
    """
    
    ber_id: str
    pac_id: str
    outcome: ReviewOutcome
    checks: tuple  # Tuple[CheckResult, ...] - immutable
    failure_reasons: tuple  # Tuple[str, ...] - immutable
    review_timestamp: datetime
    reviewer: str = "JEFFREY"
    
    @property
    def passed(self) -> bool:
        """All checks passed."""
        return self.outcome == ReviewOutcome.PASS
    
    @property
    def requires_corrective_pac(self) -> bool:
        """CORRECTIVE_PAC required when review fails."""
        return not self.passed
    
    @property
    def allows_next_pac(self) -> bool:
        """NEXT_PAC allowed only when all checks pass."""
        return self.passed
    
    @property
    def recommended_action(self) -> JeffreyAction:
        """Binary action recommendation."""
        return JeffreyAction.NEXT_PAC if self.passed else JeffreyAction.CORRECTIVE_PAC
    
    @property
    def check_count(self) -> int:
        """Number of checks executed."""
        return len(self.checks)
    
    @property
    def passed_count(self) -> int:
        """Number of checks that passed."""
        return sum(1 for c in self.checks if c.passed)
    
    @property
    def failed_count(self) -> int:
        """Number of checks that failed."""
        return sum(1 for c in self.checks if not c.passed)
    
    def get_failed_checks(self) -> List[CheckResult]:
        """Return all failed checks."""
        return [c for c in self.checks if not c.passed]
    
    def get_critical_failures(self) -> List[CheckResult]:
        """Return only critical failures."""
        return [
            c for c in self.checks 
            if not c.passed and c.severity == CheckSeverity.CRITICAL
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING SIGNAL
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class JeffreyTrainingSignal:
    """
    Training signal emitted after every BER review.
    
    Per JEFFREY_REVIEW_LAW_v1 Section 6.
    """
    
    pac_id: str
    ber_id: str
    outcome: JeffreyAction
    ber_decision: str
    review_passed: bool
    failure_reasons: tuple  # Tuple[str, ...] - immutable
    timestamp: datetime
    signal_hash: str = ""
    
    def __post_init__(self) -> None:
        """Compute signal hash if not provided."""
        if not self.signal_hash:
            import hashlib
            content = f"{self.pac_id}:{self.ber_id}:{self.outcome}:{self.timestamp.isoformat()}"
            computed = hashlib.sha256(content.encode()).hexdigest()[:16]
            object.__setattr__(self, 'signal_hash', computed)


# ═══════════════════════════════════════════════════════════════════════════════
# CHECK DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class CheckDefinition:
    """
    Definition of a single checklist item.
    
    Used to document and enumerate all required checks.
    """
    
    check_id: CheckID
    name: str
    description: str
    severity: CheckSeverity
    failure_mode: FailureMode


# Canonical check definitions
CHECKLIST_DEFINITIONS: tuple = (
    CheckDefinition(
        check_id=CheckID.CHK_001,
        name="Authority Verification",
        description="Verify BER was issued by GID-00",
        severity=CheckSeverity.CRITICAL,
        failure_mode=FailureMode.AUTHORITY_VIOLATION,
    ),
    CheckDefinition(
        check_id=CheckID.CHK_002,
        name="Loop Closure Verification",
        description="Verify BER closes a valid PAC→WRAP→BER loop",
        severity=CheckSeverity.CRITICAL,
        failure_mode=FailureMode.ORPHAN_BER,
    ),
    CheckDefinition(
        check_id=CheckID.CHK_003,
        name="PDO Chain Verification",
        description="Verify PDO artifact exists and is hash-bound",
        severity=CheckSeverity.CRITICAL,
        failure_mode=FailureMode.PDO_MISSING,
    ),
    CheckDefinition(
        check_id=CheckID.CHK_004,
        name="Emission Verification",
        description="Verify BER was emitted, not just issued",
        severity=CheckSeverity.CRITICAL,
        failure_mode=FailureMode.EMISSION_VIOLATION,
    ),
    CheckDefinition(
        check_id=CheckID.CHK_005,
        name="Decision Validity",
        description="Verify BER decision is a valid enum value",
        severity=CheckSeverity.CRITICAL,
        failure_mode=FailureMode.INVALID_DECISION,
    ),
    CheckDefinition(
        check_id=CheckID.CHK_006,
        name="Training Signal Presence",
        description="Verify training signal present for CORRECTIVE BERs",
        severity=CheckSeverity.WARNING,
        failure_mode=FailureMode.MISSING_TRAINING_SIGNAL,
    ),
    CheckDefinition(
        check_id=CheckID.CHK_007,
        name="Artifact Integrity",
        description="Verify BER artifact has not been tampered with",
        severity=CheckSeverity.CRITICAL,
        failure_mode=FailureMode.ARTIFACT_TAMPERED,
    ),
    CheckDefinition(
        check_id=CheckID.CHK_008,
        name="Temporal Ordering",
        description="Verify timestamps are in valid chronological order",
        severity=CheckSeverity.WARNING,
        failure_mode=FailureMode.TEMPORAL_VIOLATION,
    ),
)

# Required check count
REQUIRED_CHECK_COUNT = len(CHECKLIST_DEFINITIONS)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def validate_review_completeness(result: BERReviewResult) -> bool:
    """
    Validate that a review executed all required checks.
    
    Per BER_REVIEW_CHECKLIST_v1 Section 8: Skipping checks is prohibited.
    """
    return result.check_count >= REQUIRED_CHECK_COUNT


def validate_binary_outcome(result: BERReviewResult) -> bool:
    """
    Validate that review produced a binary outcome.
    
    Per JEFFREY_REVIEW_LAW_v1 INV-JEFF-001: Binary outcome only.
    """
    return result.outcome in (ReviewOutcome.PASS, ReviewOutcome.FAIL)


def get_check_by_id(check_id: str) -> Optional[CheckDefinition]:
    """Get check definition by ID."""
    for defn in CHECKLIST_DEFINITIONS:
        if defn.check_id.value == check_id:
            return defn
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════


__all__ = [
    # Enums
    "CheckID",
    "FailureMode",
    "ReviewOutcome",
    "JeffreyAction",
    "CheckSeverity",
    # Data classes
    "CheckResult",
    "BERReviewResult",
    "JeffreyTrainingSignal",
    "CheckDefinition",
    # Constants
    "CHECKLIST_DEFINITIONS",
    "REQUIRED_CHECK_COUNT",
    # Helpers
    "validate_review_completeness",
    "validate_binary_outcome",
    "get_check_by_id",
]
