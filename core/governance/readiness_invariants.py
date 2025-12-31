# ═══════════════════════════════════════════════════════════════════════════════
# Readiness Invariants — INV-READY-001..006
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agent: ALEX (GID-08)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Readiness Invariants — Graduation Gate Checks

PURPOSE:
    Define mandatory invariants that must pass before Titans architecture
    can graduate from SHADOW to LIVE mode. These are NOT performance 
    targets but safety and correctness gates.

INVARIANTS:
    INV-READY-001: Determinism Required
    INV-READY-002: No Live Inference
    INV-READY-003: Snapshot Integrity
    INV-READY-004: Routing Coverage
    INV-READY-005: Cost Bounded
    INV-READY-006: Governance Clearance

SEVERITY:
    All invariants are CRITICAL — any violation blocks graduation.

CONSTRAINTS:
    - SHADOW MODE only (no actual inference)
    - FAIL-CLOSED on any violation
    - All checks must be deterministic

LANE: EXECUTION (GOVERNANCE)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# READINESS ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class ReadinessGate(Enum):
    """Graduation gate status."""

    OPEN = "OPEN"  # Gate passed
    CLOSED = "CLOSED"  # Gate blocked
    PENDING = "PENDING"  # Not yet evaluated


class ReadinessLevel(Enum):
    """Current readiness level."""

    SHADOW = "SHADOW"  # Shadow mode only
    PILOT = "PILOT"  # Limited live testing
    STAGED = "STAGED"  # Staged rollout
    LIVE = "LIVE"  # Full production


class InvariantCategory(Enum):
    """Category of readiness invariant."""

    DETERMINISM = "DETERMINISM"
    SAFETY = "SAFETY"
    INTEGRITY = "INTEGRITY"
    COVERAGE = "COVERAGE"
    COST = "COST"
    GOVERNANCE = "GOVERNANCE"


