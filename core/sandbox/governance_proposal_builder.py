"""
Governance Proposal Builder - Proposal Generation from Sandbox Insights
PAC-P752-GOV-SANDBOX-GOVERNANCE-EVOLUTION
TASK-04: Governance Proposal Generator (GID-05)

Generates governance proposals from sandbox pattern analysis.
Proposals are SUGGESTIONS - they require explicit PAC approval to become rules.

Core Law: Sandbox observes. Humans decide. Production evolves only through PAC.

INVARIANTS ENFORCED:
- INV-SDGE-001: Sandbox data SHALL NOT modify production logic directly
- INV-SDGE-002: All governance evolution requires explicit PAC approval
- INV-SDGE-003: Audit trail completeness mandatory
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pathlib import Path


class ProposalType(Enum):
    """Types of governance proposals."""
    NEW_INVARIANT = "NEW_INVARIANT"
    INVARIANT_MODIFICATION = "INVARIANT_MODIFICATION"
    PROOF_SCHEMA_STANDARDIZATION = "PROOF_SCHEMA_STANDARDIZATION"
    DECISION_LOGIC_CLARIFICATION = "DECISION_LOGIC_CLARIFICATION"
    COVERAGE_EXPANSION = "COVERAGE_EXPANSION"
    RULE_CONSOLIDATION = "RULE_CONSOLIDATION"


class ProposalStatus(Enum):
    """Status of a governance proposal."""
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CONVERTED_TO_PAC = "CONVERTED_TO_PAC"


class ProposalPriority(Enum):
    """Priority levels for proposals."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class InvariantProposal:
    """Proposal for a new or modified invariant."""
    invariant_id: str
    name: str
    rule: str
    enforcement: str
    violation_action: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "name": self.name,
            "rule": self.rule,
            "enforcement": self.enforcement,
            "violation_action": self.violation_action,
            "rationale": self.rationale
        }


@dataclass
class GovernanceProposal:
    """
    A proposal for governance evolution.
    
    CRITICAL: This is a SUGGESTION only.
    Production modification requires explicit PAC approval.
    """
    proposal_id: str
    proposal_type: ProposalType
    title: str
    description: str
    priority: ProposalPriority
    status: ProposalStatus = ProposalStatus.DRAFT
    
    # Source information
    source_patterns: list[str] = field(default_factory=list)
    source_analysis_id: Optional[str] = None
    
    # Proposed changes
    proposed_invariant: Optional[InvariantProposal] = None
    proposed_schema: Optional[dict[str, Any]] = None
    proposed_rule_changes: list[dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    confidence_score: float = 0.0
    supporting_evidence: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    # Review information
    reviewed_by: Optional[str] = None
    review_decision: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    
    # PAC conversion
    converted_to_pac: Optional[str] = None
    
    proposal_hash: str = ""

    def __post_init__(self):
        if not self.proposal_hash:
            self.proposal_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        data = json.dumps({
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type.value,
            "title": self.title,
            "created_at": self.created_at.isoformat()
        }, sort_keys=True)
        return f"sha3-256:{hashlib.sha3_256(data.encode()).hexdigest()[:32]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type.value,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "source_patterns": self.source_patterns,
            "source_analysis_id": self.source_analysis_id,
            "proposed_invariant": self.proposed_invariant.to_dict() if self.proposed_invariant else None,
            "proposed_schema": self.proposed_schema,
            "proposed_rule_changes": self.proposed_rule_changes,
            "confidence_score": self.confidence_score,
            "supporting_evidence": self.supporting_evidence,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "reviewed_by": self.reviewed_by,
            "review_decision": self.review_decision,
            "review_notes": self.review_notes,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "converted_to_pac": self.converted_to_pac,
            "proposal_hash": self.proposal_hash
        }


