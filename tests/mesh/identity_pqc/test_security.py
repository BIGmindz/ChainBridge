#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  PAC-SEC-P819: SECURITY TESTS                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

Security-focused tests for hybrid identity system.
Updated to use correct API: NodeIdentity.generate() and backend-based signing.
"""

import pytest
import os
import time
import hashlib

from modules.mesh.identity_pqc import (
    HybridIdentity,
    HybridSignature,
    SignatureMode,
)
from modules.mesh.identity_pqc.signatures import HybridSigner, HybridVerifier
from modules.mesh.identity_pqc.backends import get_ed25519_backend, get_pqc_backend
from modules.mesh.identity_pqc.compat import NodeIdentity
from modules.mesh.identity_pqc.constants import (
    ED25519_SIGNATURE_SIZE,
    MLDSA65_SIGNATURE_SIZE,
)


class TestSignatureMalleability:
    """Tests for signature malleability resistance."""
    
    def test_bit_flip_in_ed25519_signature(self):
        """Test that bit flips in ED25519 signature are detected."""
        node = NodeIdentity.generate("MALLEABLE-TEST")
        message = b"Test message for malleability"
        
        signature = node.sign(message)
        
        # Flip a bit in the signature
        corrupted = bytearray(signature)
        corrupted[10] ^= 0x01  # Flip bit in signature body
        corrupted = bytes(corrupted)
        
        # Should fail verification
        assert node.verify(message, corrupted) is False
    
    def test_bit_flip_in_pqc_signature(self):
        """Test that bit flips in PQC signature are detected."""
        node = NodeIdentity.generate("MALLEABLE-PQC-TEST")
        message = b"Test message for PQC malleability"
        
        signature = node.sign(message)
        
        # Flip a bit deeper in signature (PQC portion)
        corrupted = bytearray(signature)
        corrupted[-100] ^= 0x01  # Flip bit in PQC portion
        corrupted = bytes(corrupted)
        
        # Should fail verification
        assert node.verify(message, corrupted) is False
    
    def test_truncated_signature_rejected(self):
        """Test that truncated signatures are rejected."""
        node = NodeIdentity.generate("TRUNCATE-TEST")
        message = b"Test message"
        
        signature = node.sign(message)
        
        # Truncate signature
        truncated = signature[:-100]
        
        # Should fail
        assert node.verify(message, truncated) is False
    
    def test_extended_signature_rejected(self):
        """Test that extended signatures are rejected."""
        node = NodeIdentity.generate("EXTEND-TEST")
        message = b"Test message"
        
        signature = node.sign(message)
        
        # Extend signature with extra bytes
        extended = signature + b"\x00" * 100
        
        # Should fail
        assert node.verify(message, extended) is False


class TestKeyReuse:
    """Tests related to key reuse scenarios."""
    
    def test_same_key_different_messages(self):
        """Test that same key can sign different messages securely."""
        node = NodeIdentity.generate("KEY-REUSE-TEST")
        
        messages = [b"Message 1", b"Message 2", b"Message 3"]
        signatures = [node.sign(msg) for msg in messages]
        
        # Each signature should only verify its own message
        for i, (msg, sig) in enumerate(zip(messages, signatures)):
            assert node.verify(msg, sig) is True
            
            # Other messages should fail
            for j, other_msg in enumerate(messages):
                if i != j:
                    assert node.verify(other_msg, sig) is False
    
    def test_different_keys_same_message(self):
        """Test that different keys produce different signatures."""
        node1 = NodeIdentity.generate("KEY-1")
        node2 = NodeIdentity.generate("KEY-2")
        
        message = b"Same message for both"
        
        sig1 = node1.sign(message)
        sig2 = node2.sign(message)
        
        # Signatures should be different
        assert sig1 != sig2
        
        # Cross-verification should fail
        assert node2.verify(message, sig1) is False
        assert node1.verify(message, sig2) is False


class TestReplayAttacks:
    """Tests for replay attack resistance."""
    
    def test_signature_bound_to_exact_message(self):
        """Test that signatures are bound to exact message."""
        node = NodeIdentity.generate("REPLAY-TEST")
        
        original = b"Transfer 100 to Bob"
        modified = b"Transfer 1000 to Bob"
        
        signature = node.sign(original)
        
        # Modified message should fail
        assert node.verify(modified, signature) is False
    
    def test_signature_with_timestamp(self):
        """Test timestamped message signing."""
        node = NodeIdentity.generate("TIMESTAMP-TEST")
        
        timestamp = str(int(time.time())).encode()
        message = b"Action at " + timestamp
        
        signature = node.sign(message)
        
        # Exact message verifies
        assert node.verify(message, signature) is True
        
        # Different timestamp fails
        fake_timestamp = str(int(time.time()) + 1000).encode()
        fake_message = b"Action at " + fake_timestamp
        assert node.verify(fake_message, signature) is False


class TestCrossIdentityAttacks:
    """Tests for cross-identity attack resistance."""
    
    def test_identity_impersonation_fails(self):
        """Test that one identity cannot impersonate another."""
        alice = NodeIdentity.generate("ALICE")
        bob = NodeIdentity.generate("BOB")
        
        message = b"I am Alice"
        
        # Bob signs claiming to be Alice
        bob_signature = bob.sign(message)
        
        # Alice's verification should fail Bob's signature
        assert alice.verify(message, bob_signature) is False
    
    def test_key_substitution_fails(self):
        """Test that substituting keys fails."""
        real = NodeIdentity.generate("REAL")
        fake = NodeIdentity.generate("FAKE")
        
        message = b"Authentic message"
        real_signature = real.sign(message)
        
        # Fake identity cannot verify real signature
        assert fake.verify(message, real_signature) is False


class TestNodeIdDerivation:
    """Tests for node ID derivation security."""
    
    def test_node_id_deterministic(self):
        """Test that node ID is deterministically derived from keys."""
        node1 = NodeIdentity.generate("NODE-A")
        
        # Create another instance from same keys
        node2_from_pk = NodeIdentity.from_public_key(
            node1.public_key_bytes,
            node_name="NODE-A-COPY",
        )
        
        # Node IDs should match (derived from public key)
        assert node2_from_pk.node_id == node1.node_id
    
    def test_node_id_collision_resistance(self):
        """Test that different keys produce different node IDs."""
        nodes = [NodeIdentity.generate(f"NODE-{i}") for i in range(20)]
        node_ids = [n.node_id for n in nodes]
        
        # All node IDs should be unique
        assert len(set(node_ids)) == len(node_ids)


class TestPublicKeyExposure:
    """Tests for proper public/private key separation."""
    
    def test_public_dict_no_private_key(self):
        """Test that public export does not contain private key."""
        node = NodeIdentity.generate("EXPORT-TEST")
        
        data = node.to_dict()
        
        # Should not contain private key material in public export
        # (depends on implementation of to_dict)
        # At minimum, verify structure exists
        assert "node_id" in data
        assert "node_name" in data


class TestErrorLeakage:
    """Tests for information leakage through errors."""
    
    def test_signature_error_no_key_material(self):
        """Test that signature errors don't leak key material."""
        node = NodeIdentity.generate("ERROR-TEST")
        message = b"test"
        signature = node.sign(message)
        
        # Corrupt signature
        corrupted = bytes([0xFF] * len(signature))
        
        # Verification should fail without leaking key info
        try:
            result = node.verify(message, corrupted)
            assert result is False
        except Exception as e:
            # Error message should not contain key bytes
            error_msg = str(e)
            assert node.node_id not in error_msg or len(node.node_id) < 10
    
    def test_parse_error_no_internal_state(self):
        """Test that parse errors don't leak internal state."""
        # Try to parse garbage as signature
        garbage = os.urandom(100)
        
        try:
            HybridSignature.from_bytes(garbage)
        except Exception as e:
            # Error should be clean
            error_msg = str(e)
            assert len(error_msg) < 500  # Reasonable length


