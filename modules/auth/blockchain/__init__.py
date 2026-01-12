"""
ChainBridge Blockchain Audit Anchoring Module
=============================================

Provides immutable audit trail anchoring to blockchain networks.

Components:
  - xrp_anchor: XRP Ledger audit anchoring with Merkle trees
"""

from .xrp_anchor import (
    XRPConfig,
    XRPNetwork,
    MerkleTree,
    MerkleNode,
    AuditAnchor,
    XRPLedgerClient,
    AuditAnchorService,
    get_anchor_service,
    init_anchor_service,
)

__all__ = [
    "XRPConfig",
    "XRPNetwork",
    "MerkleTree",
    "MerkleNode",
    "AuditAnchor",
    "XRPLedgerClient",
    "AuditAnchorService",
    "get_anchor_service",
    "init_anchor_service",
]
