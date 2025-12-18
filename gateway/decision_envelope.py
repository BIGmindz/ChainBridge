"""
Canonical Decision Envelope (CDE) v1 — PAC-GATEWAY-01

This module defines the single, stable, versioned response contract
for all gateway intent evaluations.

Design Principles:
- Versioned: version field is mandatory and locked
- Deterministic: Same input → same envelope
- Exhaustive: All fields populated in all paths
- Backward-safe: Future versions are additive only

Downstream consumers (Diggi, UI, external LLMs) MUST depend only on the envelope.
No consumer should depend on internal gateway logic.

Author: ATLAS (GID-11)
Authority: Gateway / Governance Interface
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from core.governance.acm_evaluator import ACMDecision, DenialReason, EvaluationResult

# ═══════════════════════════════════════════════════════════════════════════════
# VERSION LOCK
# ═══════════════════════════════════════════════════════════════════════════════

CDE_VERSION: str = "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION ENUM
# ═══════════════════════════════════════════════════════════════════════════════


class GatewayDecision(str, Enum):
    """Gateway decision outcomes — ALLOW or DENY only."""

    ALLOW = "ALLOW"
    DENY = "DENY"


# ═══════════════════════════════════════════════════════════════════════════════
# REASON CODE ENUM (Complete mapping of all denial reasons)
# ═══════════════════════════════════════════════════════════════════════════════


class ReasonCode(str, Enum):
    """
    Exhaustive reason codes for CDE.

    Maps 1:1 from DenialReason plus NONE for ALLOW decisions.
    Consumers should switch on these codes, not internal strings.
    """

    # Success (ALLOW)
    NONE = "NONE"

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

    # Atlas Domain Boundary
    ATLAS_DOMAIN_VIOLATION = "ATLAS_DOMAIN_VIOLATION"

    # Unknown / fallback
    UNKNOWN = "UNKNOWN"


def map_denial_reason(reason: Optional[DenialReason]) -> ReasonCode:
    """
    Map internal DenialReason to CDE ReasonCode.

    This is the ONLY place where internal reasons are translated.
    """
    if reason is None:
        return ReasonCode.NONE

    # Direct mapping — all DenialReason values have a matching ReasonCode
    try:
        return ReasonCode(reason.value)
    except ValueError:
        return ReasonCode.UNKNOWN


# ═══════════════════════════════════════════════════════════════════════════════
# CANONICAL DECISION ENVELOPE
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class GatewayDecisionEnvelope:
    """
    Canonical Decision Envelope (CDE) v1.

    This is the ONLY response contract for gateway intent evaluation.
    All consumers must depend on this envelope, not internal structures.

    Contract:
    - version: Always "1.0.0" (locked)
    - decision: ALLOW or DENY
    - reason_code: NONE for ALLOW, specific code for DENY
    - human_required: True only when human approval needed
    - next_hop: Agent GID for routing (e.g., "GID-00" for Diggi)
    - allowed_tools: Empty list if DENY
    - audit_ref: Immutable reference ID for tracing

    All fields are populated in ALL paths. No optional ambiguity
    except next_hop (which is None when not routing).
    """

    version: str
    decision: GatewayDecision
    reason_code: ReasonCode
    reason_detail: str
    human_required: bool
    next_hop: Optional[str]
    allowed_tools: List[str]
    audit_ref: str
    timestamp: str
    agent_gid: str
    intent_verb: str
    intent_target: str
    correction_plan: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate envelope integrity."""
        if self.version != CDE_VERSION:
            raise EnvelopeVersionError(f"CDE version must be {CDE_VERSION}, got {self.version}")
        if not self.audit_ref:
            raise EnvelopeMalformedError("audit_ref cannot be empty")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result["decision"] = self.decision.value
        result["reason_code"] = self.reason_code.value
        return result

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GatewayDecisionEnvelope":
        """Deserialize from dictionary."""
        return cls(
            version=data["version"],
            decision=GatewayDecision(data["decision"]),
            reason_code=ReasonCode(data["reason_code"]),
            reason_detail=data["reason_detail"],
            human_required=data["human_required"],
            next_hop=data.get("next_hop"),
            allowed_tools=data.get("allowed_tools", []),
            audit_ref=data["audit_ref"],
            timestamp=data["timestamp"],
            agent_gid=data["agent_gid"],
            intent_verb=data["intent_verb"],
            intent_target=data["intent_target"],
            correction_plan=data.get("correction_plan"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "GatewayDecisionEnvelope":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class EnvelopeError(RuntimeError):
    """Base exception for envelope errors."""

    pass


class EnvelopeVersionError(EnvelopeError):
    """Raised when envelope version is invalid."""

    pass


class EnvelopeMalformedError(EnvelopeError):
    """Raised when envelope is malformed."""

    pass


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════


def _generate_audit_ref() -> str:
    """Generate a unique audit reference ID."""
    return f"cde-{uuid.uuid4().hex[:12]}"


def _requires_human(reason: Optional[DenialReason]) -> bool:
    """
    Determine if a denial requires human intervention.

    Human required for:
    - APPROVE_NOT_PERMITTED (humans only can approve)
    - Specific escalation scenarios
    """
    if reason is None:
        return False

    human_required_reasons = {
        DenialReason.APPROVE_NOT_PERMITTED,
    }
    return reason in human_required_reasons


def _get_allowed_tools_for_result(result: EvaluationResult) -> List[str]:
    """
    Determine allowed tools based on evaluation result.

    For ALLOW: Extract from correction_plan or return empty
    For DENY: Always empty (no tools allowed on denial)
    """
    if result.decision == ACMDecision.DENY:
        return []

    # For ALLOW, tools could be specified in metadata
    # Currently returns empty list — tool binding is Phase 2
    return []


def create_envelope_from_result(
    result: EvaluationResult,
    allowed_tools: Optional[List[str]] = None,
) -> GatewayDecisionEnvelope:
    """
    Create a CDE from an internal EvaluationResult.

    This is the ONLY translation point from internal structures to CDE.
    All consumers receive the CDE, never the raw EvaluationResult.

    Args:
        result: Internal evaluation result
        allowed_tools: Optional list of allowed tools (for ALLOW decisions)

    Returns:
        GatewayDecisionEnvelope with all fields populated
    """
    decision = GatewayDecision.ALLOW if result.decision == ACMDecision.ALLOW else GatewayDecision.DENY

    reason_code = map_denial_reason(result.reason)

    # Determine allowed tools
    if allowed_tools is not None:
        tools = allowed_tools if decision == GatewayDecision.ALLOW else []
    else:
        tools = _get_allowed_tools_for_result(result)

    return GatewayDecisionEnvelope(
        version=CDE_VERSION,
        decision=decision,
        reason_code=reason_code,
        reason_detail=result.reason_detail or "",
        human_required=_requires_human(result.reason),
        next_hop=result.next_hop,
        allowed_tools=tools,
        audit_ref=_generate_audit_ref(),
        timestamp=result.timestamp,
        agent_gid=result.agent_gid,
        intent_verb=result.intent_verb,
        intent_target=result.intent_target,
        correction_plan=result.correction_plan,
    )


def create_allow_envelope(
    agent_gid: str,
    intent_verb: str,
    intent_target: str,
    allowed_tools: Optional[List[str]] = None,
    timestamp: Optional[str] = None,
) -> GatewayDecisionEnvelope:
    """
    Create an ALLOW envelope directly (convenience function).

    Args:
        agent_gid: Agent GID
        intent_verb: The verb being allowed
        intent_target: The target resource
        allowed_tools: List of tools the agent can use
        timestamp: Optional timestamp (generated if not provided)

    Returns:
        GatewayDecisionEnvelope with ALLOW decision
    """
    return GatewayDecisionEnvelope(
        version=CDE_VERSION,
        decision=GatewayDecision.ALLOW,
        reason_code=ReasonCode.NONE,
        reason_detail="",
        human_required=False,
        next_hop=None,
        allowed_tools=allowed_tools or [],
        audit_ref=_generate_audit_ref(),
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        agent_gid=agent_gid,
        intent_verb=intent_verb,
        intent_target=intent_target,
        correction_plan=None,
    )


def create_deny_envelope(
    agent_gid: str,
    intent_verb: str,
    intent_target: str,
    reason_code: ReasonCode,
    reason_detail: str,
    next_hop: Optional[str] = None,
    human_required: bool = False,
    correction_plan: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
) -> GatewayDecisionEnvelope:
    """
    Create a DENY envelope directly (convenience function).

    Args:
        agent_gid: Agent GID
        intent_verb: The verb being denied
        intent_target: The target resource
        reason_code: The denial reason code
        reason_detail: Human-readable denial detail
        next_hop: Where to route the denial (e.g., "GID-00" for Diggi)
        human_required: True if human intervention needed
        correction_plan: Optional correction plan from DCC
        timestamp: Optional timestamp (generated if not provided)

    Returns:
        GatewayDecisionEnvelope with DENY decision
    """
    return GatewayDecisionEnvelope(
        version=CDE_VERSION,
        decision=GatewayDecision.DENY,
        reason_code=reason_code,
        reason_detail=reason_detail,
        human_required=human_required,
        next_hop=next_hop,
        allowed_tools=[],  # Always empty for DENY
        audit_ref=_generate_audit_ref(),
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        agent_gid=agent_gid,
        intent_verb=intent_verb,
        intent_target=intent_target,
        correction_plan=correction_plan,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


def validate_envelope(envelope: GatewayDecisionEnvelope) -> bool:
    """
    Validate that an envelope is well-formed.

    Checks:
    - Version is CDE_VERSION
    - audit_ref is non-empty
    - DENY decisions have non-NONE reason_code
    - ALLOW decisions have NONE reason_code
    - allowed_tools is empty for DENY

    Returns:
        True if valid

    Raises:
        EnvelopeMalformedError: If envelope is invalid
    """
    if envelope.version != CDE_VERSION:
        raise EnvelopeMalformedError(f"Invalid version: expected {CDE_VERSION}, got {envelope.version}")

    if not envelope.audit_ref:
        raise EnvelopeMalformedError("audit_ref cannot be empty")

    if envelope.decision == GatewayDecision.DENY:
        if envelope.reason_code == ReasonCode.NONE:
            raise EnvelopeMalformedError("DENY decision must have a reason_code other than NONE")
        if envelope.allowed_tools:
            raise EnvelopeMalformedError("DENY decision must have empty allowed_tools")

    if envelope.decision == GatewayDecision.ALLOW:
        if envelope.reason_code != ReasonCode.NONE:
            raise EnvelopeMalformedError(f"ALLOW decision must have reason_code NONE, got {envelope.reason_code}")

    return True


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Version
    "CDE_VERSION",
    # Enums
    "GatewayDecision",
    "ReasonCode",
    # Main class
    "GatewayDecisionEnvelope",
    # Exceptions
    "EnvelopeError",
    "EnvelopeVersionError",
    "EnvelopeMalformedError",
    # Factory functions
    "create_envelope_from_result",
    "create_allow_envelope",
    "create_deny_envelope",
    # Utilities
    "map_denial_reason",
    "validate_envelope",
]
