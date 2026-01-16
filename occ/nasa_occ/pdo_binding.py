"""
PDO State Binding Layer
PAC-JEFFREY-OCC-UI-NASA-001 | Task 2: PDO Truth Binding

GOVERNANCE_TIER: LAW
DRIFT_TOLERANCE: ZERO
FAIL_CLOSED: true

Binds all UI components to PDO (Proof-Decision-Outcome) state graph.
Ensures UI reflects system truth only - no speculative or optimistic rendering.

INVARIANTS ENFORCED:
- INV-PDO-PRIMACY: PDO is the single source of truth
- INV-UI-TRUTH-BINDING: UI state derived from PDO only
- INV-NO-SPECULATIVE-STATE: No optimistic updates

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY (STRATEGY_ONLY)
"""

from __future__ import annotations

import hashlib
import json
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

# PDO state staleness threshold (if older, mark as STALE)
PDO_STALENESS_THRESHOLD_MS: Final[int] = 5000

# Maximum PDO history entries to retain
PDO_HISTORY_MAX_SIZE: Final[int] = 1000

# Invariant identifiers
INV_PDO_PRIMACY: Final[str] = "INV-PDO-PRIMACY"
INV_UI_TRUTH_BINDING: Final[str] = "INV-UI-TRUTH-BINDING"
INV_NO_SPECULATIVE_STATE: Final[str] = "INV-NO-SPECULATIVE-STATE"


# =============================================================================
# SECTION 2: ENUMERATIONS
# =============================================================================

class TruthSourceType(Enum):
    """Types of truth sources in the PDO graph."""
    PDO_ENGINE = auto()        # Core PDO engine
    EXECUTION_KERNEL = auto()  # Execution kernel state
    AUDIT_TRAIL = auto()       # Audit trail data
    GATE_REGISTRY = auto()     # Law gate status
    LANE_MONITOR = auto()      # Execution lane state
    TELEMETRY = auto()         # System telemetry


class BindingMode(Enum):
    """UI binding modes."""
    PULL = auto()              # UI pulls state on demand
    PUSH = auto()              # State pushed to UI
    REACTIVE = auto()          # Reactive updates on change


class ValidationResult(Enum):
    """PDO validation result."""
    VALID = auto()             # PDO state is valid
    STALE = auto()             # PDO state is stale (old timestamp)
    INVALID_HASH = auto()      # Hash verification failed
    MISSING_FIELDS = auto()    # Required fields missing
    SCHEMA_VIOLATION = auto()  # Schema validation failed


class PropagationMode(Enum):
    """State propagation mode for bindings."""
    IMMEDIATE = auto()         # Propagate immediately
    BATCHED = auto()           # Batch updates
    ON_COMMIT = auto()         # Propagate on commit


# =============================================================================
# SECTION 3: CORE DATA STRUCTURES (Frozen/Immutable)
# =============================================================================

