# Core ML Module
# PAC-BENSON-P26: Titans-Ready Neural Memory Architecture (SHADOW MODE)

from core.ml.neural_memory import (
    DualBrainRouterInterface,
    MemoryGateProtocol,
    MemoryMode,
    MemorySnapshot,
    MemoryStateHash,
    MemoryTier,
    MemoryUpdateRecord,
    NeuralMemoryInterface,
    ShadowModeMemory,
    SnapshotRegistry,
    SnapshotStatus,
    SurpriseLevel,
    SurpriseMetric,
)

from core.ml.dualbrain_router import (
    DualBrainRouter,
    QueryType,
    RoutingDecision,
    RoutingOutcome,
    RoutingPolicy,
    RoutingStatistics,
    RoutingStrategy,
)

__all__ = [
    # Neural Memory Enums
    "MemoryMode",
    "MemoryTier",
    "SnapshotStatus",
    "SurpriseLevel",
    # Neural Memory Data classes
    "MemoryStateHash",
    "SurpriseMetric",
    "MemorySnapshot",
    "MemoryUpdateRecord",
    # Neural Memory Interfaces
    "NeuralMemoryInterface",
    "DualBrainRouterInterface",
    "MemoryGateProtocol",
    # Neural Memory Implementations
    "ShadowModeMemory",
    "SnapshotRegistry",
    # DualBrain Router Enums
    "RoutingStrategy",
    "QueryType",
    "RoutingOutcome",
    # DualBrain Router Data classes
    "RoutingDecision",
    "RoutingPolicy",
    "RoutingStatistics",
    # DualBrain Router Implementation
    "DualBrainRouter",
]
