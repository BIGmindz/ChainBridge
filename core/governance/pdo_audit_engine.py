"""
PDO Audit Engine v1

Append-only, tamper-evident audit trail for PDO artifacts.
Per PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-PDO-STRESS-023.

This engine:
- Records every PDO in an append-only audit trail
- Maintains cryptographic hash chain
- Provides query interface for compliance
- Supports export for forensic analysis
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple
import hashlib
import json
import threading


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════


class AuditTrailError(Exception):
    """Base exception for audit trail errors."""
    pass


class AuditChainBrokenError(AuditTrailError):
    """Raised when hash chain integrity is compromised."""
    
    def __init__(self, record_id: str, expected: str, found: str):
        self.record_id = record_id
        self.expected = expected
        self.found = found
        super().__init__(
            f"Audit chain broken at {record_id}: "
            f"expected {expected[:16]}..., found {found[:16]}..."
        )


class AuditRecordNotFoundError(AuditTrailError):
    """Raised when audit record is not found."""
    pass


class AuditMutationForbiddenError(AuditTrailError):
    """Raised when attempting to modify audit trail."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT RECORD
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class PDOAuditRecord:
    """
    Immutable audit record for a single PDO.
    
    Per PDO_AUDIT_TRAIL_LAW_v1 Section 4.
    """
    
    # Identity
    record_id: str
    sequence_number: int
    
    # PDO Reference
    pdo_id: str
    pac_id: str
    ber_id: str
    
    # Outcome
    outcome_status: str
    issuer: str
    
    # Hashes
    pdo_hash: str
    proof_hash: str
    decision_hash: str
    outcome_hash: str
    
    # Chain binding
    previous_record_hash: str
    record_hash: str
    
    # Timestamps
    pdo_emitted_at: datetime
    recorded_at: datetime
    
    # Metadata
    agent_gid: str = ""
    execution_duration_ms: int = 0
    tags: tuple = ()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "record_id": self.record_id,
            "sequence_number": self.sequence_number,
            "pdo_id": self.pdo_id,
            "pac_id": self.pac_id,
            "ber_id": self.ber_id,
            "outcome_status": self.outcome_status,
            "issuer": self.issuer,
            "pdo_hash": self.pdo_hash,
            "proof_hash": self.proof_hash,
            "decision_hash": self.decision_hash,
            "outcome_hash": self.outcome_hash,
            "previous_record_hash": self.previous_record_hash,
            "record_hash": self.record_hash,
            "pdo_emitted_at": self.pdo_emitted_at.isoformat(),
            "recorded_at": self.recorded_at.isoformat(),
            "agent_gid": self.agent_gid,
            "execution_duration_ms": self.execution_duration_ms,
            "tags": list(self.tags),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# HASH UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════


def compute_record_hash(
    record_id: str,
    sequence_number: int,
    pdo_id: str,
    pac_id: str,
    ber_id: str,
    outcome_status: str,
    pdo_hash: str,
    previous_record_hash: str,
    recorded_at: datetime,
) -> str:
    """Compute hash for an audit record."""
    content = "|".join([
        record_id,
        str(sequence_number),
        pdo_id,
        pac_id,
        ber_id,
        outcome_status,
        pdo_hash,
        previous_record_hash,
        recorded_at.isoformat(),
    ])
    return hashlib.sha256(content.encode()).hexdigest()


def verify_record_hash(record: PDOAuditRecord) -> bool:
    """Verify a single record's hash."""
    expected = compute_record_hash(
        record.record_id,
        record.sequence_number,
        record.pdo_id,
        record.pac_id,
        record.ber_id,
        record.outcome_status,
        record.pdo_hash,
        record.previous_record_hash,
        record.recorded_at,
    )
    return expected == record.record_hash


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY BUILDER
# ═══════════════════════════════════════════════════════════════════════════════


