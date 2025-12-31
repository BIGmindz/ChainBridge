# ═══════════════════════════════════════════════════════════════════════════════
# AML Tier Guardrails — Product Boundaries & Constraints
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: PAX (GID-05)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Tier Guardrails — Product Boundaries & Governance Constraints

PURPOSE:
    Define and enforce product boundaries for AML automation:
    - Tier-0/Tier-1: Auto-clearable (false positive automation)
    - Tier-2+: MUST escalate to human analysts
    - SAR: PROHIBITED from autonomous filing

GOVERNANCE:
    - FAIL-CLOSED: Default to escalation on uncertainty
    - ZERO tolerance for autonomous Tier-2+ clearance
    - All decisions must be auditable

LANE: GOVERNANCE (ENFORCEMENT)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ═══════════════════════════════════════════════════════════════════════════════
# GUARDRAIL ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class GuardrailType(Enum):
    """Type of guardrail enforcement."""

    HARD_BLOCK = "HARD_BLOCK"  # Cannot proceed under any circumstance
    SOFT_BLOCK = "SOFT_BLOCK"  # Requires override
    WARNING = "WARNING"  # Logged but allowed
    AUDIT_ONLY = "AUDIT_ONLY"  # Logged for review


class ViolationSeverity(Enum):
    """Severity of guardrail violation."""

    CRITICAL = "CRITICAL"  # Immediate halt
    HIGH = "HIGH"  # Requires intervention
    MEDIUM = "MEDIUM"  # Investigation needed
    LOW = "LOW"  # Informational


class ProductScope(Enum):
    """AML product scope boundaries."""

    FALSE_POSITIVE = "FALSE_POSITIVE"  # FP automation - IN SCOPE
    SUSPICIOUS_REVIEW = "SUSPICIOUS_REVIEW"  # Manual review - ESCALATE
    SAR_FILING = "SAR_FILING"  # SAR filing - PROHIBITED
    SANCTIONS_SCREENING = "SANCTIONS_SCREENING"  # Sanctions - ESCALATE
    PEP_SCREENING = "PEP_SCREENING"  # PEP screening - ESCALATE
    ADVERSE_MEDIA = "ADVERSE_MEDIA"  # Media hits - ESCALATE


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Guardrail:
    """
    AML product guardrail definition.

    Defines a specific boundary or constraint for the AML program.
    """

    guardrail_id: str
    name: str
    description: str
    guardrail_type: GuardrailType
    violation_severity: ViolationSeverity
    scope: ProductScope
    condition: str  # Human-readable condition
    enforcement_action: str
    enabled: bool = True
    bypass_allowed: bool = False  # If soft block, can it be overridden?
    audit_required: bool = True

    def __post_init__(self) -> None:
        if not self.guardrail_id.startswith("GR-AML-"):
            raise ValueError(f"Guardrail ID must start with 'GR-AML-': {self.guardrail_id}")

    def compute_guardrail_hash(self) -> str:
        """Compute deterministic hash."""
        data = {
            "guardrail_id": self.guardrail_id,
            "guardrail_type": self.guardrail_type.value,
            "scope": self.scope.value,
            "condition": self.condition,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "guardrail_id": self.guardrail_id,
            "name": self.name,
            "description": self.description,
            "guardrail_type": self.guardrail_type.value,
            "violation_severity": self.violation_severity.value,
            "scope": self.scope.value,
            "condition": self.condition,
            "enforcement_action": self.enforcement_action,
            "enabled": self.enabled,
            "bypass_allowed": self.bypass_allowed,
            "audit_required": self.audit_required,
            "guardrail_hash": self.compute_guardrail_hash(),
        }


@dataclass
class GuardrailViolation:
    """
    Record of a guardrail violation.

    Captures when and how a guardrail was triggered.
    """

    violation_id: str
    guardrail_id: str
    case_id: str
    entity_id: str
    timestamp: str
    severity: ViolationSeverity
    context: Dict[str, Any]
    blocked: bool  # Was the action blocked?
    override_by: Optional[str] = None  # User who overrode (if any)
    override_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.violation_id.startswith("VIOL-"):
            raise ValueError(f"Violation ID must start with 'VIOL-': {self.violation_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "guardrail_id": self.guardrail_id,
            "case_id": self.case_id,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp,
            "severity": self.severity.value,
            "context": self.context,
            "blocked": self.blocked,
            "override_by": self.override_by,
            "override_reason": self.override_reason,
        }


