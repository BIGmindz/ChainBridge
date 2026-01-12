"""
Blockchain Audit Anchoring Module
=================================

PAC-SEC-P822-B: BLOCKCHAIN AUDIT ANCHORING

Provides dual-chain blockchain anchoring for immutable audit records
using XRP Ledger and Hedera Consensus Service.

COMPONENTS:
- xrp_connector: XRP Ledger integration for public anchoring
- hedera_connector: Hedera Consensus Service for high-throughput anchoring
- proof_generator: Cryptographic proof generation for third-party verification
- pqc_anchor: Post-quantum cryptographic signatures
- anchor_coordinator: Dual-chain coordination with fallback logic

INVARIANTS ENFORCED:
- INV-ANCHOR-001: Events anchor within 5 minutes
- INV-ANCHOR-002: Only hashes anchor (never content)
- INV-ANCHOR-003: Dual-chain redundancy (XRP + Hedera)
- INV-ANCHOR-004: Proofs enable third-party verification
- INV-ANCHOR-005: PQC signatures are verifiable
- INV-ANCHOR-006: Fallback activates on primary failure
- INV-ANCHOR-007: Retry logic (3 attempts) before fail-closed

COMPLIANCE:
- SOC2 AU-9: Protection of audit information
- NIST FIPS 204: ML-DSA-65 post-quantum signatures
- Public verifiability via blockchain explorers

Example usage:
    from modules.audit.blockchain import (
        AnchorCoordinator,
        create_anchor_coordinator,
        ChainPriority,
    )
    
    # Create coordinator with XRPL as primary
    coordinator = create_anchor_coordinator(
        priority=ChainPriority.XRPL_PRIMARY,
        batch_size=100,
        batch_interval_seconds=300,
    )
    
    # Start coordinator
    with coordinator:
        # Add events for anchoring
        for event_hash in event_hashes:
            result = coordinator.add_event(event_hash)
            if result:
                print(f"Anchored: {result.merkle_root}")
        
        # Force final anchor
        coordinator.force_anchor()
"""

from .xrp_connector import (
    XRPLConnector,
    XRPLConfig,
    XRPLNetwork,
    AnchorStatus,
    TransactionReceipt,
    AnchorProof,
    create_xrpl_connector,
)

from .hedera_connector import (
    HederaConnector,
    HederaConfig,
    HederaNetwork,
    MessageStatus,
    MessageReceipt,
    ConsensusTimestamp,
    ConsensusProof,
    create_hedera_connector,
)

from .proof_generator import (
    ProofGenerator,
    ProofType,
    HashAlgorithm,
    MerkleProofNode,
    InclusionProof,
    AnchorProof as MerkleAnchorProof,
    BatchProof,
    create_proof_generator,
)

from .pqc_anchor import (
    PQCAnchor,
    PQCAlgorithm,
    SignatureMode,
    PQCKeyPair,
    PQCSignature,
    HybridSignature,
    AnchorSignature,
    create_pqc_anchor,
)

from .anchor_coordinator import (
    AnchorCoordinator,
    CoordinatorConfig,
    ChainPriority,
    AnchorStrategy,
    BatchTrigger,
    AnchorResult,
    AnchorStatus as CoordinatorStatus,
    create_anchor_coordinator,
)

__all__ = [
    # XRP Ledger
    "XRPLConnector",
    "XRPLConfig",
    "XRPLNetwork",
    "TransactionReceipt",
    "create_xrpl_connector",
    
    # Hedera
    "HederaConnector",
    "HederaConfig",
    "HederaNetwork",
    "MessageStatus",
    "MessageReceipt",
    "ConsensusTimestamp",
    "ConsensusProof",
    "create_hedera_connector",
    
    # Proof Generator
    "ProofGenerator",
    "ProofType",
    "HashAlgorithm",
    "MerkleProofNode",
    "InclusionProof",
    "MerkleAnchorProof",
    "BatchProof",
    "create_proof_generator",
    
    # PQC Anchor
    "PQCAnchor",
    "PQCAlgorithm",
    "SignatureMode",
    "PQCKeyPair",
    "PQCSignature",
    "HybridSignature",
    "AnchorSignature",
    "create_pqc_anchor",
    
    # Anchor Coordinator
    "AnchorCoordinator",
    "CoordinatorConfig",
    "ChainPriority",
    "AnchorStrategy",
    "BatchTrigger",
    "AnchorResult",
    "CoordinatorStatus",
    "create_anchor_coordinator",
]

__version__ = "1.0.0"
__pac__ = "PAC-SEC-P822-B"
