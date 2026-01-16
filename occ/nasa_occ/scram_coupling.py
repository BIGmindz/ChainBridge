"""
SCRAM-UI Coupling Module
PAC-JEFFREY-OCC-UI-NASA-001 | Task 5: SCRAM-Triggered UI Halt

GOVERNANCE_TIER: LAW
DRIFT_TOLERANCE: ZERO
FAIL_CLOSED: true

Integrates SCRAM (Safety Control Rod Axe Man) mechanism with UI layer.
When SCRAM is triggered, ALL UI components halt deterministically.

INVARIANTS ENFORCED:
- INV-SCRAM-UI-COUPLING: SCRAM triggers immediate UI halt
- INV-DETERMINISTIC-SHUTDOWN: UI shutdown is predictable and complete
- INV-NO-ZOMBIE-STATE: No UI components continue after SCRAM

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY (STRATEGY_ONLY)
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    FrozenSet,
    Generic,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
    runtime_checkable,
)


# =============================================================================
# SECTION 1: CONSTANTS AND CONFIGURATION
# =============================================================================

VERSION: Final[str] = "1.0.0"
PAC_REFERENCE: Final[str] = "PAC-JEFFREY-OCC-UI-NASA-001"

# SCRAM timing constraints
SCRAM_PROPAGATION_MAX_MS: Final[int] = 100      # Max time to propagate SCRAM
UI_HALT_TIMEOUT_MS: Final[int] = 500            # Max time for UI to halt
SCRAM_VERIFICATION_DELAY_MS: Final[int] = 50    # Delay before verifying halt

# Invariant identifiers
INV_SCRAM_UI_COUPLING: Final[str] = "INV-SCRAM-UI-COUPLING"
INV_DETERMINISTIC_SHUTDOWN: Final[str] = "INV-DETERMINISTIC-SHUTDOWN"
INV_NO_ZOMBIE_STATE: Final[str] = "INV-NO-ZOMBIE-STATE"


# =============================================================================
# SECTION 2: ENUMERATIONS
# =============================================================================

class SCRAMLevel(Enum):
    """SCRAM severity levels."""
    SOFT = auto()              # Graceful shutdown, save state
    HARD = auto()              # Immediate halt, state preservation best-effort
    CRITICAL = auto()          # Emergency halt, no state operations


class SCRAMSource(Enum):
    """Source of SCRAM trigger."""
    OPERATOR = auto()          # Manual operator trigger
    INVARIANT = auto()         # Invariant violation detected
    WATCHDOG = auto()          # Watchdog timeout
    SYSTEM = auto()            # System-level trigger
    EXTERNAL = auto()          # External system trigger
    TEST = auto()              # Test/simulation trigger


class UIHaltState(Enum):
    """UI component halt state."""
    RUNNING = auto()           # Normal operation
    HALTING = auto()           # Halt in progress
    HALTED = auto()            # Fully halted
    FROZEN = auto()            # Display frozen (read-only)
    ERROR = auto()             # Halt failed - error state


class HaltVerification(Enum):
    """Halt verification result."""
    VERIFIED = auto()          # Component confirmed halted
    TIMEOUT = auto()           # Halt verification timed out
    FAILED = auto()            # Component failed to halt
    ZOMBIE = auto()            # Component still active (invariant violation)


# =============================================================================
# SECTION 3: PROTOCOLS
# =============================================================================

@runtime_checkable
class SCRAMHaltable(Protocol):
    """Protocol for components that can be halted by SCRAM."""
    
    @property
    def component_id(self) -> str: ...
    
    @property
    def halt_state(self) -> UIHaltState: ...
    
    def initiate_halt(self, scram_id: str, level: SCRAMLevel) -> bool: ...
    
    def complete_halt(self) -> bool: ...
    
    def verify_halted(self) -> HaltVerification: ...


# =============================================================================
# SECTION 4: CORE DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class SCRAMEvent:
    """
    Immutable SCRAM event record.
    
    Records a SCRAM trigger for audit trail.
    """
    scram_id: str
    level: SCRAMLevel
    source: SCRAMSource
    reason: str
    triggered_at: datetime
    triggered_by: str
    affected_components: Tuple[str, ...]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scram_id": self.scram_id,
            "level": self.level.name,
            "source": self.source.name,
            "reason": self.reason,
            "triggered_at": self.triggered_at.isoformat(),
            "triggered_by": self.triggered_by,
            "affected_components": list(self.affected_components),
        }


@dataclass(frozen=True)
class HaltRecord:
    """
    Immutable halt record for a single component.
    """
    record_id: str
    component_id: str
    scram_id: str
    halt_initiated_at: datetime
    halt_completed_at: Optional[datetime]
    verification: HaltVerification
    final_state: UIHaltState
    halt_duration_ms: float
    
    @property
    def is_successful(self) -> bool:
        return self.verification == HaltVerification.VERIFIED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "component_id": self.component_id,
            "scram_id": self.scram_id,
            "halt_initiated_at": self.halt_initiated_at.isoformat(),
            "halt_completed_at": self.halt_completed_at.isoformat() if self.halt_completed_at else None,
            "verification": self.verification.name,
            "final_state": self.final_state.name,
            "halt_duration_ms": self.halt_duration_ms,
            "is_successful": self.is_successful,
        }


@dataclass
class SCRAMStatus:
    """
    Current SCRAM system status.
    """
    is_active: bool = False
    current_scram_id: Optional[str] = None
    current_level: Optional[SCRAMLevel] = None
    triggered_at: Optional[datetime] = None
    components_halted: int = 0
    components_pending: int = 0
    components_failed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_active": self.is_active,
            "current_scram_id": self.current_scram_id,
            "current_level": self.current_level.name if self.current_level else None,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "components_halted": self.components_halted,
            "components_pending": self.components_pending,
            "components_failed": self.components_failed,
        }


# =============================================================================
# SECTION 5: HALTABLE UI COMPONENT
# =============================================================================

class HaltableUIComponent:
    """
    UI component that can be halted by SCRAM.
    
    This is the base implementation for all haltable UI components.
    """
    
    def __init__(
        self,
        component_id: str,
        critical: bool = False,
    ) -> None:
        self._component_id = component_id
        self._critical = critical
        self._halt_state = UIHaltState.RUNNING
        self._scram_id: Optional[str] = None
        self._halt_level: Optional[SCRAMLevel] = None
        self._halt_initiated_at: Optional[datetime] = None
        self._halt_completed_at: Optional[datetime] = None
        self._last_render: Dict[str, Any] = {}
        self._halt_callbacks: List[Callable[[str, SCRAMLevel], None]] = []
    
    @property
    def component_id(self) -> str:
        return self._component_id
    
    @property
    def halt_state(self) -> UIHaltState:
        return self._halt_state
    
    @property
    def is_halted(self) -> bool:
        return self._halt_state in (UIHaltState.HALTED, UIHaltState.FROZEN)
    
    def add_halt_callback(
        self,
        callback: Callable[[str, SCRAMLevel], None],
    ) -> None:
        """Add callback to be invoked on halt."""
        self._halt_callbacks.append(callback)
    
    def initiate_halt(self, scram_id: str, level: SCRAMLevel) -> bool:
        """
        Initiate halt of this component.
        
        Returns True if halt initiated successfully.
        """
        if self._halt_state != UIHaltState.RUNNING:
            return False  # Already halting or halted
        
        self._halt_state = UIHaltState.HALTING
        self._scram_id = scram_id
        self._halt_level = level
        self._halt_initiated_at = datetime.now(timezone.utc)
        
        # Capture last render state for frozen display
        self._capture_last_state()
        
        # Invoke callbacks
        for callback in self._halt_callbacks:
            try:
                callback(scram_id, level)
            except Exception:
                pass  # Callbacks should not prevent halt
        
        return True
    
    def _capture_last_state(self) -> None:
        """Capture current state for frozen display."""
        self._last_render = {
            "component_id": self._component_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "state": "FROZEN",
            "scram_id": self._scram_id,
        }
    
    def complete_halt(self) -> bool:
        """
        Complete the halt process.
        
        Returns True if halt completed successfully.
        """
        if self._halt_state != UIHaltState.HALTING:
            return False
        
        self._halt_state = UIHaltState.HALTED
        self._halt_completed_at = datetime.now(timezone.utc)
        
        return True
    
    def verify_halted(self) -> HaltVerification:
        """
        Verify that component is halted.
        
        Returns verification result.
        """
        if self._halt_state == UIHaltState.HALTED:
            return HaltVerification.VERIFIED
        elif self._halt_state == UIHaltState.FROZEN:
            return HaltVerification.VERIFIED
        elif self._halt_state == UIHaltState.HALTING:
            return HaltVerification.TIMEOUT
        elif self._halt_state == UIHaltState.RUNNING:
            return HaltVerification.ZOMBIE
        else:
            return HaltVerification.FAILED
    
    def freeze(self) -> None:
        """Freeze component (display-only mode)."""
        self._halt_state = UIHaltState.FROZEN
    
    def get_frozen_render(self) -> Dict[str, Any]:
        """Get frozen render state (for display during SCRAM)."""
        return {
            **self._last_render,
            "halt_state": self._halt_state.name,
            "scram_active": True,
        }
    
    def reset(self, authorization_code: str) -> bool:
        """
        Reset component from halted state.
        
        Requires authorization code for safety.
        """
        if len(authorization_code) < 16:
            return False
        
        if self._halt_state in (UIHaltState.HALTED, UIHaltState.FROZEN):
            self._halt_state = UIHaltState.RUNNING
            self._scram_id = None
            self._halt_level = None
            self._halt_initiated_at = None
            self._halt_completed_at = None
            return True
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self._component_id,
            "critical": self._critical,
            "halt_state": self._halt_state.name,
            "scram_id": self._scram_id,
            "halt_level": self._halt_level.name if self._halt_level else None,
            "is_halted": self.is_halted,
        }


# =============================================================================
# SECTION 6: SCRAM UI CONTROLLER
# =============================================================================

class SCRAMUIController:
    """
    SCRAM-UI Controller.
    
    Manages the coupling between SCRAM triggers and UI halt behavior.
    When SCRAM is triggered, ALL registered UI components are halted.
    
    INVARIANTS:
    - INV-SCRAM-UI-COUPLING: SCRAM halts all UI components
    - INV-DETERMINISTIC-SHUTDOWN: Shutdown is predictable
    - INV-NO-ZOMBIE-STATE: No components continue running after SCRAM
    """
    
    def __init__(self) -> None:
        self._components: Dict[str, HaltableUIComponent] = {}
        self._scram_events: List[SCRAMEvent] = []
        self._halt_records: List[HaltRecord] = []
        self._status = SCRAMStatus()
        self._scram_listeners: List[Callable[[SCRAMEvent], None]] = []
        self._lock = threading.Lock()
    
    @property
    def is_scram_active(self) -> bool:
        return self._status.is_active
    
    @property
    def status(self) -> SCRAMStatus:
        return self._status
    
    def register_component(self, component: HaltableUIComponent) -> None:
        """Register a component for SCRAM control."""
        with self._lock:
            self._components[component.component_id] = component
    
    def unregister_component(self, component_id: str) -> bool:
        """Unregister a component."""
        with self._lock:
            if component_id in self._components:
                del self._components[component_id]
                return True
            return False
    
    def add_scram_listener(
        self,
        listener: Callable[[SCRAMEvent], None],
    ) -> None:
        """Add listener for SCRAM events."""
        self._scram_listeners.append(listener)
    
    def trigger_scram(
        self,
        level: SCRAMLevel,
        source: SCRAMSource,
        reason: str,
        triggered_by: str,
    ) -> Tuple[bool, str, SCRAMEvent]:
        """
        Trigger SCRAM - halt all UI components.
        
        Returns (success, message, scram_event).
        """
        with self._lock:
            if self._status.is_active:
                # SCRAM already active
                return (False, "SCRAM already active", self._scram_events[-1])
            
            scram_id = f"SCRAM-{uuid.uuid4().hex[:12].upper()}"
            triggered_at = datetime.now(timezone.utc)
            
            # Create SCRAM event
            event = SCRAMEvent(
                scram_id=scram_id,
                level=level,
                source=source,
                reason=reason,
                triggered_at=triggered_at,
                triggered_by=triggered_by,
                affected_components=tuple(self._components.keys()),
            )
            
            self._scram_events.append(event)
            
            # Update status
            self._status.is_active = True
            self._status.current_scram_id = scram_id
            self._status.current_level = level
            self._status.triggered_at = triggered_at
            self._status.components_pending = len(self._components)
            self._status.components_halted = 0
            self._status.components_failed = 0
            
            # Notify listeners
            for listener in self._scram_listeners:
                try:
                    listener(event)
                except Exception:
                    pass  # Listeners should not prevent SCRAM
            
            # Halt all components
            halt_results = self._halt_all_components(scram_id, level)
            
            return (True, f"SCRAM triggered: {reason}", event)
    
    def _halt_all_components(
        self,
        scram_id: str,
        level: SCRAMLevel,
    ) -> List[HaltRecord]:
        """Halt all registered components."""
        records: List[HaltRecord] = []
        
        for component_id, component in self._components.items():
            record = self._halt_component(component, scram_id, level)
            records.append(record)
            self._halt_records.append(record)
            
            if record.is_successful:
                self._status.components_halted += 1
            else:
                self._status.components_failed += 1
            
            self._status.components_pending -= 1
        
        return records
    
    def _halt_component(
        self,
        component: HaltableUIComponent,
        scram_id: str,
        level: SCRAMLevel,
    ) -> HaltRecord:
        """Halt a single component."""
        import time
        
        start_time = datetime.now(timezone.utc)
        start_ms = time.time() * 1000
        
        # Initiate halt
        initiated = component.initiate_halt(scram_id, level)
        
        if not initiated:
            # Component may already be halted
            verification = component.verify_halted()
            return HaltRecord(
                record_id=f"HALT-{uuid.uuid4().hex[:12].upper()}",
                component_id=component.component_id,
                scram_id=scram_id,
                halt_initiated_at=start_time,
                halt_completed_at=datetime.now(timezone.utc),
                verification=verification,
                final_state=component.halt_state,
                halt_duration_ms=time.time() * 1000 - start_ms,
            )
        
        # Complete halt based on level
        if level == SCRAMLevel.SOFT:
            # Allow graceful completion
            component.complete_halt()
        elif level == SCRAMLevel.HARD:
            # Immediate halt
            component.complete_halt()
        else:  # CRITICAL
            # Force halt
            component.complete_halt()
            component.freeze()
        
        # Verify halt
        verification = component.verify_halted()
        
        return HaltRecord(
            record_id=f"HALT-{uuid.uuid4().hex[:12].upper()}",
            component_id=component.component_id,
            scram_id=scram_id,
            halt_initiated_at=start_time,
            halt_completed_at=datetime.now(timezone.utc),
            verification=verification,
            final_state=component.halt_state,
            halt_duration_ms=time.time() * 1000 - start_ms,
        )
    
    def verify_all_halted(self) -> Tuple[bool, List[str]]:
        """
        Verify all components are halted.
        
        Returns (all_halted, list of zombie component IDs).
        """
        zombies: List[str] = []
        
        for component_id, component in self._components.items():
            verification = component.verify_halted()
            if verification == HaltVerification.ZOMBIE:
                zombies.append(component_id)
        
        return (len(zombies) == 0, zombies)
    
    def clear_scram(
        self,
        authorization_code: str,
        operator_id: str,
    ) -> Tuple[bool, str]:
        """
        Clear SCRAM state.
        
        Requires authorization - components must be individually reset.
        """
        with self._lock:
            if not self._status.is_active:
                return (False, "No active SCRAM to clear")
            
            if len(authorization_code) < 16:
                return (False, "Invalid authorization code")
            
            # Record clearance
            self._status.is_active = False
            
            # Note: Components remain halted - must be individually reset
            return (True, f"SCRAM cleared by {operator_id}. Components require individual reset.")
    
    def reset_component(
        self,
        component_id: str,
        authorization_code: str,
    ) -> Tuple[bool, str]:
        """Reset a specific component from halted state."""
        with self._lock:
            if self._status.is_active:
                return (False, "Cannot reset while SCRAM is active")
            
            component = self._components.get(component_id)
            if not component:
                return (False, f"Unknown component: {component_id}")
            
            if component.reset(authorization_code):
                return (True, f"Component {component_id} reset successfully")
            else:
                return (False, f"Failed to reset component {component_id}")
    
    def reset_all_components(
        self,
        authorization_code: str,
    ) -> Tuple[int, int]:
        """
        Reset all components.
        
        Returns (success_count, failure_count).
        """
        if self._status.is_active:
            return (0, len(self._components))
        
        success = 0
        failure = 0
        
        for component in self._components.values():
            if component.reset(authorization_code):
                success += 1
            else:
                failure += 1
        
        return (success, failure)
    
    def get_scram_events(self) -> Sequence[SCRAMEvent]:
        """Get all SCRAM events."""
        return tuple(self._scram_events)
    
    def get_halt_records(self) -> Sequence[HaltRecord]:
        """Get all halt records."""
        return tuple(self._halt_records)
    
    def get_component_states(self) -> Dict[str, Dict[str, Any]]:
        """Get current state of all components."""
        return {
            cid: comp.to_dict()
            for cid, comp in self._components.items()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self._status.to_dict(),
            "registered_components": len(self._components),
            "scram_event_count": len(self._scram_events),
            "halt_record_count": len(self._halt_records),
        }


# =============================================================================
# SECTION 7: SCRAM INTEGRATION BRIDGE
# =============================================================================

class SCRAMIntegrationBridge:
    """
    Bridge between Execution Kernel SCRAM and UI SCRAM.
    
    Listens for SCRAM events from the execution kernel and
    propagates them to the UI layer.
    """
    
    def __init__(
        self,
        ui_controller: SCRAMUIController,
    ) -> None:
        self._ui_controller = ui_controller
        self._bridge_active = False
        self._propagation_log: List[Dict[str, Any]] = []
    
    def activate(self) -> None:
        """Activate the SCRAM bridge."""
        self._bridge_active = True
    
    def deactivate(self) -> None:
        """Deactivate the SCRAM bridge."""
        self._bridge_active = False
    
    def propagate_scram(
        self,
        kernel_scram_reason: str,
        kernel_execution_id: str,
    ) -> Tuple[bool, str]:
        """
        Propagate SCRAM from execution kernel to UI.
        
        Called when execution kernel triggers SCRAM.
        """
        if not self._bridge_active:
            return (False, "SCRAM bridge is not active")
        
        # Log propagation
        self._propagation_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "EXECUTION_KERNEL",
            "execution_id": kernel_execution_id,
            "reason": kernel_scram_reason,
        })
        
        # Trigger UI SCRAM
        success, msg, event = self._ui_controller.trigger_scram(
            level=SCRAMLevel.HARD,
            source=SCRAMSource.INVARIANT,
            reason=f"Kernel SCRAM: {kernel_scram_reason}",
            triggered_by="EXECUTION_KERNEL",
        )
        
        return (success, msg)
    
    def get_propagation_log(self) -> Sequence[Dict[str, Any]]:
        """Get propagation log."""
        return tuple(self._propagation_log)


# =============================================================================
# SECTION 8: SELF-TEST
# =============================================================================

def _run_self_test() -> None:
    """Execute self-test suite."""
    import sys
    import time
    
    print("=" * 72)
    print("  SCRAM-UI COUPLING MODULE - SELF-TEST")
    print("  PAC-JEFFREY-OCC-UI-NASA-001 | Task 5")
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
    
    # Test 1: Haltable Component
    print("\n[1] Haltable Component Tests")
    component = HaltableUIComponent("COMP-001", critical=True)
    test("Component created", component.component_id == "COMP-001")
    test("Initial state RUNNING", component.halt_state == UIHaltState.RUNNING)
    test("Not halted initially", not component.is_halted)
    
    # Test 2: Component Halt
    print("\n[2] Component Halt Tests")
    initiated = component.initiate_halt("SCRAM-TEST", SCRAMLevel.HARD)
    test("Halt initiated", initiated)
    test("State is HALTING", component.halt_state == UIHaltState.HALTING)
    
    completed = component.complete_halt()
    test("Halt completed", completed)
    test("State is HALTED", component.halt_state == UIHaltState.HALTED)
    test("Is halted", component.is_halted)
    
    # Test 3: Halt Verification
    print("\n[3] Halt Verification Tests")
    verification = component.verify_halted()
    test("Verification VERIFIED", verification == HaltVerification.VERIFIED)
    
    # Cannot initiate halt again
    initiated_again = component.initiate_halt("SCRAM-TEST-2", SCRAMLevel.HARD)
    test("Cannot re-initiate halt", not initiated_again)
    
    # Test 4: Component Reset
    print("\n[4] Component Reset Tests")
    reset_ok = component.reset("short")
    test("Short auth code rejected", not reset_ok)
    
    reset_ok = component.reset("0123456789abcdef")
    test("Valid auth code accepted", reset_ok)
    test("Component running after reset", component.halt_state == UIHaltState.RUNNING)
    
    # Test 5: SCRAM Controller
    print("\n[5] SCRAM Controller Tests")
    controller = SCRAMUIController()
    test("Controller created", not controller.is_scram_active)
    
    # Register components
    comp1 = HaltableUIComponent("UI-PANEL-1")
    comp2 = HaltableUIComponent("UI-PANEL-2")
    comp3 = HaltableUIComponent("UI-INDICATOR-1")
    
    controller.register_component(comp1)
    controller.register_component(comp2)
    controller.register_component(comp3)
    test("Components registered", len(controller._components) == 3)
    
    # Test 6: SCRAM Trigger
    print("\n[6] SCRAM Trigger Tests")
    success, msg, event = controller.trigger_scram(
        level=SCRAMLevel.HARD,
        source=SCRAMSource.OPERATOR,
        reason="TEST SCRAM TRIGGER",
        triggered_by="TEST_OPERATOR",
    )
    test("SCRAM triggered", success)
    test("SCRAM active", controller.is_scram_active)
    test("Event has SCRAM ID", event.scram_id.startswith("SCRAM-"))
    
    # Test 7: All Components Halted
    print("\n[7] Component Halt Verification Tests")
    all_halted, zombies = controller.verify_all_halted()
    test("All components halted", all_halted)
    test("No zombie components", len(zombies) == 0)
    test("Component 1 halted", comp1.is_halted)
    test("Component 2 halted", comp2.is_halted)
    test("Component 3 halted", comp3.is_halted)
    
    # Status check
    status = controller.status
    test("Status shows active", status.is_active)
    test("3 components halted", status.components_halted == 3)
    test("0 components pending", status.components_pending == 0)
    
    # Test 8: Cannot Trigger SCRAM Again
    print("\n[8] Double SCRAM Prevention Tests")
    success2, msg2, _ = controller.trigger_scram(
        level=SCRAMLevel.CRITICAL,
        source=SCRAMSource.TEST,
        reason="SECOND SCRAM",
        triggered_by="TEST",
    )
    test("Second SCRAM rejected", not success2)
    
    # Test 9: SCRAM Clear
    print("\n[9] SCRAM Clear Tests")
    success, msg = controller.clear_scram("0123456789abcdef", "TEST_OPERATOR")
    test("SCRAM cleared", success)
    test("SCRAM no longer active", not controller.is_scram_active)
    
    # Components still halted (require individual reset)
    test("Components still halted after clear", comp1.is_halted)
    
    # Test 10: Component Reset After SCRAM Clear
    print("\n[10] Post-SCRAM Component Reset Tests")
    success, msg = controller.reset_component("UI-PANEL-1", "0123456789abcdef")
    test("Component reset succeeded", success)
    test("Component 1 running", not comp1.is_halted)
    
    # Reset all
    success_count, fail_count = controller.reset_all_components("0123456789abcdef")
    test("Bulk reset succeeded", success_count >= 2)
    
    # Test 11: SCRAM Listener
    print("\n[11] SCRAM Listener Tests")
    received_events: List[SCRAMEvent] = []
    
    def on_scram(event: SCRAMEvent) -> None:
        received_events.append(event)
    
    controller2 = SCRAMUIController()
    controller2.add_scram_listener(on_scram)
    controller2.register_component(HaltableUIComponent("LISTENER-TEST"))
    
    controller2.trigger_scram(
        level=SCRAMLevel.SOFT,
        source=SCRAMSource.TEST,
        reason="LISTENER TEST",
        triggered_by="TEST",
    )
    test("Listener received event", len(received_events) == 1)
    test("Event has correct reason", received_events[0].reason == "LISTENER TEST")
    
    # Test 12: SCRAM Levels
    print("\n[12] SCRAM Level Tests")
    for level in [SCRAMLevel.SOFT, SCRAMLevel.HARD, SCRAMLevel.CRITICAL]:
        ctrl = SCRAMUIController()
        comp = HaltableUIComponent(f"COMP-{level.name}")
        ctrl.register_component(comp)
        
        success, _, event = ctrl.trigger_scram(
            level=level,
            source=SCRAMSource.TEST,
            reason=f"Test {level.name}",
            triggered_by="TEST",
        )
        test(f"{level.name} SCRAM works", success and comp.is_halted)
    
    # Test 13: Integration Bridge
    print("\n[13] Integration Bridge Tests")
    bridge_controller = SCRAMUIController()
    bridge_controller.register_component(HaltableUIComponent("BRIDGE-COMP"))
    
    bridge = SCRAMIntegrationBridge(bridge_controller)
    bridge.activate()
    
    success, msg = bridge.propagate_scram(
        kernel_scram_reason="Invariant violation",
        kernel_execution_id="EXEC-12345",
    )
    test("Bridge propagated SCRAM", success)
    test("Bridge controller SCRAM active", bridge_controller.is_scram_active)
    
    # Test 14: Halt Records
    print("\n[14] Halt Records Tests")
    records = controller.get_halt_records()
    test("Halt records exist", len(records) > 0)
    test("Records have correct structure", all(r.record_id.startswith("HALT-") for r in records))
    
    # Test 15: Deterministic Shutdown Timing
    print("\n[15] Shutdown Timing Tests")
    timing_controller = SCRAMUIController()
    for i in range(10):
        timing_controller.register_component(HaltableUIComponent(f"TIMING-{i}"))
    
    start_ms = time.time() * 1000
    timing_controller.trigger_scram(
        level=SCRAMLevel.CRITICAL,
        source=SCRAMSource.TEST,
        reason="TIMING TEST",
        triggered_by="TEST",
    )
    end_ms = time.time() * 1000
    
    shutdown_time = end_ms - start_ms
    test(f"Shutdown < {UI_HALT_TIMEOUT_MS}ms ({shutdown_time:.1f}ms)", shutdown_time < UI_HALT_TIMEOUT_MS)
    
    # Summary
    print("\n" + "=" * 72)
    total = tests_passed + tests_failed
    print(f"  RESULTS: {tests_passed}/{total} tests passed")
    print("=" * 72)
    
    if tests_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    _run_self_test()
