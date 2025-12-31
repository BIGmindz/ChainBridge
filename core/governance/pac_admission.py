"""
PAC Admission Gate
════════════════════════════════════════════════════════════════════════════════

Enforces constitutional lock acknowledgment for PAC execution.

No PAC may execute unless:
1. All applicable locks are acknowledged
2. No forbidden zones are touched without supersession
3. All scopes are declared

PAC Reference: PAC-CODY-CONSTITUTION-ENFORCEMENT-02
Effective Date: 2025-12-18

INVARIANTS:
- PAC without lock acknowledgment cannot execute
- Lock acknowledgment is not optional
- Forbidden zone violation halts PAC
- All enforcement is fail-closed

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from core.governance.constitution_engine import (
    ConstitutionEngine,
    ForbiddenZoneError,
    PACAdmissionError,
    get_constitution_engine,
)
from core.governance.color_gateway import (
    validate_execution,
    ColorGatewayViolation,
)
from core.governance.agent_roster import get_agent_by_name
from core.governance.activation_block import (
    ActivationBlock,
    ActivationBlockViolationError,
    validate_activation_block,
)

logger = logging.getLogger("governance.pac_admission")


# ═══════════════════════════════════════════════════════════════════════════════
# END BANNER ENFORCEMENT — PAC-BENSON-CODY-END-BANNER-LINT-ENFORCEMENT-01
# ═══════════════════════════════════════════════════════════════════════════════


class EndBannerViolationError(Exception):
    """
    END banner validation failed. HARD STOP.

    Raised when:
    - END banner agent doesn't match EXECUTING AGENT
    - END banner GID doesn't match agent's canonical GID
    - END banner color doesn't match agent's canonical color
    """

    def __init__(self, message: str, pac_id: Optional[str] = None):
        self.message = message
        self.pac_id = pac_id
        super().__init__(f"END banner violation: {message} (PAC: {pac_id or 'unknown'})")


# ═══════════════════════════════════════════════════════════════════════════════
# TELEMETRY EVENTS
# ═══════════════════════════════════════════════════════════════════════════════


class PACAdmissionOutcome(Enum):
    """PAC admission outcomes."""

    ADMITTED = "ADMITTED"
    DENIED_MISSING_LOCKS = "DENIED_MISSING_LOCKS"
    DENIED_FORBIDDEN_ZONE = "DENIED_FORBIDDEN_ZONE"
    DENIED_MISSING_SCOPES = "DENIED_MISSING_SCOPES"
    DENIED_INVALID_PAC = "DENIED_INVALID_PAC"
    DENIED_ACTIVATION_BLOCK = "DENIED_ACTIVATION_BLOCK"  # Activation Block violation
    DENIED_COLOR_GATEWAY = "DENIED_COLOR_GATEWAY"  # Color Gateway violation
    DENIED_END_BANNER = "DENIED_END_BANNER"  # END banner violation


@dataclass(frozen=True)
class PACAdmissionEvent:
    """Telemetry event for PAC admission decision."""

    pac_id: str
    outcome: PACAdmissionOutcome
    acknowledged_locks: tuple[str, ...]
    required_locks: tuple[str, ...]
    missing_locks: tuple[str, ...]
    affected_scopes: tuple[str, ...]
    touched_files: tuple[str, ...]
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for telemetry emission."""
        return {
            "event": "PAC_ADMISSION",
            "pac_id": self.pac_id,
            "outcome": self.outcome.value,
            "acknowledged_locks": list(self.acknowledged_locks),
            "required_locks": list(self.required_locks),
            "missing_locks": list(self.missing_locks),
            "affected_scopes": list(self.affected_scopes),
            "touched_files": list(self.touched_files),
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PAC DECLARATION
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PACDeclaration:
    """
    PAC declaration for admission gate.

    Every PAC must declare:
    - pac_id: Unique identifier (e.g., PAC-CODY-CONSTITUTION-ENFORCEMENT-02)
    - acknowledged_locks: Lock IDs the PAC acknowledges
    - affected_scopes: Scopes the PAC modifies
    - touched_files: Files the PAC will create/modify (optional)
    - executing_agent: Agent name executing the PAC (optional, for Color Gateway)
    - executing_gid: Agent GID executing the PAC (optional, for Color Gateway)
    - executing_color: Agent color lane executing the PAC (optional, for Color Gateway)
    - end_banner_agent: Agent name in END banner (optional, for END banner validation)
    - end_banner_gid: GID in END banner (optional, for END banner validation)
    - end_banner_color: Color in END banner (optional, for END banner validation)
    - activation_block: Activation Block for identity enforcement (REQUIRED for execution)
    """

    pac_id: str
    acknowledged_locks: tuple[str, ...]
    affected_scopes: tuple[str, ...]
    touched_files: tuple[str, ...] = field(default_factory=tuple)
    executing_agent: Optional[str] = None
    executing_gid: Optional[str] = None
    executing_color: Optional[str] = None
    end_banner_agent: Optional[str] = None
    end_banner_gid: Optional[str] = None
    end_banner_color: Optional[str] = None
    # Activation Block — REQUIRED for execution (PAC-BENSON-ACTIVATION-BLOCK-IMPLEMENTATION-01)
    activation_block: ActivationBlock | None = None

    def __post_init__(self) -> None:
        """Validate PAC declaration."""
        if not self.pac_id:
            raise ValueError("PAC ID cannot be empty")
        if not self.pac_id.startswith("PAC-"):
            raise ValueError(f"Invalid PAC ID format: {self.pac_id}")
        if not self.affected_scopes:
            raise ValueError("PAC must declare at least one affected scope")


# ═══════════════════════════════════════════════════════════════════════════════
# PAC ADMISSION GATE
# ═══════════════════════════════════════════════════════════════════════════════


class PACAdmissionGate:
    """
    PAC Admission Gate - enforces lock acknowledgment.

    Usage:
        gate = PACAdmissionGate()
        declaration = PACDeclaration(
            pac_id="PAC-CODY-FEATURE-01",
            acknowledged_locks=["LOCK-GW-IMMUTABILITY-001"],
            affected_scopes=["gateway"],
            touched_files=["gateway/new_module.py"],
        )
        gate.admit(declaration)  # Raises PACAdmissionError if denied
    """

    def __init__(self, engine: ConstitutionEngine | None = None):
        """Initialize PAC Admission Gate."""
        self._engine = engine or get_constitution_engine()
        self._events: list[PACAdmissionEvent] = []

    def admit(self, declaration: PACDeclaration) -> PACAdmissionEvent:
        """
        Evaluate PAC admission.

        Args:
            declaration: PAC declaration with acknowledged locks and scopes

        Returns:
            PACAdmissionEvent for successful admission

        Raises:
            PACAdmissionError: If PAC fails admission
            ActivationBlockViolationError: If Activation Block validation fails
            ColorGatewayViolation: If Color Gateway check fails
            EndBannerViolationError: If END banner validation fails
        """
        self._engine.ensure_loaded()

        # === ACTIVATION BLOCK ENFORCEMENT (FIRST — PAC-BENSON-ACTIVATION-BLOCK-IMPLEMENTATION-01) ===
        # Activation Block validation MUST run BEFORE Color Gateway and END banner
        if declaration.activation_block is not None:
            try:
                validate_activation_block(declaration.activation_block, declaration.pac_id)
            except ActivationBlockViolationError as e:
                event = PACAdmissionEvent(
                    pac_id=declaration.pac_id,
                    outcome=PACAdmissionOutcome.DENIED_ACTIVATION_BLOCK,
                    acknowledged_locks=declaration.acknowledged_locks,
                    required_locks=(),
                    missing_locks=(),
                    affected_scopes=declaration.affected_scopes,
                    touched_files=declaration.touched_files,
                    reason=f"Activation Block violation: {e.message}",
                )
                self._emit_event(event)
                raise  # Re-raise for stop-the-line

        # === COLOR GATEWAY ENFORCEMENT ===
        # If executing agent info is provided, validate Color Gateway
        if declaration.executing_gid and declaration.executing_color:
            try:
                validate_execution(
                    executing_agent_gid=declaration.executing_gid,
                    executing_color=declaration.executing_color,
                    pac_id=declaration.pac_id,
                )
            except ColorGatewayViolation as e:
                event = PACAdmissionEvent(
                    pac_id=declaration.pac_id,
                    outcome=PACAdmissionOutcome.DENIED_COLOR_GATEWAY,
                    acknowledged_locks=declaration.acknowledged_locks,
                    required_locks=(),
                    missing_locks=(),
                    affected_scopes=declaration.affected_scopes,
                    touched_files=declaration.touched_files,
                    reason=f"Color Gateway violation: {e}",
                )
                self._emit_event(event)
                raise  # Re-raise for stop-the-line

        # === END BANNER ENFORCEMENT ===
        # Validate END banner if provided
        end_banner_error = self._validate_end_banner(declaration)
        if end_banner_error:
            event = PACAdmissionEvent(
                pac_id=declaration.pac_id,
                outcome=PACAdmissionOutcome.DENIED_END_BANNER,
                acknowledged_locks=declaration.acknowledged_locks,
                required_locks=(),
                missing_locks=(),
                affected_scopes=declaration.affected_scopes,
                touched_files=declaration.touched_files,
                reason=f"END banner violation: {end_banner_error}",
            )
            self._emit_event(event)
            raise EndBannerViolationError(end_banner_error, declaration.pac_id)

        # Get required locks for declared scopes
        required_locks = self._get_required_locks(declaration.affected_scopes)
        acknowledged_set = set(declaration.acknowledged_locks)
        required_set = set(required_locks)

        # Check for missing acknowledgments
        missing = list(required_set - acknowledged_set)

        # Check for forbidden zone violations
        forbidden_violations = self._check_forbidden_zones(
            list(declaration.touched_files)
        )

        if forbidden_violations:
            event = PACAdmissionEvent(
                pac_id=declaration.pac_id,
                outcome=PACAdmissionOutcome.DENIED_FORBIDDEN_ZONE,
                acknowledged_locks=declaration.acknowledged_locks,
                required_locks=tuple(required_locks),
                missing_locks=tuple(forbidden_violations),
                affected_scopes=declaration.affected_scopes,
                touched_files=declaration.touched_files,
                reason=f"Forbidden zone violations: {', '.join(forbidden_violations)}",
            )
            self._emit_event(event)
            raise ForbiddenZoneError(
                lock_id=forbidden_violations[0].split(":")[1] if ":" in forbidden_violations[0] else "UNKNOWN",
                zone=forbidden_violations[0],
            )

        if missing:
            event = PACAdmissionEvent(
                pac_id=declaration.pac_id,
                outcome=PACAdmissionOutcome.DENIED_MISSING_LOCKS,
                acknowledged_locks=declaration.acknowledged_locks,
                required_locks=tuple(required_locks),
                missing_locks=tuple(missing),
                affected_scopes=declaration.affected_scopes,
                touched_files=declaration.touched_files,
                reason=f"Missing lock acknowledgments: {', '.join(missing)}",
            )
            self._emit_event(event)
            raise PACAdmissionError(
                reason=f"Missing lock acknowledgments: {', '.join(missing)}",
                missing_locks=missing,
            )

        # Admission granted
        event = PACAdmissionEvent(
            pac_id=declaration.pac_id,
            outcome=PACAdmissionOutcome.ADMITTED,
            acknowledged_locks=declaration.acknowledged_locks,
            required_locks=tuple(required_locks),
            missing_locks=(),
            affected_scopes=declaration.affected_scopes,
            touched_files=declaration.touched_files,
            reason="All required locks acknowledged",
        )
        self._emit_event(event)

        logger.info(
            "PAC admitted: %s (acknowledged %d locks for %d scopes)",
            declaration.pac_id,
            len(declaration.acknowledged_locks),
            len(declaration.affected_scopes),
        )

        return event

    def _get_required_locks(self, scopes: tuple[str, ...]) -> list[str]:
        """Get all locks required for given scopes."""
        required = set()
        for scope in scopes:
            for lock in self._engine.get_locks_by_scope(scope):
                if lock.status == "ACTIVE":
                    # Only require pac_gate locks
                    if any("pac_gate" in str(e) for e in lock.enforcement):
                        required.add(lock.lock_id)
        return sorted(required)

    def _check_forbidden_zones(self, files: list[str]) -> list[str]:
        """Check if any files are in forbidden zones."""
        violations = []
        for file_path in files:
            lock = self._engine.check_forbidden_zone(file_path)
            if lock:
                violations.append(f"FORBIDDEN_ZONE:{lock.lock_id}:{file_path}")
        return violations

    def _validate_end_banner(self, declaration: PACDeclaration) -> Optional[str]:
        """
        Validate END banner against executing agent info.

        Returns:
            Error message if validation fails, None if passes
        """
        # Skip if no END banner info provided
        if not declaration.end_banner_agent:
            return None

        # Check: END banner agent must match EXECUTING AGENT
        if declaration.executing_agent:
            if declaration.end_banner_agent.upper() != declaration.executing_agent.upper():
                return (
                    f"END banner agent '{declaration.end_banner_agent}' "
                    f"does not match EXECUTING AGENT '{declaration.executing_agent}'"
                )

        # Check: END banner GID must match canonical GID
        if declaration.end_banner_gid:
            agent = get_agent_by_name(declaration.end_banner_agent)
            if agent is None:
                return f"Unknown agent in END banner: {declaration.end_banner_agent}"

            if declaration.end_banner_gid.upper() != agent.gid:
                return (
                    f"END banner GID '{declaration.end_banner_gid}' "
                    f"does not match canonical GID '{agent.gid}' for {agent.name}"
                )

        # Check: END banner color must match canonical color
        if declaration.end_banner_color:
            agent = get_agent_by_name(declaration.end_banner_agent)
            if agent is None:
                return f"Unknown agent in END banner: {declaration.end_banner_agent}"

            # Normalize color names
            declared_color = declaration.end_banner_color.upper().replace(" ", "_")
            canonical_color = agent.color.upper().replace(" ", "_")

            if declared_color != canonical_color:
                return (
                    f"END banner color '{declaration.end_banner_color}' "
                    f"does not match canonical color '{agent.color}' for {agent.name}"
                )

        return None

    def _emit_event(self, event: PACAdmissionEvent) -> None:
        """Emit telemetry event."""
        self._events.append(event)
        # Structured logging for telemetry
        import json
        logger.info(
            "PAC_ADMISSION: %s",
            json.dumps(event.to_dict(), separators=(",", ":")),
        )

    def get_events(self) -> list[PACAdmissionEvent]:
        """Get all admission events (for testing)."""
        return list(self._events)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL CONVENIENCE
# ═══════════════════════════════════════════════════════════════════════════════

_gate: PACAdmissionGate | None = None


def get_pac_admission_gate() -> PACAdmissionGate:
    """Get or create the singleton PAC Admission Gate."""
    global _gate
    if _gate is None:
        _gate = PACAdmissionGate()
    return _gate


def reset_pac_admission_gate() -> None:
    """Reset the singleton (for testing)."""
    global _gate
    _gate = None


def admit_pac(declaration: PACDeclaration) -> PACAdmissionEvent:
    """
    Convenience function to admit a PAC.

    Usage:
        from core.governance.pac_admission import admit_pac, PACDeclaration

        admit_pac(PACDeclaration(
            pac_id="PAC-CODY-FEATURE-01",
            acknowledged_locks=["LOCK-GW-IMMUTABILITY-001"],
            affected_scopes=["gateway"],
        ))
    """
    gate = get_pac_admission_gate()
    return gate.admit(declaration)


def get_required_locks_for_scopes(scopes: list[str]) -> list[str]:
    """
    Get required locks for given scopes.

    Useful for PAC authors to know what to acknowledge.
    """
    gate = get_pac_admission_gate()
    return gate._get_required_locks(tuple(scopes))
