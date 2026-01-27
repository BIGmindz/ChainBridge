"""
ChainBridge Economics Package
PAC-ECO-P90 | Autopoietic Capital Loop

This package provides self-replicating growth mechanisms:
- Autopoietic Engine: Converts capital surplus → agent spawning
- Growth Cycle Management: Monitors hot wallet, executes expansions
- Legion Balancing: Maintains 3:2:1 ratio (Valuation/Governance/Security)

Exports:
- AutopoieticEngine: The life force - capital → agents
- GrowthCycleResult: Growth cycle execution result
- get_global_engine: Global engine singleton
"""

from core.economics.autopoiesis import (
    AutopoieticEngine,
    GrowthCycleResult,
    get_global_engine,
)

__all__ = [
    "AutopoieticEngine",
    "GrowthCycleResult",
    "get_global_engine",
]
