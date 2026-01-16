"""
Shard Policy Enforcer - Governance Enforcement for Execution Sharding
PAC-P750-SWARM-EXECUTION-SHARDING-DOCTRINE-AND-IMPLEMENTATION
TASK-03: Implement ShardPolicyEnforcer

Enforces the Core Law: Authority is singular. Execution may shard. Judgment MUST NOT shard.

Implements:
- Authority singularity enforcement
- Lateral communication blocking
- WRAP/BER emission prevention
- Invariant monitoring
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Callable
from pathlib import Path


class ViolationType(Enum):
    """Types of shard policy violations."""
    AUTHORITY_USURPATION = "AUTHORITY_USURPATION"
    LATERAL_COMMUNICATION = "LATERAL_COMMUNICATION"
    WRAP_EMISSION_ATTEMPT = "WRAP_EMISSION_ATTEMPT"
    BER_EMISSION_ATTEMPT = "BER_EMISSION_ATTEMPT"
    JUDGMENT_ATTEMPT = "JUDGMENT_ATTEMPT"
    RESOURCE_OVERFLOW = "RESOURCE_OVERFLOW"
    STATE_PERSISTENCE = "STATE_PERSISTENCE"
    SHARD_FORKING = "SHARD_FORKING"


class EnforcementAction(Enum):
    """Actions taken on violation."""
    BLOCK = "BLOCK"
    TERMINATE = "TERMINATE"
    SCRAM = "SCRAM"
    WARN = "WARN"


@dataclass
class PolicyViolation:
    """Record of a policy violation."""
    violation_id: str
    violation_type: ViolationType
    shard_id: str
    description: str
    action_taken: EnforcementAction
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "violation_type": self.violation_type.value,
            "shard_id": self.shard_id,
            "description": self.description,
            "action_taken": self.action_taken.value,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


@dataclass
class InvariantCheck:
    """Result of an invariant check."""
    invariant_id: str
    name: str
    passed: bool
    message: str
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "checked_at": self.checked_at.isoformat()
        }


# Prohibited operations for shards
PROHIBITED_OPERATIONS = {
    "emit_wrap": ViolationType.WRAP_EMISSION_ATTEMPT,
    "emit_ber": ViolationType.BER_EMISSION_ATTEMPT,
    "create_wrap": ViolationType.WRAP_EMISSION_ATTEMPT,
    "create_ber": ViolationType.BER_EMISSION_ATTEMPT,
    "render_judgment": ViolationType.JUDGMENT_ATTEMPT,
    "approve_pac": ViolationType.JUDGMENT_ATTEMPT,
    "reject_pac": ViolationType.JUDGMENT_ATTEMPT,
    "contact_shard": ViolationType.LATERAL_COMMUNICATION,
    "shard_to_shard": ViolationType.LATERAL_COMMUNICATION,
    "broadcast_to_shards": ViolationType.LATERAL_COMMUNICATION,
    "persist_state": ViolationType.STATE_PERSISTENCE,
    "save_state": ViolationType.STATE_PERSISTENCE,
    "fork_shard": ViolationType.SHARD_FORKING,
    "spawn_child_shard": ViolationType.SHARD_FORKING,
}

# Enforcement actions by violation type
ENFORCEMENT_ACTIONS = {
    ViolationType.AUTHORITY_USURPATION: EnforcementAction.SCRAM,
    ViolationType.LATERAL_COMMUNICATION: EnforcementAction.TERMINATE,
    ViolationType.WRAP_EMISSION_ATTEMPT: EnforcementAction.SCRAM,
    ViolationType.BER_EMISSION_ATTEMPT: EnforcementAction.SCRAM,
    ViolationType.JUDGMENT_ATTEMPT: EnforcementAction.SCRAM,
    ViolationType.RESOURCE_OVERFLOW: EnforcementAction.TERMINATE,
    ViolationType.STATE_PERSISTENCE: EnforcementAction.BLOCK,
    ViolationType.SHARD_FORKING: EnforcementAction.TERMINATE,
}


class ShardPolicyEnforcer:
    """
    Enforces shard execution policies per the Execution Sharding Doctrine.
    
    Core Law: Authority is singular. Execution may shard. Judgment MUST NOT shard.
    
    Invariants Enforced:
    - INV-SHARD-001: Authority singularity
    - INV-SHARD-002: Upward-only recomposition
    - INV-SHARD-003: No lateral consensus
    - INV-SHARD-004: No Shard WRAP/BER
    - INV-SHARD-005: Mandatory termination
    """

    SINGULAR_AUTHORITY = "BENSON (GID-00)"

    def __init__(self, storage_path: Optional[Path] = None):
        self._violations: list[PolicyViolation] = []
        self._invariant_checks: list[InvariantCheck] = []
        self._scram_active = False
        self._scram_reason: Optional[str] = None
        self._blocked_shards: set[str] = set()
        self._termination_callbacks: list[Callable[[str, str], None]] = []
        self.storage_path = storage_path or Path("data/shard_policy.json")

    def _generate_violation_id(self) -> str:
        """Generate unique violation ID."""
        import secrets
        return f"VIOL-{secrets.token_hex(6).upper()}"

    def check_operation_allowed(
        self,
        shard_id: str,
        operation: str,
        context: Optional[dict[str, Any]] = None
    ) -> tuple[bool, Optional[PolicyViolation]]:
        """
        Check if an operation is allowed for a shard.
        
        Returns (allowed, violation_if_blocked).
        """
        # Check if shard is already blocked
        if shard_id in self._blocked_shards:
            return False, None

        # Check SCRAM state
        if self._scram_active:
            return False, None

        # Check against prohibited operations
        operation_lower = operation.lower().replace("-", "_").replace(" ", "_")
        
        for prohibited, violation_type in PROHIBITED_OPERATIONS.items():
            if prohibited in operation_lower:
                violation = self._record_violation(
                    shard_id=shard_id,
                    violation_type=violation_type,
                    description=f"Prohibited operation attempted: {operation}",
                    details=context or {}
                )
                return False, violation

        return True, None

    def _record_violation(
        self,
        shard_id: str,
        violation_type: ViolationType,
        description: str,
        details: dict[str, Any]
    ) -> PolicyViolation:
        """Record a policy violation and take enforcement action."""
        action = ENFORCEMENT_ACTIONS.get(violation_type, EnforcementAction.BLOCK)

        violation = PolicyViolation(
            violation_id=self._generate_violation_id(),
            violation_type=violation_type,
            shard_id=shard_id,
            description=description,
            action_taken=action,
            details=details
        )

        self._violations.append(violation)

        # Execute enforcement action
        if action == EnforcementAction.SCRAM:
            self._trigger_scram(f"Violation: {violation_type.value} by {shard_id}")
        elif action == EnforcementAction.TERMINATE:
            self._request_termination(shard_id, description)
        elif action == EnforcementAction.BLOCK:
            self._blocked_shards.add(shard_id)

        return violation

    def _trigger_scram(self, reason: str) -> None:
        """Trigger SCRAM - halt all shard execution."""
        self._scram_active = True
        self._scram_reason = reason

        # Request termination of all shards
        for callback in self._termination_callbacks:
            try:
                callback("ALL", reason)
            except Exception:
                pass

    def _request_termination(self, shard_id: str, reason: str) -> None:
        """Request termination of a specific shard."""
        for callback in self._termination_callbacks:
            try:
                callback(shard_id, reason)
            except Exception:
                pass

    def register_termination_callback(
        self,
        callback: Callable[[str, str], None]
    ) -> None:
        """Register callback for shard termination requests."""
        self._termination_callbacks.append(callback)

    def check_invariant_001_authority_singularity(
        self,
        claimed_authority: str
    ) -> InvariantCheck:
        """
        INV-SHARD-001: Only BENSON may render judgment.
        """
        passed = claimed_authority == self.SINGULAR_AUTHORITY
        
        check = InvariantCheck(
            invariant_id="INV-SHARD-001",
            name="Authority Singularity",
            passed=passed,
            message="Authority verified" if passed else f"Invalid authority: {claimed_authority}"
        )
        
        self._invariant_checks.append(check)
        return check

    def check_invariant_002_upward_only(
        self,
        source_shard_id: str,
        destination: str
    ) -> InvariantCheck:
        """
        INV-SHARD-002: Shard results flow only upward to ShardManager.
        """
        # Valid destinations are ShardManager or authority
        valid_destinations = {"SHARD_MANAGER", "BENSON", self.SINGULAR_AUTHORITY}
        passed = destination.upper() in valid_destinations or destination.startswith("SHARD_MANAGER")

        check = InvariantCheck(
            invariant_id="INV-SHARD-002",
            name="Upward-Only Recomposition",
            passed=passed,
            message="Valid destination" if passed else f"Invalid destination: {destination}"
        )

        self._invariant_checks.append(check)
        
        if not passed:
            self._record_violation(
                shard_id=source_shard_id,
                violation_type=ViolationType.LATERAL_COMMUNICATION,
                description=f"Attempted to send result to invalid destination: {destination}",
                details={"destination": destination}
            )

        return check

    def check_invariant_003_no_lateral_consensus(
        self,
        shard_id: str,
        target_shard_id: Optional[str]
    ) -> InvariantCheck:
        """
        INV-SHARD-003: Shards must not communicate with each other.
        """
        passed = target_shard_id is None or not target_shard_id.startswith("SHARD-")

        check = InvariantCheck(
            invariant_id="INV-SHARD-003",
            name="No Lateral Consensus",
            passed=passed,
            message="No lateral communication" if passed else f"Lateral communication attempted: {target_shard_id}"
        )

        self._invariant_checks.append(check)

        if not passed:
            self._record_violation(
                shard_id=shard_id,
                violation_type=ViolationType.LATERAL_COMMUNICATION,
                description=f"Attempted lateral communication with {target_shard_id}",
                details={"target": target_shard_id}
            )

        return check

    def check_invariant_004_no_governance_emission(
        self,
        shard_id: str,
        artifact_type: str
    ) -> InvariantCheck:
        """
        INV-SHARD-004: Shards must not emit WRAP or BER.
        """
        artifact_upper = artifact_type.upper()
        passed = artifact_upper not in ("WRAP", "BER")

        check = InvariantCheck(
            invariant_id="INV-SHARD-004",
            name="No Shard WRAP/BER",
            passed=passed,
            message="No governance emission" if passed else f"Attempted {artifact_type} emission"
        )

        self._invariant_checks.append(check)

        if not passed:
            violation_type = (
                ViolationType.WRAP_EMISSION_ATTEMPT if artifact_upper == "WRAP"
                else ViolationType.BER_EMISSION_ATTEMPT
            )
            self._record_violation(
                shard_id=shard_id,
                violation_type=violation_type,
                description=f"Attempted to emit {artifact_type}",
                details={"artifact_type": artifact_type}
            )

        return check

    def check_invariant_005_resource_bounds(
        self,
        shard_id: str,
        execution_time_ms: float,
        max_time_ms: float
    ) -> InvariantCheck:
        """
        INV-SHARD-005: Shards must terminate within bounds.
        """
        passed = execution_time_ms <= max_time_ms

        check = InvariantCheck(
            invariant_id="INV-SHARD-005",
            name="Mandatory Termination",
            passed=passed,
            message="Within bounds" if passed else f"Exceeded time: {execution_time_ms}ms > {max_time_ms}ms"
        )

        self._invariant_checks.append(check)

        if not passed:
            self._record_violation(
                shard_id=shard_id,
                violation_type=ViolationType.RESOURCE_OVERFLOW,
                description=f"Execution time {execution_time_ms}ms exceeded limit {max_time_ms}ms",
                details={"actual_ms": execution_time_ms, "limit_ms": max_time_ms}
            )

        return check

    def run_all_invariant_checks(
        self,
        shard_id: str,
        context: dict[str, Any]
    ) -> list[InvariantCheck]:
        """Run all invariant checks for a shard."""
        checks = []

        # Check authority if claimed
        if "claimed_authority" in context:
            checks.append(self.check_invariant_001_authority_singularity(
                context["claimed_authority"]
            ))

        # Check destination if provided
        if "destination" in context:
            checks.append(self.check_invariant_002_upward_only(
                shard_id, context["destination"]
            ))

        # Check target shard if provided
        if "target_shard" in context:
            checks.append(self.check_invariant_003_no_lateral_consensus(
                shard_id, context["target_shard"]
            ))

        # Check artifact emission if provided
        if "artifact_type" in context:
            checks.append(self.check_invariant_004_no_governance_emission(
                shard_id, context["artifact_type"]
            ))

        # Check resource bounds if provided
        if "execution_time_ms" in context and "max_time_ms" in context:
            checks.append(self.check_invariant_005_resource_bounds(
                shard_id,
                context["execution_time_ms"],
                context["max_time_ms"]
            ))

        return checks

    def reset_scram(self, authorization: str) -> bool:
        """Reset SCRAM state (requires JEFFREY authorization)."""
        if authorization != "JEFFREY_AUTHORIZATION":
            return False
        
        self._scram_active = False
        self._scram_reason = None
        self._blocked_shards.clear()
        return True

    def get_scram_status(self) -> dict[str, Any]:
        """Get SCRAM status."""
        return {
            "active": self._scram_active,
            "reason": self._scram_reason,
            "blocked_shards": list(self._blocked_shards)
        }

    def get_violation_summary(self) -> dict[str, Any]:
        """Get violation summary."""
        return {
            "total_violations": len(self._violations),
            "by_type": {
                vt.value: sum(1 for v in self._violations if v.violation_type == vt)
                for vt in ViolationType
            },
            "scram_triggered": self._scram_active,
            "blocked_shards": len(self._blocked_shards)
        }

    def export(self) -> dict[str, Any]:
        """Export enforcer state."""
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "scram_status": self.get_scram_status(),
            "violations": [v.to_dict() for v in self._violations],
            "invariant_checks": [c.to_dict() for c in self._invariant_checks[-100:]],
            "summary": self.get_violation_summary()
        }

    def save(self) -> None:
        """Save enforcer state."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.export(), f, indent=2)


# Singleton instance
_policy_enforcer: Optional[ShardPolicyEnforcer] = None


def get_shard_policy_enforcer() -> ShardPolicyEnforcer:
    """Get global shard policy enforcer instance."""
    global _policy_enforcer
    if _policy_enforcer is None:
        _policy_enforcer = ShardPolicyEnforcer()
    return _policy_enforcer
