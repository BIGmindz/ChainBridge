# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Agent Execution Module
# PAC-008: Agent Execution Visibility
# PAC-009: End-to-End Traceability
# ═══════════════════════════════════════════════════════════════════════════════

"""
Agent Execution visibility and tracking module.

Provides:
- Agent activation events
- Agent execution state tracking
- Execution ledger persistence
- Cross-domain trace registry (PAC-009)

GOVERNANCE INVARIANTS:
INV-AGENT-001: Agent activation must be explicit and visible
INV-AGENT-002: Each execution step maps to exactly one agent
INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
INV-AGENT-004: OC is read-only; no agent control actions
INV-AGENT-005: Missing state must be explicit (no inference)

TRACE INVARIANTS (PAC-009):
INV-TRACE-001: Every settlement must trace to exactly one PDO
INV-TRACE-002: Every agent action must reference PAC + PDO
INV-TRACE-003: Ledger hash links all phases (decision → execution → settlement)
INV-TRACE-004: OC renders full chain without inference
INV-TRACE-005: Missing links are explicit and non-silent
"""

from core.execution.agent_events import (
    AgentActivationEvent,
    AgentExecutionStateEvent,
    AgentState,
    emit_agent_activation,
    emit_agent_state_change,
)
from core.execution.execution_ledger import (
    ExecutionLedger,
    ExecutionLedgerEntry,
    get_execution_ledger,
)
from core.execution.trace_registry import (
    TraceDomain,
    TraceLink,
    TraceLinkType,
    TraceRegistry,
    TraceInvariantViolation,
    get_trace_registry,
    reset_trace_registry,
    register_pdo_to_decision,
    register_decision_to_execution,
    register_execution_to_settlement,
    register_settlement_to_ledger,
)

__all__ = [
    # Agent events
    "AgentActivationEvent",
    "AgentExecutionStateEvent",
    "AgentState",
    "emit_agent_activation",
    "emit_agent_state_change",
    # Execution ledger
    "ExecutionLedger",
    "ExecutionLedgerEntry",
    "get_execution_ledger",
    # Trace registry (PAC-009)
    "TraceDomain",
    "TraceLink",
    "TraceLinkType",
    "TraceRegistry",
    "TraceInvariantViolation",
    "get_trace_registry",
    "reset_trace_registry",
    "register_pdo_to_decision",
    "register_decision_to_execution",
    "register_execution_to_settlement",
    "register_settlement_to_ledger",
]
