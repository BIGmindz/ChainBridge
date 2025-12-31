# ═══════════════════════════════════════════════════════════════════════════════
# DualBrain Router — Fast/Slow Memory Routing Architecture
# PAC-BENSON-P26: TITANS-READY NEURAL MEMORY ARCHITECTURE (SHADOW MODE)
# Agent: CODY (GID-01)
# ═══════════════════════════════════════════════════════════════════════════════

"""
DualBrain Router — Fast/Slow Memory Routing

PURPOSE:
    Implement routing logic for dual-brain architecture that decides
    whether queries should use fast (attention) or slow (persistent) memory.

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────┐
    │                    QUERY INPUT                              │
    │                         │                                   │
    │                         ▼                                   │
    │               ┌─────────────────┐                           │
    │               │  ROUTER GATE    │                           │
    │               │  (Surprise/Type)│                           │
    │               └────────┬────────┘                           │
    │                        │                                    │
    │         ┌──────────────┴──────────────┐                     │
    │         │                             │                     │
    │         ▼                             ▼                     │
    │  ┌──────────────┐            ┌──────────────┐               │
    │  │  FAST BRAIN  │            │  SLOW BRAIN  │               │
    │  │  (Attention) │            │  (Persistent)│               │
    │  │  O(context)  │            │  O(memory)   │               │
    │  └──────────────┘            └──────────────┘               │
    │         │                             │                     │
    │         └──────────────┬──────────────┘                     │
    │                        │                                    │
    │                        ▼                                    │
    │               ┌─────────────────┐                           │
    │               │  MERGE/BLEND    │                           │
    │               │  (HYBRID mode)  │                           │
    │               └─────────────────┘                           │
    └─────────────────────────────────────────────────────────────┘

ROUTING RULES:
    1. Low surprise + recent context → FAST
    2. High surprise + historical → SLOW
    3. Cross-context retrieval → SLOW
    4. Urgent/latency-critical → FAST (with SLOW fallback)

LANE: ARCHITECTURE_ONLY (NON-INFERENCING)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.ml.neural_memory import (
    DualBrainRouterInterface,
    MemoryTier,
    NeuralMemoryInterface,
    SurpriseMetric,
)


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING ENUMS
# ═══════════════════════════════════════════════════════════════════════════════


class RoutingStrategy(Enum):
    """Strategy for routing decisions."""

    SURPRISE_BASED = "SURPRISE_BASED"  # Route based on surprise metric
    TYPE_BASED = "TYPE_BASED"  # Route based on query type
    LATENCY_OPTIMIZED = "LATENCY_OPTIMIZED"  # Prefer fast for low latency
    ACCURACY_OPTIMIZED = "ACCURACY_OPTIMIZED"  # Prefer slow for accuracy
    HYBRID = "HYBRID"  # Use both with blending


class QueryType(Enum):
    """Classification of query types for routing."""

    RECENT_CONTEXT = "RECENT_CONTEXT"  # Query about recent context
    HISTORICAL = "HISTORICAL"  # Query about past interactions
    CROSS_SESSION = "CROSS_SESSION"  # Query spanning multiple sessions
    FACTUAL_RECALL = "FACTUAL_RECALL"  # Direct fact retrieval
    REASONING = "REASONING"  # Complex reasoning task
    UNKNOWN = "UNKNOWN"  # Cannot classify


class RoutingOutcome(Enum):
    """Outcome of routing decision."""

    FAST_ONLY = "FAST_ONLY"
    SLOW_ONLY = "SLOW_ONLY"
    HYBRID_FAST_PRIMARY = "HYBRID_FAST_PRIMARY"
    HYBRID_SLOW_PRIMARY = "HYBRID_SLOW_PRIMARY"
    FALLBACK = "FALLBACK"


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING DECISION
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class RoutingDecision:
    """
    Record of a routing decision.

    Contains the selected tier, strategy used, and confidence.
    """

    decision_id: str
    selected_tier: MemoryTier
    outcome: RoutingOutcome
    strategy_used: RoutingStrategy
    query_type: QueryType
    confidence: float  # 0.0 to 1.0
    surprise_value: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate confidence bounds."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")

    def compute_hash(self) -> str:
        """Compute decision hash for audit."""
        data = {
            "decision_id": self.decision_id,
            "selected_tier": self.selected_tier.value,
            "outcome": self.outcome.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING POLICY
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RoutingPolicy:
    """
    Configuration for routing decisions.

    Defines thresholds and preferences for the router.
    """

    # Surprise thresholds
    surprise_threshold_fast: float = 0.3  # Below this → FAST
    surprise_threshold_slow: float = 0.6  # Above this → SLOW

    # Strategy weights
    default_strategy: RoutingStrategy = RoutingStrategy.SURPRISE_BASED
    fallback_tier: MemoryTier = MemoryTier.FAST

    # Type-based routing preferences
    type_preferences: Dict[QueryType, MemoryTier] = field(default_factory=lambda: {
        QueryType.RECENT_CONTEXT: MemoryTier.FAST,
        QueryType.HISTORICAL: MemoryTier.SLOW,
        QueryType.CROSS_SESSION: MemoryTier.SLOW,
        QueryType.FACTUAL_RECALL: MemoryTier.SLOW,
        QueryType.REASONING: MemoryTier.HYBRID,
        QueryType.UNKNOWN: MemoryTier.FAST,
    })

    # Performance constraints
    max_latency_ms: int = 100  # Max acceptable latency
    enable_hybrid: bool = True  # Allow hybrid routing

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate policy configuration."""
        if self.surprise_threshold_fast >= self.surprise_threshold_slow:
            return False, "fast threshold must be < slow threshold"
        if not 0.0 <= self.surprise_threshold_fast <= 1.0:
            return False, "fast threshold must be in [0.0, 1.0]"
        if not 0.0 <= self.surprise_threshold_slow <= 1.0:
            return False, "slow threshold must be in [0.0, 1.0]"
        return True, None


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTING STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RoutingStatistics:
    """Statistics tracking for routing decisions."""

    fast_count: int = 0
    slow_count: int = 0
    hybrid_count: int = 0
    fallback_count: int = 0
    total_decisions: int = 0
    avg_confidence: float = 0.0
    _confidence_sum: float = 0.0

    def record(self, decision: RoutingDecision) -> None:
        """Record a routing decision."""
        self.total_decisions += 1
        self._confidence_sum += decision.confidence
        self.avg_confidence = self._confidence_sum / self.total_decisions

        if decision.outcome == RoutingOutcome.FAST_ONLY:
            self.fast_count += 1
        elif decision.outcome == RoutingOutcome.SLOW_ONLY:
            self.slow_count += 1
        elif decision.outcome in (RoutingOutcome.HYBRID_FAST_PRIMARY, RoutingOutcome.HYBRID_SLOW_PRIMARY):
            self.hybrid_count += 1
        elif decision.outcome == RoutingOutcome.FALLBACK:
            self.fallback_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fast_count": self.fast_count,
            "slow_count": self.slow_count,
            "hybrid_count": self.hybrid_count,
            "fallback_count": self.fallback_count,
            "total_decisions": self.total_decisions,
            "avg_confidence": round(self.avg_confidence, 4),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DUAL-BRAIN ROUTER IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════


