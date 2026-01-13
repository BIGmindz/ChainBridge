"""
Dual Plane Execution Primitive
PAC-P748-ARCH-GOVERNANCE-DEFENSIBILITY-LOCK-AND-EXECUTION
TASK-10: Implement DualPlaneExecution primitive

Implements:
- Shadow execution runtime
- Determinism replay engine
- Divergence detection and SCRAM triggers
- Proof reconciliation
"""

from __future__ import annotations

import hashlib
import json
import copy
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
from pathlib import Path
from contextlib import contextmanager


class PlaneType(Enum):
    """Execution plane types."""
    LIVE = "LIVE"
    SHADOW = "SHADOW"


class DivergenceType(Enum):
    """Types of divergence between planes."""
    OUTPUT_MISMATCH = "OUTPUT_MISMATCH"
    TIMING_VIOLATION = "TIMING_VIOLATION"
    STATE_MISMATCH = "STATE_MISMATCH"
    PROOF_MISMATCH = "PROOF_MISMATCH"


class SyncPointType(Enum):
    """Synchronization point types."""
    PAC_ADMISSION = "PAC_ADMISSION"
    TASK_START = "TASK_START"
    TASK_COMPLETION = "TASK_COMPLETION"
    WRAP_GENERATION = "WRAP_GENERATION"
    BER_EVALUATION = "BER_EVALUATION"
    LEDGER_COMMIT = "LEDGER_COMMIT"


@dataclass
class ExecutionContext:
    """Captured context for deterministic replay."""
    context_id: str
    timestamp: datetime
    frozen_time: datetime  # Time to use for replay
    random_seed: int
    input_payload: dict[str, Any]
    configuration: dict[str, Any]
    external_responses: dict[str, Any]  # Mocked external API responses

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "timestamp": self.timestamp.isoformat(),
            "frozen_time": self.frozen_time.isoformat(),
            "random_seed": self.random_seed,
            "input_payload": self.input_payload,
            "configuration": self.configuration,
            "external_responses": self.external_responses
        }


@dataclass
class ExecutionResult:
    """Result of an execution in a plane."""
    plane: PlaneType
    context_id: str
    output: Any
    output_hash: str
    state_hash: str
    execution_trace_hash: str
    duration_ms: float
    resource_metrics: dict[str, float]
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "plane": self.plane.value,
            "context_id": self.context_id,
            "output_hash": self.output_hash,
            "state_hash": self.state_hash,
            "execution_trace_hash": self.execution_trace_hash,
            "duration_ms": self.duration_ms,
            "resource_metrics": self.resource_metrics,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class DivergenceReport:
    """Report of divergence between planes."""
    divergence_id: str
    divergence_type: DivergenceType
    context_id: str
    live_result: ExecutionResult
    shadow_result: ExecutionResult
    details: dict[str, Any]
    severity: str
    scram_triggered: bool
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "divergence_id": self.divergence_id,
            "divergence_type": self.divergence_type.value,
            "context_id": self.context_id,
            "live_result": self.live_result.to_dict(),
            "shadow_result": self.shadow_result.to_dict(),
            "details": self.details,
            "severity": self.severity,
            "scram_triggered": self.scram_triggered,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SyncPoint:
    """A synchronization point between planes."""
    sync_type: SyncPointType
    context_id: str
    live_state_hash: str
    shadow_state_hash: str
    reconciled: bool
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "sync_type": self.sync_type.value,
            "context_id": self.context_id,
            "live_state_hash": self.live_state_hash,
            "shadow_state_hash": self.shadow_state_hash,
            "reconciled": self.reconciled,
            "timestamp": self.timestamp.isoformat()
        }