@dataclass
class TierBoundary:
    """
    Tier boundary definition.

    Defines what actions are permitted at each tier level.
    """

    tier: str  # TIER_0, TIER_1, TIER_2, TIER_3, TIER_SAR
    auto_clearable: bool
    requires_human_review: bool
    requires_senior_review: bool
    sar_eligible: bool
    permitted_actions: Set[str]
    blocked_actions: Set[str]
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "auto_clearable": self.auto_clearable,
            "requires_human_review": self.requires_human_review,
            "requires_senior_review": self.requires_senior_review,
            "sar_eligible": self.sar_eligible,
            "permitted_actions": list(self.permitted_actions),
            "blocked_actions": list(self.blocked_actions),
            "description": self.description,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT TIER BOUNDARIES
# ═══════════════════════════════════════════════════════════════════════════════


TIER_0_BOUNDARY = TierBoundary(
    tier="TIER_0",
    auto_clearable=True,
    requires_human_review=False,
    requires_senior_review=False,
    sar_eligible=False,
    permitted_actions={"AUTO_CLEAR", "LOG", "AUDIT"},
    blocked_actions={"ESCALATE_SAR", "FILE_SAR", "BLOCK_ACCOUNT"},
    description="Obvious false positives - fully automated clearance",
)

TIER_1_BOUNDARY = TierBoundary(
    tier="TIER_1",
    auto_clearable=True,
    requires_human_review=False,
    requires_senior_review=False,
    sar_eligible=False,
    permitted_actions={"AUTO_CLEAR", "LOG", "AUDIT", "REQUEST_INFO"},
    blocked_actions={"ESCALATE_SAR", "FILE_SAR", "BLOCK_ACCOUNT"},
    description="Low-risk alerts with sufficient evidence - automated clearance",
)

TIER_2_BOUNDARY = TierBoundary(
    tier="TIER_2",
    auto_clearable=False,  # CRITICAL: Cannot auto-clear
    requires_human_review=True,
    requires_senior_review=False,
    sar_eligible=False,
    permitted_actions={"ESCALATE_ANALYST", "LOG", "AUDIT", "PREPARE_NARRATIVE"},
    blocked_actions={"AUTO_CLEAR", "FILE_SAR", "BLOCK_ACCOUNT"},
    description="Requires analyst review - cannot be auto-cleared",
)

TIER_3_BOUNDARY = TierBoundary(
    tier="TIER_3",
    auto_clearable=False,  # CRITICAL: Cannot auto-clear
    requires_human_review=True,
    requires_senior_review=True,
    sar_eligible=True,
    permitted_actions={"ESCALATE_SENIOR", "LOG", "AUDIT", "PREPARE_NARRATIVE"},
    blocked_actions={"AUTO_CLEAR", "FILE_SAR"},  # Cannot FILE, only PREPARE
    description="Requires senior review - SAR-eligible but not auto-filed",
)

TIER_SAR_BOUNDARY = TierBoundary(
    tier="TIER_SAR",
    auto_clearable=False,  # CRITICAL: Cannot auto-clear
    requires_human_review=True,
    requires_senior_review=True,
    sar_eligible=True,
    permitted_actions={"ESCALATE_SAR", "LOG", "AUDIT", "PREPARE_NARRATIVE", "PREPARE_SAR"},
    blocked_actions={"AUTO_CLEAR", "FILE_SAR"},  # NEVER auto-file SAR
    description="SAR-track - requires human SAR filing decision",
)


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT GUARDRAILS
# ═══════════════════════════════════════════════════════════════════════════════


GR_NO_AUTO_CLEAR_TIER2 = Guardrail(
    guardrail_id="GR-AML-001",
    name="No Auto-Clear Tier-2+",
    description="TIER_2 and above cases CANNOT be auto-cleared",
    guardrail_type=GuardrailType.HARD_BLOCK,
    violation_severity=ViolationSeverity.CRITICAL,
    scope=ProductScope.FALSE_POSITIVE,
    condition="case.tier in ['TIER_2', 'TIER_3', 'TIER_SAR'] AND decision == 'AUTO_CLEAR'",
    enforcement_action="Block action and escalate to analyst",
    bypass_allowed=False,
)