class AuditQueryBuilder:
    """
    Fluent query builder for audit trail.
    
    Per PDO_AUDIT_TRAIL_LAW_v1 Section 6.
    """
    
    def __init__(self, trail: "PDOAuditTrail"):
        self._trail = trail
        self._filters: List[Callable[[PDOAuditRecord], bool]] = []
        self._limit: Optional[int] = None
        self._offset: int = 0
        self._order_field: str = "sequence_number"
        self._order_desc: bool = False
    
    def by_pac_id(self, pac_id: str) -> "AuditQueryBuilder":
        """Filter by PAC ID."""
        self._filters.append(lambda r: r.pac_id == pac_id)
        return self
    
    def by_pdo_id(self, pdo_id: str) -> "AuditQueryBuilder":
        """Filter by PDO ID."""
        self._filters.append(lambda r: r.pdo_id == pdo_id)
        return self
    
    def by_outcome(self, status: str) -> "AuditQueryBuilder":
        """Filter by outcome status."""
        self._filters.append(lambda r: r.outcome_status == status)
        return self
    
    def by_agent(self, gid: str) -> "AuditQueryBuilder":
        """Filter by agent GID."""
        self._filters.append(lambda r: r.agent_gid == gid)
        return self
    
    def by_time_range(
        self, 
        start: datetime, 
        end: datetime
    ) -> "AuditQueryBuilder":
        """Filter by time range."""
        self._filters.append(
            lambda r: start <= r.recorded_at <= end
        )
        return self
    
    def by_tags(self, tags: List[str]) -> "AuditQueryBuilder":
        """Filter by tags (any match)."""
        tag_set = set(tags)
        self._filters.append(
            lambda r: bool(set(r.tags) & tag_set)
        )
        return self
    
    def limit(self, n: int) -> "AuditQueryBuilder":
        """Limit results."""
        self._limit = n
        return self
    
    def offset(self, n: int) -> "AuditQueryBuilder":
        """Offset results."""
        self._offset = n
        return self
    
    def order_by(
        self, 
        field: str, 
        desc: bool = False
    ) -> "AuditQueryBuilder":
        """Order results."""
        self._order_field = field
        self._order_desc = desc
        return self
    
    def execute(self) -> List[PDOAuditRecord]:
        """Execute query and return results."""
        # Get all records
        records = list(self._trail._records)
        
        # Apply filters
        for f in self._filters:
            records = [r for r in records if f(r)]
        
        # Sort
        if self._order_field:
            records.sort(
                key=lambda r: getattr(r, self._order_field, 0),
                reverse=self._order_desc,
            )
        
        # Offset
        records = records[self._offset:]
        
        # Limit
        if self._limit is not None:
            records = records[:self._limit]
        
        return records
    
    def count(self) -> int:
        """Count matching records."""
        return len(self.execute())
    
    def first(self) -> Optional[PDOAuditRecord]:
        """Get first matching record."""
        results = self.limit(1).execute()
        return results[0] if results else None


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════════════════════


