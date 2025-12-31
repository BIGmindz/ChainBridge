# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Governance Schema & Execution Semantics
# PAC-012: Governance Hardening — ORDER 1 (Cody GID-01)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Governance schema definitions for agent acknowledgment, failure semantics,
non-capabilities declarations, and human-in-the-loop boundaries.

GOVERNANCE INVARIANTS:
- INV-GOV-001: Explicit agent acknowledgment required
- INV-GOV-002: No execution without declared dependencies
- INV-GOV-003: No silent partial success
- INV-GOV-004: No undeclared capabilities
- INV-GOV-005: No human override without PDO
- INV-GOV-006: Retention & time bounds explicit
- INV-GOV-007: Training signals classified
- INV-GOV-008: Fail-closed on any violation
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

GOVERNANCE_SCHEMA_VERSION = "1.0.0"
"""Governance schema version."""

UNAVAILABLE_MARKER = "UNAVAILABLE"
"""Explicit marker for unavailable data."""


# ═══════════════════════════════════════════════════════════════════════════════
# ACKNOWLEDGMENT SCHEMA (INV-GOV-001)
# ═══════════════════════════════════════════════════════════════════════════════

class AcknowledgmentStatus(str, Enum):
    """
    Agent acknowledgment status.
    
    INV-GOV-001: Explicit agent acknowledgment required.
    """
    PENDING = "PENDING"           # Awaiting acknowledgment
    ACKNOWLEDGED = "ACKNOWLEDGED"  # Agent has acknowledged
    REJECTED = "REJECTED"          # Agent rejected (with reason)
    TIMEOUT = "TIMEOUT"            # Acknowledgment timed out
    NOT_REQUIRED = "NOT_REQUIRED"  # Acknowledgment not required for this order


class AcknowledgmentType(str, Enum):
    """Type of acknowledgment required."""
    ACK_REQUIRED = "ACK_REQUIRED"     # Must acknowledge before execution
    ACK_OPTIONAL = "ACK_OPTIONAL"     # May acknowledge but not required
    ACK_IMPLICIT = "ACK_IMPLICIT"     # Acknowledged by starting execution