GR_NO_AUTO_SAR = Guardrail(
    guardrail_id="GR-AML-002",
    name="No Autonomous SAR Filing",
    description="SAR filing CANNOT be performed autonomously",
    guardrail_type=GuardrailType.HARD_BLOCK,
    violation_severity=ViolationSeverity.CRITICAL,
    scope=ProductScope.SAR_FILING,
    condition="action == 'FILE_SAR' AND actor == 'SYSTEM'",
    enforcement_action="Block action and require human authorization",
    bypass_allowed=False,
)

GR_SANCTIONS_ESCALATE = Guardrail(
    guardrail_id="GR-AML-003",
    name="Sanctions Hit Escalation",
    description="Any sanctions match MUST be escalated",
    guardrail_type=GuardrailType.HARD_BLOCK,
    violation_severity=ViolationSeverity.CRITICAL,
    scope=ProductScope.SANCTIONS_SCREENING,
    condition="sanctions_hit == True AND decision == 'AUTO_CLEAR'",
    enforcement_action="Block clearance and escalate to sanctions team",
    bypass_allowed=False,
)

GR_PEP_REVIEW = Guardrail(
    guardrail_id="GR-AML-004",
    name="PEP Review Required",
    description="PEP-related alerts require human review",
    guardrail_type=GuardrailType.HARD_BLOCK,
    violation_severity=ViolationSeverity.HIGH,
    scope=ProductScope.PEP_SCREENING,
    condition="pep_associated == True AND decision == 'AUTO_CLEAR'",
    enforcement_action="Block clearance and escalate to compliance",
    bypass_allowed=False,
)

GR_HIGH_AMOUNT_REVIEW = Guardrail(
    guardrail_id="GR-AML-005",
    name="High Amount Review",
    description="High-value transactions require review",
    guardrail_type=GuardrailType.SOFT_BLOCK,
    violation_severity=ViolationSeverity.MEDIUM,
    scope=ProductScope.FALSE_POSITIVE,
    condition="total_amount > 100000 AND tier in ['TIER_0', 'TIER_1']",
    enforcement_action="Escalate to analyst for confirmation",
    bypass_allowed=True,
)

GR_PROHIBITED_JURISDICTION = Guardrail(
    guardrail_id="GR-AML-006",
    name="Prohibited Jurisdiction",
    description="Transactions involving prohibited jurisdictions cannot be cleared",
    guardrail_type=GuardrailType.HARD_BLOCK,
    violation_severity=ViolationSeverity.CRITICAL,
    scope=ProductScope.SANCTIONS_SCREENING,
    condition="jurisdiction in PROHIBITED_LIST AND decision == 'AUTO_CLEAR'",
    enforcement_action="Block clearance and escalate to sanctions team",
    bypass_allowed=False,
)

GR_CONFIDENCE_THRESHOLD = Guardrail(
    guardrail_id="GR-AML-007",
    name="Confidence Threshold",
    description="Auto-clearance requires minimum confidence threshold",
    guardrail_type=GuardrailType.HARD_BLOCK,
    violation_severity=ViolationSeverity.HIGH,
    scope=ProductScope.FALSE_POSITIVE,
    condition="confidence < 0.95 AND decision == 'AUTO_CLEAR'",
    enforcement_action="Block clearance and require additional evidence",
    bypass_allowed=False,
)

