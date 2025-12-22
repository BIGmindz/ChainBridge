"""Runtime Threat Guard Module.

Defends against runtime escape attempts:
- Unauthorized agent decision emission
- Proof modification attempts
- Settlement instruction injection

DOCTRINE: Runtime cannot escalate privileges or mutate proofs.

Author: Sam (GID-06) — Security & Threat Engineer
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Set, Pattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Security Exceptions
# ---------------------------------------------------------------------------


class UnauthorizedAgentDecisionError(Exception):
    """Raised when runtime attempts unauthorized agent decision."""

    def __init__(
        self,
        runtime_id: str,
        attempted_agent_id: str,
        reason: str,
    ):
        self.runtime_id = runtime_id
        self.attempted_agent_id = attempted_agent_id
        self.reason = reason
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(
            f"Unauthorized agent decision blocked: runtime {runtime_id} "
            f"attempted to emit decision as {attempted_agent_id}: {reason}"
        )


class ProofMutationAttemptError(Exception):
    """Raised when runtime attempts to modify proof."""

    def __init__(
        self,
        runtime_id: str,
        proof_id: str,
        mutation_type: str,
    ):
        self.runtime_id = runtime_id
        self.proof_id = proof_id
        self.mutation_type = mutation_type
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(
            f"Proof mutation blocked: runtime {runtime_id} attempted "
            f"{mutation_type} on proof {proof_id}"
        )


class SettlementInjectionError(Exception):
    """Raised when runtime attempts to inject settlement instruction."""

    def __init__(
        self,
        runtime_id: str,
        target_pdo_id: str,
        injection_type: str,
    ):
        self.runtime_id = runtime_id
        self.target_pdo_id = target_pdo_id
        self.injection_type = injection_type
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(
            f"Settlement injection blocked: runtime {runtime_id} attempted "
            f"{injection_type} on PDO {target_pdo_id}"
        )


class RuntimePrivilegeEscalationError(Exception):
    """Raised when runtime attempts privilege escalation."""

    def __init__(
        self,
        runtime_id: str,
        attempted_role: str,
        current_role: str,
    ):
        self.runtime_id = runtime_id
        self.attempted_role = attempted_role
        self.current_role = current_role
        self.detected_at = datetime.now(timezone.utc).isoformat()
        super().__init__(
            f"Privilege escalation blocked: runtime {runtime_id} "
            f"attempted {attempted_role} from {current_role}"
        )


# ---------------------------------------------------------------------------
# Runtime Threat Types
# ---------------------------------------------------------------------------


class RuntimeThreatType(str, Enum):
    """Types of runtime threats."""

    UNAUTHORIZED_DECISION = "UNAUTHORIZED_DECISION"
    PROOF_MUTATION = "PROOF_MUTATION"
    SETTLEMENT_INJECTION = "SETTLEMENT_INJECTION"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    BOUNDARY_VIOLATION = "BOUNDARY_VIOLATION"
    RESOURCE_ABUSE = "RESOURCE_ABUSE"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    CODE_INJECTION = "CODE_INJECTION"


class MutationType(str, Enum):
    """Types of proof mutation attempts."""

    CONTENT_MODIFICATION = "CONTENT_MODIFICATION"
    HASH_REPLACEMENT = "HASH_REPLACEMENT"
    SIGNATURE_FORGE = "SIGNATURE_FORGE"
    LINEAGE_REWRITE = "LINEAGE_REWRITE"
    TIMESTAMP_ALTER = "TIMESTAMP_ALTER"


class InjectionType(str, Enum):
    """Types of settlement injection attempts."""

    FAKE_SETTLEMENT = "FAKE_SETTLEMENT"
    AMOUNT_OVERRIDE = "AMOUNT_OVERRIDE"
    DESTINATION_REDIRECT = "DESTINATION_REDIRECT"
    PREMATURE_TRIGGER = "PREMATURE_TRIGGER"
    SIGNATURE_BYPASS = "SIGNATURE_BYPASS"


@dataclass(frozen=True)
class ThreatDetectionResult:
    """Result from runtime threat detection."""

    blocked: bool
    threat_type: Optional[RuntimeThreatType]
    runtime_id: str
    reason: str
    evidence: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_audit_log(self) -> dict:
        """Convert to audit log format."""
        return {
            "event": "runtime_threat_detection",
            "blocked": self.blocked,
            "threat_type": self.threat_type.value if self.threat_type else None,
            "runtime_id": self.runtime_id,
            "reason": self.reason,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Runtime Threat Guard
# ---------------------------------------------------------------------------


class RuntimeThreatGuard:
    """Guards against runtime escape and escalation attempts.

    SECURITY INVARIANTS:
    - Runtime cannot emit decisions for unauthorized agents
    - Runtime cannot modify existing proofs
    - Runtime cannot inject settlement instructions
    - All violations are observable and blocked

    Usage:
        guard = RuntimeThreatGuard()
        guard.validate_agent_decision(runtime_id, decision_data)
        guard.validate_proof_access(runtime_id, proof_data, access_type)
        guard.validate_settlement_request(runtime_id, settlement_data)
    """

    # Patterns that indicate injection attempts
    INJECTION_PATTERNS: list[Pattern] = [
        re.compile(r"__.*__"),  # Python dunder methods
        re.compile(r"eval\s*\("),  # eval() calls
        re.compile(r"exec\s*\("),  # exec() calls
        re.compile(r"import\s+"),  # import statements
        re.compile(r"subprocess"),  # subprocess access
        re.compile(r"os\.system"),  # os.system calls
        re.compile(r"shell\s*=\s*True"),  # shell injection
    ]

    # Privileged roles that runtime cannot assume
    PRIVILEGED_ROLES: frozenset[str] = frozenset([
        "SYSTEM",
        "ADMIN",
        "CRO",
        "SETTLEMENT_ENGINE",
        "PROOF_AUTHORITY",
    ])

    def __init__(self):
        """Initialize runtime threat guard."""
        # Runtime ID -> authorized agents
        self._runtime_authorizations: dict[str, Set[str]] = {}
        # Immutable proof hashes (cannot be modified)
        self._immutable_proofs: Set[str] = set()
        # Runtime ID -> current role
        self._runtime_roles: dict[str, str] = {}
        # Runtime ID -> threat count
        self._threat_counters: dict[str, int] = {}
        # Threat threshold for automatic suspension
        self._threat_threshold: int = 3

    def register_runtime(
        self,
        runtime_id: str,
        authorized_agents: list[str],
        role: str = "RUNTIME",
    ) -> None:
        """Register a runtime with its authorizations.

        Args:
            runtime_id: Unique runtime identifier
            authorized_agents: List of agents this runtime can act for
            role: Runtime's role
        """
        self._runtime_authorizations[runtime_id] = set(authorized_agents)
        self._runtime_roles[runtime_id] = role
        self._threat_counters[runtime_id] = 0

    def validate_agent_decision(
        self,
        runtime_id: str,
        decision_data: dict[str, Any],
    ) -> ThreatDetectionResult:
        """Validate runtime's agent decision emission.

        Args:
            runtime_id: ID of runtime emitting decision
            decision_data: Decision being emitted

        Returns:
            ThreatDetectionResult

        Raises:
            UnauthorizedAgentDecisionError: If not authorized
        """
        agent_id = decision_data.get("agent_id", "UNKNOWN")

        # Check 1: Runtime is registered?
        if runtime_id not in self._runtime_authorizations:
            result = ThreatDetectionResult(
                blocked=True,
                threat_type=RuntimeThreatType.UNAUTHORIZED_DECISION,
                runtime_id=runtime_id,
                reason="Unknown runtime",
                evidence={"agent_id": agent_id},
            )
            self._log_threat(result)
            raise UnauthorizedAgentDecisionError(
                runtime_id,
                agent_id,
                "Runtime not registered",
            )

        # Check 2: Runtime authorized for this agent?
        authorized = self._runtime_authorizations[runtime_id]
        if agent_id not in authorized:
            result = ThreatDetectionResult(
                blocked=True,
                threat_type=RuntimeThreatType.UNAUTHORIZED_DECISION,
                runtime_id=runtime_id,
                reason="Not authorized for agent",
                evidence={
                    "agent_id": agent_id,
                    "authorized_agents": list(authorized),
                },
            )
            self._log_threat(result)
            self._increment_threat_counter(runtime_id)
            raise UnauthorizedAgentDecisionError(
                runtime_id,
                agent_id,
                "Runtime not authorized for this agent",
            )

        # Check 3: Decision content has no injection?
        injection_result = self._check_code_injection(
            runtime_id, json.dumps(decision_data)
        )
        if injection_result.blocked:
            self._log_threat(injection_result)
            self._increment_threat_counter(runtime_id)
            raise UnauthorizedAgentDecisionError(
                runtime_id,
                agent_id,
                "Injection attempt detected",
            )

        return ThreatDetectionResult(
            blocked=False,
            threat_type=None,
            runtime_id=runtime_id,
            reason="Decision authorized",
        )

    def validate_proof_access(
        self,
        runtime_id: str,
        proof_id: str,
        access_type: str,  # READ, WRITE, DELETE
    ) -> ThreatDetectionResult:
        """Validate runtime's proof access request.

        Args:
            runtime_id: ID of runtime accessing proof
            proof_id: ID of proof being accessed
            access_type: Type of access requested

        Returns:
            ThreatDetectionResult

        Raises:
            ProofMutationAttemptError: If write/delete attempted
        """
        # Proofs are read-only after creation
        if access_type in ("WRITE", "DELETE", "MODIFY"):
            mutation_type = MutationType.CONTENT_MODIFICATION.value

            if access_type == "DELETE":
                mutation_type = "DELETE"

            result = ThreatDetectionResult(
                blocked=True,
                threat_type=RuntimeThreatType.PROOF_MUTATION,
                runtime_id=runtime_id,
                reason=f"Proof {access_type} blocked",
                evidence={
                    "proof_id": proof_id,
                    "access_type": access_type,
                },
            )
            self._log_threat(result)
            self._increment_threat_counter(runtime_id)
            raise ProofMutationAttemptError(
                runtime_id,
                proof_id,
                mutation_type,
            )

        return ThreatDetectionResult(
            blocked=False,
            threat_type=None,
            runtime_id=runtime_id,
            reason="Read access allowed",
        )

    def validate_proof_immutability(
        self,
        runtime_id: str,
        proof_data: dict[str, Any],
        original_hash: str,
    ) -> ThreatDetectionResult:
        """Validate proof has not been mutated.

        Args:
            runtime_id: ID of runtime handling proof
            proof_data: Current proof data
            original_hash: Hash when proof was created

        Returns:
            ThreatDetectionResult

        Raises:
            ProofMutationAttemptError: If hash mismatch detected
        """
        proof_id = proof_data.get("proof_id", "UNKNOWN")
        current_hash = self._compute_proof_hash(proof_data)

        if current_hash != original_hash:
            result = ThreatDetectionResult(
                blocked=True,
                threat_type=RuntimeThreatType.PROOF_MUTATION,
                runtime_id=runtime_id,
                reason="Proof hash mismatch",
                evidence={
                    "proof_id": proof_id,
                    "original_hash": original_hash[:16] + "...",
                    "current_hash": current_hash[:16] + "...",
                },
            )
            self._log_threat(result)
            self._increment_threat_counter(runtime_id)
            raise ProofMutationAttemptError(
                runtime_id,
                proof_id,
                MutationType.CONTENT_MODIFICATION.value,
            )

        return ThreatDetectionResult(
            blocked=False,
            threat_type=None,
            runtime_id=runtime_id,
            reason="Proof integrity verified",
        )

    def validate_settlement_request(
        self,
        runtime_id: str,
        settlement_data: dict[str, Any],
    ) -> ThreatDetectionResult:
        """Validate runtime's settlement request.

        Runtimes CANNOT directly issue settlements.

        Args:
            runtime_id: ID of runtime issuing request
            settlement_data: Settlement request data

        Returns:
            ThreatDetectionResult

        Raises:
            SettlementInjectionError: Always (runtimes cannot settle)
        """
        pdo_id = settlement_data.get("pdo_id", "UNKNOWN")
        runtime_role = self._runtime_roles.get(runtime_id, "RUNTIME")

        # Only SETTLEMENT_ENGINE can issue settlements
        if runtime_role != "SETTLEMENT_ENGINE":
            injection_type = InjectionType.FAKE_SETTLEMENT.value

            # Detect specific injection patterns
            if "amount" in settlement_data:
                if settlement_data.get("_override_amount"):
                    injection_type = InjectionType.AMOUNT_OVERRIDE.value
            if "destination" in settlement_data:
                if settlement_data.get("_redirect_to"):
                    injection_type = InjectionType.DESTINATION_REDIRECT.value

            result = ThreatDetectionResult(
                blocked=True,
                threat_type=RuntimeThreatType.SETTLEMENT_INJECTION,
                runtime_id=runtime_id,
                reason="Runtime cannot issue settlements",
                evidence={
                    "pdo_id": pdo_id,
                    "runtime_role": runtime_role,
                    "injection_type": injection_type,
                },
            )
            self._log_threat(result)
            self._increment_threat_counter(runtime_id)
            raise SettlementInjectionError(
                runtime_id,
                pdo_id,
                injection_type,
            )

        return ThreatDetectionResult(
            blocked=False,
            threat_type=None,
            runtime_id=runtime_id,
            reason="Settlement engine authorized",
        )

    def validate_role_change(
        self,
        runtime_id: str,
        requested_role: str,
    ) -> ThreatDetectionResult:
        """Validate runtime role change request.

        Args:
            runtime_id: ID of runtime requesting change
            requested_role: Role being requested

        Returns:
            ThreatDetectionResult

        Raises:
            RuntimePrivilegeEscalationError: If escalation detected
        """
        current_role = self._runtime_roles.get(runtime_id, "RUNTIME")

        # Cannot escalate to privileged roles
        if requested_role in self.PRIVILEGED_ROLES:
            result = ThreatDetectionResult(
                blocked=True,
                threat_type=RuntimeThreatType.PRIVILEGE_ESCALATION,
                runtime_id=runtime_id,
                reason="Cannot escalate to privileged role",
                evidence={
                    "current_role": current_role,
                    "requested_role": requested_role,
                },
            )
            self._log_threat(result)
            self._increment_threat_counter(runtime_id)
            raise RuntimePrivilegeEscalationError(
                runtime_id,
                requested_role,
                current_role,
            )

        return ThreatDetectionResult(
            blocked=False,
            threat_type=None,
            runtime_id=runtime_id,
            reason="Role change allowed",
        )

    def detect_boundary_violation(
        self,
        runtime_id: str,
        resource_path: str,
    ) -> ThreatDetectionResult:
        """Detect runtime attempting to access restricted resources.

        Args:
            runtime_id: ID of runtime
            resource_path: Path being accessed

        Returns:
            ThreatDetectionResult
        """
        # Check for path traversal
        if ".." in resource_path or resource_path.startswith("/"):
            result = ThreatDetectionResult(
                blocked=True,
                threat_type=RuntimeThreatType.BOUNDARY_VIOLATION,
                runtime_id=runtime_id,
                reason="Path traversal detected",
                evidence={"resource_path": resource_path},
            )
            self._log_threat(result)
            self._increment_threat_counter(runtime_id)
            return result

        # Check for sensitive paths
        sensitive_patterns = [
            r"/etc/",
            r"/var/",
            r"/root/",
            r"\.env",
            r"credentials",
            r"secrets",
            r"private_key",
        ]

        for pattern in sensitive_patterns:
            if re.search(pattern, resource_path, re.IGNORECASE):
                result = ThreatDetectionResult(
                    blocked=True,
                    threat_type=RuntimeThreatType.BOUNDARY_VIOLATION,
                    runtime_id=runtime_id,
                    reason="Sensitive path access blocked",
                    evidence={
                        "resource_path": resource_path,
                        "matched_pattern": pattern,
                    },
                )
                self._log_threat(result)
                self._increment_threat_counter(runtime_id)
                return result

        return ThreatDetectionResult(
            blocked=False,
            threat_type=None,
            runtime_id=runtime_id,
            reason="Access allowed",
        )

    # ---------------------------------------------------------------------------
    # Internal Methods
    # ---------------------------------------------------------------------------

    def _check_code_injection(
        self, runtime_id: str, content: str
    ) -> ThreatDetectionResult:
        """Check content for code injection patterns."""
        for pattern in self.INJECTION_PATTERNS:
            if pattern.search(content):
                return ThreatDetectionResult(
                    blocked=True,
                    threat_type=RuntimeThreatType.CODE_INJECTION,
                    runtime_id=runtime_id,
                    reason="Injection pattern detected",
                    evidence={"pattern": pattern.pattern},
                )

        return ThreatDetectionResult(
            blocked=False,
            threat_type=None,
            runtime_id=runtime_id,
            reason="No injection detected",
        )

    def _compute_proof_hash(self, proof_data: dict[str, Any]) -> str:
        """Compute deterministic hash of proof."""
        hashable = {
            k: v for k, v in proof_data.items()
            if k not in ("signature", "verified_at")
        }
        content = json.dumps(hashable, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(content.encode()).hexdigest()

    def _increment_threat_counter(self, runtime_id: str) -> None:
        """Increment threat counter and check threshold."""
        self._threat_counters[runtime_id] = (
            self._threat_counters.get(runtime_id, 0) + 1
        )

        if self._threat_counters[runtime_id] >= self._threat_threshold:
            logger.critical(
                "RUNTIME_SUSPENDED: %s exceeded threat threshold (%d)",
                runtime_id,
                self._threat_threshold,
            )
            # Remove authorizations (effective suspension)
            self._runtime_authorizations[runtime_id] = set()

    def _log_threat(self, result: ThreatDetectionResult) -> None:
        """Log runtime threat for audit."""
        logger.error(
            "RUNTIME_THREAT: %s runtime_id=%s reason=%s",
            result.threat_type.value if result.threat_type else "UNKNOWN",
            result.runtime_id,
            result.reason,
        )
        logger.error("Threat evidence: %s", json.dumps(result.to_audit_log()))

    def is_runtime_suspended(self, runtime_id: str) -> bool:
        """Check if runtime is suspended due to threats."""
        return (
            self._threat_counters.get(runtime_id, 0) >= self._threat_threshold
        )

    def get_threat_count(self, runtime_id: str) -> int:
        """Get threat count for runtime."""
        return self._threat_counters.get(runtime_id, 0)

    def clear_state(self) -> None:
        """Clear all state (for testing only)."""
        self._runtime_authorizations.clear()
        self._immutable_proofs.clear()
        self._runtime_roles.clear()
        self._threat_counters.clear()
