"""
CI Guard Pipeline

Enforces WRAP presence validation before BER issuance.
Per PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-LOAD-024.

Agent: GID-07 (Dan) — DevOps/CI Lead

Invariant: INV-CI-001 - CI must fail if any WRAP is missing at BER time
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from core.governance.pdo_dependency_graph import (
    PDODependencyGraph,
    NodeStatus,
    get_dependency_graph,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

CI_GUARD_CONFIG = {
    "require_all_wraps": True,
    "allow_partial_ber": False,
    "enforce_ordering": True,
    "timeout_seconds": 300,
    "max_retries": 3,
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class PipelineStage(Enum):
    """CI pipeline stages."""
    WRAP_COLLECTION = "WRAP_COLLECTION"
    WRAP_VALIDATION = "WRAP_VALIDATION"
    DEPENDENCY_CHECK = "DEPENDENCY_CHECK"
    BER_PREPARATION = "BER_PREPARATION"
    BER_ISSUANCE = "BER_ISSUANCE"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class ValidationResult(Enum):
    """Result of a validation check."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class CIGuardError(Exception):
    """Base exception for CI guard errors."""
    pass


class MissingWRAPError(CIGuardError):
    """Raised when a required WRAP is missing (INV-CI-001)."""
    pass


class OrderingViolationError(CIGuardError):
    """Raised when dependency ordering is violated."""
    pass


