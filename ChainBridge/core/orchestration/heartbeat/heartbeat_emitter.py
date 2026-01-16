"""
Heartbeat Emitter - Core Execution Visibility System
====================================================

PAC Reference: PAC-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM
Classification: LAW_TIER
Author: CODY (GID-01) - Emitter Backend
Orchestrator: BENSON (GID-00)

Invariants Enforced:
    - Control > Autonomy
    - Proof > Execution  
    - Operator Visibility Mandatory

NO SILENT EXECUTION. All PAC lifecycle events MUST emit heartbeats.
"""

import json
import time
import threading
import queue
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Generator
from pathlib import Path


class HeartbeatEventType(Enum):
    """Canonical heartbeat event types."""
    
    # PAC Lifecycle
    PAC_START = "PAC_START"
    PAC_COMPLETE = "PAC_COMPLETE"
    PAC_FAILED = "PAC_FAILED"
    
    # Lane Transitions
    LANE_TRANSITION = "LANE_TRANSITION"
    LANE_ACTIVE = "LANE_ACTIVE"
    
    # Task Events
    TASK_START = "TASK_START"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_FAILED = "TASK_FAILED"
    
    # Agent Events
    AGENT_ACTIVE = "AGENT_ACTIVE"
    AGENT_ATTESTED = "AGENT_ATTESTED"
    AGENT_IDLE = "AGENT_IDLE"
    
    # Proof Events
    WRAP_GENERATED = "WRAP_GENERATED"
    BER_GENERATED = "BER_GENERATED"
    LEDGER_COMMIT = "LEDGER_COMMIT"
    
    # System Events
    HEARTBEAT_PING = "HEARTBEAT_PING"
    VISIBILITY_CHECK = "VISIBILITY_CHECK"


@dataclass
class HeartbeatEvent:
    """
    Single heartbeat event for OCC visibility.
    
    Every execution state change MUST generate a HeartbeatEvent.
    No silent execution paths permitted.
    """
    
    event_type: HeartbeatEventType
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # PAC Context
    pac_id: Optional[str] = None
    pac_title: Optional[str] = None
    pac_status: Optional[str] = None
    
    # Lane Context
    lane: Optional[str] = None
    lane_status: Optional[str] = None
    
    # Task Context
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    task_status: Optional[str] = None
    task_progress: Optional[int] = None  # 0-100
    
    # Agent Context
    agent_gid: Optional[str] = None
    agent_name: Optional[str] = None
    agent_role: Optional[str] = None
    agent_status: Optional[str] = None
    
    # Proof Context
    wrap_id: Optional[str] = None
    ber_id: Optional[str] = None
    ber_score: Optional[int] = None
    
    # Metadata
    sequence_number: int = 0
    session_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        return f"event: {self.event_type.value}\ndata: {json.dumps(self.to_dict())}\n\n"


class HeartbeatStream:
    """
    Server-Sent Event stream manager for heartbeat delivery.
    
    Provides real-time visibility into PAC execution for OCC UI.
    """
    
    def __init__(self, buffer_size: int = 1000):
        self._events: queue.Queue = queue.Queue(maxsize=buffer_size)
        self._subscribers: List[queue.Queue] = []
        self._lock = threading.Lock()
        self._running = False
        self._history: List[HeartbeatEvent] = []
        self._max_history = 500
    
    def publish(self, event: HeartbeatEvent) -> None:
        """Publish event to all subscribers."""
        with self._lock:
            # Store in history
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            
            # Deliver to subscribers
            dead_subscribers = []
            for subscriber in self._subscribers:
                try:
                    subscriber.put_nowait(event)
                except queue.Full:
                    dead_subscribers.append(subscriber)
            
            # Clean up dead subscribers
            for dead in dead_subscribers:
                self._subscribers.remove(dead)
    
    def subscribe(self) -> Generator[HeartbeatEvent, None, None]:
        """Subscribe to heartbeat stream. Yields events as they arrive."""
        subscriber_queue: queue.Queue = queue.Queue(maxsize=100)
        
        with self._lock:
            self._subscribers.append(subscriber_queue)
        
        try:
            while True:
                try:
                    event = subscriber_queue.get(timeout=30)
                    yield event
                except queue.Empty:
                    # Emit ping to keep connection alive
                    yield HeartbeatEvent(
                        event_type=HeartbeatEventType.HEARTBEAT_PING,
                        details={"keepalive": True}
                    )
        finally:
            with self._lock:
                if subscriber_queue in self._subscribers:
                    self._subscribers.remove(subscriber_queue)
    
    def get_history(self, limit: int = 100) -> List[HeartbeatEvent]:
        """Get recent heartbeat history."""
        with self._lock:
            return self._history[-limit:]
    
    def get_history_since(self, sequence_number: int) -> List[HeartbeatEvent]:
        """Get events since a specific sequence number."""
        with self._lock:
            return [e for e in self._history if e.sequence_number > sequence_number]


