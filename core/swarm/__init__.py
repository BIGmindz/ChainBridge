"""
Core Swarm Module — Byzantine Fault Tolerance
==============================================
PAC-44: Byzantine Supermajority & NIST Compliance

This module provides distributed consensus mechanisms for
multi-agent swarm coordination with Byzantine fault tolerance.

CANONICAL GATES:
- GATE-08: Supermajority Quorum (2/3 + 1)
- GATE-09: Diversity Parity (cross-logic audit)
- GATE-10: NIST FIPS 204/203 compliance
"""

from .byzantine_voter import (
    ByzantineVoter,
    AgentProof,
    AgentCore,
    ConsensusResult,
    ConsensusStatus,
    ByzantineMetrics
)

__all__ = [
    "ByzantineVoter",
    "AgentProof",
    "AgentCore",
    "ConsensusResult",
    "ConsensusStatus",
    "ByzantineMetrics"
]
