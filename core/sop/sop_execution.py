# ═══════════════════════════════════════════════════════════════════════════════
# SOP Execution Engine — Read-Only Execution Primitives
# PAC-BENSON-P25: PARALLEL PLATFORM EXPANSION & OPERATOR-GRADE EXECUTION
# Agent: CODY (GID-01) — Backend / APIs / PDO
# Agent: CINDY (GID-04) — Backend Support
# ═══════════════════════════════════════════════════════════════════════════════

"""
SOP Execution Engine — Enterprise Execution Primitives

PURPOSE:
    Provide execution primitives for SOP workflows with read-only guarantees
    for OCC display. Actual mutations are delegated to backend services.

EXECUTION MODEL:
    1. SOPs are validated against preconditions
    2. Approvals are collected based on severity
    3. Execution is dispatched to backend services
    4. Results are recorded in audit log
    5. OCC displays read-only execution state

INVARIANTS:
    INV-SOP-EXEC-001: SOP execution requires all preconditions satisfied
    INV-SOP-EXEC-002: Approval count must meet severity requirements
    INV-SOP-EXEC-003: All executions produce immutable audit records
    INV-SOP-EXEC-004: OCC cannot trigger SOP execution directly
    INV-SOP-EXEC-005: Execution state is read-only to OCC

EXECUTION MODE: PARALLEL
LANES: BACKEND (GID-01, GID-04)
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.sop.sop_library import (
    SOPApproval,
    SOPDefinition,
    SOPExecutionRecord,
    SOPExecutionState,
    SOPRegistry,
    SOPSeverity,
)


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class SOPValidationError(Exception):
    """Raised when SOP validation fails."""

    pass


class SOPPreconditionError(Exception):
    """Raised when SOP preconditions are not satisfied."""

    pass


class SOPApprovalError(Exception):
    """Raised when SOP approval requirements are not met."""

    pass


class SOPExecutionError(Exception):
    """Raised when SOP execution fails."""

    pass


class SOPReadOnlyViolationError(Exception):
    """
    Raised when OCC attempts to mutate SOP state.

    INV-SOP-EXEC-004: OCC cannot trigger SOP execution directly
    """

    pass


# ═══════════════════════════════════════════════════════════════════════════════
# READ-ONLY EXECUTION VIEW
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SOPExecutionView:
    """
    Read-only view of SOP execution for OCC display.

    INV-SOP-EXEC-005: Execution state is read-only to OCC
    """

    execution_id: str
    sop_id: str
    sop_name: str
    state: SOPExecutionState
    initiator_id: str
    initiated_at: datetime
    approval_count: int
    approval_required: int
    progress_percent: float
    error_message: Optional[str]
    can_view_details: bool

    @classmethod
    def from_record(
        cls, record: SOPExecutionRecord, sop_def: SOPDefinition
    ) -> "SOPExecutionView":
        """Create read-only view from execution record."""
        approval_required = cls._get_approval_requirement(sop_def.severity)

        # Calculate progress
        if record.state == SOPExecutionState.COMPLETED:
            progress = 100.0
        elif record.state == SOPExecutionState.FAILED:
            progress = 0.0
        elif record.state == SOPExecutionState.EXECUTING:
            progress = 50.0
        elif record.state == SOPExecutionState.APPROVED:
            progress = 25.0
        else:
            progress = 10.0

        return cls(
            execution_id=record.execution_id,
            sop_id=record.sop_id,
            sop_name=sop_def.name,
            state=record.state,
            initiator_id=record.initiator_id,
            initiated_at=record.initiated_at,
            approval_count=len(record.approvals),
            approval_required=approval_required,
            progress_percent=progress,
            error_message=record.error_message,
            can_view_details=True,
        )

    @staticmethod
    def _get_approval_requirement(severity: SOPSeverity) -> int:
        """Get required approval count for severity level."""
        if severity == SOPSeverity.CRITICAL:
            return 3  # Dual approval + management
        elif severity == SOPSeverity.HIGH:
            return 2  # Dual approval
        elif severity == SOPSeverity.MEDIUM:
            return 1  # Single approval
        else:
            return 0  # Self-approval allowed


# ═══════════════════════════════════════════════════════════════════════════════
# PRECONDITION VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════


class PreconditionValidator:
    """
    Validates SOP preconditions before execution.

    INV-SOP-EXEC-001: SOP execution requires all preconditions satisfied
    """

    def __init__(self) -> None:
        self._validators: Dict[str, Callable[[Dict[str, Any]], bool]] = {}

    def register_validator(
        self, condition_id: str, validator: Callable[[Dict[str, Any]], bool]
    ) -> None:
        """Register a precondition validator function."""
        self._validators[condition_id] = validator

    def validate(
        self, sop_def: SOPDefinition, context: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, bool], List[str]]:
        """
        Validate all preconditions for an SOP.

        Returns:
            - overall_valid: True if all preconditions pass
            - results: Dict mapping condition_id to pass/fail
            - errors: List of error messages for failed conditions
        """
        results: Dict[str, bool] = {}
        errors: List[str] = []

        for precondition in sop_def.preconditions:
            validator = self._validators.get(precondition.condition_id)
            if validator is None:
                # No validator registered - fail closed
                results[precondition.condition_id] = False
                errors.append(
                    f"[{precondition.condition_id}] No validator registered"
                )
                continue

            try:
                passed = validator(context)
                results[precondition.condition_id] = passed
                if not passed:
                    errors.append(
                        f"[{precondition.condition_id}] {precondition.error_message}"
                    )
            except Exception as e:
                results[precondition.condition_id] = False
                errors.append(f"[{precondition.condition_id}] Validation error: {e}")

        overall_valid = all(results.values()) if results else False
        return overall_valid, results, errors


# ═══════════════════════════════════════════════════════════════════════════════
# APPROVAL MANAGER
# ═══════════════════════════════════════════════════════════════════════════════


class ApprovalManager:
    """
    Manages SOP approval workflows.

    INV-SOP-EXEC-002: Approval count must meet severity requirements
    INV-SOP-003: Critical SOPs require dual-approval workflow
    """

    def __init__(self) -> None:
        self._pending_approvals: Dict[str, List[SOPApproval]] = {}

    def get_required_approvals(self, sop_def: SOPDefinition) -> int:
        """Get required approval count based on severity."""
        return SOPExecutionView._get_approval_requirement(sop_def.severity)

    def has_sufficient_approvals(
        self, execution_id: str, sop_def: SOPDefinition
    ) -> bool:
        """Check if execution has sufficient approvals."""
        approvals = self._pending_approvals.get(execution_id, [])
        required = self.get_required_approvals(sop_def)
        return len(approvals) >= required

    def add_approval(
        self,
        execution_id: str,
        approver_id: str,
        approver_role: str,
        notes: Optional[str] = None,
    ) -> SOPApproval:
        """Add an approval for an execution."""
        if execution_id not in self._pending_approvals:
            self._pending_approvals[execution_id] = []

        # Check for duplicate approver
        existing_approvers = {
            a.approver_id for a in self._pending_approvals[execution_id]
        }
        if approver_id in existing_approvers:
            raise SOPApprovalError(
                f"Approver {approver_id} has already approved this execution"
            )

        approval = SOPApproval(
            approver_id=approver_id,
            approver_role=approver_role,
            approved_at=datetime.now(timezone.utc),
            approval_notes=notes,
        )
        self._pending_approvals[execution_id].append(approval)
        return approval

    def get_approvals(self, execution_id: str) -> List[SOPApproval]:
        """Get all approvals for an execution."""
        return self._pending_approvals.get(execution_id, [])

    def clear_approvals(self, execution_id: str) -> None:
        """Clear approvals for an execution (on completion or rejection)."""
        self._pending_approvals.pop(execution_id, None)


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION STORE (In-Memory for OCC Display)
# ═══════════════════════════════════════════════════════════════════════════════


class SOPExecutionStore:
    """
    In-memory store for SOP execution records.

    Provides read-only access for OCC dashboard display.
    Actual persistence is handled by backend services.

    INV-SOP-EXEC-003: All executions produce immutable audit records
    """

    _instance: Optional["SOPExecutionStore"] = None
    _initialized: bool = False

    def __new__(cls) -> "SOPExecutionStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if SOPExecutionStore._initialized:
            return
        SOPExecutionStore._initialized = True

        self._records: Dict[str, SOPExecutionRecord] = {}
        self._by_sop: Dict[str, List[str]] = {}  # sop_id -> [execution_ids]
        self._by_initiator: Dict[str, List[str]] = {}  # initiator_id -> [execution_ids]

    def store(self, record: SOPExecutionRecord) -> str:
        """Store an execution record."""
        self._records[record.execution_id] = record

        # Index by SOP
        if record.sop_id not in self._by_sop:
            self._by_sop[record.sop_id] = []
        if record.execution_id not in self._by_sop[record.sop_id]:
            self._by_sop[record.sop_id].append(record.execution_id)

        # Index by initiator
        if record.initiator_id not in self._by_initiator:
            self._by_initiator[record.initiator_id] = []
        if record.execution_id not in self._by_initiator[record.initiator_id]:
            self._by_initiator[record.initiator_id].append(record.execution_id)

        return record.execution_id

    def get(self, execution_id: str) -> Optional[SOPExecutionRecord]:
        """Get execution record by ID."""
        return self._records.get(execution_id)

    def get_by_sop(self, sop_id: str) -> List[SOPExecutionRecord]:
        """Get all executions for an SOP."""
        execution_ids = self._by_sop.get(sop_id, [])
        return [self._records[eid] for eid in execution_ids if eid in self._records]

    def get_recent(self, limit: int = 50) -> List[SOPExecutionRecord]:
        """Get recent executions across all SOPs."""
        sorted_records = sorted(
            self._records.values(),
            key=lambda r: r.initiated_at,
            reverse=True,
        )
        return sorted_records[:limit]

    def get_active(self) -> List[SOPExecutionRecord]:
        """Get currently active (non-terminal) executions."""
        terminal_states = {
            SOPExecutionState.COMPLETED,
            SOPExecutionState.FAILED,
            SOPExecutionState.ROLLED_BACK,
            SOPExecutionState.REJECTED,
        }
        return [r for r in self._records.values() if r.state not in terminal_states]

    def count(self) -> int:
        """Return count of stored records."""
        return len(self._records)


# ═══════════════════════════════════════════════════════════════════════════════
# SOP EXECUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class SOPExecutionEngine:
    """
    SOP Execution Engine — Orchestrates SOP execution workflow.

    WORKFLOW:
    1. Validate SOP exists
    2. Check preconditions
    3. Collect approvals
    4. Execute via backend service
    5. Record results
    6. Provide read-only view to OCC

    This engine is for backend use. OCC gets read-only views.
    """

    def __init__(
        self,
        registry: Optional[SOPRegistry] = None,
        validator: Optional[PreconditionValidator] = None,
        approval_manager: Optional[ApprovalManager] = None,
        store: Optional[SOPExecutionStore] = None,
    ) -> None:
        self.registry = registry or SOPRegistry()
        self.validator = validator or PreconditionValidator()
        self.approval_manager = approval_manager or ApprovalManager()
        self.store = store or SOPExecutionStore()

        # Backend service handlers (pluggable)
        self._handlers: Dict[str, Callable[[SOPExecutionRecord], Dict[str, Any]]] = {}

    def register_handler(
        self, sop_id: str, handler: Callable[[SOPExecutionRecord], Dict[str, Any]]
    ) -> None:
        """Register a backend handler for an SOP."""
        self._handlers[sop_id] = handler

    def initiate(
        self,
        sop_id: str,
        initiator_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> SOPExecutionRecord:
        """
        Initiate an SOP execution.

        Returns the execution record in PENDING state.
        """
        sop_def = self.registry.get(sop_id)
        if sop_def is None:
            raise SOPValidationError(f"Unknown SOP: {sop_id}")

        execution_id = f"EXEC-{uuid.uuid4().hex[:12].upper()}"

        record = SOPExecutionRecord(
            execution_id=execution_id,
            sop_id=sop_id,
            sop_version=sop_def.version,
            initiator_id=initiator_id,
            initiated_at=datetime.now(timezone.utc),
            state=SOPExecutionState.PENDING,
            input_parameters=parameters or {},
        )

        self.store.store(record)
        return record

    def validate_preconditions(
        self, execution_id: str, context: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate preconditions for an execution.

        Returns (valid, errors).
        """
        record = self.store.get(execution_id)
        if record is None:
            return False, [f"Execution not found: {execution_id}"]

        sop_def = self.registry.get(record.sop_id)
        if sop_def is None:
            return False, [f"SOP not found: {record.sop_id}"]

        valid, checks, errors = self.validator.validate(sop_def, context)
        record.precondition_checks = checks
        return valid, errors

    def approve(
        self,
        execution_id: str,
        approver_id: str,
        approver_role: str,
        notes: Optional[str] = None,
    ) -> bool:
        """
        Add approval to an execution.

        Returns True if now fully approved.
        """
        record = self.store.get(execution_id)
        if record is None:
            raise SOPValidationError(f"Execution not found: {execution_id}")

        if record.state != SOPExecutionState.PENDING:
            raise SOPApprovalError(
                f"Cannot approve execution in state: {record.state.value}"
            )

        sop_def = self.registry.get(record.sop_id)
        if sop_def is None:
            raise SOPValidationError(f"SOP not found: {record.sop_id}")

        approval = self.approval_manager.add_approval(
            execution_id, approver_id, approver_role, notes
        )
        record.approvals.append(approval)

        if self.approval_manager.has_sufficient_approvals(execution_id, sop_def):
            record.state = SOPExecutionState.APPROVED
            return True

        return False

    def execute(self, execution_id: str) -> SOPExecutionRecord:
        """
        Execute an approved SOP.

        Must be called from backend service, not OCC.
        """
        record = self.store.get(execution_id)
        if record is None:
            raise SOPExecutionError(f"Execution not found: {execution_id}")

        if record.state != SOPExecutionState.APPROVED:
            raise SOPExecutionError(
                f"Cannot execute SOP in state: {record.state.value}"
            )

        sop_def = self.registry.get(record.sop_id)
        if sop_def is None:
            raise SOPExecutionError(f"SOP not found: {record.sop_id}")

        # Check approval requirements one more time
        if not self.approval_manager.has_sufficient_approvals(execution_id, sop_def):
            raise SOPApprovalError("Insufficient approvals for execution")

        record.state = SOPExecutionState.EXECUTING
        record.started_at = datetime.now(timezone.utc)

        # Execute via handler
        handler = self._handlers.get(record.sop_id)
        if handler is None:
            # No handler = simulation mode
            record.output_results = {"mode": "simulation", "success": True}
            record.state = SOPExecutionState.COMPLETED
        else:
            try:
                results = handler(record)
                record.output_results = results
                record.state = SOPExecutionState.COMPLETED
            except Exception as e:
                record.error_message = str(e)
                record.state = SOPExecutionState.FAILED

        record.completed_at = datetime.now(timezone.utc)
        self.approval_manager.clear_approvals(execution_id)
        return record

    def get_view(self, execution_id: str) -> Optional[SOPExecutionView]:
        """
        Get read-only view for OCC display.

        INV-SOP-EXEC-005: Execution state is read-only to OCC
        """
        record = self.store.get(execution_id)
        if record is None:
            return None

        sop_def = self.registry.get(record.sop_id)
        if sop_def is None:
            return None

        return SOPExecutionView.from_record(record, sop_def)

    def get_active_views(self) -> List[SOPExecutionView]:
        """Get all active execution views for OCC dashboard."""
        views: List[SOPExecutionView] = []
        for record in self.store.get_active():
            view = self.get_view(record.execution_id)
            if view is not None:
                views.append(view)
        return views


