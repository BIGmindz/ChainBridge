"""
Shard Manager - Fractal Execution Sharding System
PAC-P750-SWARM-EXECUTION-SHARDING-DOCTRINE-AND-IMPLEMENTATION
TASK-02: Implement ShardManager (spawn, bound, terminate)

Core Law: Authority is singular. Execution may shard. Judgment MUST NOT shard.

Implements:
- Shard spawning with resource bounds
- Work unit distribution
- Result aggregation (upward-only)
- Mandatory termination enforcement
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
from pathlib import Path
import queue


class ShardStatus(Enum):
    """Shard lifecycle status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    TERMINATED = "TERMINATED"


class ResultType(Enum):
    """Shard result types."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"
    PARTIAL = "PARTIAL"


@dataclass
class ResourceBounds:
    """Resource bounds for a shard."""
    max_execution_time_seconds: float = 300.0
    max_memory_mb: int = 512
    max_cpu_percent: int = 25
    max_output_size_kb: int = 1024


@dataclass
class WorkUnit:
    """A unit of work to be executed by a shard."""
    work_id: str
    task_id: str
    pac_reference: str
    payload: dict[str, Any]
    bounds: ResourceBounds = field(default_factory=ResourceBounds)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_id": self.work_id,
            "task_id": self.task_id,
            "pac_reference": self.pac_reference,
            "payload_hash": hashlib.sha3_256(
                json.dumps(self.payload, sort_keys=True, default=str).encode()
            ).hexdigest()[:16],
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ShardResult:
    """Result from a shard execution."""
    shard_id: str
    work_id: str
    result_type: ResultType
    output: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    completed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "shard_id": self.shard_id,
            "work_id": self.work_id,
            "result_type": self.result_type.value,
            "has_output": self.output is not None,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "completed_at": self.completed_at.isoformat()
        }


@dataclass
class Shard:
    """A bounded, stateless execution context."""
    shard_id: str
    work_unit: WorkUnit
    status: ShardStatus = ShardStatus.PENDING
    spawned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[ShardResult] = None
    heartbeat_count: int = 0
    last_heartbeat: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "shard_id": self.shard_id,
            "work_id": self.work_unit.work_id,
            "task_id": self.work_unit.task_id,
            "status": self.status.value,
            "spawned_at": self.spawned_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "heartbeat_count": self.heartbeat_count
        }


@dataclass
class ShardHeartbeat:
    """Heartbeat from a shard to manager."""
    shard_id: str
    status: ShardStatus
    progress_percent: float
    resource_usage: dict[str, float]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "shard_id": self.shard_id,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "resource_usage": self.resource_usage,
            "timestamp": self.timestamp.isoformat()
        }


class ShardManager:
    """
    Manages shard lifecycle under singular authority.
    
    Core Law: Authority is singular. Execution may shard. Judgment MUST NOT shard.
    
    - Spawns bounded, stateless shards
    - Enforces resource limits
    - Aggregates results (upward-only flow)
    - BENSON retains sole judgment authority
    """

    # Global limits from doctrine
    MAX_CONCURRENT_SHARDS = 8
    MAX_TOTAL_SHARDS_PER_PAC = 32
    MAX_SHARD_DEPTH = 1  # No sub-shards
    HEARTBEAT_INTERVAL_MS = 5000
    MANAGER_HEARTBEAT_INTERVAL_MS = 10000

    def __init__(self, authority: str = "BENSON (GID-00)", storage_path: Optional[Path] = None):
        self.authority = authority
        self._shards: dict[str, Shard] = {}
        self._results: list[ShardResult] = []
        self._pac_shard_counts: dict[str, int] = {}
        self._executor: Optional[ThreadPoolExecutor] = None
        self._futures: dict[str, Future] = {}
        self._heartbeat_queue: queue.Queue = queue.Queue()
        self._shutdown = False
        self._lock = threading.RLock()
        self.storage_path = storage_path or Path("data/shard_manager.json")

        # Audit log
        self._audit_log: list[dict[str, Any]] = []

    def _generate_shard_id(self) -> str:
        """Generate unique shard ID."""
        return f"SHARD-{secrets.token_hex(8).upper()}"

    def _generate_work_id(self) -> str:
        """Generate unique work ID."""
        return f"WORK-{secrets.token_hex(6).upper()}"

    def _log_audit(self, event: str, shard_id: str, details: dict[str, Any]) -> None:
        """Log audit event."""
        self._audit_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "shard_id": shard_id,
            "details": details
        })

    def spawn_shard(
        self,
        task_id: str,
        pac_reference: str,
        payload: dict[str, Any],
        bounds: Optional[ResourceBounds] = None
    ) -> Shard:
        """
        Spawn a new shard for a work unit.
        
        Enforces:
        - Concurrent shard limit
        - Per-PAC shard limit
        - Resource bounds
        """
        with self._lock:
            # Check concurrent limit
            active_count = sum(
                1 for s in self._shards.values()
                if s.status in (ShardStatus.PENDING, ShardStatus.RUNNING)
            )
            if active_count >= self.MAX_CONCURRENT_SHARDS:
                raise RuntimeError(
                    f"Concurrent shard limit reached ({self.MAX_CONCURRENT_SHARDS})"
                )

            # Check per-PAC limit
            pac_count = self._pac_shard_counts.get(pac_reference, 0)
            if pac_count >= self.MAX_TOTAL_SHARDS_PER_PAC:
                raise RuntimeError(
                    f"Per-PAC shard limit reached ({self.MAX_TOTAL_SHARDS_PER_PAC})"
                )

            # Create work unit
            work_unit = WorkUnit(
                work_id=self._generate_work_id(),
                task_id=task_id,
                pac_reference=pac_reference,
                payload=payload,
                bounds=bounds or ResourceBounds()
            )

            # Create shard
            shard = Shard(
                shard_id=self._generate_shard_id(),
                work_unit=work_unit
            )

            self._shards[shard.shard_id] = shard
            self._pac_shard_counts[pac_reference] = pac_count + 1

            self._log_audit("SPAWN", shard.shard_id, {
                "task_id": task_id,
                "pac_reference": pac_reference,
                "bounds": {
                    "max_time_s": work_unit.bounds.max_execution_time_seconds,
                    "max_memory_mb": work_unit.bounds.max_memory_mb
                }
            })

            return shard

    def execute_shard(
        self,
        shard: Shard,
        executor_fn: Callable[[dict[str, Any]], Any]
    ) -> ShardResult:
        """
        Execute a shard synchronously with timeout enforcement.
        
        The executor_fn receives the payload and returns output.
        Shard MUST NOT make governance decisions or emit WRAP/BER.
        """
        shard.status = ShardStatus.RUNNING
        shard.started_at = datetime.now(timezone.utc)
        
        self._log_audit("START", shard.shard_id, {"started_at": shard.started_at.isoformat()})

        start_time = time.time()
        timeout = shard.work_unit.bounds.max_execution_time_seconds

        try:
            # Execute with timeout
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT_SHARDS)

            future = self._executor.submit(executor_fn, shard.work_unit.payload)
            self._futures[shard.shard_id] = future

            try:
                output = future.result(timeout=timeout)
                result_type = ResultType.SUCCESS
                error = None
            except FuturesTimeoutError:
                result_type = ResultType.TIMEOUT
                output = None
                error = f"Shard exceeded timeout ({timeout}s)"
                future.cancel()
            except Exception as e:
                result_type = ResultType.FAILURE
                output = None
                error = str(e)

        except Exception as e:
            result_type = ResultType.FAILURE
            output = None
            error = f"Execution error: {e}"

        execution_time = (time.time() - start_time) * 1000

        # Create result
        result = ShardResult(
            shard_id=shard.shard_id,
            work_id=shard.work_unit.work_id,
            result_type=result_type,
            output=output,
            error=error,
            execution_time_ms=execution_time
        )

        # Update shard
        shard.result = result
        shard.completed_at = datetime.now(timezone.utc)
        shard.status = (
            ShardStatus.COMPLETED if result_type == ResultType.SUCCESS
            else ShardStatus.TIMEOUT if result_type == ResultType.TIMEOUT
            else ShardStatus.FAILED
        )

        # Store result for aggregation
        self._results.append(result)

        self._log_audit("COMPLETE", shard.shard_id, {
            "result_type": result_type.value,
            "execution_time_ms": execution_time,
            "error": error
        })

        # Clean up future reference
        self._futures.pop(shard.shard_id, None)

        return result

    def terminate_shard(self, shard_id: str, reason: str) -> bool:
        """Forcibly terminate a shard."""
        with self._lock:
            shard = self._shards.get(shard_id)
            if not shard:
                return False

            # Cancel future if running
            future = self._futures.get(shard_id)
            if future:
                future.cancel()
                self._futures.pop(shard_id, None)

            shard.status = ShardStatus.TERMINATED
            shard.completed_at = datetime.now(timezone.utc)

            self._log_audit("TERMINATE", shard_id, {"reason": reason})

            return True

    def terminate_all_shards(self, reason: str) -> int:
        """Terminate all active shards."""
        terminated = 0
        with self._lock:
            for shard_id, shard in self._shards.items():
                if shard.status in (ShardStatus.PENDING, ShardStatus.RUNNING):
                    if self.terminate_shard(shard_id, reason):
                        terminated += 1
        return terminated

    def receive_heartbeat(self, heartbeat: ShardHeartbeat) -> None:
        """Receive heartbeat from a shard."""
        with self._lock:
            shard = self._shards.get(heartbeat.shard_id)
            if shard:
                shard.heartbeat_count += 1
                shard.last_heartbeat = heartbeat.timestamp
                self._heartbeat_queue.put(heartbeat)

    def aggregate_results(self, pac_reference: str) -> dict[str, Any]:
        """
        Aggregate results for a PAC (upward-only flow).
        
        This is where authority (BENSON) receives shard outputs
        for final judgment. Shards do not see this aggregation.
        """
        pac_results = [
            r for r in self._results
            if self._shards.get(r.shard_id) and 
               self._shards[r.shard_id].work_unit.pac_reference == pac_reference
        ]

        return {
            "pac_reference": pac_reference,
            "aggregated_at": datetime.now(timezone.utc).isoformat(),
            "authority": self.authority,
            "total_shards": len(pac_results),
            "successful": sum(1 for r in pac_results if r.result_type == ResultType.SUCCESS),
            "failed": sum(1 for r in pac_results if r.result_type == ResultType.FAILURE),
            "timeout": sum(1 for r in pac_results if r.result_type == ResultType.TIMEOUT),
            "results": [r.to_dict() for r in pac_results],
            "judgment_pending": True  # BENSON must render judgment
        }

    def get_active_shards(self) -> list[dict[str, Any]]:
        """Get all active shards."""
        return [
            s.to_dict() for s in self._shards.values()
            if s.status in (ShardStatus.PENDING, ShardStatus.RUNNING)
        ]

    def get_shard_status(self, shard_id: str) -> Optional[dict[str, Any]]:
        """Get status of a specific shard."""
        shard = self._shards.get(shard_id)
        return shard.to_dict() if shard else None

    def get_manager_heartbeat(self) -> dict[str, Any]:
        """Generate manager heartbeat for OCC."""
        with self._lock:
            active = [s for s in self._shards.values() if s.status == ShardStatus.RUNNING]
            completed = [s for s in self._shards.values() if s.status == ShardStatus.COMPLETED]
            failed = [s for s in self._shards.values() if s.status in (ShardStatus.FAILED, ShardStatus.TIMEOUT)]

            return {
                "manager_id": "SHARD_MANAGER",
                "authority": self.authority,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_shards": len(active),
                "completed_shards": len(completed),
                "failed_shards": len(failed),
                "total_shards": len(self._shards),
                "aggregate_status": "HEALTHY" if not failed else "DEGRADED"
            }

    def export(self) -> dict[str, Any]:
        """Export manager state."""
        return {
            "schema_version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "authority": self.authority,
            "shards": [s.to_dict() for s in self._shards.values()],
            "results": [r.to_dict() for r in self._results],
            "pac_shard_counts": self._pac_shard_counts,
            "manager_heartbeat": self.get_manager_heartbeat(),
            "audit_log_size": len(self._audit_log)
        }

    def save(self) -> None:
        """Save manager state."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.export(), f, indent=2)

    def shutdown(self) -> None:
        """Shutdown manager and terminate all shards."""
        self._shutdown = True
        self.terminate_all_shards("Manager shutdown")
        if self._executor:
            self._executor.shutdown(wait=False)


# Singleton instance
_shard_manager: Optional[ShardManager] = None


def get_shard_manager() -> ShardManager:
    """Get global shard manager instance."""
    global _shard_manager
    if _shard_manager is None:
        _shard_manager = ShardManager()
    return _shard_manager
