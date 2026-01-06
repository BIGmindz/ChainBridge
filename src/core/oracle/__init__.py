"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     CHAINBRIDGE — ORACLE LAYER                                ║
║                     PAC-OCC-P34 — Universal Dispatcher                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

The Oracle Layer provides multi-ledger integration for distributed consensus.

THE FIVE PILLARS:
1. Seeburger BIS  — B2B/Legacy Enterprise Bridge
2. Space and Time — ZK-Proof Verifiable Computation
3. Chainlink      — Cross-chain Oracle Interoperability
4. XRP Ledger     — High-speed Payment/DEX Settlement
5. Hedera (Hbar)  — ABFT Consensus / Fair Ordering (HCS)

IRON ARCHITECTURE LAW:
- All ledger submissions MUST use daemon threads (non-blocking)
- Parallel dispatch to multiple ledgers simultaneously
- Local audit is authoritative; external ledgers provide attestation

QUINT-PROOF DOCTRINE:
- Hedera timestamps the decision (Fair Ordering)
- SxT computes the ZK-Proof of logic
- Chainlink bridges across chains
- XRPL finalizes value transfer
- Seeburger orchestrates enterprise workflow

Authors:
- CODY (GID-01) — Implementation
- JEFFREY — Five Pillars Architecture
"""

from .hedera_adapter import HederaAdapter, get_hedera_adapter
from .xrp_adapter import XRPAdapter, get_xrp_adapter
from .dispatcher import UniversalDispatcher, get_dispatcher

__all__ = [
    "HederaAdapter",
    "get_hedera_adapter",
    "XRPAdapter",
    "get_xrp_adapter",
    "UniversalDispatcher",
    "get_dispatcher",
]
