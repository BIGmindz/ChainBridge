"""
🟣 DAN (GID-07) — Governance Event Schema
PAC-GOV-OBS-01: Governance Observability & Event Telemetry

Canonical schema for all governance-relevant events.
This is the single source of truth for governance telemetry.

Events are:
- Deterministic
- Auditable
- Append-only
- Non-blocking
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

# ═══════════════════════════════════════════════════════════════════════════════
# EVENT TYPES
# ═══════════════════════════════════════════════════════════════════════════════


class GovernanceEventType(str, Enum):
    """Canonical governance event types."""

    # ACM (Access Control Matrix)
    ACM_EVALUATED = "ACM_EVALUATED"

    # Decision outcomes
    DECISION_ALLOWED = "DECISION_ALLOWED"
    DECISION_DENIED = "DECISION_DENIED"
    DECISION_ESCALATED = "DECISION_ESCALATED"

    # DRCP (Denial, Rejection, Correction Protocol)
    DRCP_TRIGGERED = "DRCP_TRIGGERED"

    # Diggi (Bounded Correction)
    DIGGI_CORRECTION_ISSUED = "DIGGI_CORRECTION_ISSUED"

    # Tool Execution
    TOOL_EXECUTION_ALLOWED = "TOOL_EXECUTION_ALLOWED"
    TOOL_EXECUTION_DENIED = "TOOL_EXECUTION_DENIED"

    # Artifact Integrity
    ARTIFACT_VERIFIED = "ARTIFACT_VERIFIED"
    ARTIFACT_VERIFICATION_FAILED = "ARTIFACT_VERIFICATION_FAILED"

    # Scope Guard
    SCOPE_VIOLATION = "SCOPE_VIOLATION"

    # Boot / Startup
    GOVERNANCE_BOOT_PASSED = "GOVERNANCE_BOOT_PASSED"
    GOVERNANCE_BOOT_FAILED = "GOVERNANCE_BOOT_FAILED"

    # Governance Drift (PAC-GOV-OBS-01)
    GOVERNANCE_DRIFT_DETECTED = "GOVERNANCE_DRIFT_DETECTED"


# Type alias for event type literals (for type checking)
EventTypeLiteral = Literal[
    "ACM_EVALUATED",
    "DECISION_ALLOWED",
    "DECISION_DENIED",
    "DECISION_ESCALATED",
    "DRCP_TRIGGERED",
    "DIGGI_CORRECTION_ISSUED",
    "TOOL_EXECUTION_ALLOWED",
    "TOOL_EXECUTION_DENIED",
    "ARTIFACT_VERIFIED",
    "ARTIFACT_VERIFICATION_FAILED",
    "SCOPE_VIOLATION",
    "GOVERNANCE_BOOT_PASSED",
    "GOVERNANCE_BOOT_FAILED",
    "GOVERNANCE_DRIFT_DETECTED",
]


# ═══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE EVENT SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════


def _generate_event_id() -> str:
    """Generate unique event ID."""
    return f"gov-{uuid.uuid4().hex[:12]}"


def _utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass
class GovernanceEvent:
    """
    Canonical governance event schema.

    This is the single schema for all governance telemetry.
    All fields are optional except event_type and timestamp.

    Attributes:
        event_id: Unique identifier for this event
        timestamp: UTC timestamp when event occurred
        event_type: Type of governance event (from GovernanceEventType)
        agent_gid: GID of the agent involved (e.g., "GID-07")
        verb: Action verb (e.g., "execute", "read", "write")
        target: Target of the action (e.g., tool name, file path)
        decision: Decision outcome (e.g., "ALLOW", "DENY", "ESCALATE")
        reason_code: Machine-readable reason code
        audit_ref: Reference to audit trail or proofpack
        artifact_hash: Hash of relevant artifact (for integrity events)
        metadata: Additional context as key-value pairs
    """

    event_type: GovernanceEventType | str
    timestamp: datetime = field(default_factory=_utc_now)
    event_id: str = field(default_factory=_generate_event_id)
    agent_gid: str | None = None
    verb: str | None = None
    target: str | None = None
    decision: str | None = None
    reason_code: str | None = None
    audit_ref: str | None = None
    artifact_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize event_type to string."""
        if isinstance(self.event_type, GovernanceEventType):
            self.event_type = self.event_type.value

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns ISO 8601 timestamp string.
        """
        data = asdict(self)
        # Convert datetime to ISO string
        if isinstance(data["timestamp"], datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        # Remove None values for cleaner output
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GovernanceEvent:
        """
        Create event from dictionary.

        Parses ISO 8601 timestamp string.
        """
        # Parse timestamp if string
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# EVENT FACTORIES
# ═══════════════════════════════════════════════════════════════════════════════


def acm_evaluated_event(
    agent_gid: str,
    verb: str,
    target: str,
    decision: str,
    *,
    reason_code: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernanceEvent:
    """Create ACM_EVALUATED event."""
    return GovernanceEvent(
        event_type=GovernanceEventType.ACM_EVALUATED,
        agent_gid=agent_gid,
        verb=verb,
        target=target,
        decision=decision,
        reason_code=reason_code,
        metadata=metadata or {},
    )


def decision_allowed_event(
    agent_gid: str,
    verb: str,
    target: str,
    *,
    audit_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernanceEvent:
    """Create DECISION_ALLOWED event."""
    return GovernanceEvent(
        event_type=GovernanceEventType.DECISION_ALLOWED,
        agent_gid=agent_gid,
        verb=verb,
        target=target,
        decision="ALLOW",
        audit_ref=audit_ref,
        metadata=metadata or {},
    )


def decision_denied_event(
    agent_gid: str,
    verb: str,
    target: str,
    reason_code: str,
    *,
    audit_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernanceEvent:
    """Create DECISION_DENIED event."""
    return GovernanceEvent(
        event_type=GovernanceEventType.DECISION_DENIED,
        agent_gid=agent_gid,
        verb=verb,
        target=target,
        decision="DENY",
        reason_code=reason_code,
        audit_ref=audit_ref,
        metadata=metadata or {},
    )


def decision_escalated_event(
    agent_gid: str,
    verb: str,
    target: str,
    reason_code: str,
    *,
    audit_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernanceEvent:
    """Create DECISION_ESCALATED event."""
    return GovernanceEvent(
        event_type=GovernanceEventType.DECISION_ESCALATED,
        agent_gid=agent_gid,
        verb=verb,
        target=target,
        decision="ESCALATE",
        reason_code=reason_code,
        audit_ref=audit_ref,
        metadata=metadata or {},
    )


def drcp_triggered_event(
    agent_gid: str,
    verb: str,
    target: str,
    reason_code: str,
    *,
    audit_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernanceEvent:
    """Create DRCP_TRIGGERED event."""
    return GovernanceEvent(
        event_type=GovernanceEventType.DRCP_TRIGGERED,
        agent_gid=agent_gid,
        verb=verb,
        target=target,
        reason_code=reason_code,
        audit_ref=audit_ref,
        metadata=metadata or {},
    )


def diggi_correction_event(
    agent_gid: str,
    target: str,
    *,
    correction_type: str | None = None,
    audit_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernanceEvent:
    """Create DIGGI_CORRECTION_ISSUED event."""
    meta = metadata or {}
    if correction_type:
        meta["correction_type"] = correction_type
    return GovernanceEvent(
        event_type=GovernanceEventType.DIGGI_CORRECTION_ISSUED,
        agent_gid=agent_gid,
        target=target,
        audit_ref=audit_ref,
        metadata=meta,
    )


def tool_execution_event(
    agent_gid: str,
    tool_name: str,
    allowed: bool,
    *,
    reason_code: str | None = None,
    audit_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernanceEvent:
    """Create TOOL_EXECUTION_ALLOWED or TOOL_EXECUTION_DENIED event."""
    event_type = GovernanceEventType.TOOL_EXECUTION_ALLOWED if allowed else GovernanceEventType.TOOL_EXECUTION_DENIED
    return GovernanceEvent(
        event_type=event_type,
        agent_gid=agent_gid,
        verb="execute",
        target=tool_name,
        decision="ALLOW" if allowed else "DENY",
        reason_code=reason_code,
        audit_ref=audit_ref,
        metadata=metadata or {},
    )


def artifact_verification_event(
    passed: bool,
    artifact_hash: str | None = None,
    *,
    file_count: int | None = None,
    files_verified: int | None = None,  # Alias for file_count
    mismatches: list[str] | None = None,
    manifest_path: str | None = None,
    audit_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernanceEvent:
    """Create ARTIFACT_VERIFIED or ARTIFACT_VERIFICATION_FAILED event."""
    event_type = GovernanceEventType.ARTIFACT_VERIFIED if passed else GovernanceEventType.ARTIFACT_VERIFICATION_FAILED
    meta = metadata or {}
    # Support both file_count and files_verified (alias)
    count = files_verified if files_verified is not None else file_count
    if count is not None:
        meta["file_count"] = count
        meta["files_verified"] = count  # Also set alias for compatibility
    if mismatches:
        meta["mismatches"] = mismatches
    if manifest_path:
        meta["manifest_path"] = manifest_path
    return GovernanceEvent(
        event_type=event_type,
        decision="PASS" if passed else "FAIL",
        artifact_hash=artifact_hash or "",
        audit_ref=audit_ref,
        metadata=meta,
    )


def scope_violation_event(
    file_path: str,
    violation_type: str,
    *,
    pattern: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernanceEvent:
    """Create SCOPE_VIOLATION event."""
    meta = metadata or {}
    meta["violation_type"] = violation_type
    if pattern:
        meta["pattern"] = pattern
    return GovernanceEvent(
        event_type=GovernanceEventType.SCOPE_VIOLATION,
        target=file_path,
        reason_code=violation_type,
        metadata=meta,
    )


def governance_boot_event(
    passed: bool,
    *,
    checks_passed: int | None = None,
    checks_failed: int | None = None,
    failures: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> GovernanceEvent:
    """Create GOVERNANCE_BOOT_PASSED or GOVERNANCE_BOOT_FAILED event."""
    event_type = GovernanceEventType.GOVERNANCE_BOOT_PASSED if passed else GovernanceEventType.GOVERNANCE_BOOT_FAILED
    meta = metadata or {}
    if checks_passed is not None:
        meta["checks_passed"] = checks_passed
    if checks_failed is not None:
        meta["checks_failed"] = checks_failed
    if failures:
        meta["failures"] = failures
    return GovernanceEvent(
        event_type=event_type,
        decision="PASS" if passed else "FAIL",
        metadata=meta,
    )


def governance_drift_event(
    original_hash: str,
    current_hash: str,
    message: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> GovernanceEvent:
    """Create GOVERNANCE_DRIFT_DETECTED event (PAC-GOV-OBS-01)."""
    meta = metadata or {}
    meta["original_hash"] = original_hash
    meta["current_hash"] = current_hash
    meta["message"] = message
    return GovernanceEvent(
        event_type=GovernanceEventType.GOVERNANCE_DRIFT_DETECTED,
        decision="BLOCKED",
        reason_code="GOVERNANCE_DRIFT",
        metadata=meta,
    )
