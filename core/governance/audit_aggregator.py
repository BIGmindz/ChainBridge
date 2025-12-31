"""
Audit Aggregation Service — Cross-Registry Chain Aggregation for Auditors
════════════════════════════════════════════════════════════════════════════════

PAC Reference: PAC-013A (CORRECTED · GOLD STANDARD)
Agent: Cindy (GID-04) — Audit Aggregation
Order: ORDER 2
Effective Date: 2025-12-30
Runtime: RUNTIME-013A
Execution Lane: SINGLE-LANE, ORDERED
Governance Mode: FAIL-CLOSED (LOCKED)

OBJECTIVE:
    Aggregate data from PDO, Decision, Outcome, and Settlement registries
    into unified audit views with complete chain linkage.

DEPENDENCIES:
    - ORDER 1 (Cody): audit_oc.py API types

HARD INVARIANTS (INV-AGG-*):
    INV-AGG-001: No data transformation that loses information
    INV-AGG-002: All aggregations include source registry references
    INV-AGG-003: Cross-registry joins explicit (no hidden joins)
    INV-AGG-004: Temporal ordering preserved
    INV-AGG-005: Missing data explicit (UNAVAILABLE marker)

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

UNAVAILABLE_MARKER = "UNAVAILABLE"
"""Marker for missing data (INV-AGG-005)."""


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class RegistryType(str, Enum):
    """Types of source registries."""
    PDO = "PDO"
    DECISION = "DECISION"
    OUTCOME = "OUTCOME"
    SETTLEMENT = "SETTLEMENT"
    PROOF = "PROOF"
    GOVERNANCE = "GOVERNANCE"


class AggregationStatus(str, Enum):
    """Status of an aggregation operation."""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    PENDING = "PENDING"


class ChainCompleteness(str, Enum):
    """Completeness level of an audit chain."""
    FULL = "FULL"  # All links present and verified
    PARTIAL = "PARTIAL"  # Some links missing
    MINIMAL = "MINIMAL"  # Only root present
    EMPTY = "EMPTY"  # No data


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES — REGISTRY REFERENCES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RegistryReference:
    """
    Reference to a source registry entry.
    
    INV-AGG-002: All aggregations include source registry references.
    """
    registry_type: RegistryType
    entry_id: str
    entry_hash: str
    timestamp: str
    sequence_number: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "registry_type": self.registry_type.value,
            "entry_id": self.entry_id,
            "entry_hash": self.entry_hash,
            "timestamp": self.timestamp,
            "sequence_number": self.sequence_number,
            "metadata": self.metadata
        }


@dataclass
class CrossRegistryJoin:
    """
    Explicit cross-registry join record.
    
    INV-AGG-003: Cross-registry joins explicit (no hidden joins).
    """
    join_id: str
    left_ref: RegistryReference
    right_ref: RegistryReference
    join_key: str
    join_timestamp: str
    join_type: str = "INNER"  # INNER, LEFT, RIGHT
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "join_id": self.join_id,
            "left_ref": self.left_ref.to_dict(),
            "right_ref": self.right_ref.to_dict(),
            "join_key": self.join_key,
            "join_timestamp": self.join_timestamp,
            "join_type": self.join_type
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES — AGGREGATED VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AuditChainAggregate:
    """
    Aggregated audit chain from multiple registries.
    
    INV-AGG-001: No data transformation that loses information.
    INV-AGG-004: Temporal ordering preserved.
    """
    chain_id: str
    completeness: ChainCompleteness
    
    # Source references (INV-AGG-002)
    pdo_ref: Optional[RegistryReference] = None
    proof_ref: Optional[RegistryReference] = None
    decision_ref: Optional[RegistryReference] = None
    outcome_ref: Optional[RegistryReference] = None
    settlement_ref: Optional[RegistryReference] = None
    
    # Cross-registry joins (INV-AGG-003)
    joins: List[CrossRegistryJoin] = field(default_factory=list)
    
    # Temporal data (INV-AGG-004)
    earliest_timestamp: str = ""
    latest_timestamp: str = ""
    temporal_order: List[str] = field(default_factory=list)  # Entry IDs in time order
    
    # Hashes
    aggregate_hash: str = ""
    
    # Metadata
    aggregation_timestamp: str = ""
    aggregation_status: AggregationStatus = AggregationStatus.PENDING
    
    def compute_aggregate_hash(self) -> str:
        """Compute hash of all references for integrity."""
        refs = []
        for ref in [self.pdo_ref, self.proof_ref, self.decision_ref, 
                    self.outcome_ref, self.settlement_ref]:
            if ref:
                refs.append(ref.entry_hash)
        
        combined = "|".join(refs)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chain_id": self.chain_id,
            "completeness": self.completeness.value,
            "pdo_ref": self.pdo_ref.to_dict() if self.pdo_ref else None,
            "proof_ref": self.proof_ref.to_dict() if self.proof_ref else None,
            "decision_ref": self.decision_ref.to_dict() if self.decision_ref else None,
            "outcome_ref": self.outcome_ref.to_dict() if self.outcome_ref else None,
            "settlement_ref": self.settlement_ref.to_dict() if self.settlement_ref else None,
            "joins": [j.to_dict() for j in self.joins],
            "earliest_timestamp": self.earliest_timestamp,
            "latest_timestamp": self.latest_timestamp,
            "temporal_order": self.temporal_order,
            "aggregate_hash": self.aggregate_hash,
            "aggregation_timestamp": self.aggregation_timestamp,
            "aggregation_status": self.aggregation_status.value
        }


@dataclass
class AggregationMetrics:
    """Metrics from aggregation operations."""
    total_chains: int = 0
    complete_chains: int = 0
    partial_chains: int = 0
    failed_aggregations: int = 0
    
    # Per-registry counts
    pdo_entries: int = 0
    decision_entries: int = 0
    outcome_entries: int = 0
    settlement_entries: int = 0
    proof_entries: int = 0
    
    # Join counts
    total_joins: int = 0
    
    # Computed
    completeness_rate: float = 0.0
    
    def compute_completeness_rate(self) -> float:
        """Compute chain completeness rate."""
        if self.total_chains == 0:
            return 0.0
        return self.complete_chains / self.total_chains
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_chains": self.total_chains,
            "complete_chains": self.complete_chains,
            "partial_chains": self.partial_chains,
            "failed_aggregations": self.failed_aggregations,
            "pdo_entries": self.pdo_entries,
            "decision_entries": self.decision_entries,
            "outcome_entries": self.outcome_entries,
            "settlement_entries": self.settlement_entries,
            "proof_entries": self.proof_entries,
            "total_joins": self.total_joins,
            "completeness_rate": self.compute_completeness_rate()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT AGGREGATOR (THREAD-SAFE SINGLETON)
# ═══════════════════════════════════════════════════════════════════════════════

class AuditAggregator:
    """
    Aggregates data across registries for audit chain reconstruction.
    
    Thread-safe singleton pattern per ChainBridge conventions.
    """
    
    _instance: Optional["AuditAggregator"] = None
    _lock: Lock = Lock()
    
    def __new__(cls) -> "AuditAggregator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._aggregates: Dict[str, AuditChainAggregate] = {}
        self._joins: List[CrossRegistryJoin] = []
        self._metrics = AggregationMetrics()
        self._init_timestamp = self._now_iso()
        self._initialized = True
        
        logger.info("[AUDIT-AGG] AuditAggregator initialized")
    
    @staticmethod
    def _now_iso() -> str:
        """Current UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()
    
    @staticmethod
    def _compute_hash(content: Any) -> str:
        """Compute SHA-256 hash."""
        if isinstance(content, str):
            data = content.encode("utf-8")
        else:
            data = json.dumps(content, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(data).hexdigest()
    
    def _generate_join_id(self) -> str:
        """Generate unique join identifier."""
        import uuid
        return f"JOIN-{uuid.uuid4().hex[:12].upper()}"
    
    # ───────────────────────────────────────────────────────────────────────────
    # AGGREGATION OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def aggregate_chain(
        self,
        chain_id: str,
        pdo_data: Optional[Dict[str, Any]] = None,
        proof_data: Optional[Dict[str, Any]] = None,
        decision_data: Optional[Dict[str, Any]] = None,
        outcome_data: Optional[Dict[str, Any]] = None,
        settlement_data: Optional[Dict[str, Any]] = None
    ) -> AuditChainAggregate:
        """
        Aggregate data from multiple registries into a single audit chain.
        
        INV-AGG-001: No data transformation that loses information.
        INV-AGG-002: All aggregations include source registry references.
        INV-AGG-003: Cross-registry joins explicit.
        INV-AGG-004: Temporal ordering preserved.
        INV-AGG-005: Missing data explicit.
        """
        now = self._now_iso()
        
        # Create aggregate
        aggregate = AuditChainAggregate(
            chain_id=chain_id,
            completeness=ChainCompleteness.EMPTY,
            aggregation_timestamp=now,
            aggregation_status=AggregationStatus.PENDING
        )
        
        timestamps: List[Tuple[str, str]] = []  # (timestamp, entry_id)
        
        # Process PDO reference
        if pdo_data:
            ref = self._create_reference(RegistryType.PDO, pdo_data)
            aggregate.pdo_ref = ref
            timestamps.append((ref.timestamp, ref.entry_id))
            self._metrics.pdo_entries += 1
        
        # Process Proof reference
        if proof_data:
            ref = self._create_reference(RegistryType.PROOF, proof_data)
            aggregate.proof_ref = ref
            timestamps.append((ref.timestamp, ref.entry_id))
            self._metrics.proof_entries += 1
            
            # Create explicit join if PDO exists
            if aggregate.pdo_ref:
                join = self._create_join(aggregate.pdo_ref, ref, "pdo_id")
                aggregate.joins.append(join)
                self._joins.append(join)
                self._metrics.total_joins += 1
        
        # Process Decision reference
        if decision_data:
            ref = self._create_reference(RegistryType.DECISION, decision_data)
            aggregate.decision_ref = ref
            timestamps.append((ref.timestamp, ref.entry_id))
            self._metrics.decision_entries += 1
            
            # Create explicit join if Proof exists
            if aggregate.proof_ref:
                join = self._create_join(aggregate.proof_ref, ref, "proof_id")
                aggregate.joins.append(join)
                self._joins.append(join)
                self._metrics.total_joins += 1
        
        # Process Outcome reference
        if outcome_data:
            ref = self._create_reference(RegistryType.OUTCOME, outcome_data)
            aggregate.outcome_ref = ref
            timestamps.append((ref.timestamp, ref.entry_id))
            self._metrics.outcome_entries += 1
            
            # Create explicit join if Decision exists
            if aggregate.decision_ref:
                join = self._create_join(aggregate.decision_ref, ref, "decision_id")
                aggregate.joins.append(join)
                self._joins.append(join)
                self._metrics.total_joins += 1
        
        # Process Settlement reference (optional)
        if settlement_data:
            ref = self._create_reference(RegistryType.SETTLEMENT, settlement_data)
            aggregate.settlement_ref = ref
            timestamps.append((ref.timestamp, ref.entry_id))
            self._metrics.settlement_entries += 1
            
            # Create explicit join if Outcome exists
            if aggregate.outcome_ref:
                join = self._create_join(aggregate.outcome_ref, ref, "outcome_id")
                aggregate.joins.append(join)
                self._joins.append(join)
                self._metrics.total_joins += 1
        
        # Compute temporal ordering (INV-AGG-004)
        timestamps.sort(key=lambda x: x[0])
        if timestamps:
            aggregate.earliest_timestamp = timestamps[0][0]
            aggregate.latest_timestamp = timestamps[-1][0]
            aggregate.temporal_order = [t[1] for t in timestamps]
        
        # Determine completeness
        aggregate.completeness = self._determine_completeness(aggregate)
        
        # Compute aggregate hash
        aggregate.aggregate_hash = aggregate.compute_aggregate_hash()
        
        # Update status
        aggregate.aggregation_status = AggregationStatus.COMPLETE
        
        # Store aggregate
        with self._lock:
            self._aggregates[chain_id] = aggregate
            self._metrics.total_chains += 1
            if aggregate.completeness == ChainCompleteness.FULL:
                self._metrics.complete_chains += 1
            elif aggregate.completeness in [ChainCompleteness.PARTIAL, ChainCompleteness.MINIMAL]:
                self._metrics.partial_chains += 1
        
        logger.info(f"[AUDIT-AGG] Aggregated chain {chain_id}: {aggregate.completeness.value}")
        return aggregate
    
    def _create_reference(
        self,
        registry_type: RegistryType,
        data: Dict[str, Any]
    ) -> RegistryReference:
        """Create a registry reference from data."""
        entry_id = data.get("id", data.get("entry_id", UNAVAILABLE_MARKER))
        timestamp = data.get("timestamp", self._now_iso())
        seq = data.get("sequence_number", data.get("seq", 0))
        
        return RegistryReference(
            registry_type=registry_type,
            entry_id=entry_id,
            entry_hash=self._compute_hash(data),
            timestamp=timestamp,
            sequence_number=seq,
            metadata=data
        )
    
    def _create_join(
        self,
        left_ref: RegistryReference,
        right_ref: RegistryReference,
        join_key: str
    ) -> CrossRegistryJoin:
        """Create an explicit cross-registry join record."""
        return CrossRegistryJoin(
            join_id=self._generate_join_id(),
            left_ref=left_ref,
            right_ref=right_ref,
            join_key=join_key,
            join_timestamp=self._now_iso(),
            join_type="INNER"
        )
    
    def _determine_completeness(self, aggregate: AuditChainAggregate) -> ChainCompleteness:
        """Determine chain completeness level."""
        refs_present = sum([
            1 if aggregate.pdo_ref else 0,
            1 if aggregate.proof_ref else 0,
            1 if aggregate.decision_ref else 0,
            1 if aggregate.outcome_ref else 0
        ])
        
        if refs_present == 4:
            return ChainCompleteness.FULL
        elif refs_present >= 2:
            return ChainCompleteness.PARTIAL
        elif refs_present == 1:
            return ChainCompleteness.MINIMAL
        else:
            return ChainCompleteness.EMPTY
    
    # ───────────────────────────────────────────────────────────────────────────
    # QUERY OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_aggregate(self, chain_id: str) -> Optional[AuditChainAggregate]:
        """Get an aggregated chain by ID."""
        return self._aggregates.get(chain_id)
    
    def get_all_aggregates(self) -> List[AuditChainAggregate]:
        """Get all aggregated chains."""
        return list(self._aggregates.values())
    
    def get_complete_chains(self) -> List[AuditChainAggregate]:
        """Get only fully complete chains."""
        return [a for a in self._aggregates.values() 
                if a.completeness == ChainCompleteness.FULL]
    
    def get_partial_chains(self) -> List[AuditChainAggregate]:
        """Get chains with partial data."""
        return [a for a in self._aggregates.values() 
                if a.completeness in [ChainCompleteness.PARTIAL, ChainCompleteness.MINIMAL]]
    
    def get_joins(self) -> List[CrossRegistryJoin]:
        """Get all explicit joins."""
        return self._joins.copy()
    
    def get_metrics(self) -> AggregationMetrics:
        """Get aggregation metrics."""
        self._metrics.completeness_rate = self._metrics.compute_completeness_rate()
        return self._metrics
    
    def get_chains_by_timerange(
        self,
        start: str,
        end: str
    ) -> List[AuditChainAggregate]:
        """Get chains within a time range (INV-AGG-004)."""
        result = []
        for aggregate in self._aggregates.values():
            if aggregate.earliest_timestamp >= start and aggregate.latest_timestamp <= end:
                result.append(aggregate)
        return result
    
    # ───────────────────────────────────────────────────────────────────────────
    # RESET (for testing)
    # ───────────────────────────────────────────────────────────────────────────
    
    @classmethod
    def reset(cls) -> None:
        """Reset singleton for testing."""
        with cls._lock:
            if cls._instance:
                cls._instance._aggregates.clear()
                cls._instance._joins.clear()
                cls._instance._metrics = AggregationMetrics()
            cls._instance = None


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL ACCESSORS
# ═══════════════════════════════════════════════════════════════════════════════

