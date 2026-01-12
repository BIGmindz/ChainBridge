#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  PAC-SEC-P819: COMPATIBILITY TESTS                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

Tests for backward-compatible NodeIdentity wrapper.
Simplified to match actual implementation API.
"""

import pytest
import os

from modules.mesh.identity_pqc.compat import NodeIdentity
from modules.mesh.identity_pqc import HybridIdentity
from modules.mesh.identity_pqc.constants import (
    ED25519_PUBLIC_KEY_SIZE,
    MLDSA65_PUBLIC_KEY_SIZE,
)


class TestNodeIdentityBasic:
    """Basic tests for NodeIdentity wrapper."""
    
    def test_generate_creates_identity(self):
        """Test NodeIdentity.generate() creates valid identity."""
        node = NodeIdentity.generate("TEST-NODE")
        
        assert node.node_name == "TEST-NODE"
        assert node.node_id is not None
        assert len(node.node_id) > 0
    
    def test_generate_with_federation(self):
        """Test creating NodeIdentity with federation ID."""
        node = NodeIdentity.generate("TEST-NODE", federation_id="CUSTOM-FED")
        
        assert node.federation_id == "CUSTOM-FED"
    
    def test_public_key_bytes_property(self):
        """Test public_key_bytes property returns ED25519 key."""
        node = NodeIdentity.generate("TEST-NODE")
        
        pk = node.public_key_bytes
        assert len(pk) == ED25519_PUBLIC_KEY_SIZE
    
    def test_hybrid_property(self):
        """Test access to underlying HybridIdentity."""
        node = NodeIdentity.generate("TEST-NODE")
        
        hybrid = node.hybrid
        assert isinstance(hybrid, HybridIdentity)
        assert hybrid.keys.pqc.public_key is not None
        assert len(hybrid.keys.pqc.public_key) == MLDSA65_PUBLIC_KEY_SIZE


class TestNodeIdentitySignatures:
    """Tests for NodeIdentity signing and verification."""
    
    def test_sign_message(self):
        """Test signing message."""
        node = NodeIdentity.generate("TEST-NODE")
        
        message = b"Test message to sign"
        signature = node.sign(message)
        
        assert isinstance(signature, bytes)
        assert len(signature) > 0
    
    def test_verify_signature(self):
        """Test verifying valid signature."""
        node = NodeIdentity.generate("TEST-NODE")
        
        message = b"Test message"
        signature = node.sign(message)
        
        assert node.verify(message, signature) is True
    
    def test_verify_wrong_message(self):
        """Test verification fails for wrong message."""
        node = NodeIdentity.generate("TEST-NODE")
        
        signature = node.sign(b"Original message")
        
        assert node.verify(b"Wrong message", signature) is False
    
    def test_verify_corrupted_signature(self):
        """Test verification fails for corrupted signature."""
        node = NodeIdentity.generate("TEST-NODE")
        
        message = b"Test message"
        signature = node.sign(message)
        
        # Corrupt signature
        corrupted = bytes([b ^ 0x01 for b in signature[:10]]) + signature[10:]
        
        assert node.verify(message, corrupted) is False


class TestNodeIdentityPersistence:
    """Tests for NodeIdentity persistence."""
    
    def test_save_and_load(self, tmp_path):
        """Test saving and loading identity."""
        path = tmp_path / "test_identity.json"
        
        node = NodeIdentity.generate("TEST-NODE")
        original_id = node.node_id
        original_pk = node.public_key_bytes
        
        # Save
        node.save(str(path))
        
        # Load
        loaded = NodeIdentity.load(str(path))
        
        assert loaded.node_id == original_id
        assert loaded.public_key_bytes == original_pk
    
    def test_loaded_identity_can_sign(self, tmp_path):
        """Test loaded identity can sign."""
        path = tmp_path / "test_identity.json"
        
        node = NodeIdentity.generate("TEST-NODE")
        node.save(str(path))
        
        loaded = NodeIdentity.load(str(path))
        
        message = b"Test message"
        signature = loaded.sign(message)
        
        assert loaded.verify(message, signature) is True
    
    def test_signature_verifies_after_reload(self, tmp_path):
        """Test signature created before save verifies after reload."""
        path = tmp_path / "test_identity.json"
        
        node = NodeIdentity.generate("TEST-NODE")
        message = b"Test message"
        signature = node.sign(message)
        
        node.save(str(path))
        loaded = NodeIdentity.load(str(path))
        
        assert loaded.verify(message, signature) is True


class TestNodeIdentityFromPublicKey:
    """Tests for creating NodeIdentity from public key."""
    
    def test_from_public_key(self):
        """Test creating NodeIdentity from public key only."""
        source = NodeIdentity.generate("SOURCE")
        
        peer = NodeIdentity.from_public_key(
            source.public_key_bytes,
            node_name="PEER",
        )
        
        assert peer.public_key_bytes == source.public_key_bytes
    
    def test_public_key_only_cannot_sign(self):
        """Test that public-key-only identity cannot sign."""
        source = NodeIdentity.generate("SOURCE")
        
        peer = NodeIdentity.from_public_key(
            source.public_key_bytes,
            node_name="PEER",
        )
        
        # Should not be able to sign (no private key)
        try:
            peer.sign(b"test")
            # If it doesn't raise, that's unexpected
            pytest.fail("Expected signing to fail without private key")
        except Exception:
            pass  # Expected


class TestMultipleNodes:
    """Tests with multiple nodes."""
    
    def test_different_nodes_different_signatures(self):
        """Test that different nodes produce different signatures."""
        node1 = NodeIdentity.generate("NODE-1")
        node2 = NodeIdentity.generate("NODE-2")
        
        message = b"Same message"
        sig1 = node1.sign(message)
        sig2 = node2.sign(message)
        
        assert sig1 != sig2
    
    def test_cross_node_verification_fails(self):
        """Test that one node cannot verify another's signature."""
        node1 = NodeIdentity.generate("NODE-1")
        node2 = NodeIdentity.generate("NODE-2")
        
        message = b"Test message"
        sig1 = node1.sign(message)
        
        assert node2.verify(message, sig1) is False
    
    def test_unique_node_ids(self):
        """Test that each node gets unique ID."""
        nodes = [NodeIdentity.generate(f"NODE-{i}") for i in range(10)]
        ids = [n.node_id for n in nodes]
        
        assert len(set(ids)) == len(ids)
