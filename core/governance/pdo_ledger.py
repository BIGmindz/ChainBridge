"""
PDO Ledger — Immutable, Append-Only Persistence Layer for PDO Artifacts
════════════════════════════════════════════════════════════════════════════════

This module provides the canonical persistence layer for PDO artifacts with:
    - Append-only storage (no UPDATE, no DELETE)
    - Cryptographic ordering (hash chain)
    - Audit-grade export
    - Tamper-evident verification

PAC Reference: PAC-JEFFREY-CHAINBRIDGE-PDO-CORE-EXEC-005
Effective Date: 2025-12-30

INVARIANTS:
    INV-LEDGER-001: Entries are immutable after creation
    INV-LEDGER-002: No UPDATE operations permitted
    INV-LEDGER-003: No DELETE operations permitted
    INV-LEDGER-004: Hash chain links all entries
    INV-LEDGER-005: Ordering is cryptographically enforced

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

LEDGER_VERSION = "1.0.0"
"""PDO Ledger version."""

GENESIS_HASH = "0" * 64
"""Genesis hash for first entry."""


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class LedgerError(Exception):
    """Base exception for ledger errors."""
    pass


class LedgerMutationForbiddenError(LedgerError):
    """Raised when attempting forbidden mutation (UPDATE/DELETE)."""
    
    def __init__(self, operation: str, entry_id: str):
        self.operation = operation
        self.entry_id = entry_id
        super().__init__(
            f"LEDGER_MUTATION_FORBIDDEN: {operation} on entry '{entry_id}' is prohibited. "
            f"Ledger is append-only (INV-LEDGER-002, INV-LEDGER-003)."
        )


class LedgerChainBrokenError(LedgerError):
    """Raised when hash chain verification fails."""
    
    def __init__(self, entry_id: str, expected: str, found: str):
        self.entry_id = entry_id
        self.expected = expected
        self.found = found
        super().__init__(
            f"LEDGER_CHAIN_BROKEN: Entry '{entry_id}' has broken chain. "
            f"Expected hash: {expected[:16]}..., Found: {found[:16]}..."
        )


class LedgerOrderingError(LedgerError):
    """Raised when ordering invariant is violated."""
    
    def __init__(self, entry_id: str, sequence: int, expected_sequence: int):
        self.entry_id = entry_id
        self.sequence = sequence
        self.expected_sequence = expected_sequence
        super().__init__(
            f"LEDGER_ORDERING_VIOLATION: Entry '{entry_id}' has sequence {sequence}, "
            f"expected {expected_sequence} (INV-LEDGER-005)."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LEDGER ENTRY
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LedgerEntry:
    """
    Immutable ledger entry for a PDO artifact.
    
    frozen=True ensures runtime immutability (INV-LEDGER-001).
    """
    
    # Identity
    entry_id: str
    sequence_number: int
    
    # PDO Reference
    pdo_id: str
    pac_id: str
    ber_id: str
    wrap_id: str
    
    # Outcome
    outcome_status: str
    issuer: str
    
    # Hashes
    pdo_hash: str
    proof_hash: str
    decision_hash: str
    outcome_hash: str
    
    # Chain binding
    previous_entry_hash: str
    entry_hash: str
    
    # Timestamps
    pdo_created_at: str
    ledger_recorded_at: str
    
    # Metadata
    ledger_version: str = LEDGER_VERSION
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "entry_id": self.entry_id,
            "sequence_number": self.sequence_number,
            "pdo_id": self.pdo_id,
            "pac_id": self.pac_id,
            "ber_id": self.ber_id,
            "wrap_id": self.wrap_id,
            "outcome_status": self.outcome_status,
            "issuer": self.issuer,
            "pdo_hash": self.pdo_hash,
            "proof_hash": self.proof_hash,
            "decision_hash": self.decision_hash,
            "outcome_hash": self.outcome_hash,
            "previous_entry_hash": self.previous_entry_hash,
            "entry_hash": self.entry_hash,
            "pdo_created_at": self.pdo_created_at,
            "ledger_recorded_at": self.ledger_recorded_at,
            "ledger_version": self.ledger_version,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string (deterministic)."""
        return json.dumps(self.to_dict(), sort_keys=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LedgerEntry":
        """Create from dictionary."""
        return cls(
            entry_id=data["entry_id"],
            sequence_number=data["sequence_number"],
            pdo_id=data["pdo_id"],
            pac_id=data["pac_id"],
            ber_id=data["ber_id"],
            wrap_id=data["wrap_id"],
            outcome_status=data["outcome_status"],
            issuer=data["issuer"],
            pdo_hash=data["pdo_hash"],
            proof_hash=data["proof_hash"],
            decision_hash=data["decision_hash"],
            outcome_hash=data["outcome_hash"],
            previous_entry_hash=data["previous_entry_hash"],
            entry_hash=data["entry_hash"],
            pdo_created_at=data["pdo_created_at"],
            ledger_recorded_at=data["ledger_recorded_at"],
            ledger_version=data.get("ledger_version", LEDGER_VERSION),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# HASH UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def compute_entry_hash(
    entry_id: str,
    sequence_number: int,
    pdo_id: str,
    pac_id: str,
    pdo_hash: str,
    previous_entry_hash: str,
    recorded_at: str,
) -> str:
    """Compute hash for a ledger entry."""
    content = "|".join([
        entry_id,
        str(sequence_number),
        pdo_id,
        pac_id,
        pdo_hash,
        previous_entry_hash,
        recorded_at,
    ])
    return hashlib.sha256(content.encode()).hexdigest()


def verify_entry_hash(entry: LedgerEntry) -> bool:
    """Verify a single entry's hash."""
    expected = compute_entry_hash(
        entry.entry_id,
        entry.sequence_number,
        entry.pdo_id,
        entry.pac_id,
        entry.pdo_hash,
        entry.previous_entry_hash,
        entry.ledger_recorded_at,
    )
    return expected == entry.entry_hash


# ═══════════════════════════════════════════════════════════════════════════════
# PDO LEDGER
# ═══════════════════════════════════════════════════════════════════════════════

class PDOLedger:
    """
    Append-only, hash-chained ledger for PDO artifacts.
    
    This is the canonical persistence layer that enforces:
        - No UPDATE operations (INV-LEDGER-002)
        - No DELETE operations (INV-LEDGER-003)
        - Hash chain integrity (INV-LEDGER-004)
        - Cryptographic ordering (INV-LEDGER-005)
    
    Thread-safe implementation.
    """
    
    def __init__(self):
        """Initialize empty ledger."""
        self._entries: List[LedgerEntry] = []
        self._by_pdo_id: Dict[str, LedgerEntry] = {}
        self._by_pac_id: Dict[str, LedgerEntry] = {}
        self._lock = threading.Lock()
    
    # ───────────────────────────────────────────────────────────────────────────
    # APPEND ONLY (CREATE)
    # ───────────────────────────────────────────────────────────────────────────
    
    def append(
        self,
        pdo_id: str,
        pac_id: str,
        ber_id: str,
        wrap_id: str,
        outcome_status: str,
        issuer: str,
        pdo_hash: str,
        proof_hash: str,
        decision_hash: str,
        outcome_hash: str,
        pdo_created_at: str,
    ) -> LedgerEntry:
        """
        Append a new entry to the ledger.
        
        This is the ONLY write operation permitted.
        
        Args:
            pdo_id: PDO identifier
            pac_id: PAC identifier
            ber_id: BER identifier
            wrap_id: WRAP identifier
            outcome_status: Outcome status (ACCEPTED/CORRECTIVE/REJECTED)
            issuer: Issuer GID
            pdo_hash: PDO artifact hash
            proof_hash: Proof hash
            decision_hash: Decision hash
            outcome_hash: Outcome hash
            pdo_created_at: When PDO was created
        
        Returns:
            LedgerEntry: The created entry
        """
        with self._lock:
            # Generate entry ID
            entry_id = f"ledger_{uuid.uuid4().hex[:12]}"
            
            # Get sequence and previous hash
            sequence = len(self._entries)
            previous_hash = (
                self._entries[-1].entry_hash if self._entries else GENESIS_HASH
            )
            
            # Timestamp
            recorded_at = datetime.now(timezone.utc).isoformat()
            
            # Compute entry hash
            entry_hash = compute_entry_hash(
                entry_id,
                sequence,
                pdo_id,
                pac_id,
                pdo_hash,
                previous_hash,
                recorded_at,
            )
            
            # Create immutable entry
            entry = LedgerEntry(
                entry_id=entry_id,
                sequence_number=sequence,
                pdo_id=pdo_id,
                pac_id=pac_id,
                ber_id=ber_id,
                wrap_id=wrap_id,
                outcome_status=outcome_status,
                issuer=issuer,
                pdo_hash=pdo_hash,
                proof_hash=proof_hash,
                decision_hash=decision_hash,
                outcome_hash=outcome_hash,
                previous_entry_hash=previous_hash,
                entry_hash=entry_hash,
                pdo_created_at=pdo_created_at,
                ledger_recorded_at=recorded_at,
            )
            
            # Append to structures
            self._entries.append(entry)
            self._by_pdo_id[pdo_id] = entry
            self._by_pac_id[pac_id] = entry
            
            return entry
    
    def append_pdo(self, pdo: Any) -> LedgerEntry:
        """
        Append a PDO artifact to the ledger.
        
        Convenience method that extracts fields from PDOArtifact.
        
        Args:
            pdo: PDOArtifact instance
        
        Returns:
            LedgerEntry: The created entry
        """
        return self.append(
            pdo_id=pdo.pdo_id,
            pac_id=pdo.pac_id,
            ber_id=pdo.ber_id,
            wrap_id=pdo.wrap_id,
            outcome_status=pdo.outcome_status,
            issuer=pdo.issuer,
            pdo_hash=pdo.pdo_hash,
            proof_hash=pdo.proof_hash,
            decision_hash=pdo.decision_hash,
            outcome_hash=pdo.outcome_hash,
            pdo_created_at=pdo.created_at,
        )
    
    # ───────────────────────────────────────────────────────────────────────────
    # FORBIDDEN OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def update(self, entry_id: str, **kwargs: Any) -> None:
        """
        UPDATE is forbidden.
        
        INV-LEDGER-002: No UPDATE operations permitted.
        """
        raise LedgerMutationForbiddenError("UPDATE", entry_id)
    
    def delete(self, entry_id: str) -> None:
        """
        DELETE is forbidden.
        
        INV-LEDGER-003: No DELETE operations permitted.
        """
        raise LedgerMutationForbiddenError("DELETE", entry_id)
    
    # ───────────────────────────────────────────────────────────────────────────
    # READ OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_by_pdo_id(self, pdo_id: str) -> Optional[LedgerEntry]:
        """Get entry by PDO ID."""
        with self._lock:
            return self._by_pdo_id.get(pdo_id)
    
    def get_by_pac_id(self, pac_id: str) -> Optional[LedgerEntry]:
        """Get entry by PAC ID."""
        with self._lock:
            return self._by_pac_id.get(pac_id)
    
    def get_by_sequence(self, sequence: int) -> Optional[LedgerEntry]:
        """Get entry by sequence number."""
        with self._lock:
            if 0 <= sequence < len(self._entries):
                return self._entries[sequence]
            return None
    
    def get_all(self) -> List[LedgerEntry]:
        """Get all entries (ordered by sequence)."""
        with self._lock:
            return self._entries.copy()
    
    def get_latest(self) -> Optional[LedgerEntry]:
        """Get the most recent entry."""
        with self._lock:
            return self._entries[-1] if self._entries else None
    
    def __len__(self) -> int:
        """Get number of entries."""
        with self._lock:
            return len(self._entries)
    
    def __bool__(self) -> bool:
        """
        Ledger is always truthy even when empty.
        
        This prevents the subtle bug where `ledger or get_pdo_ledger()`
        would use the singleton when an empty custom ledger is passed.
        A ledger exists as a valid object regardless of contents.
        """
        return True
    
    def __iter__(self) -> Iterator[LedgerEntry]:
        """Iterate over entries (ordered)."""
        with self._lock:
            entries = self._entries.copy()
        yield from entries
    
    # ───────────────────────────────────────────────────────────────────────────
    # VERIFICATION
    # ───────────────────────────────────────────────────────────────────────────
    
    def verify_chain(self) -> Tuple[bool, Optional[str]]:
        """
        Verify entire hash chain integrity.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        with self._lock:
            if not self._entries:
                return True, None
            
            # Verify first entry links to genesis
            first = self._entries[0]
            if first.previous_entry_hash != GENESIS_HASH:
                return False, f"First entry does not link to genesis"
            
            # Verify each entry
            for i, entry in enumerate(self._entries):
                # Verify sequence
                if entry.sequence_number != i:
                    return False, f"Entry {entry.entry_id} has wrong sequence"
                
                # Verify hash
                if not verify_entry_hash(entry):
                    return False, f"Entry {entry.entry_id} has invalid hash"
                
                # Verify chain link (except first)
                if i > 0:
                    expected_previous = self._entries[i - 1].entry_hash
                    if entry.previous_entry_hash != expected_previous:
                        return False, f"Entry {entry.entry_id} has broken chain"
            
            return True, None
    
    def verify_entry(self, entry_id: str) -> bool:
        """Verify a single entry's hash."""
        with self._lock:
            for entry in self._entries:
                if entry.entry_id == entry_id:
                    return verify_entry_hash(entry)
            return False
    
    # ───────────────────────────────────────────────────────────────────────────
    # EXPORT
    # ───────────────────────────────────────────────────────────────────────────
    
    def export_json(self) -> str:
        """Export ledger as JSON (for compliance/audit)."""
        with self._lock:
            data = {
                "ledger_version": LEDGER_VERSION,
                "entry_count": len(self._entries),
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "entries": [e.to_dict() for e in self._entries],
            }
            return json.dumps(data, sort_keys=True, indent=2)
    
    def export_to_file(self, filepath: str) -> None:
        """Export ledger to file."""
        content = self.export_json()
        with open(filepath, "w") as f:
            f.write(content)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_default_ledger: Optional[PDOLedger] = None
_ledger_lock = threading.Lock()


def get_pdo_ledger() -> PDOLedger:
    """Get the default PDO ledger (singleton)."""
    global _default_ledger
    with _ledger_lock:
        if _default_ledger is None:
            _default_ledger = PDOLedger()
        return _default_ledger


def reset_pdo_ledger() -> None:
    """Reset the default PDO ledger (for testing)."""
    global _default_ledger
    with _ledger_lock:
        _default_ledger = None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Ledger
    "PDOLedger",
    "get_pdo_ledger",
    "reset_pdo_ledger",
    
    # Entry
    "LedgerEntry",
    
    # Exceptions
    "LedgerError",
    "LedgerMutationForbiddenError",
    "LedgerChainBrokenError",
    "LedgerOrderingError",
    
    # Constants
    "LEDGER_VERSION",
    "GENESIS_HASH",
    
    # Utilities
    "compute_entry_hash",
    "verify_entry_hash",
]
