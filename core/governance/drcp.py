"""
DRCP — Diggy Rejection & Correction Protocol v1

This module implements the denial routing and correction protocol:
- All DENY decisions route to Diggy (GID-00)
- Agents cannot retry after denial
- Diggy cannot EXECUTE, BLOCK, or APPROVE
- Every correction links to the original denial

DRCP is first-class governance law.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from core.governance.acm_evaluator import EvaluationResult

# Telemetry import (PAC-GOV-OBS-01)
from core.governance.telemetry import emit_drcp_triggered

# Diggy's GID (orchestrator/correction authority)
DIGGY_GID = "GID-00"

# Verbs that Diggy is absolutely forbidden from using
DIGGY_FORBIDDEN_VERBS: Set[str] = {"EXECUTE", "BLOCK", "APPROVE"}

# Verbs that require routing to Diggy on denial
DENIAL_ROUTED_VERBS: Set[str] = {"EXECUTE", "BLOCK", "APPROVE"}


class DRCPOutcome(str, Enum):
    """Outcome of a DRCP correction cycle."""

    PROPOSED = "PROPOSED"  # Diggy proposed a corrected intent
    ESCALATED = "ESCALATED"  # Diggy escalated to human
    PENDING = "PENDING"  # Awaiting Diggy response


@dataclass
class DenialRecord:
    """Record of a denied intent for DRCP tracking.

    This is immutable once created — the denial is final.
    """

    intent_id: str
    agent_gid: str
    verb: str
    target: str
    denial_code: str
    denial_detail: str
    denied_at: str
    next_hop: str = DIGGY_GID

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "intent_id": self.intent_id,
            "agent_gid": self.agent_gid,
            "verb": self.verb,
            "target": self.target,
            "denial_code": self.denial_code,
            "denial_detail": self.denial_detail,
            "denied_at": self.denied_at,
            "next_hop": self.next_hop,
        }


@dataclass
class CorrectionOption:
    """A single correction option proposed by Diggy."""

    option_id: str
    description: str
    new_intent: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "option_id": self.option_id,
            "description": self.description,
            "new_intent": self.new_intent,
        }


@dataclass
class DiggyResponse:
    """Diggy's response to a denial — strict contract.

    Must include either corrective_options OR requires_human=True.
    """

    original_intent_id: str
    denial_code: str
    analysis: str
    corrective_options: List[CorrectionOption] = field(default_factory=list)
    recommendation: Optional[str] = None
    requires_human: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "original_intent_id": self.original_intent_id,
            "denial_code": self.denial_code,
            "analysis": self.analysis,
            "corrective_options": [opt.to_dict() for opt in self.corrective_options],
            "recommendation": self.recommendation,
            "requires_human": self.requires_human,
        }

    def validate(self) -> bool:
        """Validate the response contract.

        Returns:
            True if valid, raises ValueError if not
        """
        if not self.original_intent_id:
            raise ValueError("original_intent_id is required")
        if not self.denial_code:
            raise ValueError("denial_code is required")
        if not self.analysis:
            raise ValueError("analysis is required")

        # Must have either corrections or require human
        if not self.corrective_options and not self.requires_human:
            raise ValueError("Diggy must provide corrective_options OR set requires_human=True")

        return True


@dataclass
class DenialChain:
    """Complete denial chain for audit trail.

    Tracks the full lifecycle: denial → correction → outcome.
    """

    origin_agent: str
    denied_by: str = "ALEX"
    corrected_by: Optional[str] = None
    final_outcome: Optional[DRCPOutcome] = None
    denial_record: Optional[DenialRecord] = None
    diggy_response: Optional[DiggyResponse] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_audit_dict(self) -> Dict[str, Any]:
        """Convert to audit log format."""
        return {
            "denial_chain": {
                "origin_agent": self.origin_agent,
                "denied_by": self.denied_by,
                "corrected_by": self.corrected_by,
                "final_outcome": self.final_outcome.value if self.final_outcome else None,
                "denial_record": self.denial_record.to_dict() if self.denial_record else None,
                "created_at": self.created_at,
            }
        }


class DenialRegistry:
    """Registry tracking denied intents to prevent retries.

    This is an in-memory registry. In production, this would be backed
    by a persistent store.
    """

    def __init__(self) -> None:
        """Initialize the denial registry."""
        self._denials: Dict[str, DenialRecord] = {}  # intent_id -> record
        self._agent_denials: Dict[str, Set[str]] = {}  # agent_gid -> intent_ids

    def register_denial(self, record: DenialRecord) -> None:
        """Register a denied intent.

        Args:
            record: The denial record
        """
        self._denials[record.intent_id] = record

        if record.agent_gid not in self._agent_denials:
            self._agent_denials[record.agent_gid] = set()
        self._agent_denials[record.agent_gid].add(record.intent_id)

        # PAC-GOV-OBS-01: Emit telemetry (fail-open)
        emit_drcp_triggered(
            agent_gid=record.agent_gid,
            verb=record.verb,
            target=record.target,
            denial_code=record.denial_code,
            intent_id=record.intent_id,
        )

    def is_denied(self, intent_id: str) -> bool:
        """Check if an intent was previously denied.

        Args:
            intent_id: The intent ID to check

        Returns:
            True if the intent was denied
        """
        return intent_id in self._denials

    def get_denial(self, intent_id: str) -> Optional[DenialRecord]:
        """Get the denial record for an intent.

        Args:
            intent_id: The intent ID

        Returns:
            The denial record if found
        """
        return self._denials.get(intent_id)

    def has_active_denial(self, agent_gid: str, verb: str, target: str) -> bool:
        """Check if an agent has an active denial for the same action.

        This prevents agents from retrying the same denied action.

        Args:
            agent_gid: The agent GID
            verb: The verb
            target: The target

        Returns:
            True if a matching denial exists
        """
        if agent_gid not in self._agent_denials:
            return False

        for intent_id in self._agent_denials[agent_gid]:
            record = self._denials[intent_id]
            if record.verb == verb and record.target == target:
                return True

        return False

    def clear_denial(self, intent_id: str) -> None:
        """Clear a denial (after successful correction).

        Args:
            intent_id: The intent ID to clear
        """
        if intent_id in self._denials:
            record = self._denials[intent_id]
            if record.agent_gid in self._agent_denials:
                self._agent_denials[record.agent_gid].discard(intent_id)
            del self._denials[intent_id]


def is_diggy(agent_gid: str) -> bool:
    """Check if the agent is Diggy.

    Args:
        agent_gid: The agent GID

    Returns:
        True if this is Diggy
    """
    return agent_gid == DIGGY_GID


def is_diggy_forbidden_verb(verb: str) -> bool:
    """Check if a verb is forbidden for Diggy.

    Args:
        verb: The verb to check

    Returns:
        True if Diggy cannot use this verb
    """
    verb_upper = verb.upper() if isinstance(verb, str) else verb.value.upper()
    return verb_upper in DIGGY_FORBIDDEN_VERBS


def requires_diggy_routing(verb: str) -> bool:
    """Check if a denial of this verb requires routing to Diggy.

    Args:
        verb: The verb that was denied

    Returns:
        True if denial should route to Diggy
    """
    verb_upper = verb.upper() if isinstance(verb, str) else verb.value.upper()
    return verb_upper in DENIAL_ROUTED_VERBS


def create_denial_record(
    result: EvaluationResult,
    intent_id: Optional[str] = None,
) -> DenialRecord:
    """Create a denial record from an evaluation result.

    Args:
        result: The evaluation result
        intent_id: Optional intent ID (generated if not provided)

    Returns:
        A DenialRecord for DRCP tracking
    """
    from uuid import uuid4

    return DenialRecord(
        intent_id=intent_id or result.correlation_id or str(uuid4()),
        agent_gid=result.agent_gid,
        verb=result.intent_verb,
        target=result.intent_target,
        denial_code=result.reason.value if result.reason else "UNKNOWN",
        denial_detail=result.reason_detail or "",
        denied_at=result.timestamp,
        next_hop=DIGGY_GID,
    )


# Module-level singleton
_denial_registry: Optional[DenialRegistry] = None


def get_denial_registry() -> DenialRegistry:
    """Get or create the denial registry singleton.

    Returns:
        The denial registry instance
    """
    global _denial_registry
    if _denial_registry is None:
        _denial_registry = DenialRegistry()
    return _denial_registry


def reset_denial_registry() -> None:
    """Reset the denial registry (for testing)."""
    global _denial_registry
    _denial_registry = None
