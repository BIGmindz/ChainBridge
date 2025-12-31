"""
ChainBridge Orchestration Engine
================================

PAC-Governed, PDO-Canonical Orchestration Runtime

This module implements the deterministic orchestration engine that executes
PAG-01 → PAG-07 gates with visible runtime behavior and halt-on-failure semantics.

Canon Locks:
    - PDO = Proof → Decision → Outcome
    - Sequential, non-skippable execution
    - Explicit PASS / FAIL at every gate

Governance: GOLD STANDARD
Failure Discipline: FAIL-CLOSED
"""

from .gate import Gate, GateStatus, GateResult
from .engine import OrchestrationEngine
from .events import EventEmitter, GateEvent, EventType

__all__ = [
    "Gate",
    "GateStatus",
    "GateResult",
    "OrchestrationEngine",
    "EventEmitter",
    "GateEvent",
    "EventType",
]

__version__ = "1.0.0"
__schema__ = "CHAINBRIDGE_PAC_SCHEMA v1.0.0"
