# ═══════════════════════════════════════════════════════════════════════════════
# AML Case Engine — Alert Intake, Case Management, Tier Routing
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: CODY (GID-01)
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Case Engine — Core Case Management Infrastructure

PURPOSE:
    Provide governed case management for AML alerts including:
    - Alert intake and validation
    - Case initialization and lifecycle
    - Evidence collection coordination
    - Tiered decision proposal
    - Narrative construction

TIER DEFINITIONS:
    - Tier-0: Obvious false positive (name similarity only, no risk signals)
    - Tier-1: Low-risk false positive (explainable, documented rationale)
    - Tier-2+: Requires human review (NOT automated in this system)

CONSTRAINTS:
    - NO autonomous Tier-2+ clearance
    - NO unsupervised SAR filing
    - All decisions require ProofPack anchoring
    - FAIL-CLOSED on ambiguity

LANE: EXECUTION (AML GOVERNANCE)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# CASE ENGINE ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class AlertSource(Enum):
    """Source of the AML alert."""

    SANCTIONS_SCREENING = "SANCTIONS_SCREENING"
    TRANSACTION_MONITORING = "TRANSACTION_MONITORING"
    PEP_SCREENING = "PEP_SCREENING"
    ADVERSE_MEDIA = "ADVERSE_MEDIA"
    CUSTOMER_DUE_DILIGENCE = "CUSTOMER_DUE_DILIGENCE"
    MANUAL_REFERRAL = "MANUAL_REFERRAL"
    REGULATORY_REQUEST = "REGULATORY_REQUEST"


