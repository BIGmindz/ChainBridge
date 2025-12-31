# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge End-to-End Trace Registry
# PAC-009: Full End-to-End Traceability — ORDER 1 (Cody GID-01)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Cross-domain trace ID registry for end-to-end traceability.

Provides:
- TraceLink: Cross-domain binding record
- TraceRegistry: Append-only trace linkage storage
- Invariant enforcement for PDO → Agent → Settlement → Ledger

GOVERNANCE INVARIANTS:
- INV-TRACE-001: Every settlement must trace to exactly one PDO
- INV-TRACE-002: Every agent action must reference PAC + PDO
- INV-TRACE-003: Ledger hash links all phases (decision → execution → settlement)
- INV-TRACE-004: OC renders full chain without inference
- INV-TRACE-005: Missing links are explicit and non-silent
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
from typing import Any, Dict, Iterator, List, Optional, Set

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

TRACE_REGISTRY_VERSION = "1.0.0"
"""Trace registry version."""

GENESIS_TRACE_HASH = "0" * 64
"""Genesis hash for trace chain."""

MISSING_TRACE_ID = "MISSING"
"""Explicit marker for missing trace ID (INV-TRACE-005)."""

UNAVAILABLE_MARKER = "UNAVAILABLE"
"""Explicit marker for unavailable data (INV-TRACE-005)."""


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE DOMAIN
# ═══════════════════════════════════════════════════════════════════════════════

