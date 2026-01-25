"""
ChainBridge Gateway Infrastructure
===================================
PAC-41 Canonical Gateway Suite + PAC-42 Quantum Bridgehead + PAC-43 Swarm Siege

Modules:
- NFI-Handshake: Sovereign port authentication (Ed25519)
- Ghost-Siege Engine: Stealth transmission & stress testing
- Quantum Bridgehead: Post-quantum cryptography layer (Dilithium/Kyber)
- Swarm Orchestrator: Multi-agent resilience testing

Author: Jeffrey (Founding CTO) + Eve (GID-01)
Executor: BENSON (GID-00)
"""

from .nfi_handshake import NFIHandshake, HandshakeResult
from .ghost_siege_engine import GhostSiegeEngine, TransmissionResult, SiegeMetrics
from .quantum_bridgehead import QuantumBridgehead, QuantumSignature, QuantumKeypair
from .swarm_orchestrator import SwarmOrchestrator, AgentProfile, SwarmMetrics

__all__ = [
    'NFIHandshake',
    'HandshakeResult',
    'GhostSiegeEngine',
    'TransmissionResult',
    'SiegeMetrics',
    'QuantumBridgehead',
    'QuantumSignature',
    'QuantumKeypair',
    'SwarmOrchestrator',
    'AgentProfile',
    'SwarmMetrics',
]
