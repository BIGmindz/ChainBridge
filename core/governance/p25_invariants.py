# ═══════════════════════════════════════════════════════════════════════════════
# P25 Invariant Definitions — SOP, Risk, UI-State
# PAC-BENSON-P25: PARALLEL PLATFORM EXPANSION & OPERATOR-GRADE EXECUTION
# Agent: ALEX (GID-08) — Governance & Invariants
# ═══════════════════════════════════════════════════════════════════════════════

"""
P25 Invariant Registry — SOP, Risk, and UI-State Invariants

PURPOSE:
    Define and enforce new invariants for P25 platform expansion:
    - SOP execution invariants
    - Risk scorecard invariants
    - UI state invariants

INVARIANT GROUPS:
    INV-SOP-*: SOP Library and Execution
    INV-RISK-*: Agent Trust and Risk Scoring
    INV-UI-*: UI State and Rendering

EXECUTION MODE: PARALLEL
LANE: GOVERNANCE (GID-08)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT CLASSIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════


class InvariantCategory(Enum):
    """Categories of platform invariants."""

    SOP = "SOP"  # Standard Operating Procedures
    RISK = "RISK"  # Risk and Trust Scoring
    UI = "UI"  # User Interface State
    SECURITY = "SECURITY"  # Security Controls
    GOVERNANCE = "GOVERNANCE"  # Governance Framework
    DATA = "DATA"  # Data Integrity


class InvariantSeverity(Enum):
    """Severity of invariant violations."""

    CRITICAL = "CRITICAL"  # System halt required
    HIGH = "HIGH"  # Block operation
    MEDIUM = "MEDIUM"  # Log and alert
    LOW = "LOW"  # Log only


class EnforcementMode(Enum):
    """How the invariant is enforced."""

    HARD_FAIL = "HARD_FAIL"  # Reject on violation
    SOFT_FAIL = "SOFT_FAIL"  # Allow with warning
    AUDIT_ONLY = "AUDIT_ONLY"  # Log but don't block


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class InvariantDefinition:
    """
    Canonical invariant definition.

    Defines the rule, its category, severity, and enforcement mode.
    """

    invariant_id: str
    name: str
    description: str
    category: InvariantCategory
    severity: InvariantSeverity
    enforcement: EnforcementMode
    validation_rule: str
    error_message: str
    introduced_pac: str
    references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate invariant ID format."""
        if not self.invariant_id.startswith("INV-"):
            raise ValueError(f"Invariant ID must start with 'INV-': {self.invariant_id}")

    def compute_hash(self) -> str:
        """Compute deterministic hash of invariant definition."""
        content = json.dumps(
            {
                "id": self.invariant_id,
                "name": self.name,
                "category": self.category.value,
                "severity": self.severity.value,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class InvariantViolation:
    """Record of an invariant violation."""

    violation_id: str
    invariant_id: str
    timestamp: datetime
    context: Dict[str, Any]
    error_message: str
    pac_id: Optional[str] = None
    agent_id: Optional[str] = None
    remediation_applied: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# SOP INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════════

INV_SOP_001 = InvariantDefinition(
    invariant_id="INV-SOP-001",
    name="SOP Precondition Validation",
    description="All SOPs must validate preconditions before execution",
    category=InvariantCategory.SOP,
    severity=InvariantSeverity.HIGH,
    enforcement=EnforcementMode.HARD_FAIL,
    validation_rule="sop.preconditions.all_passed == True",
    error_message="SOP execution blocked: preconditions not satisfied",
    introduced_pac="PAC-BENSON-P25",
)

INV_SOP_002 = InvariantDefinition(
    invariant_id="INV-SOP-002",
    name="SOP Audit Trail",
    description="All SOP executions must produce audit trail entries",
    category=InvariantCategory.SOP,
    severity=InvariantSeverity.HIGH,
    enforcement=EnforcementMode.HARD_FAIL,
    validation_rule="sop.audit_entry IS NOT NULL",
    error_message="SOP execution missing audit trail entry",
    introduced_pac="PAC-BENSON-P25",
)

INV_SOP_003 = InvariantDefinition(
    invariant_id="INV-SOP-003",
    name="SOP Dual Approval",
    description="Critical SOPs require dual-approval workflow",
    category=InvariantCategory.SOP,
    severity=InvariantSeverity.CRITICAL,
    enforcement=EnforcementMode.HARD_FAIL,
    validation_rule="sop.severity IN ['HIGH', 'CRITICAL'] => sop.approvals.count >= 2",
    error_message="Critical SOP requires dual approval",
    introduced_pac="PAC-BENSON-P25",
)

INV_SOP_004 = InvariantDefinition(
    invariant_id="INV-SOP-004",
    name="SOP Idempotency",
    description="SOP execution must be idempotent where possible",
    category=InvariantCategory.SOP,
    severity=InvariantSeverity.MEDIUM,
    enforcement=EnforcementMode.SOFT_FAIL,
    validation_rule="sop.is_idempotent == True OR sop.idempotency_key IS NOT NULL",
    error_message="SOP execution may not be idempotent",
    introduced_pac="PAC-BENSON-P25",
)

INV_SOP_005 = InvariantDefinition(
    invariant_id="INV-SOP-005",
    name="SOP Rollback Existence",
    description="Reversible SOPs must have rollback procedures defined",
    category=InvariantCategory.SOP,
    severity=InvariantSeverity.MEDIUM,
    enforcement=EnforcementMode.SOFT_FAIL,
    validation_rule="sop.reversibility == 'REVERSIBLE' => sop.rollback_procedure IS NOT NULL",
    error_message="Reversible SOP missing rollback procedure",
    introduced_pac="PAC-BENSON-P25",
)

INV_SOP_006 = InvariantDefinition(
    invariant_id="INV-SOP-006",
    name="SOP OCC Read-Only",
    description="OCC cannot trigger SOP execution directly",
    category=InvariantCategory.SOP,
    severity=InvariantSeverity.CRITICAL,
    enforcement=EnforcementMode.HARD_FAIL,
    validation_rule="request.source != 'OCC' OR request.operation == 'READ'",
    error_message="OCC attempted write operation on SOP",
    introduced_pac="PAC-BENSON-P25",
)


# ═══════════════════════════════════════════════════════════════════════════════
# RISK/TRUST INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════════

INV_RISK_001 = InvariantDefinition(
    invariant_id="INV-RISK-001",
    name="Trust Score Bounds",
    description="Agent trust scores must be within valid bounds [0.0, 1.0]",
    category=InvariantCategory.RISK,
    severity=InvariantSeverity.HIGH,
    enforcement=EnforcementMode.HARD_FAIL,
    validation_rule="0.0 <= agent.trust_score <= 1.0",
    error_message="Trust score out of bounds",
    introduced_pac="PAC-BENSON-P25",
)

INV_RISK_002 = InvariantDefinition(
    invariant_id="INV-RISK-002",
    name="Trust Score Immutability",
    description="Trust scores can only be updated through scoring engine",
    category=InvariantCategory.RISK,
    severity=InvariantSeverity.HIGH,
    enforcement=EnforcementMode.HARD_FAIL,
    validation_rule="trust.update_source == 'SCORING_ENGINE'",
    error_message="Direct trust score manipulation blocked",
    introduced_pac="PAC-BENSON-P25",
)

INV_RISK_003 = InvariantDefinition(
    invariant_id="INV-RISK-003",
    name="Risk Override Audit",
    description="All risk score overrides must be audited with justification",
    category=InvariantCategory.RISK,
    severity=InvariantSeverity.HIGH,
    enforcement=EnforcementMode.HARD_FAIL,
    validation_rule="risk.override == True => risk.justification.length >= 50",
    error_message="Risk override missing required justification",
    introduced_pac="PAC-BENSON-P25",
)

INV_RISK_004 = InvariantDefinition(
    invariant_id="INV-RISK-004",
    name="Trust Tier Consistency",
    description="Trust tier must match overall trust score",
    category=InvariantCategory.RISK,
    severity=InvariantSeverity.MEDIUM,
    enforcement=EnforcementMode.SOFT_FAIL,
    validation_rule="agent.trust_tier == calculate_tier(agent.overall_trust)",
    error_message="Trust tier inconsistent with score",
    introduced_pac="PAC-BENSON-P25",
)

INV_RISK_005 = InvariantDefinition(
    invariant_id="INV-RISK-005",
    name="Probation Agent Restrictions",
    description="Agents in PROBATION tier have restricted execution privileges",
    category=InvariantCategory.RISK,
    severity=InvariantSeverity.HIGH,
    enforcement=EnforcementMode.HARD_FAIL,
    validation_rule="agent.trust_tier == 'PROBATION' => agent.can_execute_critical == False",
    error_message="Probation agent attempted critical operation",
    introduced_pac="PAC-BENSON-P25",
)


# ═══════════════════════════════════════════════════════════════════════════════
# UI STATE INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════════

INV_UI_001 = InvariantDefinition(
    invariant_id="INV-UI-001",
    name="UI Read-Only State",
    description="OCC UI displays read-only state from backend",
    category=InvariantCategory.UI,
    severity=InvariantSeverity.CRITICAL,
    enforcement=EnforcementMode.HARD_FAIL,
    validation_rule="ui.state.source == 'BACKEND' AND ui.state.mutable == False",
    error_message="UI state mutation attempted",
    introduced_pac="PAC-BENSON-P25",
    references=("INV-OCC-001", "INV-OCC-002"),
)

INV_UI_002 = InvariantDefinition(
    invariant_id="INV-UI-002",
    name="No Optimistic Updates",
    description="UI must not render optimistic state updates",
    category=InvariantCategory.UI,
    severity=InvariantSeverity.HIGH,
    enforcement=EnforcementMode.HARD_FAIL,
    validation_rule="ui.render.optimistic == False",
    error_message="Optimistic UI update blocked",
    introduced_pac="PAC-BENSON-P25",
    references=("INV-OCC-002",),
)

INV_UI_003 = InvariantDefinition(
    invariant_id="INV-UI-003",
    name="Invariant Failure Display",
    description="UI must display invariant failures with rule IDs",
    category=InvariantCategory.UI,
    severity=InvariantSeverity.MEDIUM,
    enforcement=EnforcementMode.SOFT_FAIL,
    validation_rule="invariant.failed => ui.display.includes(invariant.id)",
    error_message="Invariant failure not displayed in UI",
    introduced_pac="PAC-BENSON-P25",
    references=("INV-OCC-003",),
)

INV_UI_004 = InvariantDefinition(
    invariant_id="INV-UI-004",
    name="Input Sanitization",
    description="All user input must be sanitized before display",
    category=InvariantCategory.UI,
    severity=InvariantSeverity.HIGH,
    enforcement=EnforcementMode.HARD_FAIL,
    validation_rule="ui.input.sanitized == True",
    error_message="Unsanitized input detected",
    introduced_pac="PAC-BENSON-P25",
    references=("INV-SEC-UI-001",),
)

INV_UI_005 = InvariantDefinition(
    invariant_id="INV-UI-005",
    name="Accessibility Compliance",
    description="UI components must meet WCAG 2.1 AA standards",
    category=InvariantCategory.UI,
    severity=InvariantSeverity.MEDIUM,
    enforcement=EnforcementMode.AUDIT_ONLY,
    validation_rule="ui.component.wcag_compliant == True",
    error_message="Component may not meet accessibility standards",
    introduced_pac="PAC-BENSON-P25",
)

INV_UI_006 = InvariantDefinition(
    invariant_id="INV-UI-006",
    name="Density Mode Persistence",
    description="UI density mode preference must persist across sessions",
    category=InvariantCategory.UI,
    severity=InvariantSeverity.LOW,
    enforcement=EnforcementMode.AUDIT_ONLY,
    validation_rule="ui.preferences.persisted == True",
    error_message="UI preference not persisted",
    introduced_pac="PAC-BENSON-P25",
)


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


class P25InvariantRegistry:
    """
    Registry for P25 invariants.

    Provides validation, lookup, and reporting capabilities.
    """

    _instance: Optional["P25InvariantRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "P25InvariantRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if P25InvariantRegistry._initialized:
            return
        P25InvariantRegistry._initialized = True

        self._invariants: Dict[str, InvariantDefinition] = {}
        self._violations: List[InvariantViolation] = []
        self._validators: Dict[str, Callable[[Dict[str, Any]], bool]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all P25 invariants."""
        invariants = [
            # SOP Invariants
            INV_SOP_001,
            INV_SOP_002,
            INV_SOP_003,
            INV_SOP_004,
            INV_SOP_005,
            INV_SOP_006,
            # Risk Invariants
            INV_RISK_001,
            INV_RISK_002,
            INV_RISK_003,
            INV_RISK_004,
            INV_RISK_005,
            # UI Invariants
            INV_UI_001,
            INV_UI_002,
            INV_UI_003,
            INV_UI_004,
            INV_UI_005,
            INV_UI_006,
        ]
        for inv in invariants:
            self._invariants[inv.invariant_id] = inv

    def register_validator(
        self, invariant_id: str, validator: Callable[[Dict[str, Any]], bool]
    ) -> None:
        """Register a validation function for an invariant."""
        if invariant_id not in self._invariants:
            raise ValueError(f"Unknown invariant: {invariant_id}")
        self._validators[invariant_id] = validator

    def get(self, invariant_id: str) -> Optional[InvariantDefinition]:
        """Get invariant by ID."""
        return self._invariants.get(invariant_id)

    def get_all(self) -> List[InvariantDefinition]:
        """Get all registered invariants."""
        return list(self._invariants.values())

    def get_by_category(self, category: InvariantCategory) -> List[InvariantDefinition]:
        """Get invariants by category."""
        return [inv for inv in self._invariants.values() if inv.category == category]

    def get_by_severity(self, severity: InvariantSeverity) -> List[InvariantDefinition]:
        """Get invariants by severity."""
        return [inv for inv in self._invariants.values() if inv.severity == severity]

    def get_hard_fail(self) -> List[InvariantDefinition]:
        """Get all HARD_FAIL enforced invariants."""
        return [
            inv for inv in self._invariants.values()
            if inv.enforcement == EnforcementMode.HARD_FAIL
        ]

    def validate(
        self, invariant_id: str, context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate an invariant against context.

        Returns (passed, error_message).
        """
        inv = self._invariants.get(invariant_id)
        if inv is None:
            return False, f"Unknown invariant: {invariant_id}"

        validator = self._validators.get(invariant_id)
        if validator is None:
            # No validator registered - pass by default
            return True, None

        try:
            passed = validator(context)
            if passed:
                return True, None
            else:
                return False, inv.error_message
        except Exception as e:
            return False, f"Validation error: {e}"

    def record_violation(
        self,
        invariant_id: str,
        context: Dict[str, Any],
        pac_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> InvariantViolation:
        """Record an invariant violation."""
        inv = self._invariants.get(invariant_id)
        if inv is None:
            raise ValueError(f"Unknown invariant: {invariant_id}")

        violation = InvariantViolation(
            violation_id=f"VIO-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:17]}",
            invariant_id=invariant_id,
            timestamp=datetime.now(timezone.utc),
            context=context,
            error_message=inv.error_message,
            pac_id=pac_id,
            agent_id=agent_id,
        )
        self._violations.append(violation)
        return violation

    def get_violations(
        self,
        invariant_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[InvariantViolation]:
        """Get recorded violations, optionally filtered."""
        violations = self._violations
        if invariant_id:
            violations = [v for v in violations if v.invariant_id == invariant_id]
        if since:
            violations = [v for v in violations if v.timestamp >= since]
        return violations

    def count(self) -> int:
        """Return count of registered invariants."""
        return len(self._invariants)

    def generate_manifest(self) -> Dict[str, Any]:
        """Generate invariant manifest for documentation."""
        return {
            "pac_version": "PAC-BENSON-P25",
            "total_invariants": len(self._invariants),
            "by_category": {
                cat.value: [
                    {
                        "id": inv.invariant_id,
                        "name": inv.name,
                        "severity": inv.severity.value,
                        "enforcement": inv.enforcement.value,
                    }
                    for inv in self.get_by_category(cat)
                ]
                for cat in InvariantCategory
            },
            "hard_fail_count": len(self.get_hard_fail()),
            "violation_count": len(self._violations),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "InvariantCategory",
    "InvariantSeverity",
    "EnforcementMode",
    # Data classes
    "InvariantDefinition",
    "InvariantViolation",
    # Registry
    "P25InvariantRegistry",
    # SOP Invariants
    "INV_SOP_001",
    "INV_SOP_002",
    "INV_SOP_003",
    "INV_SOP_004",
    "INV_SOP_005",
    "INV_SOP_006",
    # Risk Invariants
    "INV_RISK_001",
    "INV_RISK_002",
    "INV_RISK_003",
    "INV_RISK_004",
    "INV_RISK_005",
    # UI Invariants
    "INV_UI_001",
    "INV_UI_002",
    "INV_UI_003",
    "INV_UI_004",
    "INV_UI_005",
    "INV_UI_006",
]
