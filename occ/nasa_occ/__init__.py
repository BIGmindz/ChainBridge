"""
NASA-Grade Operator Control Console (OCC)
PAC-JEFFREY-OCC-UI-NASA-001 | Safety-Critical UI Replacement

GOVERNANCE_TIER: LAW
DRIFT_TOLERANCE: ZERO
FAIL_CLOSED: true

This module provides mission-control grade operator interfaces
with deterministic rendering, SCRAM coupling, and PDO truth binding.
"""

from occ.nasa_occ.mission_control import (
    MissionControlOCC,
    ControlSurface,
    ControlPanel,
    StatusIndicator,
    OperatorStation,
    OCCConfiguration,
)

from occ.nasa_occ.pdo_binding import (
    PDOStateGraph,
    UIStateBinding,
    TruthSource,
)

from occ.nasa_occ.operator_primitives import (
    OperatorConfirmation,
    RollbackPrimitive,
    ActionAuthorization,
)

from occ.nasa_occ.scram_coupling import (
    SCRAMUIController,
    UIHaltState,
)

__all__ = [
    "MissionControlOCC",
    "ControlSurface",
    "ControlPanel",
    "StatusIndicator",
    "OperatorStation",
    "OCCConfiguration",
    "PDOStateGraph",
    "UIStateBinding",
    "TruthSource",
    "OperatorConfirmation",
    "RollbackPrimitive",
    "ActionAuthorization",
    "SCRAMUIController",
    "UIHaltState",
]
