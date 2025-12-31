# ═══════════════════════════════════════════════════════════════════════════════
# AML Shadow Guardrail Enforcement (SHADOW MODE)
# PAC-BENSON-P29: AML SHADOW PILOT EXECUTION
# Agent: PAX (GID-05)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Shadow Guardrail Enforcement — Tier-0/Tier-1 Rules & Escalation

PURPOSE:
    Enforce guardrail rules in shadow pilot mode:
    - Validate tier boundaries
    - Detect escalation requirements
    - Block prohibited actions
    - Generate audit trails

CONSTRAINTS:
    - SHADOW MODE: No production enforcement
    - All violations logged for analysis
    - FAIL-CLOSED: Default to escalation

LANE: GOVERNANCE (SHADOW ENFORCEMENT)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from core.aml.tier_guardrails import (
    Guardrail,
    GuardrailEngine,
    GuardrailType,
    GuardrailViolation,
    ProductScope,
    TierBoundary,
    ViolationSeverity,
    GR_NO_AUTO_CLEAR_TIER2,
    GR_NO_AUTO_SAR,
    GR_SANCTIONS_ESCALATE,
    GR_PEP_REVIEW,
    GR_CONFIDENCE_THRESHOLD,
    GR_PROHIBITED_JURISDICTION,
    TIER_0_BOUNDARY,
    TIER_1_BOUNDARY,
    TIER_2_BOUNDARY,
    TIER_SAR_BOUNDARY,
)
from core.aml.case_engine import CaseTier, CaseStatus, DecisionOutcome


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW ENFORCEMENT ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowEnforcementAction(Enum):
    """Action taken by shadow enforcement."""

    ALLOW = "ALLOW"  # Action permitted
    BLOCK = "BLOCK"  # Action blocked
    ESCALATE = "ESCALATE"  # Forced escalation
    WARN = "WARN"  # Warning issued
    LOG = "LOG"  # Logged only


class ShadowCheckResult(Enum):
    """Result of shadow guardrail check."""

    PASS = "PASS"  # All guardrails passed
    FAIL_HARD = "FAIL_HARD"  # Hard block triggered
    FAIL_SOFT = "FAIL_SOFT"  # Soft block triggered
    FAIL_WARN = "FAIL_WARN"  # Warning triggered


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ShadowGuardrailCheck:
    """
    Result of a shadow guardrail check.

    Records the outcome of checking guardrails against a proposed action.
    """

    check_id: str
    case_id: str
    proposed_action: str
    tier: str
    result: ShadowCheckResult
    enforcement_action: ShadowEnforcementAction
    triggered_guardrails: List[str] = field(default_factory=list)
    violations: List[str] = field(default_factory=list)
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    shadow_mode: bool = True

    def __post_init__(self) -> None:
        if not self.check_id.startswith("SHCHK-"):
            raise ValueError(f"Check ID must start with 'SHCHK-': {self.check_id}")
        if not self.shadow_mode:
            raise ValueError("FAIL-CLOSED: Shadow mode must be enabled")

    @property
    def is_blocked(self) -> bool:
        """Check if action was blocked."""
        return self.enforcement_action == ShadowEnforcementAction.BLOCK

    @property
    def requires_escalation(self) -> bool:
        """Check if escalation is required."""
        return self.enforcement_action == ShadowEnforcementAction.ESCALATE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_id": self.check_id,
            "case_id": self.case_id,
            "proposed_action": self.proposed_action,
            "tier": self.tier,
            "result": self.result.value,
            "enforcement_action": self.enforcement_action.value,
            "triggered_guardrails": self.triggered_guardrails,
            "violations": self.violations,
            "checked_at": self.checked_at,
            "shadow_mode": self.shadow_mode,
            "is_blocked": self.is_blocked,
            "requires_escalation": self.requires_escalation,
        }


@dataclass
class EscalationRule:
    """
    Rule defining when escalation is required.

    Specifies conditions under which a case must be escalated.
    """

    rule_id: str
    name: str
    description: str
    trigger_condition: str
    escalation_target: str  # ANALYST, SENIOR, SAR_TEAM, SANCTIONS
    priority: int  # Lower = higher priority
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.rule_id.startswith("ESC-"):
            raise ValueError(f"Rule ID must start with 'ESC-': {self.rule_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "trigger_condition": self.trigger_condition,
            "escalation_target": self.escalation_target,
            "priority": self.priority,
            "enabled": self.enabled,
        }


