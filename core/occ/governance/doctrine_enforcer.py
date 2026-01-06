"""
Doctrine Enforcement Module

PAC Reference: PAC-JEFFREY-P47
Governance Mode: HARD / FAIL-CLOSED

Implements mechanical enforcement of Structural Advantage Doctrine.
ALEX (GID-08) uses this module for doctrine compliance verification.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable
import json


class DoctrineID(Enum):
    """Doctrine identifiers from PAC-JEFFREY-P47."""
    
    DOC_001 = "DOC-001"  # Infinite Test Suite
    DOC_002 = "DOC-002"  # Chaos Coverage Index
    DOC_003 = "DOC-003"  # 100% Audit Zero Sampling
    DOC_004 = "DOC-004"  # Universal Adapter Principle
    DOC_005 = "DOC-005"  # Operator Console Supremacy
    DOC_006 = "DOC-006"  # Fail-Closed as Revenue Strategy
    DOC_007 = "DOC-007"  # AI Labor Overhead Arbitrage


class ViolationSeverity(Enum):
    """Severity levels for doctrine violations."""
    
    CRITICAL = "CRITICAL"  # Blocks execution immediately
    HIGH = "HIGH"          # Blocks merge
    MEDIUM = "MEDIUM"      # Generates alert
    LOW = "LOW"            # Logged for review


class EnforcementAction(Enum):
    """Actions taken on doctrine violation."""
    
    BLOCK_MERGE = "BLOCK_MERGE"
    BLOCK_EXECUTION = "BLOCK_EXECUTION"
    ROLLBACK = "ROLLBACK"
    ALERT = "ALERT"
    INCIDENT_REPORT = "INCIDENT_REPORT"
    LOG = "LOG"


@dataclass
class DoctrineViolation:
    """Represents a doctrine violation."""
    
    doctrine_id: DoctrineID
    description: str
    severity: ViolationSeverity
    action: EnforcementAction
    context: Dict
    timestamp: datetime
    resolved: bool = False
    resolution: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "doctrine_id": self.doctrine_id.value,
            "description": self.description,
            "severity": self.severity.value,
            "action": self.action.value,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolution": self.resolution
        }


@dataclass
class DoctrineCheckResult:
    """Result of a doctrine compliance check."""
    
    doctrine_id: DoctrineID
    passed: bool
    message: str
    details: Optional[Dict] = None
    
    def to_dict(self) -> dict:
        return {
            "doctrine_id": self.doctrine_id.value,
            "passed": self.passed,
            "message": self.message,
            "details": self.details
        }


class DoctrineEnforcer:
    """
    Mechanical enforcement of Structural Advantage Doctrine.
    
    Used by ALEX (GID-08) to verify doctrine compliance.
    Violations trigger FAIL-CLOSED per governance mode.
    """
    
    def __init__(self):
        self._violations: List[DoctrineViolation] = []
        self._check_registry: Dict[DoctrineID, Callable[[], DoctrineCheckResult]] = {}
        self._baseline_test_count: Optional[int] = None
    
    def register_check(
        self,
        doctrine_id: DoctrineID,
        check_fn: Callable[[], DoctrineCheckResult]
    ) -> None:
        """Register a compliance check function for a doctrine."""
        self._check_registry[doctrine_id] = check_fn
    
    def set_test_baseline(self, count: int) -> None:
        """Set baseline test count for DOC-001 monotonicity."""
        self._baseline_test_count = count
    
    def check_test_regression(self, current_count: int) -> DoctrineCheckResult:
        """
        DOC-001: Infinite Test Suite - No test regression allowed.
        
        Invariant: NO TEST REGRESSION → NO MERGE → NO PAC
        """
        if self._baseline_test_count is None:
            return DoctrineCheckResult(
                doctrine_id=DoctrineID.DOC_001,
                passed=True,
                message="No baseline set",
                details={"current_count": current_count}
            )
        
        if current_count < self._baseline_test_count:
            self._record_violation(
                doctrine_id=DoctrineID.DOC_001,
                description=(
                    f"Test regression detected: {self._baseline_test_count} → {current_count}. "
                    f"Lost {self._baseline_test_count - current_count} tests."
                ),
                severity=ViolationSeverity.CRITICAL,
                action=EnforcementAction.BLOCK_MERGE,
                context={
                    "baseline": self._baseline_test_count,
                    "current": current_count,
                    "delta": current_count - self._baseline_test_count
                }
            )
            return DoctrineCheckResult(
                doctrine_id=DoctrineID.DOC_001,
                passed=False,
                message=f"TEST REGRESSION: {self._baseline_test_count} → {current_count}",
                details={
                    "baseline": self._baseline_test_count,
                    "current": current_count,
                    "action": "BLOCK_MERGE"
                }
            )
        
        return DoctrineCheckResult(
            doctrine_id=DoctrineID.DOC_001,
            passed=True,
            message=f"Test count maintained: {self._baseline_test_count} → {current_count}",
            details={
                "baseline": self._baseline_test_count,
                "current": current_count,
                "delta": current_count - self._baseline_test_count
            }
        )
    
    def check_audit_coverage(self, audited_count: int, total_count: int) -> DoctrineCheckResult:
        """
        DOC-003: 100% Audit Zero Sampling.
        
        Invariant: IF NOT REPLAYABLE → NOT EXECUTED
        """
        if total_count == 0:
            return DoctrineCheckResult(
                doctrine_id=DoctrineID.DOC_003,
                passed=True,
                message="No transactions to audit",
                details={"audited": 0, "total": 0, "percentage": 100.0}
            )
        
        percentage = (audited_count / total_count) * 100
        
        if percentage < 100.0:
            self._record_violation(
                doctrine_id=DoctrineID.DOC_003,
                description=f"Audit gap detected: {percentage:.2f}% coverage (requires 100%)",
                severity=ViolationSeverity.CRITICAL,
                action=EnforcementAction.BLOCK_EXECUTION,
                context={
                    "audited": audited_count,
                    "total": total_count,
                    "percentage": percentage,
                    "gap": total_count - audited_count
                }
            )
            return DoctrineCheckResult(
                doctrine_id=DoctrineID.DOC_003,
                passed=False,
                message=f"AUDIT GAP: {percentage:.2f}% < 100%",
                details={
                    "audited": audited_count,
                    "total": total_count,
                    "gap": total_count - audited_count,
                    "action": "BLOCK_EXECUTION"
                }
            )
        
        return DoctrineCheckResult(
            doctrine_id=DoctrineID.DOC_003,
            passed=True,
            message="100% audit coverage verified",
            details={"audited": audited_count, "total": total_count, "percentage": 100.0}
        )
    
    def check_visibility(self, visible_states: int, total_states: int) -> DoctrineCheckResult:
        """
        DOC-005: Operator Console Supremacy.
        
        Invariant: IF OPERATOR CANNOT SEE IT → IT CANNOT EXECUTE
        """
        if total_states == 0:
            return DoctrineCheckResult(
                doctrine_id=DoctrineID.DOC_005,
                passed=True,
                message="No states to verify visibility",
                details={"visible": 0, "total": 0, "percentage": 100.0}
            )
        
        percentage = (visible_states / total_states) * 100
        
        if percentage < 100.0:
            self._record_violation(
                doctrine_id=DoctrineID.DOC_005,
                description=f"Visibility gap detected: {percentage:.2f}% visible (requires 100%)",
                severity=ViolationSeverity.CRITICAL,
                action=EnforcementAction.BLOCK_EXECUTION,
                context={
                    "visible": visible_states,
                    "total": total_states,
                    "percentage": percentage,
                    "hidden": total_states - visible_states
                }
            )
            return DoctrineCheckResult(
                doctrine_id=DoctrineID.DOC_005,
                passed=False,
                message=f"VISIBILITY GAP: {percentage:.2f}% < 100%",
                details={
                    "visible": visible_states,
                    "total": total_states,
                    "hidden": total_states - visible_states,
                    "action": "BLOCK_EXECUTION"
                }
            )
        
        return DoctrineCheckResult(
            doctrine_id=DoctrineID.DOC_005,
            passed=True,
            message="100% state visibility verified",
            details={"visible": visible_states, "total": total_states, "percentage": 100.0}
        )
    
    def check_fail_closed(self, ambiguous_outcomes: int) -> DoctrineCheckResult:
        """
        DOC-006: Fail-Closed as Revenue Strategy.
        
        Invariant: AMBIGUITY DEFAULTS TO STOP NOT GO
        """
        if ambiguous_outcomes > 0:
            self._record_violation(
                doctrine_id=DoctrineID.DOC_006,
                description=f"Ambiguous outcomes detected: {ambiguous_outcomes}",
                severity=ViolationSeverity.HIGH,
                action=EnforcementAction.ROLLBACK,
                context={"ambiguous_count": ambiguous_outcomes}
            )
            return DoctrineCheckResult(
                doctrine_id=DoctrineID.DOC_006,
                passed=False,
                message=f"AMBIGUOUS OUTCOMES: {ambiguous_outcomes}",
                details={
                    "ambiguous_count": ambiguous_outcomes,
                    "action": "ROLLBACK"
                }
            )
        
        return DoctrineCheckResult(
            doctrine_id=DoctrineID.DOC_006,
            passed=True,
            message="No ambiguous outcomes",
            details={"ambiguous_count": 0}
        )
    
    def _record_violation(
        self,
        doctrine_id: DoctrineID,
        description: str,
        severity: ViolationSeverity,
        action: EnforcementAction,
        context: Dict
    ) -> DoctrineViolation:
        """Record a doctrine violation."""
        violation = DoctrineViolation(
            doctrine_id=doctrine_id,
            description=description,
            severity=severity,
            action=action,
            context=context,
            timestamp=datetime.utcnow()
        )
        self._violations.append(violation)
        return violation
    
    def get_violations(self, unresolved_only: bool = False) -> List[DoctrineViolation]:
        """Get recorded violations."""
        if unresolved_only:
            return [v for v in self._violations if not v.resolved]
        return list(self._violations)
    
    def get_blocking_violations(self) -> List[DoctrineViolation]:
        """Get violations that block merge or execution."""
        blocking_actions = {
            EnforcementAction.BLOCK_MERGE,
            EnforcementAction.BLOCK_EXECUTION,
            EnforcementAction.ROLLBACK
        }
        return [
            v for v in self._violations
            if not v.resolved and v.action in blocking_actions
        ]
    
    def is_execution_allowed(self) -> tuple[bool, str]:
        """Check if execution is allowed (no blocking violations)."""
        blocking = self.get_blocking_violations()
        if blocking:
            descriptions = [v.description for v in blocking]
            return False, f"Execution blocked: {'; '.join(descriptions)}"
        return True, "Execution allowed"
    
    def run_all_checks(self) -> Dict[DoctrineID, DoctrineCheckResult]:
        """Run all registered doctrine checks."""
        results = {}
        for doctrine_id, check_fn in self._check_registry.items():
            results[doctrine_id] = check_fn()
        return results
    
    def get_compliance_report(self) -> dict:
        """Generate comprehensive compliance report."""
        blocking = self.get_blocking_violations()
        all_violations = self.get_violations()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "execution_allowed": len(blocking) == 0,
            "total_violations": len(all_violations),
            "blocking_violations": len(blocking),
            "unresolved_violations": len([v for v in all_violations if not v.resolved]),
            "violations": [v.to_dict() for v in all_violations],
            "doctrine_status": {
                d.value: "COMPLIANT" if d not in [v.doctrine_id for v in blocking] else "VIOLATION"
                for d in DoctrineID
            }
        }
    
    def to_json(self) -> str:
        """Serialize compliance state to JSON."""
        return json.dumps(self.get_compliance_report(), indent=2)


# Global enforcer instance
_enforcer_instance: Optional[DoctrineEnforcer] = None


def get_doctrine_enforcer() -> DoctrineEnforcer:
    """Get or create the global doctrine enforcer."""
    global _enforcer_instance
    if _enforcer_instance is None:
        _enforcer_instance = DoctrineEnforcer()
    return _enforcer_instance


def reset_doctrine_enforcer() -> None:
    """Reset the global enforcer (for testing)."""
    global _enforcer_instance
    _enforcer_instance = None


def check_doctrine_gate() -> tuple[bool, str]:
    """
    Doctrine gate check for CI/execution.
    
    Returns:
        (gate_passed, message)
    """
    enforcer = get_doctrine_enforcer()
    return enforcer.is_execution_allowed()


def get_compliance_report() -> dict:
    """Get compliance report for OCC dashboard."""
    enforcer = get_doctrine_enforcer()
    return enforcer.get_compliance_report()
