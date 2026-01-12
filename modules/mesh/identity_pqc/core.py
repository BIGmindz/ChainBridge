#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      HYBRID IDENTITY CORE                                    ║
║                    PAC-SEC-P819 Implementation                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Core HybridIdentity class implementing ED25519 + ML-DSA-65 cryptographic identity.

This module provides:
  - HybridKeyPair: Combined ED25519 + ML-DSA-65 key pair
  - HybridIdentity: Full node identity with hybrid cryptography
  - Full backward compatibility with legacy ED25519 identities

INVARIANTS:
  INV-SEC-002: Node ID is permanent (derived from ED25519 key for continuity)
  INV-SEC-004: All identity claims must be cryptographically verifiable
  INV-SEC-P819-001: Private key material NEVER appears in logs
"""

import base64
import hashlib
import json
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    VERSION,
    FORMAT_VERSION,
    SignatureMode,
    DEFAULT_SIGNATURE_MODE,
    DEFAULT_FEDERATION_ID,
    DEFAULT_CAPABILITIES,
    NODE_ID_LENGTH,
    IDENTITY_FILE_MODE,
    ED25519_PUBLIC_KEY_SIZE,
    ED25519_PRIVATE_KEY_SIZE,
    MLDSA65_PUBLIC_KEY_SIZE,
    MLDSA65_PRIVATE_KEY_SIZE,
    CHALLENGE_NONCE_SIZE,
    CHALLENGE_TIMEOUT_SECONDS,
    SIGNATURE_MODE_HYBRID,
    SIGNATURE_MODE_LEGACY,
)
from .signatures import HybridSignature, HybridSigner, HybridVerifier
from .errors import (
    KeyGenerationError,
    NoPrivateKeyError,
    SerializationError,
    MissingFieldError,
    CorruptedDataError,
    ValidationError,
    InvalidNodeNameError,
)
from .backends.ed25519 import CryptographyED25519Backend, is_available as ed25519_available
from .backends.dilithium_py import DilithiumPyBackend, is_available as pqc_available

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# KEY PAIR CLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ED25519KeyPair:
    """ED25519 key pair container."""
    public_key: bytes
    private_key: Optional[bytes] = None
    
    def __post_init__(self):
        if len(self.public_key) != ED25519_PUBLIC_KEY_SIZE:
            raise ValidationError(f"Invalid ED25519 public key size: {len(self.public_key)}")
        if self.private_key and len(self.private_key) != ED25519_PRIVATE_KEY_SIZE:
            raise ValidationError(f"Invalid ED25519 private key size: {len(self.private_key)}")
    
    @property
    def has_private_key(self) -> bool:
        return self.private_key is not None
    
    @property
    def public_key_b64(self) -> str:
        return base64.b64encode(self.public_key).decode("ascii")
    
    def __repr__(self) -> str:
        # SECURITY: Never expose key material in repr
        return f"ED25519KeyPair(has_private_key={self.has_private_key})"


@dataclass
class PQCKeyPair:
    """ML-DSA-65 key pair container."""
    public_key: bytes
    private_key: Optional[bytes] = None
    
    def __post_init__(self):
        if len(self.public_key) != MLDSA65_PUBLIC_KEY_SIZE:
            raise ValidationError(f"Invalid ML-DSA-65 public key size: {len(self.public_key)}")
        if self.private_key and len(self.private_key) != MLDSA65_PRIVATE_KEY_SIZE:
            raise ValidationError(f"Invalid ML-DSA-65 private key size: {len(self.private_key)}")
    
    @property
    def has_private_key(self) -> bool:
        return self.private_key is not None
    
    @property
    def public_key_b64(self) -> str:
        return base64.b64encode(self.public_key).decode("ascii")
    
    def __repr__(self) -> str:
        # SECURITY: Never expose key material in repr
        return f"PQCKeyPair(has_private_key={self.has_private_key})"


@dataclass
class HybridKeyPair:
    """
    Combined ED25519 + ML-DSA-65 key pair.
    
    Both key pairs are generated together and must be used together
    for hybrid signatures.
    """
    ed25519: ED25519KeyPair
    pqc: PQCKeyPair
    
    @property
    def has_private_keys(self) -> bool:
        return self.ed25519.has_private_key and self.pqc.has_private_key
    
    @property
    def has_ed25519_private(self) -> bool:
        return self.ed25519.has_private_key
    
    @property
    def has_pqc_private(self) -> bool:
        return self.pqc.has_private_key
    
    def __repr__(self) -> str:
        return f"HybridKeyPair(ed25519={self.ed25519}, pqc={self.pqc})"


# ══════════════════════════════════════════════════════════════════════════════
# HYBRID IDENTITY
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class HybridIdentity:
    """
    Hybrid cryptographic identity for a mesh node.
    
    Combines ED25519 (classical) and ML-DSA-65 (post-quantum) cryptography
    for quantum-resistant identity and signatures.
    
    Attributes:
        node_id: Unique node identifier (SHA256 of ED25519 public key)
        node_name: Human-readable node name
        keys: HybridKeyPair containing both key pairs
        federation_id: Federation this node belongs to
        capabilities: List of node capabilities
        created_at: ISO 8601 creation timestamp
        signature_mode: Default signature mode
    
    INV-SEC-002: Node ID is permanent and derived from ED25519 key.
    """
    
    node_id: str
    node_name: str
    keys: HybridKeyPair
    federation_id: str = DEFAULT_FEDERATION_ID
    capabilities: List[str] = field(default_factory=lambda: list(DEFAULT_CAPABILITIES))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    signature_mode: SignatureMode = SignatureMode.HYBRID
    
    # Runtime backends (not serialized)
    _ed25519_backend: Any = field(default=None, repr=False)
    _pqc_backend: Any = field(default=None, repr=False)
    _signer: Any = field(default=None, repr=False)
    _verifier: Any = field(default=None, repr=False)
    
    def __post_init__(self):
        """Initialize cryptographic backends."""
        self._init_backends()
    
    def _init_backends(self):
        """Initialize crypto backends and signer/verifier."""
        if ed25519_available():
            self._ed25519_backend = CryptographyED25519Backend()
        if pqc_available():
            self._pqc_backend = DilithiumPyBackend()
        
        if self._ed25519_backend and self._pqc_backend:
            self._signer = HybridSigner(
                self._ed25519_backend,
                self._pqc_backend,
                default_mode=self.signature_mode,
            )
            self._verifier = HybridVerifier(
                self._ed25519_backend,
                self._pqc_backend,
            )
    
    @classmethod
    def generate(
        cls,
        node_name: str,
        federation_id: str = DEFAULT_FEDERATION_ID,
        signature_mode: SignatureMode = SignatureMode.HYBRID,
    ) -> "HybridIdentity":
        """
        Generate a new hybrid identity with fresh key pairs.
        
        Args:
            node_name: Human-readable node name
            federation_id: Federation identifier
            signature_mode: Default signature mode
            
        Returns:
            New HybridIdentity instance
            
        Raises:
            KeyGenerationError: If key generation fails
            ValidationError: If node_name is invalid
        """
        # Validate node name
        if not node_name or len(node_name) > 256:
            raise InvalidNodeNameError("Node name must be 1-256 characters")
        
        # Initialize backends
        ed25519_backend = CryptographyED25519Backend()
        pqc_backend = DilithiumPyBackend()
        
        # Generate ED25519 key pair
        ed_public, ed_private = ed25519_backend.keygen()
        ed25519_keys = ED25519KeyPair(public_key=ed_public, private_key=ed_private)
        
        # Generate ML-DSA-65 key pair
        pqc_public, pqc_private = pqc_backend.keygen()
        pqc_keys = PQCKeyPair(public_key=pqc_public, private_key=pqc_private)
        
        # Create hybrid key pair
        hybrid_keys = HybridKeyPair(ed25519=ed25519_keys, pqc=pqc_keys)
        
        # Derive node ID from ED25519 public key (for backward compatibility)
        node_id = hashlib.sha256(ed_public).hexdigest()[:NODE_ID_LENGTH]
        
        identity = cls(
            node_id=node_id,
            node_name=node_name,
            keys=hybrid_keys,
            federation_id=federation_id,
            signature_mode=signature_mode,
        )
        
        logger.info(f"Generated hybrid identity: {node_name} ({node_id[:16]}...)")
        return identity
    
    @classmethod
    def from_public_keys(
        cls,
        ed25519_public: bytes,
        pqc_public: bytes,
        node_name: str = "PEER",
    ) -> "HybridIdentity":
        """
        Create identity from public keys only (for peer verification).
        
        Args:
            ed25519_public: ED25519 public key bytes
            pqc_public: ML-DSA-65 public key bytes
            node_name: Node name (default "PEER")
            
        Returns:
            HybridIdentity with public keys only (cannot sign)
        """
        ed25519_keys = ED25519KeyPair(public_key=ed25519_public)
        pqc_keys = PQCKeyPair(public_key=pqc_public)
        hybrid_keys = HybridKeyPair(ed25519=ed25519_keys, pqc=pqc_keys)
        
        node_id = hashlib.sha256(ed25519_public).hexdigest()[:NODE_ID_LENGTH]
        
        return cls(
            node_id=node_id,
            node_name=node_name,
            keys=hybrid_keys,
        )
    
    # ──────────────────────────────────────────────────────────────────────────
    # PROPERTIES
    # ──────────────────────────────────────────────────────────────────────────
    
    @property
    def has_private_keys(self) -> bool:
        """Check if this identity can sign (has private keys)."""
        return self.keys.has_private_keys
    
    @property
    def ed25519_public_key(self) -> bytes:
        """Get ED25519 public key bytes."""
        return self.keys.ed25519.public_key
    
    @property
    def pqc_public_key(self) -> bytes:
        """Get ML-DSA-65 public key bytes."""
        return self.keys.pqc.public_key
    
    @property
    def ed25519_public_key_b64(self) -> str:
        """Get base64-encoded ED25519 public key."""
        return self.keys.ed25519.public_key_b64
    
    @property
    def pqc_public_key_b64(self) -> str:
        """Get base64-encoded ML-DSA-65 public key."""
        return self.keys.pqc.public_key_b64
    
    # ──────────────────────────────────────────────────────────────────────────
    # SIGNING
    # ──────────────────────────────────────────────────────────────────────────
    
    def sign(
        self,
        message: bytes,
        mode: Optional[SignatureMode] = None,
    ) -> HybridSignature:
        """
        Sign a message with hybrid signature.
        
        Args:
            message: Raw bytes to sign
            mode: Signature mode (default: instance signature_mode)
            
        Returns:
            HybridSignature instance
            
        Raises:
            NoPrivateKeyError: If no private keys available
        """
        if not self.has_private_keys:
            raise NoPrivateKeyError()
        
        mode = mode or self.signature_mode
        
        return self._signer.sign(
            ed25519_private_key=self.keys.ed25519.private_key,
            pqc_private_key=self.keys.pqc.private_key,
            message=message,
            mode=mode,
        )
    
    def sign_bytes(self, message: bytes) -> bytes:
        """
        Sign and return raw signature bytes (for wire format).
        
        Args:
            message: Raw bytes to sign
            
        Returns:
            Serialized hybrid signature bytes
        """
        signature = self.sign(message)
        return signature.to_bytes()
    
    def sign_dict(self, data: Dict[str, Any]) -> str:
        """
        Sign a dictionary (JSON-serialized).
        
        Args:
            data: Dictionary to sign
            
        Returns:
            Base64-encoded hybrid signature
        """
        message = json.dumps(data, sort_keys=True).encode("utf-8")
        signature = self.sign(message)
        return base64.b64encode(signature.to_bytes()).decode("ascii")
    
    # ──────────────────────────────────────────────────────────────────────────
    # VERIFICATION
    # ──────────────────────────────────────────────────────────────────────────
    
    def verify(self, message: bytes, signature: HybridSignature) -> bool:
        """
        Verify a hybrid signature against our public keys.
        
        Args:
            message: Original message bytes
            signature: HybridSignature to verify
            
        Returns:
            True if valid, False otherwise
        """
        return self._verifier.verify(
            ed25519_public_key=self.keys.ed25519.public_key,
            pqc_public_key=self.keys.pqc.public_key,
            message=message,
            signature=signature,
        )
    
    def verify_bytes(self, message: bytes, signature_bytes: bytes) -> bool:
        """
        Verify raw signature bytes.
        
        Args:
            message: Original message bytes
            signature_bytes: Serialized signature bytes
            
        Returns:
            True if valid, False otherwise
        """
        try:
            signature = HybridSignature.from_bytes(signature_bytes)
            return self.verify(message, signature)
        except Exception as e:
            logger.warning(f"Signature deserialization failed: {e}")
            return False
    
    def verify_dict(self, data: Dict[str, Any], signature_b64: str) -> bool:
        """
        Verify a signed dictionary.
        
        Args:
            data: Original dictionary
            signature_b64: Base64-encoded signature
            
        Returns:
            True if valid, False otherwise
        """
        try:
            message = json.dumps(data, sort_keys=True).encode("utf-8")
            signature_bytes = base64.b64decode(signature_b64)
            return self.verify_bytes(message, signature_bytes)
        except Exception as e:
            logger.warning(f"Dict verification failed: {e}")
            return False
    
    @staticmethod
    def verify_peer(
        ed25519_public: bytes,
        pqc_public: bytes,
        message: bytes,
        signature: HybridSignature,
    ) -> bool:
        """
        Static method to verify a peer's signature.
        
        Args:
            ed25519_public: Peer's ED25519 public key
            pqc_public: Peer's ML-DSA-65 public key
            message: Original message
            signature: Signature to verify
            
        Returns:
            True if valid, False otherwise
        """
        peer = HybridIdentity.from_public_keys(ed25519_public, pqc_public)
        return peer.verify(message, signature)
    
    # ──────────────────────────────────────────────────────────────────────────
    # CHALLENGE-RESPONSE
    # ──────────────────────────────────────────────────────────────────────────
    
    def create_challenge(self) -> Dict[str, Any]:
        """
        Create a challenge for peer authentication.
        
        Returns:
            Challenge dictionary to send to peer
        """
        return {
            "type": "IDENTITY_CHALLENGE_V4",
            "challenger": self.node_id,
            "nonce": secrets.token_hex(CHALLENGE_NONCE_SIZE),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "federation_id": self.federation_id,
            "required_mode": self.signature_mode.to_string(),
        }
    
    def respond_to_challenge(self, challenge: Dict[str, Any]) -> Dict[str, Any]:
        """
        Respond to an identity challenge.
        
        Args:
            challenge: Challenge dictionary from peer
            
        Returns:
            Response dictionary with signature
            
        Raises:
            NoPrivateKeyError: If no private keys
        """
        if not self.has_private_keys:
            raise NoPrivateKeyError("Cannot respond: no private keys")
        
        response = {
            "type": "IDENTITY_RESPONSE_V4",
            "responder": self.node_id,
            "responder_name": self.node_name,
            "ed25519_public_key": self.ed25519_public_key_b64,
            "pqc_public_key": self.pqc_public_key_b64,
            "challenge_nonce": challenge["nonce"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capabilities": self.capabilities,
            "signature_mode": self.signature_mode.to_string(),
        }
        
        response["signature"] = self.sign_dict(response)
        return response
    
    def verify_challenge_response(
        self,
        original_challenge: Dict[str, Any],
        response: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify a challenge response from a peer.
        
        Args:
            original_challenge: Original challenge sent
            response: Response from peer
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check nonce matches
            if response.get("challenge_nonce") != original_challenge.get("nonce"):
                return False, "Nonce mismatch"
            
            # Extract public keys
            ed_key_b64 = response.get("ed25519_public_key")
            pqc_key_b64 = response.get("pqc_public_key")
            
            if not ed_key_b64 or not pqc_key_b64:
                return False, "Missing public keys"
            
            ed_public = base64.b64decode(ed_key_b64)
            pqc_public = base64.b64decode(pqc_key_b64)
            
            # Verify node_id matches ED25519 public key
            expected_node_id = hashlib.sha256(ed_public).hexdigest()[:NODE_ID_LENGTH]
            if response.get("responder") != expected_node_id:
                return False, "Node ID does not match public key"
            
            # Extract and verify signature
            signature_b64 = response.pop("signature", None)
            if not signature_b64:
                return False, "Missing signature"
            
            peer = HybridIdentity.from_public_keys(ed_public, pqc_public)
            if not peer.verify_dict(response, signature_b64):
                return False, "Invalid signature"
            
            # Restore signature
            response["signature"] = signature_b64
            return True, None
            
        except Exception as e:
            return False, f"Verification error: {e}"
    
    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────
    
    def save(self, path: str, include_private_keys: bool = True):
        """
        Save identity to disk.
        
        Args:
            path: File path for identity JSON
            include_private_keys: Whether to include private keys
            
        Raises:
            SerializationError: If save fails
        """
        data = {
            "version": VERSION,
            "format": "HYBRID_ED25519_MLDSA65",
            "format_version": FORMAT_VERSION,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "federation_id": self.federation_id,
            "capabilities": self.capabilities,
            "created_at": self.created_at,
            "signature_mode": self.signature_mode.to_string(),
            "keys": {
                "ed25519": {
                    "public": self.ed25519_public_key_b64,
                },
                "mldsa65": {
                    "public": self.pqc_public_key_b64,
                },
            },
        }
        
        if include_private_keys and self.has_private_keys:
            data["keys"]["ed25519"]["private"] = base64.b64encode(
                self.keys.ed25519.private_key
            ).decode("ascii")
            data["keys"]["mldsa65"]["private"] = base64.b64encode(
                self.keys.pqc.private_key
            ).decode("ascii")
        
        # Ensure directory exists
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        
        # Set secure permissions
        os.chmod(path, IDENTITY_FILE_MODE)
        
        logger.info(f"Saved hybrid identity to {path}")
    
    @classmethod
    def load(cls, path: str) -> "HybridIdentity":
        """
        Load identity from disk.
        
        Args:
            path: File path to identity JSON
            
        Returns:
            HybridIdentity instance
            
        Raises:
            SerializationError: If load fails
        """
        with open(path, "r") as f:
            data = json.load(f)
        
        # Validate required fields
        required = ["node_id", "node_name", "keys"]
        for field in required:
            if field not in data:
                raise MissingFieldError(field)
        
        # Extract keys
        keys_data = data["keys"]
        
        ed_public = base64.b64decode(keys_data["ed25519"]["public"])
        ed_private = None
        if "private" in keys_data["ed25519"]:
            ed_private = base64.b64decode(keys_data["ed25519"]["private"])
        
        pqc_public = base64.b64decode(keys_data["mldsa65"]["public"])
        pqc_private = None
        if "private" in keys_data["mldsa65"]:
            pqc_private = base64.b64decode(keys_data["mldsa65"]["private"])
        
        # Build key pairs
        ed25519_keys = ED25519KeyPair(public_key=ed_public, private_key=ed_private)
        pqc_keys = PQCKeyPair(public_key=pqc_public, private_key=pqc_private)
        hybrid_keys = HybridKeyPair(ed25519=ed25519_keys, pqc=pqc_keys)
        
        # Parse signature mode
        mode_str = data.get("signature_mode", SIGNATURE_MODE_HYBRID)
        try:
            sig_mode = SignatureMode.from_string(mode_str)
        except ValueError:
            sig_mode = SignatureMode.HYBRID
        
        identity = cls(
            node_id=data["node_id"],
            node_name=data["node_name"],
            keys=hybrid_keys,
            federation_id=data.get("federation_id", DEFAULT_FEDERATION_ID),
            capabilities=data.get("capabilities", list(DEFAULT_CAPABILITIES)),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            signature_mode=sig_mode,
        )
        
        logger.info(f"Loaded hybrid identity from {path}: {identity.node_name}")
        return identity
    
    def to_public_dict(self) -> Dict[str, Any]:
        """
        Export public identity data (safe to share).
        
        Returns:
            Dictionary with public identity information
        """
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "ed25519_public_key": self.ed25519_public_key_b64,
            "pqc_public_key": self.pqc_public_key_b64,
            "federation_id": self.federation_id,
            "capabilities": self.capabilities,
            "created_at": self.created_at,
            "signature_mode": self.signature_mode.to_string(),
        }
    
    def __repr__(self) -> str:
        return (
            f"HybridIdentity(node_id={self.node_id[:16]}..., "
            f"node_name={self.node_name}, "
            f"has_private_keys={self.has_private_keys})"
        )
