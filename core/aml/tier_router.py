# ═══════════════════════════════════════════════════════════════════════════════
# AML Tier Router — Decision Routing & Escalation
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: CODY (GID-01)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Tier Router — Tiered Decision Routing

PURPOSE:
    Route AML cases to appropriate tier based on risk signals
    and evidence. Enforces governance constraints on auto-clearance.

TIER DEFINITIONS:
    - Tier-0: Obvious false positive (auto-clearable)
    - Tier-1: Low-risk false positive (auto-clearable with rationale)
    - Tier-2: Requires human analyst review (ESCALATE)
    - Tier-3: Complex case requiring senior analyst (ESCALATE)
    - Tier-SAR: Potential SAR filing required (ESCALATE)

CONSTRAINTS:
    - ONLY Tier-0 and Tier-1 can be auto-cleared
    - All Tier-2+ cases MUST be escalated
    - No autonomous SAR filing
    - FAIL-CLOSED on ambiguity

LANE: EXECUTION (AML ROUTING)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class RoutingDecision(Enum):
    """Decision from tier routing."""

    AUTO_CLEAR = "AUTO_CLEAR"  # Can be auto-cleared (Tier-0/Tier-1)
    ESCALATE_ANALYST = "ESCALATE_ANALYST"  # Requires analyst (Tier-2)
    ESCALATE_SENIOR = "ESCALATE_SENIOR"  # Requires senior analyst (Tier-3)
    ESCALATE_SAR = "ESCALATE_SAR"  # Potential SAR (Tier-SAR)
    HOLD = "HOLD"  # Insufficient evidence


class EscalationReason(Enum):
    """Reason for escalation."""

    # Risk-based
    HIGH_RISK_MATCH = "HIGH_RISK_MATCH"
    MULTIPLE_RISK_SIGNALS = "MULTIPLE_RISK_SIGNALS"
    SANCTIONS_INVOLVEMENT = "SANCTIONS_INVOLVEMENT"
    PEP_INVOLVEMENT = "PEP_INVOLVEMENT"

    # Evidence-based
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    IDENTITY_UNCERTAINTY = "IDENTITY_UNCERTAINTY"

    # Behavioral
    SUSPICIOUS_PATTERN = "SUSPICIOUS_PATTERN"
    STRUCTURING_DETECTED = "STRUCTURING_DETECTED"

    # Jurisdictional
    HIGH_RISK_JURISDICTION = "HIGH_RISK_JURISDICTION"

    # Governance
    POLICY_REQUIREMENT = "POLICY_REQUIREMENT"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"

    # SAR-specific
    SAR_THRESHOLD_MET = "SAR_THRESHOLD_MET"
    PATTERN_OF_ACTIVITY = "PATTERN_OF_ACTIVITY"


