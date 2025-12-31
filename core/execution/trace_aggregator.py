# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Trace Graph Aggregator
# PAC-009: Full End-to-End Traceability — ORDER 3 (Cindy GID-04)
# ═══════════════════════════════════════════════════════════════════════════════

"""
End-to-end trace graph aggregation for Operator Console visibility.

Provides:
- OC_TRACE_VIEW DTO for full trace chain rendering
- TRACE_GRAPH aggregation across PDO → Agent → Settlement → Ledger
- Visual gap indicators for missing trace links

GOVERNANCE INVARIANTS:
- INV-TRACE-003: Ledger hash links all phases (decision → execution → settlement)
- INV-TRACE-004: OC renders full chain without inference
- INV-TRACE-005: Missing links are explicit and non-silent
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from core.execution.trace_registry import (
    TraceDomain,
    TraceLink,
    TraceLinkType,
    TraceRegistry,
    get_trace_registry,
    UNAVAILABLE_MARKER,
)
from core.execution.decision_rationale import (
    DecisionRationale,
    DecisionFactor,
    RationaleRegistry,
    get_rationale_registry,
)
from core.execution.execution_ledger import (
    ExecutionLedger,
    ExecutionLedgerEntry,
    get_execution_ledger,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

TRACE_AGGREGATOR_VERSION = "1.0.0"
"""Trace aggregator version."""


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE NODE STATUS
# ═══════════════════════════════════════════════════════════════════════════════

class TraceNodeStatus(str, Enum):
    """Status of a trace graph node."""
    PRESENT = "PRESENT"         # Node data is available
    MISSING = "MISSING"         # Node is expected but missing (INV-TRACE-005)
    PARTIAL = "PARTIAL"         # Node has incomplete data
    ERROR = "ERROR"             # Error retrieving node data


class TraceViewStatus(str, Enum):
    """Overall status of trace view."""
    COMPLETE = "COMPLETE"       # Full trace chain available
    INCOMPLETE = "INCOMPLETE"   # Some nodes missing
    ERROR = "ERROR"             # Error during aggregation


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE NODE DTOs
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TraceDecisionNode:
    """
    Decision phase node in trace graph.
    
    Contains PDO creation decision and rationale.
    """
    node_id: str
    domain: str = TraceDomain.DECISION.value
    status: TraceNodeStatus = TraceNodeStatus.PRESENT
    
    # Decision data
    pdo_id: str = UNAVAILABLE_MARKER
    decision_id: str = UNAVAILABLE_MARKER
    
    # Rationale (ORDER 2 integration)
    rationale_id: Optional[str] = None
    summary: str = UNAVAILABLE_MARKER
    confidence_score: float = 0.0
    factor_count: int = 0
    top_factors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timing
    timestamp: str = UNAVAILABLE_MARKER
    
    # Trace linkage
    trace_hash: str = UNAVAILABLE_MARKER
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "node_id": self.node_id,
            "domain": self.domain,
            "status": self.status.value,
            "pdo_id": self.pdo_id,
            "decision_id": self.decision_id,
            "rationale_id": self.rationale_id,
            "summary": self.summary,
            "confidence_score": self.confidence_score,
            "factor_count": self.factor_count,
            "top_factors": self.top_factors,
            "timestamp": self.timestamp,
            "trace_hash": self.trace_hash,
        }


@dataclass
class TraceExecutionNode:
    """
    Execution phase node in trace graph.
    
    Contains agent execution data.
    """
    node_id: str
    domain: str = TraceDomain.EXECUTION.value
    status: TraceNodeStatus = TraceNodeStatus.PRESENT
    
    # Execution data
    execution_id: str = UNAVAILABLE_MARKER
    pac_id: str = UNAVAILABLE_MARKER
    
    # Agent data
    agent_gid: Optional[str] = None
    agent_name: str = UNAVAILABLE_MARKER
    agent_state: str = UNAVAILABLE_MARKER
    
    # Timing
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    
    # Trace linkage
    trace_hash: str = UNAVAILABLE_MARKER
    ledger_entry_hash: str = UNAVAILABLE_MARKER
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "node_id": self.node_id,
            "domain": self.domain,
            "status": self.status.value,
            "execution_id": self.execution_id,
            "pac_id": self.pac_id,
            "agent_gid": self.agent_gid,
            "agent_name": self.agent_name,
            "agent_state": self.agent_state,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "trace_hash": self.trace_hash,
            "ledger_entry_hash": self.ledger_entry_hash,
        }


@dataclass
class TraceSettlementNode:
    """
    Settlement phase node in trace graph.
    
    Contains outcome/settlement data.
    """
    node_id: str
    domain: str = TraceDomain.SETTLEMENT.value
    status: TraceNodeStatus = TraceNodeStatus.PRESENT
    
    # Settlement data
    settlement_id: str = UNAVAILABLE_MARKER
    outcome_id: Optional[str] = None
    outcome_status: str = UNAVAILABLE_MARKER
    
    # Context
    pdo_id: str = UNAVAILABLE_MARKER
    pac_id: str = UNAVAILABLE_MARKER
    
    # Timing
    settled_at: Optional[str] = None
    
    # Trace linkage
    trace_hash: str = UNAVAILABLE_MARKER
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "node_id": self.node_id,
            "domain": self.domain,
            "status": self.status.value,
            "settlement_id": self.settlement_id,
            "outcome_id": self.outcome_id,
            "outcome_status": self.outcome_status,
            "pdo_id": self.pdo_id,
            "pac_id": self.pac_id,
            "settled_at": self.settled_at,
            "trace_hash": self.trace_hash,
        }


@dataclass
class TraceLedgerNode:
    """
    Ledger phase node in trace graph.
    
    Contains ledger persistence reference.
    """
    node_id: str
    domain: str = TraceDomain.LEDGER.value
    status: TraceNodeStatus = TraceNodeStatus.PRESENT
    
    # Ledger data
    ledger_entry_id: str = UNAVAILABLE_MARKER
    sequence_number: int = -1
    entry_type: str = UNAVAILABLE_MARKER
    
    # Chain integrity
    entry_hash: str = UNAVAILABLE_MARKER
    previous_hash: str = UNAVAILABLE_MARKER
    
    # Context
    pac_id: str = UNAVAILABLE_MARKER
    
    # Timing
    timestamp: str = UNAVAILABLE_MARKER
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "node_id": self.node_id,
            "domain": self.domain,
            "status": self.status.value,
            "ledger_entry_id": self.ledger_entry_id,
            "sequence_number": self.sequence_number,
            "entry_type": self.entry_type,
            "entry_hash": self.entry_hash,
            "previous_hash": self.previous_hash,
            "pac_id": self.pac_id,
            "timestamp": self.timestamp,
        }


@dataclass
class TraceGap:
    """
    Representation of a missing trace link.
    
    INV-TRACE-005: Missing links are explicit and non-silent.
    """
    gap_id: str
    gap_type: str  # DOMAIN_NOT_LINKED, LINK_MISSING, DATA_UNAVAILABLE
    from_domain: Optional[str] = None
    to_domain: Optional[str] = None
    missing_entity_id: Optional[str] = None
    message: str = UNAVAILABLE_MARKER
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "gap_id": self.gap_id,
            "gap_type": self.gap_type,
            "from_domain": self.from_domain,
            "to_domain": self.to_domain,
            "missing_entity_id": self.missing_entity_id,
            "message": self.message,
            "timestamp": self.timestamp,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# OC_TRACE_VIEW DTO — Section 8 Contract
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OCTraceView:
    """
    Operator Console view of full end-to-end trace.
    
    This DTO provides a complete view of the trace chain from
    PDO → Agent → Settlement → Ledger for operator visibility.
    
    INV-TRACE-004: OC renders full chain without inference.
    """
    
    # Identity
    pdo_id: str
    pac_id: str = UNAVAILABLE_MARKER
    
    # Trace nodes by domain
    decision_nodes: List[TraceDecisionNode] = field(default_factory=list)
    execution_nodes: List[TraceExecutionNode] = field(default_factory=list)
    settlement_nodes: List[TraceSettlementNode] = field(default_factory=list)
    ledger_nodes: List[TraceLedgerNode] = field(default_factory=list)
    
    # Trace links
    trace_links: List[Dict[str, Any]] = field(default_factory=list)
    
    # Gaps (INV-TRACE-005)
    gaps: List[TraceGap] = field(default_factory=list)
    
    # Status
    status: TraceViewStatus = TraceViewStatus.COMPLETE
    completeness_score: float = 1.0  # 0.0 - 1.0
    
    # Metadata
    aggregated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    aggregator_version: str = TRACE_AGGREGATOR_VERSION
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "pdo_id": self.pdo_id,
            "pac_id": self.pac_id,
            "decision_nodes": [n.to_dict() for n in self.decision_nodes],
            "execution_nodes": [n.to_dict() for n in self.execution_nodes],
            "settlement_nodes": [n.to_dict() for n in self.settlement_nodes],
            "ledger_nodes": [n.to_dict() for n in self.ledger_nodes],
            "trace_links": self.trace_links,
            "gaps": [g.to_dict() for g in self.gaps],
            "status": self.status.value,
            "completeness_score": self.completeness_score,
            "aggregated_at": self.aggregated_at,
            "aggregator_version": self.aggregator_version,
        }
    
    @property
    def total_nodes(self) -> int:
        """Total number of trace nodes."""
        return (
            len(self.decision_nodes) +
            len(self.execution_nodes) +
            len(self.settlement_nodes) +
            len(self.ledger_nodes)
        )
    
    @property
    def has_gaps(self) -> bool:
        """Check if trace has any gaps."""
        return len(self.gaps) > 0


@dataclass
class OCTraceTimeline:
    """
    Timeline view of trace events for OC visualization.
    
    Events ordered chronologically for timeline rendering.
    """
    pdo_id: str
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "pdo_id": self.pdo_id,
            "events": self.events,
            "event_count": len(self.events),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE GRAPH AGGREGATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TraceGraphAggregator:
    """
    Aggregates trace data from multiple sources into OC_TRACE_VIEW.
    
    Thread-safe, read-only aggregation from:
    - TraceRegistry (trace links)
    - RationaleRegistry (decision rationale)
    - ExecutionLedger (ledger entries)
    """
    
    def __init__(
        self,
        trace_registry: Optional[TraceRegistry] = None,
        rationale_registry: Optional[RationaleRegistry] = None,
        execution_ledger: Optional[ExecutionLedger] = None,
    ):
        """
        Initialize aggregator with data sources.
        
        Args:
            trace_registry: TraceRegistry instance (defaults to singleton)
            rationale_registry: RationaleRegistry instance (defaults to singleton)
            execution_ledger: ExecutionLedger instance (defaults to singleton)
        """
        self._trace_registry = trace_registry or get_trace_registry()
        self._rationale_registry = rationale_registry or get_rationale_registry()
        self._execution_ledger = execution_ledger or get_execution_ledger()
    
    def aggregate_trace_view(self, pdo_id: str) -> OCTraceView:
        """
        Aggregate full trace view for a PDO.
        
        INV-TRACE-004: OC renders full chain without inference.
        
        Args:
            pdo_id: PDO identifier
        
        Returns:
            OCTraceView: Complete trace view
        """
        view = OCTraceView(pdo_id=pdo_id)
        
        # Get trace links for PDO
        trace_links = self._trace_registry.get_by_pdo_id(pdo_id)
        view.trace_links = [link.to_dict() for link in trace_links]
        
        # Extract PAC ID from links
        for link in trace_links:
            if link.pac_id and link.pac_id != UNAVAILABLE_MARKER:
                view.pac_id = link.pac_id
                break
        
        # Build decision nodes from rationale
        view.decision_nodes = self._build_decision_nodes(pdo_id, trace_links)
        
        # Build execution nodes from trace links
        view.execution_nodes = self._build_execution_nodes(pdo_id, trace_links)
        
        # Build settlement nodes from trace links
        view.settlement_nodes = self._build_settlement_nodes(pdo_id, trace_links)
        
        # Build ledger nodes from execution ledger
        view.ledger_nodes = self._build_ledger_nodes(pdo_id, trace_links)
        
        # Identify gaps (INV-TRACE-005)
        view.gaps = self._identify_gaps(pdo_id, view)
        
        # Calculate status and completeness
        view.status, view.completeness_score = self._calculate_status(view)
        
        logger.debug(
            f"TRACE_AGGREGATOR: Built trace view for PDO {pdo_id} "
            f"[nodes={view.total_nodes}, gaps={len(view.gaps)}, "
            f"completeness={view.completeness_score:.2f}]"
        )
        
        return view
    
    def _build_decision_nodes(
        self,
        pdo_id: str,
        trace_links: List[TraceLink],
    ) -> List[TraceDecisionNode]:
        """Build decision phase nodes."""
        nodes: List[TraceDecisionNode] = []
        
        # Get rationales for PDO
        rationales = self._rationale_registry.get_by_pdo_id(pdo_id)
        
        for rationale in rationales:
            # Get top factors (max 3)
            top_factors = [
                f.to_dict() for f in sorted(
                    rationale.factors,
                    key=lambda x: x.weight * x.confidence,
                    reverse=True,
                )[:3]
            ]
            
            # Find trace hash for this decision
            trace_hash = UNAVAILABLE_MARKER
            for link in trace_links:
                if (link.target_domain == TraceDomain.DECISION and
                    link.target_id == rationale.decision_id):
                    trace_hash = link.trace_hash
                    break
            
            node = TraceDecisionNode(
                node_id=f"decision_{rationale.decision_id}",
                pdo_id=pdo_id,
                decision_id=rationale.decision_id,
                rationale_id=rationale.rationale_id,
                summary=rationale.summary,
                confidence_score=rationale.confidence_score,
                factor_count=len(rationale.factors),
                top_factors=top_factors,
                timestamp=rationale.timestamp,
                trace_hash=trace_hash,
            )
            nodes.append(node)
        
        # If no rationales found, create placeholder with MISSING status
        if not nodes:
            node = TraceDecisionNode(
                node_id=f"decision_{pdo_id}_missing",
                status=TraceNodeStatus.MISSING,
                pdo_id=pdo_id,
            )
            nodes.append(node)
        
        return nodes
    
    def _build_execution_nodes(
        self,
        pdo_id: str,
        trace_links: List[TraceLink],
    ) -> List[TraceExecutionNode]:
        """Build execution phase nodes."""
        nodes: List[TraceExecutionNode] = []
        seen_executions: set = set()
        
        for link in trace_links:
            if link.target_domain == TraceDomain.EXECUTION:
                execution_id = link.target_id
                
                if execution_id in seen_executions:
                    continue
                seen_executions.add(execution_id)
                
                # Get ledger entry for this execution if available
                ledger_entry_hash = UNAVAILABLE_MARKER
                if link.pac_id:
                    entries = self._execution_ledger.get_by_pac_id(link.pac_id)
                    for entry in entries:
                        if (entry.payload.get("execution_id") == execution_id or
                            entry.entry_id == execution_id):
                            ledger_entry_hash = entry.entry_hash
                            break
                
                node = TraceExecutionNode(
                    node_id=f"execution_{execution_id}",
                    execution_id=execution_id,
                    pac_id=link.pac_id,
                    agent_gid=link.agent_gid,
                    agent_name=link.metadata.get("agent_name", UNAVAILABLE_MARKER),
                    agent_state=link.metadata.get("agent_state", UNAVAILABLE_MARKER),
                    started_at=link.metadata.get("started_at"),
                    completed_at=link.metadata.get("completed_at"),
                    duration_ms=link.metadata.get("duration_ms"),
                    trace_hash=link.trace_hash,
                    ledger_entry_hash=ledger_entry_hash,
                )
                nodes.append(node)
        
        return nodes
    
    def _build_settlement_nodes(
        self,
        pdo_id: str,
        trace_links: List[TraceLink],
    ) -> List[TraceSettlementNode]:
        """Build settlement phase nodes."""
        nodes: List[TraceSettlementNode] = []
        seen_settlements: set = set()
        
        for link in trace_links:
            if link.target_domain == TraceDomain.SETTLEMENT:
                settlement_id = link.target_id
                
                if settlement_id in seen_settlements:
                    continue
                seen_settlements.add(settlement_id)
                
                node = TraceSettlementNode(
                    node_id=f"settlement_{settlement_id}",
                    settlement_id=settlement_id,
                    outcome_id=link.metadata.get("outcome_id"),
                    outcome_status=link.metadata.get("outcome_status", UNAVAILABLE_MARKER),
                    pdo_id=pdo_id,
                    pac_id=link.pac_id,
                    settled_at=link.metadata.get("settled_at"),
                    trace_hash=link.trace_hash,
                )
                nodes.append(node)
        
        return nodes
    
    def _build_ledger_nodes(
        self,
        pdo_id: str,
        trace_links: List[TraceLink],
    ) -> List[TraceLedgerNode]:
        """Build ledger phase nodes."""
        nodes: List[TraceLedgerNode] = []
        seen_entries: set = set()
        
        for link in trace_links:
            if link.target_domain == TraceDomain.LEDGER:
                ledger_entry_id = link.target_id
                
                if ledger_entry_id in seen_entries:
                    continue
                seen_entries.add(ledger_entry_id)
                
                node = TraceLedgerNode(
                    node_id=f"ledger_{ledger_entry_id}",
                    ledger_entry_id=ledger_entry_id,
                    sequence_number=link.metadata.get("sequence_number", -1),
                    entry_type=link.metadata.get("entry_type", UNAVAILABLE_MARKER),
                    entry_hash=link.metadata.get("entry_hash", UNAVAILABLE_MARKER),
                    previous_hash=link.metadata.get("previous_hash", UNAVAILABLE_MARKER),
                    pac_id=link.pac_id,
                    timestamp=link.timestamp,
                )
                nodes.append(node)
        
        return nodes
    
    def _identify_gaps(
        self,
        pdo_id: str,
        view: OCTraceView,
    ) -> List[TraceGap]:
        """
        Identify missing trace links.
        
        INV-TRACE-005: Missing links are explicit and non-silent.
        """
        gaps: List[TraceGap] = []
        gap_counter = 0
        
        # Get gaps from trace registry
        registry_gaps = self._trace_registry.get_trace_gaps(pdo_id)
        for rg in registry_gaps:
            gap_counter += 1
            gaps.append(TraceGap(
                gap_id=f"gap_{pdo_id}_{gap_counter}",
                gap_type=rg["gap_type"],
                to_domain=rg.get("missing_domain"),
                message=rg["message"],
            ))
        
        # Check for missing decision-to-execution links
        if view.decision_nodes and not view.execution_nodes:
            gap_counter += 1
            gaps.append(TraceGap(
                gap_id=f"gap_{pdo_id}_{gap_counter}",
                gap_type="LINK_MISSING",
                from_domain=TraceDomain.DECISION.value,
                to_domain=TraceDomain.EXECUTION.value,
                message=f"No execution trace for PDO {pdo_id}",
            ))
        
        # Check for missing execution-to-settlement links
        if view.execution_nodes and not view.settlement_nodes:
            gap_counter += 1
            gaps.append(TraceGap(
                gap_id=f"gap_{pdo_id}_{gap_counter}",
                gap_type="LINK_MISSING",
                from_domain=TraceDomain.EXECUTION.value,
                to_domain=TraceDomain.SETTLEMENT.value,
                message=f"No settlement trace for PDO {pdo_id}",
            ))
        
        # Check for missing settlement-to-ledger links
        if view.settlement_nodes and not view.ledger_nodes:
            gap_counter += 1
            gaps.append(TraceGap(
                gap_id=f"gap_{pdo_id}_{gap_counter}",
                gap_type="LINK_MISSING",
                from_domain=TraceDomain.SETTLEMENT.value,
                to_domain=TraceDomain.LEDGER.value,
                message=f"No ledger trace for PDO {pdo_id}",
            ))
        
        return gaps
    
    def _calculate_status(
        self,
        view: OCTraceView,
    ) -> tuple[TraceViewStatus, float]:
        """Calculate trace view status and completeness score."""
        # Expected: at least one node in each domain
        expected_domains = 4  # DECISION, EXECUTION, SETTLEMENT, LEDGER
        present_domains = 0
        
        if view.decision_nodes and view.decision_nodes[0].status != TraceNodeStatus.MISSING:
            present_domains += 1
        if view.execution_nodes:
            present_domains += 1
        if view.settlement_nodes:
            present_domains += 1
        if view.ledger_nodes:
            present_domains += 1
        
        completeness = present_domains / expected_domains
        
        if view.gaps:
            status = TraceViewStatus.INCOMPLETE
        elif completeness == 1.0:
            status = TraceViewStatus.COMPLETE
        else:
            status = TraceViewStatus.INCOMPLETE
        
        return status, completeness
    
    def aggregate_trace_timeline(self, pdo_id: str) -> OCTraceTimeline:
        """
        Aggregate chronological timeline for a PDO trace.
        
        Args:
            pdo_id: PDO identifier
        
        Returns:
            OCTraceTimeline: Timeline of trace events
        """
        timeline = OCTraceTimeline(pdo_id=pdo_id)
        events: List[Dict[str, Any]] = []
        
        # Get trace links for PDO
        trace_links = self._trace_registry.get_by_pdo_id(pdo_id)
        
        for link in trace_links:
            events.append({
                "event_id": link.trace_id,
                "event_type": link.link_type.value,
                "source_domain": link.source_domain.value,
                "target_domain": link.target_domain.value,
                "source_id": link.source_id,
                "target_id": link.target_id,
                "agent_gid": link.agent_gid,
                "trace_hash": link.trace_hash,
                "timestamp": link.timestamp,
            })
        
        # Sort by timestamp
        events.sort(key=lambda e: e["timestamp"])
        timeline.events = events
        
        return timeline
    
    def aggregate_pac_trace_summary(self, pac_id: str) -> Dict[str, Any]:
        """
        Aggregate trace summary for all PDOs in a PAC.
        
        Args:
            pac_id: PAC identifier
        
        Returns:
            Dict with PAC-level trace summary
        """
        trace_links = self._trace_registry.get_by_pac_id(pac_id)
        
        # Group by PDO
        pdo_ids: set = set()
        for link in trace_links:
            if link.pdo_id:
                pdo_ids.add(link.pdo_id)
        
        pdo_summaries: List[Dict[str, Any]] = []
        total_gaps = 0
        
        for pdo_id in pdo_ids:
            view = self.aggregate_trace_view(pdo_id)
            total_gaps += len(view.gaps)
            pdo_summaries.append({
                "pdo_id": pdo_id,
                "status": view.status.value,
                "completeness_score": view.completeness_score,
                "total_nodes": view.total_nodes,
                "gap_count": len(view.gaps),
            })
        
        return {
            "pac_id": pac_id,
            "pdo_count": len(pdo_ids),
            "total_trace_links": len(trace_links),
            "total_gaps": total_gaps,
            "pdo_summaries": pdo_summaries,
            "aggregated_at": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_TRACE_AGGREGATOR: Optional[TraceGraphAggregator] = None


def get_trace_aggregator() -> TraceGraphAggregator:
    """
    Get the singleton trace aggregator instance.
    
    Returns:
        TraceGraphAggregator: The singleton instance
    """
    global _TRACE_AGGREGATOR
    
    if _TRACE_AGGREGATOR is None:
        _TRACE_AGGREGATOR = TraceGraphAggregator()
        logger.info("Trace aggregator initialized")
    
    return _TRACE_AGGREGATOR


def reset_trace_aggregator() -> None:
    """Reset the singleton aggregator. Used for testing."""
    global _TRACE_AGGREGATOR
    _TRACE_AGGREGATOR = None


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Constants
    "TRACE_AGGREGATOR_VERSION",
    # Enums
    "TraceNodeStatus",
    "TraceViewStatus",
    # Node DTOs
    "TraceDecisionNode",
    "TraceExecutionNode",
    "TraceSettlementNode",
    "TraceLedgerNode",
    "TraceGap",
    # View DTOs
    "OCTraceView",
    "OCTraceTimeline",
    # Aggregator
    "TraceGraphAggregator",
    "get_trace_aggregator",
    "reset_trace_aggregator",
]
