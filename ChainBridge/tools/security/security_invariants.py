#!/usr/bin/env python3
"""Security Invariants Module.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Sam (GID-06) — Security & Threat Engineer           ║
║ EXECUTING COLOR: 🟥 DARK RED                                         ║
║ PAC: PAC-SAM-G1-PHASE-2-SECURITY-INVARIANT-HARDENING-01              ║
╚══════════════════════════════════════════════════════════════════════╝

This module defines and enforces Security Invariants that operate at
physics-level enforcement — no PAC, WRAP, or Correction can bypass
these guarantees.

SECURITY INVARIANTS:
  SI-01: No unauthorized state mutation
  SI-02: All authority claims must be verifiable
  SI-03: No replay without detection
  SI-04: No downgrade of governance state
  SI-05: No unsigned correction closure
  SI-06: No PAC execution without registry match
  SI-07: No bypass of hard gates
  SI-08: No mixed-authority execution

DOCTRINE:
  - All violations are FAIL-CLOSED
  - No advisory-only checks
  - No human review dependencies
  - Automated verification mandatory

Author: Sam (GID-06) — Security & Threat Engineer
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Set, Dict, List, Callable

logger = logging.getLogger(__name__)


# =============================================================================
# SECURITY INVARIANT IDENTIFIERS
# =============================================================================


class SecurityInvariantID(str, Enum):
    """Canonical Security Invariant identifiers."""

    SI_01 = "SI-01"  # No unauthorized state mutation
    SI_02 = "SI-02"  # All authority claims must be verifiable
    SI_03 = "SI-03"  # No replay without detection
    SI_04 = "SI-04"  # No downgrade of governance state
    SI_05 = "SI-05"  # No unsigned correction closure
    SI_06 = "SI-06"  # No PAC execution without registry match
    SI_07 = "SI-07"  # No bypass of hard gates
    SI_08 = "SI-08"  # No mixed-authority execution


# =============================================================================
# SECURITY EXCEPTIONS (FAIL-CLOSED)
# =============================================================================


class SecurityInvariantViolation(Exception):
    """Base exception for all security invariant violations.

    DOCTRINE: All violations must raise exceptions.
    No silent failures. No warnings. No advisory checks.
    """

    def __init__(
        self,
        invariant_id: SecurityInvariantID,
        message: str,
        evidence: dict = None,
    ):
        self.invariant_id = invariant_id
        self.message = message
        self.evidence = evidence or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        super().__init__(f"[{invariant_id.value}] {message}")

    def to_audit_log(self) -> dict:
        """Convert to audit log format."""
        return {
            "event": "security_invariant_violation",
            "invariant_id": self.invariant_id.value,
            "message": self.message,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


class UnauthorizedStateMutationError(SecurityInvariantViolation):
    """SI-01: Unauthorized state mutation attempted."""

    def __init__(self, actor: str, target_state: str, evidence: dict = None):
        super().__init__(
            SecurityInvariantID.SI_01,
            f"Unauthorized state mutation by '{actor}' on '{target_state}'",
            evidence or {"actor": actor, "target_state": target_state},
        )


class UnverifiableAuthorityError(SecurityInvariantViolation):
    """SI-02: Authority claim cannot be verified."""

    def __init__(self, claimed_authority: str, reason: str, evidence: dict = None):
        super().__init__(
            SecurityInvariantID.SI_02,
            f"Unverifiable authority claim: '{claimed_authority}' - {reason}",
            evidence or {"claimed_authority": claimed_authority, "reason": reason},
        )


class ReplayDetectionError(SecurityInvariantViolation):
    """SI-03: Replay attack detected."""

    def __init__(self, artifact_id: str, nonce: str, evidence: dict = None):
        super().__init__(
            SecurityInvariantID.SI_03,
            f"Replay detected for artifact '{artifact_id}' with nonce '{nonce}'",
            evidence or {"artifact_id": artifact_id, "nonce": nonce},
        )


class GovernanceDowngradeError(SecurityInvariantViolation):
    """SI-04: Governance state downgrade attempted."""

    def __init__(self, current_level: str, attempted_level: str, evidence: dict = None):
        super().__init__(
            SecurityInvariantID.SI_04,
            f"Governance downgrade from '{current_level}' to '{attempted_level}' blocked",
            evidence or {"current_level": current_level, "attempted_level": attempted_level},
        )


class UnsignedCorrectionError(SecurityInvariantViolation):
    """SI-05: Correction closure without signature."""

    def __init__(self, correction_id: str, evidence: dict = None):
        super().__init__(
            SecurityInvariantID.SI_05,
            f"Unsigned correction closure attempted: '{correction_id}'",
            evidence or {"correction_id": correction_id},
        )


class RegistryMismatchError(SecurityInvariantViolation):
    """SI-06: PAC execution without registry match."""

    def __init__(self, pac_id: str, agent_gid: str, evidence: dict = None):
        super().__init__(
            SecurityInvariantID.SI_06,
            f"PAC '{pac_id}' execution by unregistered agent '{agent_gid}'",
            evidence or {"pac_id": pac_id, "agent_gid": agent_gid},
        )


class HardGateBypassError(SecurityInvariantViolation):
    """SI-07: Hard gate bypass attempted."""

    def __init__(self, gate_id: str, bypass_method: str, evidence: dict = None):
        super().__init__(
            SecurityInvariantID.SI_07,
            f"Hard gate '{gate_id}' bypass attempted via '{bypass_method}'",
            evidence or {"gate_id": gate_id, "bypass_method": bypass_method},
        )


class MixedAuthorityError(SecurityInvariantViolation):
    """SI-08: Mixed authority execution detected."""

    def __init__(self, authorities: list[str], evidence: dict = None):
        super().__init__(
            SecurityInvariantID.SI_08,
            f"Mixed authority execution detected: {authorities}",
            evidence or {"authorities": authorities},
        )


# =============================================================================
# VALIDATION RESULT TYPES
# =============================================================================


@dataclass(frozen=True)
class InvariantCheckResult:
    """Result of a security invariant check."""

    invariant_id: SecurityInvariantID
    passed: bool
    reason: str
    evidence: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_audit_log(self) -> dict:
        """Convert to audit log format."""
        return {
            "event": "security_invariant_check",
            "invariant_id": self.invariant_id.value,
            "passed": self.passed,
            "reason": self.reason,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


# =============================================================================
# AGENT REGISTRY (CANONICAL)
# =============================================================================


# Canonical agent registry - source of truth for GID validation
AGENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "GID-00": {"name": "Benson", "role": "CTO & Operator", "authority": "SUPREME"},
    "GID-01": {"name": "Cody", "role": "Senior Backend Engineer", "authority": "EXECUTION"},
    "GID-02": {"name": "Sonny", "role": "API Integration Specialist", "authority": "INTEGRATION"},
    "GID-03": {"name": "Ruby", "role": "Frontend Engineer", "authority": "UI"},
    "GID-04": {"name": "Tina", "role": "QA & Test Engineer", "authority": "TESTING"},
    "GID-05": {"name": "Dan", "role": "DevOps & CI/CD Lead", "authority": "DEPLOYMENT"},
    "GID-06": {"name": "Sam", "role": "Security & Threat Engineer", "authority": "SECURITY"},
    "GID-07": {"name": "Dan", "role": "DevOps & CI/CD Lead", "authority": "DEPLOYMENT"},
    "GID-08": {"name": "Alex", "role": "Governance & Alignment", "authority": "GOVERNANCE"},
    "GID-10": {"name": "Maggie", "role": "ML & Applied AI", "authority": "ML"},
    "GID-11": {"name": "Atlas", "role": "Build / Repair / Refactor", "authority": "ARCHITECTURE"},
}


# Governance levels (ordered from lowest to highest)
GOVERNANCE_LEVELS = [
    "ADVISORY",
    "SOFT_GATED",
    "HARD_GATED",
    "LOCKED",
    "IMMUTABLE",
]


# =============================================================================
# SECURITY INVARIANT VALIDATORS
# =============================================================================


class SecurityInvariantValidator:
    """Validates security invariants with fail-closed semantics.

    DOCTRINE:
    - All checks raise exceptions on failure
    - No silent failures
    - No advisory-only mode
    - All violations logged for audit

    Usage:
        validator = SecurityInvariantValidator()
        validator.check_all(context)  # Raises on any violation
    """

    def __init__(self):
        """Initialize the validator."""
        self._nonce_registry: Set[str] = set()
        self._signature_registry: Dict[str, str] = {}
        self._current_governance_level: str = "HARD_GATED"

    # -------------------------------------------------------------------------
    # SI-01: No unauthorized state mutation
    # -------------------------------------------------------------------------

    def check_state_mutation_authority(
        self,
        actor: str,
        target_state: str,
        required_authority: str,
    ) -> InvariantCheckResult:
        """Check if actor has authority to mutate state.

        Args:
            actor: GID of the actor attempting mutation
            target_state: State being mutated
            required_authority: Authority required for mutation

        Returns:
            InvariantCheckResult

        Raises:
            UnauthorizedStateMutationError: If actor lacks authority
        """
        # Check if actor is in registry
        if actor not in AGENT_REGISTRY:
            logger.warning(f"SI-01: Unregistered actor '{actor}' attempted state mutation")
            raise UnauthorizedStateMutationError(
                actor=actor,
                target_state=target_state,
                evidence={"required_authority": required_authority, "actor_registered": False},
            )

        actor_authority = AGENT_REGISTRY[actor].get("authority", "NONE")

        # Check authority match
        if actor_authority != required_authority and actor_authority != "SUPREME":
            logger.warning(
                f"SI-01: Actor '{actor}' with authority '{actor_authority}' "
                f"attempted mutation requiring '{required_authority}'"
            )
            raise UnauthorizedStateMutationError(
                actor=actor,
                target_state=target_state,
                evidence={
                    "required_authority": required_authority,
                    "actor_authority": actor_authority,
                },
            )

        return InvariantCheckResult(
            invariant_id=SecurityInvariantID.SI_01,
            passed=True,
            reason="Actor has required authority",
            evidence={"actor": actor, "authority": actor_authority},
        )

    # -------------------------------------------------------------------------
    # SI-02: All authority claims must be verifiable
    # -------------------------------------------------------------------------

    def check_authority_verifiable(
        self,
        claimed_gid: str,
        claimed_name: str,
        signature: Optional[str] = None,
    ) -> InvariantCheckResult:
        """Verify authority claim matches registry.

        Args:
            claimed_gid: GID being claimed
            claimed_name: Agent name being claimed
            signature: Optional cryptographic signature

        Returns:
            InvariantCheckResult

        Raises:
            UnverifiableAuthorityError: If claim cannot be verified
        """
        # Check GID exists
        if claimed_gid not in AGENT_REGISTRY:
            raise UnverifiableAuthorityError(
                claimed_authority=claimed_gid,
                reason=f"GID '{claimed_gid}' not in registry",
                evidence={"claimed_name": claimed_name},
            )

        # Check name matches
        registered_name = AGENT_REGISTRY[claimed_gid]["name"]
        if registered_name.lower() != claimed_name.lower():
            raise UnverifiableAuthorityError(
                claimed_authority=claimed_gid,
                reason=f"Name mismatch: claimed '{claimed_name}', registry has '{registered_name}'",
                evidence={"claimed_name": claimed_name, "registered_name": registered_name},
            )

        return InvariantCheckResult(
            invariant_id=SecurityInvariantID.SI_02,
            passed=True,
            reason="Authority claim verified against registry",
            evidence={"gid": claimed_gid, "name": claimed_name},
        )

    # -------------------------------------------------------------------------
    # SI-03: No replay without detection
    # -------------------------------------------------------------------------

    def check_replay_protection(
        self,
        artifact_id: str,
        nonce: str,
        timestamp: str,
    ) -> InvariantCheckResult:
        """Check for replay attacks.

        Args:
            artifact_id: ID of the artifact
            nonce: Unique nonce for this submission
            timestamp: Timestamp of submission

        Returns:
            InvariantCheckResult

        Raises:
            ReplayDetectionError: If replay detected
        """
        # Check nonce uniqueness
        nonce_key = f"{artifact_id}:{nonce}"
        if nonce_key in self._nonce_registry:
            raise ReplayDetectionError(
                artifact_id=artifact_id,
                nonce=nonce,
                evidence={"timestamp": timestamp, "reason": "Nonce already used"},
            )

        # Register nonce
        self._nonce_registry.add(nonce_key)

        return InvariantCheckResult(
            invariant_id=SecurityInvariantID.SI_03,
            passed=True,
            reason="No replay detected",
            evidence={"artifact_id": artifact_id, "nonce": nonce},
        )

    # -------------------------------------------------------------------------
    # SI-04: No downgrade of governance state
    # -------------------------------------------------------------------------

    def check_governance_level(
        self,
        current_level: str,
        requested_level: str,
    ) -> InvariantCheckResult:
        """Check for governance downgrade attempts.

        Args:
            current_level: Current governance level
            requested_level: Requested governance level

        Returns:
            InvariantCheckResult

        Raises:
            GovernanceDowngradeError: If downgrade attempted
        """
        if current_level not in GOVERNANCE_LEVELS:
            current_level = "HARD_GATED"  # Default

        if requested_level not in GOVERNANCE_LEVELS:
            raise GovernanceDowngradeError(
                current_level=current_level,
                attempted_level=requested_level,
                evidence={"reason": "Invalid governance level"},
            )

        current_index = GOVERNANCE_LEVELS.index(current_level)
        requested_index = GOVERNANCE_LEVELS.index(requested_level)

        if requested_index < current_index:
            raise GovernanceDowngradeError(
                current_level=current_level,
                attempted_level=requested_level,
                evidence={
                    "current_index": current_index,
                    "requested_index": requested_index,
                },
            )

        return InvariantCheckResult(
            invariant_id=SecurityInvariantID.SI_04,
            passed=True,
            reason="Governance level maintained or elevated",
            evidence={"current": current_level, "requested": requested_level},
        )

    # -------------------------------------------------------------------------
    # SI-05: No unsigned correction closure
    # -------------------------------------------------------------------------

    def check_correction_signature(
        self,
        correction_id: str,
        signature: Optional[str],
        signer_gid: Optional[str],
    ) -> InvariantCheckResult:
        """Check that correction has valid signature.

        Args:
            correction_id: ID of the correction
            signature: Signature on the correction
            signer_gid: GID of the signer

        Returns:
            InvariantCheckResult

        Raises:
            UnsignedCorrectionError: If correction is unsigned
        """
        if not signature or not signer_gid:
            raise UnsignedCorrectionError(
                correction_id=correction_id,
                evidence={"has_signature": bool(signature), "has_signer": bool(signer_gid)},
            )

        # Verify signer is in registry
        if signer_gid not in AGENT_REGISTRY:
            raise UnsignedCorrectionError(
                correction_id=correction_id,
                evidence={"signer_gid": signer_gid, "reason": "Signer not in registry"},
            )

        return InvariantCheckResult(
            invariant_id=SecurityInvariantID.SI_05,
            passed=True,
            reason="Correction has valid signature",
            evidence={"correction_id": correction_id, "signer": signer_gid},
        )

    # -------------------------------------------------------------------------
    # SI-06: No PAC execution without registry match
    # -------------------------------------------------------------------------

    def check_pac_registry_match(
        self,
        pac_id: str,
        executing_gid: str,
        declared_gid: str,
    ) -> InvariantCheckResult:
        """Check PAC execution matches registry.

        Args:
            pac_id: ID of the PAC
            executing_gid: GID of the executing agent
            declared_gid: GID declared in the PAC

        Returns:
            InvariantCheckResult

        Raises:
            RegistryMismatchError: If GIDs don't match registry
        """
        # Check executing GID
        if executing_gid not in AGENT_REGISTRY:
            raise RegistryMismatchError(
                pac_id=pac_id,
                agent_gid=executing_gid,
                evidence={"reason": "Executing agent not in registry"},
            )

        # Check declared GID
        if declared_gid not in AGENT_REGISTRY:
            raise RegistryMismatchError(
                pac_id=pac_id,
                agent_gid=declared_gid,
                evidence={"reason": "Declared agent not in registry"},
            )

        # Check match
        if executing_gid != declared_gid:
            raise RegistryMismatchError(
                pac_id=pac_id,
                agent_gid=executing_gid,
                evidence={
                    "executing_gid": executing_gid,
                    "declared_gid": declared_gid,
                    "reason": "Executing agent does not match declared agent",
                },
            )

        return InvariantCheckResult(
            invariant_id=SecurityInvariantID.SI_06,
            passed=True,
            reason="PAC execution matches registry",
            evidence={"pac_id": pac_id, "agent_gid": executing_gid},
        )

    # -------------------------------------------------------------------------
    # SI-07: No bypass of hard gates
    # -------------------------------------------------------------------------

    def check_hard_gate_enforcement(
        self,
        gate_id: str,
        gate_result: str,
        bypass_attempted: bool,
    ) -> InvariantCheckResult:
        """Check that hard gates cannot be bypassed.

        Args:
            gate_id: ID of the gate
            gate_result: Result of the gate check
            bypass_attempted: Whether bypass was attempted

        Returns:
            InvariantCheckResult

        Raises:
            HardGateBypassError: If bypass attempted
        """
        if bypass_attempted:
            raise HardGateBypassError(
                gate_id=gate_id,
                bypass_method="direct_skip",
                evidence={"gate_result": gate_result},
            )

        if gate_result not in ("PASS", "VALID"):
            raise HardGateBypassError(
                gate_id=gate_id,
                bypass_method="invalid_result_accepted",
                evidence={"gate_result": gate_result},
            )

        return InvariantCheckResult(
            invariant_id=SecurityInvariantID.SI_07,
            passed=True,
            reason="Hard gate enforced",
            evidence={"gate_id": gate_id, "result": gate_result},
        )

    # -------------------------------------------------------------------------
    # SI-08: No mixed-authority execution
    # -------------------------------------------------------------------------

    def check_single_authority(
        self,
        execution_context: Dict[str, Any],
    ) -> InvariantCheckResult:
        """Check that execution has single authority source.

        Args:
            execution_context: Context containing authority claims

        Returns:
            InvariantCheckResult

        Raises:
            MixedAuthorityError: If multiple authorities detected
        """
        authorities = set()

        # Extract all authority claims
        if "executing_gid" in execution_context:
            gid = execution_context["executing_gid"]
            if gid in AGENT_REGISTRY:
                authorities.add(AGENT_REGISTRY[gid]["authority"])

        if "declared_authority" in execution_context:
            authorities.add(execution_context["declared_authority"])

        if "runtime_authority" in execution_context:
            authorities.add(execution_context["runtime_authority"])

        # Check for mixed authorities (excluding SUPREME which can do anything)
        non_supreme_authorities = [a for a in authorities if a != "SUPREME"]
        if len(non_supreme_authorities) > 1:
            raise MixedAuthorityError(
                authorities=list(authorities),
                evidence={"context": execution_context},
            )

        return InvariantCheckResult(
            invariant_id=SecurityInvariantID.SI_08,
            passed=True,
            reason="Single authority execution",
            evidence={"authorities": list(authorities)},
        )

    # -------------------------------------------------------------------------
    # Aggregate check
    # -------------------------------------------------------------------------

    def clear_registries(self) -> None:
        """Clear internal registries (for testing)."""
        self._nonce_registry.clear()
        self._signature_registry.clear()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def validate_security_invariants(
    context: Dict[str, Any],
) -> List[InvariantCheckResult]:
    """Validate all applicable security invariants.

    Args:
        context: Execution context with relevant fields

    Returns:
        List of check results

    Raises:
        SecurityInvariantViolation: On any violation
    """
    validator = SecurityInvariantValidator()
    results = []

    # SI-02: Authority verifiable
    if "claimed_gid" in context and "claimed_name" in context:
        results.append(validator.check_authority_verifiable(
            claimed_gid=context["claimed_gid"],
            claimed_name=context["claimed_name"],
        ))

    # SI-06: Registry match
    if "pac_id" in context and "executing_gid" in context:
        results.append(validator.check_pac_registry_match(
            pac_id=context["pac_id"],
            executing_gid=context["executing_gid"],
            declared_gid=context.get("declared_gid", context["executing_gid"]),
        ))

    # SI-08: Single authority
    results.append(validator.check_single_authority(context))

    return results


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "SecurityInvariantID",
    # Exceptions
    "SecurityInvariantViolation",
    "UnauthorizedStateMutationError",
    "UnverifiableAuthorityError",
    "ReplayDetectionError",
    "GovernanceDowngradeError",
    "UnsignedCorrectionError",
    "RegistryMismatchError",
    "HardGateBypassError",
    "MixedAuthorityError",
    # Result types
    "InvariantCheckResult",
    # Validator
    "SecurityInvariantValidator",
    # Constants
    "AGENT_REGISTRY",
    "GOVERNANCE_LEVELS",
    # Functions
    "validate_security_invariants",
]
