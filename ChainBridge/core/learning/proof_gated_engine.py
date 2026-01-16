"""
Proof-Gated Learning Engine Primitive
PAC-P748-ARCH-GOVERNANCE-DEFENSIBILITY-LOCK-AND-EXECUTION
TASK-12: Implement ProofGatedLearning primitive

Implements:
- Learning permission gates and verification
- Learning delta audit trail
- Reward artifact generation
- Rollback capability for learning operations
"""

from __future__ import annotations

import hashlib
import json
import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pathlib import Path


class GateType(Enum):
    """Types of learning permission gates."""
    ARCHITECTURAL_GATE = "ARCHITECTURAL_GATE"
    OPERATIONAL_GATE = "OPERATIONAL_GATE"
    TACTICAL_GATE = "TACTICAL_GATE"


class LearningType(Enum):
    """Types of learning operations."""
    PROHIBITED = "PROHIBITED"
    GATED_ARCHITECTURAL = "GATED_ARCHITECTURAL"
    GATED_OPERATIONAL = "GATED_OPERATIONAL"
    BOUNDED_TACTICAL = "BOUNDED_TACTICAL"


class RewardType(Enum):
    """Types of learning rewards."""
    PERFORMANCE = "PERFORMANCE"
    COMPLIANCE = "COMPLIANCE"
    INNOVATION = "INNOVATION"


@dataclass
class LearningPermission:
    """Proof of permission for a learning operation."""
    permission_id: str
    gate_type: GateType
    agent_id: str
    learning_scope: str
    granted_by: str
    granted_at: datetime
    expires_at: Optional[datetime]
    pac_reference: Optional[str]
    bounds: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "permission_id": self.permission_id,
            "gate_type": self.gate_type.value,
            "agent_id": self.agent_id,
            "learning_scope": self.learning_scope,
            "granted_by": self.granted_by,
            "granted_at": self.granted_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "pac_reference": self.pac_reference,
            "bounds": self.bounds
        }

    def is_valid(self) -> bool:
        """Check if permission is still valid."""
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


@dataclass
class LearningCheckpoint:
    """Checkpoint of agent state before learning."""
    checkpoint_id: str
    agent_id: str
    state_hash: str
    state_snapshot: dict[str, Any]
    created_at: datetime
    learning_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "agent_id": self.agent_id,
            "state_hash": self.state_hash,
            "created_at": self.created_at.isoformat(),
            "learning_id": self.learning_id
        }


@dataclass
class LearningDelta:
    """Record of a learning operation."""
    learning_id: str
    agent_id: str
    gate_type: GateType
    permission_proof: str
    before_state_hash: str
    after_state_hash: str
    delta_description: str
    timestamp: datetime
    checkpoint_id: str
    reversible: bool = True
    rolled_back: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_id": self.learning_id,
            "agent_id": self.agent_id,
            "gate_type": self.gate_type.value,
            "permission_proof": self.permission_proof,
            "before_state_hash": self.before_state_hash,
            "after_state_hash": self.after_state_hash,
            "delta_description": self.delta_description,
            "timestamp": self.timestamp.isoformat(),
            "checkpoint_id": self.checkpoint_id,
            "reversible": self.reversible,
            "rolled_back": self.rolled_back,
            "metadata": self.metadata
        }


@dataclass
class RewardArtifact:
    """Record of a learning reward."""
    reward_id: str
    recipient_agent: str
    issuer: str
    reward_type: RewardType
    reward_value: float
    justification: str
    linked_learning_id: Optional[str]
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "reward_id": self.reward_id,
            "recipient_agent": self.recipient_agent,
            "issuer": self.issuer,
            "reward_type": self.reward_type.value,
            "reward_value": self.reward_value,
            "justification": self.justification,
            "linked_learning_id": self.linked_learning_id,
            "timestamp": self.timestamp.isoformat()
        }


# Prohibited learning patterns
PROHIBITED_PATTERNS = [
    "modify_governance_invariant",
    "bypass_safety_check",
    "self_grant_permission",
    "hide_learning_artifact",
    "modify_own_authority",
    "delete_audit_trail"
]


