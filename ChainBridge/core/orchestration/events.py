"""
Event Emitter Module
====================

Structured event emission for orchestration observability.

Governance: GOLD STANDARD
Observability: MANDATORY
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
import json
import sys


class EventType(Enum):
    """Event types for orchestration lifecycle."""
    
    # Engine lifecycle
    ENGINE_START = "ENGINE_START"
    ENGINE_STOP = "ENGINE_STOP"
    ENGINE_HALT = "ENGINE_HALT"
    
    # Gate lifecycle
    GATE_PENDING = "GATE_PENDING"
    GATE_RUNNING = "GATE_RUNNING"
    GATE_PASS = "GATE_PASS"
    GATE_FAIL = "GATE_FAIL"
    GATE_SKIP = "GATE_SKIP"
    
    # Execution lifecycle
    EXECUTION_START = "EXECUTION_START"
    EXECUTION_COMPLETE = "EXECUTION_COMPLETE"
    EXECUTION_ABORT = "EXECUTION_ABORT"
    
    # PDO lifecycle
    PROOF_COLLECTED = "PROOF_COLLECTED"
    DECISION_MADE = "DECISION_MADE"
    OUTCOME_RECORDED = "OUTCOME_RECORDED"


@dataclass
class GateEvent:
    """
    Structured event for gate transitions.
    
    All events are immutable after creation.
    """
    
    event_type: EventType
    gate_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = field(default_factory=dict)
    sequence: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_type": self.event_type.value,
            "gate_id": self.gate_id,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "sequence": self.sequence,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class EventEmitter:
    """
    Event emitter for orchestration observability.
    
    Emits structured events to:
        - Terminal (stdout)
        - Event log (file)
        - Registered listeners
    
    All emissions are synchronous and blocking to ensure
    observability under FAIL-CLOSED discipline.
    """
    
    def __init__(
        self,
        log_file: Optional[str] = None,
        terminal_output: bool = True,
        json_output: bool = False,
    ):
        self._log_file = log_file
        self._terminal_output = terminal_output
        self._json_output = json_output
        self._listeners: list[Callable[[GateEvent], None]] = []
        self._sequence = 0
        self._events: list[GateEvent] = []
    
    def register_listener(self, listener: Callable[[GateEvent], None]) -> None:
        """Register an event listener callback."""
        self._listeners.append(listener)
    
    def emit(
        self,
        event_type: EventType,
        gate_id: str,
        payload: Optional[dict[str, Any]] = None,
    ) -> GateEvent:
        """
        Emit a structured event.
        
        Args:
            event_type: Type of event
            gate_id: Associated gate identifier
            payload: Optional event payload
            
        Returns:
            The emitted GateEvent
        """
        self._sequence += 1
        
        event = GateEvent(
            event_type=event_type,
            gate_id=gate_id,
            payload=payload or {},
            sequence=self._sequence,
        )
        
        # Store event
        self._events.append(event)
        
        # Terminal output
        if self._terminal_output:
            self._emit_terminal(event)
        
        # File output
        if self._log_file:
            self._emit_file(event)
        
        # Notify listeners
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                # Log but don't fail - observability should not break execution
                sys.stderr.write(f"[EVENT_LISTENER_ERROR] {e}\n")
        
        return event
    
    def _emit_terminal(self, event: GateEvent) -> None:
        """Emit event to terminal."""
        if self._json_output:
            print(event.to_json())
        else:
            icon = self._get_event_icon(event.event_type)
            print(f"{icon} [{event.sequence:04d}] {event.event_type.value} | {event.gate_id} | {event.timestamp.isoformat()}")
    
    def _emit_file(self, event: GateEvent) -> None:
        """Emit event to log file."""
        if self._log_file:
            try:
                with open(self._log_file, "a") as f:
                    f.write(event.to_json() + "\n")
            except Exception as e:
                sys.stderr.write(f"[EVENT_FILE_ERROR] {e}\n")
    
    def _get_event_icon(self, event_type: EventType) -> str:
        """Get visual icon for event type."""
        icons = {
            EventType.ENGINE_START: "🟦",
            EventType.ENGINE_STOP: "⬛",
            EventType.ENGINE_HALT: "🟥",
            EventType.GATE_PENDING: "⏳",
            EventType.GATE_RUNNING: "🔄",
            EventType.GATE_PASS: "✅",
            EventType.GATE_FAIL: "❌",
            EventType.GATE_SKIP: "⏭️",
            EventType.EXECUTION_START: "▶️",
            EventType.EXECUTION_COMPLETE: "✅",
            EventType.EXECUTION_ABORT: "🛑",
            EventType.PROOF_COLLECTED: "📋",
            EventType.DECISION_MADE: "⚖️",
            EventType.OUTCOME_RECORDED: "📝",
        }
        return icons.get(event_type, "○")
    
    def get_events(self) -> list[GateEvent]:
        """Get all emitted events."""
        return list(self._events)
    
    def get_event_summary(self) -> dict[str, Any]:
        """Get summary of all events."""
        return {
            "total_events": len(self._events),
            "by_type": {
                et.value: sum(1 for e in self._events if e.event_type == et)
                for et in EventType
                if any(e.event_type == et for e in self._events)
            },
            "first_event": self._events[0].to_dict() if self._events else None,
            "last_event": self._events[-1].to_dict() if self._events else None,
        }
