# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Execution Ledger
# PAC-008: Agent Execution Visibility — ORDER 1 (Cody GID-01)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Execution ledger for persisting agent execution events.

Provides append-only storage for:
- Agent activation events
- Agent state change events
- Execution timeline reconstruction

GOVERNANCE INVARIANTS:
- INV-AGENT-001: Agent activation must be explicit and visible
- INV-AGENT-002: Each execution step maps to exactly one agent
- INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional

from core.execution.agent_events import (
    AgentActivationEvent,
    AgentExecutionStateEvent,
    AgentState,
    UNAVAILABLE_MARKER,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

GENESIS_HASH = "0" * 64
"""Genesis hash for the first entry in the ledger."""


# ═══════════════════════════════════════════════════════════════════════════════
# LEDGER ENTRY TYPE
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionEntryType(str, Enum):
    """Types of entries in the execution ledger."""
    
    AGENT_ACTIVATION = "AGENT_ACTIVATION"
    AGENT_STATE_CHANGE = "AGENT_STATE_CHANGE"
    PAC_START = "PAC_START"
    PAC_COMPLETE = "PAC_COMPLETE"
    BER_ISSUED = "BER_ISSUED"


# ═══════════════════════════════════════════════════════════════════════════════
# HASH COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════════

def compute_entry_hash(
    entry_id: str,
    sequence: int,
    entry_type: str,
    payload_json: str,
    previous_hash: str,
    timestamp: str,
) -> str:
    """
    Compute SHA-256 hash for ledger entry.
    
    Creates a deterministic hash from entry components to ensure
    chain integrity and tamper detection.
    """
    data = f"{entry_id}|{sequence}|{entry_type}|{payload_json}|{previous_hash}|{timestamp}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# LEDGER ENTRY
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionLedgerEntry:
    """
    Single entry in the execution ledger.
    
    Each entry is hash-chained to the previous entry for integrity.
    """
    
    # Identity
    entry_id: str
    sequence_number: int
    
    # Entry type and payload
    entry_type: ExecutionEntryType
    payload: Dict[str, Any]
    
    # Chain integrity
    entry_hash: str
    previous_hash: str
    
    # Context
    pac_id: str
    agent_gid: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result["entry_type"] = self.entry_type.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionLedgerEntry":
        """Create from dictionary."""
        data = data.copy()
        data["entry_type"] = ExecutionEntryType(data["entry_type"])
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION LEDGER
# ═══════════════════════════════════════════════════════════════════════════════

class ExecutionLedger:
    """
    Append-only, hash-chained ledger for agent execution events.
    
    Thread-safe implementation that maintains:
    - Append-only semantics (no updates, no deletes)
    - Hash chain integrity
    - PAC-scoped queries
    """
    
    def __init__(self):
        """Initialize empty ledger."""
        self._entries: List[ExecutionLedgerEntry] = []
        self._by_pac_id: Dict[str, List[ExecutionLedgerEntry]] = {}
        self._by_agent_gid: Dict[str, List[ExecutionLedgerEntry]] = {}
        self._lock = threading.Lock()
    
    # ───────────────────────────────────────────────────────────────────────────
    # APPEND OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def append(
        self,
        entry_type: ExecutionEntryType,
        payload: Dict[str, Any],
        pac_id: str,
        agent_gid: Optional[str] = None,
    ) -> ExecutionLedgerEntry:
        """
        Append a new entry to the ledger.
        
        This is the ONLY write operation permitted.
        
        Args:
            entry_type: Type of execution entry
            payload: Entry payload (event data)
            pac_id: PAC identifier
            agent_gid: Optional agent GID
        
        Returns:
            ExecutionLedgerEntry: The created entry
        """
        with self._lock:
            # Generate entry ID
            entry_id = f"exec_{uuid.uuid4().hex[:12]}"
            
            # Get sequence and previous hash
            sequence = len(self._entries)
            previous_hash = (
                self._entries[-1].entry_hash if self._entries else GENESIS_HASH
            )
            
            # Timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Serialize payload for hashing
            payload_json = json.dumps(payload, sort_keys=True, default=str)
            
            # Compute entry hash
            entry_hash = compute_entry_hash(
                entry_id,
                sequence,
                entry_type.value,
                payload_json,
                previous_hash,
                timestamp,
            )
            
            # Create entry
            entry = ExecutionLedgerEntry(
                entry_id=entry_id,
                sequence_number=sequence,
                entry_type=entry_type,
                payload=payload,
                entry_hash=entry_hash,
                previous_hash=previous_hash,
                pac_id=pac_id,
                agent_gid=agent_gid,
                timestamp=timestamp,
            )
            
            # Store entry
            self._entries.append(entry)
            
            # Index by PAC ID
            if pac_id not in self._by_pac_id:
                self._by_pac_id[pac_id] = []
            self._by_pac_id[pac_id].append(entry)
            
            # Index by agent GID
            if agent_gid:
                if agent_gid not in self._by_agent_gid:
                    self._by_agent_gid[agent_gid] = []
                self._by_agent_gid[agent_gid].append(entry)
            
            logger.debug(
                f"EXECUTION_LEDGER: Appended {entry_type.value} "
                f"[pac={pac_id}, agent={agent_gid}, seq={sequence}]"
            )
            
            return entry
    
    def append_activation(self, event: AgentActivationEvent) -> ExecutionLedgerEntry:
        """
        Append an agent activation event to the ledger.
        
        Args:
            event: AgentActivationEvent to persist
        
        Returns:
            ExecutionLedgerEntry: The created entry
        """
        return self.append(
            entry_type=ExecutionEntryType.AGENT_ACTIVATION,
            payload=event.to_dict(),
            pac_id=event.pac_id,
            agent_gid=event.agent_gid,
        )
    
    def append_state_change(self, event: AgentExecutionStateEvent) -> ExecutionLedgerEntry:
        """
        Append an agent state change event to the ledger.
        
        Args:
            event: AgentExecutionStateEvent to persist
        
        Returns:
            ExecutionLedgerEntry: The created entry
        """
        return self.append(
            entry_type=ExecutionEntryType.AGENT_STATE_CHANGE,
            payload=event.to_dict(),
            pac_id=event.pac_id,
            agent_gid=event.agent_gid,
        )
    
    # ───────────────────────────────────────────────────────────────────────────
    # FORBIDDEN OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def update(self, entry_id: str, **kwargs: Any) -> None:
        """UPDATE is forbidden. Ledger is append-only."""
        raise RuntimeError(
            f"UPDATE FORBIDDEN: Execution ledger is append-only. "
            f"Cannot update entry {entry_id}."
        )
    
    def delete(self, entry_id: str) -> None:
        """DELETE is forbidden. Ledger is append-only."""
        raise RuntimeError(
            f"DELETE FORBIDDEN: Execution ledger is append-only. "
            f"Cannot delete entry {entry_id}."
        )
    
    # ───────────────────────────────────────────────────────────────────────────
    # READ OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_by_pac_id(self, pac_id: str) -> List[ExecutionLedgerEntry]:
        """Get all entries for a PAC."""
        with self._lock:
            return self._by_pac_id.get(pac_id, []).copy()
    
    def get_by_agent_gid(self, agent_gid: str) -> List[ExecutionLedgerEntry]:
        """Get all entries for an agent."""
        with self._lock:
            return self._by_agent_gid.get(agent_gid, []).copy()
    
    def get_by_sequence(self, sequence: int) -> Optional[ExecutionLedgerEntry]:
        """Get entry by sequence number."""
        with self._lock:
            if 0 <= sequence < len(self._entries):
                return self._entries[sequence]
            return None
    
    def get_all(self) -> List[ExecutionLedgerEntry]:
        """Get all entries ordered by sequence."""
        with self._lock:
            return self._entries.copy()
    
    def get_latest(self) -> Optional[ExecutionLedgerEntry]:
        """Get the most recent entry."""
        with self._lock:
            return self._entries[-1] if self._entries else None
    
    def get_agent_timeline(
        self,
        pac_id: str,
        agent_gid: Optional[str] = None,
    ) -> List[ExecutionLedgerEntry]:
        """
        Get execution timeline for a PAC, optionally filtered by agent.
        
        Args:
            pac_id: PAC identifier
            agent_gid: Optional agent GID filter
        
        Returns:
            List of entries in chronological order
        """
        with self._lock:
            entries = self._by_pac_id.get(pac_id, [])
            
            if agent_gid:
                entries = [e for e in entries if e.agent_gid == agent_gid]
            
            return sorted(entries, key=lambda e: e.sequence_number)
    
    def get_pac_agents(self, pac_id: str) -> List[str]:
        """
        Get list of unique agent GIDs that participated in a PAC.
        
        Args:
            pac_id: PAC identifier
        
        Returns:
            List of unique agent GIDs
        """
        with self._lock:
            entries = self._by_pac_id.get(pac_id, [])
            gids = {e.agent_gid for e in entries if e.agent_gid}
            return sorted(gids)
    
    def __len__(self) -> int:
        """Return number of entries in ledger."""
        with self._lock:
            return len(self._entries)
    
    def __iter__(self) -> Iterator[ExecutionLedgerEntry]:
        """Iterate over entries in order."""
        with self._lock:
            entries = self._entries.copy()
        for entry in entries:
            yield entry
    
    # ───────────────────────────────────────────────────────────────────────────
    # CHAIN VERIFICATION
    # ───────────────────────────────────────────────────────────────────────────
    
    def verify_chain(self) -> tuple[bool, Optional[str]]:
        """
        Verify the hash chain integrity.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        with self._lock:
            if not self._entries:
                return True, None
            
            # Check genesis
            if self._entries[0].previous_hash != GENESIS_HASH:
                return False, "Genesis entry has incorrect previous hash"
            
            # Verify chain
            for i in range(1, len(self._entries)):
                prev_entry = self._entries[i - 1]
                curr_entry = self._entries[i]
                
                if curr_entry.previous_hash != prev_entry.entry_hash:
                    return False, (
                        f"Chain broken at sequence {i}: "
                        f"expected previous_hash {prev_entry.entry_hash}, "
                        f"got {curr_entry.previous_hash}"
                    )
            
            return True, None


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_EXECUTION_LEDGER: Optional[ExecutionLedger] = None
_LEDGER_LOCK = threading.Lock()


def get_execution_ledger() -> ExecutionLedger:
    """
    Get the singleton execution ledger instance.
    
    Returns:
        ExecutionLedger: The singleton instance
    """
    global _EXECUTION_LEDGER
    
    if _EXECUTION_LEDGER is None:
        with _LEDGER_LOCK:
            if _EXECUTION_LEDGER is None:
                _EXECUTION_LEDGER = ExecutionLedger()
                logger.info("Execution ledger initialized")
    
    return _EXECUTION_LEDGER


def reset_execution_ledger() -> None:
    """Reset the singleton ledger. Used for testing."""
    global _EXECUTION_LEDGER
    with _LEDGER_LOCK:
        _EXECUTION_LEDGER = None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "ExecutionEntryType",
    "ExecutionLedgerEntry",
    "ExecutionLedger",
    "get_execution_ledger",
    "reset_execution_ledger",
    "GENESIS_HASH",
]
