"""
ACM Evaluator — Pure function evaluation of agent intents against ACM.

This module implements the core ALEX enforcement logic:
- Deterministic evaluation (no heuristics, no LLM)
- Fail-closed behavior (absence = denial)
- Structured denial reasons
- No capability inference

ALEX (GID-08) is the sole authority for intent evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

from core.governance.acm_loader import ACM, ACMLoader, get_acm_loader
from core.governance.intent_schema import AgentIntent, IntentVerb


class ACMDecision(str, Enum):
    """Evaluation decision outcomes."""

    ALLOW = "ALLOW"
    DENY = "DENY"


class DenialReason(str, Enum):
    """Structured denial reason codes."""

    # Intent validation failures
    INVALID_INTENT = "INVALID_INTENT"
    MALFORMED_GID = "MALFORMED_GID"

    # ACM lookup failures
    UNKNOWN_AGENT = "UNKNOWN_AGENT"
    ACM_NOT_LOADED = "ACM_NOT_LOADED"

    # Capability denials
    VERB_NOT_PERMITTED = "VERB_NOT_PERMITTED"
    TARGET_NOT_IN_SCOPE = "TARGET_NOT_IN_SCOPE"
    EXECUTE_NOT_PERMITTED = "EXECUTE_NOT_PERMITTED"
    BLOCK_NOT_PERMITTED = "BLOCK_NOT_PERMITTED"

    # Mutation guard
    MUTATION_WITHOUT_EXECUTE = "MUTATION_WITHOUT_EXECUTE"

    # Chain-of-command enforcement
    CHAIN_OF_COMMAND_VIOLATION = "CHAIN_OF_COMMAND_VIOLATION"

    # Checklist enforcement
    CHECKLIST_NOT_LOADED = "CHECKLIST_NOT_LOADED"
    CHECKLIST_VERSION_MISMATCH = "CHECKLIST_VERSION_MISMATCH"

    # Forbidden operations
    DELETE_FORBIDDEN = "DELETE_FORBIDDEN"
    APPROVE_NOT_PERMITTED = "APPROVE_NOT_PERMITTED"

    # DRCP v1 — Diggy Rejection & Correction Protocol
    RETRY_AFTER_DENY_FORBIDDEN = "RETRY_AFTER_DENY_FORBIDDEN"
    DIGGY_EXECUTE_FORBIDDEN = "DIGGY_EXECUTE_FORBIDDEN"
    DIGGY_BLOCK_FORBIDDEN = "DIGGY_BLOCK_FORBIDDEN"
    DIGGY_APPROVE_FORBIDDEN = "DIGGY_APPROVE_FORBIDDEN"

    # DCC v1 — Deterministic Correction Contract
    DIGGI_NO_VALID_CORRECTION = "DIGGI_NO_VALID_CORRECTION"

    # PAC-GOV-ATLAS-01 — Atlas Domain Boundary Enforcement
    ATLAS_DOMAIN_VIOLATION = "ATLAS_DOMAIN_VIOLATION"


@dataclass(frozen=True)
class EvaluationResult:
    """Immutable result of ACM evaluation.

    This record is emitted for every evaluation (allow or deny)
    to ensure complete audit trail.
    """

    decision: ACMDecision
    agent_gid: str
    intent_verb: str
    intent_target: str
    reason: Optional[DenialReason]
    reason_detail: Optional[str]
    acm_version: Optional[str]
    timestamp: str
    correlation_id: Optional[str]
    next_hop: Optional[str] = None  # DRCP: Where denied intents should route
    correction_plan: Optional[Dict[str, object]] = None  # DCC: Bounded correction plan

    def to_audit_dict(self) -> Dict[str, object]:
        """Convert to audit log format."""
        result: Dict[str, object] = {
            "agent_gid": self.agent_gid,
            "intent": {
                "verb": self.intent_verb,
                "target": self.intent_target,
            },
            "decision": self.decision.value,
            "reason": self.reason.value if self.reason else None,
            "reason_detail": self.reason_detail,
            "acm_version": self.acm_version,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
        }
        # Add next_hop for DENY decisions (DRCP routing)
        if self.decision == ACMDecision.DENY and self.next_hop:
            result["next_hop"] = self.next_hop
        # Add correction_plan for DENY decisions (DCC)
        if self.decision == ACMDecision.DENY and self.correction_plan:
            result["correction_plan"] = self.correction_plan
        return result


class ACMEvaluator:
    """Pure function evaluator for ACM enforcement.

    Implements the core ALEX logic:
    - ESCALATE is always allowed (universal)
    - BLOCK requires explicit BLOCK capability (Sam/ALEX only)
    - EXECUTE requires explicit EXECUTE entry
    - READ/PROPOSE require matching scope
    - Default deny for everything else

    No heuristics. No LLM calls. No capability inference.
    """

    # Agents with BLOCK authority (must match ACM)
    _BLOCK_AUTHORIZED_GIDS = frozenset({"GID-06", "GID-08"})  # Sam, ALEX

    def __init__(self, loader: ACMLoader | None = None) -> None:
        """Initialize the evaluator.

        Args:
            loader: ACM loader instance. Uses default singleton if not provided.
        """
        self._loader = loader or get_acm_loader()

    def evaluate(self, intent: AgentIntent) -> EvaluationResult:
        """Evaluate an intent against the agent's ACM.

        This is the core enforcement function. It is:
        - Deterministic (same input = same output)
        - Fail-closed (any doubt = DENY)
        - Non-interactive (no retries or clarification)

        Args:
            intent: The agent intent to evaluate

        Returns:
            EvaluationResult with ALLOW or DENY decision
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Get the agent's ACM
        acm = self._loader.get(intent.agent_gid)

        if acm is None:
            return self._deny(
                intent=intent,
                reason=DenialReason.UNKNOWN_AGENT,
                detail=f"No ACM found for {intent.agent_gid}",
                acm_version=None,
                timestamp=timestamp,
            )

        # Rule 1: ESCALATE is always allowed (universal capability)
        if intent.verb == IntentVerb.ESCALATE:
            return self._allow(intent=intent, acm=acm, timestamp=timestamp)

        # Rule 2: BLOCK requires explicit BLOCK authority
        if intent.verb == IntentVerb.BLOCK:
            if not acm.can_block():
                return self._deny(
                    intent=intent,
                    reason=DenialReason.BLOCK_NOT_PERMITTED,
                    detail=f"{acm.agent_id} ({acm.gid}) does not have BLOCK authority",
                    acm_version=acm.version,
                    timestamp=timestamp,
                )
            # Check if target is in BLOCK scope
            if not acm.has_capability("BLOCK", intent.full_target):
                return self._deny(
                    intent=intent,
                    reason=DenialReason.TARGET_NOT_IN_SCOPE,
                    detail=f"Target '{intent.full_target}' not in BLOCK scope",
                    acm_version=acm.version,
                    timestamp=timestamp,
                )
            return self._allow(intent=intent, acm=acm, timestamp=timestamp)

        # Rule 3: EXECUTE requires explicit EXECUTE entry
        if intent.verb == IntentVerb.EXECUTE:
            if not acm.has_capability("EXECUTE", intent.full_target):
                return self._deny(
                    intent=intent,
                    reason=DenialReason.EXECUTE_NOT_PERMITTED,
                    detail=f"EXECUTE not permitted for '{intent.full_target}'",
                    acm_version=acm.version,
                    timestamp=timestamp,
                )
            return self._allow(intent=intent, acm=acm, timestamp=timestamp)

        # Rule 4: READ/PROPOSE require matching scope
        if intent.verb in (IntentVerb.READ, IntentVerb.PROPOSE):
            verb_name = intent.verb.value
            if not acm.has_capability(verb_name, intent.full_target):
                return self._deny(
                    intent=intent,
                    reason=DenialReason.TARGET_NOT_IN_SCOPE,
                    detail=f"Target '{intent.full_target}' not in {verb_name} scope",
                    acm_version=acm.version,
                    timestamp=timestamp,
                )
            return self._allow(intent=intent, acm=acm, timestamp=timestamp)

        # Default deny: Unknown verb or unhandled case
        return self._deny(
            intent=intent,
            reason=DenialReason.VERB_NOT_PERMITTED,
            detail=f"Verb '{intent.verb.value}' not recognized or permitted",
            acm_version=acm.version,
            timestamp=timestamp,
        )

    def evaluate_dict(self, intent_data: Dict[str, object]) -> EvaluationResult:
        """Evaluate an intent from raw dictionary data.

        Convenience method that parses and validates the intent first.

        Args:
            intent_data: Raw intent dictionary

        Returns:
            EvaluationResult with ALLOW or DENY decision
        """
        from core.governance.intent_schema import parse_intent

        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            intent = parse_intent(intent_data)  # type: ignore[arg-type]
        except ValueError as e:
            # Malformed intent -> immediate denial
            return EvaluationResult(
                decision=ACMDecision.DENY,
                agent_gid=str(intent_data.get("agent_gid", "UNKNOWN")),
                intent_verb=str(intent_data.get("verb", "UNKNOWN")),
                intent_target=str(intent_data.get("target", "UNKNOWN")),
                reason=DenialReason.INVALID_INTENT,
                reason_detail=str(e),
                acm_version=None,
                timestamp=timestamp,
                correlation_id=str(intent_data.get("correlation_id")) if "correlation_id" in intent_data else None,
            )

        return self.evaluate(intent)

    def _allow(
        self,
        intent: AgentIntent,
        acm: ACM,
        timestamp: str,
    ) -> EvaluationResult:
        """Create an ALLOW result."""
        return EvaluationResult(
            decision=ACMDecision.ALLOW,
            agent_gid=intent.agent_gid,
            intent_verb=intent.verb.value,
            intent_target=intent.full_target,
            reason=None,
            reason_detail=None,
            acm_version=acm.version,
            timestamp=timestamp,
            correlation_id=intent.correlation_id,
        )

    def _deny(
        self,
        intent: AgentIntent,
        reason: DenialReason,
        detail: str,
        acm_version: Optional[str],
        timestamp: str,
    ) -> EvaluationResult:
        """Create a DENY result."""
        return EvaluationResult(
            decision=ACMDecision.DENY,
            agent_gid=intent.agent_gid,
            intent_verb=intent.verb.value,
            intent_target=intent.full_target,
            reason=reason,
            reason_detail=detail,
            acm_version=acm_version,
            timestamp=timestamp,
            correlation_id=intent.correlation_id,
        )


# Convenience function for direct evaluation
def evaluate_intent(intent: AgentIntent, loader: ACMLoader | None = None) -> EvaluationResult:
    """Evaluate an intent against ACM (pure function interface).

    Args:
        intent: The agent intent to evaluate
        loader: Optional ACM loader (uses default if not provided)

    Returns:
        EvaluationResult with ALLOW or DENY decision
    """
    evaluator = ACMEvaluator(loader)
    return evaluator.evaluate(intent)
