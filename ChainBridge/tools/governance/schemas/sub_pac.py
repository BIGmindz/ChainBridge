"""
Sub-PAC Schema Definition

Authority: PAC-BENSON-P66-MULTI-AGENT-ORCHESTRATION-GOVERNED-EXECUTION-MODEL-01
Doctrine Reference: GOVERNANCE_DOCTRINE_V1.3

This module defines the schema and types for Sub-PACs (child PACs)
that are issued to individual agents in a multi-agent orchestration.

INVARIANTS:
  INV-SP-001: Sub-PAC inherits parent PAC constraints
  INV-SP-002: Sub-PAC is lane-restricted to assigned agent
  INV-SP-003: Sub-PAC cannot expand parent scope
  INV-SP-004: Sub-PAC failure blocks parent WRAP
  INV-SP-005: Sub-PAC must produce independent BER
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class SubPACStatus(str, Enum):
    """Status states for a Sub-PAC lifecycle."""
    
    ISSUED = "ISSUED"
    DISPATCHED = "DISPATCHED"
    EXECUTING = "EXECUTING"
    BER_PENDING = "BER_PENDING"
    PDO_PENDING = "PDO_PENDING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass
class AgentAssignment:
    """Agent assignment for a Sub-PAC."""
    
    agent_gid: str  # e.g., "GID-01"
    agent_name: str  # e.g., "CODY"
    execution_lane: str  # e.g., "CODE_GENERATION"
    
    def validate(self) -> bool:
        """Validate the agent assignment."""
        if not self.agent_gid.startswith("GID-"):
            raise ValueError(f"Invalid agent GID format: {self.agent_gid}")
        if not self.agent_name:
            raise ValueError("Agent name cannot be empty")
        if not self.execution_lane:
            raise ValueError("Execution lane cannot be empty")
        return True


@dataclass
class SubPACScope:
    """Scope definition for a Sub-PAC."""
    
    inherited_from_parent: bool = True
    lane_restricted: bool = True
    additional_constraints: list[str] = field(default_factory=list)
    
    # INV-SP-003: Sub-PAC cannot expand parent scope
    scope_expansion_forbidden: bool = True


@dataclass
class SubPACDependencies:
    """Dependencies for a Sub-PAC."""
    
    requires_completion: list[str] = field(default_factory=list)  # Sub-PAC IDs
    data_inputs: list[str] = field(default_factory=list)  # Output references
    
    def is_root(self) -> bool:
        """Check if this Sub-PAC has no dependencies (can dispatch immediately)."""
        return len(self.requires_completion) == 0


@dataclass
class SubPACOutput:
    """Output artifacts from a Sub-PAC execution."""
    
    execution_result_id: Optional[str] = None
    ber_id: Optional[str] = None
    pdo_id: Optional[str] = None
    
    execution_result_hash: Optional[str] = None
    ber_hash: Optional[str] = None
    pdo_hash: Optional[str] = None
    
    def all_artifacts_present(self) -> bool:
        """Check if all required output artifacts are present."""
        return all([
            self.execution_result_id,
            self.ber_id,
            self.pdo_id
        ])
    
    def compute_output_hash(self) -> str:
        """Compute a combined hash of all output artifacts."""
        if not self.all_artifacts_present():
            raise ValueError("Cannot compute hash: missing artifacts")
        
        combined = f"{self.execution_result_hash}|{self.ber_hash}|{self.pdo_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()


@dataclass
class SubPAC:
    """
    Sub-PAC Schema Definition.
    
    A Sub-PAC is a child PAC issued to an individual agent as part of
    a multi-agent orchestration. Each Sub-PAC:
      - Inherits constraints from the parent PAC
      - Is lane-restricted to the assigned agent
      - Cannot expand the parent scope
      - Must produce an independent BER
      - Failure blocks the parent WRAP
    
    Authority: PAC-BENSON-P66
    """
    
    # Identity
    sub_pac_id: str  # e.g., "Sub-PAC-BENSON-P66-A1-CODY-BACKEND-IMPL"
    parent_pac_id: str  # e.g., "PAC-BENSON-P66-MULTI-AGENT-ORCHESTRATION-..."
    maeg_node_id: str  # e.g., "A1"
    sequence: int  # 1, 2, 3, ...
    
    # Assignment
    agent_assignment: AgentAssignment
    
    # Scope
    scope: SubPACScope
    
    # Dependencies
    dependencies: SubPACDependencies
    
    # Outputs (populated during execution)
    outputs: SubPACOutput = field(default_factory=SubPACOutput)
    
    # State
    status: SubPACStatus = SubPACStatus.ISSUED
    created_at: datetime = field(default_factory=datetime.utcnow)
    dispatched_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    
    # Dispatch token (assigned when dispatched)
    dispatch_token: Optional[str] = None
    
    # Hash for integrity
    sub_pac_hash: Optional[str] = None
    
    def __post_init__(self):
        """Validate and compute hash after initialization."""
        self._validate_id_format()
        self.sub_pac_hash = self._compute_hash()
    
    def _validate_id_format(self) -> None:
        """Validate the Sub-PAC ID format."""
        if not self.sub_pac_id.startswith("Sub-PAC-"):
            raise ValueError(
                f"Invalid Sub-PAC ID format: {self.sub_pac_id}. "
                f"Must start with 'Sub-PAC-'"
            )
        if not self.parent_pac_id.startswith("PAC-"):
            raise ValueError(
                f"Invalid parent PAC ID format: {self.parent_pac_id}. "
                f"Must start with 'PAC-'"
            )
    
    def _compute_hash(self) -> str:
        """Compute the Sub-PAC hash for integrity verification."""
        content = {
            "sub_pac_id": self.sub_pac_id,
            "parent_pac_id": self.parent_pac_id,
            "maeg_node_id": self.maeg_node_id,
            "sequence": self.sequence,
            "agent_gid": self.agent_assignment.agent_gid,
            "agent_name": self.agent_assignment.agent_name,
            "execution_lane": self.agent_assignment.execution_lane,
            "created_at": self.created_at.isoformat(),
        }
        canonical = json.dumps(content, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    # --- State Transitions ---
    
    def dispatch(self, dispatch_token: str) -> None:
        """
        Dispatch the Sub-PAC to its assigned agent.
        
        INV-SP-002: Enforces lane restriction via dispatch token binding.
        
        Raises:
            ValueError: If dispatch preconditions are not met.
        """
        if self.status != SubPACStatus.ISSUED:
            raise ValueError(
                f"Cannot dispatch Sub-PAC in status {self.status}. "
                f"Expected: ISSUED"
            )
        
        # Validate dependencies (INV: DISPATCH_DEPENDENCY_UNMET)
        # Note: Caller must verify predecessor BERs have passed
        
        self.dispatch_token = dispatch_token
        self.dispatched_at = datetime.utcnow()
        self.status = SubPACStatus.DISPATCHED
    
    def begin_execution(self) -> None:
        """Mark the Sub-PAC as executing."""
        if self.status != SubPACStatus.DISPATCHED:
            raise ValueError(
                f"Cannot begin execution in status {self.status}. "
                f"Expected: DISPATCHED"
            )
        self.status = SubPACStatus.EXECUTING
    
    def await_ber(self, execution_result_id: str, execution_result_hash: str) -> None:
        """Mark execution complete and await BER generation."""
        if self.status != SubPACStatus.EXECUTING:
            raise ValueError(
                f"Cannot transition to BER_PENDING in status {self.status}. "
                f"Expected: EXECUTING"
            )
        self.outputs.execution_result_id = execution_result_id
        self.outputs.execution_result_hash = execution_result_hash
        self.status = SubPACStatus.BER_PENDING
    
    def set_ber(self, ber_id: str, ber_hash: str) -> None:
        """Record the BER generated for this Sub-PAC."""
        if self.status != SubPACStatus.BER_PENDING:
            raise ValueError(
                f"Cannot set BER in status {self.status}. "
                f"Expected: BER_PENDING"
            )
        self.outputs.ber_id = ber_id
        self.outputs.ber_hash = ber_hash
        self.status = SubPACStatus.PDO_PENDING
    
    def set_pdo(self, pdo_id: str, pdo_hash: str) -> None:
        """Record the PDO generated for this Sub-PAC."""
        if self.status != SubPACStatus.PDO_PENDING:
            raise ValueError(
                f"Cannot set PDO in status {self.status}. "
                f"Expected: PDO_PENDING"
            )
        self.outputs.pdo_id = pdo_id
        self.outputs.pdo_hash = pdo_hash
        self.completed_at = datetime.utcnow()
        self.status = SubPACStatus.COMPLETE
    
    def fail(self, reason: str) -> None:
        """
        Mark the Sub-PAC as failed.
        
        INV-SP-004: Sub-PAC failure blocks parent WRAP.
        """
        self.failed_at = datetime.utcnow()
        self.failure_reason = reason
        self.status = SubPACStatus.FAILED
    
    def block(self, reason: str) -> None:
        """Mark the Sub-PAC as blocked (due to dependency failure)."""
        self.failure_reason = reason
        self.status = SubPACStatus.BLOCKED
    
    # --- Queries ---
    
    def is_complete(self) -> bool:
        """Check if the Sub-PAC has completed successfully."""
        return self.status == SubPACStatus.COMPLETE
    
    def is_failed(self) -> bool:
        """Check if the Sub-PAC has failed."""
        return self.status in (SubPACStatus.FAILED, SubPACStatus.BLOCKED)
    
    def is_dispatchable(self) -> bool:
        """Check if the Sub-PAC can be dispatched."""
        return self.status == SubPACStatus.ISSUED
    
    def can_dispatch_immediately(self) -> bool:
        """Check if this Sub-PAC can dispatch without waiting for dependencies."""
        return self.is_dispatchable() and self.dependencies.is_root()
    
    # --- Serialization ---
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "sub_pac_id": self.sub_pac_id,
            "parent_pac_id": self.parent_pac_id,
            "maeg_node_id": self.maeg_node_id,
            "sequence": self.sequence,
            "agent_assignment": {
                "agent_gid": self.agent_assignment.agent_gid,
                "agent_name": self.agent_assignment.agent_name,
                "execution_lane": self.agent_assignment.execution_lane,
            },
            "scope": {
                "inherited_from_parent": self.scope.inherited_from_parent,
                "lane_restricted": self.scope.lane_restricted,
                "additional_constraints": self.scope.additional_constraints,
            },
            "dependencies": {
                "requires_completion": self.dependencies.requires_completion,
                "data_inputs": self.dependencies.data_inputs,
            },
            "outputs": {
                "execution_result_id": self.outputs.execution_result_id,
                "ber_id": self.outputs.ber_id,
                "pdo_id": self.outputs.pdo_id,
                "execution_result_hash": self.outputs.execution_result_hash,
                "ber_hash": self.outputs.ber_hash,
                "pdo_hash": self.outputs.pdo_hash,
            },
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
            "failure_reason": self.failure_reason,
            "dispatch_token": self.dispatch_token,
            "sub_pac_hash": self.sub_pac_hash,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubPAC:
        """Create a SubPAC from dictionary representation."""
        agent = AgentAssignment(
            agent_gid=data["agent_assignment"]["agent_gid"],
            agent_name=data["agent_assignment"]["agent_name"],
            execution_lane=data["agent_assignment"]["execution_lane"],
        )
        scope = SubPACScope(
            inherited_from_parent=data["scope"]["inherited_from_parent"],
            lane_restricted=data["scope"]["lane_restricted"],
            additional_constraints=data["scope"]["additional_constraints"],
        )
        deps = SubPACDependencies(
            requires_completion=data["dependencies"]["requires_completion"],
            data_inputs=data["dependencies"]["data_inputs"],
        )
        outputs = SubPACOutput(
            execution_result_id=data["outputs"]["execution_result_id"],
            ber_id=data["outputs"]["ber_id"],
            pdo_id=data["outputs"]["pdo_id"],
            execution_result_hash=data["outputs"]["execution_result_hash"],
            ber_hash=data["outputs"]["ber_hash"],
            pdo_hash=data["outputs"]["pdo_hash"],
        )
        
        sub_pac = cls(
            sub_pac_id=data["sub_pac_id"],
            parent_pac_id=data["parent_pac_id"],
            maeg_node_id=data["maeg_node_id"],
            sequence=data["sequence"],
            agent_assignment=agent,
            scope=scope,
            dependencies=deps,
            outputs=outputs,
            status=SubPACStatus(data["status"]),
        )
        
        # Restore timestamps
        if data.get("dispatched_at"):
            sub_pac.dispatched_at = datetime.fromisoformat(data["dispatched_at"])
        if data.get("completed_at"):
            sub_pac.completed_at = datetime.fromisoformat(data["completed_at"])
        if data.get("failed_at"):
            sub_pac.failed_at = datetime.fromisoformat(data["failed_at"])
        
        sub_pac.failure_reason = data.get("failure_reason")
        sub_pac.dispatch_token = data.get("dispatch_token")
        
        return sub_pac


# --- Factory Functions ---

def create_sub_pac(
    parent_pac_id: str,
    sequence: int,
    agent_gid: str,
    agent_name: str,
    execution_lane: str,
    task_descriptor: str,
    dependencies: list[str] | None = None,
    data_inputs: list[str] | None = None,
) -> SubPAC:
    """
    Factory function to create a Sub-PAC.
    
    Args:
        parent_pac_id: The parent PAC ID.
        sequence: The sequence number (1, 2, 3, ...).
        agent_gid: The agent's GID (e.g., "GID-01").
        agent_name: The agent's name (e.g., "CODY").
        execution_lane: The execution lane (e.g., "CODE_GENERATION").
        task_descriptor: Short descriptor for the task (e.g., "BACKEND-IMPL").
        dependencies: List of Sub-PAC IDs that must complete first.
        data_inputs: List of output references from other Sub-PACs.
    
    Returns:
        A new SubPAC instance in ISSUED status.
    """
    # Extract parent PAC name for Sub-PAC ID construction
    # e.g., "PAC-BENSON-P66-..." -> "BENSON-P66"
    parts = parent_pac_id.replace("PAC-", "").split("-")
    parent_short = "-".join(parts[:2]) if len(parts) >= 2 else parts[0]
    
    sub_pac_id = f"Sub-PAC-{parent_short}-A{sequence}-{agent_name}-{task_descriptor}"
    maeg_node_id = f"A{sequence}"
    
    return SubPAC(
        sub_pac_id=sub_pac_id,
        parent_pac_id=parent_pac_id,
        maeg_node_id=maeg_node_id,
        sequence=sequence,
        agent_assignment=AgentAssignment(
            agent_gid=agent_gid,
            agent_name=agent_name,
            execution_lane=execution_lane,
        ),
        scope=SubPACScope(),
        dependencies=SubPACDependencies(
            requires_completion=dependencies or [],
            data_inputs=data_inputs or [],
        ),
    )
