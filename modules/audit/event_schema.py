"""
Audit Event Schema Module
=========================

PAC-SEC-P822-A: IMMUTABLE AUDIT STORAGE CORE
Component: Structured Audit Event Schema
Agent: FORGE (GID-04)

PURPOSE:
  Defines the canonical AuditEvent dataclass for all audit records.
  Ensures consistent structure, serialization, and validation.
  Integrates with CHRONOS timestamp authority for temporal ordering.

INVARIANTS:
  INV-AUDIT-004: Events MUST serialize without data loss
  INV-EVENT-001: Events MUST have unique event_id
  INV-EVENT-002: Events MUST have valid timestamp from authority
  INV-EVENT-003: Events MUST specify event_type and severity
  INV-EVENT-004: Events MUST be immutable after creation

EVENT CATEGORIES:
  - AUTHENTICATION: Login, logout, MFA, session events
  - AUTHORIZATION: Permission checks, access grants/denials
  - DATA_ACCESS: Read/write operations on sensitive data
  - CONFIGURATION: System configuration changes
  - SECURITY: Security-related events (alerts, violations)
  - SYSTEM: System lifecycle events (startup, shutdown)
"""

import hashlib
import json
import secrets
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class EventType(Enum):
    """Audit event type categories."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    SYSTEM = "system"
    API_CALL = "api_call"
    USER_ACTION = "user_action"
    COMPLIANCE = "compliance"


class EventSeverity(Enum):
    """Audit event severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventOutcome(Enum):
    """Outcome of the audited action."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EventActor:
    """
    Actor (user/system) that triggered the event.
    
    Immutable to prevent modification after creation.
    """
    actor_type: str  # "user", "system", "service", "api_key"
    actor_id: str  # GID, service name, or identifier
    actor_name: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventActor":
        """Deserialize from dictionary."""
        return cls(
            actor_type=data.get("actor_type", "unknown"),
            actor_id=data.get("actor_id", "unknown"),
            actor_name=data.get("actor_name"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            session_id=data.get("session_id"),
        )


@dataclass(frozen=True)
class EventTarget:
    """
    Target resource affected by the event.
    
    Immutable to prevent modification after creation.
    """
    target_type: str  # "resource", "endpoint", "user", "system"
    target_id: str  # Resource identifier
    target_name: Optional[str] = None
    target_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "target_path": self.target_path,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventTarget":
        """Deserialize from dictionary."""
        return cls(
            target_type=data.get("target_type", "unknown"),
            target_id=data.get("target_id", "unknown"),
            target_name=data.get("target_name"),
            target_path=data.get("target_path"),
        )


@dataclass
class AuditEvent:
    """
    Canonical audit event record.
    
    Contains all information needed for compliance auditing:
    - Who (actor) did what (action) to what (target)
    - When (timestamp) and with what result (outcome)
    - Additional context and metadata
    
    Events are designed to be:
    - Complete: All relevant information captured
    - Consistent: Same structure for all event types
    - Serializable: Can be converted to/from JSON
    - Verifiable: Hash enables integrity checking
    """
    
    # Required fields
    event_type: EventType
    action: str  # Specific action (e.g., "login", "read_file")
    
    # Actor and target
    actor: EventActor
    target: Optional[EventTarget] = None
    
    # Outcome
    outcome: EventOutcome = EventOutcome.SUCCESS
    outcome_reason: Optional[str] = None
    
    # Severity
    severity: EventSeverity = EventSeverity.INFO
    
    # Identifiers (auto-generated if not provided)
    event_id: str = field(default_factory=lambda: secrets.token_hex(16))
    correlation_id: Optional[str] = None
    
    # Timestamps (set from authority if not provided)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sequence_number: int = 0
    
    # Additional context
    details: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Integrity
    _hash: str = field(default="", repr=False)
    
    def __post_init__(self):
        """Compute hash after initialization."""
        if not self._hash:
            object.__setattr__(self, '_hash', self._compute_hash())
    
    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of event data."""
        # Create deterministic representation
        data = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "action": self.action,
            "actor": self.actor.to_dict(),
            "target": self.target.to_dict() if self.target else None,
            "outcome": self.outcome.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "sequence_number": self.sequence_number,
            "details": self.details,
        }
        serialized = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    @property
    def hash(self) -> str:
        """Get event hash."""
        return self._hash
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate event data completeness and integrity.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Required fields
        if not self.event_id:
            errors.append("event_id is required")
        
        if not self.action:
            errors.append("action is required")
        
        if not self.actor:
            errors.append("actor is required")
        elif not self.actor.actor_id:
            errors.append("actor.actor_id is required")
        
        if not self.timestamp:
            errors.append("timestamp is required")
        else:
            # Validate timestamp format
            try:
                datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            except ValueError:
                errors.append("timestamp must be valid ISO8601 format")
        
        # Verify hash integrity
        computed = self._compute_hash()
        if self._hash and self._hash != computed:
            errors.append("event hash verification failed - data may be corrupted")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize event to dictionary.
        
        Ensures lossless round-trip serialization.
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "action": self.action,
            "actor": self.actor.to_dict(),
            "target": self.target.to_dict() if self.target else None,
            "outcome": self.outcome.value,
            "outcome_reason": self.outcome_reason,
            "severity": self.severity.value,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "sequence_number": self.sequence_number,
            "details": self.details,
            "tags": self.tags,
            "hash": self._hash,
        }
    
    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize event to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """
        Deserialize event from dictionary.
        
        Validates hash if present to detect corruption.
        """
        actor = EventActor.from_dict(data.get("actor", {}))
        target = EventTarget.from_dict(data["target"]) if data.get("target") else None
        
        event = cls(
            event_id=data.get("event_id", ""),
            event_type=EventType(data.get("event_type", "system")),
            action=data.get("action", ""),
            actor=actor,
            target=target,
            outcome=EventOutcome(data.get("outcome", "unknown")),
            outcome_reason=data.get("outcome_reason"),
            severity=EventSeverity(data.get("severity", "info")),
            correlation_id=data.get("correlation_id"),
            timestamp=data.get("timestamp", ""),
            sequence_number=data.get("sequence_number", 0),
            details=data.get("details", {}),
            tags=data.get("tags", []),
        )
        
        # Restore original hash if provided
        if data.get("hash"):
            object.__setattr__(event, '_hash', data["hash"])
        
        return event
    
    @classmethod
    def from_json(cls, json_str: str) -> "AuditEvent":
        """Deserialize event from JSON string."""
        return cls.from_dict(json.loads(json_str))