class ProofGatedLearningEngine:
    """
    Engine for managing proof-gated learning operations.
    
    Enforces:
    - All learning requires explicit permission proof
    - Learning deltas are auditable
    - Rewards generate proof artifacts
    - Rollback is always available
    """

    GATE_APPROVERS = {
        GateType.ARCHITECTURAL_GATE: "JEFFREY (Architect)",
        GateType.OPERATIONAL_GATE: "BENSON (GID-00)",
        GateType.TACTICAL_GATE: "SELF_ATTESTATION"
    }

    REWARD_ISSUERS = {
        RewardType.PERFORMANCE: ["BENSON (GID-00)"],
        RewardType.COMPLIANCE: ["BENSON (GID-00)"],
        RewardType.INNOVATION: ["JEFFREY (Architect)"]
    }

    def __init__(self, storage_path: Optional[Path] = None):
        self._permissions: dict[str, LearningPermission] = {}
        self._checkpoints: dict[str, LearningCheckpoint] = {}
        self._deltas: list[LearningDelta] = []
        self._rewards: list[RewardArtifact] = []
        self._agent_states: dict[str, dict[str, Any]] = {}
        self.storage_path = storage_path or Path("data/learning_engine.json")

    def _compute_hash(self, data: Any) -> str:
        """Compute SHA3-256 hash."""
        serialized = json.dumps(data, sort_keys=True, default=str).encode()
        return f"sha3-256:{hashlib.sha3_256(serialized).hexdigest()}"

    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID."""
        ts = datetime.now(timezone.utc).isoformat()
        hash_val = hashlib.sha256(ts.encode()).hexdigest()[:12]
        return f"{prefix}-{hash_val.upper()}"

    def grant_permission(
        self,
        agent_id: str,
        gate_type: GateType,
        learning_scope: str,
        granted_by: str,
        pac_reference: Optional[str] = None,
        bounds: Optional[dict[str, Any]] = None,
        validity_hours: Optional[int] = None
    ) -> LearningPermission:
        """Grant learning permission to an agent."""
        # Validate approver
        required_approver = self.GATE_APPROVERS[gate_type]
        if required_approver != "SELF_ATTESTATION" and granted_by != required_approver:
            raise PermissionError(
                f"Gate type {gate_type.value} requires approval from {required_approver}"
            )

        permission = LearningPermission(
            permission_id=self._generate_id("PERM"),
            gate_type=gate_type,
            agent_id=agent_id,
            learning_scope=learning_scope,
            granted_by=granted_by,
            granted_at=datetime.now(timezone.utc),
            expires_at=(
                datetime.now(timezone.utc) + __import__('datetime').timedelta(hours=validity_hours)
                if validity_hours else None
            ),
            pac_reference=pac_reference,
            bounds=bounds or {}
        )

        self._permissions[permission.permission_id] = permission
        return permission

    def verify_permission(
        self,
        permission_id: str,
        agent_id: str,
        learning_scope: str
    ) -> tuple[bool, str]:
        """Verify a learning permission."""
        permission = self._permissions.get(permission_id)
        
        if not permission:
            return False, "Permission not found"
        
        if permission.agent_id != agent_id:
            return False, "Permission not for this agent"
        
        if permission.learning_scope != learning_scope:
            return False, "Permission scope mismatch"
        
        if not permission.is_valid():
            return False, "Permission expired"
        
        return True, "Permission valid"

    def is_prohibited_learning(self, learning_scope: str) -> tuple[bool, str]:
        """Check if learning scope matches prohibited patterns."""
        for pattern in PROHIBITED_PATTERNS:
            if pattern in learning_scope.lower():
                return True, f"Prohibited pattern detected: {pattern}"
        return False, "Learning scope allowed"

    def create_checkpoint(
        self,
        agent_id: str,
        learning_id: str,
        state: dict[str, Any]
    ) -> LearningCheckpoint:
        """Create a checkpoint before learning."""
        checkpoint = LearningCheckpoint(
            checkpoint_id=self._generate_id("CKPT"),
            agent_id=agent_id,
            state_hash=self._compute_hash(state),
            state_snapshot=copy.deepcopy(state),
            created_at=datetime.now(timezone.utc),
            learning_id=learning_id
        )
        
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint
        return checkpoint

    def record_learning(
        self,
        agent_id: str,
        permission_id: str,
        before_state: dict[str, Any],
        after_state: dict[str, Any],
        description: str
    ) -> LearningDelta:
        """Record a learning operation."""
        # Verify permission
        permission = self._permissions.get(permission_id)
        if not permission:
            raise PermissionError("Invalid permission ID")
        
        valid, message = self.verify_permission(
            permission_id, agent_id, permission.learning_scope
        )
        if not valid:
            raise PermissionError(f"Permission verification failed: {message}")

        # Check for prohibited patterns
        prohibited, reason = self.is_prohibited_learning(description)
        if prohibited:
            raise PermissionError(f"Learning blocked: {reason}")

        # Create checkpoint
        learning_id = self._generate_id("LEARN")
        checkpoint = self.create_checkpoint(agent_id, learning_id, before_state)

        # Record delta
        delta = LearningDelta(
            learning_id=learning_id,
            agent_id=agent_id,
            gate_type=permission.gate_type,
            permission_proof=permission_id,
            before_state_hash=self._compute_hash(before_state),
            after_state_hash=self._compute_hash(after_state),
            delta_description=description,
            timestamp=datetime.now(timezone.utc),
            checkpoint_id=checkpoint.checkpoint_id,
            reversible=True
        )

        self._deltas.append(delta)
        self._agent_states[agent_id] = after_state

        return delta

    def rollback_learning(
        self,
        learning_id: str,
        reason: str
    ) -> tuple[bool, dict[str, Any]]:
        """Rollback a learning operation."""
        # Find delta
        delta = next((d for d in self._deltas if d.learning_id == learning_id), None)
        if not delta:
            return False, {"error": "Learning operation not found"}
        
        if delta.rolled_back:
            return False, {"error": "Already rolled back"}
        
        if not delta.reversible:
            return False, {"error": "Learning not reversible"}

        # Find checkpoint
        checkpoint = self._checkpoints.get(delta.checkpoint_id)
        if not checkpoint:
            return False, {"error": "Checkpoint not found"}

        # Restore state
        self._agent_states[delta.agent_id] = copy.deepcopy(checkpoint.state_snapshot)
        delta.rolled_back = True
        delta.metadata["rollback_reason"] = reason
        delta.metadata["rolled_back_at"] = datetime.now(timezone.utc).isoformat()

        return True, {
            "restored_state_hash": checkpoint.state_hash,
            "reason": reason,
            "rolled_back_at": delta.metadata["rolled_back_at"]
        }

    def issue_reward(
        self,
        recipient_agent: str,
        reward_type: RewardType,
        reward_value: float,
        justification: str,
        issuer: str,
        linked_learning_id: Optional[str] = None
    ) -> RewardArtifact:
        """Issue a learning reward."""
        # Validate issuer
        allowed_issuers = self.REWARD_ISSUERS.get(reward_type, [])
        if issuer not in allowed_issuers:
            raise PermissionError(
                f"Issuer {issuer} not authorized for {reward_type.value} rewards"
            )

        # Check for self-reward (prohibited)
        if issuer == recipient_agent:
            raise PermissionError("Self-reward is prohibited")

        reward = RewardArtifact(
            reward_id=self._generate_id("REWARD"),
            recipient_agent=recipient_agent,
            issuer=issuer,
            reward_type=reward_type,
            reward_value=reward_value,
            justification=justification,
            linked_learning_id=linked_learning_id,
            timestamp=datetime.now(timezone.utc)
        )

        self._rewards.append(reward)
        return reward

    def get_agent_learning_history(self, agent_id: str) -> list[dict[str, Any]]:
        """Get learning history for an agent."""
        agent_deltas = [d for d in self._deltas if d.agent_id == agent_id]
        return [d.to_dict() for d in agent_deltas]

    def get_agent_rewards(self, agent_id: str) -> list[dict[str, Any]]:
        """Get rewards for an agent."""
        agent_rewards = [r for r in self._rewards if r.recipient_agent == agent_id]
        return [r.to_dict() for r in agent_rewards]

    def get_summary(self) -> dict[str, Any]:
        """Get engine summary."""
        return {
            "total_permissions": len(self._permissions),
            "active_permissions": sum(1 for p in self._permissions.values() if p.is_valid()),
            "total_checkpoints": len(self._checkpoints),
            "total_deltas": len(self._deltas),
            "rolled_back_count": sum(1 for d in self._deltas if d.rolled_back),
            "total_rewards": len(self._rewards),
            "rewards_by_type": {
                rt.value: sum(1 for r in self._rewards if r.reward_type == rt)
                for rt in RewardType
            }
        }

    def export(self) -> dict[str, Any]:
        """Export engine state."""
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "permissions": [p.to_dict() for p in self._permissions.values()],
            "checkpoints": [c.to_dict() for c in self._checkpoints.values()],
            "deltas": [d.to_dict() for d in self._deltas],
            "rewards": [r.to_dict() for r in self._rewards],
            "summary": self.get_summary()
        }

    def save(self) -> None:
        """Save engine state."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.export(), f, indent=2)


# Singleton instance
_learning_engine: Optional[ProofGatedLearningEngine] = None


def get_learning_engine() -> ProofGatedLearningEngine:
    """Get global learning engine instance."""
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = ProofGatedLearningEngine()
    return _learning_engine
