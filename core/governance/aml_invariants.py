# ═══════════════════════════════════════════════════════════════════════════════
# AML Invariants — INV-AML Governance Enforcement
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: ALEX (GID-08)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Invariants — INV-AML-* Governance Rules

PURPOSE:
    Define and enforce invariants specific to AML operations:
    - Decision integrity invariants
    - Tier boundary invariants
    - Evidence requirement invariants
    - Audit trail invariants
    - Timing invariants

ENFORCEMENT:
    - All invariants are FAIL-CLOSED
    - Violations block the operation
    - All checks are logged

LANE: GOVERNANCE (INVARIANT ENFORCEMENT)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class InvariantCategory(Enum):
    """Category of AML invariant."""

    DECISION = "DECISION"  # Decision-related rules
    TIER = "TIER"  # Tier classification rules
    EVIDENCE = "EVIDENCE"  # Evidence requirements
    AUDIT = "AUDIT"  # Audit trail requirements
    TIMING = "TIMING"  # Timing constraints
    ACCESS = "ACCESS"  # Access control rules


class InvariantSeverity(Enum):
    """Severity of invariant violation."""

    CRITICAL = "CRITICAL"  # Blocks operation, alerts
    HIGH = "HIGH"  # Blocks operation
    MEDIUM = "MEDIUM"  # Warning, may block
    LOW = "LOW"  # Warning only


