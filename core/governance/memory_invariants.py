# ═══════════════════════════════════════════════════════════════════════════════
# Memory Invariants — Neural Memory Governance Rules (INV-MEM-*)
# PAC-BENSON-P26: TITANS-READY NEURAL MEMORY ARCHITECTURE (SHADOW MODE)
# Agent: ALEX (GID-08)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Memory Invariants — Governance Rules for Neural Memory

PURPOSE:
    Define and enforce invariants for neural memory operations to ensure
    integrity, auditability, and safety in Titans-ready architecture.

INVARIANT CATEGORIES:
    INV-MEM-001..003: State Integrity (immutability, hashing, snapshots)
    INV-MEM-004..006: Operational Safety (freeze, rollback, learning)
    INV-MEM-007..009: Audit Trail (updates, routing, anchoring)
    INV-MEM-010..012: Shadow Mode (no inference, no weights, no training)

ENFORCEMENT MODES:
    STRICT: Violation raises exception
    WARN: Violation logs warning but continues
    AUDIT: Violation recorded but not enforced

LANE: ARCHITECTURE_ONLY (NON-INFERENCING)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class InvariantCategory(Enum):
    """Category of memory invariant."""

    STATE_INTEGRITY = "STATE_INTEGRITY"
    OPERATIONAL_SAFETY = "OPERATIONAL_SAFETY"
    AUDIT_TRAIL = "AUDIT_TRAIL"
    SHADOW_MODE = "SHADOW_MODE"


class EnforcementMode(Enum):
    """How invariant violations are handled."""

    STRICT = "STRICT"  # Raise exception
    WARN = "WARN"  # Log warning, continue
    AUDIT = "AUDIT"  # Record only


class ViolationSeverity(Enum):
    """Severity of invariant violation."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MemoryInvariant:
    """
    Definition of a memory invariant.

    Each invariant has a unique ID, description, check function,
    and enforcement configuration.
    """

    invariant_id: str
    name: str
    description: str
    category: InvariantCategory
    severity: ViolationSeverity
    enforcement: EnforcementMode = EnforcementMode.STRICT
    pdo_bound: bool = False  # If True, linked to PDO hash binding
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate invariant ID format."""
        if not self.invariant_id.startswith("INV-MEM-"):
            raise ValueError(f"Invariant ID must start with 'INV-MEM-': {self.invariant_id}")