@dataclass
class AgentAcknowledgment:
    """
    Record of agent acknowledgment for an execution order.
    
    INV-GOV-001: Every execution requires explicit acknowledgment.
    """
    ack_id: str
    pac_id: str
    order_id: str
    agent_gid: str
    agent_name: str
    
    # Acknowledgment details
    ack_type: AcknowledgmentType
    status: AcknowledgmentStatus
    
    # Timestamps
    requested_at: str
    acknowledged_at: Optional[str] = None
    timeout_at: Optional[str] = None
    
    # Response
    response_message: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    # Chain integrity
    ack_hash: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ack_id": self.ack_id,
            "pac_id": self.pac_id,
            "order_id": self.order_id,
            "agent_gid": self.agent_gid,
            "agent_name": self.agent_name,
            "ack_type": self.ack_type.value,
            "status": self.status.value,
            "requested_at": self.requested_at,
            "acknowledged_at": self.acknowledged_at,
            "timeout_at": self.timeout_at,
            "response_message": self.response_message,
            "rejection_reason": self.rejection_reason,
            "ack_hash": self.ack_hash,
        }
    
    @property
    def is_complete(self) -> bool:
        """Check if acknowledgment process is complete."""
        return self.status in {
            AcknowledgmentStatus.ACKNOWLEDGED,
            AcknowledgmentStatus.REJECTED,
            AcknowledgmentStatus.TIMEOUT,
            AcknowledgmentStatus.NOT_REQUIRED,
        }
    
    @property
    def allows_execution(self) -> bool:
        """Check if acknowledgment allows execution to proceed."""
        return self.status in {
            AcknowledgmentStatus.ACKNOWLEDGED,
            AcknowledgmentStatus.NOT_REQUIRED,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FAILURE & ROLLBACK SEMANTICS (INV-GOV-003)
# ═══════════════════════════════════════════════════════════════════════════════

class FailureMode(str, Enum):
    """
    Failure mode classification.
    
    INV-GOV-003: No silent partial success.
    """
    FAIL_CLOSED = "FAIL_CLOSED"         # Halt all downstream execution
    FAIL_OPEN = "FAIL_OPEN"             # Continue with degraded state
    FAIL_RETRY = "FAIL_RETRY"           # Retry with backoff
    FAIL_COMPENSATE = "FAIL_COMPENSATE"  # Execute compensation action


class RollbackStrategy(str, Enum):
    """Rollback strategy for failed executions."""
    NONE = "NONE"                       # No rollback possible
    COMPENSATING = "COMPENSATING"       # Execute compensating transaction
    CHECKPOINT = "CHECKPOINT"           # Restore from checkpoint
    FULL_REVERT = "FULL_REVERT"         # Revert all changes


class ExecutionOutcome(str, Enum):
    """Outcome of an execution order."""
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"  # INV-GOV-003: Must be explicit
    FAILURE = "FAILURE"
    SKIPPED = "SKIPPED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass
class FailureSemantics:
    """
    Failure semantics definition for an execution context.
    
    INV-GOV-003: No silent partial success — all outcomes explicit.
    INV-GOV-008: Fail-closed on any violation.
    """
    order_id: str
    pac_id: str
    
    # Failure configuration
    failure_mode: FailureMode
    rollback_strategy: RollbackStrategy
    
    # Retry configuration
    max_retries: int = 0
    retry_delay_seconds: int = 0
    
    # Partial success handling
    partial_success_allowed: bool = False
    partial_success_threshold: float = 0.0  # 0.0 - 1.0
    
    # Compensation
    compensation_action: Optional[str] = None
    
    # Downstream impact
    blocks_downstream: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "order_id": self.order_id,
            "pac_id": self.pac_id,
            "failure_mode": self.failure_mode.value,
            "rollback_strategy": self.rollback_strategy.value,
            "max_retries": self.max_retries,
            "retry_delay_seconds": self.retry_delay_seconds,
            "partial_success_allowed": self.partial_success_allowed,
            "partial_success_threshold": self.partial_success_threshold,
            "compensation_action": self.compensation_action,
            "blocks_downstream": self.blocks_downstream,
        }


@dataclass
class ExecutionFailure:
    """
    Record of an execution failure with full semantics.
    """
    failure_id: str
    pac_id: str
    order_id: str
    agent_gid: str
    
    # Failure details
    outcome: ExecutionOutcome
    error_code: str
    error_message: str
    
    # Recovery
    recovery_attempted: bool = False
    recovery_successful: bool = False
    rollback_executed: bool = False
    
    # Impact
    downstream_blocked: List[str] = field(default_factory=list)
    
    # Timestamps
    failed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recovered_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# NON-CAPABILITIES DECLARATION (INV-GOV-004)
# ═══════════════════════════════════════════════════════════════════════════════

class CapabilityCategory(str, Enum):
    """Categories of system capabilities."""
    DATA_ACCESS = "DATA_ACCESS"
    DATA_MUTATION = "DATA_MUTATION"
    EXTERNAL_API = "EXTERNAL_API"
    FINANCIAL_ACTION = "FINANCIAL_ACTION"
    USER_IMPERSONATION = "USER_IMPERSONATION"
    SYSTEM_CONTROL = "SYSTEM_CONTROL"
    TRAINING_FEEDBACK = "TRAINING_FEEDBACK"


@dataclass
class NonCapability:
    """
    Explicit declaration of a non-capability.
    
    INV-GOV-004: No undeclared capabilities.
    """
    capability_id: str
    category: CapabilityCategory
    description: str
    reason: str
    
    # Scope
    applies_to_agents: List[str] = field(default_factory=list)  # Empty = all agents
    applies_to_pacs: List[str] = field(default_factory=list)    # Empty = all PACs
    
    # Enforcement
    enforced: bool = True
    violation_action: str = "FAIL_CLOSED"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "capability_id": self.capability_id,
            "category": self.category.value,
            "description": self.description,
            "reason": self.reason,
            "applies_to_agents": self.applies_to_agents,
            "applies_to_pacs": self.applies_to_pacs,
            "enforced": self.enforced,
            "violation_action": self.violation_action,
        }


