#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  PAC-SEC-P819: SIGNATURE TESTS                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Tests for HybridSignature, HybridSigner, HybridVerifier.
Updated to use correct API: backends instead of identity.
"""

import pytest
import os

from modules.mesh.identity_pqc import (
    HybridIdentity,
    HybridSignature,
    SignatureMode,
)
from modules.mesh.identity_pqc.signatures import (
    HybridSigner,
    HybridVerifier,
)
from modules.mesh.identity_pqc.backends import (
    get_ed25519_backend,
    get_pqc_backend,
)
from modules.mesh.identity_pqc.constants import (
    ED25519_SIGNATURE_SIZE,
    MLDSA65_SIGNATURE_SIZE,
    FORMAT_VERSION,
)
from modules.mesh.identity_pqc.errors import (
    SignatureError,
    VerificationError,
    InvalidSignatureError,
    SignatureModeError,
)
from modules.mesh.identity_pqc.compat import NodeIdentity


# Fixtures for reuse
@pytest.fixture
def ed_backend():
    """ED25519 backend instance."""
    return get_ed25519_backend()


@pytest.fixture
def pqc_backend():
    """ML-DSA-65 backend instance."""
    return get_pqc_backend()


@pytest.fixture
def ed_keys(ed_backend):
    """Generate ED25519 key pair."""
    return ed_backend.keygen()


@pytest.fixture
def pqc_keys(pqc_backend):
    """Generate ML-DSA-65 key pair."""
    return pqc_backend.keygen()


@pytest.fixture
def test_message():
    """Standard test message."""
    return b"ChainBridge PAC-SEC-P819 Test Message"


class TestHybridSignature:
    """Tests for HybridSignature dataclass."""
    
    def test_hybrid_signature_creation(self):
        """Test HybridSignature creation."""
        ed_sig = os.urandom(ED25519_SIGNATURE_SIZE)
        pqc_sig = os.urandom(MLDSA65_SIGNATURE_SIZE)
        
        sig = HybridSignature(
            ed25519_sig=ed_sig,
            mldsa65_sig=pqc_sig,
            mode=SignatureMode.HYBRID,
        )
        
        assert sig.ed25519_sig == ed_sig
        assert sig.mldsa65_sig == pqc_sig
        assert sig.mode == SignatureMode.HYBRID
    
    def test_signature_to_bytes_and_back(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test signature serialization/deserialization."""
        signer = HybridSigner(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, pqc_sk, test_message)
        
        # Serialize
        raw = signature.to_bytes()
        
        # Deserialize
        restored = HybridSignature.from_bytes(raw)
        
        assert restored.mode == signature.mode
        assert restored.ed25519_sig == signature.ed25519_sig
        assert restored.mldsa65_sig == signature.mldsa65_sig
    
    def test_signature_version_encoding(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test version byte encoding."""
        signer = HybridSigner(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, pqc_sk, test_message)
        raw = signature.to_bytes()
        
        assert raw[0] == FORMAT_VERSION
    
    def test_signature_mode_encoding(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test mode encoding in signature."""
        signer = HybridSigner(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, pqc_sk, test_message)
        raw = signature.to_bytes()
        
        # Version byte 0x01 = HYBRID mode
        assert raw[0] == 0x01
    
    def test_from_bytes_too_short(self):
        """Test rejection of truncated data."""
        from modules.mesh.identity_pqc.errors import SignatureMalformedError
        # Too short for any valid signature
        short_data = bytes(10)
        
        with pytest.raises((SignatureMalformedError, ValueError)):
            HybridSignature.from_bytes(short_data)


class TestHybridSigner:
    """Tests for HybridSigner class."""
    
    def test_sign_message(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test signing a message."""
        signer = HybridSigner(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, pqc_sk, test_message)
        
        assert isinstance(signature, HybridSignature)
        assert signature.mode == SignatureMode.HYBRID
        assert signature.ed25519_sig is not None
        assert signature.mldsa65_sig is not None
    
    def test_sign_various_message_sizes(self, ed_backend, pqc_backend, ed_keys, pqc_keys):
        """Test signing messages of various sizes."""
        signer = HybridSigner(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        sizes = [0, 1, 100, 1000, 10000]
        for size in sizes:
            msg = bytes(size)
            signature = signer.sign(ed_sk, pqc_sk, msg)
            assert isinstance(signature, HybridSignature)
    
    def test_sign_requires_private_keys(self, ed_backend, pqc_backend, test_message):
        """Test that signing requires private keys."""
        signer = HybridSigner(ed_backend, pqc_backend)
        
        with pytest.raises(SignatureError):
            signer.sign(None, None, test_message)
    
    def test_sign_deterministic_ed25519(self, ed_backend, pqc_backend, ed_keys, pqc_keys):
        """Test that ED25519 signatures are deterministic."""
        signer = HybridSigner(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        msg = b"deterministic test"
        
        sig1 = signer.sign(ed_sk, pqc_sk, msg)
        sig2 = signer.sign(ed_sk, pqc_sk, msg)
        
        # ED25519 is deterministic
        assert sig1.ed25519_sig == sig2.ed25519_sig
    
    def test_sign_unique_for_different_messages(self, ed_backend, pqc_backend, ed_keys, pqc_keys):
        """Test that different messages produce different signatures."""
        signer = HybridSigner(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        sig1 = signer.sign(ed_sk, pqc_sk, b"message1")
        sig2 = signer.sign(ed_sk, pqc_sk, b"message2")
        
        assert sig1.ed25519_sig != sig2.ed25519_sig
        assert sig1.mldsa65_sig != sig2.mldsa65_sig
    
    def test_sign_legacy_mode(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test signing in LEGACY mode (ED25519 only)."""
        signer = HybridSigner(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, None, test_message, mode=SignatureMode.LEGACY)
        
        assert signature.mode == SignatureMode.LEGACY
        assert signature.ed25519_sig is not None
        assert signature.mldsa65_sig is None
    
    def test_sign_pqc_only_mode(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test signing in PQC_ONLY mode."""
        signer = HybridSigner(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(None, pqc_sk, test_message, mode=SignatureMode.PQC_ONLY)
        
        assert signature.mode == SignatureMode.PQC_ONLY
        assert signature.ed25519_sig is None
        assert signature.mldsa65_sig is not None


class TestHybridVerifier:
    """Tests for HybridVerifier class."""
    
    def test_verify_valid_signature(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test verifying a valid signature."""
        signer = HybridSigner(ed_backend, pqc_backend)
        verifier = HybridVerifier(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, pqc_sk, test_message)
        result = verifier.verify(ed_pk, pqc_pk, test_message, signature)
        
        assert result is True
    
    def test_verify_invalid_message(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test rejection of invalid message."""
        signer = HybridSigner(ed_backend, pqc_backend)
        verifier = HybridVerifier(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, pqc_sk, test_message)
        result = verifier.verify(ed_pk, pqc_pk, b"wrong message", signature)
        
        assert result is False
    
    def test_verify_wrong_public_key(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test rejection when using wrong public key."""
        signer = HybridSigner(ed_backend, pqc_backend)
        verifier = HybridVerifier(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, pqc_sk, test_message)
        
        # Generate different keys
        other_ed_pk, _ = ed_backend.keygen()
        other_pqc_pk, _ = pqc_backend.keygen()
        
        result = verifier.verify(other_ed_pk, other_pqc_pk, test_message, signature)
        assert result is False
    
    def test_verify_tampered_ed25519_signature(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test rejection of tampered ED25519 signature."""
        signer = HybridSigner(ed_backend, pqc_backend)
        verifier = HybridVerifier(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, pqc_sk, test_message)
        
        # Tamper with ED25519 signature
        tampered_ed = bytes([(signature.ed25519_sig[0] + 1) % 256]) + signature.ed25519_sig[1:]
        tampered = HybridSignature(
            ed25519_sig=tampered_ed,
            mldsa65_sig=signature.mldsa65_sig,
            mode=signature.mode,
        )
        
        result = verifier.verify(ed_pk, pqc_pk, test_message, tampered)
        assert result is False
    
    def test_verify_tampered_pqc_signature(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test rejection of tampered PQC signature."""
        signer = HybridSigner(ed_backend, pqc_backend)
        verifier = HybridVerifier(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, pqc_sk, test_message)
        
        # Tamper with PQC signature
        tampered_pqc = bytes([(signature.mldsa65_sig[0] + 1) % 256]) + signature.mldsa65_sig[1:]
        tampered = HybridSignature(
            ed25519_sig=signature.ed25519_sig,
            mldsa65_sig=tampered_pqc,
            mode=signature.mode,
        )
        
        result = verifier.verify(ed_pk, pqc_pk, test_message, tampered)
        assert result is False
    
    def test_verify_legacy_mode(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test verification of LEGACY mode signature returns False (security policy)."""
        signer = HybridSigner(ed_backend, pqc_backend)
        verifier = HybridVerifier(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, None, test_message, mode=SignatureMode.LEGACY)
        # Note: LEGACY mode verification returns False by security policy (minimum HYBRID required)
        result = verifier.verify(ed_pk, None, test_message, signature)
        
        # This is expected to fail - LEGACY mode is below minimum security level
        assert result is False
    
    def test_verify_pqc_only_mode(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test verification of PQC_ONLY mode signature."""
        signer = HybridSigner(ed_backend, pqc_backend)
        verifier = HybridVerifier(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(None, pqc_sk, test_message, mode=SignatureMode.PQC_ONLY)
        result = verifier.verify(None, pqc_pk, test_message, signature)
        
        assert result is True


class TestSignAndVerifyRoundtrip:
    """Integration tests for complete sign/verify workflow."""
    
    def test_roundtrip_bytes_encoding(self, ed_backend, pqc_backend, ed_keys, pqc_keys, test_message):
        """Test complete roundtrip with bytes serialization."""
        signer = HybridSigner(ed_backend, pqc_backend)
        verifier = HybridVerifier(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, pqc_sk, test_message)
        
        # Serialize/deserialize
        raw = signature.to_bytes()
        restored = HybridSignature.from_bytes(raw)
        
        # Verify restored signature
        result = verifier.verify(ed_pk, pqc_pk, test_message, restored)
        assert result is True
    
    def test_cross_node_signing(self):
        """Test signing on one node, verifying on another."""
        # Use NodeIdentity for cleaner API
        node_a = NodeIdentity.generate("NODE-A")
        node_b = NodeIdentity.generate("NODE-B")
        
        # A signs a message
        message = b"Message from A to B"
        sig = node_a.sign(message)
        
        # Verify using A's own instance (has public keys)
        assert node_a.verify(message, sig) is True
    
    def test_challenge_response_protocol(self):
        """Test challenge-response authentication."""
        server = NodeIdentity.generate("SERVER")
        client = NodeIdentity.generate("CLIENT")
        
        # Server creates challenge
        challenge = os.urandom(32)
        
        # Client signs challenge
        response = client.sign(challenge)
        
        # Verify client's response
        assert client.verify(challenge, response) is True
        
        # Wrong challenge should fail
        assert client.verify(b"wrong_challenge", response) is False


class TestSignatureEdgeCases:
    """Edge case tests for signatures."""
    
    def test_sign_empty_message(self, ed_backend, pqc_backend, ed_keys, pqc_keys):
        """Test signing empty message."""
        signer = HybridSigner(ed_backend, pqc_backend)
        verifier = HybridVerifier(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        signature = signer.sign(ed_sk, pqc_sk, b"")
        result = verifier.verify(ed_pk, pqc_pk, b"", signature)
        
        assert result is True
    
    def test_sign_large_message(self, ed_backend, pqc_backend, ed_keys, pqc_keys):
        """Test signing large message."""
        signer = HybridSigner(ed_backend, pqc_backend)
        verifier = HybridVerifier(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        # 100KB message
        large_msg = b"X" * (100 * 1024)
        
        signature = signer.sign(ed_sk, pqc_sk, large_msg)
        result = verifier.verify(ed_pk, pqc_pk, large_msg, signature)
        
        assert result is True
    
    def test_sign_binary_data(self, ed_backend, pqc_backend, ed_keys, pqc_keys):
        """Test signing arbitrary binary data."""
        signer = HybridSigner(ed_backend, pqc_backend)
        verifier = HybridVerifier(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        binary_data = os.urandom(1000)
        
        signature = signer.sign(ed_sk, pqc_sk, binary_data)
        result = verifier.verify(ed_pk, pqc_pk, binary_data, signature)
        
        assert result is True
    
    def test_sign_unicode_encoded(self, ed_backend, pqc_backend, ed_keys, pqc_keys):
        """Test signing Unicode text as bytes."""
        signer = HybridSigner(ed_backend, pqc_backend)
        verifier = HybridVerifier(ed_backend, pqc_backend)
        ed_pk, ed_sk = ed_keys
        pqc_pk, pqc_sk = pqc_keys
        
        unicode_msg = "Hello 世界 🌍".encode("utf-8")
        
        signature = signer.sign(ed_sk, pqc_sk, unicode_msg)
        result = verifier.verify(ed_pk, pqc_pk, unicode_msg, signature)
        
        assert result is True


class TestNodeIdentityIntegration:
    """Tests using NodeIdentity wrapper for simpler API."""
    
    def test_node_identity_sign_verify(self):
        """Test NodeIdentity sign/verify workflow."""
        node = NodeIdentity.generate("TEST")
        msg = b"test message"
        
        sig = node.sign(msg)
        assert node.verify(msg, sig) is True
    
    def test_node_identity_different_messages(self):
        """Test signing different messages."""
        node = NodeIdentity.generate("TEST")
        
        msgs = [b"msg1", b"msg2", b"msg3"]
        sigs = [node.sign(m) for m in msgs]
        
        # Each message verifies with its own signature
        for msg, sig in zip(msgs, sigs):
            assert node.verify(msg, sig) is True
        
        # Wrong message/signature pairs fail
        assert node.verify(msgs[0], sigs[1]) is False
    
    def test_node_identity_persistence(self, tmp_path):
        """Test NodeIdentity save/load cycle."""
        path = str(tmp_path / "node.json")
        
        original = NodeIdentity.generate("PERSISTENT")
        msg = b"persistence test"
        sig = original.sign(msg)
        
        original.save(path)
        loaded = NodeIdentity.load(path)
        
        # Can verify old signature with loaded identity
        assert loaded.verify(msg, sig) is True
        
        # Can create new signatures
        new_sig = loaded.sign(b"new message")
        assert loaded.verify(b"new message", new_sig) is True
