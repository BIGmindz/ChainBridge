# ═══════════════════════════════════════════════════════════════════════════════
# BensonExecution — Audit Emitter
# PAC-BENSON-EXEC-C01: BENSON EXECUTION GENESIS & IDENTITY INSTANTIATION
# Agent: Benson Execution (GID-00-EXEC) — Deterministic Execution Engine
# ═══════════════════════════════════════════════════════════════════════════════

"""
Benson Audit Emitter — Deterministic Audit Trail

PURPOSE:
    Emit audit events for all Benson Execution actions.
    Supports deterministic replay of execution history.

AUDIT EVENTS:
    - PAC_INGRESS_RECEIVED
    - PAC_SCHEMA_VALIDATED
    - PAC_LINT_PASSED
    - PAC_LINT_FAILED
    - PAC_PREFLIGHT_PASSED
    - PAC_PREFLIGHT_FAILED
    - PAC_ADMITTED
    - PAC_REJECTED
    - EXECUTION_STARTED
    - EXECUTION_COMPLETED
    - EXECUTION_HALTED

INVARIANTS:
    INV-AUDIT-001: All actions emit audit events
    INV-AUDIT-002: Audit events are immutable
    INV-AUDIT-003: Audit events include deterministic replay data
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT EVENT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class AuditEventType(Enum):
    """Canonical audit event types."""
    
    # Ingress events
    PAC_INGRESS_RECEIVED = "PAC_INGRESS_RECEIVED"
    PAC_SCHEMA_VALIDATED = "PAC_SCHEMA_VALIDATED"
    PAC_SCHEMA_FAILED = "PAC_SCHEMA_FAILED"
    PAC_LINT_PASSED = "PAC_LINT_PASSED"
    PAC_LINT_FAILED = "PAC_LINT_FAILED"
    PAC_PREFLIGHT_PASSED = "PAC_PREFLIGHT_PASSED"
    PAC_PREFLIGHT_FAILED = "PAC_PREFLIGHT_FAILED"
    
    # Decision events
    PAC_ADMITTED = "PAC_ADMITTED"
    PAC_REJECTED = "PAC_REJECTED"
    
    # Execution events
    EXECUTION_STARTED = "EXECUTION_STARTED"
    EXECUTION_COMPLETED = "EXECUTION_COMPLETED"
    EXECUTION_HALTED = "EXECUTION_HALTED"
    
    # System events
    BENSON_INITIALIZED = "BENSON_INITIALIZED"
    BENSON_SHUTDOWN = "BENSON_SHUTDOWN"
    DUPLICATE_INSTANCE_BLOCKED = "DUPLICATE_INSTANCE_BLOCKED"


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT EVENT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class AuditEvent:
    """
    Immutable audit event record.
    
    Attributes:
        event_type: Type of audit event
        pac_id: Associated PAC ID (if applicable)
        timestamp: When the event occurred
        details: Event-specific details
        sequence_number: Monotonic sequence number
        event_hash: Deterministic hash of event data
        previous_hash: Hash of previous event (chain)
    """
    
    event_type: AuditEventType
    pac_id: Optional[str]
    timestamp: str
    details: Dict[str, Any]
    sequence_number: int
    event_hash: str
    previous_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "pac_id": self.pac_id,
            "timestamp": self.timestamp,
            "details": self.details,
            "sequence_number": self.sequence_number,
            "event_hash": self.event_hash,
            "previous_hash": self.previous_hash,
        }
    
    def __str__(self) -> str:
        return f"[{self.sequence_number}] {self.event_type.value} | PAC: {self.pac_id or 'N/A'} | {self.timestamp}"


# ═══════════════════════════════════════════════════════════════════════════════
# BENSON AUDIT EMITTER
# ═══════════════════════════════════════════════════════════════════════════════

class BensonAuditEmitter:
    """
    Benson Audit Emitter — Immutable Audit Trail
    
    Emits and stores audit events for all Benson Execution actions.
    Events form a hash chain for integrity verification.
    
    Usage:
        emitter = BensonAuditEmitter()
        emitter.emit(AuditEventType.PAC_ADMITTED, pac_id="PAC-001", details={...})
        
        # Get audit trail
        events = emitter.get_events()
        
        # Verify integrity
        if not emitter.verify_chain():
            raise AuditIntegrityError("Chain broken")
    """
    
    VERSION = "1.0.0"
    GID = "GID-00-EXEC"
    
    def __init__(self) -> None:
        """Initialize the audit emitter."""
        self._events: List[AuditEvent] = []
        self._sequence_counter: int = 0
        self._previous_hash: Optional[str] = None
    
    def emit(
        self,
        event_type: AuditEventType,
        pac_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """
        Emit an audit event.
        
        Args:
            event_type: Type of event
            pac_id: Associated PAC ID (if applicable)
            details: Event-specific details
            
        Returns:
            The created audit event
        """
        timestamp = datetime.utcnow().isoformat() + "Z"
        sequence = self._sequence_counter
        self._sequence_counter += 1
        
        # Compute deterministic hash
        hash_data = {
            "event_type": event_type.value,
            "pac_id": pac_id,
            "timestamp": timestamp,
            "details": details or {},
            "sequence_number": sequence,
            "previous_hash": self._previous_hash,
        }
        hash_input = json.dumps(hash_data, sort_keys=True, default=str)
        event_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:32]
        
        event = AuditEvent(
            event_type=event_type,
            pac_id=pac_id,
            timestamp=timestamp,
            details=details or {},
            sequence_number=sequence,
            event_hash=event_hash,
            previous_hash=self._previous_hash,
        )
        
        self._events.append(event)
        self._previous_hash = event_hash
        
        return event
    
    def get_events(self) -> Tuple[AuditEvent, ...]:
        """Get all audit events."""
        return tuple(self._events)
    
    def get_events_for_pac(self, pac_id: str) -> Tuple[AuditEvent, ...]:
        """Get all events for a specific PAC."""
        return tuple(e for e in self._events if e.pac_id == pac_id)
    
    def get_events_by_type(self, event_type: AuditEventType) -> Tuple[AuditEvent, ...]:
        """Get all events of a specific type."""
        return tuple(e for e in self._events if e.event_type == event_type)
    
    def verify_chain(self) -> bool:
        """
        Verify the integrity of the audit chain.
        
        Returns:
            True if chain is intact, False if compromised
        """
        if not self._events:
            return True
        
        # First event should have no previous hash
        if self._events[0].previous_hash is not None:
            return False
        
        # Verify hash chain
        for i in range(1, len(self._events)):
            if self._events[i].previous_hash != self._events[i - 1].event_hash:
                return False
        
        return True
    
    @property
    def event_count(self) -> int:
        """Number of events emitted."""
        return len(self._events)
    
    @property
    def latest_event(self) -> Optional[AuditEvent]:
        """Get the most recent event."""
        return self._events[-1] if self._events else None
    
    def export_json(self) -> str:
        """Export audit trail as JSON."""
        return json.dumps([e.to_dict() for e in self._events], indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

_AUDIT_EMITTER_INSTANCE: Optional[BensonAuditEmitter] = None


def get_benson_audit_emitter() -> BensonAuditEmitter:
    """Get the singleton BensonAuditEmitter instance."""
    global _AUDIT_EMITTER_INSTANCE
    if _AUDIT_EMITTER_INSTANCE is None:
        _AUDIT_EMITTER_INSTANCE = BensonAuditEmitter()
    return _AUDIT_EMITTER_INSTANCE