# Canonical non-capabilities list
CANONICAL_NON_CAPABILITIES: List[NonCapability] = [
    NonCapability(
        capability_id="NON-CAP-001",
        category=CapabilityCategory.FINANCIAL_ACTION,
        description="Direct financial transaction execution",
        reason="All financial actions require PDO creation and explicit settlement",
    ),
    NonCapability(
        capability_id="NON-CAP-002",
        category=CapabilityCategory.USER_IMPERSONATION,
        description="Acting as or impersonating a user",
        reason="Agents act only in their declared GID capacity",
    ),
    NonCapability(
        capability_id="NON-CAP-003",
        category=CapabilityCategory.DATA_MUTATION,
        description="Direct database mutation outside ledger",
        reason="All mutations must flow through append-only ledgers",
    ),
    NonCapability(
        capability_id="NON-CAP-004",
        category=CapabilityCategory.SYSTEM_CONTROL,
        description="System configuration changes at runtime",
        reason="Configuration changes require explicit PAC governance",
    ),
    NonCapability(
        capability_id="NON-CAP-005",
        category=CapabilityCategory.TRAINING_FEEDBACK,
        description="Direct model training or weight updates",
        reason="ML models are inference-only; training is out-of-band",
    ),
    NonCapability(
        capability_id="NON-CAP-006",
        category=CapabilityCategory.EXTERNAL_API,
        description="Unauthenticated external API calls",
        reason="All external calls must be declared and logged",
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# HUMAN-IN-THE-LOOP BOUNDARY CONTRACT (INV-GOV-005)
# ═══════════════════════════════════════════════════════════════════════════════

class HumanInterventionType(str, Enum):
    """Types of human intervention."""
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"     # Must approve before action
    REVIEW_REQUIRED = "REVIEW_REQUIRED"         # Must review but not approve
    NOTIFICATION_ONLY = "NOTIFICATION_ONLY"     # Inform only, no action required
    OVERRIDE = "OVERRIDE"                       # Human overriding system decision
    ESCALATION = "ESCALATION"                   # Escalating to human decision


class HumanBoundaryStatus(str, Enum):
    """Status of human boundary check."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TIMEOUT = "TIMEOUT"
    BYPASSED = "BYPASSED"  # With explicit PDO reference


@dataclass
class HumanBoundaryContract:
    """
    Contract defining human-in-the-loop boundaries.
    
    INV-GOV-005: No human override without PDO.
    """
    boundary_id: str
    pac_id: str
    
    # Boundary definition
    intervention_type: HumanInterventionType
    trigger_condition: str
    required_for: List[str]  # List of order IDs or action types
    
    # Requirements
    min_approvers: int = 1
    timeout_hours: int = 24
    
    # PDO requirement for overrides
    override_requires_pdo: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "boundary_id": self.boundary_id,
            "pac_id": self.pac_id,
            "intervention_type": self.intervention_type.value,
            "trigger_condition": self.trigger_condition,
            "required_for": self.required_for,
            "min_approvers": self.min_approvers,
            "timeout_hours": self.timeout_hours,
            "override_requires_pdo": self.override_requires_pdo,
        }


@dataclass
class HumanIntervention:
    """
    Record of a human intervention event.
    
    INV-GOV-005: All overrides must reference a PDO.
    """
    intervention_id: str
    boundary_id: str
    pac_id: str
    
    # Intervention details
    intervention_type: HumanInterventionType
    status: HumanBoundaryStatus
    
    # Human actor
    actor_id: str
    actor_role: str
    
    # Override PDO (required if override)
    override_pdo_id: Optional[str] = None
    
    # Decision
    decision: Optional[str] = None
    rationale: Optional[str] = None
    
    # Timestamps
    requested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def validate_override(self) -> tuple[bool, Optional[str]]:
        """
        Validate that override has required PDO.
        
        INV-GOV-005: No human override without PDO.
        """
        if self.intervention_type == HumanInterventionType.OVERRIDE:
            if not self.override_pdo_id:
                return False, "INV-GOV-005: Human override requires PDO reference"
        return True, None


# ═══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE VIOLATION
# ═══════════════════════════════════════════════════════════════════════════════

class GovernanceViolation(Exception):
    """
    Exception raised when a governance invariant is violated.
    
    INV-GOV-008: Fail-closed on any violation.
    """
    
    def __init__(
        self,
        invariant: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        fail_closed: bool = True,
    ):
        self.invariant = invariant
        self.message = message
        self.context = context or {}
        self.fail_closed = fail_closed
        self.timestamp = datetime.now(timezone.utc).isoformat()
        super().__init__(f"{invariant}: {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "invariant": self.invariant,
            "message": self.message,
            "context": self.context,
            "fail_closed": self.fail_closed,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ACKNOWLEDGMENT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class AcknowledgmentRegistry:
    """
    Registry for tracking agent acknowledgments.
    
    Thread-safe, append-only storage.
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._acknowledgments: List[AgentAcknowledgment] = []
        self._by_pac_id: Dict[str, List[AgentAcknowledgment]] = {}
        self._by_order_id: Dict[str, List[AgentAcknowledgment]] = {}
        self._by_agent_gid: Dict[str, List[AgentAcknowledgment]] = {}
        self._lock = threading.Lock()
    
    def request_acknowledgment(
        self,
        pac_id: str,
        order_id: str,
        agent_gid: str,
        agent_name: str,
        ack_type: AcknowledgmentType = AcknowledgmentType.ACK_REQUIRED,
        timeout_minutes: int = 60,
    ) -> AgentAcknowledgment:
        """
        Request acknowledgment from an agent.
        
        INV-GOV-001: Explicit agent acknowledgment required.
        """
        with self._lock:
            now = datetime.now(timezone.utc)
            timeout_at = (now + timedelta(minutes=timeout_minutes)).isoformat()
            
            ack_id = f"ack_{uuid.uuid4().hex[:12]}"
            
            # Compute hash
            content = f"{ack_id}|{pac_id}|{order_id}|{agent_gid}|{now.isoformat()}"
            ack_hash = hashlib.sha256(content.encode()).hexdigest()
            
            ack = AgentAcknowledgment(
                ack_id=ack_id,
                pac_id=pac_id,
                order_id=order_id,
                agent_gid=agent_gid,
                agent_name=agent_name,
                ack_type=ack_type,
                status=AcknowledgmentStatus.PENDING,
                requested_at=now.isoformat(),
                timeout_at=timeout_at,
                ack_hash=ack_hash,
            )
            
            self._store(ack)
            
            logger.info(
                f"GOVERNANCE: Acknowledgment requested [{ack_id}] "
                f"agent={agent_gid} order={order_id}"
            )
            
            return ack
    
    def acknowledge(
        self,
        ack_id: str,
        response_message: Optional[str] = None,
    ) -> AgentAcknowledgment:
        """
        Record agent acknowledgment.
        """
        with self._lock:
            ack = self._find_by_id(ack_id)
            if not ack:
                raise GovernanceViolation(
                    invariant="INV-GOV-001",
                    message=f"Acknowledgment {ack_id} not found",
                )
            
            ack.status = AcknowledgmentStatus.ACKNOWLEDGED
            ack.acknowledged_at = datetime.now(timezone.utc).isoformat()
            ack.response_message = response_message
            
            logger.info(f"GOVERNANCE: Acknowledged [{ack_id}]")
            
            return ack
    
    def reject(
        self,
        ack_id: str,
        rejection_reason: str,
    ) -> AgentAcknowledgment:
        """
        Record acknowledgment rejection.
        """
        with self._lock:
            ack = self._find_by_id(ack_id)
            if not ack:
                raise GovernanceViolation(
                    invariant="INV-GOV-001",
                    message=f"Acknowledgment {ack_id} not found",
                )
            
            ack.status = AcknowledgmentStatus.REJECTED
            ack.acknowledged_at = datetime.now(timezone.utc).isoformat()
            ack.rejection_reason = rejection_reason
            
            logger.warning(f"GOVERNANCE: Rejected [{ack_id}] reason={rejection_reason}")
            
            return ack
    
    def get_by_pac_id(self, pac_id: str) -> List[AgentAcknowledgment]:
        """Get all acknowledgments for a PAC."""
        with self._lock:
            return self._by_pac_id.get(pac_id, []).copy()
    
    def get_by_order_id(self, order_id: str) -> List[AgentAcknowledgment]:
        """Get all acknowledgments for an order."""
        with self._lock:
            return self._by_order_id.get(order_id, []).copy()
    
    def verify_execution_allowed(
        self,
        pac_id: str,
        order_id: str,
        agent_gid: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Verify execution is allowed based on acknowledgments.
        
        INV-GOV-001: Explicit agent acknowledgment required.
        """
        with self._lock:
            acks = [
                a for a in self._by_order_id.get(order_id, [])
                if a.agent_gid == agent_gid
            ]
            
            if not acks:
                return False, "No acknowledgment found for this order/agent"
            
            latest = max(acks, key=lambda a: a.requested_at)
            
            if not latest.allows_execution:
                return False, f"Acknowledgment status is {latest.status.value}"
            
            return True, None
    
    def _store(self, ack: AgentAcknowledgment) -> None:
        """Store acknowledgment with indexing."""
        self._acknowledgments.append(ack)
        
        if ack.pac_id not in self._by_pac_id:
            self._by_pac_id[ack.pac_id] = []
        self._by_pac_id[ack.pac_id].append(ack)
        
        if ack.order_id not in self._by_order_id:
            self._by_order_id[ack.order_id] = []
        self._by_order_id[ack.order_id].append(ack)
        
        if ack.agent_gid not in self._by_agent_gid:
            self._by_agent_gid[ack.agent_gid] = []
        self._by_agent_gid[ack.agent_gid].append(ack)
    
    def _find_by_id(self, ack_id: str) -> Optional[AgentAcknowledgment]:
        """Find acknowledgment by ID."""
        for ack in self._acknowledgments:
            if ack.ack_id == ack_id:
                return ack
        return None
    
    def __len__(self) -> int:
        """Return number of acknowledgments."""
        with self._lock:
            return len(self._acknowledgments)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCES
# ═══════════════════════════════════════════════════════════════════════════════

_ACK_REGISTRY: Optional[AcknowledgmentRegistry] = None
_REGISTRY_LOCK = threading.Lock()


def get_acknowledgment_registry() -> AcknowledgmentRegistry:
    """Get singleton acknowledgment registry."""
    global _ACK_REGISTRY
    
    if _ACK_REGISTRY is None:
        with _REGISTRY_LOCK:
            if _ACK_REGISTRY is None:
                _ACK_REGISTRY = AcknowledgmentRegistry()
                logger.info("Acknowledgment registry initialized")
    
    return _ACK_REGISTRY


def reset_acknowledgment_registry() -> None:
    """Reset singleton. For testing only."""
    global _ACK_REGISTRY
    with _REGISTRY_LOCK:
        _ACK_REGISTRY = None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Version
    "GOVERNANCE_SCHEMA_VERSION",
    # Acknowledgment
    "AcknowledgmentStatus",
    "AcknowledgmentType",
    "AgentAcknowledgment",
    "AcknowledgmentRegistry",
    "get_acknowledgment_registry",
    "reset_acknowledgment_registry",
    # Failure semantics
    "FailureMode",
    "RollbackStrategy",
    "ExecutionOutcome",
    "FailureSemantics",
    "ExecutionFailure",
    # Non-capabilities
    "CapabilityCategory",
    "NonCapability",
    "CANONICAL_NON_CAPABILITIES",
    # Human-in-the-loop
    "HumanInterventionType",
    "HumanBoundaryStatus",
    "HumanBoundaryContract",
    "HumanIntervention",
    # Violations
    "GovernanceViolation",
]