class GovernanceProposalBuilder:
    """
    Builds governance proposals from sandbox pattern analysis.
    
    Core Law: Sandbox observes. Humans decide. Production evolves only through PAC.
    
    This builder:
    - Analyzes detected patterns
    - Generates structured proposals
    - NEVER applies changes directly
    - Requires PAC approval for any production modification
    """

    OUTPUT_MODE = "PROPOSAL_ONLY"
    AUTO_ENFORCEMENT = False
    MAX_PROPOSALS_PER_CYCLE = 5

    def __init__(self):
        self._proposals: list[GovernanceProposal] = []
        self._proposal_log: list[dict[str, Any]] = []

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}-{secrets.token_hex(6).upper()}"

    def _log_proposal(self, event: str, details: dict[str, Any]) -> None:
        self._proposal_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": details,
            "output_mode": self.OUTPUT_MODE,
            "auto_enforcement": self.AUTO_ENFORCEMENT
        })

    def generate_from_invariant_gap(
        self,
        pattern: dict[str, Any],
        analysis_id: Optional[str] = None
    ) -> GovernanceProposal:
        """
        Generate proposal from detected invariant gap.
        """
        evidence = pattern.get("evidence", {})
        block_reason = evidence.get("block_reason", "UNKNOWN")
        occurrence_count = evidence.get("occurrence_count", 0)

        # Derive invariant ID from block reason
        invariant_id = f"INV-{block_reason.upper().replace(' ', '-')[:20]}"

        proposed_invariant = InvariantProposal(
            invariant_id=invariant_id,
            name=f"Formalized: {block_reason}",
            rule=f"Actions triggering '{block_reason}' SHALL be blocked",
            enforcement="HARD_BLOCK",
            violation_action="BLOCK",
            rationale=f"Derived from {occurrence_count} sandbox blocked attempts"
        )

        priority = ProposalPriority.HIGH if occurrence_count > 10 else ProposalPriority.MEDIUM

        proposal = GovernanceProposal(
            proposal_id=self._generate_id("PROP"),
            proposal_type=ProposalType.NEW_INVARIANT,
            title=f"New Invariant: {block_reason}",
            description=f"Formalize invariant for block reason '{block_reason}' observed {occurrence_count} times in sandbox",
            priority=priority,
            source_patterns=[pattern.get("pattern_id", "")],
            source_analysis_id=analysis_id,
            proposed_invariant=proposed_invariant,
            confidence_score=pattern.get("confidence", 0.0),
            supporting_evidence=evidence
        )

        self._proposals.append(proposal)
        self._log_proposal("PROPOSAL_GENERATED", {
            "proposal_id": proposal.proposal_id,
            "type": "NEW_INVARIANT",
            "from_pattern": pattern.get("pattern_id")
        })

        return proposal

    def generate_from_proof_ambiguity(
        self,
        pattern: dict[str, Any],
        analysis_id: Optional[str] = None
    ) -> GovernanceProposal:
        """
        Generate proposal from detected proof ambiguity.
        """
        evidence = pattern.get("evidence", {})
        proof_type = evidence.get("proof_type", "UNKNOWN")
        common_keys = evidence.get("common_keys", [])
        all_keys = evidence.get("all_keys", [])

        proposed_schema = {
            "proof_type": proof_type,
            "required_fields": common_keys,
            "optional_fields": list(set(all_keys) - set(common_keys)),
            "validation": "STRICT"
        }

        proposal = GovernanceProposal(
            proposal_id=self._generate_id("PROP"),
            proposal_type=ProposalType.PROOF_SCHEMA_STANDARDIZATION,
            title=f"Standardize Proof Schema: {proof_type}",
            description=f"Standardize proof schema for '{proof_type}' to ensure consistent evidence collection",
            priority=ProposalPriority.MEDIUM,
            source_patterns=[pattern.get("pattern_id", "")],
            source_analysis_id=analysis_id,
            proposed_schema=proposed_schema,
            confidence_score=pattern.get("confidence", 0.0),
            supporting_evidence=evidence
        )

        self._proposals.append(proposal)
        self._log_proposal("PROPOSAL_GENERATED", {
            "proposal_id": proposal.proposal_id,
            "type": "PROOF_SCHEMA_STANDARDIZATION",
            "from_pattern": pattern.get("pattern_id")
        })

        return proposal

    def generate_from_decision_inconsistency(
        self,
        pattern: dict[str, Any],
        analysis_id: Optional[str] = None
    ) -> GovernanceProposal:
        """
        Generate proposal from detected decision inconsistency.
        """
        evidence = pattern.get("evidence", {})
        invariants = evidence.get("invariants", [])
        decision_distribution = evidence.get("decision_distribution", {})

        proposed_changes = [{
            "change_type": "DECISION_LOGIC_CLARIFICATION",
            "affected_invariants": invariants,
            "current_behavior": decision_distribution,
            "proposed_behavior": "Consistent decision based on dominant pattern",
            "requires_review": True
        }]

        proposal = GovernanceProposal(
            proposal_id=self._generate_id("PROP"),
            proposal_type=ProposalType.DECISION_LOGIC_CLARIFICATION,
            title=f"Clarify Decision Logic for {len(invariants)} Invariants",
            description=f"Resolve inconsistent decisions observed for invariants: {', '.join(invariants[:3])}",
            priority=ProposalPriority.HIGH,
            source_patterns=[pattern.get("pattern_id", "")],
            source_analysis_id=analysis_id,
            proposed_rule_changes=proposed_changes,
            confidence_score=pattern.get("confidence", 0.0),
            supporting_evidence=evidence
        )

        self._proposals.append(proposal)
        self._log_proposal("PROPOSAL_GENERATED", {
            "proposal_id": proposal.proposal_id,
            "type": "DECISION_LOGIC_CLARIFICATION",
            "from_pattern": pattern.get("pattern_id")
        })

        return proposal

    def generate_from_coverage_gap(
        self,
        pattern: dict[str, Any],
        analysis_id: Optional[str] = None
    ) -> GovernanceProposal:
        """
        Generate proposal from detected coverage gap.
        """
        evidence = pattern.get("evidence", {})
        invariant = evidence.get("invariant", "UNKNOWN")

        proposed_changes = [{
            "change_type": "COVERAGE_EXPANSION",
            "invariant": invariant,
            "recommendation": "Create sandbox scenarios to exercise this invariant",
            "alternative": "Deprecate if no longer relevant"
        }]

        proposal = GovernanceProposal(
            proposal_id=self._generate_id("PROP"),
            proposal_type=ProposalType.COVERAGE_EXPANSION,
            title=f"Expand Coverage: {invariant}",
            description=f"Invariant '{invariant}' was never exercised in sandbox - expand test coverage or evaluate relevance",
            priority=ProposalPriority.LOW,
            source_patterns=[pattern.get("pattern_id", "")],
            source_analysis_id=analysis_id,
            proposed_rule_changes=proposed_changes,
            confidence_score=1.0,
            supporting_evidence=evidence
        )

        self._proposals.append(proposal)
        self._log_proposal("PROPOSAL_GENERATED", {
            "proposal_id": proposal.proposal_id,
            "type": "COVERAGE_EXPANSION",
            "from_pattern": pattern.get("pattern_id")
        })

        return proposal

    def build_proposals_from_analysis(
        self,
        analysis_result: dict[str, Any]
    ) -> list[GovernanceProposal]:
        """
        Build governance proposals from complete analysis result.
        
        Respects MAX_PROPOSALS_PER_CYCLE limit.
        """
        proposals = []
        analysis_id = analysis_result.get("analysis_id")
        patterns = analysis_result.get("patterns", [])

        # Sort patterns by severity and confidence
        sorted_patterns = sorted(
            patterns,
            key=lambda p: (
                {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}.get(p.get("severity", "INFO"), 5),
                -p.get("confidence", 0)
            )
        )

        for pattern in sorted_patterns[:self.MAX_PROPOSALS_PER_CYCLE]:
            pattern_type = pattern.get("pattern_type", "")
            
            try:
                if pattern_type == "INVARIANT_GAP":
                    proposals.append(self.generate_from_invariant_gap(pattern, analysis_id))
                elif pattern_type == "PROOF_AMBIGUITY":
                    proposals.append(self.generate_from_proof_ambiguity(pattern, analysis_id))
                elif pattern_type == "DECISION_INCONSISTENCY":
                    proposals.append(self.generate_from_decision_inconsistency(pattern, analysis_id))
                elif pattern_type == "COVERAGE_GAP":
                    proposals.append(self.generate_from_coverage_gap(pattern, analysis_id))
            except Exception as e:
                self._log_proposal("PROPOSAL_GENERATION_ERROR", {
                    "pattern_id": pattern.get("pattern_id"),
                    "error": str(e)
                })

        self._log_proposal("BATCH_PROPOSALS_GENERATED", {
            "analysis_id": analysis_id,
            "patterns_processed": len(sorted_patterns[:self.MAX_PROPOSALS_PER_CYCLE]),
            "proposals_generated": len(proposals)
        })

        return proposals

    def submit_for_review(self, proposal_id: str) -> bool:
        """Submit a proposal for human review."""
        for proposal in self._proposals:
            if proposal.proposal_id == proposal_id:
                proposal.status = ProposalStatus.PENDING_REVIEW
                self._log_proposal("SUBMITTED_FOR_REVIEW", {
                    "proposal_id": proposal_id
                })
                return True
        return False

    def record_review_decision(
        self,
        proposal_id: str,
        reviewer: str,
        decision: str,
        notes: Optional[str] = None
    ) -> bool:
        """Record human review decision on a proposal."""
        for proposal in self._proposals:
            if proposal.proposal_id == proposal_id:
                proposal.reviewed_by = reviewer
                proposal.review_decision = decision
                proposal.review_notes = notes
                proposal.reviewed_at = datetime.now(timezone.utc)
                
                if decision.upper() == "APPROVED":
                    proposal.status = ProposalStatus.APPROVED
                elif decision.upper() == "REJECTED":
                    proposal.status = ProposalStatus.REJECTED
                
                self._log_proposal("REVIEW_RECORDED", {
                    "proposal_id": proposal_id,
                    "reviewer": reviewer,
                    "decision": decision
                })
                return True
        return False

    def convert_to_pac(self, proposal_id: str, pac_id: str) -> bool:
        """
        Mark proposal as converted to PAC.
        
        This does NOT apply the change - PAC execution does.
        """
        for proposal in self._proposals:
            if proposal.proposal_id == proposal_id:
                if proposal.status != ProposalStatus.APPROVED:
                    return False
                    
                proposal.status = ProposalStatus.CONVERTED_TO_PAC
                proposal.converted_to_pac = pac_id
                
                self._log_proposal("CONVERTED_TO_PAC", {
                    "proposal_id": proposal_id,
                    "pac_id": pac_id
                })
                return True
        return False

    def get_pending_proposals(self) -> list[GovernanceProposal]:
        """Get proposals pending review."""
        return [p for p in self._proposals if p.status == ProposalStatus.PENDING_REVIEW]

    def get_approved_proposals(self) -> list[GovernanceProposal]:
        """Get approved proposals not yet converted to PAC."""
        return [p for p in self._proposals if p.status == ProposalStatus.APPROVED]

    def export(self) -> dict[str, Any]:
        """Export builder state."""
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "output_mode": self.OUTPUT_MODE,
            "auto_enforcement": self.AUTO_ENFORCEMENT,
            "max_proposals_per_cycle": self.MAX_PROPOSALS_PER_CYCLE,
            "proposals": [p.to_dict() for p in self._proposals],
            "summary": {
                "total": len(self._proposals),
                "by_status": {
                    status.value: len([p for p in self._proposals if p.status == status])
                    for status in ProposalStatus
                }
            }
        }


# Singleton instance
_proposal_builder: Optional[GovernanceProposalBuilder] = None


def get_governance_proposal_builder() -> GovernanceProposalBuilder:
    """Get global proposal builder instance."""
    global _proposal_builder
    if _proposal_builder is None:
        _proposal_builder = GovernanceProposalBuilder()
    return _proposal_builder
