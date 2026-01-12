"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     CHAINBRIDGE SxT DATA SCHEMAS                             ║
║                      PAC-SYN-P930-SXT-BINDING                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Schema Definitions for Space and Time (SxT) Decentralized Data Warehouse    ║
║                                                                              ║
║  "We do not ask for trust. We provide proof."                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

SQL DDL schemas for SxT tables that store transaction anchors.
All PII is hashed before transmission. All queries are ZK-provable.

INVARIANTS:
  INV-DATA-005 (Ledger Mirroring): Every finalized tx MUST have SxT record
  INV-DATA-006 (Proof Finality): SxT Record is ultimate arbiter of history
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, timezone
import hashlib
import json


class SchemaVersion(Enum):
    """Schema versioning for migration support."""
    V1_0_0 = "1.0.0"
    V1_1_0 = "1.1.0"  # Added audit_log table
    
    @classmethod
    def current(cls) -> "SchemaVersion":
        return cls.V1_1_0


# ═══════════════════════════════════════════════════════════════════════════════
# SPACE AND TIME SQL SCHEMA (DDL)
# ═══════════════════════════════════════════════════════════════════════════════

CHAINBRIDGE_TRANSACTION_SCHEMA = """
-- ChainBridge Transaction Anchor Table
-- This is the PRIMARY ledger mirror in SxT
-- Every finalized transaction gets a row here
CREATE TABLE IF NOT EXISTS chainbridge_transactions (
    -- Primary identifier (UUID v7 for time-ordering)
    tx_id VARCHAR(64) PRIMARY KEY,
    
    -- Tenant isolation (hashed for privacy)
    tenant_hash VARCHAR(64) NOT NULL,
    
    -- Transaction metadata
    tx_type VARCHAR(32) NOT NULL,
    amount_cents BIGINT NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- Counterparty information (all hashed)
    sender_hash VARCHAR(64) NOT NULL,
    receiver_hash VARCHAR(64) NOT NULL,
    
    -- Temporal anchors (UTC epoch milliseconds)
    created_at BIGINT NOT NULL,
    finalized_at BIGINT NOT NULL,
    anchor_time BIGINT NOT NULL,
    
    -- Cryptographic anchors
    tx_hash VARCHAR(64) NOT NULL,
    merkle_root VARCHAR(64),
    state_root_before VARCHAR(64),
    state_root_after VARCHAR(64) NOT NULL,
    
    -- Node attestation
    node_id VARCHAR(64) NOT NULL,
    node_signature VARCHAR(128) NOT NULL,
    
    -- Consensus metadata
    raft_term BIGINT,
    raft_index BIGINT,
    block_height BIGINT,
    
    -- Schema version for migrations
    schema_version VARCHAR(16) NOT NULL DEFAULT '1.0.0',
    
    -- Indexes for query optimization
    INDEX idx_tenant_time (tenant_hash, finalized_at),
    INDEX idx_tx_hash (tx_hash),
    INDEX idx_block (block_height)
);
"""

CHAINBRIDGE_AUDIT_SCHEMA = """
-- ChainBridge Audit Log Table
-- Immutable record of all state transitions
CREATE TABLE IF NOT EXISTS chainbridge_audit_log (
    -- Primary identifier
    audit_id VARCHAR(64) PRIMARY KEY,
    
    -- Reference to transaction (if applicable)
    tx_id VARCHAR(64),
    
    -- Event classification
    event_type VARCHAR(32) NOT NULL,
    event_category VARCHAR(32) NOT NULL,
    
    -- Actor information (hashed)
    actor_hash VARCHAR(64),
    actor_role VARCHAR(32),
    
    -- Event payload (JSON, no PII)
    event_payload TEXT NOT NULL,
    
    -- Temporal
    event_time BIGINT NOT NULL,
    
    -- Cryptographic anchor
    event_hash VARCHAR(64) NOT NULL,
    previous_audit_hash VARCHAR(64),
    
    -- Chain linkage
    chain_position BIGINT NOT NULL,
    
    INDEX idx_event_time (event_time),
    INDEX idx_tx_ref (tx_id),
    INDEX idx_event_type (event_type)
);
"""

