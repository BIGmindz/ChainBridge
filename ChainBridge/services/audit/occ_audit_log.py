"""
OCC Audit Log - Immutable audit trail for Operator Control Center.

PAC Reference: PAC-OCC-P02
Constitutional Authority: OCC_CONSTITUTION_v1.0, Article VI
Invariants Enforced: INV-OCC-002 (Override Audit Immutability), INV-OVR-003, INV-OVR-004

This module implements an append-only, hash-chained audit log that:
1. Records all OCC actions with complete attribution
2. Enforces immutability (no updates, deletes)
3. Maintains cryptographic hash chain for tamper detection
4. Supports deterministic replay
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterator


class AuditRecordType(str, Enum):
    """
    Types of audit records.
    
    Constitutional basis: All OCC operations must be auditable.
    """
    # Queue operations
    QUEUE_ENQUEUE = "QUEUE_ENQUEUE"
    QUEUE_DEQUEUE = "QUEUE_DEQUEUE"
    QUEUE_ESCALATE = "QUEUE_ESCALATE"
    
    # Action operations
    ACTION_SUBMITTED = "ACTION_SUBMITTED"
    ACTION_VALIDATED = "ACTION_VALIDATED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    ACTION_BLOCKED = "ACTION_BLOCKED"
    
    # Override operations (special tracking)
    OVERRIDE_REQUESTED = "OVERRIDE_REQUESTED"
    OVERRIDE_VALIDATED = "OVERRIDE_VALIDATED"
    OVERRIDE_EXECUTED = "OVERRIDE_EXECUTED"
    OVERRIDE_BLOCKED = "OVERRIDE_BLOCKED"
    
    # State machine operations
    PDO_TRANSITION = "PDO_TRANSITION"
    PDO_OVERRIDE_APPLIED = "PDO_OVERRIDE_APPLIED"
    
    # System events
    SYSTEM_STARTUP = "SYSTEM_STARTUP"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    SYSTEM_FAIL_CLOSED = "SYSTEM_FAIL_CLOSED"
    
    # Authentication events
    OPERATOR_LOGIN = "OPERATOR_LOGIN"
    OPERATOR_LOGOUT = "OPERATOR_LOGOUT"
    MFA_VERIFIED = "MFA_VERIFIED"
    
    # Error events
    INVARIANT_VIOLATION = "INVARIANT_VIOLATION"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"


@dataclass(frozen=True)
class AuditRecord:
    """
    A single immutable audit record.
    
    Invariant: INV-OCC-002 - Records cannot be modified after creation.
    Invariant: INV-OVR-003 - Override records are append-only.
    """
    id: str
    record_type: AuditRecordType
    timestamp: datetime
    operator_id: str | None  # None for SYSTEM events
    operator_tier: str | None
    session_id: str | None
    ip_address: str | None
    user_agent: str | None
    target_id: str | None  # PDO ID, Queue Item ID, etc.
    action_type: str | None
    payload: dict[str, Any]
    result: str  # SUCCESS, BLOCKED, ERROR
    message: str
    hash_previous: str | None
    hash_current: str
    
    @staticmethod
    def compute_hash(
        id: str,
        record_type: AuditRecordType,
        timestamp: datetime,
        operator_id: str | None,
        target_id: str | None,
        result: str,
        hash_previous: str | None,
    ) -> str:
        """Compute cryptographic hash for audit record."""
        content = (
            f"{id}|{record_type.value}|{timestamp.isoformat()}|"
            f"{operator_id or 'SYSTEM'}|{target_id or 'N/A'}|"
            f"{result}|{hash_previous or 'GENESIS'}"
        )
        return hashlib.sha256(content.encode()).hexdigest()


class AuditImmutabilityViolation(Exception):
    """Raised when an attempt is made to modify or delete audit records."""


class AuditChainBrokenError(Exception):
    """Raised when hash chain integrity is compromised."""


class OCCAuditLog:
    """
    Immutable, hash-chained audit log for OCC operations.
    
    Constitutional Invariants Enforced:
    - INV-OCC-002: Override Audit Immutability
    - INV-OVR-003: Override Immutability (append-only)
    - INV-OVR-004: Override Audit Trail (complete records)
    
    This implementation:
    - Append-only: No update or delete operations
    - Hash-chained: Each record includes hash of previous
    - Thread-safe: All operations are synchronized
    - Persistent: Records are written to disk
    """
    
    # Singleton enforcement
    _INSTANCE: OCCAuditLog | None = None
    _LOCK = threading.Lock()
    
    # Required fields for override records per INV-OVR-004
    OVERRIDE_REQUIRED_FIELDS = {
        "override_id",
        "operator_id",
        "operator_tier",
        "target_pdo_id",
        "original_decision",
        "override_decision",
        "justification",
        "constitutional_citation",
        "risk_acknowledgment",
        "timestamp",
        "session_id",
        "ip_address",
    }
    
    def __init__(
        self,
        log_dir: Path | None = None,
        max_memory_records: int = 10000,
    ) -> None:
        """
        Initialize OCC Audit Log.
        
        Args:
            log_dir: Directory for persistent log files
            max_memory_records: Maximum records to keep in memory
        """
        self._records: list[AuditRecord] = []
        self._lock = threading.Lock()
        self._sequence_counter = 0
        self._last_hash: str | None = None
        self._log_dir = log_dir
        self._max_memory_records = max_memory_records
        self._closed = False
        
        # Create log directory if specified
        if self._log_dir:
            self._log_dir.mkdir(parents=True, exist_ok=True)
        
        # Log startup
        self._record_system_event(AuditRecordType.SYSTEM_STARTUP, "OCC Audit Log initialized")
        
    @classmethod
    def get_instance(cls) -> OCCAuditLog:
        """Get singleton instance."""
        if cls._INSTANCE is None:
            with cls._LOCK:
                if cls._INSTANCE is None:
                    cls._INSTANCE = cls()
        return cls._INSTANCE
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton for testing."""
        with cls._LOCK:
            cls._INSTANCE = None
    
    def record(
        self,
        record_type: AuditRecordType,
        operator_id: str | None = None,
        operator_tier: str | None = None,
        session_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        target_id: str | None = None,
        action_type: str | None = None,
        payload: dict[str, Any] | None = None,
        result: str = "SUCCESS",
        message: str = "",
    ) -> AuditRecord:
        """
        Record an audit event.
        
        Args:
            record_type: Type of audit record
            operator_id: ID of operator (None for system events)
            operator_tier: Tier of operator
            session_id: Session ID
            ip_address: Client IP address
            user_agent: Client user agent
            target_id: Target entity ID (PDO, queue item, etc.)
            action_type: Type of action performed
            payload: Additional event data
            result: Result of operation
            message: Human-readable message
            
        Returns:
            The created AuditRecord
        """
        with self._lock:
            if self._closed:
                raise AuditImmutabilityViolation(
                    "Audit log is closed - fail-closed state"
                )
            
            # Validate override records have required fields
            if record_type in (
                AuditRecordType.OVERRIDE_REQUESTED,
                AuditRecordType.OVERRIDE_EXECUTED,
            ):
                self._validate_override_payload(payload or {})
            
            # Generate record ID
            self._sequence_counter += 1
            record_id = f"AUD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{self._sequence_counter:08d}"
            timestamp = datetime.now(timezone.utc)
            
            # Compute hash
            hash_current = AuditRecord.compute_hash(
                id=record_id,
                record_type=record_type,
                timestamp=timestamp,
                operator_id=operator_id,
                target_id=target_id,
                result=result,
                hash_previous=self._last_hash,
            )
            
            # Create record
            record = AuditRecord(
                id=record_id,
                record_type=record_type,
                timestamp=timestamp,
                operator_id=operator_id,
                operator_tier=operator_tier,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                target_id=target_id,
                action_type=action_type,
                payload=payload or {},
                result=result,
                message=message,
                hash_previous=self._last_hash,
                hash_current=hash_current,
            )
            
            # Append to log (immutable operation)
            self._records.append(record)
            self._last_hash = hash_current
            
            # Persist to disk if configured
            if self._log_dir:
                self._persist_record(record)
            
            # Trim memory if needed (keep tail)
            if len(self._records) > self._max_memory_records:
                self._records = self._records[-self._max_memory_records:]
            
            return record
    
    def _validate_override_payload(self, payload: dict[str, Any]) -> None:
        """
        Validate override record has all required fields per INV-OVR-004.
        
        Raises:
            AuditImmutabilityViolation: If required fields are missing
        """
        missing = self.OVERRIDE_REQUIRED_FIELDS - set(payload.keys())
        if missing:
            raise AuditImmutabilityViolation(
                f"INV-OVR-004 VIOLATION: Override audit record missing required fields: {missing}"
            )
    
    def _record_system_event(
        self, record_type: AuditRecordType, message: str
    ) -> AuditRecord:
        """Record a system event (no operator context)."""
        return self.record(
            record_type=record_type,
            result="SUCCESS",
            message=message,
        )
    
    def _persist_record(self, record: AuditRecord) -> None:
        """
        Persist record to disk.
        
        Uses append-only file operations for immutability.
        """
        if not self._log_dir:
            return
        
        # Daily log files
        log_file = self._log_dir / f"occ_audit_{record.timestamp.strftime('%Y%m%d')}.jsonl"
        
        # Convert to JSON (handle datetime serialization)
        record_dict = {
            "id": record.id,
            "record_type": record.record_type.value,
            "timestamp": record.timestamp.isoformat(),
            "operator_id": record.operator_id,
            "operator_tier": record.operator_tier,
            "session_id": record.session_id,
            "ip_address": record.ip_address,
            "user_agent": record.user_agent,
            "target_id": record.target_id,
            "action_type": record.action_type,
            "payload": record.payload,
            "result": record.result,
            "message": record.message,
            "hash_previous": record.hash_previous,
            "hash_current": record.hash_current,
        }
        
        # Append to file (atomic operation)
        with open(log_file, "a") as f:
            f.write(json.dumps(record_dict) + "\n")
    
    def get_records(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        record_type: AuditRecordType | None = None,
        operator_id: str | None = None,
        target_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditRecord]:
        """
        Query audit records with filters.
        
        Note: This is a read-only operation.
        
        Args:
            start_time: Filter by start time
            end_time: Filter by end time
            record_type: Filter by record type
            operator_id: Filter by operator
            target_id: Filter by target entity
            limit: Maximum records to return
            
        Returns:
            List of matching records
        """
        with self._lock:
            results = []
            for record in reversed(self._records):  # Most recent first
                if len(results) >= limit:
                    break
                
                # Apply filters
                if start_time and record.timestamp < start_time:
                    continue
                if end_time and record.timestamp > end_time:
                    continue
                if record_type and record.record_type != record_type:
                    continue
                if operator_id and record.operator_id != operator_id:
                    continue
                if target_id and record.target_id != target_id:
                    continue
                
                results.append(record)
            
            return results
    
    def get_record_by_id(self, record_id: str) -> AuditRecord | None:
        """Get a specific audit record by ID."""
        with self._lock:
            for record in self._records:
                if record.id == record_id:
                    return record
            return None
    
    def get_override_history(self, pdo_id: str) -> list[AuditRecord]:
        """
        Get override history for a specific PDO.
        
        Returns all override-related audit records for the PDO.
        """
        override_types = {
            AuditRecordType.OVERRIDE_REQUESTED,
            AuditRecordType.OVERRIDE_VALIDATED,
            AuditRecordType.OVERRIDE_EXECUTED,
            AuditRecordType.OVERRIDE_BLOCKED,
            AuditRecordType.PDO_OVERRIDE_APPLIED,
        }
        
        return self.get_records(
            target_id=pdo_id,
            limit=1000,  # Get all for specific PDO
        )
    
    def verify_chain_integrity(self) -> tuple[bool, str | None]:
        """
        Verify hash chain integrity of entire log.
        
        Returns:
            (is_valid, error_message)
        """
        with self._lock:
            if not self._records:
                return True, None
            
            for i, record in enumerate(self._records):
                # Verify previous hash link
                expected_previous = None if i == 0 else self._records[i - 1].hash_current
                if record.hash_previous != expected_previous:
                    return False, f"Chain broken at record {record.id}: expected previous {expected_previous}, got {record.hash_previous}"
                
                # Verify current hash
                computed = AuditRecord.compute_hash(
                    id=record.id,
                    record_type=record.record_type,
                    timestamp=record.timestamp,
                    operator_id=record.operator_id,
                    target_id=record.target_id,
                    result=record.result,
                    hash_previous=record.hash_previous,
                )
                
                if computed != record.hash_current:
                    return False, f"Hash mismatch at record {record.id}"
            
            return True, None
    
    def iter_records(self) -> Iterator[AuditRecord]:
        """
        Iterate over all records (chronological order).
        
        Note: Use with caution on large logs.
        """
        with self._lock:
            for record in self._records:
                yield record
    
    def get_statistics(self) -> dict[str, Any]:
        """Get audit log statistics."""
        with self._lock:
            type_counts: dict[str, int] = {}
            result_counts: dict[str, int] = {}
            
            for record in self._records:
                type_counts[record.record_type.value] = type_counts.get(
                    record.record_type.value, 0
                ) + 1
                result_counts[record.result] = result_counts.get(record.result, 0) + 1
            
            return {
                "total_records": len(self._records),
                "sequence_counter": self._sequence_counter,
                "records_by_type": type_counts,
                "records_by_result": result_counts,
                "chain_valid": self.verify_chain_integrity()[0],
            }
    
    def close(self) -> None:
        """
        Close audit log - enter fail-closed state.
        
        Records a final shutdown event before closing.
        """
        with self._lock:
            if not self._closed:
                # Record shutdown
                self._record_system_event(
                    AuditRecordType.SYSTEM_SHUTDOWN,
                    "OCC Audit Log shutting down"
                )
                self._closed = True
    
    def is_closed(self) -> bool:
        """Check if audit log is closed."""
        with self._lock:
            return self._closed
    
    # ==========================================================================
    # PROHIBITED OPERATIONS - Constitutional Enforcement
    # ==========================================================================
    
    def update(self, *args: Any, **kwargs: Any) -> None:
        """
        UPDATE IS PROHIBITED.
        
        Invariant: INV-OCC-002 - Override Audit Immutability
        Invariant: INV-OVR-003 - Override Immutability
        """
        raise AuditImmutabilityViolation(
            "INV-OCC-002/INV-OVR-003 VIOLATION: Audit records cannot be updated"
        )
    
    def delete(self, *args: Any, **kwargs: Any) -> None:
        """
        DELETE IS PROHIBITED.
        
        Invariant: INV-OCC-002 - Override Audit Immutability
        Invariant: INV-OVR-003 - Override Immutability
        """
        raise AuditImmutabilityViolation(
            "INV-OCC-002/INV-OVR-003 VIOLATION: Audit records cannot be deleted"
        )
    
    def truncate(self, *args: Any, **kwargs: Any) -> None:
        """
        TRUNCATE IS PROHIBITED.
        
        Invariant: INV-OCC-002 - Override Audit Immutability
        Invariant: INV-OVR-003 - Override Immutability
        """
        raise AuditImmutabilityViolation(
            "INV-OCC-002/INV-OVR-003 VIOLATION: Audit log cannot be truncated"
        )
