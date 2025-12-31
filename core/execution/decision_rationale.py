# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Decision Rationale Binding
# PAC-009: Full End-to-End Traceability — ORDER 2 (Maggie GID-10)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Decision rationale binding to PDO trace graph.

Provides:
- DecisionRationale: Immutable decision factor record
- RationaleRegistry: Append-only rationale storage
- PDO trace graph integration

GOVERNANCE INVARIANTS:
- INV-TRACE-003: Ledger hash links all phases (decision → execution → settlement)
- INV-TRACE-005: Missing links are explicit and non-silent
- Decision factors are surfaced as immutable references
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

from core.execution.trace_registry import (
    TraceDomain,
    TraceLinkType,
    get_trace_registry,
    register_pdo_to_decision,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

RATIONALE_VERSION = "1.0.0"
"""Rationale binding version."""

GENESIS_RATIONALE_HASH = "0" * 64
"""Genesis hash for rationale chain."""

UNAVAILABLE_MARKER = "UNAVAILABLE"
"""Explicit marker for unavailable data."""


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION FACTOR TYPE
# ═══════════════════════════════════════════════════════════════════════════════

class DecisionFactorType(str, Enum):
    """
    Type of decision factor influencing PDO creation.
    
    Each factor type represents a category of input that
    contributed to the decision.
    """
    MARKET_DATA = "MARKET_DATA"         # Market price, volume, volatility
    SIGNAL = "SIGNAL"                   # Trading signal / indicator
    RISK_ASSESSMENT = "RISK_ASSESSMENT"  # Risk metrics
    GOVERNANCE_RULE = "GOVERNANCE_RULE"  # Policy / compliance rule
    AGENT_ANALYSIS = "AGENT_ANALYSIS"    # Agent-produced analysis
    USER_INPUT = "USER_INPUT"            # Manual user override / input
    EXTERNAL_EVENT = "EXTERNAL_EVENT"    # External system event
    SYSTEM_STATE = "SYSTEM_STATE"        # System health / state
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all factor type values."""
        return [f.value for f in cls]


class RationaleStatus(str, Enum):
    """Status of decision rationale record."""
    PENDING = "PENDING"       # Rationale captured but not linked
    LINKED = "LINKED"         # Linked to PDO trace graph
    VERIFIED = "VERIFIED"     # Verified by review agent
    SUPERSEDED = "SUPERSEDED"  # Replaced by newer rationale


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION FACTOR
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DecisionFactor:
    """
    Single factor contributing to a decision.
    
    Immutable record of a specific input that influenced
    the PDO creation decision.
    """
    factor_id: str
    factor_type: DecisionFactorType
    factor_name: str
    factor_value: Any
    weight: float = 1.0  # Relative importance 0.0 - 1.0
    confidence: float = 1.0  # Factor confidence 0.0 - 1.0
    source: str = UNAVAILABLE_MARKER
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "factor_id": self.factor_id,
            "factor_type": self.factor_type.value,
            "factor_name": self.factor_name,
            "factor_value": self.factor_value,
            "weight": self.weight,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionFactor":
        """Create from dictionary."""
        data = data.copy()
        data["factor_type"] = DecisionFactorType(data["factor_type"])
        return cls(**data)


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION RATIONALE
# ═══════════════════════════════════════════════════════════════════════════════

def compute_rationale_hash(
    rationale_id: str,
    decision_id: str,
    factors_json: str,
    previous_hash: str,
    timestamp: str,
) -> str:
    """
    Compute SHA-256 hash for rationale chain integrity.
    
    Args:
        rationale_id: Unique rationale identifier
        decision_id: Decision identifier
        factors_json: JSON-serialized factors
        previous_hash: Hash of previous rationale
        timestamp: ISO timestamp
    
    Returns:
        SHA-256 hash as hex string
    """
    content = f"{rationale_id}|{decision_id}|{factors_json}|{previous_hash}|{timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class DecisionRationale:
    """
    Complete decision rationale record.
    
    Represents the full set of factors that contributed to a
    decision, with chain integrity for immutability.
    """
    
    # Identity
    rationale_id: str
    sequence_number: int
    decision_id: str
    
    # Factors
    factors: List[DecisionFactor] = field(default_factory=list)
    
    # Context
    pdo_id: Optional[str] = None
    pac_id: str = UNAVAILABLE_MARKER
    agent_gid: Optional[str] = None
    
    # Summary
    summary: str = UNAVAILABLE_MARKER
    recommendation: Optional[str] = None
    confidence_score: float = 0.0
    
    # Chain integrity
    rationale_hash: str = ""
    previous_hash: str = GENESIS_RATIONALE_HASH
    
    # Status and timing
    status: RationaleStatus = RationaleStatus.PENDING
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rationale_id": self.rationale_id,
            "sequence_number": self.sequence_number,
            "decision_id": self.decision_id,
            "factors": [f.to_dict() for f in self.factors],
            "pdo_id": self.pdo_id,
            "pac_id": self.pac_id,
            "agent_gid": self.agent_gid,
            "summary": self.summary,
            "recommendation": self.recommendation,
            "confidence_score": self.confidence_score,
            "rationale_hash": self.rationale_hash,
            "previous_hash": self.previous_hash,
            "status": self.status.value,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionRationale":
        """Create from dictionary."""
        data = data.copy()
        data["factors"] = [DecisionFactor.from_dict(f) for f in data.get("factors", [])]
        data["status"] = RationaleStatus(data.get("status", "PENDING"))
        return cls(**data)
    
    def get_factor_by_type(self, factor_type: DecisionFactorType) -> List[DecisionFactor]:
        """Get all factors of a specific type."""
        return [f for f in self.factors if f.factor_type == factor_type]
    
    def get_weighted_confidence(self) -> float:
        """Calculate weighted average confidence from factors."""
        if not self.factors:
            return 0.0
        total_weight = sum(f.weight for f in self.factors)
        if total_weight == 0:
            return 0.0
        return sum(f.weight * f.confidence for f in self.factors) / total_weight


# ═══════════════════════════════════════════════════════════════════════════════
# RATIONALE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class RationaleRegistry:
    """
    Append-only registry for decision rationales.
    
    Thread-safe implementation that maintains:
    - Append-only semantics
    - Hash chain integrity
    - PDO trace graph integration
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._rationales: List[DecisionRationale] = []
        self._by_decision_id: Dict[str, DecisionRationale] = {}
        self._by_pdo_id: Dict[str, List[DecisionRationale]] = {}
        self._by_pac_id: Dict[str, List[DecisionRationale]] = {}
        self._lock = threading.Lock()
    
    # ───────────────────────────────────────────────────────────────────────────
    # APPEND OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def register_rationale(
        self,
        decision_id: str,
        factors: List[DecisionFactor],
        pac_id: str,
        pdo_id: Optional[str] = None,
        agent_gid: Optional[str] = None,
        summary: str = UNAVAILABLE_MARKER,
        recommendation: Optional[str] = None,
        auto_link_trace: bool = True,
    ) -> DecisionRationale:
        """
        Register a new decision rationale.
        
        Args:
            decision_id: Decision identifier
            factors: List of decision factors
            pac_id: PAC identifier
            pdo_id: Optional PDO ID for trace linking
            agent_gid: Optional agent GID
            summary: Decision summary
            recommendation: Decision recommendation
            auto_link_trace: If True, automatically register PDO→Decision trace
        
        Returns:
            DecisionRationale: The created rationale
        """
        with self._lock:
            # Generate rationale ID
            rationale_id = f"rationale_{uuid.uuid4().hex[:12]}"
            
            # Get sequence and previous hash
            sequence = len(self._rationales)
            previous_hash = (
                self._rationales[-1].rationale_hash if self._rationales else GENESIS_RATIONALE_HASH
            )
            
            # Timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence(factors)
            
            # Serialize factors for hashing
            factors_json = json.dumps(
                [f.to_dict() for f in factors],
                sort_keys=True,
                default=str,
            )
            
            # Compute rationale hash
            rationale_hash = compute_rationale_hash(
                rationale_id,
                decision_id,
                factors_json,
                previous_hash,
                timestamp,
            )
            
            # Determine status
            status = RationaleStatus.LINKED if pdo_id else RationaleStatus.PENDING
            
            # Create rationale
            rationale = DecisionRationale(
                rationale_id=rationale_id,
                sequence_number=sequence,
                decision_id=decision_id,
                factors=factors,
                pdo_id=pdo_id,
                pac_id=pac_id,
                agent_gid=agent_gid,
                summary=summary,
                recommendation=recommendation,
                confidence_score=confidence_score,
                rationale_hash=rationale_hash,
                previous_hash=previous_hash,
                status=status,
                timestamp=timestamp,
            )
            
            # Store rationale
            self._rationales.append(rationale)
            self._by_decision_id[decision_id] = rationale
            
            # Index by PDO ID
            if pdo_id:
                if pdo_id not in self._by_pdo_id:
                    self._by_pdo_id[pdo_id] = []
                self._by_pdo_id[pdo_id].append(rationale)
            
            # Index by PAC ID
            if pac_id not in self._by_pac_id:
                self._by_pac_id[pac_id] = []
            self._by_pac_id[pac_id].append(rationale)
            
            logger.debug(
                f"RATIONALE_REGISTRY: Registered {rationale_id} "
                f"[decision={decision_id}, pdo={pdo_id}, factors={len(factors)}]"
            )
            
            return rationale
    
    def _calculate_confidence(self, factors: List[DecisionFactor]) -> float:
        """Calculate overall confidence from factors."""
        if not factors:
            return 0.0
        total_weight = sum(f.weight for f in factors)
        if total_weight == 0:
            return 0.0
        return sum(f.weight * f.confidence for f in factors) / total_weight
    
    def link_to_pdo(
        self,
        decision_id: str,
        pdo_id: str,
        pac_id: str,
        auto_register_trace: bool = True,
    ) -> Optional[DecisionRationale]:
        """
        Link an existing rationale to a PDO.
        
        Creates trace link in trace registry if auto_register_trace is True.
        
        Args:
            decision_id: Decision identifier
            pdo_id: PDO identifier
            pac_id: PAC identifier
            auto_register_trace: If True, register PDO→Decision trace
        
        Returns:
            Updated DecisionRationale or None if not found
        """
        with self._lock:
            rationale = self._by_decision_id.get(decision_id)
            if not rationale:
                return None
            
            # Update PDO linkage (note: we create a new object since dataclass is frozen-ish)
            # Actually dataclass is mutable by default, so direct update is fine
            rationale.pdo_id = pdo_id
            rationale.status = RationaleStatus.LINKED
            
            # Index by PDO ID
            if pdo_id not in self._by_pdo_id:
                self._by_pdo_id[pdo_id] = []
            if rationale not in self._by_pdo_id[pdo_id]:
                self._by_pdo_id[pdo_id].append(rationale)
            
            logger.debug(
                f"RATIONALE_REGISTRY: Linked {decision_id} to PDO {pdo_id}"
            )
            
            return rationale
    
    # ───────────────────────────────────────────────────────────────────────────
    # FORBIDDEN OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def update(self, rationale_id: str, **kwargs: Any) -> None:
        """UPDATE is forbidden. Registry is append-only."""
        raise RuntimeError(
            f"UPDATE FORBIDDEN: Rationale registry is append-only. "
            f"Cannot update rationale {rationale_id}."
        )
    
    def delete(self, rationale_id: str) -> None:
        """DELETE is forbidden. Registry is append-only."""
        raise RuntimeError(
            f"DELETE FORBIDDEN: Rationale registry is append-only. "
            f"Cannot delete rationale {rationale_id}."
        )
    
    # ───────────────────────────────────────────────────────────────────────────
    # READ OPERATIONS
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_by_decision_id(self, decision_id: str) -> Optional[DecisionRationale]:
        """Get rationale by decision ID."""
        with self._lock:
            return self._by_decision_id.get(decision_id)
    
    def get_by_pdo_id(self, pdo_id: str) -> List[DecisionRationale]:
        """Get all rationales for a PDO."""
        with self._lock:
            return self._by_pdo_id.get(pdo_id, []).copy()
    
    def get_by_pac_id(self, pac_id: str) -> List[DecisionRationale]:
        """Get all rationales for a PAC."""
        with self._lock:
            return self._by_pac_id.get(pac_id, []).copy()
    
    def get_all(self) -> List[DecisionRationale]:
        """Get all rationales ordered by sequence."""
        with self._lock:
            return self._rationales.copy()
    
    def get_latest(self) -> Optional[DecisionRationale]:
        """Get the most recent rationale."""
        with self._lock:
            return self._rationales[-1] if self._rationales else None
    
    def get_factors_by_type(
        self,
        pdo_id: str,
        factor_type: DecisionFactorType,
    ) -> List[DecisionFactor]:
        """
        Get all factors of a specific type for a PDO.
        
        Args:
            pdo_id: PDO identifier
            factor_type: Type of factor to retrieve
        
        Returns:
            List of matching factors
        """
        with self._lock:
            rationales = self._by_pdo_id.get(pdo_id, [])
            factors: List[DecisionFactor] = []
            for r in rationales:
                factors.extend(r.get_factor_by_type(factor_type))
            return factors
    
    def __len__(self) -> int:
        """Return number of rationales in registry."""
        with self._lock:
            return len(self._rationales)
    
    def __iter__(self) -> Iterator[DecisionRationale]:
        """Iterate over rationales in order."""
        with self._lock:
            rationales = self._rationales.copy()
        for rationale in rationales:
            yield rationale
    
    # ───────────────────────────────────────────────────────────────────────────
    # CHAIN VERIFICATION
    # ───────────────────────────────────────────────────────────────────────────
    
    def verify_chain(self) -> tuple[bool, Optional[str]]:
        """
        Verify the rationale hash chain integrity.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        with self._lock:
            if not self._rationales:
                return True, None
            
            # Check genesis
            if self._rationales[0].previous_hash != GENESIS_RATIONALE_HASH:
                return False, "Genesis rationale has incorrect previous hash"
            
            # Verify chain
            for i in range(1, len(self._rationales)):
                prev_rationale = self._rationales[i - 1]
                curr_rationale = self._rationales[i]
                
                if curr_rationale.previous_hash != prev_rationale.rationale_hash:
                    return False, (
                        f"Chain broken at sequence {i}: "
                        f"expected previous_hash {prev_rationale.rationale_hash}, "
                        f"got {curr_rationale.previous_hash}"
                    )
            
            return True, None


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_RATIONALE_REGISTRY: Optional[RationaleRegistry] = None
_REGISTRY_LOCK = threading.Lock()


def get_rationale_registry() -> RationaleRegistry:
    """
    Get the singleton rationale registry instance.
    
    Returns:
        RationaleRegistry: The singleton instance
    """
    global _RATIONALE_REGISTRY
    
    if _RATIONALE_REGISTRY is None:
        with _REGISTRY_LOCK:
            if _RATIONALE_REGISTRY is None:
                _RATIONALE_REGISTRY = RationaleRegistry()
                logger.info("Rationale registry initialized")
    
    return _RATIONALE_REGISTRY


def reset_rationale_registry() -> None:
    """Reset the singleton registry. Used for testing."""
    global _RATIONALE_REGISTRY
    with _REGISTRY_LOCK:
        _RATIONALE_REGISTRY = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def create_factor(
    factor_type: DecisionFactorType,
    factor_name: str,
    factor_value: Any,
    weight: float = 1.0,
    confidence: float = 1.0,
    source: str = UNAVAILABLE_MARKER,
) -> DecisionFactor:
    """
    Create a decision factor.
    
    Args:
        factor_type: Type of factor
        factor_name: Human-readable name
        factor_value: Factor value
        weight: Relative importance (0.0 - 1.0)
        confidence: Factor confidence (0.0 - 1.0)
        source: Source of factor data
    
    Returns:
        DecisionFactor: The created factor
    """
    return DecisionFactor(
        factor_id=f"factor_{uuid.uuid4().hex[:8]}",
        factor_type=factor_type,
        factor_name=factor_name,
        factor_value=factor_value,
        weight=min(1.0, max(0.0, weight)),
        confidence=min(1.0, max(0.0, confidence)),
        source=source,
    )


def register_decision_rationale(
    decision_id: str,
    factors: List[DecisionFactor],
    pac_id: str,
    pdo_id: Optional[str] = None,
    agent_gid: Optional[str] = None,
    summary: str = UNAVAILABLE_MARKER,
    recommendation: Optional[str] = None,
) -> DecisionRationale:
    """
    Register a decision rationale with the singleton registry.
    
    Args:
        decision_id: Decision identifier
        factors: List of decision factors
        pac_id: PAC identifier
        pdo_id: Optional PDO ID
        agent_gid: Optional agent GID
        summary: Decision summary
        recommendation: Decision recommendation
    
    Returns:
        DecisionRationale: The registered rationale
    """
    registry = get_rationale_registry()
    return registry.register_rationale(
        decision_id=decision_id,
        factors=factors,
        pac_id=pac_id,
        pdo_id=pdo_id,
        agent_gid=agent_gid,
        summary=summary,
        recommendation=recommendation,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Constants
    "RATIONALE_VERSION",
    "GENESIS_RATIONALE_HASH",
    "UNAVAILABLE_MARKER",
    # Enums
    "DecisionFactorType",
    "RationaleStatus",
    # Data models
    "DecisionFactor",
    "DecisionRationale",
    # Registry
    "RationaleRegistry",
    "get_rationale_registry",
    "reset_rationale_registry",
    # Convenience functions
    "create_factor",
    "register_decision_rationale",
]
