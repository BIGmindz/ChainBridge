"""
Gate Abstraction Module
=======================

Base abstraction for PAG gates in the orchestration engine.

PDO Canon: Proof → Decision → Outcome
Governance: GOLD STANDARD
Failure Discipline: FAIL-CLOSED
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class GateStatus(Enum):
    """Gate execution status values."""
    
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    HALTED = "HALTED"


@dataclass
class GateResult:
    """
    Result of a gate execution.
    
    PDO Structure:
        - proof: Evidence collected during execution
        - decision: Determination made based on proof
        - outcome: Final result (PASS/FAIL)
    """
    
    gate_id: str
    status: GateStatus
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    proof: dict[str, Any] = field(default_factory=dict)
    decision: str = ""
    outcome: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for event emission."""
        return {
            "gate_id": self.gate_id,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "proof": self.proof,
            "decision": self.decision,
            "outcome": self.outcome,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }
    
    @property
    def passed(self) -> bool:
        """Check if gate passed."""
        return self.status == GateStatus.PASS
    
    @property
    def failed(self) -> bool:
        """Check if gate failed."""
        return self.status == GateStatus.FAIL


class Gate(ABC):
    """
    Abstract base class for PAG gates.
    
    All gates must implement:
        - execute(): Perform gate logic and return GateResult
        - render_terminal(): Produce canonical terminal output
    
    Invariants:
        - Proof precedes Decision
        - Decision precedes Outcome
        - No Outcome without prior gates
    """
    
    def __init__(self, gate_id: str, name: str, description: str = ""):
        self.gate_id = gate_id
        self.name = name
        self.description = description
        self._status = GateStatus.PENDING
        self._result: Optional[GateResult] = None
    
    @property
    def status(self) -> GateStatus:
        """Current gate status."""
        return self._status
    
    @property
    def result(self) -> Optional[GateResult]:
        """Gate execution result."""
        return self._result
    
    @abstractmethod
    def execute(self, context: dict[str, Any]) -> GateResult:
        """
        Execute the gate logic.
        
        Args:
            context: Execution context with runtime state
            
        Returns:
            GateResult with PDO structure (proof, decision, outcome)
            
        Note:
            Implementations MUST:
            - Collect proof before making decisions
            - Make explicit PASS/FAIL decision
            - Record outcome with justification
        """
        pass
    
    def render_terminal(self, result: GateResult) -> str:
        """
        Render canonical terminal output for the gate.
        
        Format:
            🟦 {GATE_ID} — {NAME}
            Status: {STATUS}
            Proof: {PROOF_SUMMARY}
            Decision: {DECISION}
            Outcome: {OUTCOME}
            Duration: {DURATION_MS}ms
        """
        status_icon = "✓" if result.passed else "✗" if result.failed else "○"
        
        lines = [
            f"",
            f"{'─' * 60}",
            f"🟦 {self.gate_id} — {self.name}",
            f"{'─' * 60}",
            f"Status: {status_icon} {result.status.value}",
        ]
        
        if result.proof:
            proof_summary = ", ".join(f"{k}={v}" for k, v in result.proof.items())
            lines.append(f"Proof: {proof_summary}")
        
        if result.decision:
            lines.append(f"Decision: {result.decision}")
        
        if result.outcome:
            lines.append(f"Outcome: {result.outcome}")
        
        if result.error:
            lines.append(f"Error: {result.error}")
        
        lines.append(f"Duration: {result.duration_ms:.2f}ms")
        lines.append(f"Timestamp: {result.timestamp.isoformat()}")
        lines.append(f"{'─' * 60}")
        
        return "\n".join(lines)
    
    def run(self, context: dict[str, Any]) -> GateResult:
        """
        Execute gate with status tracking and timing.
        
        This is the public interface for gate execution.
        Handles status transitions and timing automatically.
        """
        import time
        
        self._status = GateStatus.RUNNING
        start_time = time.perf_counter()
        
        try:
            result = self.execute(context)
            result.duration_ms = (time.perf_counter() - start_time) * 1000
            self._result = result
            self._status = result.status
            return result
        except Exception as e:
            elapsed = (time.perf_counter() - start_time) * 1000
            self._status = GateStatus.FAIL
            self._result = GateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                proof={"exception_type": type(e).__name__},
                decision="FAIL due to unhandled exception",
                outcome="Gate execution aborted",
                error=str(e),
                duration_ms=elapsed,
            )
            return self._result