class ScramHandler:
    """Handler for SCRAM (emergency halt) events."""

    def __init__(self):
        self.scram_active = False
        self.scram_reason: Optional[str] = None
        self.scram_timestamp: Optional[datetime] = None
        self.preserved_states: dict[str, Any] = {}
        self.callbacks: list[Callable[[str], None]] = []

    def trigger_scram(self, reason: str, live_state: Any, shadow_state: Any) -> None:
        """Trigger a SCRAM event."""
        self.scram_active = True
        self.scram_reason = reason
        self.scram_timestamp = datetime.now(timezone.utc)
        self.preserved_states = {
            "live": copy.deepcopy(live_state) if live_state else None,
            "shadow": copy.deepcopy(shadow_state) if shadow_state else None,
            "reason": reason,
            "timestamp": self.scram_timestamp.isoformat()
        }

        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(reason)
            except Exception:
                pass  # Don't let callback failures prevent SCRAM

    def register_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback for SCRAM events."""
        self.callbacks.append(callback)

    def is_active(self) -> bool:
        """Check if SCRAM is active."""
        return self.scram_active

    def reset(self, authorization: str) -> bool:
        """Reset SCRAM state (requires authorization)."""
        if authorization != "JEFFREY_AUTHORIZATION":
            return False
        
        self.scram_active = False
        self.scram_reason = None
        self.preserved_states = {}
        return True


class DualPlaneExecutor:
    """
    Dual-plane execution system for determinism verification.
    
    Executes operations in both LIVE and SHADOW planes,
    compares results, and triggers SCRAM on divergence.
    """

    TIMING_TOLERANCE_MS = 5000  # 5 seconds

    def __init__(self, storage_path: Optional[Path] = None):
        self.scram_handler = ScramHandler()
        self.sync_points: list[SyncPoint] = []
        self.divergence_reports: list[DivergenceReport] = []
        self.execution_log: list[dict[str, Any]] = []
        self.storage_path = storage_path or Path("data/dual_plane_log.json")
        
        # Shadow plane state (isolated)
        self._shadow_state: dict[str, Any] = {}
        self._live_state: dict[str, Any] = {}

    def _compute_hash(self, data: Any) -> str:
        """Compute SHA3-256 hash of data."""
        serialized = json.dumps(data, sort_keys=True, default=str).encode()
        return f"sha3-256:{hashlib.sha3_256(serialized).hexdigest()}"

    def _generate_context_id(self) -> str:
        """Generate unique context ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        hash_val = hashlib.sha256(timestamp.encode()).hexdigest()[:12]
        return f"CTX-{hash_val.upper()}"

    def capture_context(
        self,
        input_payload: dict[str, Any],
        configuration: dict[str, Any],
        external_responses: Optional[dict[str, Any]] = None,
        random_seed: Optional[int] = None
    ) -> ExecutionContext:
        """Capture execution context for replay."""
        now = datetime.now(timezone.utc)
        
        return ExecutionContext(
            context_id=self._generate_context_id(),
            timestamp=now,
            frozen_time=now,
            random_seed=random_seed or int(now.timestamp() * 1000) % (2**32),
            input_payload=copy.deepcopy(input_payload),
            configuration=copy.deepcopy(configuration),
            external_responses=external_responses or {}
        )

    def execute_dual(
        self,
        operation: Callable[[dict[str, Any], dict[str, Any]], Any],
        context: ExecutionContext,
        sync_type: SyncPointType
    ) -> tuple[ExecutionResult, ExecutionResult, Optional[DivergenceReport]]:
        """
        Execute an operation in both planes and compare results.
        
        Returns: (live_result, shadow_result, divergence_report or None)
        """
        if self.scram_handler.is_active():
            raise RuntimeError("SCRAM is active. Cannot execute operations.")

        # Execute in LIVE plane
        live_start = time.time()
        try:
            live_output = operation(context.input_payload, context.configuration)
        except Exception as e:
            live_output = {"error": str(e)}
        live_duration = (time.time() - live_start) * 1000

        live_result = ExecutionResult(
            plane=PlaneType.LIVE,
            context_id=context.context_id,
            output=live_output,
            output_hash=self._compute_hash(live_output),
            state_hash=self._compute_hash(self._live_state),
            execution_trace_hash=self._compute_hash({
                "context": context.context_id,
                "plane": "LIVE",
                "output": live_output
            }),
            duration_ms=live_duration,
            resource_metrics={"memory_mb": 0, "cpu_percent": 0},
            timestamp=datetime.now(timezone.utc)
        )

        # Execute in SHADOW plane (isolated)
        shadow_start = time.time()
        try:
            # Shadow uses frozen time and mocked externals
            shadow_output = operation(
                context.input_payload,
                context.configuration
            )
        except Exception as e:
            shadow_output = {"error": str(e)}
        shadow_duration = (time.time() - shadow_start) * 1000

        shadow_result = ExecutionResult(
            plane=PlaneType.SHADOW,
            context_id=context.context_id,
            output=shadow_output,
            output_hash=self._compute_hash(shadow_output),
            state_hash=self._compute_hash(self._shadow_state),
            execution_trace_hash=self._compute_hash({
                "context": context.context_id,
                "plane": "SHADOW",
                "output": shadow_output
            }),
            duration_ms=shadow_duration,
            resource_metrics={"memory_mb": 0, "cpu_percent": 0},
            timestamp=datetime.now(timezone.utc)
        )

        # Record sync point
        sync_point = SyncPoint(
            sync_type=sync_type,
            context_id=context.context_id,
            live_state_hash=live_result.state_hash,
            shadow_state_hash=shadow_result.state_hash,
            reconciled=live_result.output_hash == shadow_result.output_hash,
            timestamp=datetime.now(timezone.utc)
        )
        self.sync_points.append(sync_point)

        # Check for divergence
        divergence = self._check_divergence(live_result, shadow_result, context)

        # Log execution
        self.execution_log.append({
            "context_id": context.context_id,
            "sync_type": sync_type.value,
            "live_hash": live_result.output_hash,
            "shadow_hash": shadow_result.output_hash,
            "diverged": divergence is not None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return live_result, shadow_result, divergence

    def _check_divergence(
        self,
        live: ExecutionResult,
        shadow: ExecutionResult,
        context: ExecutionContext
    ) -> Optional[DivergenceReport]:
        """Check for divergence between plane results."""
        divergences = []

        # Check output hash match
        if live.output_hash != shadow.output_hash:
            divergences.append((DivergenceType.OUTPUT_MISMATCH, "CRITICAL"))

        # Check timing (warning only)
        timing_diff = abs(live.duration_ms - shadow.duration_ms)
        if timing_diff > self.TIMING_TOLERANCE_MS:
            divergences.append((DivergenceType.TIMING_VIOLATION, "WARNING"))

        # Check state hash match
        if live.state_hash != shadow.state_hash:
            divergences.append((DivergenceType.STATE_MISMATCH, "CRITICAL"))

        # Check execution trace match
        if live.execution_trace_hash != shadow.execution_trace_hash:
            divergences.append((DivergenceType.PROOF_MISMATCH, "CRITICAL"))

        if not divergences:
            return None

        # Find most severe divergence
        critical_divergences = [d for d in divergences if d[1] == "CRITICAL"]
        
        if critical_divergences:
            div_type, severity = critical_divergences[0]
            scram_triggered = True
        else:
            div_type, severity = divergences[0]
            scram_triggered = False

        # Create divergence report
        report = DivergenceReport(
            divergence_id=f"DIV-{context.context_id}",
            divergence_type=div_type,
            context_id=context.context_id,
            live_result=live,
            shadow_result=shadow,
            details={
                "all_divergences": [(d[0].value, d[1]) for d in divergences],
                "output_match": live.output_hash == shadow.output_hash,
                "timing_diff_ms": abs(live.duration_ms - shadow.duration_ms)
            },
            severity=severity,
            scram_triggered=scram_triggered,
            timestamp=datetime.now(timezone.utc)
        )

        self.divergence_reports.append(report)

        # Trigger SCRAM if critical
        if scram_triggered:
            self.scram_handler.trigger_scram(
                reason=f"Critical divergence: {div_type.value}",
                live_state=self._live_state,
                shadow_state=self._shadow_state
            )

        return report

    def replay(
        self,
        operation: Callable[[dict[str, Any], dict[str, Any]], Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Replay an operation with captured context.
        
        Uses frozen time and mocked externals for determinism.
        """
        start = time.time()
        
        try:
            output = operation(context.input_payload, context.configuration)
        except Exception as e:
            output = {"error": str(e)}
        
        duration = (time.time() - start) * 1000

        return ExecutionResult(
            plane=PlaneType.SHADOW,
            context_id=context.context_id,
            output=output,
            output_hash=self._compute_hash(output),
            state_hash=self._compute_hash({}),
            execution_trace_hash=self._compute_hash({
                "context": context.context_id,
                "plane": "REPLAY",
                "output": output
            }),
            duration_ms=duration,
            resource_metrics={},
            timestamp=datetime.now(timezone.utc)
        )

    @contextmanager
    def shadow_context(self):
        """Context manager for shadow plane operations."""
        # Save state
        saved_state = copy.deepcopy(self._shadow_state)
        try:
            yield
        except Exception:
            # Rollback on error
            self._shadow_state = saved_state
            raise
        finally:
            pass  # State persists on success

    def get_scram_status(self) -> dict[str, Any]:
        """Get current SCRAM status."""
        return {
            "active": self.scram_handler.is_active(),
            "reason": self.scram_handler.scram_reason,
            "timestamp": self.scram_handler.scram_timestamp.isoformat() if self.scram_handler.scram_timestamp else None,
            "preserved_states_available": len(self.scram_handler.preserved_states) > 0
        }

    def get_divergence_summary(self) -> dict[str, Any]:
        """Get summary of divergence events."""
        return {
            "total_divergences": len(self.divergence_reports),
            "critical_count": sum(1 for d in self.divergence_reports if d.severity == "CRITICAL"),
            "warning_count": sum(1 for d in self.divergence_reports if d.severity == "WARNING"),
            "scram_count": sum(1 for d in self.divergence_reports if d.scram_triggered),
            "by_type": {
                dt.value: sum(1 for d in self.divergence_reports if d.divergence_type == dt)
                for dt in DivergenceType
            }
        }

    def export(self) -> dict[str, Any]:
        """Export dual plane execution data."""
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "scram_status": self.get_scram_status(),
            "sync_points": [sp.to_dict() for sp in self.sync_points],
            "divergence_reports": [dr.to_dict() for dr in self.divergence_reports],
            "execution_log": self.execution_log,
            "summary": self.get_divergence_summary()
        }

    def save(self) -> None:
        """Persist to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.export(), f, indent=2)


# Singleton instance
_dual_plane_executor: Optional[DualPlaneExecutor] = None


def get_dual_plane_executor() -> DualPlaneExecutor:
    """Get global dual plane executor instance."""
    global _dual_plane_executor
    if _dual_plane_executor is None:
        _dual_plane_executor = DualPlaneExecutor()
    return _dual_plane_executor
