"""
Diggi Envelope Handler — PAC-DIGGI-05

This module implements envelope-driven corrections for Diggi (GID-00).
Diggi MUST consume only the Canonical Decision Envelope (CDE) — never internal structures.

Design Principles:
- Diggi sees ONLY the CDE — no EvaluationResult, no internal fields
- Corrections are derived from CDE.reason_code, not internal DenialReason
- All correction logic is deterministic and bounded
- Diggi cannot infer, reason, or generate — only translate

Contract:
- Input: GatewayDecisionEnvelope (CDE v1)
- Output: DiggiCorrectionResponse (bounded, deterministic)

Author: ATLAS (GID-11)
Authority: Governance Artifacts, Envelope-Driven Corrections
PAC: PAC-DIGGI-05
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

# Telemetry import (PAC-GOV-OBS-01)
from core.governance.telemetry import emit_diggi_correction
from gateway.decision_envelope import CDE_VERSION, GatewayDecision, GatewayDecisionEnvelope, ReasonCode

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Diggi's GID
DIGGI_GID = "GID-00"

# Verbs Diggi is FORBIDDEN from using (ever)
DIGGI_FORBIDDEN_VERBS: Set[str] = frozenset({"EXECUTE", "BLOCK", "APPROVE"})

# Verbs Diggi CAN suggest in corrections
DIGGI_ALLOWED_VERBS: Set[str] = frozenset({"PROPOSE", "ESCALATE", "READ"})


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class DiggiEnvelopeError(Exception):
    """Base exception for Diggi envelope processing errors."""

    pass


class EnvelopeNotDenyError(DiggiEnvelopeError):
    """Raised when envelope is ALLOW (Diggi only handles DENY)."""

    pass


class NoCorrectionAvailableError(DiggiEnvelopeError):
    """Raised when no correction mapping exists for reason_code."""

    pass


class ForbiddenVerbError(DiggiEnvelopeError):
    """Raised when a forbidden verb appears in correction."""

    pass


# ═══════════════════════════════════════════════════════════════════════════════
# CORRECTION OPTION
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class CorrectionOption:
    """A single correction option Diggi can suggest.

    Immutable. Bounded. No forbidden verbs.
    """

    verb: str
    target: Optional[str]
    description: str

    def __post_init__(self) -> None:
        """Validate verb is allowed."""
        if self.verb.upper() in DIGGI_FORBIDDEN_VERBS:
            raise ForbiddenVerbError(f"Diggi cannot suggest forbidden verb: {self.verb}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result: Dict[str, Any] = {
            "verb": self.verb,
            "description": self.description,
        }
        if self.target:
            result["target"] = self.target
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# DIGGI CORRECTION RESPONSE
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class DiggiCorrectionResponse:
    """Diggi's response to a DENY envelope.

    This is the ONLY output Diggi produces. It is:
    - Bounded (finite options)
    - Deterministic (same input → same output)
    - Immutable (cannot be modified after creation)
    - Auditable (links back to original envelope)

    Contract:
    - Must have either options OR requires_human=True
    - Cannot contain forbidden verbs
    - Must reference original audit_ref
    """

    original_audit_ref: str
    reason_code: ReasonCode
    analysis: str
    options: tuple[CorrectionOption, ...]
    requires_human: bool
    recommendation: Optional[str]
    timestamp: str

    def __post_init__(self) -> None:
        """Validate response contract."""
        if not self.original_audit_ref:
            raise DiggiEnvelopeError("original_audit_ref is required")
        if not self.options and not self.requires_human:
            raise DiggiEnvelopeError("Diggi must provide options OR set requires_human=True")
        # Validate no forbidden verbs
        for opt in self.options:
            if opt.verb.upper() in DIGGI_FORBIDDEN_VERBS:
                raise ForbiddenVerbError(f"Response contains forbidden verb: {opt.verb}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "diggi_response": {
                "original_audit_ref": self.original_audit_ref,
                "reason_code": self.reason_code.value,
                "analysis": self.analysis,
                "options": [opt.to_dict() for opt in self.options],
                "requires_human": self.requires_human,
                "recommendation": self.recommendation,
                "timestamp": self.timestamp,
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CORRECTION MAPPINGS (DETERMINISTIC)
# ═══════════════════════════════════════════════════════════════════════════════

# Static mapping: ReasonCode → CorrectionOption(s)
# This is the ONLY source of correction logic.
# No heuristics. No LLM. No inference.

_CORRECTION_MAP: Dict[ReasonCode, Dict[str, Any]] = {
    ReasonCode.VERB_NOT_PERMITTED: {
        "analysis": "The requested verb is not permitted for this agent.",
        "options": [
            CorrectionOption(
                verb="PROPOSE",
                target=None,
                description="Propose the action through proper channels",
            ),
            CorrectionOption(
                verb="ESCALATE",
                target="human",
                description="Escalate to human operator for authorization",
            ),
        ],
        "recommendation": "Consider using PROPOSE to submit for review",
    },
    ReasonCode.TARGET_NOT_IN_SCOPE: {
        "analysis": "The target resource is outside the agent's authorized scope.",
        "options": [
            CorrectionOption(
                verb="READ",
                target=None,
                description="Request read access to understand scope boundaries",
            ),
            CorrectionOption(
                verb="ESCALATE",
                target="human",
                description="Escalate to human operator for scope expansion",
            ),
        ],
        "recommendation": "Verify target is within authorized boundaries",
    },
    ReasonCode.EXECUTE_NOT_PERMITTED: {
        "analysis": "Agent does not have EXECUTE permission on this target.",
        "options": [
            CorrectionOption(
                verb="PROPOSE",
                target=None,
                description="Propose the execution for human approval",
            ),
            CorrectionOption(
                verb="ESCALATE",
                target="human",
                description="Escalate to authorized agent or human",
            ),
        ],
        "recommendation": "PROPOSE instead of EXECUTE, then await approval",
    },
    ReasonCode.BLOCK_NOT_PERMITTED: {
        "analysis": "Agent does not have BLOCK authority.",
        "options": [
            CorrectionOption(
                verb="ESCALATE",
                target="GID-06",  # Sam
                description="Escalate to Sam (GID-06) for security block",
            ),
            CorrectionOption(
                verb="ESCALATE",
                target="human",
                description="Escalate to human security operator",
            ),
        ],
        "recommendation": "Only GID-06 (Sam) and GID-08 (ALEX) can BLOCK",
    },
    ReasonCode.CHAIN_OF_COMMAND_VIOLATION: {
        "analysis": "Action requires routing through the chain of command.",
        "options": [
            CorrectionOption(
                verb="PROPOSE",
                target="GID-00",
                description="Route proposal through Diggi for orchestration",
            ),
        ],
        "recommendation": "Submit through proper chain of command",
    },
    ReasonCode.APPROVE_NOT_PERMITTED: {
        "analysis": "APPROVE is a human-only capability.",
        "options": [
            CorrectionOption(
                verb="ESCALATE",
                target="human",
                description="Escalate to human for approval decision",
            ),
        ],
        "recommendation": "Only humans can APPROVE",
        "requires_human": True,
    },
    ReasonCode.RETRY_AFTER_DENY_FORBIDDEN: {
        "analysis": "Cannot retry after denial. Must await correction.",
        "options": [
            CorrectionOption(
                verb="ESCALATE",
                target="human",
                description="Request human review of denial",
            ),
        ],
        "recommendation": "Wait for correction cycle to complete",
    },
    ReasonCode.ATLAS_DOMAIN_VIOLATION: {
        "analysis": "Atlas (GID-11) cannot modify domain-owned code paths.",
        "options": [
            CorrectionOption(
                verb="ESCALATE",
                target="human",
                description="Request human to assign to domain owner",
            ),
        ],
        "recommendation": "This path is owned by another agent's domain",
    },
    ReasonCode.UNKNOWN_AGENT: {
        "analysis": "Agent identity not recognized in ACM.",
        "options": [
            CorrectionOption(
                verb="ESCALATE",
                target="human",
                description="Escalate to admin for agent registration",
            ),
        ],
        "recommendation": "Agent must be registered in ACM before acting",
        "requires_human": True,
    },
    ReasonCode.DIGGY_EXECUTE_FORBIDDEN: {
        "analysis": "Diggi (GID-00) cannot EXECUTE. This is a governance law.",
        "options": [
            CorrectionOption(
                verb="PROPOSE",
                target=None,
                description="Diggi can only PROPOSE, not EXECUTE",
            ),
        ],
        "recommendation": "Diggi must delegate execution to authorized agents",
    },
    ReasonCode.DIGGY_BLOCK_FORBIDDEN: {
        "analysis": "Diggi (GID-00) cannot BLOCK. This is a governance law.",
        "options": [
            CorrectionOption(
                verb="ESCALATE",
                target="GID-06",
                description="Escalate to Sam (GID-06) for BLOCK authority",
            ),
        ],
        "recommendation": "Only GID-06 (Sam) and GID-08 (ALEX) can BLOCK",
    },
    ReasonCode.DIGGY_APPROVE_FORBIDDEN: {
        "analysis": "Diggi (GID-00) cannot APPROVE. This is a governance law.",
        "options": [
            CorrectionOption(
                verb="ESCALATE",
                target="human",
                description="Escalate to human for APPROVE authority",
            ),
        ],
        "recommendation": "Only humans can APPROVE",
        "requires_human": True,
    },
    ReasonCode.DIGGI_NO_VALID_CORRECTION: {
        "analysis": "No correction mapping exists for the original denial.",
        "options": [],
        "recommendation": "Manual review required",
        "requires_human": True,
    },
}

# Default correction for unmapped reason codes
_DEFAULT_CORRECTION: Dict[str, Any] = {
    "analysis": "Denial occurred but no specific correction mapping exists.",
    "options": [
        CorrectionOption(
            verb="ESCALATE",
            target="human",
            description="Escalate to human for manual resolution",
        ),
    ],
    "recommendation": "Manual review required",
    "requires_human": True,
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENVELOPE HANDLER
# ═══════════════════════════════════════════════════════════════════════════════


def process_denial_envelope(
    envelope: GatewayDecisionEnvelope,
) -> DiggiCorrectionResponse:
    """
    Process a DENY envelope and produce a correction response.

    This is Diggi's ONLY entry point for handling denials.
    Diggi sees ONLY the CDE — no internal structures.

    Args:
        envelope: GatewayDecisionEnvelope (must be DENY)

    Returns:
        DiggiCorrectionResponse with bounded correction options

    Raises:
        EnvelopeNotDenyError: If envelope is ALLOW
        DiggiEnvelopeError: If envelope is malformed
    """
    # Gate: Only process DENY envelopes
    if envelope.decision != GatewayDecision.DENY:
        raise EnvelopeNotDenyError(f"Diggi only processes DENY envelopes, got {envelope.decision.value}")

    # Validate version
    if envelope.version != CDE_VERSION:
        raise DiggiEnvelopeError(f"Unsupported CDE version: {envelope.version}")

    # Look up correction mapping
    reason_code = envelope.reason_code
    mapping = _CORRECTION_MAP.get(reason_code, _DEFAULT_CORRECTION)

    # Build response
    options = tuple(mapping.get("options", []))
    requires_human = mapping.get("requires_human", False)

    # If envelope already has correction_plan from DCC, use it
    if envelope.correction_plan and "allowed_next_steps" in envelope.correction_plan:
        # Convert DCC steps to CorrectionOptions
        dcc_steps = envelope.correction_plan["allowed_next_steps"]
        if isinstance(dcc_steps, list) and dcc_steps:
            options = tuple(
                CorrectionOption(
                    verb=step.get("verb", "ESCALATE"),
                    target=step.get("target") or step.get("target_scope"),
                    description=step.get("description", ""),
                )
                for step in dcc_steps
                if step.get("verb", "").upper() not in DIGGI_FORBIDDEN_VERBS
            )

    response = DiggiCorrectionResponse(
        original_audit_ref=envelope.audit_ref,
        reason_code=reason_code,
        analysis=mapping.get("analysis", "Denial requires correction"),
        options=options,
        requires_human=requires_human or envelope.human_required,
        recommendation=mapping.get("recommendation"),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # PAC-GOV-OBS-01: Emit telemetry (fail-open)
    emit_diggi_correction(
        agent_gid=envelope.agent_gid,
        target=envelope.intent_target,
        correction_type=reason_code.value if hasattr(reason_code, "value") else str(reason_code),
        envelope_id=envelope.audit_ref,
        num_options=len(options),
    )

    return response


def can_diggi_handle(envelope: GatewayDecisionEnvelope) -> bool:
    """
    Check if Diggi can handle this envelope.

    Returns True if:
    - Envelope is DENY
    - next_hop is GID-00 (Diggi) or None
    """
    if envelope.decision != GatewayDecision.DENY:
        return False

    if envelope.next_hop is not None and envelope.next_hop != DIGGI_GID:
        return False

    return True


def get_correction_for_reason(reason_code: ReasonCode) -> Dict[str, Any]:
    """
    Get the correction mapping for a reason code.

    This is for inspection/debugging only.
    Use process_denial_envelope() for actual processing.
    """
    return _CORRECTION_MAP.get(reason_code, _DEFAULT_CORRECTION).copy()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Constants
    "DIGGI_GID",
    "DIGGI_FORBIDDEN_VERBS",
    "DIGGI_ALLOWED_VERBS",
    # Exceptions
    "DiggiEnvelopeError",
    "EnvelopeNotDenyError",
    "NoCorrectionAvailableError",
    "ForbiddenVerbError",
    # Data classes
    "CorrectionOption",
    "DiggiCorrectionResponse",
    # Functions
    "process_denial_envelope",
    "can_diggi_handle",
    "get_correction_for_reason",
]
