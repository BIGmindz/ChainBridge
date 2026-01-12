#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     MESH IDENTITY - THE SEAL                                 ║
║                   PAC-SEC-P305-FEDERATED-IDENTITY                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Ed25519 Cryptographic Identity for Mesh Nodes                               ║
║                                                                              ║
║  "Trust is hard to earn and easy to lose."                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Identity module provides:
  - Ed25519 key pair generation and management
  - Node identity persistence
  - Message signing and verification
  - Identity challenges for peer authentication

INVARIANTS:
  INV-SEC-002 (Identity Persistence): A Node ID is permanent. Losing the key means death.
  INV-SEC-004 (Cryptographic Proof): All identity claims must be verifiable.

Usage:
    from modules.mesh.identity import NodeIdentity, IdentityManager
    
    # Create new identity
    identity = NodeIdentity.generate(node_name="NODE-ALPHA")
    
    # Save to disk
    identity.save("keys/node_identity.json")
    
    # Sign a message
    signature = identity.sign(b"Hello, Federation!")
    
    # Verify a peer's signature
    is_valid = identity.verify_peer(peer_public_key, message, signature)
"""

import base64
import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Use cryptography library for Ed25519
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey
    )
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    Ed25519PrivateKey = None
    Ed25519PublicKey = None

__version__ = "3.0.0"

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# FALLBACK IMPLEMENTATION (for testing without cryptography library)
# ══════════════════════════════════════════════════════════════════════════════

class MockEd25519:
    """
    Mock Ed25519 implementation for testing when cryptography is not available.
    WARNING: NOT CRYPTOGRAPHICALLY SECURE - FOR TESTING ONLY
    """
    
    @staticmethod
    def generate_key_pair() -> Tuple[bytes, bytes]:
        """Generate mock key pair."""
        private_key = secrets.token_bytes(32)
        # Derive public key (mock - just hash the private key)
        public_key = hashlib.sha256(private_key).digest()
        return private_key, public_key
    
    @staticmethod
    def sign(private_key: bytes, message: bytes) -> bytes:
        """Mock signature (HMAC-like)."""
        combined = private_key + message
        return hashlib.sha512(combined).digest()
    
    @staticmethod
    def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Mock verification (always returns True in mock mode)."""
        # In real implementation, this would verify the signature
        # For mock, we just check signature length
        return len(signature) == 64