class CheckResult(Enum):
    """Result of invariant check."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"  # Not applicable
    ERROR = "ERROR"  # Check failed to execute


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class AMLInvariant:
    """
    AML-specific invariant definition.

    Defines a governance rule that must hold true.
    """

    invariant_id: str
    name: str
    category: InvariantCategory
    severity: InvariantSeverity
    description: str
    condition: str  # Human-readable condition
    error_message: str
    enabled: bool = True
    fail_closed: bool = True  # Block on failure by default

    def __post_init__(self) -> None:
        if not self.invariant_id.startswith("INV-AML-"):
            raise ValueError(f"Invariant ID must start with 'INV-AML-': {self.invariant_id}")

    def compute_invariant_hash(self) -> str:
        """Compute deterministic hash."""
        data = {
            "invariant_id": self.invariant_id,
            "category": self.category.value,
            "condition": self.condition,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "name": self.name,
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "condition": self.condition,
            "error_message": self.error_message,
            "enabled": self.enabled,
            "fail_closed": self.fail_closed,
            "invariant_hash": self.compute_invariant_hash(),
        }


@dataclass
class InvariantCheckResult:
    """
    Result of an invariant check.

    Captures the outcome and context of a check.
    """

    check_id: str
    invariant_id: str
    result: CheckResult
    timestamp: str
    context: Dict[str, Any]
    message: str
    blocked: bool = False
    duration_ms: float = 0.0

    def __post_init__(self) -> None:
        if not self.check_id.startswith("CHK-"):
            raise ValueError(f"Check ID must start with 'CHK-': {self.check_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "invariant_id": self.invariant_id,
            "result": self.result.value,
            "timestamp": self.timestamp,
            "context": self.context,
            "message": self.message,
            "blocked": self.blocked,
            "duration_ms": self.duration_ms,
        }


@dataclass
class InvariantViolation:
    """
    Record of an invariant violation.

    Captures when and how an invariant was violated.
    """

    violation_id: str
    invariant_id: str
    case_id: str
    timestamp: str
    severity: InvariantSeverity
    context: Dict[str, Any]
    action_blocked: bool
    remediation: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.violation_id.startswith("VINV-"):
            raise ValueError(f"Violation ID must start with 'VINV-': {self.violation_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "invariant_id": self.invariant_id,
            "case_id": self.case_id,
            "timestamp": self.timestamp,
            "severity": self.severity.value,
            "context": self.context,
            "action_blocked": self.action_blocked,
            "remediation": self.remediation,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════════


INV_AML_001 = AMLInvariant(
    invariant_id="INV-AML-001",
    name="No Autonomous Tier-2+ Clearance",
    category=InvariantCategory.DECISION,
    severity=InvariantSeverity.CRITICAL,
    description="Cases classified as Tier-2 or above CANNOT be auto-cleared",
    condition="tier >= TIER_2 → decision ≠ AUTO_CLEAR",
    error_message="Attempted to auto-clear a Tier-2+ case",
)

INV_AML_002 = AMLInvariant(
    invariant_id="INV-AML-002",
    name="No Autonomous SAR Filing",
    category=InvariantCategory.DECISION,
    severity=InvariantSeverity.CRITICAL,
    description="SAR filing MUST be performed by a human",
    condition="action = FILE_SAR → actor ≠ SYSTEM",
    error_message="Attempted autonomous SAR filing",
)

INV_AML_003 = AMLInvariant(
    invariant_id="INV-AML-003",
    name="Confidence Threshold for Auto-Clear",
    category=InvariantCategory.DECISION,
    severity=InvariantSeverity.HIGH,
    description="Auto-clearance requires confidence >= 0.95",
    condition="decision = AUTO_CLEAR → confidence >= 0.95",
    error_message="Auto-clearance confidence below threshold",
)

INV_AML_004 = AMLInvariant(
    invariant_id="INV-AML-004",
    name="Sanctions Hit Blocks Clearance",
    category=InvariantCategory.DECISION,
    severity=InvariantSeverity.CRITICAL,
    description="Any sanctions hit MUST block auto-clearance",
    condition="sanctions_hit = TRUE → decision ≠ AUTO_CLEAR",
    error_message="Attempted to auto-clear case with sanctions hit",
)

INV_AML_005 = AMLInvariant(
    invariant_id="INV-AML-005",
    name="Evidence Required for Decision",
    category=InvariantCategory.EVIDENCE,
    severity=InvariantSeverity.HIGH,
    description="All decisions must have supporting evidence",
    condition="has_decision → evidence_count > 0",
    error_message="Decision made without supporting evidence",
)

INV_AML_006 = AMLInvariant(
    invariant_id="INV-AML-006",
    name="Audit Trail Required",
    category=InvariantCategory.AUDIT,
    severity=InvariantSeverity.HIGH,
    description="All decisions must be logged to audit ledger",
    condition="has_decision → audit_entry_exists",
    error_message="Decision not logged to audit trail",
)

INV_AML_007 = AMLInvariant(
    invariant_id="INV-AML-007",
    name="Tier Downgrade Requires Justification",
    category=InvariantCategory.TIER,
    severity=InvariantSeverity.MEDIUM,
    description="Tier downgrades must have documented justification",
    condition="tier_decreased → has_justification",
    error_message="Tier downgrade without justification",
)

INV_AML_008 = AMLInvariant(
    invariant_id="INV-AML-008",
    name="PEP Cases Require Review",
    category=InvariantCategory.DECISION,
    severity=InvariantSeverity.HIGH,
    description="PEP-associated cases cannot be auto-cleared",
    condition="pep_associated = TRUE → decision ≠ AUTO_CLEAR",
    error_message="Attempted to auto-clear PEP-associated case",
)

INV_AML_009 = AMLInvariant(
    invariant_id="INV-AML-009",
    name="Prohibited Jurisdiction Blocks Clearance",
    category=InvariantCategory.DECISION,
    severity=InvariantSeverity.CRITICAL,
    description="Cases involving prohibited jurisdictions cannot be cleared",
    condition="prohibited_jurisdiction = TRUE → decision ≠ AUTO_CLEAR",
    error_message="Attempted to auto-clear case with prohibited jurisdiction",
)

INV_AML_010 = AMLInvariant(
    invariant_id="INV-AML-010",
    name="Case Age SLA Warning",
    category=InvariantCategory.TIMING,
    severity=InvariantSeverity.MEDIUM,
    description="Cases should not remain open beyond SLA",
    condition="case_age_hours < sla_hours",
    error_message="Case exceeds SLA threshold",
    fail_closed=False,  # Warning only
)

INV_AML_011 = AMLInvariant(
    invariant_id="INV-AML-011",
    name="Adverse Media Requires Review",
    category=InvariantCategory.DECISION,
    severity=InvariantSeverity.HIGH,
    description="Cases with adverse media cannot be auto-cleared",
    condition="adverse_media_hit = TRUE → decision ≠ AUTO_CLEAR",
    error_message="Attempted to auto-clear case with adverse media",
)

INV_AML_012 = AMLInvariant(
    invariant_id="INV-AML-012",
    name="Narrative Required for Escalation",
    category=InvariantCategory.EVIDENCE,
    severity=InvariantSeverity.MEDIUM,
    description="Escalations must include narrative explanation",
    condition="decision = ESCALATE → has_narrative",
    error_message="Escalation without narrative",
)


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class AMLInvariantEngine:
    """
    AML Invariant enforcement engine.

    Provides:
    - Invariant registration and management
    - Invariant checking with fail-closed semantics
    - Violation recording
    - Batch checking support
    """

    def __init__(self) -> None:
        self._invariants: Dict[str, AMLInvariant] = {}
        self._violations: List[InvariantViolation] = []
        self._checks: List[InvariantCheckResult] = []
        self._check_counter = 0
        self._violation_counter = 0
        self._checkers: Dict[str, Callable[[Dict[str, Any]], bool]] = {}

        # Load defaults
        self._load_defaults()
        self._register_checkers()

    def _load_defaults(self) -> None:
        """Load default invariants."""
        for inv in [
            INV_AML_001,
            INV_AML_002,
            INV_AML_003,
            INV_AML_004,
            INV_AML_005,
            INV_AML_006,
            INV_AML_007,
            INV_AML_008,
            INV_AML_009,
            INV_AML_010,
            INV_AML_011,
            INV_AML_012,
        ]:
            self._invariants[inv.invariant_id] = inv

    def _register_checkers(self) -> None:
        """Register invariant checker functions."""
        self._checkers["INV-AML-001"] = self._check_no_tier2_auto_clear
        self._checkers["INV-AML-002"] = self._check_no_auto_sar
        self._checkers["INV-AML-003"] = self._check_confidence_threshold
        self._checkers["INV-AML-004"] = self._check_sanctions_block
        self._checkers["INV-AML-005"] = self._check_evidence_required
        self._checkers["INV-AML-006"] = self._check_audit_required
        self._checkers["INV-AML-007"] = self._check_tier_downgrade
        self._checkers["INV-AML-008"] = self._check_pep_review
        self._checkers["INV-AML-009"] = self._check_prohibited_jurisdiction
        self._checkers["INV-AML-010"] = self._check_sla
        self._checkers["INV-AML-011"] = self._check_adverse_media
        self._checkers["INV-AML-012"] = self._check_escalation_narrative

    # ───────────────────────────────────────────────────────────────────────────
    # CHECKER IMPLEMENTATIONS
    # ───────────────────────────────────────────────────────────────────────────

    def _check_no_tier2_auto_clear(self, context: Dict[str, Any]) -> bool:
        """Check INV-AML-001: No Tier-2+ auto-clearance."""
        tier = context.get("tier", "")
        decision = context.get("decision", "")
        if tier in ["TIER_2", "TIER_3", "TIER_SAR"]:
            return decision != "AUTO_CLEAR"
        return True

    def _check_no_auto_sar(self, context: Dict[str, Any]) -> bool:
        """Check INV-AML-002: No autonomous SAR filing."""
        action = context.get("action", "")
        actor = context.get("actor", "")
        if action == "FILE_SAR":
            return actor != "SYSTEM"
        return True

    def _check_confidence_threshold(self, context: Dict[str, Any]) -> bool:
        """Check INV-AML-003: Confidence threshold."""
        decision = context.get("decision", "")
        confidence = context.get("confidence", 1.0)
        if decision == "AUTO_CLEAR":
            return confidence >= 0.95
        return True

    def _check_sanctions_block(self, context: Dict[str, Any]) -> bool:
        """Check INV-AML-004: Sanctions hit blocks clearance."""
        sanctions_hit = context.get("sanctions_hit", False)
        decision = context.get("decision", "")
        if sanctions_hit:
            return decision != "AUTO_CLEAR"
        return True

    def _check_evidence_required(self, context: Dict[str, Any]) -> bool:
        """Check INV-AML-005: Evidence required for decision."""
        has_decision = context.get("has_decision", False)
        evidence_count = context.get("evidence_count", 0)
        if has_decision:
            return evidence_count > 0
        return True

    def _check_audit_required(self, context: Dict[str, Any]) -> bool:
        """Check INV-AML-006: Audit trail required."""
        has_decision = context.get("has_decision", False)
        audit_entry_exists = context.get("audit_entry_exists", True)
        if has_decision:
            return audit_entry_exists
        return True

    def _check_tier_downgrade(self, context: Dict[str, Any]) -> bool:
        """Check INV-AML-007: Tier downgrade requires justification."""
        tier_decreased = context.get("tier_decreased", False)
        has_justification = context.get("has_justification", True)
        if tier_decreased:
            return has_justification
        return True

    def _check_pep_review(self, context: Dict[str, Any]) -> bool:
        """Check INV-AML-008: PEP cases require review."""
        pep_associated = context.get("pep_associated", False)
        decision = context.get("decision", "")
        if pep_associated:
            return decision != "AUTO_CLEAR"
        return True

    def _check_prohibited_jurisdiction(self, context: Dict[str, Any]) -> bool:
        """Check INV-AML-009: Prohibited jurisdiction blocks clearance."""
        prohibited = context.get("prohibited_jurisdiction", False)
        decision = context.get("decision", "")
        if prohibited:
            return decision != "AUTO_CLEAR"
        return True

    def _check_sla(self, context: Dict[str, Any]) -> bool:
        """Check INV-AML-010: Case age SLA."""
        case_age_hours = context.get("case_age_hours", 0)
        sla_hours = context.get("sla_hours", 72)  # Default 72 hour SLA
        return case_age_hours < sla_hours

    def _check_adverse_media(self, context: Dict[str, Any]) -> bool:
        """Check INV-AML-011: Adverse media requires review."""
        adverse_media_hit = context.get("adverse_media_hit", False)
        decision = context.get("decision", "")
        if adverse_media_hit:
            return decision != "AUTO_CLEAR"
        return True

    def _check_escalation_narrative(self, context: Dict[str, Any]) -> bool:
        """Check INV-AML-012: Escalation requires narrative."""
        decision = context.get("decision", "")
        has_narrative = context.get("has_narrative", True)
        if decision == "ESCALATE":
            return has_narrative
        return True

    # ───────────────────────────────────────────────────────────────────────────
    # INVARIANT CHECKING
    # ───────────────────────────────────────────────────────────────────────────

    def check_invariant(
        self,
        invariant_id: str,
        context: Dict[str, Any],
        case_id: Optional[str] = None,
    ) -> InvariantCheckResult:
        """
        Check a single invariant.

        Args:
            invariant_id: ID of invariant to check
            context: Context data for check
            case_id: Optional case ID for violation recording

        Returns:
            Check result
        """
        import time

        start_time = time.time()
        self._check_counter += 1
        check_id = f"CHK-{self._check_counter:08d}"

        invariant = self._invariants.get(invariant_id)
        if invariant is None:
            return InvariantCheckResult(
                check_id=check_id,
                invariant_id=invariant_id,
                result=CheckResult.ERROR,
                timestamp=datetime.now(timezone.utc).isoformat(),
                context=context,
                message=f"Unknown invariant: {invariant_id}",
            )

        if not invariant.enabled:
            return InvariantCheckResult(
                check_id=check_id,
                invariant_id=invariant_id,
                result=CheckResult.SKIP,
                timestamp=datetime.now(timezone.utc).isoformat(),
                context=context,
                message="Invariant disabled",
            )

        checker = self._checkers.get(invariant_id)
        if checker is None:
            return InvariantCheckResult(
                check_id=check_id,
                invariant_id=invariant_id,
                result=CheckResult.ERROR,
                timestamp=datetime.now(timezone.utc).isoformat(),
                context=context,
                message="No checker registered",
            )

        try:
            passed = checker(context)
            duration_ms = (time.time() - start_time) * 1000

            result = InvariantCheckResult(
                check_id=check_id,
                invariant_id=invariant_id,
                result=CheckResult.PASS if passed else CheckResult.FAIL,
                timestamp=datetime.now(timezone.utc).isoformat(),
                context=context,
                message="" if passed else invariant.error_message,
                blocked=not passed and invariant.fail_closed,
                duration_ms=duration_ms,
            )

            # Record violation if failed
            if not passed and case_id:
                self._record_violation(invariant, case_id, context)

            self._checks.append(result)
            return result

        except Exception as e:
            return InvariantCheckResult(
                check_id=check_id,
                invariant_id=invariant_id,
                result=CheckResult.ERROR,
                timestamp=datetime.now(timezone.utc).isoformat(),
                context=context,
                message=f"Check error: {str(e)}",
            )

    def check_all(
        self,
        context: Dict[str, Any],
        case_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check all enabled invariants.

        Returns summary with pass/fail counts and any blocking violations.
        """
        results: List[InvariantCheckResult] = []
        blocking_violations: List[str] = []

        for invariant_id in self._invariants:
            result = self.check_invariant(invariant_id, context, case_id)
            results.append(result)
            if result.blocked:
                blocking_violations.append(invariant_id)

        passed = sum(1 for r in results if r.result == CheckResult.PASS)
        failed = sum(1 for r in results if r.result == CheckResult.FAIL)
        skipped = sum(1 for r in results if r.result == CheckResult.SKIP)
        errors = sum(1 for r in results if r.result == CheckResult.ERROR)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "case_id": case_id,
            "total_checks": len(results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
            "all_passed": failed == 0 and errors == 0,
            "blocked": len(blocking_violations) > 0,
            "blocking_violations": blocking_violations,
            "results": [r.to_dict() for r in results],
        }

    def check_clearance_decision(
        self,
        case_id: str,
        tier: str,
        decision: str,
        confidence: float,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check invariants specific to clearance decisions.

        Convenience method for decision-time checks.
        """
        full_context = {
            "tier": tier,
            "decision": decision,
            "confidence": confidence,
            "has_decision": True,
            **context,
        }

        # Check decision-relevant invariants
        relevant_ids = [
            "INV-AML-001",  # No Tier-2+ auto-clear
            "INV-AML-003",  # Confidence threshold
            "INV-AML-004",  # Sanctions block
            "INV-AML-005",  # Evidence required
            "INV-AML-008",  # PEP review
            "INV-AML-009",  # Prohibited jurisdiction
            "INV-AML-011",  # Adverse media
        ]

        results: List[InvariantCheckResult] = []
        blocking: List[str] = []

        for inv_id in relevant_ids:
            result = self.check_invariant(inv_id, full_context, case_id)
            results.append(result)
            if result.blocked:
                blocking.append(inv_id)

        return {
            "case_id": case_id,
            "decision_allowed": len(blocking) == 0,
            "blocking_invariants": blocking,
            "results": [r.to_dict() for r in results],
        }

    def _record_violation(
        self,
        invariant: AMLInvariant,
        case_id: str,
        context: Dict[str, Any],
    ) -> InvariantViolation:
        """Record an invariant violation."""
        self._violation_counter += 1
        violation = InvariantViolation(
            violation_id=f"VINV-{self._violation_counter:08d}",
            invariant_id=invariant.invariant_id,
            case_id=case_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity=invariant.severity,
            context=context,
            action_blocked=invariant.fail_closed,
        )
        self._violations.append(violation)
        return violation

    # ───────────────────────────────────────────────────────────────────────────
    # QUERIES
    # ───────────────────────────────────────────────────────────────────────────

    def get_invariant(self, invariant_id: str) -> Optional[AMLInvariant]:
        """Get invariant by ID."""
        return self._invariants.get(invariant_id)

    def list_invariants(self) -> List[AMLInvariant]:
        """List all invariants."""
        return list(self._invariants.values())

    def list_violations(self) -> List[InvariantViolation]:
        """List all violations."""
        return self._violations.copy()

    def get_violations_for_case(self, case_id: str) -> List[InvariantViolation]:
        """Get violations for a specific case."""
        return [v for v in self._violations if v.case_id == case_id]

    def get_critical_violations(self) -> List[InvariantViolation]:
        """Get critical severity violations."""
        return [v for v in self._violations if v.severity == InvariantSeverity.CRITICAL]

    # ───────────────────────────────────────────────────────────────────────────
    # REPORTING
    # ───────────────────────────────────────────────────────────────────────────

    def generate_report(self) -> Dict[str, Any]:
        """Generate invariant status report."""
        violations_by_invariant: Dict[str, int] = {}
        for inv_id in self._invariants:
            violations_by_invariant[inv_id] = len([
                v for v in self._violations if v.invariant_id == inv_id
            ])

        violations_by_severity: Dict[str, int] = {}
        for severity in InvariantSeverity:
            violations_by_severity[severity.value] = len([
                v for v in self._violations if v.severity == severity
            ])

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_invariants": len(self._invariants),
            "enabled_invariants": len([i for i in self._invariants.values() if i.enabled]),
            "total_checks": len(self._checks),
            "total_violations": len(self._violations),
            "blocked_actions": len([v for v in self._violations if v.action_blocked]),
            "violations_by_invariant": violations_by_invariant,
            "violations_by_severity": violations_by_severity,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "InvariantCategory",
    "InvariantSeverity",
    "CheckResult",
    # Data Classes
    "AMLInvariant",
    "InvariantCheckResult",
    "InvariantViolation",
    # Service
    "AMLInvariantEngine",
    # Default Invariants
    "INV_AML_001",
    "INV_AML_002",
    "INV_AML_003",
    "INV_AML_004",
    "INV_AML_005",
    "INV_AML_006",
    "INV_AML_007",
    "INV_AML_008",
    "INV_AML_009",
    "INV_AML_010",
    "INV_AML_011",
    "INV_AML_012",
]
