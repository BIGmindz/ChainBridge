"""
ChainBridge Swarm Types
=======================
Canonical type definitions for agent orchestration to prevent circular dependencies.

Created: PAC-DEV-P50 (Cortex Resonance)
Purpose: Shared types between AgentClone, LLMBridge, and AgentUniversity
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PrimeDirective:
    """
    Constitutional instructions for an AgentClone.
    
    Attributes:
        mission: High-level objective (e.g., "Validate governance compliance")
        constraints: Operating boundaries (e.g., "READ_ONLY", "NO_EXTERNAL_API_CALLS")
        success_criteria: Measurable outcomes
        escalation_policy: When to defer to parent GID
        metadata: Custom configuration (PAC ID, batch ID, etc.)
    """
    mission: str
    constraints: List[str] = field(default_factory=list)
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    escalation_policy: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate directive completeness."""
        if not self.mission:
            raise ValueError("PrimeDirective.mission cannot be empty")
        if not self.constraints:
            self.constraints = ["DETERMINISTIC_ONLY"]  # Default to safe mode


@dataclass
class Task:
    """
    Atomic work unit for agent execution.
    
    Attributes:
        task_id: Unique identifier (e.g., "TASK-VAL-001")
        task_type: Category (e.g., "GOVERNANCE_CHECK", "RISK_ASSESSMENT")
        payload: Input data for processing
        priority: Execution order (1=highest)
        timeout_seconds: Max execution time
        created_at: Timestamp of task creation
        assigned_to: GID of assigned agent (optional)
    """
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: int = 1
    timeout_seconds: int = 300
    created_at: datetime = field(default_factory=datetime.now)
    assigned_to: Optional[str] = None
    
    def __post_init__(self):
        """Validate task structure."""
        if not self.task_id or not self.task_type:
            raise ValueError("Task must have task_id and task_type")
        if self.priority < 1:
            raise ValueError("Task priority must be >= 1")


@dataclass
class ReasoningResult:
    """
    Output from LLMBridge reasoning process.
    
    Attributes:
        decision: Final recommendation (e.g., "APPROVE", "REJECT", "ESCALATE")
        reasoning: Chain-of-thought explanation
        confidence: Score 0.0-1.0
        hash: SHA3-256 of decision+reasoning (determinism check)
        metadata: LLM config (model, temperature, token count)
    """
    decision: str
    reasoning: str
    confidence: float
    hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate reasoning result."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if not self.hash or len(self.hash) != 64:  # SHA3-256 = 32 bytes = 64 hex chars
            raise ValueError("Invalid SHA3-256 hash (expected 64 hex characters)")
