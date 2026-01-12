#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     MESH TRUST - THE GATEKEEPER                              ║
║                   PAC-SEC-P305-FEDERATED-IDENTITY                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Trust Registry and Ban Propagation for Federated Mesh                       ║
║                                                                              ║
║  "Trust, but verify. Ban, and propagate."                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Trust module provides:
  - Trust Registry: Node ID → Trust Level mapping
  - Ban Proofs: Cryptographically signed bans with evidence
  - Ban Propagation: Gossip-based ban distribution
  - Trust persistence: Registry saved to disk

INVARIANTS:
  INV-SEC-003 (Ban Finality): A valid Ban Proof propagates faster than the 
                             bad actor can move.
  INV-SEC-005 (Quorum Enforcement): Critical actions require multiple signatures.

Usage:
    from modules.mesh.trust import TrustRegistry, BanProof, TrustLevel
    
    # Initialize registry
    registry = TrustRegistry(admin_node_ids=["admin1", "admin2"])
    
    # Add trusted node
    registry.add_node("node123", TrustLevel.PEER)
    
    # Issue a ban (requires admin or quorum)
    ban = BanProof.create(
        target_node_id="malicious_node",
        reason=BanReason.PROTOCOL_VIOLATION,
        evidence={"transactions": [...], "timestamp": "..."},
        issuer_identity=admin_identity
    )
    
    # Process ban from gossip
    registry.process_ban_gossip(ban)