CHAINBRIDGE_PROOF_SCHEMA = """
-- ChainBridge Proof Receipt Table
-- Stores ZK-Proof receipts from SxT
CREATE TABLE IF NOT EXISTS chainbridge_proofs (
    -- Primary identifier
    proof_id VARCHAR(64) PRIMARY KEY,
    
    -- Reference to source record
    source_table VARCHAR(64) NOT NULL,
    source_id VARCHAR(64) NOT NULL,
    
    -- Proof metadata
    proof_type VARCHAR(32) NOT NULL,
    prover_version VARCHAR(16),
    
    -- The actual proof (base64 encoded)
    proof_data TEXT NOT NULL,
    
    -- Verification
    verified_at BIGINT,
    verification_status VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    
    -- SxT metadata
    sxt_commitment VARCHAR(128),
    sxt_block_hash VARCHAR(64),
    
    INDEX idx_source (source_table, source_id),
    INDEX idx_verification (verification_status)
);
"""


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASS SCHEMAS (FOR PYTHON)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TransactionSchema:
    """
    Python representation of a transaction record for SxT.
    
    All PII fields are hashed before transmission.
    """
    tx_id: str
    tenant_hash: str
    tx_type: str
    amount_cents: int
    currency: str
    sender_hash: str
    receiver_hash: str
    created_at: int
    finalized_at: int
    anchor_time: int
    tx_hash: str
    state_root_after: str
    node_id: str
    node_signature: str
    schema_version: str = "1.0.0"
    merkle_root: Optional[str] = None
    state_root_before: Optional[str] = None
    raft_term: Optional[int] = None
    raft_index: Optional[int] = None
    block_height: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "tx_id": self.tx_id,
            "tenant_hash": self.tenant_hash,
            "tx_type": self.tx_type,
            "amount_cents": self.amount_cents,
            "currency": self.currency,
            "sender_hash": self.sender_hash,
            "receiver_hash": self.receiver_hash,
            "created_at": self.created_at,
            "finalized_at": self.finalized_at,
            "anchor_time": self.anchor_time,
            "tx_hash": self.tx_hash,
            "merkle_root": self.merkle_root,
            "state_root_before": self.state_root_before,
            "state_root_after": self.state_root_after,
            "node_id": self.node_id,
            "node_signature": self.node_signature,
            "raft_term": self.raft_term,
            "raft_index": self.raft_index,
            "block_height": self.block_height,
            "schema_version": self.schema_version,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransactionSchema":
        """Create from dictionary."""
        return cls(**data)
    
    def compute_content_hash(self) -> str:
        """Compute deterministic hash of record content."""
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class AuditLogSchema:
    """Python representation of an audit log entry."""
    audit_id: str
    event_type: str
    event_category: str
    event_payload: str
    event_time: int
    event_hash: str
    chain_position: int
    tx_id: Optional[str] = None
    actor_hash: Optional[str] = None
    actor_role: Optional[str] = None
    previous_audit_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "tx_id": self.tx_id,
            "event_type": self.event_type,
            "event_category": self.event_category,
            "actor_hash": self.actor_hash,
            "actor_role": self.actor_role,
            "event_payload": self.event_payload,
            "event_time": self.event_time,
            "event_hash": self.event_hash,
            "previous_audit_hash": self.previous_audit_hash,
            "chain_position": self.chain_position,
        }


@dataclass
class ProofReceipt:
    """Receipt for a ZK-Proof from SxT."""
    proof_id: str
    source_table: str
    source_id: str
    proof_type: str
    proof_data: str
    verification_status: str = "PENDING"
    prover_version: Optional[str] = None
    verified_at: Optional[int] = None
    sxt_commitment: Optional[str] = None
    sxt_block_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "source_table": self.source_table,
            "source_id": self.source_id,
            "proof_type": self.proof_type,
            "prover_version": self.prover_version,
            "proof_data": self.proof_data,
            "verified_at": self.verified_at,
            "verification_status": self.verification_status,
            "sxt_commitment": self.sxt_commitment,
            "sxt_block_hash": self.sxt_block_hash,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PII HASHING UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

class PIIHasher:
    """
    Secure hasher for Personally Identifiable Information.
    
    Uses HMAC-SHA256 with a tenant-specific salt to prevent
    rainbow table attacks while maintaining determinism for
    deduplication.
    """
    
    def __init__(self, pepper: bytes):
        """
        Initialize with a system-wide pepper.
        
        Args:
            pepper: 32-byte secret key (from environment)
        """
        if len(pepper) < 32:
            raise ValueError("Pepper must be at least 32 bytes")
        self.pepper = pepper
    
    def hash_pii(self, value: str, tenant_id: str) -> str:
        """
        Hash a PII value with tenant-specific salting.
        
        Args:
            value: The PII value to hash (e.g., name, email)
            tenant_id: Tenant identifier for domain separation
            
        Returns:
            64-character hex string
        """
        import hmac
        
        # Combine pepper + tenant for domain separation
        salt = hashlib.sha256(
            self.pepper + tenant_id.encode()
        ).digest()
        
        # HMAC-SHA256 for the actual hash
        h = hmac.new(salt, value.encode(), hashlib.sha256)
        return h.hexdigest()
    
    def hash_tenant(self, tenant_id: str) -> str:
        """Hash a tenant ID (no additional salt needed)."""
        return hashlib.sha256(
            self.pepper + tenant_id.encode()
        ).hexdigest()
    
    def hash_address(self, address_dict: Dict[str, str], tenant_id: str) -> str:
        """
        Hash an address record deterministically.
        
        Args:
            address_dict: Dict with street, city, state, zip, country
            tenant_id: Tenant identifier
            
        Returns:
            64-character hex string representing the address
        """
        canonical = json.dumps(address_dict, sort_keys=True, separators=(',', ':'))
        return self.hash_pii(canonical, tenant_id)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class SchemaRegistry:
    """Registry of all SxT schemas."""
    
    SCHEMAS = {
        "chainbridge_transactions": CHAINBRIDGE_TRANSACTION_SCHEMA,
        "chainbridge_audit_log": CHAINBRIDGE_AUDIT_SCHEMA,
        "chainbridge_proofs": CHAINBRIDGE_PROOF_SCHEMA,
    }
    
    @classmethod
    def get_all_ddl(cls) -> str:
        """Get combined DDL for all tables."""
        return "\n\n".join(cls.SCHEMAS.values())
    
    @classmethod
    def get_schema(cls, table_name: str) -> str:
        """Get DDL for a specific table."""
        if table_name not in cls.SCHEMAS:
            raise ValueError(f"Unknown schema: {table_name}")
        return cls.SCHEMAS[table_name]
    
    @classmethod
    def list_tables(cls) -> List[str]:
        """List all registered table names."""
        return list(cls.SCHEMAS.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # DDL
    "CHAINBRIDGE_TRANSACTION_SCHEMA",
    "CHAINBRIDGE_AUDIT_SCHEMA",
    "CHAINBRIDGE_PROOF_SCHEMA",
    # Dataclasses
    "TransactionSchema",
    "AuditLogSchema",
    "ProofReceipt",
    # Utilities
    "PIIHasher",
    "SchemaRegistry",
    "SchemaVersion",
]