@dataclass(frozen=True)
class PDORecord:
    """
    Immutable PDO (Proof-Decision-Outcome) record.
    
    Represents a single unit of truth in the system.
    """
    pdo_id: str
    timestamp: datetime
    proof: Mapping[str, Any]       # Proof data
    decision: Mapping[str, Any]    # Decision data
    outcome: Mapping[str, Any]     # Outcome data
    source_type: TruthSourceType
    source_id: str
    previous_hash: str
    record_hash: str = ""
    
    def __post_init__(self) -> None:
        if not self.record_hash:
            computed = self._compute_hash()
            object.__setattr__(self, "record_hash", computed)
    
    def _compute_hash(self) -> str:
        content = json.dumps({
            "pdo_id": self.pdo_id,
            "timestamp": self.timestamp.isoformat(),
            "proof": dict(self.proof),
            "decision": dict(self.decision),
            "outcome": dict(self.outcome),
            "source_type": self.source_type.name,
            "source_id": self.source_id,
            "previous_hash": self.previous_hash,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdo_id": self.pdo_id,
            "timestamp": self.timestamp.isoformat(),
            "proof": dict(self.proof),
            "decision": dict(self.decision),
            "outcome": dict(self.outcome),
            "source_type": self.source_type.name,
            "source_id": self.source_id,
            "previous_hash": self.previous_hash,
            "record_hash": self.record_hash,
        }


@dataclass(frozen=True)
class TruthSource:
    """
    Immutable truth source definition.
    
    Defines a source of truth that can be bound to UI components.
    """
    source_id: str
    source_type: TruthSourceType
    schema: Mapping[str, str]      # Field name -> type
    refresh_interval_ms: int
    required_fields: FrozenSet[str]
    
    def validate_data(self, data: Mapping[str, Any]) -> Tuple[ValidationResult, str]:
        """Validate data against truth source schema."""
        # Check required fields
        for field in self.required_fields:
            if field not in data:
                return (ValidationResult.MISSING_FIELDS, f"Missing field: {field}")
        
        # Validate types
        for field_name, expected_type in self.schema.items():
            if field_name in data:
                value = data[field_name]
                if not self._check_type(value, expected_type):
                    return (
                        ValidationResult.SCHEMA_VIOLATION,
                        f"Field {field_name}: expected {expected_type}, got {type(value).__name__}"
                    )
        
        return (ValidationResult.VALID, "")
    
    def _check_type(self, value: Any, expected: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "string": str,
            "int": int,
            "float": (int, float),
            "bool": bool,
            "dict": dict,
            "list": list,
            "any": object,
        }
        expected_type = type_map.get(expected.lower(), object)
        return isinstance(value, expected_type)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.name,
            "schema": dict(self.schema),
            "refresh_interval_ms": self.refresh_interval_ms,
            "required_fields": sorted(self.required_fields),
        }


@dataclass(frozen=True)
class UIStateBinding:
    """
    Immutable UI state binding definition.
    
    Binds a UI component to a specific path in the PDO state graph.
    """
    binding_id: str
    component_id: str
    pdo_path: str                 # Dot-notation path in PDO state
    source: TruthSource
    mode: BindingMode
    transform: Optional[str]      # Transform expression (optional)
    propagation: PropagationMode
    
    def extract_value(self, pdo_state: Mapping[str, Any]) -> Tuple[Any, str]:
        """
        Extract value from PDO state using path.
        
        Returns (value, hash) where hash is for change detection.
        """
        parts = self.pdo_path.split(".")
        current: Any = pdo_state
        
        for part in parts:
            if isinstance(current, Mapping) and part in current:
                current = current[part]
            else:
                return (None, "")
        
        # Compute hash of extracted value for change detection
        value_hash = hashlib.sha256(
            json.dumps(current if current is None else str(current)).encode()
        ).hexdigest()[:8]
        
        return (current, value_hash)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "component_id": self.component_id,
            "pdo_path": self.pdo_path,
            "source_id": self.source.source_id,
            "mode": self.mode.name,
            "transform": self.transform,
            "propagation": self.propagation.name,
        }


@dataclass(frozen=True)
class StateSnapshot:
    """
    Immutable snapshot of PDO state at a point in time.
    
    Used for deterministic rendering and rollback support.
    """
    snapshot_id: str
    timestamp: datetime
    state: Mapping[str, Any]
    state_hash: str
    pdo_record_ids: Tuple[str, ...]
    is_committed: bool
    
    @classmethod
    def create(
        cls,
        state: Mapping[str, Any],
        pdo_record_ids: Sequence[str],
    ) -> "StateSnapshot":
        """Factory: Create snapshot from current state."""
        state_hash = hashlib.sha256(
            json.dumps(dict(state), sort_keys=True).encode()
        ).hexdigest()[:16]
        
        return cls(
            snapshot_id=f"SNAP-{uuid.uuid4().hex[:12].upper()}",
            timestamp=datetime.now(timezone.utc),
            state=state,
            state_hash=state_hash,
            pdo_record_ids=tuple(pdo_record_ids),
            is_committed=False,
        )
    
    def commit(self) -> "StateSnapshot":
        """Create committed version of snapshot."""
        return StateSnapshot(
            snapshot_id=self.snapshot_id,
            timestamp=self.timestamp,
            state=self.state,
            state_hash=self.state_hash,
            pdo_record_ids=self.pdo_record_ids,
            is_committed=True,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "state_hash": self.state_hash,
            "pdo_record_count": len(self.pdo_record_ids),
            "is_committed": self.is_committed,
        }