@dataclass
class ShadowEnforcementResult:
    """
    Overall result of shadow enforcement.

    Aggregates results from multiple guardrail checks.
    """

    result_id: str
    case_id: str
    entity_id: str
    tier: str
    proposed_decision: str
    final_decision: str
    checks_performed: int = 0
    violations_detected: int = 0
    escalation_required: bool = False
    escalation_target: Optional[str] = None
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.result_id.startswith("SHRES-"):
            raise ValueError(f"Result ID must start with 'SHRES-': {self.result_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "case_id": self.case_id,
            "entity_id": self.entity_id,
            "tier": self.tier,
            "proposed_decision": self.proposed_decision,
            "final_decision": self.final_decision,
            "checks_performed": self.checks_performed,
            "violations_detected": self.violations_detected,
            "escalation_required": self.escalation_required,
            "escalation_target": self.escalation_target,
            "audit_trail": self.audit_trail,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ESCALATION RULES
# ═══════════════════════════════════════════════════════════════════════════════


ESC_TIER2_ANALYST = EscalationRule(
    rule_id="ESC-001",
    name="Tier-2 to Analyst",
    description="Tier-2 cases must be escalated to analyst",
    trigger_condition="tier == 'TIER_2'",
    escalation_target="ANALYST",
    priority=1,
)

ESC_TIER3_SENIOR = EscalationRule(
    rule_id="ESC-002",
    name="Tier-3 to Senior",
    description="Tier-3 cases must be escalated to senior analyst",
    trigger_condition="tier == 'TIER_3'",
    escalation_target="SENIOR",
    priority=1,
)

ESC_SAR_TRACK = EscalationRule(
    rule_id="ESC-003",
    name="SAR Track Escalation",
    description="SAR-track cases must be escalated to SAR team",
    trigger_condition="tier == 'TIER_SAR'",
    escalation_target="SAR_TEAM",
    priority=1,
)

ESC_SANCTIONS_HIT = EscalationRule(
    rule_id="ESC-004",
    name="Sanctions Hit Escalation",
    description="Any sanctions hit must be escalated immediately",
    trigger_condition="sanctions_hit == True",
    escalation_target="SANCTIONS",
    priority=0,  # Highest priority
)

ESC_PEP_HIT = EscalationRule(
    rule_id="ESC-005",
    name="PEP Hit Escalation",
    description="PEP-associated cases require compliance escalation",
    trigger_condition="pep_hit == True",
    escalation_target="COMPLIANCE",
    priority=1,
)

ESC_HIGH_RISK_JURISDICTION = EscalationRule(
    rule_id="ESC-006",
    name="High-Risk Jurisdiction",
    description="Cases involving high-risk jurisdictions require escalation",
    trigger_condition="high_risk_jurisdiction == True",
    escalation_target="ANALYST",
    priority=2,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW GUARDRAIL ENFORCER
# ═══════════════════════════════════════════════════════════════════════════════


class ShadowGuardrailEnforcer:
    """
    Shadow mode guardrail enforcer.

    Validates proposed actions against guardrails and tier boundaries.
    All enforcement is in SHADOW mode - logged but not blocking production.
    """

    # Tier to boundary mapping
    TIER_BOUNDARIES: Dict[str, TierBoundary] = {
        "TIER_0": TIER_0_BOUNDARY,
        "TIER_1": TIER_1_BOUNDARY,
        "TIER_2": TIER_2_BOUNDARY,
        "TIER_3": TierBoundary(
            tier="TIER_3",
            auto_clearable=False,
            requires_human_review=True,
            requires_senior_review=True,
            sar_eligible=True,
            permitted_actions={"ESCALATE_SENIOR", "LOG", "AUDIT", "PREPARE_NARRATIVE"},
            blocked_actions={"AUTO_CLEAR", "FILE_SAR"},
            description="Requires senior review - SAR-eligible",
        ),
        "TIER_SAR": TIER_SAR_BOUNDARY,
    }

    def __init__(self) -> None:
        """Initialize enforcer."""
        self._base_engine = GuardrailEngine()
        self._escalation_rules: Dict[str, EscalationRule] = {}
        self._check_counter = 0
        self._result_counter = 0
        self._enforcement_log: List[ShadowGuardrailCheck] = []
        self._shadow_mode = True  # ALWAYS TRUE

        self._load_escalation_rules()

    def _load_escalation_rules(self) -> None:
        """Load default escalation rules."""
        for rule in [
            ESC_TIER2_ANALYST,
            ESC_TIER3_SENIOR,
            ESC_SAR_TRACK,
            ESC_SANCTIONS_HIT,
            ESC_PEP_HIT,
            ESC_HIGH_RISK_JURISDICTION,
        ]:
            self._escalation_rules[rule.rule_id] = rule

    @property
    def is_shadow_mode(self) -> bool:
        """Verify shadow mode is enabled (always true)."""
        return self._shadow_mode

    def _generate_check_id(self) -> str:
        """Generate unique check ID."""
        self._check_counter += 1
        return f"SHCHK-{self._check_counter:08d}"

    def _generate_result_id(self) -> str:
        """Generate unique result ID."""
        self._result_counter += 1
        return f"SHRES-{self._result_counter:08d}"

    def check_tier_boundary(
        self,
        tier: str,
        proposed_action: str,
    ) -> Tuple[bool, str]:
        """
        Check if action is permitted for tier.

        Args:
            tier: Case tier
            proposed_action: Action to validate

        Returns:
            Tuple of (is_permitted, reason)
        """
        boundary = self.TIER_BOUNDARIES.get(tier)
        if boundary is None:
            return False, f"Unknown tier: {tier}"

        if proposed_action in boundary.blocked_actions:
            return False, f"Action '{proposed_action}' blocked for {tier}"

        if proposed_action in boundary.permitted_actions:
            return True, f"Action '{proposed_action}' permitted for {tier}"

        # FAIL-CLOSED: Unknown actions are blocked
        return False, f"Unknown action '{proposed_action}' - FAIL-CLOSED"

    def check_auto_clear_eligibility(
        self,
        tier: str,
        context: Dict[str, Any],
    ) -> ShadowGuardrailCheck:
        """
        Check if case is eligible for auto-clearance.

        Args:
            tier: Case tier
            context: Case context (match_score, sanctions_hit, etc.)

        Returns:
            Shadow guardrail check result
        """
        check = ShadowGuardrailCheck(
            check_id=self._generate_check_id(),
            case_id=context.get("case_id", "UNKNOWN"),
            proposed_action="AUTO_CLEAR",
            tier=tier,
            result=ShadowCheckResult.PASS,
            enforcement_action=ShadowEnforcementAction.ALLOW,
        )

        # Check tier boundary
        boundary = self.TIER_BOUNDARIES.get(tier)
        if boundary is None:
            check.result = ShadowCheckResult.FAIL_HARD
            check.enforcement_action = ShadowEnforcementAction.BLOCK
            check.violations.append(f"Unknown tier: {tier}")
            return check

        # Tier-2+ cannot auto-clear
        if not boundary.auto_clearable:
            check.result = ShadowCheckResult.FAIL_HARD
            check.enforcement_action = ShadowEnforcementAction.ESCALATE
            check.triggered_guardrails.append("GR-AML-001")
            check.violations.append(f"{tier} cases cannot be auto-cleared")
            self._enforcement_log.append(check)
            return check

        # Check sanctions hit
        if context.get("sanctions_hit", False):
            check.result = ShadowCheckResult.FAIL_HARD
            check.enforcement_action = ShadowEnforcementAction.ESCALATE
            check.triggered_guardrails.append("GR-AML-003")
            check.violations.append("Sanctions hit detected")
            self._enforcement_log.append(check)
            return check

        # Check PEP hit
        if context.get("pep_hit", False):
            check.result = ShadowCheckResult.FAIL_HARD
            check.enforcement_action = ShadowEnforcementAction.ESCALATE
            check.triggered_guardrails.append("GR-AML-004")
            check.violations.append("PEP association detected")
            self._enforcement_log.append(check)
            return check

        # Check confidence threshold
        confidence = context.get("confidence", 0.0)
        if confidence < 0.95:
            check.result = ShadowCheckResult.FAIL_HARD
            check.enforcement_action = ShadowEnforcementAction.ESCALATE
            check.triggered_guardrails.append("GR-AML-007")
            check.violations.append(f"Confidence {confidence:.2f} below threshold 0.95")
            self._enforcement_log.append(check)
            return check

        # All checks passed
        self._enforcement_log.append(check)
        return check

    def determine_escalation_target(
        self,
        tier: str,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """
        Determine escalation target based on tier and context.

        Args:
            tier: Case tier
            context: Case context

        Returns:
            Escalation target or None
        """
        # Priority-sorted escalation rules
        sorted_rules = sorted(
            self._escalation_rules.values(),
            key=lambda r: r.priority,
        )

        for rule in sorted_rules:
            if not rule.enabled:
                continue

            # Check tier-based rules
            if rule.trigger_condition.startswith("tier =="):
                expected_tier = rule.trigger_condition.split("==")[1].strip().strip("'\"")
                if tier == expected_tier:
                    return rule.escalation_target

            # Check sanctions hit
            if "sanctions_hit" in rule.trigger_condition and context.get("sanctions_hit"):
                return rule.escalation_target

            # Check PEP hit
            if "pep_hit" in rule.trigger_condition and context.get("pep_hit"):
                return rule.escalation_target

            # Check jurisdiction risk
            if "high_risk_jurisdiction" in rule.trigger_condition and context.get("high_risk_jurisdiction"):
                return rule.escalation_target

        return None

    def enforce_decision(
        self,
        case_id: str,
        entity_id: str,
        tier: str,
        proposed_decision: str,
        context: Dict[str, Any],
    ) -> ShadowEnforcementResult:
        """
        Enforce guardrails on a proposed decision.

        Args:
            case_id: Case identifier
            entity_id: Entity identifier
            tier: Case tier
            proposed_decision: Proposed decision outcome
            context: Additional context

        Returns:
            Shadow enforcement result
        """
        result = ShadowEnforcementResult(
            result_id=self._generate_result_id(),
            case_id=case_id,
            entity_id=entity_id,
            tier=tier,
            proposed_decision=proposed_decision,
            final_decision=proposed_decision,  # May change based on checks
        )

        # Add context to audit trail
        result.audit_trail.append({
            "action": "START_ENFORCEMENT",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": context,
        })

        # Check tier boundary
        result.checks_performed += 1
        is_permitted, reason = self.check_tier_boundary(tier, proposed_decision)

        if not is_permitted:
            result.violations_detected += 1
            result.escalation_required = True
            result.final_decision = "ESCALATE"
            result.audit_trail.append({
                "action": "TIER_BOUNDARY_CHECK",
                "result": "BLOCKED",
                "reason": reason,
            })
        else:
            result.audit_trail.append({
                "action": "TIER_BOUNDARY_CHECK",
                "result": "PASSED",
                "reason": reason,
            })

        # If auto-clear proposed, check eligibility
        if proposed_decision == "AUTO_CLEAR":
            result.checks_performed += 1
            auto_clear_check = self.check_auto_clear_eligibility(tier, {
                "case_id": case_id,
                **context,
            })

            if auto_clear_check.is_blocked or auto_clear_check.requires_escalation:
                result.violations_detected += len(auto_clear_check.violations)
                result.escalation_required = True
                result.final_decision = "ESCALATE"
                result.audit_trail.append({
                    "action": "AUTO_CLEAR_CHECK",
                    "result": auto_clear_check.result.value,
                    "violations": auto_clear_check.violations,
                })
            else:
                result.audit_trail.append({
                    "action": "AUTO_CLEAR_CHECK",
                    "result": "PASSED",
                })

        # Determine escalation target if needed
        if result.escalation_required:
            result.escalation_target = self.determine_escalation_target(tier, context)
            result.audit_trail.append({
                "action": "ESCALATION_TARGET",
                "target": result.escalation_target,
            })

        result.audit_trail.append({
            "action": "END_ENFORCEMENT",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "final_decision": result.final_decision,
        })

        return result

    def get_enforcement_summary(self) -> Dict[str, Any]:
        """Get summary of enforcement activity."""
        total_checks = len(self._enforcement_log)
        blocked = sum(1 for c in self._enforcement_log if c.is_blocked)
        escalated = sum(1 for c in self._enforcement_log if c.requires_escalation)
        passed = sum(1 for c in self._enforcement_log if c.result == ShadowCheckResult.PASS)

        return {
            "total_checks": total_checks,
            "blocked": blocked,
            "escalated": escalated,
            "passed": passed,
            "shadow_mode": self._shadow_mode,
        }

    def validate_governance_invariants(self) -> List[Dict[str, Any]]:
        """
        Validate critical governance invariants.

        Returns list of validation results.
        """
        invariants = []

        # Invariant 1: Tier-2+ cannot auto-clear
        for tier in ["TIER_2", "TIER_3", "TIER_SAR"]:
            boundary = self.TIER_BOUNDARIES.get(tier)
            if boundary and boundary.auto_clearable:
                invariants.append({
                    "invariant": f"{tier}_NO_AUTO_CLEAR",
                    "passed": False,
                    "reason": f"{tier} marked as auto-clearable (VIOLATION)",
                })
            else:
                invariants.append({
                    "invariant": f"{tier}_NO_AUTO_CLEAR",
                    "passed": True,
                    "reason": f"{tier} correctly blocks auto-clearance",
                })

        # Invariant 2: SAR filing is never autonomous
        if "FILE_SAR" in TIER_SAR_BOUNDARY.blocked_actions:
            invariants.append({
                "invariant": "NO_AUTO_SAR_FILING",
                "passed": True,
                "reason": "FILE_SAR correctly blocked",
            })
        else:
            invariants.append({
                "invariant": "NO_AUTO_SAR_FILING",
                "passed": False,
                "reason": "FILE_SAR not blocked (VIOLATION)",
            })

        # Invariant 3: Shadow mode is always enabled
        invariants.append({
            "invariant": "SHADOW_MODE_ENABLED",
            "passed": self._shadow_mode,
            "reason": "Shadow mode active" if self._shadow_mode else "Shadow mode disabled (VIOLATION)",
        })

        return invariants