# ═══════════════════════════════════════════════════════════════════════════════
# VIOLATION RECORD
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ViolationRecord:
    """Record of an invariant violation."""

    violation_id: str
    invariant_id: str
    severity: ViolationSeverity
    context: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved: bool = False
    resolution_note: Optional[str] = None

    def compute_hash(self) -> str:
        """Compute hash for audit integrity."""
        data = {
            "violation_id": self.violation_id,
            "invariant_id": self.invariant_id,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# P26 MEMORY INVARIANTS DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════

# State Integrity Invariants
INV_MEM_001 = MemoryInvariant(
    invariant_id="INV-MEM-001",
    name="Snapshot Immutability",
    description="Memory state is immutable once snapshotted. No modifications allowed to existing snapshots.",
    category=InvariantCategory.STATE_INTEGRITY,
    severity=ViolationSeverity.CRITICAL,
    enforcement=EnforcementMode.STRICT,
    pdo_bound=True,
)

INV_MEM_002 = MemoryInvariant(
    invariant_id="INV-MEM-002",
    name="Update Audit Trail",
    description="All memory updates require complete audit trail with pre/post state hashes.",
    category=InvariantCategory.AUDIT_TRAIL,
    severity=ViolationSeverity.CRITICAL,
    enforcement=EnforcementMode.STRICT,
    pdo_bound=True,
)

INV_MEM_003 = MemoryInvariant(
    invariant_id="INV-MEM-003",
    name="Snapshot Hash Integrity",
    description="Memory snapshots must include cryptographic integrity hash that is verifiable.",
    category=InvariantCategory.STATE_INTEGRITY,
    severity=ViolationSeverity.CRITICAL,
    enforcement=EnforcementMode.STRICT,
    pdo_bound=True,
)

# Operational Safety Invariants
INV_MEM_004 = MemoryInvariant(
    invariant_id="INV-MEM-004",
    name="Frozen Memory Protection",
    description="Frozen memory cannot be modified. Any update attempt must fail.",
    category=InvariantCategory.OPERATIONAL_SAFETY,
    severity=ViolationSeverity.CRITICAL,
    enforcement=EnforcementMode.STRICT,
)

INV_MEM_005 = MemoryInvariant(
    invariant_id="INV-MEM-005",
    name="Rollback Chain Integrity",
    description="Memory rollback must preserve chain integrity. No orphaned snapshots allowed.",
    category=InvariantCategory.OPERATIONAL_SAFETY,
    severity=ViolationSeverity.HIGH,
    enforcement=EnforcementMode.STRICT,
)

INV_MEM_006 = MemoryInvariant(
    invariant_id="INV-MEM-006",
    name="No Production Learning",
    description="No runtime learning or test-time training in production mode.",
    category=InvariantCategory.SHADOW_MODE,
    severity=ViolationSeverity.CRITICAL,
    enforcement=EnforcementMode.STRICT,
)

# Audit Trail Invariants
INV_MEM_007 = MemoryInvariant(
    invariant_id="INV-MEM-007",
    name="Routing Decision Logging",
    description="All dual-brain routing decisions must be logged with decision metadata.",
    category=InvariantCategory.AUDIT_TRAIL,
    severity=ViolationSeverity.MEDIUM,
    enforcement=EnforcementMode.WARN,
)

INV_MEM_008 = MemoryInvariant(
    invariant_id="INV-MEM-008",
    name="Surprise Metric Recording",
    description="Surprise metrics that trigger memory updates must be recorded.",
    category=InvariantCategory.AUDIT_TRAIL,
    severity=ViolationSeverity.MEDIUM,
    enforcement=EnforcementMode.WARN,
)

INV_MEM_009 = MemoryInvariant(
    invariant_id="INV-MEM-009",
    name="Ledger Anchor Requirement",
    description="Production snapshots must be anchored to ledger within anchor window.",
    category=InvariantCategory.AUDIT_TRAIL,
    severity=ViolationSeverity.HIGH,
    enforcement=EnforcementMode.AUDIT,
    pdo_bound=True,
)

# Shadow Mode Invariants
INV_MEM_010 = MemoryInvariant(
    invariant_id="INV-MEM-010",
    name="No Inference Execution",
    description="Shadow mode must not execute actual neural inference.",
    category=InvariantCategory.SHADOW_MODE,
    severity=ViolationSeverity.CRITICAL,
    enforcement=EnforcementMode.STRICT,
)

INV_MEM_011 = MemoryInvariant(
    invariant_id="INV-MEM-011",
    name="No Model Weights",
    description="Shadow mode architecture must not include model weights.",
    category=InvariantCategory.SHADOW_MODE,
    severity=ViolationSeverity.CRITICAL,
    enforcement=EnforcementMode.STRICT,
)

INV_MEM_012 = MemoryInvariant(
    invariant_id="INV-MEM-012",
    name="Interface-Only Validation",
    description="Shadow mode components must be interface-only, no runtime behavior.",
    category=InvariantCategory.SHADOW_MODE,
    severity=ViolationSeverity.HIGH,
    enforcement=EnforcementMode.STRICT,
)


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


class MemoryInvariantRegistry:
    """
    Registry for memory invariants.

    Provides registration, lookup, and enforcement of memory invariants.
    """

    _instance: Optional["MemoryInvariantRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "MemoryInvariantRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if MemoryInvariantRegistry._initialized:
            return
        MemoryInvariantRegistry._initialized = True

        self._invariants: Dict[str, MemoryInvariant] = {}
        self._check_functions: Dict[str, Callable[..., Tuple[bool, str]]] = {}
        self._violations: List[ViolationRecord] = []
        self._violation_counter = 0

        # Register P26 invariants
        self._register_p26_invariants()

    def _register_p26_invariants(self) -> None:
        """Register all P26 memory invariants."""
        invariants = [
            INV_MEM_001, INV_MEM_002, INV_MEM_003,
            INV_MEM_004, INV_MEM_005, INV_MEM_006,
            INV_MEM_007, INV_MEM_008, INV_MEM_009,
            INV_MEM_010, INV_MEM_011, INV_MEM_012,
        ]
        for inv in invariants:
            self._invariants[inv.invariant_id] = inv

    def register_check(
        self,
        invariant_id: str,
        check_fn: Callable[..., Tuple[bool, str]],
    ) -> bool:
        """Register a check function for an invariant."""
        if invariant_id not in self._invariants:
            return False
        self._check_functions[invariant_id] = check_fn
        return True

    def get(self, invariant_id: str) -> Optional[MemoryInvariant]:
        """Get invariant by ID."""
        return self._invariants.get(invariant_id)

    def list_all(self) -> List[MemoryInvariant]:
        """List all registered invariants."""
        return list(self._invariants.values())

    def list_by_category(self, category: InvariantCategory) -> List[MemoryInvariant]:
        """List invariants by category."""
        return [inv for inv in self._invariants.values() if inv.category == category]

    def list_pdo_bound(self) -> List[MemoryInvariant]:
        """List invariants bound to PDO hash."""
        return [inv for inv in self._invariants.values() if inv.pdo_bound]

    def check(
        self,
        invariant_id: str,
        context: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Check an invariant against context.

        Returns (passed, error_message).
        """
        invariant = self._invariants.get(invariant_id)
        if not invariant:
            return False, f"Unknown invariant: {invariant_id}"

        check_fn = self._check_functions.get(invariant_id)
        if not check_fn:
            # No check function registered, assume pass
            return True, None

        try:
            passed, message = check_fn(context)
        except Exception as e:
            passed, message = False, str(e)

        if not passed:
            self._record_violation(invariant, context, message)

        return passed, message if not passed else None

    def check_all(self, context: Dict[str, Any]) -> Dict[str, Tuple[bool, Optional[str]]]:
        """Check all invariants against context."""
        results = {}
        for inv_id in self._invariants:
            results[inv_id] = self.check(inv_id, context)
        return results

    def _record_violation(
        self,
        invariant: MemoryInvariant,
        context: Dict[str, Any],
        message: str,
    ) -> ViolationRecord:
        """Record an invariant violation."""
        self._violation_counter += 1
        violation = ViolationRecord(
            violation_id=f"VIOL-MEM-{self._violation_counter:06d}",
            invariant_id=invariant.invariant_id,
            severity=invariant.severity,
            context={
                "message": message,
                "enforcement": invariant.enforcement.value,
                **context,
            },
        )
        self._violations.append(violation)

        # Enforce based on mode
        if invariant.enforcement == EnforcementMode.STRICT:
            raise InvariantViolationError(
                f"{invariant.invariant_id} [{invariant.severity.value}]: {message}"
            )

        return violation

    def get_violations(self, limit: int = 100) -> List[ViolationRecord]:
        """Get recent violations."""
        return self._violations[-limit:]

    def count(self) -> int:
        """Return count of registered invariants."""
        return len(self._invariants)

    def violation_count(self) -> int:
        """Return count of recorded violations."""
        return len(self._violations)


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class InvariantViolationError(Exception):
    """Raised when a STRICT invariant is violated."""

    pass


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT CHECKER HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def check_snapshot_immutability(context: Dict[str, Any]) -> Tuple[bool, str]:
    """Check INV-MEM-001: Snapshot Immutability."""
    snapshot = context.get("snapshot")
    if snapshot is None:
        return True, "No snapshot in context"

    # Check if snapshot has been modified
    original_hash = context.get("original_hash")
    current_hash = context.get("current_hash")

    if original_hash and current_hash and original_hash != current_hash:
        return False, f"Snapshot modified: {original_hash} != {current_hash}"

    return True, "Snapshot immutability preserved"


def check_frozen_protection(context: Dict[str, Any]) -> Tuple[bool, str]:
    """Check INV-MEM-004: Frozen Memory Protection."""
    is_frozen = context.get("is_frozen", False)
    is_update_attempt = context.get("is_update_attempt", False)

    if is_frozen and is_update_attempt:
        return False, "Cannot update frozen memory"

    return True, "Frozen protection enforced"


def check_no_production_learning(context: Dict[str, Any]) -> Tuple[bool, str]:
    """Check INV-MEM-006: No Production Learning."""
    mode = context.get("mode", "SHADOW")
    is_learning = context.get("is_learning", False)
    environment = context.get("environment", "development")

    if environment == "production" and is_learning:
        return False, "Learning disabled in production mode"

    if mode == "LEARNING" and environment == "production":
        return False, "LEARNING mode forbidden in production"

    return True, "No production learning verified"


def check_shadow_mode_inference(context: Dict[str, Any]) -> Tuple[bool, str]:
    """Check INV-MEM-010: No Inference Execution."""
    mode = context.get("mode", "SHADOW")
    has_inference = context.get("has_inference_execution", False)

    if mode == "SHADOW" and has_inference:
        return False, "Shadow mode cannot execute inference"

    return True, "Shadow mode inference check passed"


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTER DEFAULT CHECKS
# ═══════════════════════════════════════════════════════════════════════════════


def register_default_checks(registry: MemoryInvariantRegistry) -> None:
    """Register default check functions for invariants."""
    registry.register_check("INV-MEM-001", check_snapshot_immutability)
    registry.register_check("INV-MEM-004", check_frozen_protection)
    registry.register_check("INV-MEM-006", check_no_production_learning)
    registry.register_check("INV-MEM-010", check_shadow_mode_inference)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "InvariantCategory",
    "EnforcementMode",
    "ViolationSeverity",
    # Data classes
    "MemoryInvariant",
    "ViolationRecord",
    # Invariant definitions
    "INV_MEM_001",
    "INV_MEM_002",
    "INV_MEM_003",
    "INV_MEM_004",
    "INV_MEM_005",
    "INV_MEM_006",
    "INV_MEM_007",
    "INV_MEM_008",
    "INV_MEM_009",
    "INV_MEM_010",
    "INV_MEM_011",
    "INV_MEM_012",
    # Registry
    "MemoryInvariantRegistry",
    # Exceptions
    "InvariantViolationError",
    # Check helpers
    "check_snapshot_immutability",
    "check_frozen_protection",
    "check_no_production_learning",
    "check_shadow_mode_inference",
    "register_default_checks",
]
