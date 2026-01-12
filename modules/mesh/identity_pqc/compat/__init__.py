#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      LEGACY COMPATIBILITY ADAPTER                            ║
║                    PAC-SEC-P819 Implementation                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Adapter layer providing backward compatibility with the legacy identity.py API.

This module allows existing code using:
    from modules.mesh.identity import NodeIdentity, IdentityManager

To transparently use:
    from modules.mesh.identity_pqc.compat import NodeIdentity, IdentityManager

With full hybrid PQC support behind the scenes.
"""

import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core import HybridIdentity, HybridKeyPair, ED25519KeyPair, PQCKeyPair
from ..signatures import HybridSignature, SignatureMode
from ..constants import (
    NODE_ID_LENGTH,
    DEFAULT_FEDERATION_ID,
    ED25519_SIGNATURE_SIZE,
)
from ..errors import NoPrivateKeyError
from ..backends.ed25519 import CryptographyED25519Backend
from ..backends.dilithium_py import DilithiumPyBackend

logger = logging.getLogger(__name__)


class NodeIdentity:
    """
    Backward-compatible NodeIdentity wrapper around HybridIdentity.
    
    Provides the same API as the legacy modules/mesh/identity.py NodeIdentity
    class while using hybrid PQC cryptography internally.
    
    Legacy API preserved:
        - generate(node_name, federation_id)
        - from_public_key(public_key_bytes, node_name)
        - sign(message) -> bytes (returns ED25519 component for compatibility)
        - verify(message, signature) -> bool
        - save(path), load(path)
        - create_challenge(), respond_to_challenge(), verify_challenge_response()
    
    New capabilities (accessed via .hybrid property):
        - Hybrid ED25519 + ML-DSA-65 signatures
        - Full HybridIdentity API
    """
    
    def __init__(
        self,
        node_id: str,
        node_name: str,
        public_key_bytes: bytes,
        private_key_bytes: Optional[bytes] = None,
        federation_id: str = DEFAULT_FEDERATION_ID,
        capabilities: Optional[List[str]] = None,
        created_at: Optional[str] = None,
        # PQC extensions
        pqc_public_key: Optional[bytes] = None,
        pqc_private_key: Optional[bytes] = None,
        _hybrid: Optional[HybridIdentity] = None,
    ):
        """
        Initialize NodeIdentity.
        
        Args:
            node_id: Node identifier
            node_name: Human-readable name
            public_key_bytes: ED25519 public key
            private_key_bytes: ED25519 private key (optional)
            federation_id: Federation ID
            capabilities: List of capabilities
            created_at: Creation timestamp
            pqc_public_key: ML-DSA-65 public key (optional)
            pqc_private_key: ML-DSA-65 private key (optional)
            _hybrid: Pre-built HybridIdentity (internal use)
        """
        self.node_id = node_id
        self.node_name = node_name
        self.public_key_bytes = public_key_bytes
        self.private_key_bytes = private_key_bytes
        self.federation_id = federation_id
        self.capabilities = capabilities or ["ATTEST", "RELAY", "GOSSIP", "PQC"]
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        
        # PQC key storage
        self._pqc_public_key = pqc_public_key
        self._pqc_private_key = pqc_private_key
        
        # Internal hybrid identity (lazy init)
        self._hybrid = _hybrid
        
        # Backends
        self._ed25519_backend = CryptographyED25519Backend()
    
    def _ensure_hybrid(self) -> HybridIdentity:
        """Ensure HybridIdentity is initialized."""
        if self._hybrid is None:
            # Build hybrid identity from components
            ed_keys = ED25519KeyPair(
                public_key=self.public_key_bytes,
                private_key=self.private_key_bytes,
            )
            
            # Generate PQC keys if we have ED25519 private key but no PQC keys
            if self.private_key_bytes and not self._pqc_public_key:
                pqc_backend = DilithiumPyBackend()
                self._pqc_public_key, self._pqc_private_key = pqc_backend.keygen()
                logger.info(f"Generated PQC keys for {self.node_id[:16]}...")
            
            if self._pqc_public_key:
                pqc_keys = PQCKeyPair(
                    public_key=self._pqc_public_key,
                    private_key=self._pqc_private_key,
                )
            else:
                # Generate minimal PQC keys for public-key-only identity
                # (verification only, cannot sign with PQC)
                pqc_backend = DilithiumPyBackend()
                pqc_pub, _ = pqc_backend.keygen()
                pqc_keys = PQCKeyPair(public_key=pqc_pub, private_key=None)
            
            self._hybrid = HybridIdentity(
                node_id=self.node_id,
                node_name=self.node_name,
                keys=HybridKeyPair(ed25519=ed_keys, pqc=pqc_keys),
                federation_id=self.federation_id,
                capabilities=self.capabilities,
                created_at=self.created_at,
            )
        
        return self._hybrid
    
    @property
    def hybrid(self) -> HybridIdentity:
        """Access the underlying HybridIdentity."""
        return self._ensure_hybrid()
    
    @property
    def public_key_b64(self) -> str:
        """Get base64-encoded public key."""
        return base64.b64encode(self.public_key_bytes).decode("ascii")
    
    @property
    def has_private_key(self) -> bool:
        """Check if this identity can sign."""
        return self.private_key_bytes is not None
    
    @classmethod
    def generate(
        cls,
        node_name: str,
        federation_id: str = DEFAULT_FEDERATION_ID,
    ) -> "NodeIdentity":
        """
        Generate a new node identity with fresh key pairs.
        
        This generates BOTH ED25519 and ML-DSA-65 key pairs for
        full hybrid signature capability.
        """
        # Generate via HybridIdentity
        hybrid = HybridIdentity.generate(node_name, federation_id)
        
        return cls(
            node_id=hybrid.node_id,
            node_name=hybrid.node_name,
            public_key_bytes=hybrid.keys.ed25519.public_key,
            private_key_bytes=hybrid.keys.ed25519.private_key,
            federation_id=hybrid.federation_id,
            capabilities=hybrid.capabilities,
            created_at=hybrid.created_at,
            pqc_public_key=hybrid.keys.pqc.public_key,
            pqc_private_key=hybrid.keys.pqc.private_key,
            _hybrid=hybrid,
        )
    
    @classmethod
    def from_public_key(
        cls,
        public_key_bytes: bytes,
        node_name: str = "PEER",
    ) -> "NodeIdentity":
        """Create identity from public key only (for peers)."""
        node_id = hashlib.sha256(public_key_bytes).hexdigest()[:NODE_ID_LENGTH]
        return cls(
            node_id=node_id,
            node_name=node_name,
            public_key_bytes=public_key_bytes,
            private_key_bytes=None,
        )
    
    # ──────────────────────────────────────────────────────────────────────────
    # SIGNING & VERIFICATION (Legacy API)
    # ──────────────────────────────────────────────────────────────────────────
    
    def sign(self, message: bytes) -> bytes:
        """
        Sign a message.
        
        For backward compatibility, returns ED25519 signature only (64 bytes).
        Use sign_hybrid() for full hybrid signature.
        """
        if not self.has_private_key:
            raise ValueError("Cannot sign: no private key")
        
        return self._ed25519_backend.sign(self.private_key_bytes, message)
    
    def sign_hybrid(self, message: bytes) -> bytes:
        """
        Sign with full hybrid signature.
        
        Returns serialized HybridSignature bytes.
        """
        hybrid = self._ensure_hybrid()
        signature = hybrid.sign(message)
        return signature.to_bytes()
    
    def sign_dict(self, data: Dict[str, Any]) -> str:
        """Sign a dictionary (JSON-serialized)."""
        message = json.dumps(data, sort_keys=True).encode("utf-8")
        signature = self.sign(message)
        return base64.b64encode(signature).decode("ascii")
    
    def verify(self, message: bytes, signature: bytes) -> bool:
        """
        Verify a signature.
        
        Handles both legacy ED25519 (64 bytes) and hybrid signatures.
        """
        # Detect signature type by size
        if len(signature) == ED25519_SIGNATURE_SIZE:
            # Legacy ED25519 signature
            return self._ed25519_backend.verify(
                self.public_key_bytes, message, signature
            )
        else:
            # Try as hybrid signature
            try:
                hybrid_sig = HybridSignature.from_bytes(signature)
                hybrid = self._ensure_hybrid()
                return hybrid.verify(message, hybrid_sig)
            except Exception:
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
        signature: bytes,
    ) -> bool:
        """Verify a peer's signature given their public key."""
        peer = NodeIdentity.from_public_key(public_key_bytes)
        return peer.verify(message, signature)
    
    # ──────────────────────────────────────────────────────────────────────────
    # CHALLENGE-RESPONSE
    # ──────────────────────────────────────────────────────────────────────────
    
    def create_challenge(self) -> Dict[str, Any]:
        """Create a challenge for peer authentication."""
        import secrets
        return {
            "type": "IDENTITY_CHALLENGE",
            "challenger": self.node_id,
            "nonce": secrets.token_hex(32),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "federation_id": self.federation_id,
        }
    
    def respond_to_challenge(self, challenge: Dict[str, Any]) -> Dict[str, Any]:
        """Respond to an identity challenge."""
        if not self.has_private_key:
            raise ValueError("Cannot respond: no private key")
        
        response = {
            "type": "IDENTITY_RESPONSE",
            "responder": self.node_id,
            "responder_name": self.node_name,
            "public_key": self.public_key_b64,
            "challenge_nonce": challenge["nonce"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capabilities": self.capabilities,
        }
        
        response["signature"] = self.sign_dict(response)
        return response
    
    def verify_challenge_response(
        self,
        original_challenge: Dict[str, Any],
        response: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """Verify a challenge response from a peer."""
        try:
            if response.get("challenge_nonce") != original_challenge.get("nonce"):
                return False, "Nonce mismatch"
            
            public_key_b64 = response.get("public_key")
            if not public_key_b64:
                return False, "Missing public key"
            
            public_key_bytes = base64.b64decode(public_key_b64)
            
            expected_node_id = hashlib.sha256(public_key_bytes).hexdigest()[:NODE_ID_LENGTH]
            if response.get("responder") != expected_node_id:
                return False, "Node ID does not match public key"
            
            signature_b64 = response.pop("signature", None)
            if not signature_b64:
                return False, "Missing signature"
            
            peer = NodeIdentity.from_public_key(public_key_bytes)
            if not peer.verify_dict(response, signature_b64):
                return False, "Invalid signature"
            
            response["signature"] = signature_b64
            return True, None
            
        except Exception as e:
            return False, f"Verification error: {e}"
    
    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────
    
    def save(self, path: str, include_private_key: bool = True):
        """Save identity to disk."""
        hybrid = self._ensure_hybrid()
        hybrid.save(path, include_private_keys=include_private_key)
    
    @classmethod
    def load(cls, path: str) -> "NodeIdentity":
        """Load identity from disk."""
        # Try loading as hybrid first
        try:
            with open(path, "r") as f:
                data = json.load(f)
            
            if data.get("format") == "HYBRID_ED25519_MLDSA65":
                # Load as hybrid
                hybrid = HybridIdentity.load(path)
                return cls(
                    node_id=hybrid.node_id,
                    node_name=hybrid.node_name,
                    public_key_bytes=hybrid.keys.ed25519.public_key,
                    private_key_bytes=hybrid.keys.ed25519.private_key,
                    federation_id=hybrid.federation_id,
                    capabilities=hybrid.capabilities,
                    created_at=hybrid.created_at,
                    pqc_public_key=hybrid.keys.pqc.public_key,
                    pqc_private_key=hybrid.keys.pqc.private_key,
                    _hybrid=hybrid,
                )
            else:
                # Legacy format
                public_key_bytes = base64.b64decode(data["public_key"])
                private_key_bytes = None
                if "private_key" in data:
                    private_key_bytes = base64.b64decode(data["private_key"])
                
                return cls(
                    node_id=data["node_id"],
                    node_name=data["node_name"],
                    public_key_bytes=public_key_bytes,
                    private_key_bytes=private_key_bytes,
                    federation_id=data.get("federation_id", DEFAULT_FEDERATION_ID),
                    capabilities=data.get("capabilities", ["ATTEST", "RELAY", "GOSSIP"]),
                    created_at=data.get("created_at"),
                )
        except Exception as e:
            raise ValueError(f"Failed to load identity: {e}")
    
    def to_public_dict(self) -> Dict[str, Any]:
        """Export public identity data (safe to share)."""
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "public_key": self.public_key_b64,
            "federation_id": self.federation_id,
            "capabilities": self.capabilities,
            "created_at": self.created_at,
        }


class IdentityManager:
    """
    Backward-compatible IdentityManager.
    
    Manages node identity and peer identities with PQC support.
    """
    
    def __init__(self, identity_path: Optional[str] = None):
        """Initialize identity manager."""
        self.identity_path = identity_path
        self._self_identity: Optional[NodeIdentity] = None
        self._peer_identities: Dict[str, NodeIdentity] = {}
        
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
    
    def initialize(
        self,
        node_name: str,
        federation_id: str = DEFAULT_FEDERATION_ID,
    ) -> NodeIdentity:
        """Initialize a new identity or load existing one."""
        if self._self_identity:
            return self._self_identity
        
        self._self_identity = NodeIdentity.generate(node_name, federation_id)
        
        if self.identity_path:
            self._self_identity.save(self.identity_path)
        
        return self._self_identity
    
    def add_peer_identity(self, peer: NodeIdentity):
        """Cache a verified peer identity."""
        self._peer_identities[peer.node_id] = peer
    
    def get_peer_identity(self, node_id: str) -> Optional[NodeIdentity]:
        """Get a cached peer identity."""
        return self._peer_identities.get(node_id)
    
    def verify_peer_signature(
        self,
        node_id: str,
        message: bytes,
        signature: bytes,
    ) -> bool:
        """Verify a signature from a known peer."""
        peer = self._peer_identities.get(node_id)
        if not peer:
            return False
        return peer.verify(message, signature)
    
    def get_peer_count(self) -> int:
        """Get number of known peer identities."""
        return len(self._peer_identities)
    
    def get_all_peer_ids(self) -> list:
        """Get all known peer node IDs."""
        return list(self._peer_identities.keys())
