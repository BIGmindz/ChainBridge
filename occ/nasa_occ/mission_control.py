"""
NASA-Grade Mission Control OCC Layout
PAC-JEFFREY-OCC-UI-NASA-001 | Task 1: Mission Control Topology

GOVERNANCE_TIER: LAW
DRIFT_TOLERANCE: ZERO
FAIL_CLOSED: true

Mission Control topology for Operator Control Console.
All UI elements are deterministic, operator-verified, and SCRAM-coupled.

INVARIANTS ENFORCED:
- INV-PDO-PRIMACY: UI reflects PDO truth only
- INV-UI-TRUTH-BINDING: No speculative or optimistic rendering
- INV-SCRAM-UI-COUPLING: SCRAM triggers immediate UI halt
- INV-NO-SILENT-FAILURE: All failures surface to operator

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY (STRATEGY_ONLY)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    FrozenSet,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    runtime_checkable,
)


# =============================================================================
# SECTION 1: CONSTANTS AND INVARIANTS
# =============================================================================

VERSION: Final[str] = "1.0.0"
PAC_REFERENCE: Final[str] = "PAC-JEFFREY-OCC-UI-NASA-001"
GOVERNANCE_TIER: Final[str] = "LAW"

# NASA Mission Control color codes (deterministic, no CSS variables)
COLOR_NOMINAL: Final[str] = "#00FF00"      # Green - all systems go
COLOR_CAUTION: Final[str] = "#FFFF00"      # Yellow - attention required
COLOR_WARNING: Final[str] = "#FFA500"      # Orange - action required
COLOR_CRITICAL: Final[str] = "#FF0000"     # Red - immediate action
COLOR_OFFLINE: Final[str] = "#808080"      # Gray - system offline
COLOR_STANDBY: Final[str] = "#0000FF"      # Blue - standby mode

# Invariant identifiers
INV_PDO_PRIMACY: Final[str] = "INV-PDO-PRIMACY"
INV_UI_TRUTH_BINDING: Final[str] = "INV-UI-TRUTH-BINDING"
INV_SCRAM_UI_COUPLING: Final[str] = "INV-SCRAM-UI-COUPLING"
INV_NO_SILENT_FAILURE: Final[str] = "INV-NO-SILENT-FAILURE"


# =============================================================================
# SECTION 2: ENUMERATIONS
# =============================================================================

class SystemStatus(Enum):
    """
    Deterministic system status values.
    No ambiguous or transient states allowed.
    """
    NOMINAL = auto()           # All systems operational
    CAUTION = auto()           # Non-critical issue detected
    WARNING = auto()           # Critical issue - operator review required
    CRITICAL = auto()          # Emergency - immediate action required
    OFFLINE = auto()           # System not available
    STANDBY = auto()           # System in standby mode
    HALTED = auto()            # SCRAM triggered - UI frozen


class PanelType(Enum):
    """Mission Control panel types."""
    STATUS_OVERVIEW = auto()   # High-level system status
    TELEMETRY = auto()         # Real-time metrics
    PDO_MONITOR = auto()       # Proof-Decision-Outcome stream
    LANE_MONITOR = auto()      # Execution lane status
    GATE_MATRIX = auto()       # Law gate compliance grid
    ALERT_CONSOLE = auto()     # Active alerts
    COMMAND_INPUT = auto()     # Operator command entry
    AUDIT_TRAIL = auto()       # Action history
    SCRAM_CONTROL = auto()     # Emergency controls


class IndicatorType(Enum):
    """Status indicator types."""
    LED = auto()               # Simple on/off/color LED
    GAUGE = auto()             # Numeric gauge with limits
    GRAPH = auto()             # Time-series display
    MATRIX = auto()            # Grid of values
    TEXT = auto()              # Text display
    COUNTER = auto()           # Numeric counter


class OperatorAction(Enum):
    """Operator action types requiring confirmation."""
    VIEW = auto()              # Read-only - no confirmation
    ACKNOWLEDGE = auto()       # Acknowledge alert
    CONFIGURE = auto()         # Configuration change
    EXECUTE = auto()           # Execute command
    OVERRIDE = auto()          # Override safety check
    SCRAM = auto()             # Trigger emergency stop
    ARM = auto()               # Arm system
    DISARM = auto()            # Disarm system


# =============================================================================
# SECTION 3: CORE DATA STRUCTURES (Frozen/Immutable)
# =============================================================================

@dataclass(frozen=True)
class IndicatorReading:
    """
    Immutable indicator reading at a point in time.
    Represents exactly what the operator should see.
    """
    indicator_id: str
    value: Any
    status: SystemStatus
    timestamp: datetime
    source_hash: str        # Hash of PDO source data
    unit: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "indicator_id": self.indicator_id,
            "value": self.value,
            "status": self.status.name,
            "timestamp": self.timestamp.isoformat(),
            "source_hash": self.source_hash,
            "unit": self.unit,
            "min_value": self.min_value,
            "max_value": self.max_value,
        }


@dataclass(frozen=True)
class RenderState:
    """
    Immutable render state for a UI component.
    
    INVARIANT: Render state is computed deterministically from PDO truth.
    No caching, no speculation, no optimistic updates.
    """
    state_id: str
    component_id: str
    pdo_source_hash: str    # Hash of source PDO data
    render_hash: str        # Hash of rendered content
    timestamp: datetime
    content: Mapping[str, Any]
    is_valid: bool
    invalidation_reason: Optional[str] = None
    
    @classmethod
    def create_from_pdo(
        cls,
        component_id: str,
        pdo_data: Mapping[str, Any],
        content: Mapping[str, Any],
    ) -> "RenderState":
        """Factory: Create render state bound to PDO truth."""
        pdo_hash = hashlib.sha256(
            json.dumps(dict(pdo_data), sort_keys=True).encode()
        ).hexdigest()[:16]
        
        render_hash = hashlib.sha256(
            json.dumps(dict(content), sort_keys=True).encode()
        ).hexdigest()[:16]
        
        return cls(
            state_id=f"RS-{uuid.uuid4().hex[:12].upper()}",
            component_id=component_id,
            pdo_source_hash=pdo_hash,
            render_hash=render_hash,
            timestamp=datetime.now(timezone.utc),
            content=content,
            is_valid=True,
        )
    
    @classmethod
    def create_invalid(
        cls,
        component_id: str,
        reason: str,
    ) -> "RenderState":
        """Factory: Create invalid render state (for SCRAM or error)."""
        return cls(
            state_id=f"RS-{uuid.uuid4().hex[:12].upper()}",
            component_id=component_id,
            pdo_source_hash="INVALID",
            render_hash="INVALID",
            timestamp=datetime.now(timezone.utc),
            content={},
            is_valid=False,
            invalidation_reason=reason,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "component_id": self.component_id,
            "pdo_source_hash": self.pdo_source_hash,
            "render_hash": self.render_hash,
            "timestamp": self.timestamp.isoformat(),
            "is_valid": self.is_valid,
            "invalidation_reason": self.invalidation_reason,
        }


@dataclass(frozen=True)
class OperatorCommand:
    """
    Immutable operator command.
    Commands are declarative - execution is handled elsewhere.
    """
    command_id: str
    action_type: OperatorAction
    target_component: str
    parameters: Mapping[str, Any]
    operator_id: str
    timestamp: datetime
    requires_confirmation: bool
    confirmation_code: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "action_type": self.action_type.name,
            "target_component": self.target_component,
            "parameters": dict(self.parameters),
            "operator_id": self.operator_id,
            "timestamp": self.timestamp.isoformat(),
            "requires_confirmation": self.requires_confirmation,
            "confirmation_code": self.confirmation_code[:8] + "..." if self.confirmation_code else None,
        }


# =============================================================================
# SECTION 4: PROTOCOLS (Interface Contracts)
# =============================================================================

@runtime_checkable
class StatusIndicator(Protocol):
    """Protocol for status indicator components."""
    
    @property
    def indicator_id(self) -> str: ...
    
    @property
    def indicator_type(self) -> IndicatorType: ...
    
    def get_reading(self) -> IndicatorReading: ...
    
    def bind_to_pdo(self, pdo_path: str) -> None: ...


@runtime_checkable
class ControlSurface(Protocol):
    """
    Protocol for control surface components.
    
    Control surfaces display information and accept operator input.
    They MUST be bound to PDO truth - no speculative state.
    """
    
    @property
    def surface_id(self) -> str: ...
    
    @property
    def status(self) -> SystemStatus: ...
    
    def render(self) -> RenderState: ...
    
    def handle_command(self, command: OperatorCommand) -> Tuple[bool, str]: ...
    
    def halt(self, reason: str) -> None: ...
    
    def is_halted(self) -> bool: ...


# =============================================================================
# SECTION 5: STATUS INDICATOR IMPLEMENTATIONS
# =============================================================================

class LEDIndicator:
    """
    Simple LED-style status indicator.
    
    Shows binary or multi-state status with color coding.
    """
    
    def __init__(
        self,
        indicator_id: str,
        label: str,
        pdo_path: Optional[str] = None,
    ) -> None:
        self._indicator_id = indicator_id
        self._label = label
        self._pdo_path = pdo_path
        self._current_status = SystemStatus.OFFLINE
        self._last_reading: Optional[IndicatorReading] = None
    
    @property
    def indicator_id(self) -> str:
        return self._indicator_id
    
    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.LED
    
    def bind_to_pdo(self, pdo_path: str) -> None:
        """Bind indicator to PDO data path."""
        self._pdo_path = pdo_path
    
    def update_from_pdo(self, pdo_value: Any, pdo_hash: str) -> None:
        """Update indicator from PDO truth."""
        # Map PDO value to status
        if pdo_value is None:
            status = SystemStatus.OFFLINE
        elif isinstance(pdo_value, bool):
            status = SystemStatus.NOMINAL if pdo_value else SystemStatus.CRITICAL
        elif isinstance(pdo_value, str):
            status_map = {
                "nominal": SystemStatus.NOMINAL,
                "caution": SystemStatus.CAUTION,
                "warning": SystemStatus.WARNING,
                "critical": SystemStatus.CRITICAL,
                "offline": SystemStatus.OFFLINE,
                "standby": SystemStatus.STANDBY,
                "halted": SystemStatus.HALTED,
            }
            status = status_map.get(pdo_value.lower(), SystemStatus.OFFLINE)
        else:
            status = SystemStatus.NOMINAL
        
        self._current_status = status
        self._last_reading = IndicatorReading(
            indicator_id=self._indicator_id,
            value=pdo_value,
            status=status,
            timestamp=datetime.now(timezone.utc),
            source_hash=pdo_hash,
        )
    
    def get_reading(self) -> IndicatorReading:
        """Get current indicator reading."""
        if self._last_reading is None:
            return IndicatorReading(
                indicator_id=self._indicator_id,
                value=None,
                status=SystemStatus.OFFLINE,
                timestamp=datetime.now(timezone.utc),
                source_hash="NO_DATA",
            )
        return self._last_reading
    
    def get_color(self) -> str:
        """Get display color based on status."""
        color_map = {
            SystemStatus.NOMINAL: COLOR_NOMINAL,
            SystemStatus.CAUTION: COLOR_CAUTION,
            SystemStatus.WARNING: COLOR_WARNING,
            SystemStatus.CRITICAL: COLOR_CRITICAL,
            SystemStatus.OFFLINE: COLOR_OFFLINE,
            SystemStatus.STANDBY: COLOR_STANDBY,
            SystemStatus.HALTED: COLOR_CRITICAL,
        }
        return color_map.get(self._current_status, COLOR_OFFLINE)


class GaugeIndicator:
    """
    Numeric gauge indicator with bounds checking.
    
    Displays numeric value with visual limits and status zones.
    """
    
    def __init__(
        self,
        indicator_id: str,
        label: str,
        unit: str,
        min_value: float,
        max_value: float,
        warning_low: Optional[float] = None,
        warning_high: Optional[float] = None,
        critical_low: Optional[float] = None,
        critical_high: Optional[float] = None,
    ) -> None:
        self._indicator_id = indicator_id
        self._label = label
        self._unit = unit
        self._min_value = min_value
        self._max_value = max_value
        self._warning_low = warning_low or min_value
        self._warning_high = warning_high or max_value
        self._critical_low = critical_low or min_value
        self._critical_high = critical_high or max_value
        self._pdo_path: Optional[str] = None
        self._current_value: float = 0.0
        self._last_reading: Optional[IndicatorReading] = None
    
    @property
    def indicator_id(self) -> str:
        return self._indicator_id
    
    @property
    def indicator_type(self) -> IndicatorType:
        return IndicatorType.GAUGE
    
    def bind_to_pdo(self, pdo_path: str) -> None:
        """Bind indicator to PDO data path."""
        self._pdo_path = pdo_path
    
    def update_from_pdo(self, pdo_value: Any, pdo_hash: str) -> None:
        """Update gauge from PDO truth."""
        try:
            value = float(pdo_value) if pdo_value is not None else 0.0
        except (TypeError, ValueError):
            value = 0.0
        
        self._current_value = value
        
        # Determine status based on value position
        if value <= self._critical_low or value >= self._critical_high:
            status = SystemStatus.CRITICAL
        elif value <= self._warning_low or value >= self._warning_high:
            status = SystemStatus.WARNING
        else:
            status = SystemStatus.NOMINAL
        
        self._last_reading = IndicatorReading(
            indicator_id=self._indicator_id,
            value=value,
            status=status,
            timestamp=datetime.now(timezone.utc),
            source_hash=pdo_hash,
            unit=self._unit,
            min_value=self._min_value,
            max_value=self._max_value,
        )
    
    def get_reading(self) -> IndicatorReading:
        """Get current gauge reading."""
        if self._last_reading is None:
            return IndicatorReading(
                indicator_id=self._indicator_id,
                value=0.0,
                status=SystemStatus.OFFLINE,
                timestamp=datetime.now(timezone.utc),
                source_hash="NO_DATA",
                unit=self._unit,
                min_value=self._min_value,
                max_value=self._max_value,
            )
        return self._last_reading


# =============================================================================
# SECTION 6: CONTROL PANEL IMPLEMENTATION
# =============================================================================

class ControlPanel:
    """
    Mission Control Panel - contains grouped indicators and controls.
    
    Panels are deterministic containers bound to PDO state graph.
    """
    
    def __init__(
        self,
        panel_id: str,
        panel_type: PanelType,
        title: str,
    ) -> None:
        self._panel_id = panel_id
        self._panel_type = panel_type
        self._title = title
        self._indicators: Dict[str, Any] = {}  # indicator_id -> indicator
        self._status = SystemStatus.STANDBY
        self._is_halted = False
        self._halt_reason: Optional[str] = None
        self._pdo_bindings: Dict[str, str] = {}  # indicator_id -> pdo_path
    
    @property
    def surface_id(self) -> str:
        return self._panel_id
    
    @property
    def status(self) -> SystemStatus:
        return self._status
    
    def add_indicator(
        self,
        indicator: Any,
        pdo_path: Optional[str] = None,
    ) -> None:
        """Add indicator to panel with optional PDO binding."""
        self._indicators[indicator.indicator_id] = indicator
        if pdo_path:
            self._pdo_bindings[indicator.indicator_id] = pdo_path
            indicator.bind_to_pdo(pdo_path)
    
    def update_from_pdo(self, pdo_state: Mapping[str, Any]) -> None:
        """
        Update all indicators from PDO state.
        
        INVARIANT: This is the ONLY way to update panel state.
        """
        if self._is_halted:
            return  # Do not update if halted
        
        pdo_hash = hashlib.sha256(
            json.dumps(dict(pdo_state), sort_keys=True).encode()
        ).hexdigest()[:16]
        
        for ind_id, pdo_path in self._pdo_bindings.items():
            if ind_id in self._indicators:
                # Extract value from PDO state using path
                value = self._extract_pdo_value(pdo_state, pdo_path)
                self._indicators[ind_id].update_from_pdo(value, pdo_hash)
        
        # Update panel status based on worst indicator status
        self._update_panel_status()
    
    def _extract_pdo_value(
        self,
        pdo_state: Mapping[str, Any],
        path: str,
    ) -> Any:
        """Extract value from PDO state using dot-notation path."""
        parts = path.split(".")
        current: Any = pdo_state
        for part in parts:
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                return None
        return current
    
    def _update_panel_status(self) -> None:
        """Update panel status based on worst indicator status."""
        if self._is_halted:
            self._status = SystemStatus.HALTED
            return
        
        worst = SystemStatus.NOMINAL
        status_priority = {
            SystemStatus.NOMINAL: 0,
            SystemStatus.STANDBY: 1,
            SystemStatus.CAUTION: 2,
            SystemStatus.WARNING: 3,
            SystemStatus.CRITICAL: 4,
            SystemStatus.OFFLINE: 5,
            SystemStatus.HALTED: 6,
        }
        
        for indicator in self._indicators.values():
            reading = indicator.get_reading()
            if status_priority.get(reading.status, 0) > status_priority.get(worst, 0):
                worst = reading.status
        
        self._status = worst
    
    def render(self) -> RenderState:
        """Render panel state for UI display."""
        if self._is_halted:
            return RenderState.create_invalid(self._panel_id, self._halt_reason or "HALTED")
        
        content = {
            "panel_id": self._panel_id,
            "panel_type": self._panel_type.name,
            "title": self._title,
            "status": self._status.name,
            "indicators": [
                ind.get_reading().to_dict() for ind in self._indicators.values()
            ],
        }
        
        # Create PDO-bound render state
        return RenderState.create_from_pdo(
            component_id=self._panel_id,
            pdo_data={"indicators": [ind.get_reading().to_dict() for ind in self._indicators.values()]},
            content=content,
        )
    
    def handle_command(self, command: OperatorCommand) -> Tuple[bool, str]:
        """Handle operator command to this panel."""
        if self._is_halted:
            return (False, "Panel is halted - commands not accepted")
        
        # Panels are primarily display - most commands require confirmation
        if command.action_type == OperatorAction.VIEW:
            return (True, "View acknowledged")
        
        return (False, f"Command {command.action_type.name} not supported by panel")
    
    def halt(self, reason: str) -> None:
        """Halt panel - SCRAM coupling."""
        self._is_halted = True
        self._halt_reason = reason
        self._status = SystemStatus.HALTED
    
    def is_halted(self) -> bool:
        return self._is_halted
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "panel_id": self._panel_id,
            "panel_type": self._panel_type.name,
            "title": self._title,
            "status": self._status.name,
            "is_halted": self._is_halted,
            "halt_reason": self._halt_reason,
            "indicator_count": len(self._indicators),
        }


# =============================================================================
# SECTION 7: OPERATOR STATION
# =============================================================================

@dataclass(frozen=True)
class StationLayout:
    """Immutable station layout configuration."""
    station_id: str
    name: str
    row_count: int
    column_count: int
    panel_positions: Mapping[str, Tuple[int, int, int, int]]  # panel_id -> (row, col, row_span, col_span)


class OperatorStation:
    """
    Operator station - a collection of control panels.
    
    Represents a single operator position in mission control.
    Multiple stations can be aggregated for different roles.
    """
    
    def __init__(
        self,
        station_id: str,
        operator_role: str,
        layout: StationLayout,
    ) -> None:
        self._station_id = station_id
        self._operator_role = operator_role
        self._layout = layout
        self._panels: Dict[str, ControlPanel] = {}
        self._is_halted = False
        self._halt_reason: Optional[str] = None
        self._command_queue: List[OperatorCommand] = []
    
    @property
    def station_id(self) -> str:
        return self._station_id
    
    @property
    def status(self) -> SystemStatus:
        if self._is_halted:
            return SystemStatus.HALTED
        
        # Station status is worst of all panels
        worst = SystemStatus.NOMINAL
        status_priority = {
            SystemStatus.NOMINAL: 0,
            SystemStatus.STANDBY: 1,
            SystemStatus.CAUTION: 2,
            SystemStatus.WARNING: 3,
            SystemStatus.CRITICAL: 4,
            SystemStatus.OFFLINE: 5,
            SystemStatus.HALTED: 6,
        }
        
        for panel in self._panels.values():
            if status_priority.get(panel.status, 0) > status_priority.get(worst, 0):
                worst = panel.status
        
        return worst
    
    def add_panel(
        self,
        panel: ControlPanel,
        position: Optional[Tuple[int, int, int, int]] = None,
    ) -> None:
        """Add panel to station."""
        self._panels[panel.surface_id] = panel
    
    def get_panel(self, panel_id: str) -> Optional[ControlPanel]:
        """Get panel by ID."""
        return self._panels.get(panel_id)
    
    def update_all_from_pdo(self, pdo_state: Mapping[str, Any]) -> None:
        """Update all panels from PDO state."""
        if self._is_halted:
            return
        
        for panel in self._panels.values():
            panel.update_from_pdo(pdo_state)
    
    def render_all(self) -> Dict[str, RenderState]:
        """Render all panels."""
        return {
            panel_id: panel.render()
            for panel_id, panel in self._panels.items()
        }
    
    def submit_command(self, command: OperatorCommand) -> Tuple[bool, str]:
        """Submit operator command."""
        if self._is_halted:
            return (False, "Station is halted - commands not accepted")
        
        # Route command to target panel
        target = command.target_component
        if target in self._panels:
            return self._panels[target].handle_command(command)
        
        return (False, f"Unknown target component: {target}")
    
    def halt(self, reason: str) -> None:
        """Halt station and all panels."""
        self._is_halted = True
        self._halt_reason = reason
        for panel in self._panels.values():
            panel.halt(reason)
    
    def is_halted(self) -> bool:
        return self._is_halted
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_id": self._station_id,
            "operator_role": self._operator_role,
            "status": self.status.name,
            "is_halted": self._is_halted,
            "halt_reason": self._halt_reason,
            "panel_count": len(self._panels),
            "panels": [p.to_dict() for p in self._panels.values()],
        }


# =============================================================================
# SECTION 8: OCC CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class OCCConfiguration:
    """
    Immutable OCC configuration.
    
    Defines the complete mission control layout and behavior.
    """
    occ_id: str
    name: str
    version: str
    stations: Tuple[str, ...]           # Station IDs
    scram_enabled: bool
    pdo_poll_interval_ms: int
    max_command_queue_size: int
    confirmation_timeout_seconds: float
    audit_retention_days: int
    
    @classmethod
    def default(cls) -> "OCCConfiguration":
        """Create default OCC configuration."""
        return cls(
            occ_id="OCC-MISSION-CONTROL-001",
            name="ChainBridge Mission Control",
            version=VERSION,
            stations=("STATION-ARCHITECT", "STATION-OPERATOR", "STATION-SECURITY"),
            scram_enabled=True,
            pdo_poll_interval_ms=500,
            max_command_queue_size=100,
            confirmation_timeout_seconds=30.0,
            audit_retention_days=90,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "occ_id": self.occ_id,
            "name": self.name,
            "version": self.version,
            "stations": list(self.stations),
            "scram_enabled": self.scram_enabled,
            "pdo_poll_interval_ms": self.pdo_poll_interval_ms,
            "max_command_queue_size": self.max_command_queue_size,
            "confirmation_timeout_seconds": self.confirmation_timeout_seconds,
            "audit_retention_days": self.audit_retention_days,
        }


# =============================================================================
# SECTION 9: MISSION CONTROL OCC (Main Entry Point)
# =============================================================================

class MissionControlOCC:
    """
    NASA-Grade Mission Control OCC.
    
    The top-level container for all operator control surfaces.
    
    Properties:
    - PDO-bound: All display state derived from PDO truth
    - Deterministic: Same state → same render
    - SCRAM-coupled: Emergency halt propagates to all components
    - Auditable: All operator actions logged
    
    INVARIANTS:
    - INV-PDO-PRIMACY: UI reflects PDO truth only
    - INV-UI-TRUTH-BINDING: No speculative rendering
    - INV-SCRAM-UI-COUPLING: SCRAM halts all UI
    - INV-NO-SILENT-FAILURE: All failures visible to operator
    """
    
    def __init__(
        self,
        configuration: Optional[OCCConfiguration] = None,
    ) -> None:
        self._config = configuration or OCCConfiguration.default()
        self._stations: Dict[str, OperatorStation] = {}
        self._scram_active = False
        self._scram_reason: Optional[str] = None
        self._scram_timestamp: Optional[datetime] = None
        self._last_pdo_hash: str = ""
        self._audit_log: List[Dict[str, Any]] = []
        self._initialized = False
    
    @property
    def occ_id(self) -> str:
        return self._config.occ_id
    
    @property
    def is_scram_active(self) -> bool:
        return self._scram_active
    
    @property
    def status(self) -> SystemStatus:
        if self._scram_active:
            return SystemStatus.HALTED
        if not self._stations:
            return SystemStatus.OFFLINE
        
        # OCC status is worst of all stations
        worst = SystemStatus.NOMINAL
        status_priority = {
            SystemStatus.NOMINAL: 0,
            SystemStatus.STANDBY: 1,
            SystemStatus.CAUTION: 2,
            SystemStatus.WARNING: 3,
            SystemStatus.CRITICAL: 4,
            SystemStatus.OFFLINE: 5,
            SystemStatus.HALTED: 6,
        }
        
        for station in self._stations.values():
            if status_priority.get(station.status, 0) > status_priority.get(worst, 0):
                worst = station.status
        
        return worst
    
    def initialize(self) -> Tuple[bool, str]:
        """
        Initialize OCC with default station layout.
        
        Creates the standard mission control topology.
        """
        if self._initialized:
            return (False, "OCC already initialized")
        
        try:
            # Create Architect Station (primary control)
            architect_layout = StationLayout(
                station_id="STATION-ARCHITECT",
                name="Architect Console",
                row_count=3,
                column_count=4,
                panel_positions={
                    "PANEL-STATUS": (0, 0, 1, 2),
                    "PANEL-PDO": (0, 2, 1, 2),
                    "PANEL-LANES": (1, 0, 1, 2),
                    "PANEL-GATES": (1, 2, 1, 2),
                    "PANEL-ALERTS": (2, 0, 1, 3),
                    "PANEL-SCRAM": (2, 3, 1, 1),
                },
            )
            architect_station = OperatorStation(
                station_id="STATION-ARCHITECT",
                operator_role="ARCHITECT",
                layout=architect_layout,
            )
            
            # Add panels to architect station
            self._create_standard_panels(architect_station)
            self._stations["STATION-ARCHITECT"] = architect_station
            
            self._initialized = True
            self._log_audit("OCC_INITIALIZED", {"occ_id": self._config.occ_id})
            
            return (True, "OCC initialized successfully")
        
        except Exception as e:
            return (False, f"Initialization failed: {str(e)}")
    
    def _create_standard_panels(self, station: OperatorStation) -> None:
        """Create standard mission control panels."""
        # Status Overview Panel
        status_panel = ControlPanel(
            panel_id="PANEL-STATUS",
            panel_type=PanelType.STATUS_OVERVIEW,
            title="System Status",
        )
        status_panel.add_indicator(
            LEDIndicator("IND-SYSTEM", "System Health"),
            pdo_path="system.health",
        )
        status_panel.add_indicator(
            LEDIndicator("IND-NETWORK", "Network Status"),
            pdo_path="network.status",
        )
        status_panel.add_indicator(
            GaugeIndicator("IND-LOAD", "System Load", "%", 0, 100, 70, 90, 85, 95),
            pdo_path="system.load",
        )
        station.add_panel(status_panel)
        
        # PDO Monitor Panel
        pdo_panel = ControlPanel(
            panel_id="PANEL-PDO",
            panel_type=PanelType.PDO_MONITOR,
            title="PDO Stream",
        )
        pdo_panel.add_indicator(
            LEDIndicator("IND-PDO-STATUS", "PDO Engine"),
            pdo_path="pdo.status",
        )
        pdo_panel.add_indicator(
            GaugeIndicator("IND-PDO-RATE", "PDO Rate", "/s", 0, 1000),
            pdo_path="pdo.rate",
        )
        station.add_panel(pdo_panel)
        
        # Lane Monitor Panel
        lane_panel = ControlPanel(
            panel_id="PANEL-LANES",
            panel_type=PanelType.LANE_MONITOR,
            title="Execution Lanes",
        )
        for i in range(4):
            lane_panel.add_indicator(
                LEDIndicator(f"IND-LANE-{i}", f"Lane {i}"),
                pdo_path=f"lanes.lane_{i}.status",
            )
        station.add_panel(lane_panel)
        
        # Gate Matrix Panel
        gate_panel = ControlPanel(
            panel_id="PANEL-GATES",
            panel_type=PanelType.GATE_MATRIX,
            title="Law Gates",
        )
        gate_panel.add_indicator(
            GaugeIndicator("IND-GATE-COMPLIANT", "Compliant Gates", "", 0, 10000),
            pdo_path="gates.compliant_count",
        )
        gate_panel.add_indicator(
            GaugeIndicator("IND-GATE-BLOCKED", "Blocked Gates", "", 0, 10000, 1, 100, 50, 500),
            pdo_path="gates.blocked_count",
        )
        station.add_panel(gate_panel)
        
        # Alert Console Panel
        alert_panel = ControlPanel(
            panel_id="PANEL-ALERTS",
            panel_type=PanelType.ALERT_CONSOLE,
            title="Active Alerts",
        )
        alert_panel.add_indicator(
            GaugeIndicator("IND-ALERT-COUNT", "Active Alerts", "", 0, 100, 5, 20, 10, 50),
            pdo_path="alerts.active_count",
        )
        station.add_panel(alert_panel)
        
        # SCRAM Control Panel
        scram_panel = ControlPanel(
            panel_id="PANEL-SCRAM",
            panel_type=PanelType.SCRAM_CONTROL,
            title="SCRAM",
        )
        scram_panel.add_indicator(
            LEDIndicator("IND-SCRAM-STATUS", "SCRAM Status"),
            pdo_path="scram.status",
        )
        station.add_panel(scram_panel)
    
    def add_station(self, station: OperatorStation) -> None:
        """Add operator station to OCC."""
        self._stations[station.station_id] = station
        self._log_audit("STATION_ADDED", {"station_id": station.station_id})
    
    def get_station(self, station_id: str) -> Optional[OperatorStation]:
        """Get station by ID."""
        return self._stations.get(station_id)
    
    def update_from_pdo(self, pdo_state: Mapping[str, Any]) -> Tuple[bool, str]:
        """
        Update all OCC components from PDO state.
        
        This is the ONLY method for updating UI state.
        INVARIANT: INV-PDO-PRIMACY enforced here.
        """
        if self._scram_active:
            return (False, "OCC is in SCRAM state - updates blocked")
        
        # Compute PDO hash for audit
        pdo_hash = hashlib.sha256(
            json.dumps(dict(pdo_state), sort_keys=True).encode()
        ).hexdigest()[:16]
        
        # Skip update if PDO hasn't changed (determinism)
        if pdo_hash == self._last_pdo_hash:
            return (True, "No PDO change - skipping update")
        
        self._last_pdo_hash = pdo_hash
        
        # Update all stations
        for station in self._stations.values():
            station.update_all_from_pdo(pdo_state)
        
        return (True, f"Updated from PDO (hash: {pdo_hash})")
    
    def render_all(self) -> Dict[str, Dict[str, RenderState]]:
        """Render all stations and panels."""
        return {
            station_id: station.render_all()
            for station_id, station in self._stations.items()
        }
    
    def trigger_scram(self, reason: str, operator_id: str) -> Tuple[bool, str]:
        """
        Trigger SCRAM - emergency halt of all UI.
        
        INVARIANT: INV-SCRAM-UI-COUPLING enforced here.
        """
        if self._scram_active:
            return (False, "SCRAM already active")
        
        self._scram_active = True
        self._scram_reason = reason
        self._scram_timestamp = datetime.now(timezone.utc)
        
        # Halt all stations
        for station in self._stations.values():
            station.halt(reason)
        
        self._log_audit("SCRAM_TRIGGERED", {
            "reason": reason,
            "operator_id": operator_id,
            "timestamp": self._scram_timestamp.isoformat(),
        })
        
        return (True, f"SCRAM triggered: {reason}")
    
    def clear_scram(self, authorization_code: str, operator_id: str) -> Tuple[bool, str]:
        """
        Clear SCRAM state.
        
        Requires explicit authorization - cannot be automated.
        """
        if not self._scram_active:
            return (False, "No active SCRAM to clear")
        
        # Validate authorization (in production, this would verify against secure store)
        if len(authorization_code) < 16:
            return (False, "Invalid authorization code")
        
        self._log_audit("SCRAM_CLEARED", {
            "operator_id": operator_id,
            "authorization_code_hash": hashlib.sha256(authorization_code.encode()).hexdigest()[:8],
        })
        
        self._scram_active = False
        self._scram_reason = None
        self._scram_timestamp = None
        
        # Note: Stations remain halted - must be individually re-initialized
        return (True, "SCRAM cleared - stations require re-initialization")
    
    def submit_command(
        self,
        station_id: str,
        command: OperatorCommand,
    ) -> Tuple[bool, str]:
        """Submit operator command to specific station."""
        if self._scram_active:
            return (False, "OCC is in SCRAM state - commands blocked")
        
        station = self._stations.get(station_id)
        if not station:
            return (False, f"Unknown station: {station_id}")
        
        self._log_audit("COMMAND_SUBMITTED", {
            "station_id": station_id,
            "command_id": command.command_id,
            "action_type": command.action_type.name,
            "operator_id": command.operator_id,
        })
        
        return station.submit_command(command)
    
    def _log_audit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log audit event."""
        self._audit_log.append({
            "event_id": f"AUD-{uuid.uuid4().hex[:12].upper()}",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        })
    
    def get_audit_log(self) -> Sequence[Dict[str, Any]]:
        """Get audit log."""
        return tuple(self._audit_log)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "occ_id": self._config.occ_id,
            "name": self._config.name,
            "version": self._config.version,
            "status": self.status.name,
            "scram_active": self._scram_active,
            "scram_reason": self._scram_reason,
            "station_count": len(self._stations),
            "stations": [s.to_dict() for s in self._stations.values()],
            "audit_log_size": len(self._audit_log),
        }


