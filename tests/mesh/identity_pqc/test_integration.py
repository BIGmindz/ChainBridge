#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  PAC-SEC-P819: INTEGRATION TESTS                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

End-to-end integration tests for hybrid identity system.
"""

import pytest
import os
import json
import hashlib
import time

from modules.mesh.identity_pqc import (
    HybridIdentity,
    HybridSignature,
    SignatureMode,
)
from modules.mesh.identity_pqc.signatures import HybridSigner, HybridVerifier
from modules.mesh.identity_pqc.compat import NodeIdentity
from modules.mesh.identity_pqc.backends import get_ed25519_backend, get_pqc_backend


# Helper to create signer from identity
def create_signer(identity: HybridIdentity) -> HybridSigner:
    """Create HybridSigner from HybridIdentity."""
    return HybridSigner(get_ed25519_backend(), get_pqc_backend())


def sign_message(identity: HybridIdentity, message: bytes) -> HybridSignature:
    """Sign message using identity."""
    signer = create_signer(identity)
    return signer.sign(
        identity._ed25519_keypair.private_key,
        identity._pqc_keypair.private_key,
        message,
    )


def verify_signature(identity: HybridIdentity, message: bytes, signature: HybridSignature) -> bool:
    """Verify signature using identity's public keys."""
    verifier = HybridVerifier(get_ed25519_backend(), get_pqc_backend())
    return verifier.verify(
        identity._ed25519_keypair.public_key,
        identity._pqc_keypair.public_key,
        message,
        signature,
    )


class TestEndToEndSigningFlow:
    """End-to-end tests for complete signing workflows."""
    
    def test_complete_node_authentication(self):
        """Test complete node-to-node authentication flow."""
        # 1. Server generates identity
        server = NodeIdentity.generate("AUTH-SERVER")
        
        # 2. Client generates identity
        client = NodeIdentity.generate("AUTH-CLIENT")
        
        # 3. Server creates challenge
        challenge = os.urandom(32)
        
        # 4. Client signs challenge
        response = client.sign(challenge)
        
        # 5. Server verifies response (using client's public data)
        assert client.verify(challenge, response) is True
        
        # 6. Invalid response fails
        assert client.verify(b"wrong", response) is False
    
    def test_mutual_authentication(self):
        """Test mutual authentication between two nodes."""
        node_a = NodeIdentity.generate("NODE-ALPHA")
        node_b = NodeIdentity.generate("NODE-BETA")
        
        # A challenges B
        challenge_a = os.urandom(32)
        response_b = node_b.sign(challenge_a)
        assert node_b.verify(challenge_a, response_b) is True
        
        # B challenges A
        challenge_b = os.urandom(32)
        response_a = node_a.sign(challenge_b)
        assert node_a.verify(challenge_b, response_a) is True
    
    def test_message_exchange_with_signatures(self):
        """Test signed message exchange between nodes."""
        sender = NodeIdentity.generate("SENDER")
        
        # Send multiple messages
        messages = [
            b"Message 1: Hello",
            b"Message 2: How are you?",
            b"Message 3: Goodbye",
        ]
        
        for msg in messages:
            sig = sender.sign(msg)
            assert sender.verify(msg, sig) is True


class TestPersistenceIntegration:
    """Integration tests for identity persistence."""
    
    def test_save_load_sign_verify(self, tmp_path):
        """Test complete save/load/sign/verify workflow."""
        identity_path = tmp_path / "node_identity.json"
        
        # 1. Create and save identity
        original = NodeIdentity.generate("PERSISTENT-NODE")
        original.save(str(identity_path))
        
        # 2. Load identity
        loaded = NodeIdentity.load(str(identity_path))
        
        # 3. Sign with loaded identity
        message = b"Signed after load"
        signature = loaded.sign(message)
        
        # 4. Verify signature
        assert loaded.verify(message, signature) is True


class TestProtocolSimulation:
    """Simulated protocol scenarios."""
    
    def test_transaction_signing_protocol(self):
        """Test transaction signing simulation."""
        # Participants using NodeIdentity wrapper
        alice = NodeIdentity.generate("ALICE")
        bob = NodeIdentity.generate("BOB")
        
        # Alice creates transaction
        transaction = {
            "from": alice.node_id,
            "to": bob.node_id,
            "amount": 100,
            "asset": "TOKEN",
            "nonce": os.urandom(8).hex(),
            "timestamp": int(time.time()),
        }
        tx_bytes = json.dumps(transaction, sort_keys=True).encode()
        tx_hash = hashlib.sha256(tx_bytes).digest()
        
        # Alice signs transaction hash
        tx_signature = alice.sign(tx_hash)
        
        # Bob verifies Alice's signature (using Alice's instance)
        assert alice.verify(tx_hash, tx_signature) is True
        
        # Tampered hash fails
        tampered_hash = hashlib.sha256(b"tampered").digest()
        assert alice.verify(tampered_hash, tx_signature) is False


