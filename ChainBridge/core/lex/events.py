"""
Lex Events Module
=================

Structured event emission for Lex enforcement observability.

All enforcement actions emit events for audit and monitoring.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
import json
import sys


class LexEventType(Enum):
    """Event types for Lex enforcement lifecycle."""
    
    # Validation lifecycle
    VALIDATION_START = "VALIDATION_START"
    VALIDATION_COMPLETE = "VALIDATION_COMPLETE"
    
    # Rule evaluation
    RULE_EVALUATE = "RULE_EVALUATE"
    RULE_PASS = "RULE_PASS"
    RULE_FAIL = "RULE_FAIL"
    
    # Verdict
    VERDICT_APPROVED = "VERDICT_APPROVED"
    VERDICT_REJECTED = "VERDICT_REJECTED"
    
    # Override
    OVERRIDE_REQUESTED = "OVERRIDE_REQUESTED"
    OVERRIDE_APPROVED = "OVERRIDE_APPROVED"
    OVERRIDE_DENIED = "OVERRIDE_DENIED"
    
    # Enforcement
    EXECUTION_BLOCKED = "EXECUTION_BLOCKED"
    EXECUTION_PERMITTED = "EXECUTION_PERMITTED"


@dataclass
class LexEvent:
    """
    Structured event for Lex enforcement actions.
    
    Immutable after creation.
    """
    
    event_type: LexEventType
    verdict_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = field(default_factory=dict)
    sequence: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "event_type": self.event_type.value,
            "verdict_id": self.verdict_id,
            "timestamp": self.timestamp.isoformat(),
            "payload": self.payload,
            "sequence": self.sequence,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class LexEventEmitter:
    """
    Event emitter for Lex enforcement observability.
    
    Emits structured events for:
        - Rule evaluations
        - Verdicts
        - Overrides
        - Execution blocks/permits
    
    Observability: MANDATORY
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
        self._listeners: list[Callable[[LexEvent], None]] = []
        self._sequence = 0
        self._events: list[LexEvent] = []
    
    def register_listener(self, listener: Callable[[LexEvent], None]) -> None:
        """Register an event listener callback."""
        self._listeners.append(listener)
    
    def emit(
        self,
        event_type: LexEventType,
        verdict_id: str,
        payload: Optional[dict[str, Any]] = None,
    ) -> LexEvent:
        """
        Emit a structured Lex event.
        
        Args:
            event_type: Type of event
            verdict_id: Associated verdict identifier
            payload: Optional event payload
            
        Returns:
            The emitted LexEvent
        """
        self._sequence += 1
        
        event = LexEvent(
            event_type=event_type,
            verdict_id=verdict_id,
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
                sys.stderr.write(f"[LEX_EVENT_LISTENER_ERROR] {e}\n")
        
        return event
    
    def _emit_terminal(self, event: LexEvent) -> None:
        """Emit event to terminal."""
        if self._json_output:
            print(event.to_json())
        else:
            icon = self._get_event_icon(event.event_type)
            print(f"{icon} [{event.sequence:04d}] {event.event_type.value} | {event.verdict_id} | {event.timestamp.isoformat()}")
    
    def _emit_file(self, event: LexEvent) -> None:
        """Emit event to log file."""
        if self._log_file:
            try:
                with open(self._log_file, "a") as f:
                    f.write(event.to_json() + "\n")
            except Exception as e:
                sys.stderr.write(f"[LEX_EVENT_FILE_ERROR] {e}\n")
    
    def _get_event_icon(self, event_type: LexEventType) -> str:
        """Get visual icon for event type."""
        icons = {
            LexEventType.VALIDATION_START: "🟥",
            LexEventType.VALIDATION_COMPLETE: "🟥",
            LexEventType.RULE_EVALUATE: "⚖️",
            LexEventType.RULE_PASS: "✅",
            LexEventType.RULE_FAIL: "❌",
            LexEventType.VERDICT_APPROVED: "✅",
            LexEventType.VERDICT_REJECTED: "🛑",
            LexEventType.OVERRIDE_REQUESTED: "🔓",
            LexEventType.OVERRIDE_APPROVED: "✅",
            LexEventType.OVERRIDE_DENIED: "🚫",
            LexEventType.EXECUTION_BLOCKED: "🛑",
            LexEventType.EXECUTION_PERMITTED: "▶️",
        }
        return icons.get(event_type, "○")
    
    def get_events(self) -> list[LexEvent]:
        """Get all emitted events."""
        return list(self._events)
    
    def get_event_summary(self) -> dict[str, Any]:
        """Get summary of all events."""
        return {
            "total_events": len(self._events),
            "by_type": {
                et.value: sum(1 for e in self._events if e.event_type == et)
                for et in LexEventType
                if any(e.event_type == et for e in self._events)
            },
        }