GR_ADVERSE_MEDIA_ESCALATE = Guardrail(
    guardrail_id="GR-AML-008",
    name="Adverse Media Escalation",
    description="Adverse media hits require human review",
    guardrail_type=GuardrailType.HARD_BLOCK,
    violation_severity=ViolationSeverity.HIGH,
    scope=ProductScope.ADVERSE_MEDIA,
    condition="adverse_media_hit == True AND decision == 'AUTO_CLEAR'",
    enforcement_action="Block clearance and escalate to analyst",
    bypass_allowed=False,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GUARDRAIL ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class GuardrailEngine:
    """
    AML Guardrail enforcement engine.

    Provides:
    - Guardrail registration and management
    - Violation detection and recording
    - Tier boundary enforcement
    - Audit trail generation
    """

    def __init__(self) -> None:
        self._guardrails: Dict[str, Guardrail] = {}
        self._tier_boundaries: Dict[str, TierBoundary] = {}
        self._violations: List[GuardrailViolation] = []
        self._violation_counter = 0

        # Load defaults
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default guardrails and boundaries."""
        # Guardrails
        for guardrail in [
            GR_NO_AUTO_CLEAR_TIER2,
            GR_NO_AUTO_SAR,
            GR_SANCTIONS_ESCALATE,
            GR_PEP_REVIEW,
            GR_HIGH_AMOUNT_REVIEW,
            GR_PROHIBITED_JURISDICTION,
            GR_CONFIDENCE_THRESHOLD,
            GR_ADVERSE_MEDIA_ESCALATE,
        ]:
            self._guardrails[guardrail.guardrail_id] = guardrail

        # Tier boundaries
        for boundary in [
            TIER_0_BOUNDARY,
            TIER_1_BOUNDARY,
            TIER_2_BOUNDARY,
            TIER_3_BOUNDARY,
            TIER_SAR_BOUNDARY,
        ]:
            self._tier_boundaries[boundary.tier] = boundary

    # ───────────────────────────────────────────────────────────────────────────
    # TIER BOUNDARY CHECKS
    # ───────────────────────────────────────────────────────────────────────────

    def get_tier_boundary(self, tier: str) -> Optional[TierBoundary]:
        """Get tier boundary definition."""
        return self._tier_boundaries.get(tier)

    def is_auto_clearable(self, tier: str) -> bool:
        """Check if tier allows auto-clearance."""
        boundary = self.get_tier_boundary(tier)
        return boundary.auto_clearable if boundary else False

    def check_action_permitted(self, tier: str, action: str) -> bool:
        """Check if action is permitted for tier."""
        boundary = self.get_tier_boundary(tier)
        if boundary is None:
            return False

        if action in boundary.blocked_actions:
            return False

        return action in boundary.permitted_actions

    # ───────────────────────────────────────────────────────────────────────────
    # GUARDRAIL EVALUATION
    # ───────────────────────────────────────────────────────────────────────────

    def evaluate_clearance(
        self,
        case_id: str,
        entity_id: str,
        tier: str,
        confidence: float,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate whether a clearance decision is permitted.

        Args:
            case_id: Case being evaluated
            entity_id: Entity associated with case
            tier: Current tier classification
            confidence: Decision confidence
            context: Additional context (sanctions_hit, pep_associated, etc.)

        Returns:
            Evaluation result with violations and recommendation
        """
        violations: List[GuardrailViolation] = []
        blocked = False

        # Check tier boundary
        if not self.is_auto_clearable(tier):
            violation = self._record_violation(
                guardrail_id="GR-AML-001",
                case_id=case_id,
                entity_id=entity_id,
                context={"tier": tier, "action": "AUTO_CLEAR"},
                blocked=True,
            )
            violations.append(violation)
            blocked = True

        # Check confidence threshold
        if confidence < 0.95:
            violation = self._record_violation(
                guardrail_id="GR-AML-007",
                case_id=case_id,
                entity_id=entity_id,
                context={"confidence": confidence, "threshold": 0.95},
                blocked=True,
            )
            violations.append(violation)
            blocked = True

        # Check sanctions hit
        if context.get("sanctions_hit", False):
            violation = self._record_violation(
                guardrail_id="GR-AML-003",
                case_id=case_id,
                entity_id=entity_id,
                context={"sanctions_hit": True},
                blocked=True,
            )
            violations.append(violation)
            blocked = True

        # Check PEP association
        if context.get("pep_associated", False):
            violation = self._record_violation(
                guardrail_id="GR-AML-004",
                case_id=case_id,
                entity_id=entity_id,
                context={"pep_associated": True},
                blocked=True,
            )
            violations.append(violation)
            blocked = True

        # Check adverse media
        if context.get("adverse_media_hit", False):
            violation = self._record_violation(
                guardrail_id="GR-AML-008",
                case_id=case_id,
                entity_id=entity_id,
                context={"adverse_media_hit": True},
                blocked=True,
            )
            violations.append(violation)
            blocked = True

        # Check prohibited jurisdiction
        if context.get("prohibited_jurisdiction", False):
            violation = self._record_violation(
                guardrail_id="GR-AML-006",
                case_id=case_id,
                entity_id=entity_id,
                context={"prohibited_jurisdiction": True},
                blocked=True,
            )
            violations.append(violation)
            blocked = True

        return {
            "case_id": case_id,
            "tier": tier,
            "clearance_permitted": not blocked,
            "violations": [v.to_dict() for v in violations],
            "violation_count": len(violations),
            "recommendation": "ESCALATE" if blocked else "CLEAR",
            "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def evaluate_sar_filing(
        self,
        case_id: str,
        entity_id: str,
        actor: str,  # "SYSTEM" or user ID
    ) -> Dict[str, Any]:
        """
        Evaluate whether SAR filing is permitted.

        SAR filing is NEVER permitted autonomously.
        """
        if actor == "SYSTEM":
            violation = self._record_violation(
                guardrail_id="GR-AML-002",
                case_id=case_id,
                entity_id=entity_id,
                context={"actor": actor, "action": "FILE_SAR"},
                blocked=True,
            )
            return {
                "case_id": case_id,
                "filing_permitted": False,
                "violation": violation.to_dict(),
                "reason": "SAR filing cannot be performed autonomously",
            }

        return {
            "case_id": case_id,
            "filing_permitted": True,
            "actor": actor,
            "note": "Human-initiated SAR filing is permitted",
        }

    def _record_violation(
        self,
        guardrail_id: str,
        case_id: str,
        entity_id: str,
        context: Dict[str, Any],
        blocked: bool,
    ) -> GuardrailViolation:
        """Record a guardrail violation."""
        self._violation_counter += 1
        guardrail = self._guardrails.get(guardrail_id)

        violation = GuardrailViolation(
            violation_id=f"VIOL-{self._violation_counter:08d}",
            guardrail_id=guardrail_id,
            case_id=case_id,
            entity_id=entity_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity=guardrail.violation_severity if guardrail else ViolationSeverity.HIGH,
            context=context,
            blocked=blocked,
        )

        self._violations.append(violation)
        return violation

    # ───────────────────────────────────────────────────────────────────────────
    # QUERIES
    # ───────────────────────────────────────────────────────────────────────────

    def get_guardrail(self, guardrail_id: str) -> Optional[Guardrail]:
        """Get guardrail by ID."""
        return self._guardrails.get(guardrail_id)

    def list_guardrails(self) -> List[Guardrail]:
        """List all guardrails."""
        return list(self._guardrails.values())

    def list_violations(self) -> List[GuardrailViolation]:
        """List all violations."""
        return self._violations.copy()

    def get_violations_for_case(self, case_id: str) -> List[GuardrailViolation]:
        """Get violations for a specific case."""
        return [v for v in self._violations if v.case_id == case_id]

    def get_critical_violations(self) -> List[GuardrailViolation]:
        """Get critical severity violations."""
        return [v for v in self._violations if v.severity == ViolationSeverity.CRITICAL]

    # ───────────────────────────────────────────────────────────────────────────
    # REPORTING
    # ───────────────────────────────────────────────────────────────────────────

    def generate_report(self) -> Dict[str, Any]:
        """Generate guardrail status report."""
        violations_by_severity: Dict[str, int] = {}
        for severity in ViolationSeverity:
            violations_by_severity[severity.value] = len([
                v for v in self._violations if v.severity == severity
            ])

        violations_by_guardrail: Dict[str, int] = {}
        for guardrail_id in self._guardrails:
            violations_by_guardrail[guardrail_id] = len([
                v for v in self._violations if v.guardrail_id == guardrail_id
            ])

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_guardrails": len(self._guardrails),
            "enabled_guardrails": len([g for g in self._guardrails.values() if g.enabled]),
            "total_violations": len(self._violations),
            "blocked_actions": len([v for v in self._violations if v.blocked]),
            "violations_by_severity": violations_by_severity,
            "violations_by_guardrail": violations_by_guardrail,
            "tier_boundaries": {
                tier: boundary.to_dict()
                for tier, boundary in self._tier_boundaries.items()
            },
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "GuardrailType",
    "ViolationSeverity",
    "ProductScope",
    # Data Classes
    "Guardrail",
    "GuardrailViolation",
    "TierBoundary",
    # Service
    "GuardrailEngine",
    # Default Boundaries
    "TIER_0_BOUNDARY",
    "TIER_1_BOUNDARY",
    "TIER_2_BOUNDARY",
    "TIER_3_BOUNDARY",
    "TIER_SAR_BOUNDARY",
    # Default Guardrails
    "GR_NO_AUTO_CLEAR_TIER2",
    "GR_NO_AUTO_SAR",
    "GR_SANCTIONS_ESCALATE",
    "GR_PEP_REVIEW",
    "GR_HIGH_AMOUNT_REVIEW",
    "GR_PROHIBITED_JURISDICTION",
    "GR_CONFIDENCE_THRESHOLD",
    "GR_ADVERSE_MEDIA_ESCALATE",
]