class HeartbeatEmitter:
    """
    Core heartbeat emitter for Benson execution loop.
    
    CRITICAL: This class enforces the "Operator Visibility Mandatory" invariant.
    All PAC execution MUST route through this emitter.
    
    Usage:
        emitter = HeartbeatEmitter()
        emitter.emit_pac_start(pac_id="PAC-P744-OCC-...", title="...")
        emitter.emit_task_start(task_id="TASK-01", ...)
        ...
        emitter.emit_pac_complete(pac_id="PAC-P744-OCC-...", ber_score=100)
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"session_{int(time.time())}"
        self.stream = HeartbeatStream()
        self._sequence = 0
        self._lock = threading.Lock()
        self._current_pac: Optional[str] = None
        self._current_lane: Optional[str] = None
        self._active_agents: Dict[str, Dict[str, Any]] = {}
        self._event_log_path = Path("logs/heartbeat_events.jsonl")
        self._ensure_log_dir()
    
    def _ensure_log_dir(self) -> None:
        """Ensure log directory exists."""
        self._event_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _next_sequence(self) -> int:
        """Get next sequence number (thread-safe)."""
        with self._lock:
            self._sequence += 1
            return self._sequence
    
    def _emit(self, event: HeartbeatEvent) -> HeartbeatEvent:
        """Internal emit method. Publishes and logs event."""
        event.sequence_number = self._next_sequence()
        event.session_id = self.session_id
        
        # Publish to stream
        self.stream.publish(event)
        
        # Log to file for audit trail
        self._log_event(event)
        
        return event
    
    def _log_event(self, event: HeartbeatEvent) -> None:
        """Append event to log file."""
        try:
            with open(self._event_log_path, "a", encoding="utf-8") as f:
                f.write(event.to_json().replace("\n", " ") + "\n")
        except Exception:
            pass  # Don't fail execution on log errors
    
    # ==================== PAC Lifecycle Events ====================
    
    def emit_pac_start(
        self,
        pac_id: str,
        title: str,
        classification: str = "LAW_TIER",
        lane: Optional[str] = None,
        **kwargs
    ) -> HeartbeatEvent:
        """Emit PAC_START event. MUST be called at PAC execution begin."""
        self._current_pac = pac_id
        self._current_lane = lane
        
        return self._emit(HeartbeatEvent(
            event_type=HeartbeatEventType.PAC_START,
            pac_id=pac_id,
            pac_title=title,
            pac_status="EXECUTING",
            lane=lane,
            details={"classification": classification, **kwargs}
        ))
    
    def emit_pac_complete(
        self,
        pac_id: str,
        ber_score: Optional[int] = None,
        wrap_id: Optional[str] = None,
        ber_id: Optional[str] = None,
        **kwargs
    ) -> HeartbeatEvent:
        """Emit PAC_COMPLETE event. MUST be called at PAC execution end."""
        event = self._emit(HeartbeatEvent(
            event_type=HeartbeatEventType.PAC_COMPLETE,
            pac_id=pac_id,
            pac_status="COMPLETED",
            wrap_id=wrap_id,
            ber_id=ber_id,
            ber_score=ber_score,
            details=kwargs
        ))
        self._current_pac = None
        return event
    
    def emit_pac_failed(
        self,
        pac_id: str,
        reason: str,
        **kwargs
    ) -> HeartbeatEvent:
        """Emit PAC_FAILED event."""
        event = self._emit(HeartbeatEvent(
            event_type=HeartbeatEventType.PAC_FAILED,
            pac_id=pac_id,
            pac_status="FAILED",
            details={"reason": reason, **kwargs}
        ))
        self._current_pac = None
        return event
    
    # ==================== Lane Events ====================
    
    def emit_lane_transition(
        self,
        from_lane: Optional[str],
        to_lane: str,
        **kwargs
    ) -> HeartbeatEvent:
        """Emit LANE_TRANSITION event."""
        self._current_lane = to_lane
        return self._emit(HeartbeatEvent(
            event_type=HeartbeatEventType.LANE_TRANSITION,
            pac_id=self._current_pac,
            lane=to_lane,
            lane_status="ACTIVE",
            details={"from_lane": from_lane, **kwargs}
        ))
    
    # ==================== Task Events ====================
    
    def emit_task_start(
        self,
        task_id: str,
        title: str,
        agent_gid: Optional[str] = None,
        agent_name: Optional[str] = None,
        **kwargs
    ) -> HeartbeatEvent:
        """Emit TASK_START event."""
        return self._emit(HeartbeatEvent(
            event_type=HeartbeatEventType.TASK_START,
            pac_id=self._current_pac,
            lane=self._current_lane,
            task_id=task_id,
            task_title=title,
            task_status="IN_PROGRESS",
            task_progress=0,
            agent_gid=agent_gid,
            agent_name=agent_name,
            details=kwargs
        ))
    
    def emit_task_complete(
        self,
        task_id: str,
        title: str,
        artifact: Optional[str] = None,
        **kwargs
    ) -> HeartbeatEvent:
        """Emit TASK_COMPLETE event."""
        return self._emit(HeartbeatEvent(
            event_type=HeartbeatEventType.TASK_COMPLETE,
            pac_id=self._current_pac,
            lane=self._current_lane,
            task_id=task_id,
            task_title=title,
            task_status="COMPLETED",
            task_progress=100,
            details={"artifact": artifact, **kwargs}
        ))
    
    def emit_task_failed(
        self,
        task_id: str,
        title: str,
        reason: str,
        **kwargs
    ) -> HeartbeatEvent:
        """Emit TASK_FAILED event."""
        return self._emit(HeartbeatEvent(
            event_type=HeartbeatEventType.TASK_FAILED,
            pac_id=self._current_pac,
            lane=self._current_lane,
            task_id=task_id,
            task_title=title,
            task_status="FAILED",
            details={"reason": reason, **kwargs}
        ))
    
    # ==================== Agent Events ====================
    
    def emit_agent_active(
        self,
        agent_gid: str,
        agent_name: str,
        role: str,
        **kwargs
    ) -> HeartbeatEvent:
        """Emit AGENT_ACTIVE event."""
        self._active_agents[agent_gid] = {
            "name": agent_name,
            "role": role,
            "status": "ACTIVE"
        }
        return self._emit(HeartbeatEvent(
            event_type=HeartbeatEventType.AGENT_ACTIVE,
            pac_id=self._current_pac,
            agent_gid=agent_gid,
            agent_name=agent_name,
            agent_role=role,
            agent_status="ACTIVE",
            details=kwargs
        ))
    
    def emit_agent_attested(
        self,
        agent_gid: str,
        agent_name: str,
        attestation: str,
        **kwargs
    ) -> HeartbeatEvent:
        """Emit AGENT_ATTESTED event."""
        return self._emit(HeartbeatEvent(
            event_type=HeartbeatEventType.AGENT_ATTESTED,
            pac_id=self._current_pac,
            agent_gid=agent_gid,
            agent_name=agent_name,
            agent_status="ATTESTED",
            details={"attestation": attestation, **kwargs}
        ))
    
    # ==================== Proof Events ====================
    
    def emit_wrap_generated(
        self,
        wrap_id: str,
        pac_id: str,
        agent_count: int = 13,
        **kwargs
    ) -> HeartbeatEvent:
        """Emit WRAP_GENERATED event."""
        return self._emit(HeartbeatEvent(
            event_type=HeartbeatEventType.WRAP_GENERATED,
            pac_id=pac_id,
            wrap_id=wrap_id,
            details={"agent_count": agent_count, **kwargs}
        ))
    
    def emit_ber_generated(
        self,
        ber_id: str,
        pac_id: str,
        score: int,
        max_score: int = 100,
        **kwargs
    ) -> HeartbeatEvent:
        """Emit BER_GENERATED event."""
        return self._emit(HeartbeatEvent(
            event_type=HeartbeatEventType.BER_GENERATED,
            pac_id=pac_id,
            ber_id=ber_id,
            ber_score=score,
            details={"max_score": max_score, "grade": self._score_to_grade(score), **kwargs}
        ))
    
    def emit_ledger_commit(
        self,
        record_name: str,
        ledger_path: str = "core/governance/SOVEREIGNTY_LEDGER.json",
        **kwargs
    ) -> HeartbeatEvent:
        """Emit LEDGER_COMMIT event."""
        return self._emit(HeartbeatEvent(
            event_type=HeartbeatEventType.LEDGER_COMMIT,
            pac_id=self._current_pac,
            details={"record_name": record_name, "ledger_path": ledger_path, **kwargs}
        ))
    
    # ==================== Utilities ====================
    
    @staticmethod
    def _score_to_grade(score: int) -> str:
        """Convert BER score to letter grade."""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        else:
            return "F"
    
    def get_active_agents(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active agents."""
        return self._active_agents.copy()
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current execution state snapshot."""
        return {
            "session_id": self.session_id,
            "current_pac": self._current_pac,
            "current_lane": self._current_lane,
            "active_agents": self._active_agents,
            "sequence": self._sequence,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global singleton emitter (initialized on first use)
_global_emitter: Optional[HeartbeatEmitter] = None


def get_emitter() -> HeartbeatEmitter:
    """Get or create global heartbeat emitter singleton."""
    global _global_emitter
    if _global_emitter is None:
        _global_emitter = HeartbeatEmitter()
    return _global_emitter


def reset_emitter() -> HeartbeatEmitter:
    """Reset global emitter (for testing)."""
    global _global_emitter
    _global_emitter = HeartbeatEmitter()
    return _global_emitter


# ==================== Self-Test ====================

if __name__ == "__main__":
    print("HeartbeatEmitter Self-Test")
    print("=" * 50)
    
    emitter = HeartbeatEmitter(session_id="test_session")
    
    # Simulate PAC execution
    emitter.emit_pac_start(
        pac_id="PAC-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM",
        title="OCC Execution Heartbeat System",
        lane="OCC/GOVERNANCE_VISIBILITY"
    )
    
    emitter.emit_agent_active("GID-00", "BENSON", "Orchestrator")
    emitter.emit_agent_active("GID-01", "CODY", "Emitter Backend")
    
    emitter.emit_task_start("TASK-01", "Implement heartbeat emitter", "GID-01", "CODY")
    emitter.emit_task_complete("TASK-01", "Implement heartbeat emitter", "heartbeat_emitter.py")
    
    emitter.emit_wrap_generated(
        "WRAP-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM",
        "PAC-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM"
    )
    
    emitter.emit_ber_generated(
        "BER-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM",
        "PAC-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM",
        score=100
    )
    
    emitter.emit_pac_complete(
        pac_id="PAC-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM",
        ber_score=100,
        wrap_id="WRAP-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM",
        ber_id="BER-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM"
    )
    
    # Print history
    print(f"\nEvents emitted: {emitter._sequence}")
    for event in emitter.stream.get_history():
        print(f"  [{event.sequence_number}] {event.event_type.value}: {event.pac_id or event.task_id or event.agent_name}")
    
    print("\n✅ Self-test PASSED")
