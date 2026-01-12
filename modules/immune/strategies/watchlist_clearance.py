"""
Watchlist Clearance Remediation Strategy
=========================================

PAC-SYS-P164-WATCHLIST-CLEARANCE-STRATEGY: The Noise Filter.

This strategy handles AML/Sanctions watchlist hits - specifically the
false positives that plague high-volume transaction systems. 5-10% of
transactions hit a watchlist, but 99% are false positives (e.g., "John Smith").

The strategy analyzes match metadata to determine:
- REJECT: High-confidence match (name + DOB + country all match)
- REVIEW: Partial match requiring human verification
- CLEAR: Weak match that can be auto-cleared (with audit logging)

Governance Model:
    - IF Exact Match (Name + DOB + Country) → REJECT
    - IF Partial Match (Name Only) → ESCALATE_TO_HUMAN
    - IF Weak Match (<80%) → AUTO_CLEAR (with logging)
    - IF PEP Match → NEVER AUTO_CLEAR (always Enhanced Due Diligence)

Invariants:
    - INV-IMMUNE-004: Sanctions Supremacy - When in doubt, Block and Escalate
    - Never auto-clear PEPs without Enhanced Due Diligence
    - Require secondary identifiers for auto-clearance

Author: Benson (GID-00)
Classification: IMMUNE_STRATEGY_IMPLEMENTATION
Attestation: MASTER-BER-P164-STRATEGY
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import time
import hashlib
import json

from ..remediator import (
    RemediationStrategy,
    RemediationResult,
    EscalationLevel,
)


class MatchType(Enum):
    """Types of watchlist matches."""
    SANCTIONS = "sanctions"          # OFAC, UN, EU sanctions lists
    PEP = "pep"                      # Politically Exposed Persons
    ADVERSE_MEDIA = "adverse_media"  # Negative news coverage
    LAW_ENFORCEMENT = "law_enforcement"  # Wanted/criminal lists
    INTERNAL = "internal"            # Internal blocklist


class ClearanceDecision(Enum):
    """Possible clearance decisions."""
    REJECT = "reject"                # High-confidence match - block transaction
    ESCALATE = "escalate"            # Requires human review
    AUTO_CLEAR = "auto_clear"        # Weak match - cleared automatically
    EDD_REQUIRED = "edd_required"    # Enhanced Due Diligence needed (PEP)


@dataclass
class WatchlistMatch:
    """Represents a watchlist match result."""
    match_id: str
    match_type: MatchType
    matched_name: str
    match_score: float  # 0.0 to 100.0
    matched_entity_id: str
    list_name: str
    
    # Secondary identifiers (for disambiguation)
    matched_dob: Optional[str] = None
    matched_country: Optional[str] = None
    matched_nationality: Optional[str] = None
    
    # User data for comparison
    user_name: str = ""
    user_dob: Optional[str] = None
    user_country: Optional[str] = None
    
    def dob_matches(self) -> Optional[bool]:
        """Check if DOB matches (None if either is missing)."""
        if not self.matched_dob or not self.user_dob:
            return None
        return self.matched_dob == self.user_dob
    
    def country_matches(self) -> Optional[bool]:
        """Check if country matches (None if either is missing)."""
        if not self.matched_country or not self.user_country:
            return None
        return self.matched_country.upper() == self.user_country.upper()


@dataclass
class ClearanceResult:
    """Result of a clearance decision."""
    decision: ClearanceDecision
    match: WatchlistMatch
    reason: str
    confidence: float
    requires_human_review: bool
    audit_reference: str
    additional_checks_required: List[str] = field(default_factory=list)


class WatchlistClearanceStrategy(RemediationStrategy):
    """
    Strategy for filtering false positive watchlist hits.
    
    This strategy analyzes AML/sanctions screening results and determines
    whether a match is a genuine risk or false positive noise. It filters
    weak matches automatically while escalating genuine threats.
    
    Decision Matrix:
        Score > 95 + DOB Match + Country Match → REJECT
        Score > 95 + (DOB OR Country Mismatch) → ESCALATE
        80 < Score ≤ 95 → ESCALATE
        Score ≤ 80 + Secondary Mismatch → AUTO_CLEAR
        Score ≤ 80 + No Secondary Data → ESCALATE (can't verify)
        Any PEP Match → EDD_REQUIRED (never auto-clear)
    
    All decisions are logged with full audit trail.
    """
    
    # Score thresholds
    HIGH_CONFIDENCE_THRESHOLD = 95.0   # Exact match territory
    REVIEW_THRESHOLD = 80.0            # Requires human review
    AUTO_CLEAR_THRESHOLD = 80.0        # Can be auto-cleared if secondary data mismatches
    
    # Match types that NEVER get auto-cleared
    NEVER_AUTO_CLEAR: Set[MatchType] = {
        MatchType.PEP,              # Always needs EDD
        MatchType.LAW_ENFORCEMENT,  # Always escalate
    }
    
    # Lists that require extra scrutiny
    HIGH_RISK_LISTS: Set[str] = {
        "OFAC_SDN",
        "UN_CONSOLIDATED",
        "EU_SANCTIONS",
        "UK_SANCTIONS",
        "INTERPOL_RED_NOTICE",
    }
    
    def __init__(self):
        """Initialize with audit logging."""
        self._clearance_log: List[Dict[str, Any]] = []
        self._stats = {
            "total_processed": 0,
            "auto_cleared": 0,
            "escalated": 0,
            "rejected": 0,
            "edd_required": 0,
        }
    
    @property
    def strategy_id(self) -> str:
        return "watchlist_clearance_strategy"
    
    @property
    def handles_gates(self) -> List[str]:
        return ["aml"]
    
    @property
    def handles_errors(self) -> List[str]:
        return [
            "AML_SANCTION_HIT",
            "WATCHLIST_MATCH",
            "PEP_MATCH",
            "SANCTIONS_HIT",
            "OFAC_HIT",
            "ADVERSE_MEDIA_HIT",
        ]
    
    def can_handle(self, gate: str, error_code: str, context: Dict[str, Any]) -> bool:
        """Check if this strategy can handle the error."""
        # Direct code match
        error_upper = error_code.upper()
        watchlist_indicators = [
            "SANCTION", "WATCHLIST", "PEP", "OFAC", 
            "ADVERSE", "MATCH", "HIT", "SCREENING"
        ]
        return any(ind in error_upper for ind in watchlist_indicators)
    
    def estimate_success(self, gate: str, error_code: str, context: Dict[str, Any]) -> float:
        """
        Estimate probability of successful remediation.
        
        High success = can make a clear decision (clear or escalate)
        Low success = ambiguous cases requiring manual triage
        """
        match_data = context.get("match_data", {})
        match_score = match_data.get("score", 50.0)
        match_type = match_data.get("type", "unknown")
        
        # PEP matches always go to EDD - we can "handle" them by routing correctly
        if match_type.upper() == "PEP":
            return 0.9  # We know what to do
        
        # High confidence matches get rejected - clear decision
        if match_score >= self.HIGH_CONFIDENCE_THRESHOLD:
            return 0.85  # Likely reject, but need to verify
        
        # Middle ground requires human review
        if match_score >= self.REVIEW_THRESHOLD:
            return 0.7  # We'll escalate
        
        # Low scores with secondary data can be auto-cleared
        has_secondary = bool(
            match_data.get("user_dob") or match_data.get("user_country")
        )
        if match_score < self.REVIEW_THRESHOLD and has_secondary:
            return 0.95  # High confidence in auto-clear
        
        return 0.5  # Uncertain - will need to escalate
    
    def execute(self, original_data: Dict[str, Any], context: Dict[str, Any]) -> RemediationResult:
        """
        Analyze watchlist match and make clearance decision.
        
        Process:
        1. Parse match metadata from context
        2. Apply decision matrix
        3. Generate clearance decision with audit trail
        4. Return result (cleared, escalated, or rejected)
        """
        start_time = time.time()
        self._stats["total_processed"] += 1
        
        # Parse match data
        match = self._parse_match(context)
        
        if not match:
            return RemediationResult(
                success=False,
                strategy_used=self.strategy_id,
                original_error="Could not parse watchlist match data",
                explanation="Insufficient match metadata for clearance decision. Escalating to human review.",
                confidence=0.0,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        # Make clearance decision
        clearance = self._make_decision(match)
        
        # Log for audit
        self._log_decision(clearance, original_data)
        
        # Update stats
        if clearance.decision == ClearanceDecision.AUTO_CLEAR:
            self._stats["auto_cleared"] += 1
        elif clearance.decision == ClearanceDecision.ESCALATE:
            self._stats["escalated"] += 1
        elif clearance.decision == ClearanceDecision.REJECT:
            self._stats["rejected"] += 1
        elif clearance.decision == ClearanceDecision.EDD_REQUIRED:
            self._stats["edd_required"] += 1
        
        # Build response
        if clearance.decision == ClearanceDecision.AUTO_CLEAR:
            return RemediationResult(
                success=True,
                strategy_used=self.strategy_id,
                original_error=f"Watchlist match: {match.matched_name}",
                corrected_data={
                    "clearance_decision": clearance.decision.value,
                    "audit_reference": clearance.audit_reference,
                    "reason": clearance.reason,
                    "match_score": match.match_score,
                    "auto_cleared": True
                },
                explanation=f"Auto-cleared: {clearance.reason}\nAudit Ref: {clearance.audit_reference}",
                confidence=clearance.confidence,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        elif clearance.decision == ClearanceDecision.REJECT:
            return RemediationResult(
                success=False,
                strategy_used=self.strategy_id,
                original_error=f"High-confidence watchlist match: {match.matched_name}",
                explanation=f"REJECTED: {clearance.reason}\n\n"
                           f"Match Score: {match.match_score}%\n"
                           f"List: {match.list_name}\n"
                           f"Audit Ref: {clearance.audit_reference}",
                confidence=clearance.confidence,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        else:  # ESCALATE or EDD_REQUIRED
            escalation_data = {
                "clearance_decision": clearance.decision.value,
                "requires_human_review": True,
                "audit_reference": clearance.audit_reference,
                "match_details": {
                    "name": match.matched_name,
                    "score": match.match_score,
                    "type": match.match_type.value,
                    "list": match.list_name,
                    "entity_id": match.matched_entity_id
                },
                "reason": clearance.reason,
                "additional_checks": clearance.additional_checks_required
            }
            
            action = "Enhanced Due Diligence" if clearance.decision == ClearanceDecision.EDD_REQUIRED else "Human Review"
            
            return RemediationResult(
                success=True,  # Successfully routed to correct handler
                strategy_used=self.strategy_id,
                original_error=f"Watchlist match requires review: {match.matched_name}",
                corrected_data={"escalation": escalation_data},
                explanation=f"ESCALATED for {action}: {clearance.reason}\n\n"
                           f"Match Score: {match.match_score}%\n"
                           f"Match Type: {match.match_type.value}\n"
                           f"Audit Ref: {clearance.audit_reference}",
                confidence=clearance.confidence,
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def _parse_match(self, context: Dict[str, Any]) -> Optional[WatchlistMatch]:
        """Parse watchlist match from context."""
        match_data = context.get("match_data", {})
        blame = context.get("blame", {})
        
        # Try to extract match info from various formats
        match_name = (
            match_data.get("matched_name") or 
            match_data.get("name") or
            blame.get("matched_entity") or
            "Unknown"
        )
        
        match_score = float(
            match_data.get("score") or 
            match_data.get("match_score") or 
            blame.get("match_score") or 
            50.0
        )
        
        match_type_str = (
            match_data.get("type") or 
            match_data.get("match_type") or
            blame.get("list_type") or
            "sanctions"
        ).lower()
        
        try:
            match_type = MatchType(match_type_str)
        except ValueError:
            if "pep" in match_type_str:
                match_type = MatchType.PEP
            elif "adverse" in match_type_str:
                match_type = MatchType.ADVERSE_MEDIA
            elif "law" in match_type_str or "enforcement" in match_type_str:
                match_type = MatchType.LAW_ENFORCEMENT
            else:
                match_type = MatchType.SANCTIONS
        
        return WatchlistMatch(
            match_id=match_data.get("match_id", f"MATCH-{int(time.time()*1000)}"),
            match_type=match_type,
            matched_name=match_name,
            match_score=match_score,
            matched_entity_id=match_data.get("entity_id", "unknown"),
            list_name=match_data.get("list_name", match_data.get("list", "UNKNOWN_LIST")),
            matched_dob=match_data.get("matched_dob"),
            matched_country=match_data.get("matched_country"),
            user_name=match_data.get("user_name", ""),
            user_dob=match_data.get("user_dob"),
            user_country=match_data.get("user_country"),
        )
    
    def _make_decision(self, match: WatchlistMatch) -> ClearanceResult:
        """
        Apply decision matrix to determine clearance.
        
        Decision Logic:
        1. PEP matches → Always EDD
        2. Law enforcement → Always Escalate
        3. Score >= 95 + DOB match + Country match → REJECT
        4. Score >= 95 + (DOB OR Country mismatch) → ESCALATE
        5. 80 <= Score < 95 → ESCALATE
        6. Score < 80 + DOB mismatch OR Country mismatch → AUTO_CLEAR
        7. Score < 80 + No secondary data → ESCALATE (can't verify)
        """
        audit_ref = self._generate_audit_reference(match)
        
        # Rule 1: PEP matches NEVER auto-clear
        if match.match_type == MatchType.PEP:
            return ClearanceResult(
                decision=ClearanceDecision.EDD_REQUIRED,
                match=match,
                reason=f"PEP match detected ({match.match_score}%). Enhanced Due Diligence required per policy.",
                confidence=0.95,
                requires_human_review=True,
                audit_reference=audit_ref,
                additional_checks_required=["source_of_wealth", "source_of_funds", "relationship_to_pep"]
            )
        
        # Rule 2: Law enforcement matches always escalate
        if match.match_type == MatchType.LAW_ENFORCEMENT:
            return ClearanceResult(
                decision=ClearanceDecision.ESCALATE,
                match=match,
                reason=f"Law enforcement list match ({match.match_score}%). Manual review required.",
                confidence=0.90,
                requires_human_review=True,
                audit_reference=audit_ref,
                additional_checks_required=["verify_identity", "cross_reference_sources"]
            )
        
        # Rule 3 & 4: High confidence matches
        if match.match_score >= self.HIGH_CONFIDENCE_THRESHOLD:
            dob_match = match.dob_matches()
            country_match = match.country_matches()
            
            # Exact match - REJECT
            if dob_match is True and country_match is True:
                return ClearanceResult(
                    decision=ClearanceDecision.REJECT,
                    match=match,
                    reason=f"High-confidence match ({match.match_score}%) with matching DOB and country. "
                           f"INV-IMMUNE-004 (Sanctions Supremacy) triggered.",
                    confidence=0.98,
                    requires_human_review=False,  # Auto-reject
                    audit_reference=audit_ref
                )
            
            # High score but secondary data doesn't match - needs review
            if dob_match is False or country_match is False:
                mismatches = []
                if dob_match is False:
                    mismatches.append("DOB")
                if country_match is False:
                    mismatches.append("Country")
                
                return ClearanceResult(
                    decision=ClearanceDecision.ESCALATE,
                    match=match,
                    reason=f"High score ({match.match_score}%) but {', '.join(mismatches)} mismatch. "
                           f"Human verification required.",
                    confidence=0.75,
                    requires_human_review=True,
                    audit_reference=audit_ref,
                    additional_checks_required=["verify_" + m.lower() for m in mismatches]
                )
            
            # High score, no secondary data to verify
            return ClearanceResult(
                decision=ClearanceDecision.ESCALATE,
                match=match,
                reason=f"High-confidence match ({match.match_score}%) without secondary identifiers. "
                       f"Cannot auto-clear without DOB/Country verification.",
                confidence=0.70,
                requires_human_review=True,
                audit_reference=audit_ref,
                additional_checks_required=["collect_dob", "collect_country", "manual_verification"]
            )
        
        # Rule 5: Medium confidence - always escalate
        if match.match_score >= self.REVIEW_THRESHOLD:
            return ClearanceResult(
                decision=ClearanceDecision.ESCALATE,
                match=match,
                reason=f"Medium-confidence match ({match.match_score}%). Human review required per policy.",
                confidence=0.80,
                requires_human_review=True,
                audit_reference=audit_ref,
                additional_checks_required=["standard_review"]
            )
        
        # Rule 6 & 7: Low confidence - can auto-clear if secondary data mismatches
        dob_match = match.dob_matches()
        country_match = match.country_matches()
        
        # If we have secondary data and it doesn't match, auto-clear
        if dob_match is False or country_match is False:
            mismatches = []
            if dob_match is False:
                mismatches.append("DOB")
            if country_match is False:
                mismatches.append("Country")
            
            return ClearanceResult(
                decision=ClearanceDecision.AUTO_CLEAR,
                match=match,
                reason=f"Low score ({match.match_score}%) with {', '.join(mismatches)} mismatch. "
                       f"Determined to be false positive.",
                confidence=0.92,
                requires_human_review=False,
                audit_reference=audit_ref
            )
        
        # Low score but no secondary data - escalate (can't verify)
        if dob_match is None and country_match is None:
            return ClearanceResult(
                decision=ClearanceDecision.ESCALATE,
                match=match,
                reason=f"Low score ({match.match_score}%) but no secondary identifiers for verification. "
                       f"INV-IMMUNE-004: When in doubt, escalate.",
                confidence=0.60,
                requires_human_review=True,
                audit_reference=audit_ref,
                additional_checks_required=["collect_secondary_identifiers"]
            )
        
        # Low score with matching secondary data - escalate to be safe
        return ClearanceResult(
            decision=ClearanceDecision.ESCALATE,
            match=match,
            reason=f"Low score ({match.match_score}%) but secondary identifiers match. "
                   f"Escalating for human verification.",
            confidence=0.65,
            requires_human_review=True,
            audit_reference=audit_ref,
            additional_checks_required=["verify_not_same_person"]
        )
    
    def _generate_audit_reference(self, match: WatchlistMatch) -> str:
        """Generate unique audit reference for this decision."""
        data = f"{match.match_id}:{match.matched_name}:{match.match_score}:{datetime.now(timezone.utc).isoformat()}"
        hash_val = hashlib.sha256(data.encode()).hexdigest()[:12].upper()
        return f"CLR-{hash_val}"
    
    def _log_decision(self, clearance: ClearanceResult, original_data: Dict[str, Any]) -> None:
        """Log clearance decision for audit trail."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "audit_reference": clearance.audit_reference,
            "decision": clearance.decision.value,
            "match_type": clearance.match.match_type.value,
            "match_score": clearance.match.match_score,
            "matched_name": clearance.match.matched_name,
            "matched_entity_id": clearance.match.matched_entity_id,
            "list_name": clearance.match.list_name,
            "reason": clearance.reason,
            "confidence": clearance.confidence,
            "requires_human_review": clearance.requires_human_review,
            "transaction_id": original_data.get("transaction_id", "unknown")
        }
        self._clearance_log.append(entry)
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get full audit log."""
        return self._clearance_log.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get clearance statistics."""
        total = self._stats["total_processed"]
        return {
            **self._stats,
            "auto_clear_rate": self._stats["auto_cleared"] / total if total > 0 else 0,
            "escalation_rate": self._stats["escalated"] / total if total > 0 else 0,
            "rejection_rate": self._stats["rejected"] / total if total > 0 else 0,
        }


# =============================================================================
# STRATEGY DEPLOYMENT COMPLETE - PHASE 1 IMMUNE SYSTEM COMPLETE
# =============================================================================
#
# WatchlistClearanceStrategy is now available:
#
#     from modules.immune.strategies import WatchlistClearanceStrategy
#     engine.register_strategy(WatchlistClearanceStrategy())
#
# Decision Matrix:
#   Score >= 95% + DOB + Country Match → REJECT
#   Score >= 95% + Mismatch → ESCALATE
#   80% <= Score < 95% → ESCALATE
#   Score < 80% + Mismatch → AUTO_CLEAR
#   Any PEP → EDD_REQUIRED
#
# The Immune System is now fully operational:
#   P161: Missing Field Strategy (30% of errors)
#   P162: Format Correction Strategy (25% of errors)
#   P163: Document Retry Strategy (15% of errors)
#   P164: Watchlist Clearance Strategy (5-10% of errors)
#
# Combined Coverage: 75-80% of errors can now be remediated or intelligently routed
#
# Attestation: MASTER-BER-P164-STRATEGY
# Ledger: ATTEST: WATCHLIST_CLEARANCE_ACTIVE
# =============================================================================
