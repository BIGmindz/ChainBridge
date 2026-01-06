"""
OCC v1.x Decision Threshold Framework

PAC: PAC-OCC-P06
Lane: 4 — Regulatory Safeguards
Agent: Maggie (GID-10) — Decision Integrity Thresholds

Implements configurable decision thresholds for human oversight.
Addresses P04A finding: "Time pressure" and "Justification quality".

Invariant: INV-OCC-THRESH-001 — Threshold violations require mandatory escalation
Invariant: INV-OCC-THRESH-002 — Thresholds cannot be bypassed by any actor
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# THRESHOLD CATEGORIES
# ═══════════════════════════════════════════════════════════════════════════════


class ThresholdCategory(Enum):
    """Categories of decision thresholds."""

    FINANCIAL = "financial"  # Monetary value thresholds
    RISK = "risk"  # Risk score thresholds
    VOLUME = "volume"  # Transaction volume
    TIME = "time"  # Time-based decisions
    AUTHORITY = "authority"  # Permission escalation
    BATCH = "batch"  # Batch operation limits


class ThresholdAction(Enum):
    """Actions when threshold is breached."""

    ALLOW = "allow"  # Proceed (threshold not breached)
    REQUIRE_JUSTIFICATION = "require_justification"  # Must provide reason
    REQUIRE_APPROVAL = "require_approval"  # Needs higher tier approval
    REQUIRE_DUAL_CONTROL = "require_dual_control"  # Two approvers needed
    DENY = "deny"  # Automatically reject
    ESCALATE = "escalate"  # Escalate to next tier


class EscalationLevel(Enum):
    """Escalation levels for threshold breaches."""

    NONE = 0
    LOW = 1  # Logging only
    MEDIUM = 2  # Justification required
    HIGH = 3  # Approval required
    CRITICAL = 4  # Dual control required


# ═══════════════════════════════════════════════════════════════════════════════
# THRESHOLD DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ThresholdDefinition:
    """Definition of a decision threshold."""

    threshold_id: str
    name: str
    category: ThresholdCategory
    description: str
    check_func: Callable[[Any], bool]  # Returns True if threshold breached
    action: ThresholdAction
    escalation_level: EscalationLevel
    minimum_tier: str = "T1"  # Minimum tier to perform action
    escalation_tier: str = "T3"  # Tier to escalate to if breached
    cooldown_seconds: int = 0  # Minimum time between actions


@dataclass
class ThresholdCheck:
    """Result of a threshold check."""

    threshold_id: str
    breached: bool
    action_required: ThresholdAction
    escalation_level: EscalationLevel
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class JustificationRequirement:
    """Justification requirements for a decision."""

    required: bool
    minimum_length: int = 20
    required_fields: List[str] = field(default_factory=list)
    template: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# THRESHOLD ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class ThresholdEngine:
    """
    Decision threshold enforcement engine.

    Provides:
    - Configurable thresholds by category
    - Automatic escalation
    - Justification requirements
    - Audit trail for threshold decisions
    """

    def __init__(self) -> None:
        self._thresholds: Dict[str, ThresholdDefinition] = {}
        self._action_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._register_default_thresholds()

    def _register_default_thresholds(self) -> None:
        """Register default decision thresholds."""

        # ─────────────────────────────────────────────────────────────────
        # FINANCIAL THRESHOLDS
        # ─────────────────────────────────────────────────────────────────

        self.register_threshold(
            ThresholdDefinition(
                threshold_id="FIN-001",
                name="High Value Transaction",
                category=ThresholdCategory.FINANCIAL,
                description="Transactions above $10,000 require justification",
                check_func=lambda v: v.get("amount", 0) > 10000,
                action=ThresholdAction.REQUIRE_JUSTIFICATION,
                escalation_level=EscalationLevel.MEDIUM,
                minimum_tier="T2",
            )
        )

        self.register_threshold(
            ThresholdDefinition(
                threshold_id="FIN-002",
                name="Critical Value Transaction",
                category=ThresholdCategory.FINANCIAL,
                description="Transactions above $100,000 require approval",
                check_func=lambda v: v.get("amount", 0) > 100000,
                action=ThresholdAction.REQUIRE_APPROVAL,
                escalation_level=EscalationLevel.HIGH,
                minimum_tier="T3",
                escalation_tier="T4",
            )
        )

        self.register_threshold(
            ThresholdDefinition(
                threshold_id="FIN-003",
                name="Extreme Value Transaction",
                category=ThresholdCategory.FINANCIAL,
                description="Transactions above $1,000,000 require dual control",
                check_func=lambda v: v.get("amount", 0) > 1000000,
                action=ThresholdAction.REQUIRE_DUAL_CONTROL,
                escalation_level=EscalationLevel.CRITICAL,
                minimum_tier="T4",
            )
        )

        # ─────────────────────────────────────────────────────────────────
        # RISK THRESHOLDS
        # ─────────────────────────────────────────────────────────────────

        self.register_threshold(
            ThresholdDefinition(
                threshold_id="RISK-001",
                name="Elevated Risk Score",
                category=ThresholdCategory.RISK,
                description="Risk score above 70 requires review",
                check_func=lambda v: v.get("risk_score", 0) > 70,
                action=ThresholdAction.REQUIRE_JUSTIFICATION,
                escalation_level=EscalationLevel.MEDIUM,
            )
        )

        self.register_threshold(
            ThresholdDefinition(
                threshold_id="RISK-002",
                name="High Risk Score",
                category=ThresholdCategory.RISK,
                description="Risk score above 90 requires T3 approval",
                check_func=lambda v: v.get("risk_score", 0) > 90,
                action=ThresholdAction.REQUIRE_APPROVAL,
                escalation_level=EscalationLevel.HIGH,
                escalation_tier="T3",
            )
        )

        # ─────────────────────────────────────────────────────────────────
        # TIME THRESHOLDS (Anti-Pressure)
        # ─────────────────────────────────────────────────────────────────

        self.register_threshold(
            ThresholdDefinition(
                threshold_id="TIME-001",
                name="Rapid Decision Cooldown",
                category=ThresholdCategory.TIME,
                description="Decisions within 60 seconds of each other require justification",
                check_func=lambda v: v.get("seconds_since_last", float("inf")) < 60,
                action=ThresholdAction.REQUIRE_JUSTIFICATION,
                escalation_level=EscalationLevel.MEDIUM,
                cooldown_seconds=60,
            )
        )

        self.register_threshold(
            ThresholdDefinition(
                threshold_id="TIME-002",
                name="Off-Hours Decision",
                category=ThresholdCategory.TIME,
                description="Decisions outside business hours require justification",
                check_func=lambda v: not (9 <= v.get("hour", 12) <= 17),
                action=ThresholdAction.REQUIRE_JUSTIFICATION,
                escalation_level=EscalationLevel.LOW,
            )
        )

        # ─────────────────────────────────────────────────────────────────
        # BATCH THRESHOLDS
        # ─────────────────────────────────────────────────────────────────

        self.register_threshold(
            ThresholdDefinition(
                threshold_id="BATCH-001",
                name="Large Batch Operation",
                category=ThresholdCategory.BATCH,
                description="Batch operations with >100 items require approval",
                check_func=lambda v: v.get("batch_size", 0) > 100,
                action=ThresholdAction.REQUIRE_APPROVAL,
                escalation_level=EscalationLevel.HIGH,
                minimum_tier="T3",
            )
        )

        # ─────────────────────────────────────────────────────────────────
        # AUTHORITY THRESHOLDS
        # ─────────────────────────────────────────────────────────────────

        self.register_threshold(
            ThresholdDefinition(
                threshold_id="AUTH-001",
                name="Override Action",
                category=ThresholdCategory.AUTHORITY,
                description="Override actions always require justification",
                check_func=lambda v: v.get("action_type") == "override",
                action=ThresholdAction.REQUIRE_JUSTIFICATION,
                escalation_level=EscalationLevel.HIGH,
                minimum_tier="T3",
            )
        )

        self.register_threshold(
            ThresholdDefinition(
                threshold_id="AUTH-002",
                name="Kill Switch Activation",
                category=ThresholdCategory.AUTHORITY,
                description="Kill switch requires T4 and dual control",
                check_func=lambda v: v.get("action_type") == "kill_switch",
                action=ThresholdAction.REQUIRE_DUAL_CONTROL,
                escalation_level=EscalationLevel.CRITICAL,
                minimum_tier="T4",
            )
        )

    def register_threshold(self, threshold: ThresholdDefinition) -> None:
        """Register a threshold definition."""
        with self._lock:
            self._thresholds[threshold.threshold_id] = threshold
            logger.debug(f"Registered threshold: {threshold.name}")

    def get_threshold(self, threshold_id: str) -> Optional[ThresholdDefinition]:
        """Get a threshold by ID."""
        return self._thresholds.get(threshold_id)

    def list_thresholds(
        self,
        category: Optional[ThresholdCategory] = None,
    ) -> List[ThresholdDefinition]:
        """List registered thresholds."""
        with self._lock:
            thresholds = list(self._thresholds.values())
            if category:
                thresholds = [t for t in thresholds if t.category == category]
            return thresholds

    def check_thresholds(
        self,
        context: Dict[str, Any],
        categories: Optional[List[ThresholdCategory]] = None,
    ) -> List[ThresholdCheck]:
        """
        Check all relevant thresholds for a given context.

        Args:
            context: Decision context (amount, risk_score, etc.)
            categories: Limit to specific categories

        Returns:
            List of threshold check results
        """
        results = []
        thresholds = self.list_thresholds()

        if categories:
            thresholds = [t for t in thresholds if t.category in categories]

        for threshold in thresholds:
            try:
                breached = threshold.check_func(context)
                results.append(
                    ThresholdCheck(
                        threshold_id=threshold.threshold_id,
                        breached=breached,
                        action_required=threshold.action if breached else ThresholdAction.ALLOW,
                        escalation_level=threshold.escalation_level if breached else EscalationLevel.NONE,
                        details={
                            "threshold_name": threshold.name,
                            "minimum_tier": threshold.minimum_tier,
                            "escalation_tier": threshold.escalation_tier,
                        },
                    )
                )
            except Exception as e:
                logger.warning(f"Threshold check failed: {threshold.threshold_id}: {e}")

        return results

    def get_required_action(
        self,
        checks: List[ThresholdCheck],
    ) -> Tuple[ThresholdAction, EscalationLevel]:
        """
        Determine the strictest required action from threshold checks.

        Returns:
            Tuple of (most_restrictive_action, highest_escalation_level)
        """
        if not checks:
            return ThresholdAction.ALLOW, EscalationLevel.NONE

        # Priority order (highest to lowest)
        action_priority = [
            ThresholdAction.DENY,
            ThresholdAction.REQUIRE_DUAL_CONTROL,
            ThresholdAction.REQUIRE_APPROVAL,
            ThresholdAction.ESCALATE,
            ThresholdAction.REQUIRE_JUSTIFICATION,
            ThresholdAction.ALLOW,
        ]

        breached_checks = [c for c in checks if c.breached]
        if not breached_checks:
            return ThresholdAction.ALLOW, EscalationLevel.NONE

        # Find strictest action
        strictest_action = ThresholdAction.ALLOW
        for action in action_priority:
            if any(c.action_required == action for c in breached_checks):
                strictest_action = action
                break

        # Find highest escalation
        highest_level = max(c.escalation_level for c in breached_checks)

        return strictest_action, highest_level

    def get_justification_requirements(
        self,
        checks: List[ThresholdCheck],
    ) -> JustificationRequirement:
        """
        Determine justification requirements from threshold checks.
        """
        action, level = self.get_required_action(checks)

        if action == ThresholdAction.ALLOW:
            return JustificationRequirement(required=False)

        if action == ThresholdAction.REQUIRE_JUSTIFICATION:
            return JustificationRequirement(
                required=True,
                minimum_length=20,
                required_fields=["reason"],
            )

        if action in (
            ThresholdAction.REQUIRE_APPROVAL,
            ThresholdAction.REQUIRE_DUAL_CONTROL,
        ):
            return JustificationRequirement(
                required=True,
                minimum_length=50,
                required_fields=["reason", "business_case", "risk_acknowledgment"],
                template="Approval Request: {reason}\nBusiness Case: {business_case}\nRisk Acknowledgment: {risk_acknowledgment}",
            )

        return JustificationRequirement(required=True)

    def validate_justification(
        self,
        justification: str,
        requirements: JustificationRequirement,
    ) -> Tuple[bool, List[str]]:
        """
        Validate a justification against requirements.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        if not requirements.required:
            return True, []

        if not justification:
            issues.append("Justification is required but not provided")
            return False, issues

        if len(justification) < requirements.minimum_length:
            issues.append(
                f"Justification must be at least {requirements.minimum_length} characters"
            )

        # Check for required fields in structured justification
        for field in requirements.required_fields:
            if field.lower() not in justification.lower():
                issues.append(f"Justification should address: {field}")

        return len(issues) == 0, issues


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_threshold_engine: Optional[ThresholdEngine] = None


def get_threshold_engine() -> ThresholdEngine:
    """Get global threshold engine."""
    global _threshold_engine
    if _threshold_engine is None:
        _threshold_engine = ThresholdEngine()
    return _threshold_engine


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def check_decision_thresholds(
    context: Dict[str, Any],
) -> Tuple[ThresholdAction, EscalationLevel, List[str]]:
    """
    Convenience function to check all thresholds for a decision.

    Returns:
        Tuple of (required_action, escalation_level, breached_threshold_ids)
    """
    engine = get_threshold_engine()
    checks = engine.check_thresholds(context)
    action, level = engine.get_required_action(checks)
    breached_ids = [c.threshold_id for c in checks if c.breached]
    return action, level, breached_ids


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "ThresholdCategory",
    "ThresholdAction",
    "EscalationLevel",
    "ThresholdDefinition",
    "ThresholdCheck",
    "JustificationRequirement",
    "ThresholdEngine",
    "get_threshold_engine",
    "check_decision_thresholds",
]