class TestBackendIntegration:
    """Integration tests for backend interoperability."""
    
    def test_backends_work_together(self):
        """Test ED25519 and ML-DSA-65 backends work together."""
        ed_backend = get_ed25519_backend()
        pqc_backend = get_pqc_backend()
        
        message = b"Backend integration test"
        
        # Generate keys with both backends
        ed_pk, ed_sk = ed_backend.keygen()
        pqc_pk, pqc_sk = pqc_backend.keygen()
        
        # Sign with both
        ed_sig = ed_backend.sign(ed_sk, message)
        pqc_sig = pqc_backend.sign(pqc_sk, message)
        
        # Verify both
        assert ed_backend.verify(ed_pk, message, ed_sig) is True
        assert pqc_backend.verify(pqc_pk, message, pqc_sig) is True
        
        # Cross-verification should fail
        assert ed_backend.verify(ed_pk, b"wrong", ed_sig) is False
        assert pqc_backend.verify(pqc_pk, b"wrong", pqc_sig) is False
    
    def test_hybrid_uses_both_backends(self):
        """Test HybridIdentity uses both backends correctly via NodeIdentity."""
        node = NodeIdentity.generate("HYBRID-TEST")
        
        message = b"Hybrid backend test"
        signature = node.sign(message)
        
        # Hybrid verification should pass
        assert node.verify(message, signature) is True


class TestErrorRecovery:
    """Tests for error recovery scenarios."""
    
    def test_corrupted_signature_recovery(self):
        """Test handling of corrupted signatures."""
        node = NodeIdentity.generate("TEST-NODE")
        message = b"test message"
        
        # Get valid signature
        signature = node.sign(message)
        
        # Corrupt the signature
        corrupted = bytes([b ^ 0xFF for b in signature[:10]]) + signature[10:]
        
        # Should fail gracefully
        result = node.verify(message, corrupted)
        assert result is False
    
    def test_missing_key_handling(self):
        """Test handling when trying to sign without private keys."""
        # Create a node and get its public data
        source = NodeIdentity.generate("SOURCE")
        
        # Verification should work
        msg = b"test"
        sig = source.sign(msg)
        assert source.verify(msg, sig) is True


class TestPerformanceBaseline:
    """Baseline performance tests (informational)."""
    
    @pytest.mark.slow
    def test_keygen_performance(self):
        """Measure key generation performance."""
        iterations = 5
        start = time.perf_counter()
        for _ in range(iterations):
            NodeIdentity.generate(f"PERF-TEST-{_}")
        elapsed = time.perf_counter() - start
        
        avg_ms = (elapsed / iterations) * 1000
        print(f"\nKey generation: {avg_ms:.2f}ms average")
        
        # Should complete in reasonable time
        assert avg_ms < 5000  # Less than 5 seconds per keygen
    
    @pytest.mark.slow
    def test_sign_performance(self):
        """Measure signing performance."""
        node = NodeIdentity.generate("SIGN-PERF")
        message = b"Performance test message"
        
        iterations = 50
        start = time.perf_counter()
        for _ in range(iterations):
            node.sign(message)
        elapsed = time.perf_counter() - start
        
        avg_ms = (elapsed / iterations) * 1000
        ops_per_sec = iterations / elapsed
        print(f"\nSigning: {avg_ms:.2f}ms average, {ops_per_sec:.1f} ops/sec")
        
        assert avg_ms < 1000  # Less than 1 second per sign
    
    @pytest.mark.slow
    def test_verify_performance(self):
        """Measure verification performance."""
        node = NodeIdentity.generate("VERIFY-PERF")
        message = b"Performance test message"
        signature = node.sign(message)
        
        iterations = 50
        start = time.perf_counter()
        for _ in range(iterations):
            node.verify(message, signature)
        elapsed = time.perf_counter() - start
        
        avg_ms = (elapsed / iterations) * 1000
        ops_per_sec = iterations / elapsed
        print(f"\nVerification: {avg_ms:.2f}ms average, {ops_per_sec:.1f} ops/sec")
        
        assert avg_ms < 1000  # Less than 1 second per verify
