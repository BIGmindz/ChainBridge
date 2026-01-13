"""
OCC Governance Integration Package

This package binds the full-swarm governance doctrine into the OCC backend,
providing enforcement, API exposure, and operator approval gates.

DOCTRINE REFERENCE: DOCTRINE-FULL-SWARM-EXECUTION-001
PAC REFERENCE: PAC-JEFFREY-OCC-GOVERNANCE-INTEGRATION-01
"""

from .doctrine_enforcer import (
    DoctrineEnforcer,
    OCCGovernanceGate,
    GovernanceContext,
    EnforcementResult,
    GovernanceTier,
    EnforcementMode,
    ActionStatus,
    get_enforcer,
    get_gate
)

__all__ = [
    "DoctrineEnforcer",
    "OCCGovernanceGate",
    "GovernanceContext",
    "EnforcementResult",
    "GovernanceTier",
    "EnforcementMode",
    "ActionStatus",
    "get_enforcer",
    "get_gate"
]

__version__ = "1.0.0"
__pac_reference__ = "PAC-JEFFREY-OCC-GOVERNANCE-INTEGRATION-01"
