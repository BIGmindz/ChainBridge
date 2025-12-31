"""Runtime Boundary Guards.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Cody (GID-01) — Senior Backend Engineer             ║
║ EXECUTING COLOR: 🟢 BLUE                                             ║
║ PAC: PAC-CODY-A6-ARCHITECTURE-ENFORCEMENT-WIRING-01                  ║
╚══════════════════════════════════════════════════════════════════════╝

DOCTRINE (FAIL-CLOSED):
Runtimes (GitHub Copilot, ChatGPT, etc.) are EXECUTION ENGINES, not AGENTS.
They MUST NOT:
- Assign or claim GIDs (GID-NN pattern)
- Emit PDO decisions (only agents with valid GIDs can)
- Create proofs (proofs must be bound to agent identity)

INVARIANTS (NON-NEGOTIABLE):
- Runtime has NO GID
- Runtime cannot sign PDOs
- Runtime cannot create proofs
- All boundary violations → FAIL (execution blocked)

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Pattern for valid Agent GIDs (runtimes should NEVER match this)
AGENT_GID_PATTERN = re.compile(r"^GID-\d{2}$")

# Known runtime identifiers (these should never appear as signer/agent_id)
KNOWN_RUNTIME_IDENTIFIERS = frozenset({
    "github_copilot",
    "chatgpt",
    "claude",
    "gemini",
    "runtime",
    "system_runtime",
    "execution_runtime",
})

# Fields that ONLY agents can populate (runtimes must not set these)
AGENT_ONLY_FIELDS = frozenset({
    "agent_gid",
    "agent_id",  # When it contains GID
    "authority_gid",
    "authority_signature",
    "signer",  # When it starts with "agent::"
})


class RuntimeViolationType(str, Enum):
    """Types of runtime boundary violations."""

    RUNTIME_CLAIMS_GID = "RUNTIME_CLAIMS_GID"
    RUNTIME_SIGNS_PDO = "RUNTIME_SIGNS_PDO"
    RUNTIME_CREATES_PROOF = "RUNTIME_CREATES_PROOF"
    RUNTIME_EMITS_DECISION = "RUNTIME_EMITS_DECISION"
    RUNTIME_SETS_AUTHORITY = "RUNTIME_SETS_AUTHORITY"


@dataclass(frozen=True)
class RuntimeViolation:
    """Immutable record of a runtime boundary violation."""

    violation_type: RuntimeViolationType
    field: str
    value: str
    message: str
    timestamp: str


@dataclass(frozen=True)
class RuntimeGuardResult:
    """Result of runtime boundary check.

    Attributes:
        valid: True if no boundary violations detected
        violations: List of detected violations (empty if valid)
        checked_at: ISO 8601 timestamp of check
    """

    valid: bool
    violations: tuple[RuntimeViolation, ...]
    checked_at: str


# ---------------------------------------------------------------------------
# Runtime Boundary Guard
# ---------------------------------------------------------------------------


class RuntimeBoundaryGuard:
    """Guards against runtime identity escalation.

    Runtimes are execution engines that MUST NOT:
    - Claim agent GIDs
    - Sign PDOs as agents
    - Create proofs with agent identity
    - Emit decisions requiring agent authority

    DOCTRINE (FAIL-CLOSED):
    - Any violation → FAIL
    - No soft bypasses
    - All violations logged
    """

    def check_pdo_creation(
        self,
        pdo_data: Optional[dict],
        caller_identity: Optional[str] = None,
    ) -> RuntimeGuardResult:
        """Check PDO creation for runtime boundary violations.

        INVARIANTS:
        - PDO signer MUST be valid agent (not runtime)
        - PDO agent_id (if GID) MUST be valid agent
        - Runtime identifiers MUST NOT appear as signers

        Args:
            pdo_data: PDO data dictionary
            caller_identity: Identity of the caller (for logging)

        Returns:
            RuntimeGuardResult with any violations detected
        """
        violations: list[RuntimeViolation] = []
        timestamp = datetime.now(timezone.utc).isoformat()

        if pdo_data is None:
            return RuntimeGuardResult(
                valid=True,
                violations=(),
                checked_at=timestamp,
            )

        # Check signer field
        signer = pdo_data.get("signer")
        if signer and self._is_runtime_identity(signer):
            violations.append(RuntimeViolation(
                violation_type=RuntimeViolationType.RUNTIME_SIGNS_PDO,
                field="signer",
                value=str(signer)[:50],
                message=f"Runtime '{signer}' cannot sign PDOs. Only agents can sign.",
                timestamp=timestamp,
            ))

        # Check agent_id field (if it looks like a GID attempt by runtime)
        agent_id = pdo_data.get("agent_id")
        if agent_id:
            # If caller is known runtime but tries to set agent_id with GID
            if caller_identity and self._is_runtime_identity(caller_identity):
                if AGENT_GID_PATTERN.match(str(agent_id)):
                    violations.append(RuntimeViolation(
                        violation_type=RuntimeViolationType.RUNTIME_CLAIMS_GID,
                        field="agent_id",
                        value=str(agent_id),
                        message=f"Runtime cannot claim GID '{agent_id}'",
                        timestamp=timestamp,
                    ))

        # Check for runtime trying to set authority
        if caller_identity and self._is_runtime_identity(caller_identity):
            if pdo_data.get("authority_gid") or pdo_data.get("authority_signature"):
                violations.append(RuntimeViolation(
                    violation_type=RuntimeViolationType.RUNTIME_SETS_AUTHORITY,
                    field="authority_gid/authority_signature",
                    value="<present>",
                    message="Runtime cannot set authority fields. Only agents can authorize.",
                    timestamp=timestamp,
                ))

        result = RuntimeGuardResult(
            valid=len(violations) == 0,
            violations=tuple(violations),
            checked_at=timestamp,
        )

        # Log violations
        if not result.valid:
            self._log_violations(result, "pdo_creation", caller_identity)

        return result

    def check_proof_creation(
        self,
        proof_data: Optional[dict],
        caller_identity: Optional[str] = None,
    ) -> RuntimeGuardResult:
        """Check proof creation for runtime boundary violations.

        INVARIANTS:
        - Proofs MUST be bound to valid agent identity
        - Runtime cannot create proofs with agent binding

        Args:
            proof_data: Proof data dictionary
            caller_identity: Identity of the caller

        Returns:
            RuntimeGuardResult with any violations detected
        """
        violations: list[RuntimeViolation] = []
        timestamp = datetime.now(timezone.utc).isoformat()

        if proof_data is None:
            return RuntimeGuardResult(
                valid=True,
                violations=(),
                checked_at=timestamp,
            )

        # If caller is runtime, they cannot create proofs with agent binding
        if caller_identity and self._is_runtime_identity(caller_identity):
            agent_binding = proof_data.get("agent_id") or proof_data.get("agent_gid")
            if agent_binding:
                violations.append(RuntimeViolation(
                    violation_type=RuntimeViolationType.RUNTIME_CREATES_PROOF,
                    field="agent_id/agent_gid",
                    value=str(agent_binding)[:50],
                    message=f"Runtime cannot create proofs with agent binding '{agent_binding}'",
                    timestamp=timestamp,
                ))

        result = RuntimeGuardResult(
            valid=len(violations) == 0,
            violations=tuple(violations),
            checked_at=timestamp,
        )

        if not result.valid:
            self._log_violations(result, "proof_creation", caller_identity)

        return result

    def check_decision_emission(
        self,
        decision_data: Optional[dict],
        caller_identity: Optional[str] = None,
    ) -> RuntimeGuardResult:
        """Check decision emission for runtime boundary violations.

        INVARIANTS:
        - Decisions MUST be emitted by valid agents
        - Runtime cannot emit decisions requiring agent authority

        Args:
            decision_data: Decision data dictionary
            caller_identity: Identity of the caller

        Returns:
            RuntimeGuardResult with any violations detected
        """
        violations: list[RuntimeViolation] = []
        timestamp = datetime.now(timezone.utc).isoformat()

        if decision_data is None:
            return RuntimeGuardResult(
                valid=True,
                violations=(),
                checked_at=timestamp,
            )

        if caller_identity and self._is_runtime_identity(caller_identity):
            # Runtime cannot emit decisions at all
            violations.append(RuntimeViolation(
                violation_type=RuntimeViolationType.RUNTIME_EMITS_DECISION,
                field="decision",
                value="<decision_data>",
                message=f"Runtime '{caller_identity}' cannot emit decisions. Only agents can decide.",
                timestamp=timestamp,
            ))

        result = RuntimeGuardResult(
            valid=len(violations) == 0,
            violations=tuple(violations),
            checked_at=timestamp,
        )

        if not result.valid:
            self._log_violations(result, "decision_emission", caller_identity)

        return result

    def _is_runtime_identity(self, identity: str) -> bool:
        """Check if identity is a known runtime identifier.

        Returns True if identity is:
        - In KNOWN_RUNTIME_IDENTIFIERS
        - Contains 'runtime' (case-insensitive)
        - Starts with 'system::' (system signers are runtime context)
        """
        if not identity:
            return False

        identity_lower = identity.lower()

        # Direct match
        if identity_lower in KNOWN_RUNTIME_IDENTIFIERS:
            return True

        # Contains 'runtime'
        if "runtime" in identity_lower:
            return True

        # System signer pattern (system::xxx is runtime context)
        if identity_lower.startswith("system::"):
            return True

        return False

    def _log_violations(
        self,
        result: RuntimeGuardResult,
        check_type: str,
        caller_identity: Optional[str],
    ) -> None:
        """Log runtime boundary violations for audit."""
        log_data = {
            "event": "runtime_boundary_violation",
            "check_type": check_type,
            "caller_identity": caller_identity,
            "violation_count": len(result.violations),
            "violations": [
                {
                    "type": v.violation_type.value,
                    "field": v.field,
                    "value": v.value[:20] + "..." if len(v.value) > 20 else v.value,
                    "message": v.message,
                }
                for v in result.violations
            ],
            "checked_at": result.checked_at,
        }

        logger.warning(
            "Runtime boundary violation detected: %s",
            log_data,
        )


# ---------------------------------------------------------------------------
# Module-level guard instance
# ---------------------------------------------------------------------------

_runtime_guard = RuntimeBoundaryGuard()


def check_runtime_boundary_pdo(
    pdo_data: Optional[dict],
    caller_identity: Optional[str] = None,
) -> RuntimeGuardResult:
    """Check PDO creation for runtime boundary violations.

    Module-level convenience function.

    Args:
        pdo_data: PDO data dictionary
        caller_identity: Identity of the caller

    Returns:
        RuntimeGuardResult with any violations detected
    """
    return _runtime_guard.check_pdo_creation(pdo_data, caller_identity)


def check_runtime_boundary_proof(
    proof_data: Optional[dict],
    caller_identity: Optional[str] = None,
) -> RuntimeGuardResult:
    """Check proof creation for runtime boundary violations.

    Module-level convenience function.

    Args:
        proof_data: Proof data dictionary
        caller_identity: Identity of the caller

    Returns:
        RuntimeGuardResult with any violations detected
    """
    return _runtime_guard.check_proof_creation(proof_data, caller_identity)


def check_runtime_boundary_decision(
    decision_data: Optional[dict],
    caller_identity: Optional[str] = None,
) -> RuntimeGuardResult:
    """Check decision emission for runtime boundary violations.

    Module-level convenience function.

    Args:
        decision_data: Decision data dictionary
        caller_identity: Identity of the caller

    Returns:
        RuntimeGuardResult with any violations detected
    """
    return _runtime_guard.check_decision_emission(decision_data, caller_identity)


# ═══════════════════════════════════════════════════════════════════════════
# END — Cody (GID-01) — 🔵
# ═══════════════════════════════════════════════════════════════════════════
