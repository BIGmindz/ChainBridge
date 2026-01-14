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
- SovereignCommandCanvas: Visual Swarm Builder (PAC-CANVAS-DEPLOY-39)
- AgentForge: Draggable agent roster
- LogicCanvas: Node-based workflow editor
- StrikeConsole: Deployment execution

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY
Epoch: EPOCH_001
PAC: PAC-OCC-COMMAND-34, PAC-CANVAS-DEPLOY-39
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

# Canvas exports
from occ.command_canvas import (
    SovereignCommandCanvas,
    AgentForge,
    LogicCanvas,
    StrikeConsole,
    LogicPreFlight,
    SwarmAgent,
    CanvasNode,
    CanvasConnection,
    SwarmDeployment,
    BinaryReasonProof,
    AgentStatus,
    NodeType,
    ConnectionType,
    SwarmState,
    EnclaveLockReason,
    launch_command_canvas,
    CANVAS_VERSION,
    MAX_AGENTS_STANDARD,
    MAX_AGENTS_CLUSTERED,
)

__all__ += [
    # Canvas components
    "SovereignCommandCanvas",
    "AgentForge",
    "LogicCanvas",
    "StrikeConsole",
    "LogicPreFlight",
    
    # Canvas data classes
    "SwarmAgent",
    "CanvasNode",
    "CanvasConnection",
    "SwarmDeployment",
    "BinaryReasonProof",
    
    # Canvas enums
    "AgentStatus",
    "NodeType",
    "ConnectionType",
    "SwarmState",
    "EnclaveLockReason",
    
    # Canvas entry point
    "launch_command_canvas",
    
    # Canvas constants
    "CANVAS_VERSION",
    "MAX_AGENTS_STANDARD",
    "MAX_AGENTS_CLUSTERED",
]
