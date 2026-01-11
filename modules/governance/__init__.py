"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     CHAINBRIDGE GOVERNANCE MODULE                            ║
║                   PAC-GOV-P320-FEDERATION-POLICY                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Phase 3: THE MESH - Constitutional Law Layer                                ║
║                                                                              ║
║  "Freedom requires Law."                                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Governance Module enforces:
  - Peering Contracts: Who can join the federation
  - Slashing Conditions: Who must leave (and lose stake)
  - Policy Updates: How rules evolve (2/3 quorum)
  - Automated Justice: Code enforces law, not committees

Components:
  - policy.py: The Constitution (FederationPolicy)
  - slashing.py: The Court (SlashingEngine)

INVARIANTS:
  INV-GOV-001 (Constitutional Rigidity): Policy changes require 2/3 consensus
  INV-GOV-002 (Automated Justice): Slashing is code. If proof exists, punishment is immediate.

TRAINING SIGNAL:
  "The Rules are set. The Game is fair."
"""

__version__ = "3.0.0"
__phase__ = "THE_MESH"

from .policy import FederationPolicy, PeeringContract, PolicyConfig, NodeStatus
from .slashing import SlashingEngine, SlashingEvidence, SlashingResult, ViolationType

__all__ = [
    # Policy (The Constitution)
    "FederationPolicy",
    "PeeringContract",
    "PolicyConfig",
    "NodeStatus",
    # Slashing (The Court)
    "SlashingEngine",
    "SlashingEvidence",
    "SlashingResult",
    "ViolationType",
]
