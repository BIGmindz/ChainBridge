# ═══════════════════════════════════════════════════════════════════════════════
# Readiness Graduation Checklist — HOLD/FROZEN Only
# PAC-BENSON-P27: BENCHMARK & READINESS EXECUTION
# Agent: PAX (GID-05)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Readiness Graduation Checklist — Complete Graduation Gate System

PURPOSE:
    Define the complete checklist required to graduate from SHADOW to LIVE mode.
    All items are currently in HOLD or FROZEN status — no live graduation
    is permitted until all gates pass.

CHECKLIST ITEMS:
    GC-001: Determinism Verified (INV-READY-001)
    GC-002: No Live Inference (INV-READY-002)
    GC-003: Snapshot Integrity (INV-READY-003)
    GC-004: Routing Complete (INV-READY-004)
    GC-005: Cost Bounded (INV-READY-005)
    GC-006: Governance Approved (INV-READY-006)
    GC-007: Benchmark Thresholds Met
    GC-008: Security Review Complete
    GC-009: Rollback Plan Verified
    GC-010: Operator Signoff

CONSTRAINTS:
    - All items HOLD or FROZEN (no auto-pass)
    - Manual operator signoff required
    - FAIL-CLOSED governance
    - Audit trail required

LANE: EXECUTION (GOVERNANCE)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# CHECKLIST ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class ChecklistStatus(Enum):
    """Status of a checklist item."""

    HOLD = "HOLD"  # Waiting for evaluation
    FROZEN = "FROZEN"  # Blocked, cannot proceed
    PASSED = "PASSED"  # Manually verified
    WAIVED = "WAIVED"  # Exempted with approval


class ChecklistCategory(Enum):
    """Category of checklist item."""

    INVARIANT = "INVARIANT"  # Maps to INV-READY-*
    BENCHMARK = "BENCHMARK"  # Performance threshold
    SECURITY = "SECURITY"  # Security review
    OPERATIONS = "OPERATIONS"  # Operational readiness
    GOVERNANCE = "GOVERNANCE"  # Approval/signoff


class GraduationPhase(Enum):
    """Phase of graduation process."""

    PRE_CHECK = "PRE_CHECK"  # Initial validation
    EVALUATION = "EVALUATION"  # Running checks
    APPROVAL = "APPROVAL"  # Awaiting approval
    EXECUTION = "EXECUTION"  # Graduation in progress
    COMPLETE = "COMPLETE"  # Graduated
    ABORTED = "ABORTED"  # Graduation failed