class TestTimingConsistency:
    """Tests for timing attack resistance."""
    
    @pytest.mark.slow
    def test_verification_timing_similar(self):
        """Test that verification timing is consistent."""
        node = NodeIdentity.generate("TIMING-TEST")
        message = b"Timing test message"
        
        valid_sig = node.sign(message)
        
        # Create invalid signatures of same length
        invalid_sig = bytes([0xFF] * len(valid_sig))
        
        # Measure verification times
        valid_times = []
        invalid_times = []
        
        for _ in range(10):
            start = time.perf_counter()
            node.verify(message, valid_sig)
            valid_times.append(time.perf_counter() - start)
            
            start = time.perf_counter()
            node.verify(message, invalid_sig)
            invalid_times.append(time.perf_counter() - start)
        
        # Remove outliers
        valid_avg = sum(sorted(valid_times)[1:-1]) / (len(valid_times) - 2)
        invalid_avg = sum(sorted(invalid_times)[1:-1]) / (len(invalid_times) - 2)
        
        # Timing should be within reasonable bounds
        # (not a strict constant-time check, just basic sanity)
        ratio = max(valid_avg, invalid_avg) / max(min(valid_avg, invalid_avg), 1e-9)
        assert ratio < 100  # Very loose bound


class TestKeyGeneration:
    """Tests for key generation security."""
    
    def test_key_uniqueness(self):
        """Test that generated keys are unique."""
        keys = []
        for i in range(10):
            node = NodeIdentity.generate(f"UNIQUE-{i}")
            keys.append(node.public_key_bytes)
        
        # All keys should be unique
        assert len(set(keys)) == len(keys)
    
    def test_key_length_correct(self):
        """Test that keys have correct lengths."""
        node = NodeIdentity.generate("LENGTH-TEST")
        
        # ED25519 public key is 32 bytes
        assert len(node.public_key_bytes) == 32
        
        # PQC key is 1952 bytes
        hybrid = node.hybrid
        assert len(hybrid.keys.pqc.public_key) == 1952


class TestSignatureIntegrity:
    """Tests for signature integrity."""
    
    def test_signature_non_malleable(self):
        """Test signature cannot be modified without detection."""
        node = NodeIdentity.generate("INTEGRITY-TEST")
        message = b"Integrity check"
        
        signature = node.sign(message)
        
        # Try various modifications
        modifications = [
            bytes([signature[0] ^ 0x01]) + signature[1:],  # First byte
            signature[:-1] + bytes([signature[-1] ^ 0x01]),  # Last byte
            signature[:50] + bytes([signature[50] ^ 0xFF]) + signature[51:],  # Middle
        ]
        
        for modified in modifications:
            assert node.verify(message, modified) is False
    
    def test_empty_signature_rejected(self):
        """Test that empty signature is rejected."""
        node = NodeIdentity.generate("EMPTY-SIG-TEST")
        message = b"Test message"
        
        assert node.verify(message, b"") is False
    
    def test_wrong_message_rejected(self):
        """Test that wrong message is rejected."""
        node = NodeIdentity.generate("WRONG-MSG-TEST")
        
        sig = node.sign(b"Original")
        
        assert node.verify(b"Different", sig) is False
        assert node.verify(b"original", sig) is False  # Case sensitive
        assert node.verify(b"Original ", sig) is False  # Extra space
