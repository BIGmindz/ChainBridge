"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     CHAINBRIDGE — MIDDLEWARE LAYER                            ║
║                     PAC-OCC-P33 — C-Borgs Bridge                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

The Middleware Layer provides adapters for external service integration.

IRON ARCHITECTURE LAW:
- All outbound calls MUST use daemon threads (non-blocking)
- All data MUST pass through ALEX governance review
- Failures degrade gracefully (local state is authoritative)

Adapters:
- CBorgsAdapter: Sea Burgers Biz integration
- (Future) ChainlinkAdapter: Oracle dispatcher
- (Future) SxTAdapter: ZK-Proof attestation (moved from audit)

Authors:
- CODY (GID-01) — Implementation
- ALEX (GID-08) — Governance Review
- JEFFREY — Architecture
"""

from .cborgs_adapter import CBorgsAdapter, get_cborgs_adapter

__all__ = ["CBorgsAdapter", "get_cborgs_adapter"]
