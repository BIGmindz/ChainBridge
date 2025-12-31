"""
PDO Index

Hash-based indexing for proof-addressed PDO retrieval.
Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-PROOF-LAYER-024.

Agent: GID-07 (Dan) — DevOps/Systems Engineer

Implements:
- Proof-first lookup (INV-STORE-002)
- Secondary indices for PDO hash, agent, PAC
- Fast O(1) retrieval by hash
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from core.gie.storage.pdo_store import PDORecord, PDOStore, get_pdo_store


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class IndexType(Enum):
    """Types of indices."""
    PROOF_HASH = "PROOF_HASH"  # Primary
    PDO_HASH = "PDO_HASH"      # Content hash
    PDO_ID = "PDO_ID"          # Human-readable ID
    AGENT_GID = "AGENT_GID"    # By creating agent
    PAC_ID = "PAC_ID"          # By source PAC
    ARTIFACT = "ARTIFACT"      # By artifact hash


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class IndexEntry:
    """
    Index entry mapping a hash to PDO record.
    """
    hash_value: str
    index_type: IndexType
    proof_hash: str  # Points to PDORecord via proof_hash (primary key)
    created_at: str


@dataclass
class IndexStatistics:
    """Statistics about index state."""
    total_entries: int
    index_counts: Dict[str, int]
    last_updated: str


# ═══════════════════════════════════════════════════════════════════════════════
# PDO INDEX
# ═══════════════════════════════════════════════════════════════════════════════

class PDOIndex:
    """
    Hash-based index for fast PDO retrieval.
    
    Provides multiple access patterns while maintaining
    proof-first addressing (INV-STORE-002).
    
    Index Types:
    - PROOF_HASH: Primary (1:1 mapping to PDORecord)
    - PDO_HASH: Content hash (may be 1:N if re-proven)
    - PDO_ID: Human ID (should be 1:1)
    - AGENT_GID: By agent (1:N)
    - PAC_ID: By PAC (1:N)
    - ARTIFACT: By artifact hash (N:M)
    """

    def __init__(self, store: Optional[PDOStore] = None):
        """
        Initialize PDO index.
        
        Args:
            store: PDOStore to index (uses global if not provided)
        """
        self._store = store or get_pdo_store()
        self._lock = threading.RLock()
        
        # Index structures: index_type → value → set of proof_hashes
        self._indices: Dict[IndexType, Dict[str, Set[str]]] = {
            index_type: {} for index_type in IndexType
        }
        
        # Track all indexed proof_hashes
        self._indexed: Set[str] = set()

    # ─────────────────────────────────────────────────────────────────────────
    # Indexing Operations
    # ─────────────────────────────────────────────────────────────────────────

    def index_record(self, record: PDORecord) -> None:
        """
        Add a PDORecord to all relevant indices.
        """
        with self._lock:
            proof_hash = record.proof_hash
            
            if proof_hash in self._indexed:
                return  # Already indexed
            
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            # Primary: PROOF_HASH (1:1)
            self._add_to_index(IndexType.PROOF_HASH, proof_hash, proof_hash)
            
            # Secondary: PDO_HASH
            self._add_to_index(IndexType.PDO_HASH, record.pdo_hash, proof_hash)
            
            # Secondary: PDO_ID
            self._add_to_index(IndexType.PDO_ID, record.pdo_id, proof_hash)
            
            # Secondary: AGENT_GID
            self._add_to_index(IndexType.AGENT_GID, record.agent_gid, proof_hash)
            
            # Secondary: PAC_ID
            self._add_to_index(IndexType.PAC_ID, record.pac_id, proof_hash)
            
            # Secondary: ARTIFACT (for each artifact)
            for artifact_hash in record.artifact_hashes:
                self._add_to_index(IndexType.ARTIFACT, artifact_hash, proof_hash)
            
            self._indexed.add(proof_hash)

    def _add_to_index(
        self,
        index_type: IndexType,
        key: str,
        proof_hash: str,
    ) -> None:
        """Add entry to specific index."""
        if key not in self._indices[index_type]:
            self._indices[index_type][key] = set()
        self._indices[index_type][key].add(proof_hash)

    def reindex_all(self) -> int:
        """
        Rebuild all indices from store.
        
        Returns number of records indexed.
        """
        with self._lock:
            # Clear existing indices
            self._indices = {index_type: {} for index_type in IndexType}
            self._indexed.clear()
            
            # Index all records
            count = 0
            for proof_hash in self._store.list_all_proof_hashes():
                record = self._store.get_by_proof_hash(proof_hash)
                if record:
                    self.index_record(record)
                    count += 1
            
            return count

    # ─────────────────────────────────────────────────────────────────────────
    # Lookup Operations
    # ─────────────────────────────────────────────────────────────────────────

    def lookup_by_proof_hash(self, proof_hash: str) -> Optional[PDORecord]:
        """
        Primary lookup by proof hash.
        
        Per INV-STORE-002: This is the canonical retrieval path.
        """
        return self._store.get_by_proof_hash(proof_hash)

    def lookup_by_pdo_hash(self, pdo_hash: str) -> List[PDORecord]:
        """
        Lookup by content hash.
        
        May return multiple records if same content was proven multiple times.
        """
        with self._lock:
            proof_hashes = self._indices[IndexType.PDO_HASH].get(pdo_hash, set())
            
            records = []
            for proof_hash in proof_hashes:
                record = self._store.get_by_proof_hash(proof_hash)
                if record:
                    records.append(record)
            
            return records

    def lookup_by_pdo_id(self, pdo_id: str) -> Optional[PDORecord]:
        """
        Lookup by human-readable PDO ID.
        
        Returns first match (should be unique).
        """
        with self._lock:
            proof_hashes = self._indices[IndexType.PDO_ID].get(pdo_id, set())
            
            for proof_hash in proof_hashes:
                record = self._store.get_by_proof_hash(proof_hash)
                if record:
                    return record
            
            return None

    def lookup_by_agent(self, agent_gid: str) -> List[PDORecord]:
        """Lookup all PDOs created by an agent."""
        with self._lock:
            proof_hashes = self._indices[IndexType.AGENT_GID].get(agent_gid, set())
            
            records = []
            for proof_hash in proof_hashes:
                record = self._store.get_by_proof_hash(proof_hash)
                if record:
                    records.append(record)
            
            return records

    def lookup_by_pac(self, pac_id: str) -> List[PDORecord]:
        """Lookup all PDOs from a PAC."""
        with self._lock:
            proof_hashes = self._indices[IndexType.PAC_ID].get(pac_id, set())
            
            records = []
            for proof_hash in proof_hashes:
                record = self._store.get_by_proof_hash(proof_hash)
                if record:
                    records.append(record)
            
            return records

    def lookup_by_artifact(self, artifact_hash: str) -> List[PDORecord]:
        """Lookup all PDOs containing a specific artifact."""
        with self._lock:
            proof_hashes = self._indices[IndexType.ARTIFACT].get(artifact_hash, set())
            
            records = []
            for proof_hash in proof_hashes:
                record = self._store.get_by_proof_hash(proof_hash)
                if record:
                    records.append(record)
            
            return records

    # ─────────────────────────────────────────────────────────────────────────
    # Query Operations
    # ─────────────────────────────────────────────────────────────────────────

    def query(
        self,
        agent_gid: Optional[str] = None,
        pac_id: Optional[str] = None,
        proof_class: Optional[str] = None,
        limit: int = 100,
    ) -> List[PDORecord]:
        """
        Query PDOs with optional filters.
        
        Args:
            agent_gid: Filter by agent
            pac_id: Filter by PAC
            proof_class: Filter by proof class
            limit: Maximum results
        
        Returns:
            List of matching PDORecords
        """
        with self._lock:
            # Start with all indexed proof_hashes
            candidates = set(self._indexed)
            
            # Apply agent filter
            if agent_gid:
                agent_matches = self._indices[IndexType.AGENT_GID].get(agent_gid, set())
                candidates &= agent_matches
            
            # Apply PAC filter
            if pac_id:
                pac_matches = self._indices[IndexType.PAC_ID].get(pac_id, set())
                candidates &= pac_matches
            
            # Retrieve and filter records
            results = []
            for proof_hash in candidates:
                if len(results) >= limit:
                    break
                
                record = self._store.get_by_proof_hash(proof_hash)
                if record:
                    # Apply proof_class filter
                    if proof_class and record.proof_class != proof_class:
                        continue
                    results.append(record)
            
            return results

    # ─────────────────────────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────────────────────────

    def get_statistics(self) -> IndexStatistics:
        """Get index statistics."""
        with self._lock:
            index_counts = {}
            for index_type in IndexType:
                index_counts[index_type.value] = len(self._indices[index_type])
            
            return IndexStatistics(
                total_entries=len(self._indexed),
                index_counts=index_counts,
                last_updated=datetime.utcnow().isoformat() + "Z",
            )

    def count_by_agent(self) -> Dict[str, int]:
        """Get PDO count per agent."""
        with self._lock:
            return {
                agent: len(proof_hashes)
                for agent, proof_hashes in self._indices[IndexType.AGENT_GID].items()
            }

    def count_by_pac(self) -> Dict[str, int]:
        """Get PDO count per PAC."""
        with self._lock:
            return {
                pac: len(proof_hashes)
                for pac, proof_hashes in self._indices[IndexType.PAC_ID].items()
            }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

_global_index: Optional[PDOIndex] = None
_global_lock = threading.Lock()


def get_pdo_index(store: Optional[PDOStore] = None) -> PDOIndex:
    """Get or create global PDO index."""
    global _global_index
    
    with _global_lock:
        if _global_index is None:
            _global_index = PDOIndex(store=store)
        return _global_index


def reset_pdo_index() -> None:
    """Reset global index (for testing)."""
    global _global_index
    
    with _global_lock:
        _global_index = None