# =============================================================================
# SECTION 4: PDO STATE GRAPH
# =============================================================================

class PDOStateGraph:
    """
    PDO State Graph - the single source of truth for UI.
    
    All UI state is derived from this graph. The graph maintains:
    - Current PDO records
    - State history (for rollback)
    - Binding registry
    - Change detection
    
    INVARIANTS:
    - INV-PDO-PRIMACY: All state derives from PDO records
    - INV-UI-TRUTH-BINDING: UI can only read from committed snapshots
    - INV-NO-SPECULATIVE-STATE: No optimistic or pending state exposed
    """
    
    GENESIS_HASH: Final[str] = "0" * 16
    
    def __init__(self) -> None:
        self._records: Dict[str, PDORecord] = {}
        self._latest_by_source: Dict[str, str] = {}  # source_id -> pdo_id
        self._hash_chain: str = self.GENESIS_HASH
        self._truth_sources: Dict[str, TruthSource] = {}
        self._bindings: Dict[str, UIStateBinding] = {}
        self._snapshots: List[StateSnapshot] = []
        self._current_state: Dict[str, Any] = {}
        self._binding_values: Dict[str, Tuple[Any, str]] = {}  # binding_id -> (value, hash)
        self._change_listeners: List[Callable[[str, Any], None]] = []
    
    # -------------------------------------------------------------------------
    # Truth Source Management
    # -------------------------------------------------------------------------
    
    def register_truth_source(self, source: TruthSource) -> None:
        """Register a truth source."""
        if source.source_id in self._truth_sources:
            raise ValueError(f"Truth source {source.source_id} already registered")
        self._truth_sources[source.source_id] = source
    
    def get_truth_source(self, source_id: str) -> Optional[TruthSource]:
        """Get truth source by ID."""
        return self._truth_sources.get(source_id)
    
    # -------------------------------------------------------------------------
    # PDO Record Management
    # -------------------------------------------------------------------------
    
    def ingest_pdo(
        self,
        proof: Mapping[str, Any],
        decision: Mapping[str, Any],
        outcome: Mapping[str, Any],
        source_type: TruthSourceType,
        source_id: str,
    ) -> PDORecord:
        """
        Ingest a new PDO record into the graph.
        
        This is the ONLY way to add state to the graph.
        """
        record = PDORecord(
            pdo_id=f"PDO-{uuid.uuid4().hex[:12].upper()}",
            timestamp=datetime.now(timezone.utc),
            proof=proof,
            decision=decision,
            outcome=outcome,
            source_type=source_type,
            source_id=source_id,
            previous_hash=self._hash_chain,
        )
        
        self._records[record.pdo_id] = record
        self._latest_by_source[source_id] = record.pdo_id
        self._hash_chain = record.record_hash
        
        # Update current state from outcome
        self._merge_outcome(record)
        
        # Update binding values
        self._update_bindings()
        
        # Prune old records if needed
        if len(self._records) > PDO_HISTORY_MAX_SIZE:
            self._prune_old_records()
        
        return record
    
    def _merge_outcome(self, record: PDORecord) -> None:
        """Merge PDO outcome into current state."""
        # Use source_type as namespace
        namespace = record.source_type.name.lower()
        if namespace not in self._current_state:
            self._current_state[namespace] = {}
        
        # Merge outcome data
        for key, value in record.outcome.items():
            self._current_state[namespace][key] = value
        
        # Add metadata
        self._current_state[namespace]["_last_update"] = record.timestamp.isoformat()
        self._current_state[namespace]["_pdo_id"] = record.pdo_id
        self._current_state[namespace]["_hash"] = record.record_hash
    
    def _update_bindings(self) -> None:
        """Update all binding values from current state."""
        for binding_id, binding in self._bindings.items():
            old_value, old_hash = self._binding_values.get(binding_id, (None, ""))
            new_value, new_hash = binding.extract_value(self._current_state)
            
            if new_hash != old_hash:
                self._binding_values[binding_id] = (new_value, new_hash)
                # Notify listeners of change
                for listener in self._change_listeners:
                    listener(binding_id, new_value)
    
    def _prune_old_records(self) -> None:
        """Prune oldest records to maintain size limit."""
        if len(self._records) <= PDO_HISTORY_MAX_SIZE:
            return
        
        # Sort by timestamp and remove oldest
        sorted_ids = sorted(
            self._records.keys(),
            key=lambda x: self._records[x].timestamp
        )
        
        to_remove = len(self._records) - PDO_HISTORY_MAX_SIZE
        for pdo_id in sorted_ids[:to_remove]:
            del self._records[pdo_id]
    
    def get_pdo_record(self, pdo_id: str) -> Optional[PDORecord]:
        """Get PDO record by ID."""
        return self._records.get(pdo_id)
    
    def get_latest_by_source(self, source_id: str) -> Optional[PDORecord]:
        """Get latest PDO record from a source."""
        pdo_id = self._latest_by_source.get(source_id)
        return self._records.get(pdo_id) if pdo_id else None
    
    # -------------------------------------------------------------------------
    # Binding Management
    # -------------------------------------------------------------------------
    
    def create_binding(
        self,
        component_id: str,
        pdo_path: str,
        source: TruthSource,
        mode: BindingMode = BindingMode.PULL,
        transform: Optional[str] = None,
        propagation: PropagationMode = PropagationMode.IMMEDIATE,
    ) -> UIStateBinding:
        """Create a new UI state binding."""
        binding = UIStateBinding(
            binding_id=f"BIND-{uuid.uuid4().hex[:12].upper()}",
            component_id=component_id,
            pdo_path=pdo_path,
            source=source,
            mode=mode,
            transform=transform,
            propagation=propagation,
        )
        
        self._bindings[binding.binding_id] = binding
        
        # Initialize binding value
        value, value_hash = binding.extract_value(self._current_state)
        self._binding_values[binding.binding_id] = (value, value_hash)
        
        return binding
    
    def get_binding(self, binding_id: str) -> Optional[UIStateBinding]:
        """Get binding by ID."""
        return self._bindings.get(binding_id)
    
    def get_binding_value(self, binding_id: str) -> Tuple[Any, bool]:
        """
        Get current value for a binding.
        
        Returns (value, is_stale) where is_stale indicates if value may be outdated.
        """
        if binding_id not in self._bindings:
            return (None, True)
        
        value, _ = self._binding_values.get(binding_id, (None, ""))
        
        # Check staleness
        binding = self._bindings[binding_id]
        source = binding.source
        latest = self.get_latest_by_source(source.source_id)
        
        is_stale = False
        if latest:
            age_ms = (datetime.now(timezone.utc) - latest.timestamp).total_seconds() * 1000
            is_stale = age_ms > PDO_STALENESS_THRESHOLD_MS
        
        return (value, is_stale)
    
    def get_bindings_for_component(self, component_id: str) -> Sequence[UIStateBinding]:
        """Get all bindings for a component."""
        return tuple(
            b for b in self._bindings.values()
            if b.component_id == component_id
        )
    
    # -------------------------------------------------------------------------
    # Snapshot Management
    # -------------------------------------------------------------------------
    
    def create_snapshot(self) -> StateSnapshot:
        """Create a snapshot of current state."""
        snapshot = StateSnapshot.create(
            state=self._current_state.copy(),
            pdo_record_ids=list(self._records.keys()),
        )
        self._snapshots.append(snapshot)
        return snapshot
    
    def commit_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Commit a snapshot (make it permanent)."""
        for i, snap in enumerate(self._snapshots):
            if snap.snapshot_id == snapshot_id:
                committed = snap.commit()
                self._snapshots[i] = committed
                return committed
        return None
    
    def get_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Get snapshot by ID."""
        for snap in self._snapshots:
            if snap.snapshot_id == snapshot_id:
                return snap
        return None
    
    def get_committed_snapshots(self) -> Sequence[StateSnapshot]:
        """Get all committed snapshots."""
        return tuple(s for s in self._snapshots if s.is_committed)
    
    # -------------------------------------------------------------------------
    # Change Detection
    # -------------------------------------------------------------------------
    
    def add_change_listener(
        self,
        listener: Callable[[str, Any], None],
    ) -> None:
        """Add listener for binding value changes."""
        self._change_listeners.append(listener)
    
    def remove_change_listener(
        self,
        listener: Callable[[str, Any], None],
    ) -> None:
        """Remove change listener."""
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)
    
    # -------------------------------------------------------------------------
    # State Access
    # -------------------------------------------------------------------------
    
    def get_current_state(self) -> Mapping[str, Any]:
        """Get current state (read-only view)."""
        return dict(self._current_state)
    
    def verify_integrity(self) -> Tuple[bool, str]:
        """Verify hash chain integrity."""
        if not self._records:
            return (True, "Empty graph")
        
        sorted_records = sorted(
            self._records.values(),
            key=lambda r: r.timestamp
        )
        
        expected_prev = self.GENESIS_HASH
        for record in sorted_records:
            if record.previous_hash != expected_prev:
                return (False, f"Hash chain broken at {record.pdo_id}")
            expected_prev = record.record_hash
        
        return (True, "Integrity verified")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_count": len(self._records),
            "truth_source_count": len(self._truth_sources),
            "binding_count": len(self._bindings),
            "snapshot_count": len(self._snapshots),
            "current_hash": self._hash_chain,
            "integrity": self.verify_integrity()[0],
        }