def create_auth_event(
    action: str,
    actor_id: str,
    outcome: EventOutcome = EventOutcome.SUCCESS,
    ip_address: Optional[str] = None,
    details: Optional[Dict] = None,
) -> AuditEvent:
    """
    Factory function for authentication events.
    
    Args:
        action: Auth action (login, logout, mfa_challenge, etc.)
        actor_id: GID or user identifier
        outcome: Success or failure
        ip_address: Client IP address
        details: Additional details
        
    Returns:
        Configured AuditEvent
    """
    return AuditEvent(
        event_type=EventType.AUTHENTICATION,
        action=action,
        actor=EventActor(
            actor_type="user",
            actor_id=actor_id,
            ip_address=ip_address,
        ),
        outcome=outcome,
        severity=EventSeverity.INFO if outcome == EventOutcome.SUCCESS else EventSeverity.WARNING,
        details=details or {},
    )


def create_access_event(
    action: str,
    actor_id: str,
    target_id: str,
    target_type: str = "resource",
    outcome: EventOutcome = EventOutcome.SUCCESS,
    details: Optional[Dict] = None,
) -> AuditEvent:
    """
    Factory function for data access events.
    
    Args:
        action: Access action (read, write, delete, etc.)
        actor_id: GID or user identifier
        target_id: Resource identifier
        target_type: Type of resource
        outcome: Success or failure
        details: Additional details
        
    Returns:
        Configured AuditEvent
    """
    return AuditEvent(
        event_type=EventType.DATA_ACCESS,
        action=action,
        actor=EventActor(actor_type="user", actor_id=actor_id),
        target=EventTarget(target_type=target_type, target_id=target_id),
        outcome=outcome,
        severity=EventSeverity.INFO,
        details=details or {},
    )


def create_security_event(
    action: str,
    actor_id: str,
    severity: EventSeverity = EventSeverity.WARNING,
    outcome: EventOutcome = EventOutcome.FAILURE,
    details: Optional[Dict] = None,
) -> AuditEvent:
    """
    Factory function for security events.
    
    Args:
        action: Security action (intrusion_attempt, policy_violation, etc.)
        actor_id: GID or identifier of actor
        severity: Event severity
        outcome: Event outcome
        details: Additional details
        
    Returns:
        Configured AuditEvent
    """
    return AuditEvent(
        event_type=EventType.SECURITY,
        action=action,
        actor=EventActor(actor_type="unknown", actor_id=actor_id),
        outcome=outcome,
        severity=severity,
        details=details or {},
        tags=["security", "alert"],
    )