class DualBrainRouter(DualBrainRouterInterface):
    """
    Implementation of dual-brain routing logic.

    Routes queries between FAST (attention) and SLOW (persistent) memory
    based on surprise metrics, query type, and policy configuration.
    """

    def __init__(self, policy: Optional[RoutingPolicy] = None) -> None:
        self._policy = policy or RoutingPolicy()
        self._stats = RoutingStatistics()
        self._decision_log: List[RoutingDecision] = []
        self._decision_counter = 0

        # Validate policy
        valid, error = self._policy.validate()
        if not valid:
            raise ValueError(f"Invalid routing policy: {error}")

    @property
    def policy(self) -> RoutingPolicy:
        """Get current routing policy."""
        return self._policy

    def route_query(
        self,
        query: Dict[str, Any],
        fast_memory: NeuralMemoryInterface,
        slow_memory: NeuralMemoryInterface,
    ) -> Tuple[MemoryTier, Dict[str, Any]]:
        """
        Route query to appropriate memory tier.

        Returns (selected_tier, routing_metadata).
        """
        # Classify query type
        query_type = self._classify_query(query)

        # Compute surprise if possible
        surprise: Optional[SurpriseMetric] = None
        if self._policy.default_strategy == RoutingStrategy.SURPRISE_BASED:
            surprise = slow_memory.compute_surprise(query)

        # Make routing decision
        decision = self._make_decision(query_type, surprise)

        # Record decision
        self._stats.record(decision)
        self._decision_log.append(decision)

        # Build metadata
        metadata = {
            "decision_id": decision.decision_id,
            "outcome": decision.outcome.value,
            "confidence": decision.confidence,
            "query_type": query_type.value,
            "strategy": decision.strategy_used.value,
        }
        if surprise:
            metadata["surprise_value"] = surprise.value

        return decision.selected_tier, metadata

    def get_routing_stats(self) -> Dict[str, int]:
        """Get statistics on routing decisions."""
        return {
            "fast": self._stats.fast_count,
            "slow": self._stats.slow_count,
            "hybrid": self._stats.hybrid_count,
            "total": self._stats.total_decisions,
        }

    def _classify_query(self, query: Dict[str, Any]) -> QueryType:
        """Classify query type for routing."""
        # Check for explicit type hint
        if "query_type" in query:
            type_str = query["query_type"]
            try:
                return QueryType(type_str)
            except ValueError:
                pass

        # Check for context hints
        if query.get("is_recent", False):
            return QueryType.RECENT_CONTEXT
        if query.get("is_historical", False):
            return QueryType.HISTORICAL
        if query.get("cross_session", False):
            return QueryType.CROSS_SESSION
        if query.get("requires_reasoning", False):
            return QueryType.REASONING

        return QueryType.UNKNOWN

    def _make_decision(
        self,
        query_type: QueryType,
        surprise: Optional[SurpriseMetric],
    ) -> RoutingDecision:
        """Make routing decision based on inputs."""
        self._decision_counter += 1
        decision_id = f"ROUTE-{self._decision_counter:08d}"

        strategy = self._policy.default_strategy

        # Surprise-based routing
        if strategy == RoutingStrategy.SURPRISE_BASED and surprise:
            return self._surprise_based_decision(decision_id, query_type, surprise)

        # Type-based routing
        if strategy == RoutingStrategy.TYPE_BASED:
            return self._type_based_decision(decision_id, query_type)

        # Hybrid routing
        if strategy == RoutingStrategy.HYBRID:
            return self._hybrid_decision(decision_id, query_type, surprise)

        # Default fallback
        return RoutingDecision(
            decision_id=decision_id,
            selected_tier=self._policy.fallback_tier,
            outcome=RoutingOutcome.FALLBACK,
            strategy_used=strategy,
            query_type=query_type,
            confidence=0.5,
        )

    def _surprise_based_decision(
        self,
        decision_id: str,
        query_type: QueryType,
        surprise: SurpriseMetric,
    ) -> RoutingDecision:
        """Make decision based on surprise metric."""
        if surprise.value < self._policy.surprise_threshold_fast:
            return RoutingDecision(
                decision_id=decision_id,
                selected_tier=MemoryTier.FAST,
                outcome=RoutingOutcome.FAST_ONLY,
                strategy_used=RoutingStrategy.SURPRISE_BASED,
                query_type=query_type,
                confidence=1.0 - surprise.value,
                surprise_value=surprise.value,
            )
        elif surprise.value > self._policy.surprise_threshold_slow:
            return RoutingDecision(
                decision_id=decision_id,
                selected_tier=MemoryTier.SLOW,
                outcome=RoutingOutcome.SLOW_ONLY,
                strategy_used=RoutingStrategy.SURPRISE_BASED,
                query_type=query_type,
                confidence=surprise.value,
                surprise_value=surprise.value,
            )
        else:
            # In between thresholds → hybrid
            if self._policy.enable_hybrid:
                return RoutingDecision(
                    decision_id=decision_id,
                    selected_tier=MemoryTier.HYBRID,
                    outcome=RoutingOutcome.HYBRID_FAST_PRIMARY,
                    strategy_used=RoutingStrategy.SURPRISE_BASED,
                    query_type=query_type,
                    confidence=0.7,
                    surprise_value=surprise.value,
                )
            else:
                return RoutingDecision(
                    decision_id=decision_id,
                    selected_tier=MemoryTier.FAST,
                    outcome=RoutingOutcome.FAST_ONLY,
                    strategy_used=RoutingStrategy.SURPRISE_BASED,
                    query_type=query_type,
                    confidence=0.6,
                    surprise_value=surprise.value,
                )

    def _type_based_decision(
        self,
        decision_id: str,
        query_type: QueryType,
    ) -> RoutingDecision:
        """Make decision based on query type."""
        tier = self._policy.type_preferences.get(query_type, self._policy.fallback_tier)

        if tier == MemoryTier.FAST:
            outcome = RoutingOutcome.FAST_ONLY
        elif tier == MemoryTier.SLOW:
            outcome = RoutingOutcome.SLOW_ONLY
        else:
            outcome = RoutingOutcome.HYBRID_FAST_PRIMARY

        return RoutingDecision(
            decision_id=decision_id,
            selected_tier=tier,
            outcome=outcome,
            strategy_used=RoutingStrategy.TYPE_BASED,
            query_type=query_type,
            confidence=0.8,
        )

    def _hybrid_decision(
        self,
        decision_id: str,
        query_type: QueryType,
        surprise: Optional[SurpriseMetric],
    ) -> RoutingDecision:
        """Make hybrid routing decision."""
        # Combine type and surprise signals
        type_tier = self._policy.type_preferences.get(query_type, MemoryTier.FAST)

        if surprise and surprise.value > 0.5:
            primary = MemoryTier.SLOW
            outcome = RoutingOutcome.HYBRID_SLOW_PRIMARY
        else:
            primary = type_tier
            outcome = RoutingOutcome.HYBRID_FAST_PRIMARY if primary == MemoryTier.FAST else RoutingOutcome.HYBRID_SLOW_PRIMARY

        return RoutingDecision(
            decision_id=decision_id,
            selected_tier=MemoryTier.HYBRID,
            outcome=outcome,
            strategy_used=RoutingStrategy.HYBRID,
            query_type=query_type,
            confidence=0.85,
            surprise_value=surprise.value if surprise else None,
        )

    def get_decision_log(self, limit: int = 100) -> List[RoutingDecision]:
        """Get recent routing decisions."""
        return self._decision_log[-limit:]

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed routing statistics."""
        return self._stats.to_dict()


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Enums
    "RoutingStrategy",
    "QueryType",
    "RoutingOutcome",
    # Data classes
    "RoutingDecision",
    "RoutingPolicy",
    "RoutingStatistics",
    # Implementation
    "DualBrainRouter",
]