# ═══════════════════════════════════════════════════════════════════════════════
# OCC READ-ONLY FACADE
# ═══════════════════════════════════════════════════════════════════════════════


class OCCSOPFacade:
    """
    Read-only facade for OCC SOP display.

    INV-SOP-EXEC-004: OCC cannot trigger SOP execution directly
    INV-SOP-EXEC-005: Execution state is read-only to OCC

    This class ONLY provides read operations. Any write attempt
    raises SOPReadOnlyViolationError.
    """

    def __init__(self, engine: Optional[SOPExecutionEngine] = None) -> None:
        self._engine = engine or SOPExecutionEngine()

    # ─────────────────────────────────────────────────────────────────────────
    # READ OPERATIONS (Allowed for OCC)
    # ─────────────────────────────────────────────────────────────────────────

    def list_sops(self) -> List[Dict[str, Any]]:
        """List all available SOPs (read-only)."""
        registry = self._engine.registry
        return [
            {
                "sop_id": sop.sop_id,
                "name": sop.name,
                "description": sop.description,
                "category": sop.category.value,
                "severity": sop.severity.value,
                "reversibility": sop.reversibility.value,
                "precondition_count": len(sop.preconditions),
                "requires_dual_approval": registry.requires_dual_approval(sop.sop_id),
            }
            for sop in registry.get_all()
        ]

    def get_sop(self, sop_id: str) -> Optional[Dict[str, Any]]:
        """Get SOP details (read-only)."""
        sop = self._engine.registry.get(sop_id)
        if sop is None:
            return None
        return {
            "sop_id": sop.sop_id,
            "name": sop.name,
            "description": sop.description,
            "category": sop.category.value,
            "severity": sop.severity.value,
            "reversibility": sop.reversibility.value,
            "version": sop.version,
            "preconditions": [
                {
                    "condition_id": p.condition_id,
                    "description": p.description,
                }
                for p in sop.preconditions
            ],
            "estimated_duration_seconds": sop.estimated_duration_seconds,
            "requires_maintenance_window": sop.requires_maintenance_window,
            "documentation_url": sop.documentation_url,
        }

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution view (read-only)."""
        view = self._engine.get_view(execution_id)
        if view is None:
            return None
        return {
            "execution_id": view.execution_id,
            "sop_id": view.sop_id,
            "sop_name": view.sop_name,
            "state": view.state.value,
            "initiator_id": view.initiator_id,
            "initiated_at": view.initiated_at.isoformat(),
            "approval_count": view.approval_count,
            "approval_required": view.approval_required,
            "progress_percent": view.progress_percent,
            "error_message": view.error_message,
        }

    def list_active_executions(self) -> List[Dict[str, Any]]:
        """List active executions (read-only)."""
        views = self._engine.get_active_views()
        return [
            {
                "execution_id": v.execution_id,
                "sop_id": v.sop_id,
                "sop_name": v.sop_name,
                "state": v.state.value,
                "progress_percent": v.progress_percent,
            }
            for v in views
        ]

    def get_execution_count(self) -> int:
        """Get count of stored executions (read-only)."""
        return self._engine.store.count()

    # ─────────────────────────────────────────────────────────────────────────
    # WRITE OPERATIONS (Blocked for OCC)
    # ─────────────────────────────────────────────────────────────────────────

    def _block_write(self, operation: str) -> None:
        """Block write operations from OCC."""
        raise SOPReadOnlyViolationError(
            f"OCC cannot perform write operation: {operation}. "
            "INV-SOP-EXEC-004: OCC cannot trigger SOP execution directly."
        )

    def initiate_sop(self, *args: Any, **kwargs: Any) -> None:
        """BLOCKED: OCC cannot initiate SOPs."""
        self._block_write("initiate_sop")

    def approve_sop(self, *args: Any, **kwargs: Any) -> None:
        """BLOCKED: OCC cannot approve SOPs."""
        self._block_write("approve_sop")

    def execute_sop(self, *args: Any, **kwargs: Any) -> None:
        """BLOCKED: OCC cannot execute SOPs."""
        self._block_write("execute_sop")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Exceptions
    "SOPValidationError",
    "SOPPreconditionError",
    "SOPApprovalError",
    "SOPExecutionError",
    "SOPReadOnlyViolationError",
    # Views
    "SOPExecutionView",
    # Components
    "PreconditionValidator",
    "ApprovalManager",
    "SOPExecutionStore",
    "SOPExecutionEngine",
    "OCCSOPFacade",
]
