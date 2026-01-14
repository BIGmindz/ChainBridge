"""
ChainBridge Sovereign Swarm - Zero-Knowledge Module
PAC-CONCORDIUM-ZK-26

Provides Concordium Layer 1 ZK-Proof integration for Zero-PII compliance.

Components:
- concordium_bridge: Main bridge to Concordium ZK-Proofs
- identity_gate_mapper: Maps ZK-Attributes to 2,000 Identity Gates

Author: BENSON-GID-00
Authority: ARCHITECT-JEFFREY
Epoch: EPOCH_001
"""

from .concordium_bridge import (
    ConcordiumBridge,
    ZKProof,
    ZKProofStatus,
    ZKValidationResult,
    SovereignSalt,
    ConcordiumLocalMirror,
    ZKIdentifierOrchestrator,
    IdentityAttribute,
    IdentityGate,
)

from .identity_gate_mapper import (
    IdentityGateMapper,
    GateDefinition,
    GateCategory,
    GateMapping,
    ValidationRule,
    get_identity_gate_mapper,
)

__all__ = [
    # Bridge classes
    "ConcordiumBridge",
    "ZKProof",
    "ZKProofStatus",
    "ZKValidationResult",
    "SovereignSalt",
    "ConcordiumLocalMirror",
    "ZKIdentifierOrchestrator",
    "IdentityAttribute",
    "IdentityGate",
    # Mapper classes
    "IdentityGateMapper",
    "GateDefinition",
    "GateCategory",
    "GateMapping",
    "ValidationRule",
    "get_identity_gate_mapper",
]

__version__ = "1.0.0"
__pac__ = "PAC-CONCORDIUM-ZK-26"
__epoch__ = "EPOCH_001"