"""

import base64
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Import identity module
try:
    from modules.mesh.identity import NodeIdentity, IdentityManager
except ImportError:
    # Allow standalone testing
    from identity import NodeIdentity, IdentityManager

__version__ = "3.0.0"

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# TRUST LEVELS
# ══════════════════════════════════════════════════════════════════════════════

class TrustLevel(Enum):
    """
    Trust levels for nodes in the federation.
    
    Higher levels have more privileges.
    """
    
    BANNED = 0          # Permanently banned, reject all connections
    UNKNOWN = 1         # New node, limited trust
    PENDING = 2         # Awaiting verification
    PEER = 3            # Verified peer, normal operations
    TRUSTED = 4         # Trusted partner, elevated privileges
    ADMIN = 5           # Administrator, can issue bans
    FOUNDER = 6         # Founding node, highest authority


class BanReason(Enum):
    """Reasons for banning a node."""
    
    PROTOCOL_VIOLATION = auto()     # Violated mesh protocol
    DOUBLE_SPEND = auto()           # Attempted double-spend attack
    SYBIL_ATTACK = auto()           # Multiple fake identities
    SPAM = auto()                   # Excessive spam/noise
    MALICIOUS_GOSSIP = auto()       # Spreading false information
    KEY_COMPROMISE = auto()         # Private key suspected compromised
    MANUAL_BAN = auto()             # Manual admin action
    QUORUM_BAN = auto()             # Banned by quorum vote
    FEDERATION_EXPULSION = auto()   # Expelled from federation


# ══════════════════════════════════════════════════════════════════════════════
# BAN PROOF
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class BanProof:
    """
    Cryptographically signed proof of a ban.
    
    INV-SEC-003: A valid ban proof MUST be propagated and enforced.
    
    Ban proofs can be issued by:
      1. A single ADMIN or FOUNDER node
      2. A quorum of TRUSTED nodes
    """
    
    # Ban target
    target_node_id: str
    target_node_name: Optional[str] = None
    
    # Ban details
    reason: BanReason = BanReason.MANUAL_BAN
    evidence_hash: str = ""  # SHA256 of evidence JSON
    evidence: Optional[Dict[str, Any]] = None  # Optional full evidence
    
    # Issuer information
    issuer_node_id: str = ""
    issuer_node_name: str = ""
    issuer_trust_level: TrustLevel = TrustLevel.UNKNOWN
    
    # Quorum support (for quorum bans)
    supporting_signatures: List[Dict[str, str]] = field(default_factory=list)
    required_quorum: int = 0  # 0 = single admin, >0 = quorum required
    
    # Metadata
    issued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None  # None = permanent
    ban_id: str = ""
    federation_id: str = "CHAINBRIDGE-FEDERATION"
    
    # Cryptographic proof
    signature: str = ""  # Base64 signature of ban data
    
    def __post_init__(self):
        """Generate ban ID if not provided."""
        if not self.ban_id:
            self.ban_id = self._generate_ban_id()
    
    def _generate_ban_id(self) -> str:
        """Generate unique ban ID from content hash."""
        content = f"{self.target_node_id}:{self.reason.name}:{self.issued_at}:{self.issuer_node_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    @classmethod
    def create(
        cls,
        target_node_id: str,
        reason: BanReason,
        evidence: Dict[str, Any],
        issuer_identity: NodeIdentity,
        issuer_trust_level: TrustLevel = TrustLevel.ADMIN,
        target_node_name: Optional[str] = None,
        expires_at: Optional[str] = None,
        federation_id: str = "CHAINBRIDGE-FEDERATION"
    ) -> "BanProof":
        """
        Create and sign a ban proof.
        
        INV-SEC-004: Ban includes cryptographic proof of issuer authority.
        
        Args:
            target_node_id: Node to ban
            reason: Reason for ban
            evidence: Dict of evidence data
            issuer_identity: Identity of issuer (must have private key)
            issuer_trust_level: Trust level of issuer
            target_node_name: Optional human-readable name
            expires_at: Optional expiration (None = permanent)
            federation_id: Federation identifier
            
        Returns:
            Signed BanProof
            
        Raises:
            ValueError: If issuer lacks authority or signing capability
        """
        # Verify authority
        if issuer_trust_level.value < TrustLevel.ADMIN.value:
            raise ValueError(f"Insufficient authority: {issuer_trust_level.name} cannot issue single-signer ban")
        
        if not issuer_identity.has_private_key:
            raise ValueError("Issuer identity cannot sign (no private key)")
        
        # Hash evidence
        evidence_json = json.dumps(evidence, sort_keys=True)
        evidence_hash = hashlib.sha256(evidence_json.encode()).hexdigest()
        
        # Create proof
        proof = cls(
            target_node_id=target_node_id,
            target_node_name=target_node_name,
            reason=reason,
            evidence_hash=evidence_hash,
            evidence=evidence,
            issuer_node_id=issuer_identity.node_id,
            issuer_node_name=issuer_identity.node_name,
            issuer_trust_level=issuer_trust_level,
            expires_at=expires_at,
            federation_id=federation_id
        )
        
        # Sign the proof
        proof.signature = proof._sign(issuer_identity)
        
        logger.warning(f"Ban proof created: {proof.target_node_id[:16]}... "
                      f"reason={proof.reason.name} by {proof.issuer_node_name}")
        
        return proof
    
    @classmethod
    def create_quorum_ban(
        cls,
        target_node_id: str,
        reason: BanReason,
        evidence: Dict[str, Any],
        signers: List[Tuple[NodeIdentity, TrustLevel]],
        quorum_threshold: int = 3,
        target_node_name: Optional[str] = None,
        federation_id: str = "CHAINBRIDGE-FEDERATION"
    ) -> "BanProof":
        """
        Create a quorum-signed ban proof.
        
        INV-SEC-005: Critical actions require multiple signatures.
        
        Args:
            target_node_id: Node to ban
            reason: Reason for ban
            evidence: Dict of evidence data
            signers: List of (identity, trust_level) tuples
            quorum_threshold: Minimum signatures required
            target_node_name: Optional human-readable name
            federation_id: Federation identifier
            
        Returns:
            Quorum-signed BanProof
            
        Raises:
            ValueError: If quorum not met
        """
        # Verify quorum
        valid_signers = [
            (id, lvl) for id, lvl in signers
            if lvl.value >= TrustLevel.TRUSTED.value and id.has_private_key
        ]
        
        if len(valid_signers) < quorum_threshold:
            raise ValueError(f"Quorum not met: {len(valid_signers)}/{quorum_threshold} valid signers")
        
        # Hash evidence
        evidence_json = json.dumps(evidence, sort_keys=True)
        evidence_hash = hashlib.sha256(evidence_json.encode()).hexdigest()
        
        # Create proof with first signer as primary
        first_identity, first_level = valid_signers[0]
        proof = cls(
            target_node_id=target_node_id,
            target_node_name=target_node_name,
            reason=BanReason.QUORUM_BAN,
            evidence_hash=evidence_hash,
            evidence=evidence,
            issuer_node_id=first_identity.node_id,
            issuer_node_name=first_identity.node_name,
            issuer_trust_level=first_level,
            required_quorum=quorum_threshold,
            federation_id=federation_id
        )
        
        # Sign with primary signer
        proof.signature = proof._sign(first_identity)
        
        # Collect supporting signatures
        for identity, level in valid_signers[1:]:
            sig = proof._sign(identity)
            proof.supporting_signatures.append({
                "node_id": identity.node_id,
                "node_name": identity.node_name,
                "trust_level": level.name,
                "signature": sig
            })
        
        logger.warning(f"Quorum ban proof created: {proof.target_node_id[:16]}... "
                      f"reason={proof.reason.name} with {len(valid_signers)} signatures")
        
        return proof
    
    def _get_signable_data(self) -> Dict[str, Any]:
        """Get data to sign (excludes signature field)."""
        return {
            "target_node_id": self.target_node_id,
            "reason": self.reason.name,
            "evidence_hash": self.evidence_hash,
            "issuer_node_id": self.issuer_node_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "ban_id": self.ban_id,
            "federation_id": self.federation_id,
            "required_quorum": self.required_quorum
        }
    
    def _sign(self, identity: NodeIdentity) -> str:
        """Sign the ban proof with an identity."""
        data = self._get_signable_data()
        return identity.sign_dict(data)
    
    def verify_signature(self, issuer_identity: NodeIdentity) -> bool:
        """Verify the primary signature."""
        data = self._get_signable_data()
        return issuer_identity.verify_dict(data, self.signature)
    
    def verify_quorum(self, identities: Dict[str, NodeIdentity]) -> Tuple[bool, int]:
        """
        Verify quorum signatures.
        
        Args:
            identities: Dict mapping node_id → NodeIdentity
            
        Returns:
            Tuple of (is_valid, verified_count)
        """
        if self.required_quorum == 0:
            # Single-signer ban, verify primary only
            issuer = identities.get(self.issuer_node_id)
            if issuer and self.verify_signature(issuer):
                return True, 1
            return False, 0
        
        # Count verified signatures
        verified = 0
        
        # Check primary
        issuer = identities.get(self.issuer_node_id)
        if issuer and self.verify_signature(issuer):
            verified += 1
        
        # Check supporting signatures
        data = self._get_signable_data()
        for support in self.supporting_signatures:
            signer_id = support["node_id"]
            sig = support["signature"]
            signer = identities.get(signer_id)
            
            if signer and signer.verify_dict(data, sig):
                verified += 1
        
        return verified >= self.required_quorum, verified
    
    def is_expired(self) -> bool:
        """Check if ban has expired."""
        if not self.expires_at:
            return False  # Permanent ban
        
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > expires
    
    def to_dict(self, include_evidence: bool = False) -> Dict[str, Any]:
        """Serialize to dictionary."""
        data = {
            "ban_id": self.ban_id,
            "target_node_id": self.target_node_id,
            "target_node_name": self.target_node_name,
            "reason": self.reason.name,
            "evidence_hash": self.evidence_hash,
            "issuer_node_id": self.issuer_node_id,
            "issuer_node_name": self.issuer_node_name,
            "issuer_trust_level": self.issuer_trust_level.name,
            "supporting_signatures": self.supporting_signatures,
            "required_quorum": self.required_quorum,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "federation_id": self.federation_id,
            "signature": self.signature
        }
        
        if include_evidence and self.evidence:
            data["evidence"] = self.evidence
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BanProof":
        """Deserialize from dictionary."""
        return cls(
            ban_id=data["ban_id"],
            target_node_id=data["target_node_id"],
            target_node_name=data.get("target_node_name"),
            reason=BanReason[data["reason"]],
            evidence_hash=data["evidence_hash"],
            evidence=data.get("evidence"),
            issuer_node_id=data["issuer_node_id"],
            issuer_node_name=data["issuer_node_name"],
            issuer_trust_level=TrustLevel[data["issuer_trust_level"]],
            supporting_signatures=data.get("supporting_signatures", []),
            required_quorum=data.get("required_quorum", 0),
            issued_at=data["issued_at"],
            expires_at=data.get("expires_at"),
            federation_id=data.get("federation_id", "CHAINBRIDGE-FEDERATION"),
            signature=data["signature"]
        )


# ══════════════════════════════════════════════════════════════════════════════
# TRUST REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

class TrustRegistry:
    """
    Registry mapping Node IDs to Trust Levels.
    
    INV-SEC-003: Bans are enforced and propagated automatically.
    
    The registry:
      - Tracks trust levels for all known nodes
      - Maintains a ban list with proofs
      - Persists to disk for durability
      - Provides allow/deny decisions for connections
    """
    
    def __init__(
        self,
        admin_node_ids: Optional[List[str]] = None,
        founder_node_ids: Optional[List[str]] = None,
        persistence_path: Optional[str] = None
    ):
        """
        Initialize trust registry.
        
        Args:
            admin_node_ids: Node IDs with ADMIN trust level
            founder_node_ids: Node IDs with FOUNDER trust level
            persistence_path: Path to persist registry
        """
        self._trust_levels: Dict[str, TrustLevel] = {}
        self._node_names: Dict[str, str] = {}
        self._bans: Dict[str, BanProof] = {}  # node_id → BanProof
        self._known_identities: Dict[str, NodeIdentity] = {}
        self._persistence_path = persistence_path
        
        # Initialize admins and founders
        for node_id in (founder_node_ids or []):
            self._trust_levels[node_id] = TrustLevel.FOUNDER
        
        for node_id in (admin_node_ids or []):
            if node_id not in self._trust_levels:  # Don't override FOUNDER
                self._trust_levels[node_id] = TrustLevel.ADMIN
        
        # Load existing registry if path provided
        if persistence_path and Path(persistence_path).exists():
            self._load()
    
    # ──────────────────────────────────────────────────────────────────────────
    # TRUST MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────────
    
    def get_trust_level(self, node_id: str) -> TrustLevel:
        """Get trust level for a node."""
        # Check bans first
        if node_id in self._bans:
            ban = self._bans[node_id]
            if not ban.is_expired():
                return TrustLevel.BANNED
        
        return self._trust_levels.get(node_id, TrustLevel.UNKNOWN)
    
    def set_trust_level(
        self,
        node_id: str,
        level: TrustLevel,
        node_name: Optional[str] = None
    ):
        """
        Set trust level for a node.
        
        Note: Cannot set BANNED directly, use issue_ban() instead.
        """
        if level == TrustLevel.BANNED:
            raise ValueError("Use issue_ban() to ban nodes")
        
        self._trust_levels[node_id] = level
        if node_name:
            self._node_names[node_id] = node_name
        
        logger.info(f"Trust level set: {node_id[:16]}... → {level.name}")
        self._save()
    
    def add_node(
        self,
        node_id: str,
        level: TrustLevel = TrustLevel.PEER,
        node_name: Optional[str] = None,
        identity: Optional[NodeIdentity] = None
    ):
        """Add a node with specified trust level."""
        self.set_trust_level(node_id, level, node_name)
        
        if identity:
            self._known_identities[node_id] = identity
    
    def remove_node(self, node_id: str):
        """Remove a node from the registry (does not ban)."""
        self._trust_levels.pop(node_id, None)
        self._node_names.pop(node_id, None)
        self._known_identities.pop(node_id, None)
        self._save()
    
    # ──────────────────────────────────────────────────────────────────────────
    # ACCESS CONTROL
    # ──────────────────────────────────────────────────────────────────────────
    
    def is_allowed(self, node_id: str, minimum_level: TrustLevel = TrustLevel.UNKNOWN) -> bool:
        """
        Check if node is allowed for an operation.
        
        INV-SEC-003: Banned nodes are always rejected.
        
        Args:
            node_id: Node to check
            minimum_level: Minimum required trust level
            
        Returns:
            True if allowed, False otherwise
        """
        level = self.get_trust_level(node_id)
        
        # Banned is always denied
        if level == TrustLevel.BANNED:
            logger.warning(f"Access denied (BANNED): {node_id[:16]}...")
            return False
        
        # Check minimum level
        allowed = level.value >= minimum_level.value
        
        if not allowed:
            logger.debug(f"Access denied: {node_id[:16]}... "
                        f"has {level.name}, needs {minimum_level.name}")
        
        return allowed
    
    def is_banned(self, node_id: str) -> bool:
        """Check if node is banned."""
        return self.get_trust_level(node_id) == TrustLevel.BANNED
    
    def can_connect(self, node_id: str) -> bool:
        """Check if node can establish a connection."""
        return self.is_allowed(node_id, TrustLevel.UNKNOWN)
    
    def can_attest(self, node_id: str) -> bool:
        """Check if node can submit attestations."""
        return self.is_allowed(node_id, TrustLevel.PEER)
    
    def can_admin(self, node_id: str) -> bool:
        """Check if node has admin privileges."""
        return self.is_allowed(node_id, TrustLevel.ADMIN)
    
    # ──────────────────────────────────────────────────────────────────────────
    # BAN MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────────
    
    def issue_ban(
        self,
        target_node_id: str,
        reason: BanReason,
        evidence: Dict[str, Any],
        issuer_identity: NodeIdentity,
        target_node_name: Optional[str] = None
    ) -> BanProof:
        """
        Issue a ban for a node.
        
        INV-SEC-003: Ban is immediately enforced and persisted.
        
        Args:
            target_node_id: Node to ban
            reason: Reason for ban
            evidence: Evidence supporting the ban
            issuer_identity: Identity of admin issuing ban
            target_node_name: Optional human-readable name
            
        Returns:
            BanProof to propagate via gossip
            
        Raises:
            ValueError: If issuer lacks authority
        """
        # Verify issuer authority
        issuer_level = self.get_trust_level(issuer_identity.node_id)
        
        if issuer_level.value < TrustLevel.ADMIN.value:
            raise ValueError(f"Cannot issue ban: {issuer_level.name} lacks authority")
        
        # Create ban proof
        ban = BanProof.create(
            target_node_id=target_node_id,
            reason=reason,
            evidence=evidence,
            issuer_identity=issuer_identity,
            issuer_trust_level=issuer_level,
            target_node_name=target_node_name
        )
        
        # Apply ban locally
        self._apply_ban(ban)
        
        return ban
    
    def _apply_ban(self, ban: BanProof):
        """Apply a ban to the registry."""
        self._bans[ban.target_node_id] = ban
        self._trust_levels[ban.target_node_id] = TrustLevel.BANNED
        
        if ban.target_node_name:
            self._node_names[ban.target_node_id] = ban.target_node_name
        
        logger.warning(f"BAN APPLIED: {ban.target_node_id[:16]}... "
                      f"reason={ban.reason.name}")
        
        self._save()
    
    def process_ban_gossip(self, ban: BanProof) -> Tuple[bool, str]:
        """
        Process a ban received via gossip.
        
        INV-SEC-003: Valid bans are applied immediately.
        
        Args:
            ban: BanProof received from gossip
            
        Returns:
            Tuple of (accepted, reason)
        """
        # Check if already banned
        if ban.target_node_id in self._bans:
            existing = self._bans[ban.target_node_id]
            if not existing.is_expired():
                return False, "Already banned"
        
        # Check expiration
        if ban.is_expired():
            return False, "Ban expired"
        
        # Verify signature (requires known issuer identity)
        issuer_identity = self._known_identities.get(ban.issuer_node_id)
        
        if issuer_identity:
            if ban.required_quorum > 0:
                # Verify quorum
                is_valid, count = ban.verify_quorum(self._known_identities)
                if not is_valid:
                    return False, f"Quorum verification failed: {count}/{ban.required_quorum}"
            else:
                # Single signature
                if not ban.verify_signature(issuer_identity):
                    return False, "Invalid signature"
        else:
            # Unknown issuer - check trust level claim
            # In production, would require identity lookup
            logger.warning(f"Unknown ban issuer: {ban.issuer_node_id[:16]}...")
            
            # For safety, reject bans from unknown issuers
            return False, "Unknown issuer"
        
        # Verify issuer authority
        issuer_level = self.get_trust_level(ban.issuer_node_id)
        
        if ban.required_quorum > 0:
            # Quorum ban - accept from TRUSTED and above
            if issuer_level.value < TrustLevel.TRUSTED.value:
                return False, f"Issuer lacks quorum authority: {issuer_level.name}"
        else:
            # Single-signer ban - requires ADMIN
            if issuer_level.value < TrustLevel.ADMIN.value:
                return False, f"Issuer lacks admin authority: {issuer_level.name}"
        
        # All checks passed - apply ban
        self._apply_ban(ban)
        
        return True, "Ban applied"
    
    def revoke_ban(
        self,
        node_id: str,
        admin_identity: NodeIdentity,
        new_level: TrustLevel = TrustLevel.PENDING
    ) -> bool:
        """
        Revoke a ban (admin action).
        
        Args:
            node_id: Node to unban
            admin_identity: Admin identity
            new_level: Trust level to assign after unban
            
        Returns:
            True if ban revoked, False otherwise
        """
        admin_level = self.get_trust_level(admin_identity.node_id)
        
        if admin_level.value < TrustLevel.ADMIN.value:
            logger.warning(f"Revoke denied: {admin_level.name} lacks authority")
            return False
        
        if node_id not in self._bans:
            logger.warning(f"No ban to revoke for {node_id[:16]}...")
            return False
        
        # Remove ban
        del self._bans[node_id]
        self._trust_levels[node_id] = new_level
        
        logger.warning(f"BAN REVOKED: {node_id[:16]}... → {new_level.name} "
                      f"by {admin_identity.node_name}")
        
        self._save()
        return True
    
    def get_ban_proof(self, node_id: str) -> Optional[BanProof]:
        """Get ban proof for a node."""
        return self._bans.get(node_id)
    
    def get_all_bans(self) -> List[BanProof]:
        """Get all active bans."""
        return [
            ban for ban in self._bans.values()
            if not ban.is_expired()
        ]
    
    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────
    
    def _save(self):
        """Persist registry to disk."""
        if not self._persistence_path:
            return
        
        data = {
            "version": __version__,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "trust_levels": {
                nid: level.name for nid, level in self._trust_levels.items()
            },
            "node_names": self._node_names,
            "bans": {
                nid: ban.to_dict() for nid, ban in self._bans.items()
            }
        }
        
        # Ensure directory exists
        Path(self._persistence_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self._persistence_path, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.debug(f"Registry saved to {self._persistence_path}")
    
    def _load(self):
        """Load registry from disk."""
        if not self._persistence_path or not Path(self._persistence_path).exists():
            return
        
        with open(self._persistence_path, "r") as f:
            data = json.load(f)
        
        # Load trust levels
        for nid, level_name in data.get("trust_levels", {}).items():
            try:
                self._trust_levels[nid] = TrustLevel[level_name]
            except KeyError:
                logger.warning(f"Unknown trust level: {level_name}")
        
        # Load names
        self._node_names = data.get("node_names", {})
        
        # Load bans
        for nid, ban_data in data.get("bans", {}).items():
            try:
                self._bans[nid] = BanProof.from_dict(ban_data)
            except Exception as e:
                logger.error(f"Failed to load ban: {e}")
        
        logger.info(f"Registry loaded: {len(self._trust_levels)} nodes, "
                   f"{len(self._bans)} bans")
    
    # ──────────────────────────────────────────────────────────────────────────
    # STATISTICS
    # ──────────────────────────────────────────────────────────────────────────
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        level_counts = {}
        for level in TrustLevel:
            count = sum(1 for l in self._trust_levels.values() if l == level)
            if count > 0:
                level_counts[level.name] = count
        
        active_bans = sum(1 for b in self._bans.values() if not b.is_expired())
        expired_bans = len(self._bans) - active_bans
        
        return {
            "total_nodes": len(self._trust_levels),
            "trust_levels": level_counts,
            "active_bans": active_bans,
            "expired_bans": expired_bans,
            "known_identities": len(self._known_identities)
        }


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test():
    """Run self-test to validate trust module."""
    print("=" * 70)
    print("MESH TRUST v3.0.0 - Self Test")
    print("=" * 70)
    
    # Test 1: Trust Registry setup
    print("\n[1/6] Testing trust registry setup...")
    admin = NodeIdentity.generate("ADMIN-NODE", "TEST-FEDERATION")
    founder = NodeIdentity.generate("FOUNDER-NODE", "TEST-FEDERATION")
    
    registry = TrustRegistry(
        admin_node_ids=[admin.node_id],
        founder_node_ids=[founder.node_id]
    )
    registry._known_identities[admin.node_id] = admin
    registry._known_identities[founder.node_id] = founder
    
    print(f"      ✓ Admin: {admin.node_id[:16]}...")
    print(f"      ✓ Founder: {founder.node_id[:16]}...")
    print(f"      ✓ Admin level: {registry.get_trust_level(admin.node_id).name}")
    print(f"      ✓ Founder level: {registry.get_trust_level(founder.node_id).name}")
    
    # Test 2: Trust level management
    print("\n[2/6] Testing trust level management...")
    peer = NodeIdentity.generate("PEER-NODE", "TEST-FEDERATION")
    
    registry.add_node(peer.node_id, TrustLevel.PEER, "PEER-NODE", peer)
    
    print(f"      ✓ Peer added: {peer.node_id[:16]}...")
    print(f"      ✓ Peer level: {registry.get_trust_level(peer.node_id).name}")
    print(f"      ✓ Peer can connect: {registry.can_connect(peer.node_id)}")
    print(f"      ✓ Peer can attest: {registry.can_attest(peer.node_id)}")
    print(f"      ✓ Peer can admin: {registry.can_admin(peer.node_id)}")
    
    # Test 3: Issue ban
    print("\n[3/6] Testing ban issuance...")
    bad_actor = NodeIdentity.generate("BAD-ACTOR", "TEST-FEDERATION")
    
    evidence = {
        "type": "DOUBLE_SPEND",
        "transactions": ["tx_001", "tx_002"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": "Attempted to spend same UTXO twice"
    }
    
    ban = registry.issue_ban(
        target_node_id=bad_actor.node_id,
        reason=BanReason.DOUBLE_SPEND,
        evidence=evidence,
        issuer_identity=admin,
        target_node_name="BAD-ACTOR"
    )
    
    print(f"      ✓ Ban ID: {ban.ban_id[:16]}...")
    print(f"      ✓ Reason: {ban.reason.name}")
    print(f"      ✓ Issuer: {ban.issuer_node_name}")
    print(f"      ✓ Evidence hash: {ban.evidence_hash[:16]}...")
    
    # Test 4: Ban enforcement
    print("\n[4/6] Testing ban enforcement...")
    print(f"      ✓ Bad actor level: {registry.get_trust_level(bad_actor.node_id).name}")
    print(f"      ✓ Is banned: {registry.is_banned(bad_actor.node_id)}")
    print(f"      ✓ Can connect: {registry.can_connect(bad_actor.node_id)}")
    assert registry.is_banned(bad_actor.node_id), "Bad actor should be banned"
    assert not registry.can_connect(bad_actor.node_id), "Banned node should not connect"
    
    # Test 5: Ban propagation via gossip
    print("\n[5/6] Testing ban propagation via gossip...")
    
    # Create new registry (simulating another node)
    registry2 = TrustRegistry(admin_node_ids=[admin.node_id])
    registry2._known_identities[admin.node_id] = admin
    
    # Process ban gossip
    accepted, reason = registry2.process_ban_gossip(ban)
    print(f"      ✓ Ban accepted: {accepted}")
    print(f"      ✓ Reason: {reason}")
    print(f"      ✓ Bad actor banned in registry2: {registry2.is_banned(bad_actor.node_id)}")
    assert accepted, f"Ban should be accepted: {reason}"
    assert registry2.is_banned(bad_actor.node_id), "Ban should propagate"
    
    # Test 6: Statistics
    print("\n[6/6] Testing registry statistics...")
    stats = registry.get_stats()
    print(f"      ✓ Total nodes: {stats['total_nodes']}")
    print(f"      ✓ Trust levels: {stats['trust_levels']}")
    print(f"      ✓ Active bans: {stats['active_bans']}")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print(f"Version: {__version__}")
    print("INV-SEC-003 (Ban Finality): ENFORCED")
    print("INV-SEC-005 (Quorum Enforcement): READY")
    print("=" * 70)
    print("\n🛡️ The Gatekeeper is ready. Bad actors will be rejected.")


if __name__ == "__main__":
    _self_test()