# ═══════════════════════════════════════════════════════════════════════════════
# CHECKLIST ITEM
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ChecklistItem:
    """A single graduation checklist item."""

    item_id: str
    name: str
    description: str
    category: ChecklistCategory
    status: ChecklistStatus = ChecklistStatus.HOLD
    invariant_ref: Optional[str] = None  # Reference to INV-READY-*
    required: bool = True
    evidence: Dict[str, Any] = field(default_factory=dict)
    evaluator: Optional[str] = None  # Who evaluated
    evaluated_at: Optional[str] = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.item_id.startswith("GC-"):
            raise ValueError(f"Checklist item ID must start with 'GC-': {self.item_id}")

    @property
    def is_blocking(self) -> bool:
        return self.required and self.status in (ChecklistStatus.HOLD, ChecklistStatus.FROZEN)

    @property
    def is_cleared(self) -> bool:
        return self.status in (ChecklistStatus.PASSED, ChecklistStatus.WAIVED)

    def mark_passed(self, evaluator: str, evidence: Optional[Dict[str, Any]] = None, notes: str = "") -> None:
        """Mark item as passed."""
        self.status = ChecklistStatus.PASSED
        self.evaluator = evaluator
        self.evaluated_at = datetime.now(timezone.utc).isoformat()
        if evidence:
            self.evidence.update(evidence)
        self.notes = notes

    def mark_frozen(self, reason: str) -> None:
        """Freeze item (cannot proceed)."""
        self.status = ChecklistStatus.FROZEN
        self.notes = reason
        self.evaluated_at = datetime.now(timezone.utc).isoformat()

    def mark_waived(self, evaluator: str, justification: str) -> None:
        """Waive item with justification."""
        self.status = ChecklistStatus.WAIVED
        self.evaluator = evaluator
        self.evaluated_at = datetime.now(timezone.utc).isoformat()
        self.notes = f"WAIVED: {justification}"

    def reset(self) -> None:
        """Reset to HOLD status."""
        self.status = ChecklistStatus.HOLD
        self.evaluator = None
        self.evaluated_at = None
        self.notes = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "status": self.status.value,
            "invariant_ref": self.invariant_ref,
            "required": self.required,
            "is_blocking": self.is_blocking,
            "is_cleared": self.is_cleared,
            "evaluator": self.evaluator,
            "evaluated_at": self.evaluated_at,
            "evidence": self.evidence,
            "notes": self.notes,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GRADUATION RESULT
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class GraduationResult:
    """Result of a graduation attempt."""

    result_id: str
    phase: GraduationPhase
    success: bool
    timestamp: str
    from_level: str  # e.g., "SHADOW"
    to_level: str  # e.g., "PILOT"
    cleared_items: List[str] = field(default_factory=list)
    blocking_items: List[str] = field(default_factory=list)
    waived_items: List[str] = field(default_factory=list)
    operator: Optional[str] = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.result_id.startswith("GRAD-"):
            raise ValueError(f"Graduation result ID must start with 'GRAD-': {self.result_id}")

    def compute_hash(self) -> str:
        """Compute hash of graduation result."""
        data = {
            "result_id": self.result_id,
            "success": self.success,
            "from_level": self.from_level,
            "to_level": self.to_level,
            "cleared": sorted(self.cleared_items),
            "blocking": sorted(self.blocking_items),
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "phase": self.phase.value,
            "success": self.success,
            "timestamp": self.timestamp,
            "from_level": self.from_level,
            "to_level": self.to_level,
            "cleared_items": self.cleared_items,
            "blocking_items": self.blocking_items,
            "waived_items": self.waived_items,
            "operator": self.operator,
            "notes": self.notes,
            "result_hash": self.compute_hash(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PRE-DEFINED CHECKLIST ITEMS
# ═══════════════════════════════════════════════════════════════════════════════


GC_001 = ChecklistItem(
    item_id="GC-001",
    name="Determinism Verified",
    description="All replay sequences must produce identical outputs (INV-READY-001)",
    category=ChecklistCategory.INVARIANT,
    invariant_ref="INV-READY-001",
)

GC_002 = ChecklistItem(
    item_id="GC-002",
    name="No Live Inference",
    description="No live inference calls in SHADOW mode (INV-READY-002)",
    category=ChecklistCategory.INVARIANT,
    invariant_ref="INV-READY-002",
)

GC_003 = ChecklistItem(
    item_id="GC-003",
    name="Snapshot Integrity",
    description="All snapshots have valid integrity proofs (INV-READY-003)",
    category=ChecklistCategory.INVARIANT,
    invariant_ref="INV-READY-003",
)

GC_004 = ChecklistItem(
    item_id="GC-004",
    name="Routing Complete",
    description="All query types have routing coverage (INV-READY-004)",
    category=ChecklistCategory.INVARIANT,
    invariant_ref="INV-READY-004",
)

GC_005 = ChecklistItem(
    item_id="GC-005",
    name="Cost Bounded",
    description="Estimated costs within budget (INV-READY-005)",
    category=ChecklistCategory.INVARIANT,
    invariant_ref="INV-READY-005",
)

GC_006 = ChecklistItem(
    item_id="GC-006",
    name="Governance Approved",
    description="Governance has approved graduation (INV-READY-006)",
    category=ChecklistCategory.INVARIANT,
    invariant_ref="INV-READY-006",
)

GC_007 = ChecklistItem(
    item_id="GC-007",
    name="Benchmark Thresholds Met",
    description="All performance benchmarks meet minimum thresholds",
    category=ChecklistCategory.BENCHMARK,
)

GC_008 = ChecklistItem(
    item_id="GC-008",
    name="Security Review Complete",
    description="Security threat model reviewed and mitigations verified",
    category=ChecklistCategory.SECURITY,
)

GC_009 = ChecklistItem(
    item_id="GC-009",
    name="Rollback Plan Verified",
    description="Rollback procedures tested and documented",
    category=ChecklistCategory.OPERATIONS,
)

GC_010 = ChecklistItem(
    item_id="GC-010",
    name="Operator Signoff",
    description="Human operator has signed off on graduation",
    category=ChecklistCategory.GOVERNANCE,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GRADUATION CHECKLIST
# ═══════════════════════════════════════════════════════════════════════════════


class GraduationChecklist:
    """
    Complete graduation checklist manager.

    Manages:
    - Checklist item registration
    - Status tracking
    - Graduation attempts
    - Audit trail
    """

    def __init__(self) -> None:
        self._items: Dict[str, ChecklistItem] = {}
        self._graduation_history: List[GraduationResult] = []
        self._graduation_counter = 0
        self._current_phase = GraduationPhase.PRE_CHECK

        # Register default items
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default checklist items (fresh copies)."""
        import copy
        defaults = [
            GC_001, GC_002, GC_003, GC_004, GC_005,
            GC_006, GC_007, GC_008, GC_009, GC_010,
        ]
        for item in defaults:
            # Create fresh copy to avoid shared state between instances
            self.register(copy.deepcopy(item))

    def register(self, item: ChecklistItem) -> None:
        """Register a checklist item."""
        self._items[item.item_id] = item

    def get(self, item_id: str) -> Optional[ChecklistItem]:
        """Get item by ID."""
        return self._items.get(item_id)

    def list_all(self) -> List[ChecklistItem]:
        """List all checklist items."""
        return list(self._items.values())

    def list_blocking(self) -> List[ChecklistItem]:
        """List blocking items."""
        return [item for item in self._items.values() if item.is_blocking]

    def list_cleared(self) -> List[ChecklistItem]:
        """List cleared items."""
        return [item for item in self._items.values() if item.is_cleared]

    def list_by_category(self, category: ChecklistCategory) -> List[ChecklistItem]:
        """List items by category."""
        return [item for item in self._items.values() if item.category == category]

    def get_completion_rate(self) -> float:
        """Get completion rate (0.0 to 1.0)."""
        if not self._items:
            return 0.0
        cleared = sum(1 for item in self._items.values() if item.is_cleared)
        return cleared / len(self._items)

    def is_ready_to_graduate(self) -> bool:
        """Check if all required items are cleared."""
        required_items = [item for item in self._items.values() if item.required]
        return all(item.is_cleared for item in required_items)

    def attempt_graduation(
        self,
        from_level: str,
        to_level: str,
        operator: Optional[str] = None,
    ) -> GraduationResult:
        """
        Attempt graduation to next level.

        NOTE: This will ALWAYS return success=False in SHADOW mode
        because all items are HOLD/FROZEN by default.
        """
        self._graduation_counter += 1
        result_id = f"GRAD-{self._graduation_counter:06d}"

        self._current_phase = GraduationPhase.EVALUATION

        cleared = [item.item_id for item in self._items.values() if item.is_cleared]
        blocking = [item.item_id for item in self._items.values() if item.is_blocking]
        waived = [item.item_id for item in self._items.values() if item.status == ChecklistStatus.WAIVED]

        # Determine success
        can_graduate = self.is_ready_to_graduate()

        if can_graduate:
            self._current_phase = GraduationPhase.COMPLETE
        else:
            self._current_phase = GraduationPhase.ABORTED

        result = GraduationResult(
            result_id=result_id,
            phase=self._current_phase,
            success=can_graduate,
            timestamp=datetime.now(timezone.utc).isoformat(),
            from_level=from_level,
            to_level=to_level if can_graduate else from_level,
            cleared_items=cleared,
            blocking_items=blocking,
            waived_items=waived,
            operator=operator,
            notes="Graduation attempt" if can_graduate else "Blocked by uncleared items",
        )

        self._graduation_history.append(result)
        return result

    def reset_all(self) -> None:
        """Reset all items to HOLD status."""
        for item in self._items.values():
            item.reset()
        self._current_phase = GraduationPhase.PRE_CHECK

    def freeze_all(self, reason: str) -> None:
        """Freeze all pending items."""
        for item in self._items.values():
            if item.status == ChecklistStatus.HOLD:
                item.mark_frozen(reason)

    def generate_report(self) -> Dict[str, Any]:
        """Generate checklist report."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_phase": self._current_phase.value,
            "completion_rate": round(self.get_completion_rate(), 4),
            "is_ready": self.is_ready_to_graduate(),
            "total_items": len(self._items),
            "cleared_count": len(self.list_cleared()),
            "blocking_count": len(self.list_blocking()),
            "items": {item_id: item.to_dict() for item_id, item in self._items.items()},
            "blocking_details": [
                {"id": item.item_id, "name": item.name, "status": item.status.value}
                for item in self.list_blocking()
            ],
            "graduation_attempts": len(self._graduation_history),
            "last_graduation": self._graduation_history[-1].to_dict() if self._graduation_history else None,
        }

    def compute_state_hash(self) -> str:
        """Compute hash of current checklist state."""
        data = {
            "items": {item_id: item.status.value for item_id, item in self._items.items()},
            "phase": self._current_phase.value,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "ChecklistStatus",
    "ChecklistCategory",
    "GraduationPhase",
    # Data classes
    "ChecklistItem",
    "GraduationResult",
    # Pre-defined items
    "GC_001",
    "GC_002",
    "GC_003",
    "GC_004",
    "GC_005",
    "GC_006",
    "GC_007",
    "GC_008",
    "GC_009",
    "GC_010",
    # Checklist
    "GraduationChecklist",
]