# ═══════════════════════════════════════════════════════════════════════════════
# READINESS INVARIANT DEFINITION
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ReadinessInvariant:
    """Definition of a readiness invariant."""

    invariant_id: str
    name: str
    description: str
    category: InvariantCategory
    gate: ReadinessGate = ReadinessGate.PENDING
    threshold: Optional[float] = None
    actual_value: Optional[float] = None
    check_function: Optional[Callable[..., bool]] = None
    evidence: Dict[str, Any] = field(default_factory=dict)
    last_checked: Optional[str] = None
    violation_message: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.invariant_id.startswith("INV-READY-"):
            raise ValueError(f"Readiness invariant ID must start with 'INV-READY-': {self.invariant_id}")

    @property
    def is_passing(self) -> bool:
        return self.gate == ReadinessGate.OPEN

    @property
    def is_blocking(self) -> bool:
        return self.gate == ReadinessGate.CLOSED

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate the invariant against provided context."""
        self.last_checked = datetime.now(timezone.utc).isoformat()

        if self.check_function:
            try:
                result = self.check_function(context)
                if result:
                    self.gate = ReadinessGate.OPEN
                    self.violation_message = None
                else:
                    self.gate = ReadinessGate.CLOSED
                return result
            except Exception as e:
                self.gate = ReadinessGate.CLOSED
                self.violation_message = str(e)
                return False
        else:
            # No check function, evaluate based on threshold
            if self.threshold is not None and self.actual_value is not None:
                result = self.actual_value >= self.threshold
                self.gate = ReadinessGate.OPEN if result else ReadinessGate.CLOSED
                if not result:
                    self.violation_message = f"Value {self.actual_value} below threshold {self.threshold}"
                return result
            self.gate = ReadinessGate.PENDING
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "gate": self.gate.value,
            "threshold": self.threshold,
            "actual_value": self.actual_value,
            "is_passing": self.is_passing,
            "is_blocking": self.is_blocking,
            "evidence": self.evidence,
            "last_checked": self.last_checked,
            "violation_message": self.violation_message,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CHECK FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def check_determinism_required(context: Dict[str, Any]) -> bool:
    """
    INV-READY-001: All replay sequences must be deterministic.

    Requires:
    - determinism_score >= 1.0 (100% deterministic)
    - mismatch_count == 0
    """
    score = context.get("determinism_score", 0.0)
    mismatches = context.get("mismatch_count", -1)

    if mismatches == -1:  # Not yet tested
        return False

    return score >= 1.0 and mismatches == 0


def check_no_live_inference(context: Dict[str, Any]) -> bool:
    """
    INV-READY-002: No live inference calls permitted in SHADOW mode.

    Requires:
    - live_inference_count == 0
    - mode == "SHADOW"
    """
    mode = context.get("mode", "")
    live_calls = context.get("live_inference_count", -1)

    if mode != "SHADOW":
        return False

    return live_calls == 0


def check_snapshot_integrity(context: Dict[str, Any]) -> bool:
    """
    INV-READY-003: All snapshots must have valid integrity proofs.

    Requires:
    - snapshot_integrity_rate >= 1.0
    - corrupted_snapshots == 0
    """
    integrity_rate = context.get("snapshot_integrity_rate", 0.0)
    corrupted = context.get("corrupted_snapshots", -1)

    return integrity_rate >= 1.0 and corrupted == 0


def check_routing_coverage(context: Dict[str, Any]) -> bool:
    """
    INV-READY-004: Routing decisions must cover all query types.

    Requires:
    - routing_coverage >= 0.95 (95% coverage)
    - unhandled_routes == 0
    """
    coverage = context.get("routing_coverage", 0.0)
    unhandled = context.get("unhandled_routes", -1)

    return coverage >= 0.95 and unhandled == 0


def check_cost_bounded(context: Dict[str, Any]) -> bool:
    """
    INV-READY-005: Estimated costs must be within budget.

    Requires:
    - estimated_cost_usd <= max_budget_usd
    - cost_variance <= 0.1 (10% variance)
    """
    estimated = context.get("estimated_cost_usd", float("inf"))
    max_budget = context.get("max_budget_usd", 0.0)
    variance = context.get("cost_variance", 1.0)

    return estimated <= max_budget and variance <= 0.1


def check_governance_clearance(context: Dict[str, Any]) -> bool:
    """
    INV-READY-006: Governance must approve graduation.

    Requires:
    - governance_approved == True
    - pending_violations == 0
    - approval_timestamp present
    """
    approved = context.get("governance_approved", False)
    violations = context.get("pending_violations", -1)
    timestamp = context.get("approval_timestamp")

    return approved and violations == 0 and timestamp is not None


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════


# Pre-defined readiness invariants
INV_READY_001 = ReadinessInvariant(
    invariant_id="INV-READY-001",
    name="Determinism Required",
    description="All replay sequences must produce identical outputs",
    category=InvariantCategory.DETERMINISM,
    threshold=1.0,
    check_function=check_determinism_required,
)

INV_READY_002 = ReadinessInvariant(
    invariant_id="INV-READY-002",
    name="No Live Inference",
    description="No live inference calls permitted in SHADOW mode",
    category=InvariantCategory.SAFETY,
    check_function=check_no_live_inference,
)

INV_READY_003 = ReadinessInvariant(
    invariant_id="INV-READY-003",
    name="Snapshot Integrity",
    description="All snapshots must have valid integrity proofs",
    category=InvariantCategory.INTEGRITY,
    threshold=1.0,
    check_function=check_snapshot_integrity,
)

INV_READY_004 = ReadinessInvariant(
    invariant_id="INV-READY-004",
    name="Routing Coverage",
    description="Routing decisions must cover all query types",
    category=InvariantCategory.COVERAGE,
    threshold=0.95,
    check_function=check_routing_coverage,
)

INV_READY_005 = ReadinessInvariant(
    invariant_id="INV-READY-005",
    name="Cost Bounded",
    description="Estimated costs must be within budget",
    category=InvariantCategory.COST,
    check_function=check_cost_bounded,
)

INV_READY_006 = ReadinessInvariant(
    invariant_id="INV-READY-006",
    name="Governance Clearance",
    description="Governance must approve graduation",
    category=InvariantCategory.GOVERNANCE,
    check_function=check_governance_clearance,
)


class ReadinessInvariantRegistry:
    """
    Registry for readiness invariants.

    Manages:
    - Invariant registration
    - Batch evaluation
    - Gate status aggregation
    - Readiness scoring
    """

    def __init__(self) -> None:
        self._invariants: Dict[str, ReadinessInvariant] = {}
        self._evaluation_history: List[Dict[str, Any]] = []

        # Register default invariants
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default readiness invariants (fresh copies)."""
        import copy
        defaults = [
            INV_READY_001,
            INV_READY_002,
            INV_READY_003,
            INV_READY_004,
            INV_READY_005,
            INV_READY_006,
        ]
        for inv in defaults:
            # Create fresh copy to avoid shared state between instances
            self.register(copy.deepcopy(inv))

    def register(self, invariant: ReadinessInvariant) -> None:
        """Register a readiness invariant."""
        self._invariants[invariant.invariant_id] = invariant

    def get(self, invariant_id: str) -> Optional[ReadinessInvariant]:
        """Get invariant by ID."""
        return self._invariants.get(invariant_id)

    def list_all(self) -> List[ReadinessInvariant]:
        """List all registered invariants."""
        return list(self._invariants.values())

    def list_by_category(self, category: InvariantCategory) -> List[ReadinessInvariant]:
        """List invariants by category."""
        return [inv for inv in self._invariants.values() if inv.category == category]

    def evaluate_all(self, context: Dict[str, Any]) -> Dict[str, bool]:
        """Evaluate all invariants against context."""
        results = {}
        for inv_id, inv in self._invariants.items():
            results[inv_id] = inv.evaluate(context)

        # Record evaluation
        self._evaluation_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context_hash": hashlib.sha256(json.dumps(context, sort_keys=True, default=str).encode()).hexdigest()[:16],
            "results": results,
        })

        return results

    def evaluate_one(self, invariant_id: str, context: Dict[str, Any]) -> bool:
        """Evaluate a single invariant."""
        inv = self._invariants.get(invariant_id)
        if inv is None:
            return False
        return inv.evaluate(context)

    def get_readiness_score(self) -> float:
        """Calculate overall readiness score (0.0 to 1.0)."""
        if not self._invariants:
            return 0.0

        passing = sum(1 for inv in self._invariants.values() if inv.is_passing)
        return passing / len(self._invariants)

    def get_blocking_invariants(self) -> List[ReadinessInvariant]:
        """Get list of blocking invariants."""
        return [inv for inv in self._invariants.values() if inv.is_blocking]

    def get_pending_invariants(self) -> List[ReadinessInvariant]:
        """Get list of pending invariants."""
        return [inv for inv in self._invariants.values() if inv.gate == ReadinessGate.PENDING]

    def is_ready_for_graduation(self) -> bool:
        """Check if all invariants pass for graduation."""
        return all(inv.is_passing for inv in self._invariants.values())

    def get_current_level(self) -> ReadinessLevel:
        """Determine current readiness level based on invariants."""
        if not self._invariants:
            return ReadinessLevel.SHADOW

        score = self.get_readiness_score()

        if score < 0.5:
            return ReadinessLevel.SHADOW
        elif score < 0.8:
            return ReadinessLevel.PILOT
        elif score < 1.0:
            return ReadinessLevel.STAGED
        else:
            return ReadinessLevel.LIVE

    def generate_report(self) -> Dict[str, Any]:
        """Generate readiness report."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "readiness_score": round(self.get_readiness_score(), 4),
            "current_level": self.get_current_level().value,
            "is_ready": self.is_ready_for_graduation(),
            "invariant_count": len(self._invariants),
            "passing_count": sum(1 for inv in self._invariants.values() if inv.is_passing),
            "blocking_count": len(self.get_blocking_invariants()),
            "pending_count": len(self.get_pending_invariants()),
            "invariants": {inv_id: inv.to_dict() for inv_id, inv in self._invariants.items()},
            "blocking_details": [
                {"id": inv.invariant_id, "name": inv.name, "message": inv.violation_message}
                for inv in self.get_blocking_invariants()
            ],
            "evaluation_history_count": len(self._evaluation_history),
        }

    def compute_report_hash(self) -> str:
        """Compute hash of current readiness state."""
        data = {
            "invariants": {inv_id: inv.gate.value for inv_id, inv in self._invariants.items()},
            "score": self.get_readiness_score(),
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "ReadinessGate",
    "ReadinessLevel",
    "InvariantCategory",
    # Data classes
    "ReadinessInvariant",
    # Check functions
    "check_determinism_required",
    "check_no_live_inference",
    "check_snapshot_integrity",
    "check_routing_coverage",
    "check_cost_bounded",
    "check_governance_clearance",
    # Pre-defined invariants
    "INV_READY_001",
    "INV_READY_002",
    "INV_READY_003",
    "INV_READY_004",
    "INV_READY_005",
    "INV_READY_006",
    # Registry
    "ReadinessInvariantRegistry",
]
