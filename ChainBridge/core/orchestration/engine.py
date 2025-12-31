"""
Orchestration Engine Module
===========================

Deterministic, observable runtime engine for PAG gate execution.

PDO Canon: Proof → Decision → Outcome
Governance: GOLD STANDARD
Failure Discipline: FAIL-CLOSED

Invariants:
    - Gates execute in strict order (PAG-01 → PAG-07)
    - Any FAIL halts downstream execution
    - All transitions are visible
    - No optimistic execution paths
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from .gate import Gate, GateStatus, GateResult
from .events import EventEmitter, EventType


class EngineState(Enum):
    """Engine lifecycle states."""
    
    IDLE = "IDLE"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    HALTED = "HALTED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


@dataclass
class ExecutionReport:
    """
    Execution report containing full PDO trace.
    
    This is the BER (Benson Execution Report) or WRAP (Agent Work Report)
    artifact produced at execution completion.
    """
    
    execution_id: str
    state: EngineState
    started_at: datetime
    completed_at: Optional[datetime] = None
    gates_executed: int = 0
    gates_passed: int = 0
    gates_failed: int = 0
    gate_results: list[dict[str, Any]] = field(default_factory=list)
    halt_reason: Optional[str] = None
    proof: dict[str, Any] = field(default_factory=dict)
    decision: str = ""
    outcome: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "execution_id": self.execution_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "gates_executed": self.gates_executed,
            "gates_passed": self.gates_passed,
            "gates_failed": self.gates_failed,
            "gate_results": self.gate_results,
            "halt_reason": self.halt_reason,
            "proof": self.proof,
            "decision": self.decision,
            "outcome": self.outcome,
        }
    
    def render_terminal(self) -> str:
        """Render canonical terminal report."""
        status_icon = "✅" if self.state == EngineState.COMPLETED else "🛑"
        
        lines = [
            "",
            "═" * 70,
            f"🟦🟦🟦 EXECUTION REPORT — {self.execution_id} 🟦🟦🟦",
            "═" * 70,
            "",
            f"State: {status_icon} {self.state.value}",
            f"Started: {self.started_at.isoformat()}",
            f"Completed: {self.completed_at.isoformat() if self.completed_at else 'N/A'}",
            "",
            "─" * 70,
            "GATE SUMMARY",
            "─" * 70,
            f"  Executed: {self.gates_executed}",
            f"  Passed:   {self.gates_passed}",
            f"  Failed:   {self.gates_failed}",
            "",
        ]
        
        # Gate results table
        lines.append("─" * 70)
        lines.append(f"{'GATE':<20} {'STATUS':<12} {'DURATION':<12} {'OUTCOME':<24}")
        lines.append("─" * 70)
        
        for gr in self.gate_results:
            gate_id = gr.get("gate_id", "N/A")[:18]
            status = gr.get("status", "N/A")
            duration = f"{gr.get('duration_ms', 0):.2f}ms"
            outcome = gr.get("outcome", "")[:22]
            icon = "✓" if status == "PASS" else "✗" if status == "FAIL" else "○"
            lines.append(f"  {icon} {gate_id:<17} {status:<12} {duration:<12} {outcome}")
        
        lines.append("─" * 70)
        
        # PDO Summary
        lines.append("")
        lines.append("─" * 70)
        lines.append("PDO SUMMARY")
        lines.append("─" * 70)
        lines.append(f"  Proof: {self.proof}")
        lines.append(f"  Decision: {self.decision}")
        lines.append(f"  Outcome: {self.outcome}")
        
        if self.halt_reason:
            lines.append("")
            lines.append("─" * 70)
            lines.append(f"🛑 HALT REASON: {self.halt_reason}")
            lines.append("─" * 70)
        
        lines.append("")
        lines.append("═" * 70)
        lines.append(f"🟦🟦🟦 END — EXECUTION REPORT 🟦🟦🟦")
        lines.append("═" * 70)
        
        return "\n".join(lines)


class OrchestrationEngine:
    """
    Deterministic orchestration engine for PAG gate execution.
    
    Execution Model:
        1. Initialize with ordered list of gates
        2. Execute gates sequentially (PAG-01 → PAG-07)
        3. Emit events for each gate transition
        4. HALT on any FAIL (fail-closed discipline)
        5. Produce ExecutionReport (WRAP/BER)
    
    Governance: GOLD STANDARD
    Failure Discipline: FAIL-CLOSED
    Observability: MANDATORY
    """
    
    def __init__(
        self,
        execution_id: str,
        event_emitter: Optional[EventEmitter] = None,
        terminal_output: bool = True,
    ):
        self.execution_id = execution_id
        self._state = EngineState.IDLE
        self._gates: list[Gate] = []
        self._results: list[GateResult] = []
        self._context: dict[str, Any] = {}
        self._terminal_output = terminal_output
        
        # Initialize event emitter
        self._emitter = event_emitter or EventEmitter(
            terminal_output=terminal_output,
            json_output=False,
        )
        
        # Execution tracking
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._halt_reason: Optional[str] = None
    
    @property
    def state(self) -> EngineState:
        """Current engine state."""
        return self._state
    
    def register_gate(self, gate: Gate) -> None:
        """
        Register a gate for execution.
        
        Gates execute in registration order.
        """
        self._gates.append(gate)
    
    def register_gates(self, gates: list[Gate]) -> None:
        """Register multiple gates in order."""
        for gate in gates:
            self.register_gate(gate)
    
    def set_context(self, context: dict[str, Any]) -> None:
        """Set execution context."""
        self._context = context
    
    def update_context(self, updates: dict[str, Any]) -> None:
        """Update execution context."""
        self._context.update(updates)
    
    def run(self) -> ExecutionReport:
        """
        Execute all registered gates.
        
        Execution Rules:
            - Gates execute in registration order
            - Each gate receives accumulated context
            - Any FAIL triggers immediate HALT
            - All transitions emit events
        
        Returns:
            ExecutionReport (WRAP/BER artifact)
        """
        self._state = EngineState.INITIALIZING
        self._started_at = datetime.now(timezone.utc)
        self._results = []
        
        # Emit engine start
        self._emitter.emit(
            EventType.ENGINE_START,
            gate_id="ENGINE",
            payload={"execution_id": self.execution_id, "gate_count": len(self._gates)},
        )
        
        if self._terminal_output:
            self._render_header()
        
        self._state = EngineState.RUNNING
        
        # Execute gates sequentially
        for i, gate in enumerate(self._gates):
            # Emit gate pending
            self._emitter.emit(
                EventType.GATE_PENDING,
                gate_id=gate.gate_id,
                payload={"sequence": i + 1, "total": len(self._gates)},
            )
            
            # Emit gate running
            self._emitter.emit(
                EventType.GATE_RUNNING,
                gate_id=gate.gate_id,
            )
            
            # Execute gate
            result = gate.run(self._context)
            self._results.append(result)
            
            # Emit result event
            if result.passed:
                self._emitter.emit(
                    EventType.GATE_PASS,
                    gate_id=gate.gate_id,
                    payload=result.to_dict(),
                )
            else:
                self._emitter.emit(
                    EventType.GATE_FAIL,
                    gate_id=gate.gate_id,
                    payload=result.to_dict(),
                )
            
            # Render terminal output
            if self._terminal_output:
                print(gate.render_terminal(result))
            
            # Update context with result
            self._context[f"gate_{gate.gate_id}_result"] = result.to_dict()
            
            # HALT on failure (fail-closed discipline)
            if result.failed:
                self._halt(f"Gate {gate.gate_id} FAILED: {result.error or result.outcome}")
                break
        
        # Complete execution
        if self._state != EngineState.HALTED:
            self._state = EngineState.COMPLETED
        
        self._completed_at = datetime.now(timezone.utc)
        
        # Emit engine stop/halt
        event_type = EventType.ENGINE_HALT if self._state == EngineState.HALTED else EventType.ENGINE_STOP
        self._emitter.emit(
            event_type,
            gate_id="ENGINE",
            payload={"state": self._state.value, "halt_reason": self._halt_reason},
        )
        
        # Produce report
        report = self._produce_report()
        
        if self._terminal_output:
            print(report.render_terminal())
        
        return report
    
    def _halt(self, reason: str) -> None:
        """Halt execution with reason."""
        self._state = EngineState.HALTED
        self._halt_reason = reason
        
        # Skip remaining gates
        for gate in self._gates:
            if gate.status == GateStatus.PENDING:
                self._emitter.emit(
                    EventType.GATE_SKIP,
                    gate_id=gate.gate_id,
                    payload={"reason": "Upstream gate failed"},
                )
    
    def _produce_report(self) -> ExecutionReport:
        """Produce execution report (WRAP/BER)."""
        gates_passed = sum(1 for r in self._results if r.passed)
        gates_failed = sum(1 for r in self._results if r.failed)
        
        # Aggregate proof
        proof = {
            "execution_id": self.execution_id,
            "gates_registered": len(self._gates),
            "gates_executed": len(self._results),
            "gate_ids": [g.gate_id for g in self._gates],
        }
        
        # Determine decision
        if self._state == EngineState.COMPLETED:
            decision = f"All {len(self._gates)} gates executed successfully"
        elif self._state == EngineState.HALTED:
            decision = f"Execution halted after {len(self._results)} gates due to failure"
        else:
            decision = f"Execution ended in state {self._state.value}"
        
        # Determine outcome
        if gates_failed == 0 and gates_passed == len(self._gates):
            outcome = "SUCCESS - All gates passed"
        elif gates_failed > 0:
            outcome = f"FAILURE - {gates_failed} gate(s) failed"
        else:
            outcome = f"INCOMPLETE - {gates_passed}/{len(self._gates)} gates passed"
        
        return ExecutionReport(
            execution_id=self.execution_id,
            state=self._state,
            started_at=self._started_at,
            completed_at=self._completed_at,
            gates_executed=len(self._results),
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            gate_results=[r.to_dict() for r in self._results],
            halt_reason=self._halt_reason,
            proof=proof,
            decision=decision,
            outcome=outcome,
        )
    
    def _render_header(self) -> None:
        """Render execution header to terminal."""
        print("")
        print("═" * 70)
        print(f"🟦🟦🟦 ORCHESTRATION ENGINE — {self.execution_id} 🟦🟦🟦")
        print("═" * 70)
        print("")
        print(f"Governance: GOLD STANDARD")
        print(f"Failure Discipline: FAIL-CLOSED")
        print(f"PDO Canon: Proof → Decision → Outcome")
        print(f"Gates Registered: {len(self._gates)}")
        print("")
        print("─" * 70)
        print("GATE EXECUTION SEQUENCE")
        print("─" * 70)
        for i, gate in enumerate(self._gates, 1):
            print(f"  [{i}] {gate.gate_id}: {gate.name}")
        print("─" * 70)
        print("")