# ═══════════════════════════════════════════════════════════════════════════════
# TIER CRITERIA
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TierCriteria:
    """
    Criteria for tier classification.

    Defines the thresholds and conditions for each tier.
    """

    tier_id: str
    tier_name: str
    max_risk_score: float  # Maximum aggregate risk score
    max_match_score: float  # Maximum match score from screening
    allowed_indicators: List[str]  # Risk indicators that don't escalate
    blocked_indicators: List[str]  # Risk indicators that force escalation
    min_evidence_strength: str  # Minimum required evidence strength
    requires_human_review: bool
    auto_clearable: bool

    def __post_init__(self) -> None:
        if not self.tier_id.startswith("TIER-"):
            raise ValueError(f"Tier ID must start with 'TIER-': {self.tier_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier_id": self.tier_id,
            "tier_name": self.tier_name,
            "max_risk_score": self.max_risk_score,
            "max_match_score": self.max_match_score,
            "allowed_indicators": self.allowed_indicators,
            "blocked_indicators": self.blocked_indicators,
            "min_evidence_strength": self.min_evidence_strength,
            "requires_human_review": self.requires_human_review,
            "auto_clearable": self.auto_clearable,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING RESULT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RoutingResult:
    """
    Result of tier routing decision.

    Contains the routing decision with full rationale
    and supporting evidence.
    """

    result_id: str
    case_id: str
    decision: RoutingDecision
    assigned_tier: str
    confidence: float
    risk_score: float
    match_score: float
    escalation_reasons: List[EscalationReason] = field(default_factory=list)
    cleared_indicators: List[str] = field(default_factory=list)
    blocking_indicators: List[str] = field(default_factory=list)
    rationale: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.result_id.startswith("ROUTE-"):
            raise ValueError(f"Result ID must start with 'ROUTE-': {self.result_id}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0: {self.confidence}")

    @property
    def is_auto_clearable(self) -> bool:
        """Check if result allows auto-clearance."""
        return (
            self.decision == RoutingDecision.AUTO_CLEAR
            and self.confidence >= 0.90
            and len(self.blocking_indicators) == 0
        )

    @property
    def requires_escalation(self) -> bool:
        """Check if result requires escalation."""
        return self.decision in (
            RoutingDecision.ESCALATE_ANALYST,
            RoutingDecision.ESCALATE_SENIOR,
            RoutingDecision.ESCALATE_SAR,
        )

    def compute_result_hash(self) -> str:
        """Compute deterministic hash of result."""
        data = {
            "result_id": self.result_id,
            "case_id": self.case_id,
            "decision": self.decision.value,
            "assigned_tier": self.assigned_tier,
            "risk_score": self.risk_score,
            "match_score": self.match_score,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "case_id": self.case_id,
            "decision": self.decision.value,
            "assigned_tier": self.assigned_tier,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "match_score": self.match_score,
            "escalation_reasons": [r.value for r in self.escalation_reasons],
            "cleared_indicators": self.cleared_indicators,
            "blocking_indicators": self.blocking_indicators,
            "rationale": self.rationale,
            "is_auto_clearable": self.is_auto_clearable,
            "requires_escalation": self.requires_escalation,
            "created_at": self.created_at,
            "result_hash": self.compute_result_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ESCALATION CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class EscalationContext:
    """
    Context for escalation decision.

    Provides all relevant information for escalated review.
    """

    context_id: str
    case_id: str
    routing_result_id: str
    escalation_reasons: List[EscalationReason]
    risk_summary: Dict[str, Any]
    evidence_summary: Dict[str, Any]
    recommended_actions: List[str]
    urgency: str  # LOW, MEDIUM, HIGH, CRITICAL
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.context_id.startswith("ESC-"):
            raise ValueError(f"Context ID must start with 'ESC-': {self.context_id}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "case_id": self.case_id,
            "routing_result_id": self.routing_result_id,
            "escalation_reasons": [r.value for r in self.escalation_reasons],
            "risk_summary": self.risk_summary,
            "evidence_summary": self.evidence_summary,
            "recommended_actions": self.recommended_actions,
            "urgency": self.urgency,
            "created_at": self.created_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT TIER CRITERIA
# ═══════════════════════════════════════════════════════════════════════════════


# Tier-0: Obvious false positive
TIER_0_CRITERIA = TierCriteria(
    tier_id="TIER-0",
    tier_name="Obvious False Positive",
    max_risk_score=0.1,
    max_match_score=0.3,
    allowed_indicators=[],  # No risk indicators allowed
    blocked_indicators=[
        "SANCTIONS_MATCH", "SANCTIONS_ASSOCIATE", "SANCTIONS_OWNED_ENTITY",
        "PEP_MATCH", "PEP_FAMILY", "PEP_ASSOCIATE",
        "NEGATIVE_NEWS", "FRAUD_ALLEGATION", "CORRUPTION_ALLEGATION",
        "STRUCTURING", "HIGH_RISK_JURISDICTION",
    ],
    min_evidence_strength="MODERATE",
    requires_human_review=False,
    auto_clearable=True,
)

# Tier-1: Low-risk false positive
TIER_1_CRITERIA = TierCriteria(
    tier_id="TIER-1",
    tier_name="Low-Risk False Positive",
    max_risk_score=0.3,
    max_match_score=0.5,
    allowed_indicators=[
        "IDENTITY_MISMATCH",  # Can be explained
        "INCOMPLETE_KYC",  # If remediated
    ],
    blocked_indicators=[
        "SANCTIONS_MATCH", "SANCTIONS_ASSOCIATE", "SANCTIONS_OWNED_ENTITY",
        "PEP_MATCH", "PEP_FAMILY",
        "FRAUD_ALLEGATION", "CORRUPTION_ALLEGATION",
        "STRUCTURING",
    ],
    min_evidence_strength="MODERATE",
    requires_human_review=False,
    auto_clearable=True,
)

# Tier-2: Requires analyst review
TIER_2_CRITERIA = TierCriteria(
    tier_id="TIER-2",
    tier_name="Analyst Review Required",
    max_risk_score=0.6,
    max_match_score=0.8,
    allowed_indicators=[
        "IDENTITY_MISMATCH", "INCOMPLETE_KYC",
        "PEP_ASSOCIATE", "HIGH_RISK_JURISDICTION",
        "UNUSUAL_ACTIVITY",
    ],
    blocked_indicators=[
        "SANCTIONS_MATCH", "SANCTIONS_OWNED_ENTITY",
        "FRAUD_ALLEGATION", "STRUCTURING",
    ],
    min_evidence_strength="STRONG",
    requires_human_review=True,
    auto_clearable=False,
)

# Tier-3: Senior analyst required
TIER_3_CRITERIA = TierCriteria(
    tier_id="TIER-3",
    tier_name="Senior Analyst Review",
    max_risk_score=0.85,
    max_match_score=0.95,
    allowed_indicators=[
        "PEP_MATCH", "PEP_FAMILY", "PEP_ASSOCIATE",
        "SANCTIONS_ASSOCIATE", "HIGH_RISK_JURISDICTION",
        "UNUSUAL_ACTIVITY", "RAPID_MOVEMENT",
    ],
    blocked_indicators=[
        "SANCTIONS_MATCH",
        "STRUCTURING",
    ],
    min_evidence_strength="VERIFIED",
    requires_human_review=True,
    auto_clearable=False,
)

# Tier-SAR: Potential SAR
TIER_SAR_CRITERIA = TierCriteria(
    tier_id="TIER-SAR",
    tier_name="SAR Review Required",
    max_risk_score=1.0,
    max_match_score=1.0,
    allowed_indicators=[],  # All indicators acceptable at this tier
    blocked_indicators=[],  # Nothing blocked - all goes to SAR review
    min_evidence_strength="VERIFIED",
    requires_human_review=True,
    auto_clearable=False,
)


# ═══════════════════════════════════════════════════════════════════════════════
# TIER ROUTER
# ═══════════════════════════════════════════════════════════════════════════════


class TierRouter:
    """
    Router for tiered AML decision making.

    Provides:
    - Tier classification based on risk signals
    - Routing decision generation
    - Escalation context creation
    - Governance constraint enforcement
    """

    def __init__(self) -> None:
        self._criteria: Dict[str, TierCriteria] = {}
        self._result_counter = 0
        self._escalation_counter = 0

        # Register default criteria
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default tier criteria."""
        defaults = [
            TIER_0_CRITERIA,
            TIER_1_CRITERIA,
            TIER_2_CRITERIA,
            TIER_3_CRITERIA,
            TIER_SAR_CRITERIA,
        ]
        for criteria in defaults:
            self._criteria[criteria.tier_id] = criteria

    # ───────────────────────────────────────────────────────────────────────────
    # ROUTING
    # ───────────────────────────────────────────────────────────────────────────

    def route_case(
        self,
        case_id: str,
        risk_score: float,
        match_score: float,
        risk_indicators: List[str],
        evidence_strength: str,
    ) -> RoutingResult:
        """
        Route a case to appropriate tier.

        Args:
            case_id: The case to route
            risk_score: Aggregate risk score (0.0-1.0)
            match_score: Match score from screening (0.0-1.0)
            risk_indicators: List of identified risk indicators
            evidence_strength: Strength of supporting evidence

        Returns:
            RoutingResult with tier assignment and decision
        """
        self._result_counter += 1
        result_id = f"ROUTE-{self._result_counter:08d}"

        # Evaluate against each tier (lowest to highest)
        assigned_tier: Optional[str] = None
        decision = RoutingDecision.HOLD
        escalation_reasons: List[EscalationReason] = []
        cleared_indicators: List[str] = []
        blocking_indicators: List[str] = []
        rationale_parts: List[str] = []

        # Check Tier-0
        if self._check_tier_eligibility(
            TIER_0_CRITERIA, risk_score, match_score, risk_indicators, evidence_strength
        ):
            assigned_tier = "TIER-0"
            decision = RoutingDecision.AUTO_CLEAR
            rationale_parts.append("Obvious false positive: no risk signals, low match score")

        # Check Tier-1
        elif self._check_tier_eligibility(
            TIER_1_CRITERIA, risk_score, match_score, risk_indicators, evidence_strength
        ):
            assigned_tier = "TIER-1"
            decision = RoutingDecision.AUTO_CLEAR
            cleared_indicators = [i for i in risk_indicators if i in TIER_1_CRITERIA.allowed_indicators]
            rationale_parts.append("Low-risk false positive: explainable indicators with documentation")

        # Check Tier-2
        elif self._check_tier_eligibility(
            TIER_2_CRITERIA, risk_score, match_score, risk_indicators, evidence_strength
        ):
            assigned_tier = "TIER-2"
            decision = RoutingDecision.ESCALATE_ANALYST
            escalation_reasons.append(EscalationReason.POLICY_REQUIREMENT)
            blocking_indicators = [i for i in risk_indicators if i in TIER_2_CRITERIA.blocked_indicators]
            rationale_parts.append("Requires analyst review: elevated risk signals present")

        # Check Tier-3
        elif self._check_tier_eligibility(
            TIER_3_CRITERIA, risk_score, match_score, risk_indicators, evidence_strength
        ):
            assigned_tier = "TIER-3"
            decision = RoutingDecision.ESCALATE_SENIOR
            escalation_reasons.append(EscalationReason.HIGH_RISK_MATCH)
            escalation_reasons.append(EscalationReason.POLICY_REQUIREMENT)
            blocking_indicators = [i for i in risk_indicators if i in TIER_3_CRITERIA.blocked_indicators]
            rationale_parts.append("Complex case: multiple significant risk factors requiring senior review")

        # Default to Tier-SAR
        else:
            assigned_tier = "TIER-SAR"
            decision = RoutingDecision.ESCALATE_SAR

            # Determine SAR-specific reasons
            if "SANCTIONS_MATCH" in risk_indicators:
                escalation_reasons.append(EscalationReason.SANCTIONS_INVOLVEMENT)
            if any(i.startswith("PEP") for i in risk_indicators):
                escalation_reasons.append(EscalationReason.PEP_INVOLVEMENT)
            if "STRUCTURING" in risk_indicators:
                escalation_reasons.append(EscalationReason.STRUCTURING_DETECTED)
            if risk_score >= 0.9:
                escalation_reasons.append(EscalationReason.SAR_THRESHOLD_MET)

            if not escalation_reasons:
                escalation_reasons.append(EscalationReason.MULTIPLE_RISK_SIGNALS)

            rationale_parts.append("SAR review required: significant risk indicators warrant compliance review")

        # Calculate confidence based on evidence and score alignment
        confidence = self._calculate_confidence(
            assigned_tier, risk_score, match_score, evidence_strength
        )

        return RoutingResult(
            result_id=result_id,
            case_id=case_id,
            decision=decision,
            assigned_tier=assigned_tier,
            confidence=confidence,
            risk_score=risk_score,
            match_score=match_score,
            escalation_reasons=escalation_reasons,
            cleared_indicators=cleared_indicators,
            blocking_indicators=blocking_indicators,
            rationale=" ".join(rationale_parts),
        )

    def _check_tier_eligibility(
        self,
        criteria: TierCriteria,
        risk_score: float,
        match_score: float,
        risk_indicators: List[str],
        evidence_strength: str,
    ) -> bool:
        """Check if a case is eligible for a specific tier."""
        # Check score thresholds
        if risk_score > criteria.max_risk_score:
            return False
        if match_score > criteria.max_match_score:
            return False

        # Check for blocking indicators
        for indicator in risk_indicators:
            if indicator in criteria.blocked_indicators:
                return False

        # Check evidence strength
        strength_order = ["UNVERIFIED", "WEAK", "MODERATE", "STRONG", "VERIFIED"]
        min_idx = strength_order.index(criteria.min_evidence_strength)
        current_idx = strength_order.index(evidence_strength) if evidence_strength in strength_order else 0
        if current_idx < min_idx:
            return False

        return True

    def _calculate_confidence(
        self,
        tier: str,
        risk_score: float,
        match_score: float,
        evidence_strength: str,
    ) -> float:
        """Calculate confidence in routing decision."""
        # Base confidence from evidence strength
        strength_confidence = {
            "VERIFIED": 0.95,
            "STRONG": 0.85,
            "MODERATE": 0.70,
            "WEAK": 0.50,
            "UNVERIFIED": 0.30,
        }
        base = strength_confidence.get(evidence_strength, 0.50)

        # Adjust based on score clarity
        criteria = self._criteria.get(tier)
        if criteria:
            # Higher confidence if scores are well below thresholds
            risk_margin = criteria.max_risk_score - risk_score
            match_margin = criteria.max_match_score - match_score
            margin_bonus = min(0.1, (risk_margin + match_margin) / 4)
            base += margin_bonus

        return min(1.0, base)

    # ───────────────────────────────────────────────────────────────────────────
    # ESCALATION
    # ───────────────────────────────────────────────────────────────────────────

    def create_escalation_context(
        self,
        routing_result: RoutingResult,
        risk_summary: Dict[str, Any],
        evidence_summary: Dict[str, Any],
    ) -> EscalationContext:
        """
        Create escalation context for human review.

        Args:
            routing_result: The routing result requiring escalation
            risk_summary: Summary of identified risks
            evidence_summary: Summary of collected evidence

        Returns:
            EscalationContext for human reviewer
        """
        if not routing_result.requires_escalation:
            raise ValueError(f"Routing result {routing_result.result_id} does not require escalation")

        self._escalation_counter += 1
        context_id = f"ESC-{self._escalation_counter:08d}"

        # Determine urgency
        urgency = self._determine_urgency(routing_result)

        # Generate recommended actions
        recommended_actions = self._generate_recommended_actions(routing_result)

        return EscalationContext(
            context_id=context_id,
            case_id=routing_result.case_id,
            routing_result_id=routing_result.result_id,
            escalation_reasons=routing_result.escalation_reasons,
            risk_summary=risk_summary,
            evidence_summary=evidence_summary,
            recommended_actions=recommended_actions,
            urgency=urgency,
        )

    def _determine_urgency(self, result: RoutingResult) -> str:
        """Determine urgency level for escalation."""
        if result.decision == RoutingDecision.ESCALATE_SAR:
            return "CRITICAL" if result.risk_score >= 0.9 else "HIGH"
        if result.decision == RoutingDecision.ESCALATE_SENIOR:
            return "HIGH" if result.risk_score >= 0.7 else "MEDIUM"
        if result.decision == RoutingDecision.ESCALATE_ANALYST:
            return "MEDIUM" if result.risk_score >= 0.5 else "LOW"
        return "LOW"

    def _generate_recommended_actions(self, result: RoutingResult) -> List[str]:
        """Generate recommended actions for escalated case."""
        actions: List[str] = []

        if EscalationReason.SANCTIONS_INVOLVEMENT in result.escalation_reasons:
            actions.append("Verify sanctions list entry against customer records")
            actions.append("Check for potential name variations or transliterations")

        if EscalationReason.PEP_INVOLVEMENT in result.escalation_reasons:
            actions.append("Review PEP status and political exposure level")
            actions.append("Assess source of funds and wealth")

        if EscalationReason.INSUFFICIENT_EVIDENCE in result.escalation_reasons:
            actions.append("Request additional customer documentation")
            actions.append("Conduct enhanced due diligence")

        if EscalationReason.STRUCTURING_DETECTED in result.escalation_reasons:
            actions.append("Review transaction patterns for intentional structuring")
            actions.append("Interview customer if appropriate")

        if EscalationReason.SAR_THRESHOLD_MET in result.escalation_reasons:
            actions.append("Prepare SAR documentation")
            actions.append("Consult with compliance officer")

        if not actions:
            actions.append("Review all evidence and risk indicators")
            actions.append("Document disposition rationale")

        return actions

    # ───────────────────────────────────────────────────────────────────────────
    # QUERIES
    # ───────────────────────────────────────────────────────────────────────────

    def get_tier_criteria(self, tier_id: str) -> Optional[TierCriteria]:
        """Get criteria for a specific tier."""
        return self._criteria.get(tier_id)

    def list_auto_clearable_tiers(self) -> List[TierCriteria]:
        """List all tiers that allow auto-clearance."""
        return [c for c in self._criteria.values() if c.auto_clearable]

    def generate_report(self) -> Dict[str, Any]:
        """Generate router status report."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_routing_decisions": self._result_counter,
            "total_escalations": self._escalation_counter,
            "configured_tiers": len(self._criteria),
            "auto_clearable_tiers": len(self.list_auto_clearable_tiers()),
            "tier_definitions": [c.to_dict() for c in self._criteria.values()],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "RoutingDecision",
    "EscalationReason",
    # Data Classes
    "TierCriteria",
    "RoutingResult",
    "EscalationContext",
    # Services
    "TierRouter",
    # Default Criteria
    "TIER_0_CRITERIA",
    "TIER_1_CRITERIA",
    "TIER_2_CRITERIA",
    "TIER_3_CRITERIA",
    "TIER_SAR_CRITERIA",
]