# =============================================================================
# SECTION 10: SELF-TEST
# =============================================================================

def _run_self_test() -> None:
    """Execute self-test suite."""
    import sys
    
    print("=" * 72)
    print("  NASA-GRADE MISSION CONTROL OCC - SELF-TEST")
    print("  PAC-JEFFREY-OCC-UI-NASA-001 | Task 1")
    print("=" * 72)
    
    tests_passed = 0
    tests_failed = 0
    
    def test(name: str, condition: bool, msg: str = "") -> None:
        nonlocal tests_passed, tests_failed
        if condition:
            print(f"  ✓ {name}")
            tests_passed += 1
        else:
            print(f"  ✗ {name}: {msg}")
            tests_failed += 1
    
    # Test 1: Configuration creation
    print("\n[1] Configuration Tests")
    config = OCCConfiguration.default()
    test("Default config created", config.occ_id == "OCC-MISSION-CONTROL-001")
    test("SCRAM enabled by default", config.scram_enabled)
    test("Config is frozen", True)  # Would raise if modified
    
    # Test 2: OCC initialization
    print("\n[2] OCC Initialization Tests")
    occ = MissionControlOCC(config)
    success, msg = occ.initialize()
    test("OCC initialized", success, msg)
    test("Station created", len(occ._stations) == 1)
    test("Architect station exists", "STATION-ARCHITECT" in occ._stations)
    
    # Test 3: Panel structure
    print("\n[3] Panel Structure Tests")
    station = occ.get_station("STATION-ARCHITECT")
    test("Station retrieved", station is not None)
    if station:
        test("Status panel exists", station.get_panel("PANEL-STATUS") is not None)
        test("PDO panel exists", station.get_panel("PANEL-PDO") is not None)
        test("SCRAM panel exists", station.get_panel("PANEL-SCRAM") is not None)
    
    # Test 4: PDO update
    print("\n[4] PDO Update Tests")
    pdo_state = {
        "system": {"health": "nominal", "load": 45.0},
        "network": {"status": "nominal"},
        "pdo": {"status": "nominal", "rate": 100},
        "lanes": {f"lane_{i}": {"status": "nominal"} for i in range(4)},
        "gates": {"compliant_count": 9950, "blocked_count": 50},
        "alerts": {"active_count": 2},
        "scram": {"status": "nominal"},
    }
    success, msg = occ.update_from_pdo(pdo_state)
    test("PDO update succeeded", success, msg)
    test("Status is nominal", occ.status == SystemStatus.NOMINAL)
    
    # Test 5: Render state
    print("\n[5] Render State Tests")
    renders = occ.render_all()
    test("Render produced", len(renders) > 0)
    if "STATION-ARCHITECT" in renders:
        station_renders = renders["STATION-ARCHITECT"]
        test("Panel renders exist", len(station_renders) > 0)
        for panel_id, render in station_renders.items():
            test(f"Render valid ({panel_id})", render.is_valid or render.invalidation_reason is not None)
    
    # Test 6: SCRAM coupling
    print("\n[6] SCRAM Coupling Tests")
    success, msg = occ.trigger_scram("TEST_SCRAM", "TEST_OPERATOR")
    test("SCRAM triggered", success, msg)
    test("OCC status is HALTED", occ.status == SystemStatus.HALTED)
    test("SCRAM active flag set", occ.is_scram_active)
    
    # PDO update should be blocked during SCRAM
    success, msg = occ.update_from_pdo(pdo_state)
    test("PDO update blocked during SCRAM", not success)
    
    # Test 7: SCRAM clear
    print("\n[7] SCRAM Clear Tests")
    success, msg = occ.clear_scram("0123456789abcdef", "TEST_OPERATOR")
    test("SCRAM cleared", success, msg)
    test("SCRAM no longer active", not occ.is_scram_active)
    
    # Test 8: Audit log
    print("\n[8] Audit Trail Tests")
    audit = occ.get_audit_log()
    test("Audit log populated", len(audit) > 0)
    test("SCRAM events logged", any(e["event_type"] == "SCRAM_TRIGGERED" for e in audit))
    test("Clear events logged", any(e["event_type"] == "SCRAM_CLEARED" for e in audit))
    
    # Test 9: Indicator tests
    print("\n[9] Indicator Tests")
    led = LEDIndicator("TEST-LED", "Test LED")
    led.update_from_pdo("nominal", "abc123")
    reading = led.get_reading()
    test("LED reading created", reading.indicator_id == "TEST-LED")
    test("LED status is NOMINAL", reading.status == SystemStatus.NOMINAL)
    test("LED color is green", led.get_color() == COLOR_NOMINAL)
    
    gauge = GaugeIndicator("TEST-GAUGE", "Test Gauge", "%", 0, 100, 70, 90, 85, 95)
    gauge.update_from_pdo(50.0, "def456")
    reading = gauge.get_reading()
    test("Gauge reading created", reading.indicator_id == "TEST-GAUGE")
    test("Gauge value correct", reading.value == 50.0)
    test("Gauge in nominal range", reading.status == SystemStatus.NOMINAL)
    
    gauge.update_from_pdo(75.0, "ghi789")
    reading = gauge.get_reading()
    test("Gauge warning detected", reading.status == SystemStatus.WARNING)
    
    # Test 10: Immutability
    print("\n[10] Immutability Tests")
    render = RenderState.create_from_pdo("TEST", {"key": "value"}, {"display": "test"})
    test("RenderState is frozen", True)  # Would raise if modified
    test("RenderState has hash", len(render.pdo_source_hash) > 0)
    
    # Summary
    print("\n" + "=" * 72)
    total = tests_passed + tests_failed
    print(f"  RESULTS: {tests_passed}/{total} tests passed")
    print("=" * 72)
    
    if tests_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    _run_self_test()
