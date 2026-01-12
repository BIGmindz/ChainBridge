#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  PAC-SEC-P819: CORE MODULE TESTS                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Tests for HybridIdentity, HybridKeyPair, and related core classes.
"""

import pytest
import hashlib
from datetime import datetime

from modules.mesh.identity_pqc import (
    HybridIdentity,
    HybridKeyPair,
    ED25519KeyPair,
    PQCKeyPair,
    SignatureMode,
)
from modules.mesh.identity_pqc.constants import (
    ED25519_PUBLIC_KEY_SIZE,
    ED25519_PRIVATE_KEY_SIZE,
    MLDSA65_PUBLIC_KEY_SIZE,
    MLDSA65_PRIVATE_KEY_SIZE,
    NODE_ID_LENGTH,
    DEFAULT_FEDERATION_ID,
)
from modules.mesh.identity_pqc.errors import (
    ValidationError,
    InvalidNodeNameError,
)


class TestED25519KeyPair:
    """Tests for ED25519KeyPair dataclass."""
    
    def test_create_with_valid_keys(self, ed25519_keypair):
        """Test creating keypair with valid keys."""
        assert len(ed25519_keypair.public_key) == ED25519_PUBLIC_KEY_SIZE
        assert len(ed25519_keypair.private_key) == ED25519_PRIVATE_KEY_SIZE
        assert ed25519_keypair.has_private_key is True
    
    def test_create_public_only(self, ed25519_backend):
        """Test creating keypair with public key only."""
        public, _ = ed25519_backend.keygen()
        keypair = ED25519KeyPair(public_key=public)
        
        assert keypair.has_private_key is False
        assert len(keypair.public_key) == ED25519_PUBLIC_KEY_SIZE
    
    def test_invalid_public_key_size(self):
        """Test rejection of invalid public key size."""
        with pytest.raises(ValidationError):
            ED25519KeyPair(public_key=b"too_short")
    
    def test_invalid_private_key_size(self, ed25519_backend):
        """Test rejection of invalid private key size."""
        public, _ = ed25519_backend.keygen()
        with pytest.raises(ValidationError):
            ED25519KeyPair(public_key=public, private_key=b"too_short")
    
    def test_public_key_b64(self, ed25519_keypair):
        """Test base64 encoding of public key."""
        b64 = ed25519_keypair.public_key_b64
        assert isinstance(b64, str)
        assert len(b64) > 0
    
    def test_repr_no_key_exposure(self, ed25519_keypair):
        """Test that repr doesn't expose key material."""
        repr_str = repr(ed25519_keypair)
        assert "has_private_key" in repr_str
        # Should not contain actual key bytes
        assert ed25519_keypair.public_key.hex() not in repr_str


class TestPQCKeyPair:
    """Tests for PQCKeyPair dataclass."""
    
    def test_create_with_valid_keys(self, pqc_keypair):
        """Test creating keypair with valid keys."""
        assert len(pqc_keypair.public_key) == MLDSA65_PUBLIC_KEY_SIZE
        assert len(pqc_keypair.private_key) == MLDSA65_PRIVATE_KEY_SIZE
        assert pqc_keypair.has_private_key is True
    
    def test_create_public_only(self, pqc_backend):
        """Test creating keypair with public key only."""
        public, _ = pqc_backend.keygen()
        keypair = PQCKeyPair(public_key=public)
        
        assert keypair.has_private_key is False
        assert len(keypair.public_key) == MLDSA65_PUBLIC_KEY_SIZE
    
    def test_invalid_public_key_size(self):
        """Test rejection of invalid public key size."""
        with pytest.raises(ValidationError):
            PQCKeyPair(public_key=b"too_short")


class TestHybridKeyPair:
    """Tests for HybridKeyPair dataclass."""
    
    def test_create_hybrid_keypair(self, hybrid_keypair):
        """Test creating hybrid keypair."""
        assert hybrid_keypair.has_private_keys is True
        assert hybrid_keypair.has_ed25519_private is True
        assert hybrid_keypair.has_pqc_private is True
    
    def test_partial_private_keys(self, ed25519_keypair, pqc_backend):
        """Test hybrid keypair with partial private keys."""
        public, _ = pqc_backend.keygen()
        pqc = PQCKeyPair(public_key=public)  # No private key
        
        hybrid = HybridKeyPair(ed25519=ed25519_keypair, pqc=pqc)
        
        assert hybrid.has_private_keys is False
        assert hybrid.has_ed25519_private is True
        assert hybrid.has_pqc_private is False