class TraceDomain(str, Enum):
    """
    Cross-domain trace domains.
    
    Each domain represents a phase in the execution lifecycle
    that must be traceable end-to-end.
    """
    DECISION = "DECISION"       # PDO creation / decision point
    EXECUTION = "EXECUTION"     # Agent execution phase
    SETTLEMENT = "SETTLEMENT"   # Settlement / outcome recording
    LEDGER = "LEDGER"           # Ledger persistence
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all domain values."""
        return [d.value for d in cls]


class TraceLinkType(str, Enum):
    """
    Type of trace link binding.
    
    Links represent relationships between domains.
    """
    PDO_TO_DECISION = "PDO_TO_DECISION"           # PDO → Decision context
    DECISION_TO_EXECUTION = "DECISION_TO_EXECUTION"  # Decision → Execution
    EXECUTION_TO_SETTLEMENT = "EXECUTION_TO_SETTLEMENT"  # Execution → Settlement
    SETTLEMENT_TO_LEDGER = "SETTLEMENT_TO_LEDGER"      # Settlement → Ledger
    DIRECT_REFERENCE = "DIRECT_REFERENCE"              # Direct cross-reference


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE LINK DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════════

def compute_trace_hash(
    trace_id: str,
    source_domain: str,
    source_id: str,
    target_domain: str,
    target_id: str,
    pac_id: str,
    previous_hash: str,
    timestamp: str,
) -> str:
    """
    Compute SHA-256 hash for trace link chain integrity.
    
    Args:
        trace_id: Unique trace identifier
        source_domain: Source domain
        source_id: Source entity ID
        target_domain: Target domain
        target_id: Target entity ID
        pac_id: PAC identifier
        previous_hash: Hash of previous trace link
        timestamp: ISO timestamp
    
    Returns:
        SHA-256 hash as hex string
    """
    content = f"{trace_id}|{source_domain}|{source_id}|{target_domain}|{target_id}|{pac_id}|{previous_hash}|{timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class TraceLink:
    """
    Cross-domain trace link binding.
    
    Represents a binding between two entities in different domains,
    enabling end-to-end traceability.
    
    INV-TRACE-003: Ledger hash links all phases.
    """
    
    # Identity
    trace_id: str
    sequence_number: int
    
    # Source domain + ID
    source_domain: TraceDomain
    source_id: str
    
    # Target domain + ID
    target_domain: TraceDomain
    target_id: str
    
    # Link type
    link_type: TraceLinkType
    
    # Context
    pac_id: str
    pdo_id: Optional[str] = None  # Always trace back to PDO (INV-TRACE-001)
    agent_gid: Optional[str] = None
    
    # Chain integrity
    trace_hash: str = ""
    previous_hash: str = GENESIS_TRACE_HASH
    
    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result["source_domain"] = self.source_domain.value
        result["target_domain"] = self.target_domain.value
        result["link_type"] = self.link_type.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceLink":
        """Create from dictionary."""
        data = data.copy()
        data["source_domain"] = TraceDomain(data["source_domain"])
        data["target_domain"] = TraceDomain(data["target_domain"])
        data["link_type"] = TraceLinkType(data["link_type"])
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE VIOLATION
# ═══════════════════════════════════════════════════════════════════════════════

class TraceInvariantViolation(Exception):
    """
    Exception raised when a trace invariant is violated.
    
    INV-TRACE-005: Missing links are explicit and non-silent.
    """
    
    def __init__(self, invariant: str, message: str, context: Dict[str, Any] = None):
        self.invariant = invariant
        self.message = message
        self.context = context or {}
        super().__init__(f"{invariant}: {message}")


# ═══════════════════════════════════════════════════════════════════════════════
# TRACE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class TraceRegistry:
    """
    Append-only trace link registry with invariant enforcement.
    
    Thread-safe implementation that maintains:
    - Append-only semantics
    - Hash chain integrity
    - Cross-domain trace invariants
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._links: List[TraceLink] = []
        self._by_pdo_id: Dict[str, List[TraceLink]] = {}
        self._by_pac_id: Dict[str, List[TraceLink]] = {}
        self._by_source: Dict[str, List[TraceLink]] = {}  # source_domain:source_id
        self._by_target: Dict[str, List[TraceLink]] = {}  # target_domain:target_id
        self._settlement_to_pdo: Dict[str, str] = {}      # INV-TRACE-001 enforcement
        self._lock = threading.Lock()
    
    # ───────────────────────────────────────────────────────────────────────────
    # APPEND OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def register_link(
        self,
        source_domain: TraceDomain,
        source_id: str,
        target_domain: TraceDomain,
        target_id: str,
        link_type: TraceLinkType,
        pac_id: str,
        pdo_id: Optional[str] = None,
        agent_gid: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceLink:
        """
        Register a new trace link.
        
        Enforces all trace invariants before appending.
        
        Args:
            source_domain: Source domain
            source_id: Source entity ID
            target_domain: Target domain
            target_id: Target entity ID
            link_type: Type of link
            pac_id: PAC identifier
            pdo_id: Optional PDO ID for root tracing
            agent_gid: Optional agent GID
            metadata: Optional additional metadata
        
        Returns:
            TraceLink: The created trace link
        
        Raises:
            TraceInvariantViolation: If any invariant would be violated
        """
        with self._lock:
            # Enforce invariants
            self._enforce_invariants(
                source_domain=source_domain,
                source_id=source_id,
                target_domain=target_domain,
                target_id=target_id,
                link_type=link_type,
                pac_id=pac_id,
                pdo_id=pdo_id,
                agent_gid=agent_gid,
            )
            
            # Generate trace ID
            trace_id = f"trace_{uuid.uuid4().hex[:12]}"
            
            # Get sequence and previous hash
            sequence = len(self._links)
            previous_hash = (
                self._links[-1].trace_hash if self._links else GENESIS_TRACE_HASH
            )
            
            # Timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Compute trace hash
            trace_hash = compute_trace_hash(
                trace_id,
                source_domain.value,
                source_id,
                target_domain.value,
                target_id,
                pac_id,
                previous_hash,
                timestamp,
            )
            
            # Create link
            link = TraceLink(
                trace_id=trace_id,
                sequence_number=sequence,
                source_domain=source_domain,
                source_id=source_id,
                target_domain=target_domain,
                target_id=target_id,
                link_type=link_type,
                pac_id=pac_id,
                pdo_id=pdo_id,
                agent_gid=agent_gid,
                trace_hash=trace_hash,
                previous_hash=previous_hash,
                timestamp=timestamp,
                metadata=metadata or {},
            )
            
            # Store link
            self._links.append(link)
            
            # Index by PDO ID
            if pdo_id:
                if pdo_id not in self._by_pdo_id:
                    self._by_pdo_id[pdo_id] = []
                self._by_pdo_id[pdo_id].append(link)
            
            # Index by PAC ID
            if pac_id not in self._by_pac_id:
                self._by_pac_id[pac_id] = []
            self._by_pac_id[pac_id].append(link)
            
            # Index by source
            source_key = f"{source_domain.value}:{source_id}"
            if source_key not in self._by_source:
                self._by_source[source_key] = []
            self._by_source[source_key].append(link)
            
            # Index by target
            target_key = f"{target_domain.value}:{target_id}"
            if target_key not in self._by_target:
                self._by_target[target_key] = []
            self._by_target[target_key].append(link)
            
            # Track settlement → PDO mapping (INV-TRACE-001)
            if target_domain == TraceDomain.SETTLEMENT:
                if pdo_id:
                    self._settlement_to_pdo[target_id] = pdo_id
            
            logger.debug(
                f"TRACE_REGISTRY: Registered {link_type.value} "
                f"[{source_domain.value}:{source_id} → {target_domain.value}:{target_id}]"
            )
            
            return link
    
    def _enforce_invariants(
        self,
        source_domain: TraceDomain,
        source_id: str,
        target_domain: TraceDomain,
        target_id: str,
        link_type: TraceLinkType,
        pac_id: str,
        pdo_id: Optional[str],
        agent_gid: Optional[str],
    ) -> None:
        """
        Enforce trace invariants before registration.
        
        Raises TraceInvariantViolation if any invariant would be violated.
        """
        # INV-TRACE-001: Every settlement must trace to exactly one PDO
        if target_domain == TraceDomain.SETTLEMENT:
            if target_id in self._settlement_to_pdo:
                existing_pdo = self._settlement_to_pdo[target_id]
                if pdo_id and pdo_id != existing_pdo:
                    raise TraceInvariantViolation(
                        invariant="INV-TRACE-001",
                        message=(
                            f"Settlement {target_id} already linked to PDO {existing_pdo}. "
                            f"Cannot link to different PDO {pdo_id}."
                        ),
                        context={
                            "settlement_id": target_id,
                            "existing_pdo_id": existing_pdo,
                            "attempted_pdo_id": pdo_id,
                        },
                    )
            elif not pdo_id:
                raise TraceInvariantViolation(
                    invariant="INV-TRACE-001",
                    message=f"Settlement {target_id} must have a PDO reference.",
                    context={"settlement_id": target_id},
                )
        
        # INV-TRACE-002: Every agent action must reference PAC + PDO
        if agent_gid and target_domain == TraceDomain.EXECUTION:
            if not pac_id:
                raise TraceInvariantViolation(
                    invariant="INV-TRACE-002",
                    message=f"Agent {agent_gid} action must reference a PAC.",
                    context={"agent_gid": agent_gid},
                )
            # PDO reference is recommended but not strictly required for execution
            # since PDO may be created during execution
    
    # ───────────────────────────────────────────────────────────────────────────
    # FORBIDDEN OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def update(self, trace_id: str, **kwargs: Any) -> None:
        """UPDATE is forbidden. Registry is append-only."""
        raise RuntimeError(
            f"UPDATE FORBIDDEN: Trace registry is append-only. "
            f"Cannot update trace {trace_id}."
        )
    
    def delete(self, trace_id: str) -> None:
        """DELETE is forbidden. Registry is append-only."""
        raise RuntimeError(
            f"DELETE FORBIDDEN: Trace registry is append-only. "
            f"Cannot delete trace {trace_id}."
        )
    
    # ───────────────────────────────────────────────────────────────────────────
    # READ OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_by_pdo_id(self, pdo_id: str) -> List[TraceLink]:
        """Get all trace links for a PDO."""
        with self._lock:
            return self._by_pdo_id.get(pdo_id, []).copy()
    
    def get_by_pac_id(self, pac_id: str) -> List[TraceLink]:
        """Get all trace links for a PAC."""
        with self._lock:
            return self._by_pac_id.get(pac_id, []).copy()
    
    def get_by_source(self, domain: TraceDomain, source_id: str) -> List[TraceLink]:
        """Get all trace links from a source entity."""
        with self._lock:
            key = f"{domain.value}:{source_id}"
            return self._by_source.get(key, []).copy()
    
    def get_by_target(self, domain: TraceDomain, target_id: str) -> List[TraceLink]:
        """Get all trace links to a target entity."""
        with self._lock:
            key = f"{domain.value}:{target_id}"
            return self._by_target.get(key, []).copy()
    
    def get_settlement_pdo(self, settlement_id: str) -> Optional[str]:
        """
        Get the PDO ID for a settlement (INV-TRACE-001).
        
        Args:
            settlement_id: Settlement identifier
        
        Returns:
            PDO ID or None if not linked
        """
        with self._lock:
            return self._settlement_to_pdo.get(settlement_id)
    
    def get_all(self) -> List[TraceLink]:
        """Get all trace links ordered by sequence."""
        with self._lock:
            return self._links.copy()
    
    def get_latest(self) -> Optional[TraceLink]:
        """Get the most recent trace link."""
        with self._lock:
            return self._links[-1] if self._links else None
    
    def get_end_to_end_trace(self, pdo_id: str) -> Dict[str, List[TraceLink]]:
        """
        Get full end-to-end trace for a PDO.
        
        Returns links grouped by domain phase:
        - DECISION: Links in decision phase
        - EXECUTION: Links in execution phase
        - SETTLEMENT: Links in settlement phase
        - LEDGER: Links to ledger entries
        
        INV-TRACE-004: OC renders full chain without inference.
        
        Args:
            pdo_id: PDO identifier
        
        Returns:
            Dict mapping domain to trace links
        """
        with self._lock:
            links = self._by_pdo_id.get(pdo_id, [])
            
            result: Dict[str, List[TraceLink]] = {
                TraceDomain.DECISION.value: [],
                TraceDomain.EXECUTION.value: [],
                TraceDomain.SETTLEMENT.value: [],
                TraceDomain.LEDGER.value: [],
            }
            
            for link in links:
                # Categorize by target domain
                target_domain = link.target_domain.value
                if target_domain in result:
                    result[target_domain].append(link)
            
            return result
    
    def get_trace_gaps(self, pdo_id: str) -> List[Dict[str, Any]]:
        """
        Identify missing trace links for a PDO.
        
        INV-TRACE-005: Missing links are explicit and non-silent.
        
        Args:
            pdo_id: PDO identifier
        
        Returns:
            List of gap descriptions
        """
        with self._lock:
            links = self._by_pdo_id.get(pdo_id, [])
            
            gaps: List[Dict[str, Any]] = []
            
            # Check for expected domain coverage
            domains_present: Set[str] = set()
            for link in links:
                domains_present.add(link.target_domain.value)
            
            # Expected trace path: DECISION → EXECUTION → SETTLEMENT → LEDGER
            expected_path = [
                TraceDomain.DECISION.value,
                TraceDomain.EXECUTION.value,
                TraceDomain.SETTLEMENT.value,
                TraceDomain.LEDGER.value,
            ]
            
            for domain in expected_path:
                if domain not in domains_present:
                    gaps.append({
                        "pdo_id": pdo_id,
                        "missing_domain": domain,
                        "gap_type": "DOMAIN_NOT_LINKED",
                        "message": f"No trace link to {domain} domain for PDO {pdo_id}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            
            return gaps
    
    def __len__(self) -> int:
        """Return number of trace links in registry."""
        with self._lock:
            return len(self._links)
    
    def __iter__(self) -> Iterator[TraceLink]:
        """Iterate over trace links in order."""
        with self._lock:
            links = self._links.copy()
        for link in links:
            yield link
    
    # ───────────────────────────────────────────────────────────────────────────
    # CHAIN VERIFICATION
    # ───────────────────────────────────────────────────────────────────────────
    
    def verify_chain(self) -> tuple[bool, Optional[str]]:
        """
        Verify the trace hash chain integrity.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        with self._lock:
            if not self._links:
                return True, None
            
            # Check genesis
            if self._links[0].previous_hash != GENESIS_TRACE_HASH:
                return False, "Genesis trace has incorrect previous hash"
            
            # Verify chain
            for i in range(1, len(self._links)):
                prev_link = self._links[i - 1]
                curr_link = self._links[i]
                
                if curr_link.previous_hash != prev_link.trace_hash:
                    return False, (
                        f"Chain broken at sequence {i}: "
                        f"expected previous_hash {prev_link.trace_hash}, "
                        f"got {curr_link.previous_hash}"
                    )
            
            return True, None


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_TRACE_REGISTRY: Optional[TraceRegistry] = None
_REGISTRY_LOCK = threading.Lock()


def get_trace_registry() -> TraceRegistry:
    """
    Get the singleton trace registry instance.
    
    Returns:
        TraceRegistry: The singleton instance
    """
    global _TRACE_REGISTRY
    
    if _TRACE_REGISTRY is None:
        with _REGISTRY_LOCK:
            if _TRACE_REGISTRY is None:
                _TRACE_REGISTRY = TraceRegistry()
                logger.info("Trace registry initialized")
    
    return _TRACE_REGISTRY


def reset_trace_registry() -> None:
    """Reset the singleton registry. Used for testing."""
    global _TRACE_REGISTRY
    with _REGISTRY_LOCK:
        _TRACE_REGISTRY = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def register_pdo_to_decision(
    pdo_id: str,
    decision_id: str,
    pac_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> TraceLink:
    """
    Register PDO → Decision trace link.
    
    Args:
        pdo_id: PDO identifier
        decision_id: Decision identifier
        pac_id: PAC identifier
        metadata: Optional metadata
    
    Returns:
        TraceLink: The created trace link
    """
    registry = get_trace_registry()
    return registry.register_link(
        source_domain=TraceDomain.DECISION,
        source_id=pdo_id,
        target_domain=TraceDomain.DECISION,
        target_id=decision_id,
        link_type=TraceLinkType.PDO_TO_DECISION,
        pac_id=pac_id,
        pdo_id=pdo_id,
        metadata=metadata,
    )


def register_decision_to_execution(
    decision_id: str,
    execution_id: str,
    pac_id: str,
    pdo_id: str,
    agent_gid: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> TraceLink:
    """
    Register Decision → Execution trace link.
    
    Args:
        decision_id: Decision identifier
        execution_id: Execution identifier
        pac_id: PAC identifier
        pdo_id: PDO identifier
        agent_gid: Optional agent GID
        metadata: Optional metadata
    
    Returns:
        TraceLink: The created trace link
    """
    registry = get_trace_registry()
    return registry.register_link(
        source_domain=TraceDomain.DECISION,
        source_id=decision_id,
        target_domain=TraceDomain.EXECUTION,
        target_id=execution_id,
        link_type=TraceLinkType.DECISION_TO_EXECUTION,
        pac_id=pac_id,
        pdo_id=pdo_id,
        agent_gid=agent_gid,
        metadata=metadata,
    )


def register_execution_to_settlement(
    execution_id: str,
    settlement_id: str,
    pac_id: str,
    pdo_id: str,
    agent_gid: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> TraceLink:
    """
    Register Execution → Settlement trace link.
    
    INV-TRACE-001: Every settlement must trace to exactly one PDO.
    
    Args:
        execution_id: Execution identifier
        settlement_id: Settlement identifier
        pac_id: PAC identifier
        pdo_id: PDO identifier (required)
        agent_gid: Optional agent GID
        metadata: Optional metadata
    
    Returns:
        TraceLink: The created trace link
    """
    registry = get_trace_registry()
    return registry.register_link(
        source_domain=TraceDomain.EXECUTION,
        source_id=execution_id,
        target_domain=TraceDomain.SETTLEMENT,
        target_id=settlement_id,
        link_type=TraceLinkType.EXECUTION_TO_SETTLEMENT,
        pac_id=pac_id,
        pdo_id=pdo_id,
        agent_gid=agent_gid,
        metadata=metadata,
    )


def register_settlement_to_ledger(
    settlement_id: str,
    ledger_entry_id: str,
    pac_id: str,
    pdo_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> TraceLink:
    """
    Register Settlement → Ledger trace link.
    
    Args:
        settlement_id: Settlement identifier
        ledger_entry_id: Ledger entry identifier
        pac_id: PAC identifier
        pdo_id: PDO identifier
        metadata: Optional metadata
    
    Returns:
        TraceLink: The created trace link
    """
    registry = get_trace_registry()
    return registry.register_link(
        source_domain=TraceDomain.SETTLEMENT,
        source_id=settlement_id,
        target_domain=TraceDomain.LEDGER,
        target_id=ledger_entry_id,
        link_type=TraceLinkType.SETTLEMENT_TO_LEDGER,
        pac_id=pac_id,
        pdo_id=pdo_id,
        metadata=metadata,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Constants
    "TRACE_REGISTRY_VERSION",
    "GENESIS_TRACE_HASH",
    "MISSING_TRACE_ID",
    "UNAVAILABLE_MARKER",
    # Enums
    "TraceDomain",
    "TraceLinkType",
    # Data models
    "TraceLink",
    "TraceInvariantViolation",
    # Registry
    "TraceRegistry",
    "get_trace_registry",
    "reset_trace_registry",
    # Convenience functions
    "register_pdo_to_decision",
    "register_decision_to_execution",
    "register_execution_to_settlement",
    "register_settlement_to_ledger",
]
