"""
OCC Package - Operators Control in Command
ChainBridge Sovereign Systems

The "War Room" interface for the Founding CTO/Architect.
Root-level monitoring and control of the Sovereign Mesh.

Components:
- OCCCommandCenter: Master orchestrator
- QuadLaneMonitor: Real-time execution lane visualization
- GateHeatmap: 10,000 Law-Gates status grid
- PDOTicker: Proof → Decision → Outcome feed
- ARRCounter: Live financial odometer
- KillSwitch: Hardware-level emergency stop
- SovereignKeyManager: Architect authentication

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY
Epoch: EPOCH_001
PAC: PAC-OCC-COMMAND-34
"""

from occ.command_center import (
    # Main orchestrator
    OCCCommandCenter,
    
    # Monitors
    QuadLaneMonitor,
    GateHeatmap,
    PDOTicker,
    ARRCounter,
    
    # Security
    SovereignKeyManager,
    SovereignMasterKey,
    KillSwitch,
    KillSwitchState,
    
    # Data classes
    ExecutionLane,
    PDOUnit,
    OCCAlert,
    
    # Enums
    LaneStatus,
    GateStatus,
    AlertLevel,
    
    # Entry point
    launch_occ_command_center,
    
    # Constants
    GENESIS_ANCHOR,
    GENESIS_BLOCK_HASH,
    EPOCH_001,
    OCC_VERSION,
    CURRENT_ARR_USD,
    TOTAL_GATES,
    GATE_GRID_SIZE,
)

__all__ = [
    # Main orchestrator
    "OCCCommandCenter",
    
    # Monitors
    "QuadLaneMonitor",
    "GateHeatmap",
    "PDOTicker",
    "ARRCounter",
    
    # Security
    "SovereignKeyManager",
    "SovereignMasterKey",
    "KillSwitch",
    "KillSwitchState",
    
    # Data classes
    "ExecutionLane",
    "PDOUnit",
    "OCCAlert",
    
    # Enums
    "LaneStatus",
    "GateStatus",
    "AlertLevel",
    
    # Entry point
    "launch_occ_command_center",
    
    # Constants
    "GENESIS_ANCHOR",
    "GENESIS_BLOCK_HASH",
    "EPOCH_001",
    "OCC_VERSION",
    "CURRENT_ARR_USD",
    "TOTAL_GATES",
    "GATE_GRID_SIZE",
]