class AlertPriority(Enum):
    """Priority level of the alert."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CaseStatus(Enum):
    """Status of an AML case."""

    CREATED = "CREATED"
    EVIDENCE_GATHERING = "EVIDENCE_GATHERING"
    UNDER_REVIEW = "UNDER_REVIEW"
    DECISION_PENDING = "DECISION_PENDING"
    CLEARED = "CLEARED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class CaseTier(Enum):
    """Tier classification for case handling."""

    TIER_0 = "TIER_0"  # Obvious false positive - auto-clearable
    TIER_1 = "TIER_1"  # Low-risk false positive - requires rationale
    TIER_2 = "TIER_2"  # Requires human review
    TIER_3 = "TIER_3"  # Complex case - senior analyst
    TIER_SAR = "TIER_SAR"  # Potential SAR - compliance review


class DecisionOutcome(Enum):
    """Outcome of a case decision."""

    CLEAR = "CLEAR"  # False positive confirmed
    ESCALATE = "ESCALATE"  # Requires higher tier review
    HOLD = "HOLD"  # Pending additional information
    SAR_REVIEW = "SAR_REVIEW"  # Requires SAR consideration


class EvidenceType(Enum):
    """Type of evidence collected for a case."""

    KYC_DATA = "KYC_DATA"
    TRANSACTION_HISTORY = "TRANSACTION_HISTORY"
    SANCTIONS_CHECK = "SANCTIONS_CHECK"
    PEP_CHECK = "PEP_CHECK"
    ADVERSE_MEDIA = "ADVERSE_MEDIA"
    ENTITY_RESOLUTION = "ENTITY_RESOLUTION"
    CUSTOMER_PROFILE = "CUSTOMER_PROFILE"
    ACCOUNT_ACTIVITY = "ACCOUNT_ACTIVITY"
    RELATIONSHIP_MAP = "RELATIONSHIP_MAP"
    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"


# ═══════════════════════════════════════════════════════════════════════════════
# AML ALERT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class AMLAlert:
    """
    Incoming AML alert to be processed.

    Represents a raw alert from screening or monitoring systems
    that requires investigation and disposition.
    """

    alert_id: str
    source: AlertSource
    priority: AlertPriority
    subject_name: str
    subject_id: str
    match_details: Dict[str, Any]
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    match_score: float = 0.0
    list_name: Optional[str] = None
    list_entry_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.alert_id.startswith("ALERT-"):
            raise ValueError(f"Alert ID must start with 'ALERT-': {self.alert_id}")
        if not 0.0 <= self.match_score <= 1.0:
            raise ValueError(f"Match score must be between 0.0 and 1.0: {self.match_score}")

    def compute_alert_hash(self) -> str:
        """Compute deterministic hash of alert content."""
        data = {
            "alert_id": self.alert_id,
            "source": self.source.value,
            "subject_name": self.subject_name,
            "subject_id": self.subject_id,
            "match_details": self.match_details,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "source": self.source.value,
            "priority": self.priority.value,
            "subject_name": self.subject_name,
            "subject_id": self.subject_id,
            "match_details": self.match_details,
            "match_score": self.match_score,
            "list_name": self.list_name,
            "list_entry_id": self.list_entry_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
            "alert_hash": self.compute_alert_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CASE EVIDENCE
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class CaseEvidence:
    """
    Evidence item collected for a case.

    Represents a single piece of evidence with provenance
    and integrity verification.
    """

    evidence_id: str
    evidence_type: EvidenceType
    source_system: str
    collected_at: str
    content: Dict[str, Any]
    confidence: float = 1.0
    provenance_uri: Optional[str] = None
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id.startswith("EVID-"):
            raise ValueError(f"Evidence ID must start with 'EVID-': {self.evidence_id}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0: {self.confidence}")

    def compute_evidence_hash(self) -> str:
        """Compute deterministic hash of evidence content."""
        data = {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "source_system": self.source_system,
            "content": self.content,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "source_system": self.source_system,
            "collected_at": self.collected_at,
            "content": self.content,
            "confidence": self.confidence,
            "provenance_uri": self.provenance_uri,
            "verified": self.verified,
            "evidence_hash": self.compute_evidence_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CASE NARRATIVE
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class CaseNarrative:
    """
    Explainable narrative for case decision.

    Provides human-readable rationale for the decision
    with supporting evidence references.
    """

    narrative_id: str
    summary: str
    key_findings: List[str]
    evidence_refs: List[str]
    risk_indicators: List[str]
    mitigating_factors: List[str]
    recommendation: str
    generated_at: str
    generator: str = "AML_CASE_ENGINE"

    def __post_init__(self) -> None:
        if not self.narrative_id.startswith("NARR-"):
            raise ValueError(f"Narrative ID must start with 'NARR-': {self.narrative_id}")

    def compute_narrative_hash(self) -> str:
        """Compute deterministic hash of narrative."""
        data = {
            "narrative_id": self.narrative_id,
            "summary": self.summary,
            "key_findings": sorted(self.key_findings),
            "recommendation": self.recommendation,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "narrative_id": self.narrative_id,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "evidence_refs": self.evidence_refs,
            "risk_indicators": self.risk_indicators,
            "mitigating_factors": self.mitigating_factors,
            "recommendation": self.recommendation,
            "generated_at": self.generated_at,
            "generator": self.generator,
            "narrative_hash": self.compute_narrative_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CASE DECISION
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class CaseDecision:
    """
    Decision proposal for a case.

    Represents the recommended disposition with full
    audit trail and governance compliance.
    """

    decision_id: str
    case_id: str
    outcome: DecisionOutcome
    tier: CaseTier
    narrative_id: str
    confidence: float
    decided_at: str
    decided_by: str
    approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    proofpack_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.decision_id.startswith("DEC-"):
            raise ValueError(f"Decision ID must start with 'DEC-': {self.decision_id}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0: {self.confidence}")

    @property
    def is_auto_clearable(self) -> bool:
        """Check if decision can be auto-cleared (Tier-0/Tier-1 only)."""
        return (
            self.outcome == DecisionOutcome.CLEAR
            and self.tier in (CaseTier.TIER_0, CaseTier.TIER_1)
            and self.confidence >= 0.95
        )

    @property
    def requires_human_review(self) -> bool:
        """Check if decision requires human review."""
        return self.tier in (CaseTier.TIER_2, CaseTier.TIER_3, CaseTier.TIER_SAR)

    def compute_decision_hash(self) -> str:
        """Compute deterministic hash of decision."""
        data = {
            "decision_id": self.decision_id,
            "case_id": self.case_id,
            "outcome": self.outcome.value,
            "tier": self.tier.value,
            "narrative_id": self.narrative_id,
            "confidence": self.confidence,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "case_id": self.case_id,
            "outcome": self.outcome.value,
            "tier": self.tier.value,
            "narrative_id": self.narrative_id,
            "confidence": self.confidence,
            "decided_at": self.decided_at,
            "decided_by": self.decided_by,
            "approved": self.approved,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "proofpack_id": self.proofpack_id,
            "is_auto_clearable": self.is_auto_clearable,
            "requires_human_review": self.requires_human_review,
            "decision_hash": self.compute_decision_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AML CASE
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class AMLCase:
    """
    AML case under investigation.

    Represents the full lifecycle of an AML case from
    alert intake through disposition.
    """

    case_id: str
    alert: AMLAlert
    status: CaseStatus
    tier: CaseTier
    created_at: str
    evidence: List[CaseEvidence] = field(default_factory=list)
    narrative: Optional[CaseNarrative] = None
    decision: Optional[CaseDecision] = None
    assigned_to: Optional[str] = None
    updated_at: Optional[str] = None
    closed_at: Optional[str] = None
    proofpack_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.case_id.startswith("CASE-"):
            raise ValueError(f"Case ID must start with 'CASE-': {self.case_id}")

    def add_evidence(self, evidence: CaseEvidence) -> None:
        """Add evidence to the case."""
        self.evidence.append(evidence)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def set_narrative(self, narrative: CaseNarrative) -> None:
        """Set the case narrative."""
        self.narrative = narrative
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def set_decision(self, decision: CaseDecision) -> None:
        """Set the case decision."""
        self.decision = decision
        self.status = CaseStatus.DECISION_PENDING
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def close(self, outcome: CaseStatus) -> None:
        """Close the case with specified outcome."""
        if outcome not in (CaseStatus.CLEARED, CaseStatus.ESCALATED, CaseStatus.CLOSED):
            raise ValueError(f"Invalid close outcome: {outcome}")
        self.status = outcome
        self.closed_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.closed_at

    def compute_case_hash(self) -> str:
        """Compute deterministic hash of case state."""
        evidence_hashes = [e.compute_evidence_hash() for e in self.evidence]
        data = {
            "case_id": self.case_id,
            "alert_hash": self.alert.compute_alert_hash(),
            "status": self.status.value,
            "tier": self.tier.value,
            "evidence_hashes": sorted(evidence_hashes),
            "narrative_hash": self.narrative.compute_narrative_hash() if self.narrative else None,
            "decision_hash": self.decision.compute_decision_hash() if self.decision else None,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "alert": self.alert.to_dict(),
            "status": self.status.value,
            "tier": self.tier.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "closed_at": self.closed_at,
            "assigned_to": self.assigned_to,
            "evidence": [e.to_dict() for e in self.evidence],
            "narrative": self.narrative.to_dict() if self.narrative else None,
            "decision": self.decision.to_dict() if self.decision else None,
            "proofpack_id": self.proofpack_id,
            "metadata": self.metadata,
            "case_hash": self.compute_case_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AML CASE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class AMLCaseEngine:
    """
    Central engine for AML case management.

    Provides:
    - Alert intake and validation
    - Case lifecycle management
    - Evidence coordination
    - Decision proposal (Tier-0/Tier-1 ONLY)
    - Audit trail generation
    """

    def __init__(self) -> None:
        self._cases: Dict[str, AMLCase] = {}
        self._alerts: Dict[str, AMLAlert] = {}
        self._case_counter = 0
        self._evidence_counter = 0
        self._narrative_counter = 0
        self._decision_counter = 0

        # Validation callbacks
        self._tier_validators: Dict[CaseTier, Callable[[AMLCase], bool]] = {}
        self._evidence_validators: Dict[EvidenceType, Callable[[CaseEvidence], bool]] = {}

    # ───────────────────────────────────────────────────────────────────────────
    # ALERT INTAKE
    # ───────────────────────────────────────────────────────────────────────────

    def intake_alert(self, alert: AMLAlert) -> AMLCase:
        """
        Intake an AML alert and create a case.

        Args:
            alert: The AML alert to process

        Returns:
            The created AML case
        """
        self._alerts[alert.alert_id] = alert

        # Determine initial tier based on alert properties
        initial_tier = self._classify_initial_tier(alert)

        self._case_counter += 1
        case_id = f"CASE-{self._case_counter:08d}"

        case = AMLCase(
            case_id=case_id,
            alert=alert,
            status=CaseStatus.CREATED,
            tier=initial_tier,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self._cases[case_id] = case
        return case

    def _classify_initial_tier(self, alert: AMLAlert) -> CaseTier:
        """Classify initial tier based on alert properties."""
        # Low match score and no critical indicators -> Tier-0
        if alert.match_score < 0.5 and alert.priority == AlertPriority.LOW:
            return CaseTier.TIER_0

        # Medium confidence -> Tier-1
        if alert.match_score < 0.8 and alert.priority in (AlertPriority.LOW, AlertPriority.MEDIUM):
            return CaseTier.TIER_1

        # High confidence or critical -> Tier-2+
        if alert.priority == AlertPriority.CRITICAL:
            return CaseTier.TIER_3

        return CaseTier.TIER_2

    # ───────────────────────────────────────────────────────────────────────────
    # EVIDENCE MANAGEMENT
    # ───────────────────────────────────────────────────────────────────────────

    def add_evidence(
        self,
        case_id: str,
        evidence_type: EvidenceType,
        source_system: str,
        content: Dict[str, Any],
        confidence: float = 1.0,
        provenance_uri: Optional[str] = None,
    ) -> CaseEvidence:
        """
        Add evidence to a case.

        Args:
            case_id: The case to add evidence to
            evidence_type: Type of evidence
            source_system: Source system identifier
            content: Evidence content
            confidence: Confidence level (0.0-1.0)
            provenance_uri: URI for evidence provenance

        Returns:
            The created evidence record
        """
        case = self._cases.get(case_id)
        if case is None:
            raise ValueError(f"Case not found: {case_id}")

        self._evidence_counter += 1
        evidence_id = f"EVID-{self._evidence_counter:08d}"

        evidence = CaseEvidence(
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            source_system=source_system,
            collected_at=datetime.now(timezone.utc).isoformat(),
            content=content,
            confidence=confidence,
            provenance_uri=provenance_uri,
        )

        # Validate if validator exists
        validator = self._evidence_validators.get(evidence_type)
        if validator:
            evidence.verified = validator(evidence)

        case.add_evidence(evidence)
        case.status = CaseStatus.EVIDENCE_GATHERING

        return evidence

    # ───────────────────────────────────────────────────────────────────────────
    # NARRATIVE GENERATION
    # ───────────────────────────────────────────────────────────────────────────

    def generate_narrative(
        self,
        case_id: str,
        summary: str,
        key_findings: List[str],
        risk_indicators: List[str],
        mitigating_factors: List[str],
        recommendation: str,
    ) -> CaseNarrative:
        """
        Generate a narrative for a case.

        Args:
            case_id: The case to generate narrative for
            summary: Summary of findings
            key_findings: List of key findings
            risk_indicators: Identified risk indicators
            mitigating_factors: Factors that mitigate risk
            recommendation: Recommended disposition

        Returns:
            The generated narrative
        """
        case = self._cases.get(case_id)
        if case is None:
            raise ValueError(f"Case not found: {case_id}")

        self._narrative_counter += 1
        narrative_id = f"NARR-{self._narrative_counter:08d}"

        evidence_refs = [e.evidence_id for e in case.evidence]

        narrative = CaseNarrative(
            narrative_id=narrative_id,
            summary=summary,
            key_findings=key_findings,
            evidence_refs=evidence_refs,
            risk_indicators=risk_indicators,
            mitigating_factors=mitigating_factors,
            recommendation=recommendation,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        case.set_narrative(narrative)
        return narrative

    # ───────────────────────────────────────────────────────────────────────────
    # DECISION PROPOSAL
    # ───────────────────────────────────────────────────────────────────────────

    def propose_decision(
        self,
        case_id: str,
        outcome: DecisionOutcome,
        confidence: float,
        decided_by: str = "AML_CASE_ENGINE",
    ) -> CaseDecision:
        """
        Propose a decision for a case.

        NOTE: This engine can only propose CLEAR for Tier-0/Tier-1 cases.
        All Tier-2+ cases must be escalated.

        Args:
            case_id: The case to decide
            outcome: Proposed outcome
            confidence: Confidence level
            decided_by: Agent/system making decision

        Returns:
            The decision proposal

        Raises:
            ValueError: If attempting to clear a Tier-2+ case
        """
        case = self._cases.get(case_id)
        if case is None:
            raise ValueError(f"Case not found: {case_id}")

        if case.narrative is None:
            raise ValueError(f"Case {case_id} requires narrative before decision")

        # GOVERNANCE CONSTRAINT: Cannot auto-clear Tier-2+
        if outcome == DecisionOutcome.CLEAR and case.tier not in (CaseTier.TIER_0, CaseTier.TIER_1):
            raise ValueError(
                f"Cannot auto-clear case {case_id} at tier {case.tier.value}. "
                "Only Tier-0 and Tier-1 cases can be auto-cleared. "
                "Use ESCALATE for higher tiers."
            )

        self._decision_counter += 1
        decision_id = f"DEC-{self._decision_counter:08d}"

        decision = CaseDecision(
            decision_id=decision_id,
            case_id=case_id,
            outcome=outcome,
            tier=case.tier,
            narrative_id=case.narrative.narrative_id,
            confidence=confidence,
            decided_at=datetime.now(timezone.utc).isoformat(),
            decided_by=decided_by,
        )

        case.set_decision(decision)
        return decision

    # ───────────────────────────────────────────────────────────────────────────
    # CASE LIFECYCLE
    # ───────────────────────────────────────────────────────────────────────────

    def approve_decision(
        self,
        case_id: str,
        approved_by: str,
        proofpack_id: Optional[str] = None,
    ) -> bool:
        """
        Approve a pending decision.

        Args:
            case_id: The case to approve
            approved_by: Who is approving
            proofpack_id: Associated proofpack

        Returns:
            True if approved successfully
        """
        case = self._cases.get(case_id)
        if case is None:
            raise ValueError(f"Case not found: {case_id}")

        if case.decision is None:
            raise ValueError(f"Case {case_id} has no pending decision")

        # GOVERNANCE CONSTRAINT: Cannot approve Tier-2+ without escalation
        if case.decision.requires_human_review:
            raise ValueError(
                f"Case {case_id} requires human review (Tier {case.tier.value}). "
                "Cannot auto-approve."
            )

        case.decision.approved = True
        case.decision.approved_by = approved_by
        case.decision.approved_at = datetime.now(timezone.utc).isoformat()
        case.decision.proofpack_id = proofpack_id
        case.proofpack_id = proofpack_id

        # Close case based on decision
        if case.decision.outcome == DecisionOutcome.CLEAR:
            case.close(CaseStatus.CLEARED)
        elif case.decision.outcome == DecisionOutcome.ESCALATE:
            case.close(CaseStatus.ESCALATED)

        return True

    def escalate_case(self, case_id: str, reason: str) -> None:
        """
        Escalate a case to higher tier review.

        Args:
            case_id: The case to escalate
            reason: Reason for escalation
        """
        case = self._cases.get(case_id)
        if case is None:
            raise ValueError(f"Case not found: {case_id}")

        case.metadata["escalation_reason"] = reason
        case.metadata["escalated_at"] = datetime.now(timezone.utc).isoformat()
        case.close(CaseStatus.ESCALATED)

    # ───────────────────────────────────────────────────────────────────────────
    # QUERIES
    # ───────────────────────────────────────────────────────────────────────────

    def get_case(self, case_id: str) -> Optional[AMLCase]:
        """Get a case by ID."""
        return self._cases.get(case_id)

    def get_cases_by_status(self, status: CaseStatus) -> List[AMLCase]:
        """Get all cases with a specific status."""
        return [c for c in self._cases.values() if c.status == status]

    def get_cases_by_tier(self, tier: CaseTier) -> List[AMLCase]:
        """Get all cases at a specific tier."""
        return [c for c in self._cases.values() if c.tier == tier]

    def get_pending_decisions(self) -> List[AMLCase]:
        """Get all cases with pending decisions."""
        return [c for c in self._cases.values() if c.status == CaseStatus.DECISION_PENDING]

    def get_auto_clearable_cases(self) -> List[AMLCase]:
        """Get all cases that can be auto-cleared."""
        return [
            c for c in self._cases.values()
            if c.decision is not None and c.decision.is_auto_clearable
        ]

    # ───────────────────────────────────────────────────────────────────────────
    # REPORTING
    # ───────────────────────────────────────────────────────────────────────────

    def generate_report(self) -> Dict[str, Any]:
        """Generate engine status report."""
        cases_by_status = {}
        for status in CaseStatus:
            cases_by_status[status.value] = len(self.get_cases_by_status(status))

        cases_by_tier = {}
        for tier in CaseTier:
            cases_by_tier[tier.value] = len(self.get_cases_by_tier(tier))

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_cases": len(self._cases),
            "total_alerts": len(self._alerts),
            "cases_by_status": cases_by_status,
            "cases_by_tier": cases_by_tier,
            "pending_decisions": len(self.get_pending_decisions()),
            "auto_clearable": len(self.get_auto_clearable_cases()),
            "evidence_records": self._evidence_counter,
            "narratives_generated": self._narrative_counter,
            "decisions_made": self._decision_counter,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "AlertSource",
    "AlertPriority",
    "CaseStatus",
    "CaseTier",
    "DecisionOutcome",
    "EvidenceType",
    # Data Classes
    "AMLAlert",
    "AMLCase",
    "CaseEvidence",
    "CaseDecision",
    "CaseNarrative",
    # Services
    "AMLCaseEngine",
]
