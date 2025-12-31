"""
PAG Gates Package
=================

Individual gate implementations for PAG-01 through PAG-07.

PDO Canon: Proof → Decision → Outcome
Governance: GOLD STANDARD
"""

from .pag01_agent import AgentActivationGate
from .pag02_runtime import RuntimeActivationGate
from .pag03_lane import ExecutionLaneGate
from .pag04_governance import GovernanceModeGate
from .pag05_review import ReviewGate
from .pag06_payload import PayloadGate
from .pag07_attestation import AttestationGate

__all__ = [
    "AgentActivationGate",
    "RuntimeActivationGate",
    "ExecutionLaneGate",
    "GovernanceModeGate",
    "ReviewGate",
    "PayloadGate",
    "AttestationGate",
]


def create_standard_gates() -> list:
    """
    Create the standard PAG-01 through PAG-07 gate sequence.
    
    Returns:
        List of gates in execution order
    """
    return [
        AgentActivationGate(),
        RuntimeActivationGate(),
        ExecutionLaneGate(),
        GovernanceModeGate(),
        ReviewGate(),
        PayloadGate(),
        AttestationGate(),
    ]