class TestHybridIdentityGeneration:
    """Tests for HybridIdentity.generate()."""
    
    def test_generate_identity(self):
        """Test generating a new hybrid identity."""
        identity = HybridIdentity.generate("TEST-NODE")
        
        assert identity.node_name == "TEST-NODE"
        assert len(identity.node_id) == NODE_ID_LENGTH
        assert identity.has_private_keys is True
        assert identity.federation_id == DEFAULT_FEDERATION_ID
        assert "PQC" in identity.capabilities
    
    def test_generate_with_custom_federation(self):
        """Test generating identity with custom federation."""
        identity = HybridIdentity.generate("TEST-NODE", federation_id="CUSTOM-FED")
        
        assert identity.federation_id == "CUSTOM-FED"
    
    def test_generate_unique_identities(self):
        """Test that each generation produces unique identity."""
        id1 = HybridIdentity.generate("NODE-1")
        id2 = HybridIdentity.generate("NODE-2")
        
        assert id1.node_id != id2.node_id
        assert id1.ed25519_public_key != id2.ed25519_public_key
        assert id1.pqc_public_key != id2.pqc_public_key
    
    def test_node_id_derived_from_ed25519(self):
        """Test that node ID is derived from ED25519 public key."""
        identity = HybridIdentity.generate("TEST-NODE")
        
        expected_id = hashlib.sha256(identity.ed25519_public_key).hexdigest()[:NODE_ID_LENGTH]
        assert identity.node_id == expected_id
    
    def test_empty_node_name_rejected(self):
        """Test that empty node name is rejected."""
        with pytest.raises(InvalidNodeNameError):
            HybridIdentity.generate("")
    
    def test_long_node_name_rejected(self):
        """Test that excessively long node name is rejected."""
        with pytest.raises(InvalidNodeNameError):
            HybridIdentity.generate("X" * 300)
    
    def test_signature_mode_default(self):
        """Test default signature mode is HYBRID."""
        identity = HybridIdentity.generate("TEST-NODE")
        assert identity.signature_mode == SignatureMode.HYBRID
    
    def test_created_at_timestamp(self):
        """Test that created_at is a valid ISO timestamp."""
        identity = HybridIdentity.generate("TEST-NODE")
        # Should not raise
        datetime.fromisoformat(identity.created_at.replace("Z", "+00:00"))


class TestHybridIdentityFromPublicKeys:
    """Tests for HybridIdentity.from_public_keys()."""
    
    def test_from_public_keys(self, hybrid_identity):
        """Test creating identity from public keys only."""
        peer = HybridIdentity.from_public_keys(
            ed25519_public=hybrid_identity.ed25519_public_key,
            pqc_public=hybrid_identity.pqc_public_key,
            node_name="PEER",
        )
        
        assert peer.node_id == hybrid_identity.node_id
        assert peer.has_private_keys is False
        assert peer.node_name == "PEER"
    
    def test_from_public_keys_default_name(self, hybrid_identity):
        """Test default node name for from_public_keys."""
        peer = HybridIdentity.from_public_keys(
            ed25519_public=hybrid_identity.ed25519_public_key,
            pqc_public=hybrid_identity.pqc_public_key,
        )
        
        assert peer.node_name == "PEER"


class TestHybridIdentityProperties:
    """Tests for HybridIdentity properties."""
    
    def test_ed25519_public_key(self, hybrid_identity):
        """Test ED25519 public key property."""
        pk = hybrid_identity.ed25519_public_key
        assert len(pk) == ED25519_PUBLIC_KEY_SIZE
    
    def test_pqc_public_key(self, hybrid_identity):
        """Test ML-DSA-65 public key property."""
        pk = hybrid_identity.pqc_public_key
        assert len(pk) == MLDSA65_PUBLIC_KEY_SIZE
    
    def test_public_key_b64_properties(self, hybrid_identity):
        """Test base64 public key properties."""
        ed_b64 = hybrid_identity.ed25519_public_key_b64
        pqc_b64 = hybrid_identity.pqc_public_key_b64
        
        assert isinstance(ed_b64, str)
        assert isinstance(pqc_b64, str)
        assert len(pqc_b64) > len(ed_b64)  # PQC key is larger
    
    def test_to_public_dict(self, hybrid_identity):
        """Test public dict export."""
        pub_dict = hybrid_identity.to_public_dict()
        
        assert "node_id" in pub_dict
        assert "node_name" in pub_dict
        assert "ed25519_public_key" in pub_dict
        assert "pqc_public_key" in pub_dict
        assert "private_key" not in str(pub_dict).lower()


class TestHybridIdentityRepr:
    """Tests for HybridIdentity string representation."""
    
    def test_repr_contains_node_id(self, hybrid_identity):
        """Test repr contains truncated node ID."""
        repr_str = repr(hybrid_identity)
        assert hybrid_identity.node_id[:16] in repr_str
    
    def test_repr_contains_node_name(self, hybrid_identity):
        """Test repr contains node name."""
        repr_str = repr(hybrid_identity)
        assert hybrid_identity.node_name in repr_str
    
    def test_repr_no_key_material(self, hybrid_identity):
        """Test repr doesn't expose key material."""
        repr_str = repr(hybrid_identity)
        # Full public keys should not appear
        assert hybrid_identity.ed25519_public_key_b64 not in repr_str