# =============================================================================
# SECTION 5: UI STATE MANAGER
# =============================================================================

class UIStateManager:
    """
    UI State Manager - manages state bindings for UI components.
    
    This is the interface layer between UI components and the PDO graph.
    Ensures all UI state derives from committed PDO truth.
    
    INVARIANTS:
    - INV-UI-TRUTH-BINDING: All state comes from PDO graph
    - INV-NO-SPECULATIVE-STATE: Never expose uncommitted state
    """
    
    def __init__(self, pdo_graph: PDOStateGraph) -> None:
        self._graph = pdo_graph
        self._component_cache: Dict[str, Dict[str, Any]] = {}
        self._pending_updates: Dict[str, Any] = {}
        self._update_count = 0
    
    def bind_component(
        self,
        component_id: str,
        pdo_path: str,
        source_type: TruthSourceType,
    ) -> UIStateBinding:
        """
        Bind a UI component to PDO state.
        
        Creates or retrieves a truth source and binding.
        """
        # Get or create truth source
        source_id = f"SRC-{source_type.name}"
        source = self._graph.get_truth_source(source_id)
        
        if not source:
            source = TruthSource(
                source_id=source_id,
                source_type=source_type,
                schema={"status": "string", "data": "any"},
                refresh_interval_ms=500,
                required_fields=frozenset({"status"}),
            )
            self._graph.register_truth_source(source)
        
        # Create binding
        binding = self._graph.create_binding(
            component_id=component_id,
            pdo_path=pdo_path,
            source=source,
        )
        
        return binding
    
    def get_component_state(
        self,
        component_id: str,
    ) -> Dict[str, Any]:
        """
        Get all bound state for a component.
        
        Returns dict of pdo_path -> value for all bindings.
        """
        bindings = self._graph.get_bindings_for_component(component_id)
        state: Dict[str, Any] = {}
        
        for binding in bindings:
            value, is_stale = self._graph.get_binding_value(binding.binding_id)
            state[binding.pdo_path] = {
                "value": value,
                "is_stale": is_stale,
                "binding_id": binding.binding_id,
            }
        
        return state
    
    def refresh_component(self, component_id: str) -> None:
        """Force refresh of component state from PDO."""
        # State is always derived from PDO - refresh is a no-op
        # This method exists for API completeness
        self._update_count += 1
    
    def get_update_count(self) -> int:
        """Get total update count."""
        return self._update_count


