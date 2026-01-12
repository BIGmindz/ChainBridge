"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     CHAINBRIDGE MESH MODULE                                  ║
║                   PAC-NET-P300-MESH-NETWORKING                               ║
║                   PAC-SEC-P305-FEDERATED-IDENTITY                            ║
║                   PAC-CON-P310-CONSENSUS-ENGINE                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Phase 3: THE MESH - Federated Sovereignty                                   ║
║                                                                              ║
║  "One is none. Two is one. Many is Sovereign."                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Mesh Layer enables Sovereign Nodes to:
  - Discover each other via Gossip Protocol
  - Authenticate via mutual TLS (mTLS)
  - Maintain topology awareness
  - Cross-attest transactions across node boundaries
  - Prove identity via Ed25519 signatures (P305)
  - Enforce bans with cryptographic proofs (P305)
  - Achieve distributed consensus via Raft (P310)

Components:
  - networking.py: The Listener (mTLS server, peer connections)
  - discovery.py: The Gossip (SWIM-lite protocol, peer discovery)
  - identity.py: The Seal (Ed25519 keys, signature verification) [P305]
  - trust.py: The Gatekeeper (trust registry, ban propagation) [P305]
  - consensus.py: The Parliament (Raft leader election, log replication) [P310]
  - topology.py: The Map (network state, routing)
  - attestation.py: The Chain (cross-node proofs)

INVARIANTS:
  INV-NET-001 (Zero Trust Transport): Encryption and Auth are mandatory
  INV-NET-002 (Topology Awareness): Every node knows its neighbors
  INV-NET-003 (Sovereign Interop): Each node retains autonomy
  INV-SEC-002 (Identity Persistence): A Node ID is permanent [P305]
  INV-SEC-003 (Ban Finality): Valid bans propagate faster than bad actors [P305]
  INV-CON-001 (Safety): Never commit different values at same log index [P310]
  INV-CON-002 (Liveness): Eventually elect a leader if quorum is up [P310]

TRAINING SIGNAL:
  "The network is hostile. Trust no one. Verify everyone."
"""

__version__ = "3.0.0"
__phase__ = "THE_MESH"

from .networking import MeshNode, PeerConnection, MeshConfig
from .discovery import GossipProtocol, PeerRegistry, DiscoveryEvent
from .identity import NodeIdentity, IdentityManager
from .trust import TrustRegistry, BanProof, TrustLevel, BanReason
from .consensus import ConsensusEngine, RaftState, LogEntry, ClusterSimulator
from .explorer import MeshExplorer, NodeStatus, NetworkTopology, HealthReport, NodeRole, NodeHealth

__all__ = [
    # Networking (P300)
    "MeshNode",
    "PeerConnection",
    "MeshConfig",
    # Discovery (P300)
    "GossipProtocol",
    "PeerRegistry",
    "DiscoveryEvent",
    # Identity (P305)
    "NodeIdentity",
    "IdentityManager",
    # Trust (P305)
    "TrustRegistry",
    "BanProof",
    "TrustLevel",
    "BanReason",
    # Consensus (P310)
    "ConsensusEngine",
    "RaftState",
    "LogEntry",
    "ClusterSimulator",
    # Explorer (P330)
    "MeshExplorer",
    "NodeStatus",
    "NetworkTopology",
    "HealthReport",
    "NodeRole",
    "NodeHealth",
]