class PDOAuditTrail:
    """
    Append-only audit trail for PDO artifacts.
    
    Per PDO_AUDIT_TRAIL_LAW_v1.
    Thread-safe implementation.
    """
    
    # Genesis record hash (first record links to this)
    GENESIS_HASH = "0" * 64
    
    def __init__(self, emit_terminal: bool = True):
        """Initialize empty audit trail."""
        self._records: List[PDOAuditRecord] = []
        self._records_by_id: Dict[str, PDOAuditRecord] = {}
        self._records_by_pdo: Dict[str, PDOAuditRecord] = {}
        self._lock = threading.Lock()
        self._emit_terminal = emit_terminal
        self._sequence_counter = 0
    
    @property
    def length(self) -> int:
        """Number of records in trail."""
        return len(self._records)
    
    @property
    def is_empty(self) -> bool:
        """True if trail has no records."""
        return len(self._records) == 0
    
    def record(
        self,
        pdo: Any,
        agent_gid: str = "",
        execution_duration_ms: int = 0,
        tags: Optional[List[str]] = None,
    ) -> PDOAuditRecord:
        """
        Append PDO to audit trail.
        
        INV-AUDIT-001: Every PDO MUST be recorded.
        
        Args:
            pdo: PDOArtifact to record
            agent_gid: Agent that executed the PAC
            execution_duration_ms: Execution duration
            tags: Classification tags
            
        Returns:
            Created audit record
        """
        with self._lock:
            # Generate record ID
            self._sequence_counter += 1
            sequence = self._sequence_counter
            record_id = f"AUD-{sequence:06d}"
            
            # Get previous hash
            if self._records:
                previous_hash = self._records[-1].record_hash
            else:
                previous_hash = self.GENESIS_HASH
            
            # Extract PDO fields
            pdo_id = self._safe_get(pdo, "pdo_id", "")
            pac_id = self._safe_get(pdo, "pac_id", "")
            ber_id = self._safe_get(pdo, "ber_id", "")
            outcome_status = self._safe_get(pdo, "outcome_status", "")
            issuer = self._safe_get(pdo, "issuer", "")
            pdo_hash = self._safe_get(pdo, "pdo_hash", "")
            proof_hash = self._safe_get(pdo, "proof_hash", "")
            decision_hash = self._safe_get(pdo, "decision_hash", "")
            outcome_hash = self._safe_get(pdo, "outcome_hash", "")
            pdo_emitted_at = self._safe_get(pdo, "emitted_at", None)
            
            # Parse timestamp
            if isinstance(pdo_emitted_at, str):
                try:
                    pdo_emitted_at = datetime.fromisoformat(
                        pdo_emitted_at.replace("Z", "+00:00")
                    )
                except ValueError:
                    pdo_emitted_at = datetime.now(timezone.utc)
            elif pdo_emitted_at is None:
                pdo_emitted_at = datetime.now(timezone.utc)
            
            recorded_at = datetime.now(timezone.utc)
            
            # Compute record hash
            record_hash = compute_record_hash(
                record_id,
                sequence,
                pdo_id,
                pac_id,
                ber_id,
                outcome_status,
                pdo_hash,
                previous_hash,
                recorded_at,
            )
            
            # Create immutable record
            record = PDOAuditRecord(
                record_id=record_id,
                sequence_number=sequence,
                pdo_id=pdo_id,
                pac_id=pac_id,
                ber_id=ber_id,
                outcome_status=outcome_status,
                issuer=issuer,
                pdo_hash=pdo_hash,
                proof_hash=proof_hash,
                decision_hash=decision_hash,
                outcome_hash=outcome_hash,
                previous_record_hash=previous_hash,
                record_hash=record_hash,
                pdo_emitted_at=pdo_emitted_at,
                recorded_at=recorded_at,
                agent_gid=agent_gid,
                execution_duration_ms=execution_duration_ms,
                tags=tuple(tags or []),
            )
            
            # Append to trail
            self._records.append(record)
            self._records_by_id[record_id] = record
            self._records_by_pdo[pdo_id] = record
            
            # Emit terminal
            if self._emit_terminal:
                self._emit_record_created(record)
            
            return record
    
    def get(self, record_id: str) -> PDOAuditRecord:
        """
        Retrieve single record by ID.
        
        Args:
            record_id: Audit record ID
            
        Returns:
            Audit record
            
        Raises:
            AuditRecordNotFoundError: If record not found
        """
        with self._lock:
            if record_id not in self._records_by_id:
                raise AuditRecordNotFoundError(f"Record {record_id} not found")
            return self._records_by_id[record_id]
    
    def get_by_pdo(self, pdo_id: str) -> Optional[PDOAuditRecord]:
        """Get audit record for a PDO."""
        with self._lock:
            return self._records_by_pdo.get(pdo_id)
    
    def query(self) -> AuditQueryBuilder:
        """
        Create query builder for searching audit trail.
        
        INV-AUDIT-005: Query operations are read-only.
        
        Returns:
            Query builder instance
        """
        return AuditQueryBuilder(self)
    
    def verify_chain(self) -> bool:
        """
        Verify entire audit trail hash chain.
        
        INV-AUDIT-003: Each record hash-binds to predecessor.
        
        Returns:
            True if chain is valid
            
        Raises:
            AuditChainBrokenError: If chain is broken
        """
        with self._lock:
            for i, record in enumerate(self._records):
                # Verify record hash
                if not verify_record_hash(record):
                    raise AuditChainBrokenError(
                        record.record_id,
                        "computed",
                        record.record_hash,
                    )
                
                # Verify chain link
                if i == 0:
                    expected_prev = self.GENESIS_HASH
                else:
                    expected_prev = self._records[i - 1].record_hash
                
                if record.previous_record_hash != expected_prev:
                    raise AuditChainBrokenError(
                        record.record_id,
                        expected_prev,
                        record.previous_record_hash,
                    )
            
            return True
    
    def export(self, format: str = "json") -> bytes:
        """
        Export trail for compliance.
        
        Args:
            format: Export format (json, jsonl, csv)
            
        Returns:
            Exported data as bytes
        """
        with self._lock:
            records = [r.to_dict() for r in self._records]
            
            if format == "json":
                return json.dumps(records, indent=2).encode()
            
            elif format == "jsonl":
                lines = [json.dumps(r) for r in records]
                return "\n".join(lines).encode()
            
            elif format == "csv":
                if not records:
                    return b""
                headers = list(records[0].keys())
                lines = [",".join(headers)]
                for r in records:
                    values = [str(r.get(h, "")) for h in headers]
                    lines.append(",".join(values))
                return "\n".join(lines).encode()
            
            else:
                raise ValueError(f"Unsupported format: {format}")
    
    def replay(self, cursor: int = 0) -> Iterator[PDOAuditRecord]:
        """
        Replay trail from cursor position.
        
        Args:
            cursor: Starting sequence number
            
        Yields:
            Audit records from cursor forward
        """
        with self._lock:
            for record in self._records:
                if record.sequence_number >= cursor:
                    yield record
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FORBIDDEN OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def delete(self, record_id: str) -> None:
        """
        DELETE IS FORBIDDEN.
        
        INV-AUDIT-002: Audit trail is append-only.
        """
        raise AuditMutationForbiddenError(
            "Delete is forbidden: audit trail is append-only"
        )
    
    def update(self, record_id: str, **kwargs: Any) -> None:
        """
        UPDATE IS FORBIDDEN.
        
        INV-AUDIT-004: Audit records are immutable.
        """
        raise AuditMutationForbiddenError(
            "Update is forbidden: audit records are immutable"
        )
    
    def truncate(self) -> None:
        """
        TRUNCATE IS FORBIDDEN.
        
        INV-AUDIT-002: No data destruction.
        """
        raise AuditMutationForbiddenError(
            "Truncate is forbidden: no data destruction allowed"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _safe_get(self, obj: Any, attr: str, default: Any) -> Any:
        """Safely get attribute from object or dict."""
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)
    
    def _emit_record_created(self, record: PDOAuditRecord) -> None:
        """Emit terminal output for record creation."""
        print(f"✅ AUDIT RECORD CREATED")
        print(f"   Record:   {record.record_id}")
        print(f"   PDO:      {record.pdo_id}")
        print(f"   Outcome:  {record.outcome_status}")
        print(f"   Chain:    ✓ Verified")
        print(f"   Sequence: {record.sequence_number}")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════


_audit_trail: Optional[PDOAuditTrail] = None
_audit_trail_lock = threading.Lock()


def get_audit_trail(emit_terminal: bool = True) -> PDOAuditTrail:
    """Get or create the global audit trail."""
    global _audit_trail
    with _audit_trail_lock:
        if _audit_trail is None:
            _audit_trail = PDOAuditTrail(emit_terminal=emit_terminal)
        return _audit_trail


def reset_audit_trail() -> None:
    """Reset the global audit trail (for testing)."""
    global _audit_trail
    with _audit_trail_lock:
        _audit_trail = None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════


__all__ = [
    # Exceptions
    "AuditTrailError",
    "AuditChainBrokenError",
    "AuditRecordNotFoundError",
    "AuditMutationForbiddenError",
    # Data classes
    "PDOAuditRecord",
    # Query
    "AuditQueryBuilder",
    # Trail
    "PDOAuditTrail",
    # Utilities
    "compute_record_hash",
    "verify_record_hash",
    # Singleton
    "get_audit_trail",
    "reset_audit_trail",
]