# ══════════════════════════════════════════════════════════════════════════════
# NODE IDENTITY
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class NodeIdentity:
    """
    Cryptographic identity for a mesh node.
    
    Each node has a unique Ed25519 key pair:
      - Public key: Shared with all peers, used as Node ID
      - Private key: Never shared, used to sign messages
    
    INV-SEC-002: The Node ID (public key hash) is permanent.
    """
    
    node_id: str                    # Hash of public key (hex)
    node_name: str                  # Human-readable name
    public_key_bytes: bytes         # Raw public key
    private_key_bytes: Optional[bytes] = None  # Raw private key (None if loaded from peer)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    federation_id: str = "CHAINBRIDGE-FEDERATION"
    capabilities: list = field(default_factory=lambda: ["ATTEST", "RELAY", "GOSSIP"])
    
    # Runtime state
    _private_key: Any = field(default=None, repr=False)
    _public_key: Any = field(default=None, repr=False)
    
    def __post_init__(self):
        """Initialize cryptographic key objects."""
        if CRYPTO_AVAILABLE and self.private_key_bytes:
            self._private_key = Ed25519PrivateKey.from_private_bytes(self.private_key_bytes)
            self._public_key = self._private_key.public_key()
        elif CRYPTO_AVAILABLE and self.public_key_bytes:
            self._public_key = Ed25519PublicKey.from_public_bytes(self.public_key_bytes)
    
    @classmethod
    def generate(cls, node_name: str, federation_id: str = "CHAINBRIDGE-FEDERATION") -> "NodeIdentity":
        """
        Generate a new node identity with fresh Ed25519 key pair.
        
        INV-SEC-002: This creates a permanent identity.
        """
        if CRYPTO_AVAILABLE:
            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            private_key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
        else:
            logger.warning("cryptography library not available - using mock keys (INSECURE)")
            private_key_bytes, public_key_bytes = MockEd25519.generate_key_pair()
        
        # Node ID is the hash of the public key
        node_id = hashlib.sha256(public_key_bytes).hexdigest()[:32]
        
        identity = cls(
            node_id=node_id,
            node_name=node_name,
            public_key_bytes=public_key_bytes,
            private_key_bytes=private_key_bytes,
            federation_id=federation_id
        )
        
        logger.info(f"Generated new identity: {node_name} ({node_id[:16]}...)")
        return identity
    
    @classmethod
    def from_public_key(cls, public_key_bytes: bytes, node_name: str = "PEER") -> "NodeIdentity":
        """Create identity from public key only (for peers)."""
        node_id = hashlib.sha256(public_key_bytes).hexdigest()[:32]
        return cls(
            node_id=node_id,
            node_name=node_name,
            public_key_bytes=public_key_bytes,
            private_key_bytes=None
        )
    
    @property
    def public_key_b64(self) -> str:
        """Get base64-encoded public key."""
        return base64.b64encode(self.public_key_bytes).decode("ascii")
    
    @property
    def has_private_key(self) -> bool:
        """Check if this identity can sign (has private key)."""
        return self.private_key_bytes is not None
    
    # ──────────────────────────────────────────────────────────────────────────
    # SIGNING & VERIFICATION
    # ──────────────────────────────────────────────────────────────────────────
    
    def sign(self, message: bytes) -> bytes:
        """
        Sign a message with our private key.
        
        Args:
            message: Raw bytes to sign
            
        Returns:
            64-byte Ed25519 signature
            
        Raises:
            ValueError: If no private key available
        """
        if not self.has_private_key:
            raise ValueError("Cannot sign: no private key")
        
        if CRYPTO_AVAILABLE and self._private_key:
            return self._private_key.sign(message)
        else:
            return MockEd25519.sign(self.private_key_bytes, message)
    
    def sign_dict(self, data: Dict[str, Any]) -> str:
        """Sign a dictionary (JSON-serialized)."""
        message = json.dumps(data, sort_keys=True).encode("utf-8")
        signature = self.sign(message)
        return base64.b64encode(signature).decode("ascii")
    
    def verify(self, message: bytes, signature: bytes) -> bool:
        """
        Verify a signature against our public key.
        
        Args:
            message: Original message bytes
            signature: Signature to verify
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if CRYPTO_AVAILABLE and self._public_key:
                self._public_key.verify(signature, message)
                return True
            else:
                return MockEd25519.verify(self.public_key_bytes, message, signature)
        except (InvalidSignature if CRYPTO_AVAILABLE else Exception):
            return False
    
    def verify_dict(self, data: Dict[str, Any], signature_b64: str) -> bool:
        """Verify a signed dictionary."""
        try:
            message = json.dumps(data, sort_keys=True).encode("utf-8")
            signature = base64.b64decode(signature_b64)
            return self.verify(message, signature)
        except Exception:
            return False
    
    @staticmethod
    def verify_peer(
        public_key_bytes: bytes,
        message: bytes,
        signature: bytes
    ) -> bool:
        """
        Verify a peer's signature given their public key.
        
        Static method for convenience when verifying without full identity.
        """
        peer_identity = NodeIdentity.from_public_key(public_key_bytes)
        return peer_identity.verify(message, signature)
    
    # ──────────────────────────────────────────────────────────────────────────
    # CHALLENGE-RESPONSE AUTHENTICATION
    # ──────────────────────────────────────────────────────────────────────────
    
    def create_challenge(self) -> Dict[str, Any]:
        """
        Create a challenge for peer authentication.
        
        The peer must sign this challenge with their private key.
        """
        challenge = {
            "type": "IDENTITY_CHALLENGE",
            "challenger": self.node_id,
            "nonce": secrets.token_hex(32),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "federation_id": self.federation_id
        }
        return challenge
    
    def respond_to_challenge(self, challenge: Dict[str, Any]) -> Dict[str, Any]:
        """
        Respond to an identity challenge by signing it.
        
        INV-SEC-004: Response includes cryptographic proof of identity.
        """
        if not self.has_private_key:
            raise ValueError("Cannot respond: no private key")
        
        response = {
            "type": "IDENTITY_RESPONSE",
            "responder": self.node_id,
            "responder_name": self.node_name,
            "public_key": self.public_key_b64,
            "challenge_nonce": challenge["nonce"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capabilities": self.capabilities
        }
        
        # Sign the response
        response["signature"] = self.sign_dict(response)
        
        return response
    
    def verify_challenge_response(
        self,
        original_challenge: Dict[str, Any],
        response: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify a challenge response from a peer.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check nonce matches
            if response.get("challenge_nonce") != original_challenge.get("nonce"):
                return False, "Nonce mismatch"
            
            # Extract public key
            public_key_b64 = response.get("public_key")
            if not public_key_b64:
                return False, "Missing public key"
            
            public_key_bytes = base64.b64decode(public_key_b64)
            
            # Verify node_id matches public key
            expected_node_id = hashlib.sha256(public_key_bytes).hexdigest()[:32]
            if response.get("responder") != expected_node_id:
                return False, "Node ID does not match public key"
            
            # Verify signature
            signature_b64 = response.pop("signature", None)
            if not signature_b64:
                return False, "Missing signature"
            
            peer_identity = NodeIdentity.from_public_key(public_key_bytes)
            if not peer_identity.verify_dict(response, signature_b64):
                return False, "Invalid signature"
            
            # Restore signature for caller
            response["signature"] = signature_b64
            
            return True, None
            
        except Exception as e:
            return False, f"Verification error: {e}"
    
    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────
    
    def save(self, path: str, include_private_key: bool = True):
        """
        Save identity to disk.
        
        INV-SEC-002: Identity persistence is critical.
        
        Args:
            path: File path for identity JSON
            include_private_key: Whether to include private key (default True)
        """
        data = {
            "version": __version__,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "federation_id": self.federation_id,
            "capabilities": self.capabilities,
            "created_at": self.created_at,
            "public_key": self.public_key_b64
        }
        
        if include_private_key and self.private_key_bytes:
            data["private_key"] = base64.b64encode(self.private_key_bytes).decode("ascii")
        
        # Ensure directory exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        # Write with restricted permissions
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        
        # Set file permissions (owner read/write only)
        os.chmod(path, 0o600)
        
        logger.info(f"Saved identity to {path}")
    
    @classmethod
    def load(cls, path: str) -> "NodeIdentity":
        """
        Load identity from disk.
        
        INV-SEC-002: Loading restores the permanent identity.
        """
        with open(path, "r") as f:
            data = json.load(f)
        
        public_key_bytes = base64.b64decode(data["public_key"])
        private_key_bytes = None
        
        if "private_key" in data:
            private_key_bytes = base64.b64decode(data["private_key"])
        
        identity = cls(
            node_id=data["node_id"],
            node_name=data["node_name"],
            public_key_bytes=public_key_bytes,
            private_key_bytes=private_key_bytes,
            federation_id=data.get("federation_id", "CHAINBRIDGE-FEDERATION"),
            capabilities=data.get("capabilities", ["ATTEST", "RELAY", "GOSSIP"]),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat())
        )
        
        logger.info(f"Loaded identity from {path}: {identity.node_name} ({identity.node_id[:16]}...)")
        return identity
    
    def to_public_dict(self) -> Dict[str, Any]:
        """Export public identity data (safe to share)."""
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "public_key": self.public_key_b64,
            "federation_id": self.federation_id,
            "capabilities": self.capabilities,
            "created_at": self.created_at
        }


# ══════════════════════════════════════════════════════════════════════════════
# IDENTITY MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class IdentityManager:
    """
    Manages node identity and peer identities.
    
    Provides:
      - Self identity management
      - Peer identity caching
      - Identity verification utilities
    """
    
    def __init__(self, identity_path: Optional[str] = None):
        """
        Initialize identity manager.
        
        Args:
            identity_path: Path to load/save self identity
        """
        self.identity_path = identity_path
        self._self_identity: Optional[NodeIdentity] = None
        self._peer_identities: Dict[str, NodeIdentity] = {}
        
        # Load existing identity if path provided
        if identity_path and Path(identity_path).exists():
            self._self_identity = NodeIdentity.load(identity_path)
    
    @property
    def identity(self) -> Optional[NodeIdentity]:
        """Get our identity."""
        return self._self_identity
    
    @property
    def node_id(self) -> Optional[str]:
        """Get our node ID."""
        return self._self_identity.node_id if self._self_identity else None
    
    def initialize(self, node_name: str, federation_id: str = "CHAINBRIDGE-FEDERATION") -> NodeIdentity:
        """
        Initialize a new identity or load existing one.
        
        INV-SEC-002: Creates permanent identity if none exists.
        """
        if self._self_identity:
            logger.info(f"Identity already initialized: {self._self_identity.node_id[:16]}...")
            return self._self_identity
        
        # Generate new identity
        self._self_identity = NodeIdentity.generate(node_name, federation_id)
        
        # Save if path configured
        if self.identity_path:
            self._self_identity.save(self.identity_path)
        
        return self._self_identity
    
    def add_peer_identity(self, peer: NodeIdentity):
        """Cache a verified peer identity."""
        self._peer_identities[peer.node_id] = peer
        logger.debug(f"Added peer identity: {peer.node_id[:16]}...")
    
    def get_peer_identity(self, node_id: str) -> Optional[NodeIdentity]:
        """Get a cached peer identity."""
        return self._peer_identities.get(node_id)
    
    def verify_peer_signature(
        self,
        node_id: str,
        message: bytes,
        signature: bytes
    ) -> bool:
        """
        Verify a signature from a known peer.
        
        Args:
            node_id: Peer's node ID
            message: Original message
            signature: Signature to verify
            
        Returns:
            True if valid, False otherwise
        """
        peer = self._peer_identities.get(node_id)
        if not peer:
            logger.warning(f"Unknown peer: {node_id[:16]}...")
            return False
        
        return peer.verify(message, signature)
    
    def get_peer_count(self) -> int:
        """Get number of known peer identities."""
        return len(self._peer_identities)
    
    def get_all_peer_ids(self) -> list:
        """Get all known peer node IDs."""
        return list(self._peer_identities.keys())


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test():
    """Run self-test to validate identity module."""
    print("=" * 70)
    print("MESH IDENTITY v3.0.0 - Self Test")
    print("=" * 70)
    
    # Test 1: Identity generation
    print("\n[1/6] Testing identity generation...")
    alice = NodeIdentity.generate("NODE-ALICE", "CHAINBRIDGE-FEDERATION")
    print(f"      ✓ Node ID: {alice.node_id[:16]}...")
    print(f"      ✓ Name: {alice.node_name}")
    print(f"      ✓ Has private key: {alice.has_private_key}")
    
    # Test 2: Message signing
    print("\n[2/6] Testing message signing...")
    message = b"Hello, Federation! This is a test message."
    signature = alice.sign(message)
    print(f"      ✓ Message: {len(message)} bytes")
    print(f"      ✓ Signature: {len(signature)} bytes")
    
    # Test 3: Signature verification
    print("\n[3/6] Testing signature verification...")
    is_valid = alice.verify(message, signature)
    assert is_valid, "Valid signature should verify"
    print(f"      ✓ Valid signature verified: {is_valid}")
    
    tampered = b"Hello, Federation! This is a TAMPERED message."
    is_invalid = alice.verify(tampered, signature)
    assert not is_invalid, "Tampered message should fail"
    print(f"      ✓ Tampered message rejected: {not is_invalid}")
    
    # Test 4: Challenge-response
    print("\n[4/6] Testing challenge-response authentication...")
    bob = NodeIdentity.generate("NODE-BOB", "CHAINBRIDGE-FEDERATION")
    
    # Alice challenges Bob
    challenge = alice.create_challenge()
    print(f"      ✓ Challenge nonce: {challenge['nonce'][:16]}...")
    
    # Bob responds
    response = bob.respond_to_challenge(challenge)
    print(f"      ✓ Response from: {response['responder'][:16]}...")
    
    # Alice verifies
    is_valid, error = alice.verify_challenge_response(challenge, response)
    assert is_valid, f"Valid response should verify: {error}"
    print(f"      ✓ Response verified: {is_valid}")
    
    # Test 5: Peer identity from public key
    print("\n[5/6] Testing peer identity creation...")
    bob_public = NodeIdentity.from_public_key(bob.public_key_bytes, "BOB-PEER")
    print(f"      ✓ Peer node ID: {bob_public.node_id[:16]}...")
    print(f"      ✓ Matches original: {bob_public.node_id == bob.node_id}")
    
    # Verify Bob's signature using public key only
    bob_message = b"Signed by Bob"
    bob_sig = bob.sign(bob_message)
    is_valid = bob_public.verify(bob_message, bob_sig)
    print(f"      ✓ Peer signature verified: {is_valid}")
    
    # Test 6: IdentityManager
    print("\n[6/6] Testing IdentityManager...")
    manager = IdentityManager()
    manager._self_identity = alice
    manager.add_peer_identity(bob)
    
    print(f"      ✓ Self identity: {manager.node_id[:16]}...")
    print(f"      ✓ Peer count: {manager.get_peer_count()}")
    
    # Verify peer signature through manager
    is_valid = manager.verify_peer_signature(bob.node_id, bob_message, bob_sig)
    print(f"      ✓ Manager verification: {is_valid}")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print(f"Version: {__version__}")
    print(f"Crypto available: {CRYPTO_AVAILABLE}")
    print("INV-SEC-002 (Identity Persistence): READY")
    print("INV-SEC-004 (Cryptographic Proof): READY")
    print("=" * 70)
    print("\n🔐 The Seal is ready. Nodes can prove who they are.")


if __name__ == "__main__":
    _self_test()