class PipelineFailedError(CIGuardError):
    """Raised when the CI pipeline fails."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WRAPArtifact:
    """Represents a WRAP artifact from an agent."""
    wrap_id: str
    agent_gid: str
    pdo_ids: List[str]
    pac_id: str
    status: str  # SUBMITTED | VALIDATED | REJECTED
    submitted_at: str
    validated_at: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "wrap_id": self.wrap_id,
            "agent_gid": self.agent_gid,
            "pdo_ids": self.pdo_ids,
            "pac_id": self.pac_id,
            "status": self.status,
            "submitted_at": self.submitted_at,
            "validated_at": self.validated_at,
            "validation_errors": self.validation_errors,
        }


@dataclass
class ValidationCheck:
    """Result of a single validation check."""
    check_id: str
    check_name: str
    result: ValidationResult
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    executed_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


@dataclass
class PipelineRun:
    """Represents a CI pipeline execution."""
    run_id: str
    pac_id: str
    expected_agents: List[str]
    current_stage: PipelineStage
    received_wraps: Dict[str, WRAPArtifact]
    validation_checks: List[ValidationCheck]
    started_at: str
    completed_at: Optional[str] = None
    final_status: Optional[str] = None  # SUCCESS | FAILED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "pac_id": self.pac_id,
            "expected_agents": self.expected_agents,
            "current_stage": self.current_stage.value,
            "received_wraps": {
                k: v.to_dict() for k, v in self.received_wraps.items()
            },
            "validation_checks": [
                {
                    "check_id": c.check_id,
                    "check_name": c.check_name,
                    "result": c.result.value,
                    "message": c.message,
                }
                for c in self.validation_checks
            ],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "final_status": self.final_status,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CI GUARD
# ═══════════════════════════════════════════════════════════════════════════════

class CIGuardPipeline:
    """
    CI pipeline guard that enforces WRAP presence and ordering.
    
    Implements INV-CI-001: CI must fail if any WRAP is missing at BER time.
    """
    
    def __init__(
        self,
        dependency_graph: Optional[PDODependencyGraph] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the CI guard pipeline."""
        self._dependency_graph = dependency_graph or get_dependency_graph()
        self._config = {**CI_GUARD_CONFIG, **(config or {})}
        self._lock = threading.RLock()
        
        # Active pipeline runs
        self._runs: Dict[str, PipelineRun] = {}
        
        # Run counter
        self._run_counter = 0

    @property
    def config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()

    # ─────────────────────────────────────────────────────────────────────────
    # Pipeline Management
    # ─────────────────────────────────────────────────────────────────────────

    def start_pipeline(
        self,
        pac_id: str,
        expected_agents: List[str],
    ) -> PipelineRun:
        """
        Start a new CI pipeline run for a PAC.
        
        Args:
            pac_id: The PAC being executed
            expected_agents: List of agent GIDs expected to submit WRAPs
        """
        with self._lock:
            self._run_counter += 1
            run_id = f"CI-RUN-{pac_id}-{self._run_counter:04d}"
            
            run = PipelineRun(
                run_id=run_id,
                pac_id=pac_id,
                expected_agents=expected_agents,
                current_stage=PipelineStage.WRAP_COLLECTION,
                received_wraps={},
                validation_checks=[],
                started_at=datetime.utcnow().isoformat() + "Z",
            )
            
            self._runs[run_id] = run
            
            return run

    def get_pipeline_run(self, run_id: str) -> Optional[PipelineRun]:
        """Get a pipeline run by ID."""
        with self._lock:
            return self._runs.get(run_id)

    # ─────────────────────────────────────────────────────────────────────────
    # WRAP Collection
    # ─────────────────────────────────────────────────────────────────────────

    def submit_wrap(
        self,
        run_id: str,
        agent_gid: str,
        wrap_id: str,
        pdo_ids: List[str],
    ) -> WRAPArtifact:
        """
        Submit a WRAP artifact from an agent.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise CIGuardError(f"Pipeline run not found: {run_id}")
            
            if run.current_stage not in (
                PipelineStage.WRAP_COLLECTION,
                PipelineStage.WRAP_VALIDATION,
            ):
                raise CIGuardError(
                    f"Cannot submit WRAP in stage {run.current_stage.value}"
                )
            
            wrap = WRAPArtifact(
                wrap_id=wrap_id,
                agent_gid=agent_gid,
                pdo_ids=pdo_ids,
                pac_id=run.pac_id,
                status="SUBMITTED",
                submitted_at=datetime.utcnow().isoformat() + "Z",
            )
            
            run.received_wraps[agent_gid] = wrap
            
            return wrap

    # ─────────────────────────────────────────────────────────────────────────
    # Validation Checks
    # ─────────────────────────────────────────────────────────────────────────

    def check_all_wraps_present(self, run_id: str) -> ValidationCheck:
        """
        Check that all expected WRAPs are present.
        
        INV-CI-001: CI must fail if any WRAP is missing at BER time.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise CIGuardError(f"Pipeline run not found: {run_id}")
            
            received = set(run.received_wraps.keys())
            expected = set(run.expected_agents)
            missing = expected - received
            
            if missing:
                result = ValidationResult.FAIL
                message = f"Missing WRAPs from agents: {sorted(missing)}"
            else:
                result = ValidationResult.PASS
                message = f"All {len(expected)} expected WRAPs received"
            
            check = ValidationCheck(
                check_id=f"CHK-WRAP-PRESENCE-{run_id}",
                check_name="WRAP Presence Check (INV-CI-001)",
                result=result,
                message=message,
                details={
                    "expected": sorted(expected),
                    "received": sorted(received),
                    "missing": sorted(missing),
                },
            )
            
            run.validation_checks.append(check)
            
            return check

    def check_dependency_ordering(self, run_id: str) -> ValidationCheck:
        """
        Check that dependencies are satisfied in correct order.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise CIGuardError(f"Pipeline run not found: {run_id}")
            
            if not self._config["enforce_ordering"]:
                check = ValidationCheck(
                    check_id=f"CHK-ORDERING-{run_id}",
                    check_name="Dependency Ordering Check",
                    result=ValidationResult.SKIP,
                    message="Ordering enforcement disabled",
                )
                run.validation_checks.append(check)
                return check
            
            # Get all PDOs from WRAPs
            all_pdo_ids: Set[str] = set()
            for wrap in run.received_wraps.values():
                all_pdo_ids.update(wrap.pdo_ids)
            
            # Check each PDO's dependencies
            violations: List[str] = []
            
            for pdo_id in all_pdo_ids:
                try:
                    deps = self._dependency_graph.get_dependencies(pdo_id)
                    for dep in deps:
                        if dep.pdo_id not in all_pdo_ids:
                            violations.append(
                                f"{pdo_id} depends on {dep.pdo_id} which is not in WRAPs"
                            )
                except Exception:
                    pass  # Node might not exist in graph
            
            if violations:
                result = ValidationResult.FAIL
                message = f"Found {len(violations)} ordering violations"
            else:
                result = ValidationResult.PASS
                message = "All dependencies satisfied"
            
            check = ValidationCheck(
                check_id=f"CHK-ORDERING-{run_id}",
                check_name="Dependency Ordering Check",
                result=result,
                message=message,
                details={"violations": violations},
            )
            
            run.validation_checks.append(check)
            
            return check

    def check_no_blocked_pdos(self, run_id: str) -> ValidationCheck:
        """
        Check that no PDOs are in BLOCKED state.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise CIGuardError(f"Pipeline run not found: {run_id}")
            
            blocked_pdos: List[str] = []
            
            for wrap in run.received_wraps.values():
                for pdo_id in wrap.pdo_ids:
                    try:
                        status = self._dependency_graph.get_node_status(pdo_id)
                        if status == NodeStatus.BLOCKED:
                            blocked_pdos.append(pdo_id)
                    except Exception:
                        pass
            
            if blocked_pdos:
                result = ValidationResult.FAIL
                message = f"Found {len(blocked_pdos)} blocked PDOs"
            else:
                result = ValidationResult.PASS
                message = "No blocked PDOs"
            
            check = ValidationCheck(
                check_id=f"CHK-BLOCKED-{run_id}",
                check_name="Blocked PDO Check",
                result=result,
                message=message,
                details={"blocked_pdos": blocked_pdos},
            )
            
            run.validation_checks.append(check)
            
            return check

    # ─────────────────────────────────────────────────────────────────────────
    # Pipeline Execution
    # ─────────────────────────────────────────────────────────────────────────

    def run_validation(self, run_id: str) -> List[ValidationCheck]:
        """
        Run all validation checks for a pipeline.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise CIGuardError(f"Pipeline run not found: {run_id}")
            
            run.current_stage = PipelineStage.WRAP_VALIDATION
            
            checks = [
                self.check_all_wraps_present(run_id),
                self.check_dependency_ordering(run_id),
                self.check_no_blocked_pdos(run_id),
            ]
            
            return checks

    def can_issue_ber(self, run_id: str) -> Tuple[bool, List[str]]:
        """
        Check if BER can be issued based on validation results.
        
        INV-CI-001: Returns False if any WRAP is missing.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise CIGuardError(f"Pipeline run not found: {run_id}")
            
            # Run validation if not done
            if run.current_stage == PipelineStage.WRAP_COLLECTION:
                self.run_validation(run_id)
            
            failures: List[str] = []
            
            for check in run.validation_checks:
                if check.result == ValidationResult.FAIL:
                    failures.append(f"{check.check_name}: {check.message}")
            
            can_issue = len(failures) == 0
            
            if can_issue:
                run.current_stage = PipelineStage.BER_PREPARATION
            else:
                run.current_stage = PipelineStage.FAILED
            
            return (can_issue, failures)

    def complete_pipeline(
        self,
        run_id: str,
        success: bool,
    ) -> PipelineRun:
        """
        Mark pipeline as complete.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise CIGuardError(f"Pipeline run not found: {run_id}")
            
            run.completed_at = datetime.utcnow().isoformat() + "Z"
            run.final_status = "SUCCESS" if success else "FAILED"
            run.current_stage = (
                PipelineStage.COMPLETE if success else PipelineStage.FAILED
            )
            
            return run

    # ─────────────────────────────────────────────────────────────────────────
    # Guard Function (Main Entry Point)
    # ─────────────────────────────────────────────────────────────────────────

    def guard_ber_issuance(
        self,
        run_id: str,
    ) -> None:
        """
        Guard function that raises if BER cannot be issued.
        
        INV-CI-001: Raises MissingWRAPError if any WRAP is missing.
        """
        can_issue, failures = self.can_issue_ber(run_id)
        
        if not can_issue:
            # Check specifically for missing WRAPs
            run = self._runs.get(run_id)
            if run:
                received = set(run.received_wraps.keys())
                expected = set(run.expected_agents)
                missing = expected - received
                
                if missing:
                    raise MissingWRAPError(
                        f"Cannot issue BER. Missing WRAPs from: {sorted(missing)}. "
                        f"INV-CI-001 violation."
                    )
            
            raise PipelineFailedError(
                f"Cannot issue BER. Validation failures:\n" +
                "\n".join(f"  • {f}" for f in failures)
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Export
    # ─────────────────────────────────────────────────────────────────────────

    def export_run_report(self, run_id: str) -> str:
        """Export pipeline run as JSON report."""
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise CIGuardError(f"Pipeline run not found: {run_id}")
            
            return json.dumps(run.to_dict(), indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

_global_ci_guard: Optional[CIGuardPipeline] = None
_global_lock = threading.Lock()


def get_ci_guard(config: Optional[Dict[str, Any]] = None) -> CIGuardPipeline:
    """Get or create the global CI guard instance."""
    global _global_ci_guard
    
    with _global_lock:
        if _global_ci_guard is None:
            _global_ci_guard = CIGuardPipeline(config=config)
        return _global_ci_guard


def reset_ci_guard() -> None:
    """Reset the global CI guard (for testing)."""
    global _global_ci_guard
    
    with _global_lock:
        _global_ci_guard = None