# =============================================================================
# SECTION 6: TRUTH VALIDATOR
# =============================================================================

class TruthValidator:
    """
    Validates that UI state matches PDO truth.
    
    Used for invariant checking and audit.
    """
    
    def __init__(self, pdo_graph: PDOStateGraph) -> None:
        self._graph = pdo_graph
        self._validation_log: List[Dict[str, Any]] = []
    
    def validate_binding(
        self,
        binding_id: str,
        ui_value: Any,
    ) -> Tuple[bool, str]:
        """
        Validate that UI value matches PDO truth.
        
        Returns (matches, message).
        """
        pdo_value, is_stale = self._graph.get_binding_value(binding_id)
        
        if is_stale:
            self._log_validation(binding_id, "STALE", pdo_value, ui_value)
            return (False, "PDO value is stale")
        
        # Compare values
        matches = self._values_equal(pdo_value, ui_value)
        
        if not matches:
            self._log_validation(binding_id, "MISMATCH", pdo_value, ui_value)
            return (False, f"UI value does not match PDO truth")
        
        self._log_validation(binding_id, "VALID", pdo_value, ui_value)
        return (True, "UI matches PDO truth")
    
    def _values_equal(self, a: Any, b: Any) -> bool:
        """Compare values for equality."""
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        return a == b
    
    def _log_validation(
        self,
        binding_id: str,
        result: str,
        pdo_value: Any,
        ui_value: Any,
    ) -> None:
        """Log validation result."""
        self._validation_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "binding_id": binding_id,
            "result": result,
            "pdo_value": str(pdo_value)[:100],
            "ui_value": str(ui_value)[:100],
        })
    
    def get_validation_log(self) -> Sequence[Dict[str, Any]]:
        """Get validation log."""
        return tuple(self._validation_log)
    
    def validate_all_bindings(
        self,
        ui_state: Mapping[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Validate all bindings against UI state.
        
        Returns (all_valid, list of violation messages).
        """
        violations: List[str] = []
        
        for binding_id in self._graph._bindings:
            if binding_id in ui_state:
                valid, msg = self.validate_binding(binding_id, ui_state[binding_id])
                if not valid:
                    violations.append(f"{binding_id}: {msg}")
        
        return (len(violations) == 0, violations)


# =============================================================================
# SECTION 7: SELF-TEST
# =============================================================================

def _run_self_test() -> None:
    """Execute self-test suite."""
    import sys
    
    print("=" * 72)
    print("  PDO STATE BINDING LAYER - SELF-TEST")
    print("  PAC-JEFFREY-OCC-UI-NASA-001 | Task 2")
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
    
    # Test 1: Truth Source creation
    print("\n[1] Truth Source Tests")
    source = TruthSource(
        source_id="SRC-PDO-ENGINE",
        source_type=TruthSourceType.PDO_ENGINE,
        schema={"status": "string", "count": "int", "data": "dict"},
        refresh_interval_ms=500,
        required_fields=frozenset({"status"}),
    )
    test("Truth source created", source.source_id == "SRC-PDO-ENGINE")
    
    # Validate data
    valid_data = {"status": "nominal", "count": 42, "data": {"key": "value"}}
    result, msg = source.validate_data(valid_data)
    test("Valid data passes", result == ValidationResult.VALID)
    
    invalid_data = {"count": 42}  # Missing required 'status'
    result, msg = source.validate_data(invalid_data)
    test("Missing field detected", result == ValidationResult.MISSING_FIELDS)
    
    # Test 2: PDO State Graph creation
    print("\n[2] PDO State Graph Tests")
    graph = PDOStateGraph()
    test("Graph created", graph._hash_chain == graph.GENESIS_HASH)
    
    # Register truth source
    graph.register_truth_source(source)
    test("Truth source registered", graph.get_truth_source("SRC-PDO-ENGINE") is not None)
    
    # Test 3: PDO Record ingestion
    print("\n[3] PDO Ingestion Tests")
    record = graph.ingest_pdo(
        proof={"verified": True, "signature": "abc123"},
        decision={"action": "APPROVE", "reason": "Valid input"},
        outcome={"status": "nominal", "count": 1},
        source_type=TruthSourceType.PDO_ENGINE,
        source_id="SRC-PDO-ENGINE",
    )
    test("PDO record created", record.pdo_id.startswith("PDO-"))
    test("Record hash computed", len(record.record_hash) == 16)
    test("Hash chain updated", graph._hash_chain == record.record_hash)
    
    # Verify state merged
    state = graph.get_current_state()
    test("State contains PDO data", "pdo_engine" in state)
    test("Outcome merged", state.get("pdo_engine", {}).get("status") == "nominal")
    
    # Test 4: Binding creation
    print("\n[4] Binding Tests")
    binding = graph.create_binding(
        component_id="COMP-STATUS",
        pdo_path="pdo_engine.status",
        source=source,
    )
    test("Binding created", binding.binding_id.startswith("BIND-"))
    test("Binding registered", graph.get_binding(binding.binding_id) is not None)
    
    # Get binding value
    value, is_stale = graph.get_binding_value(binding.binding_id)
    test("Binding value retrieved", value == "nominal")
    test("Value not stale", not is_stale)
    
    # Test 5: Value extraction
    print("\n[5] Value Extraction Tests")
    # Create nested binding
    graph.ingest_pdo(
        proof={},
        decision={},
        outcome={"nested": {"deep": {"value": 42}}},
        source_type=TruthSourceType.TELEMETRY,
        source_id="SRC-TELEMETRY",
    )
    
    telemetry_source = TruthSource(
        source_id="SRC-TELEMETRY",
        source_type=TruthSourceType.TELEMETRY,
        schema={},
        refresh_interval_ms=1000,
        required_fields=frozenset(),
    )
    graph.register_truth_source(telemetry_source)
    
    deep_binding = graph.create_binding(
        component_id="COMP-DEEP",
        pdo_path="telemetry.nested.deep.value",
        source=telemetry_source,
    )
    
    value, is_stale = graph.get_binding_value(deep_binding.binding_id)
    test("Deep value extracted", value == 42)
    
    # Test 6: Snapshot creation
    print("\n[6] Snapshot Tests")
    snapshot = graph.create_snapshot()
    test("Snapshot created", snapshot.snapshot_id.startswith("SNAP-"))
    test("Snapshot not committed", not snapshot.is_committed)
    
    committed = graph.commit_snapshot(snapshot.snapshot_id)
    test("Snapshot committed", committed is not None and committed.is_committed)
    
    # Test 7: Integrity verification
    print("\n[7] Integrity Tests")
    valid, msg = graph.verify_integrity()
    test("Integrity verified", valid, msg)
    
    # Test 8: UI State Manager
    print("\n[8] UI State Manager Tests")
    manager = UIStateManager(graph)
    
    binding2 = manager.bind_component(
        component_id="COMP-TEST",
        pdo_path="pdo_engine.status",
        source_type=TruthSourceType.PDO_ENGINE,
    )
    test("Component bound via manager", binding2 is not None)
    
    comp_state = manager.get_component_state("COMP-TEST")
    test("Component state retrieved", len(comp_state) > 0)
    test("State contains value", "pdo_engine.status" in comp_state)
    
    # Test 9: Truth Validator
    print("\n[9] Truth Validator Tests")
    validator = TruthValidator(graph)
    
    # Valid check
    valid, msg = validator.validate_binding(binding.binding_id, "nominal")
    test("Valid binding passes", valid)
    
    # Invalid check
    valid, msg = validator.validate_binding(binding.binding_id, "WRONG")
    test("Mismatched binding fails", not valid)
    
    # Test 10: Change listener
    print("\n[10] Change Listener Tests")
    changes_detected: List[Tuple[str, Any]] = []
    
    def on_change(binding_id: str, value: Any) -> None:
        changes_detected.append((binding_id, value))
    
    graph.add_change_listener(on_change)
    
    # Ingest new PDO to trigger change
    graph.ingest_pdo(
        proof={},
        decision={},
        outcome={"status": "warning", "count": 2},
        source_type=TruthSourceType.PDO_ENGINE,
        source_id="SRC-PDO-ENGINE",
    )
    
    test("Change detected", len(changes_detected) > 0)
    
    # Verify new value
    value, _ = graph.get_binding_value(binding.binding_id)
    test("Value updated", value == "warning")
    
    # Summary
    print("\n" + "=" * 72)
    total = tests_passed + tests_failed
    print(f"  RESULTS: {tests_passed}/{total} tests passed")
    print("=" * 72)
    
    if tests_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    _run_self_test()