_aggregator: Optional[AuditAggregator] = None


def get_audit_aggregator() -> AuditAggregator:
    """Get the singleton AuditAggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = AuditAggregator()
    return _aggregator


def reset_audit_aggregator() -> None:
    """Reset the singleton for testing."""
    global _aggregator
    AuditAggregator.reset()
    _aggregator = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def aggregate_audit_chain(
    chain_id: str,
    pdo_data: Optional[Dict[str, Any]] = None,
    proof_data: Optional[Dict[str, Any]] = None,
    decision_data: Optional[Dict[str, Any]] = None,
    outcome_data: Optional[Dict[str, Any]] = None,
    settlement_data: Optional[Dict[str, Any]] = None
) -> AuditChainAggregate:
    """
    Aggregate an audit chain from registry data.
    
    Convenience function wrapping AuditAggregator.aggregate_chain().
    """
    return get_audit_aggregator().aggregate_chain(
        chain_id=chain_id,
        pdo_data=pdo_data,
        proof_data=proof_data,
        decision_data=decision_data,
        outcome_data=outcome_data,
        settlement_data=settlement_data
    )


def get_aggregation_metrics() -> Dict[str, Any]:
    """Get aggregation metrics as dictionary."""
    return get_audit_aggregator().get_metrics().to_dict()


def list_all_joins() -> List[Dict[str, Any]]:
    """List all explicit cross-registry joins."""
    return [j.to_dict() for j in get_audit_aggregator().get_joins()]
