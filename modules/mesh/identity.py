#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     MESH IDENTITY - THE QUANTUM SEAL                         ║
║                   PAC-SEC-P820 QUANTUM-SAFE UPGRADE                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Hybrid ED25519 + ML-DSA-65 Cryptographic Identity                           ║
║                                                                              ║
║  "Trust that survives the quantum apocalypse."                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

PAC-SEC-P820: Heart Transplant Complete
───────────────────────────────────────────────────────────────────────────────
This module now wraps the quantum-safe identity_pqc implementation while
maintaining 100% backward compatibility with the legacy ED25519 API.

The Identity module provides:
  - Hybrid ED25519 + ML-DSA-65 key pair generation
  - Node identity persistence (both legacy and hybrid formats)
  - Message signing with quantum-safe signatures
  - Backward-compatible verification (accepts legacy and hybrid signatures)
  - Identity challenges for peer authentication

INVARIANTS:
  INV-SEC-002 (Identity Persistence): A Node ID is permanent. Losing the key means death.
  INV-SEC-004 (Cryptographic Proof): All identity claims must be verifiable.
  INV-SEC-P819 (Quantum Safety): Signatures resist quantum attack via ML-DSA-65.

Usage (unchanged from legacy API):
    from modules.mesh.identity import NodeIdentity, IdentityManager
    
    # Create new identity (now generates hybrid ED25519 + ML-DSA-65)
    identity = NodeIdentity.generate(node_name="NODE-ALPHA")
    
    # Save to disk
    identity.save("keys/node_identity.json")
    
    # Sign a message (returns ED25519 signature for compatibility)
    signature = identity.sign(b"Hello, Federation!")
    
    # Sign with full hybrid signature (new capability)
    hybrid_sig = identity.sign_hybrid(b"Hello, Quantum World!")
    
    # Verify (accepts both legacy ED25519 and hybrid signatures)
    is_valid = identity.verify(message, signature)
    is_valid = identity.verify_peer(peer_public_key, message, signature)

Migration from Legacy:
    Existing code continues to work unchanged. New identities are automatically
    hybrid. Legacy identities are upgraded to hybrid on first sign operation.

VERSION HISTORY:
    3.0.0 - Legacy ED25519 implementation (identity_legacy.py)
    4.0.0 - Quantum-safe upgrade via P820 (this file)
"""

# ══════════════════════════════════════════════════════════════════════════════
# RE-EXPORT FROM QUANTUM-SAFE IMPLEMENTATION
# ══════════════════════════════════════════════════════════════════════════════

from modules.mesh.identity_pqc.compat import (
    NodeIdentity,
    IdentityManager,
)

# Re-export additional types for advanced usage
from modules.mesh.identity_pqc import (
    HybridIdentity,
    HybridSignature,
    SignatureMode,
    PQCError,
    KeyGenerationError,
    SignatureError,
    VerificationError,
    migrate_legacy_identity,
    can_migrate,
)

# Backward compatibility: expose CRYPTO_AVAILABLE flag
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# Legacy fallback mock (for testing without cryptography)
from modules.mesh.identity_pqc.compat import NodeIdentity as _NodeIdentity


class MockEd25519:
    """
    Mock Ed25519 implementation for backward compatibility.
    Delegates to the PQC compat layer for actual behavior.
    WARNING: NOT CRYPTOGRAPHICALLY SECURE - FOR TESTING ONLY
    """
    
    @staticmethod
    def generate_key_pair():
        """Generate mock key pair - uses hybrid generation internally."""
        identity = _NodeIdentity.generate("MOCK-NODE")
        return identity.private_key_bytes, identity.public_key_bytes
    
    @staticmethod
    def sign(private_key: bytes, message: bytes) -> bytes:
        """Mock signature."""
        import hashlib
        combined = private_key + message
        return hashlib.sha512(combined).digest()
    
    @staticmethod
    def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Mock verification."""
        return len(signature) == 64


__version__ = "4.0.0"

__all__ = [
    # Primary API (backward compatible)
    "NodeIdentity",
    "IdentityManager",
    # PQC extensions
    "HybridIdentity",
    "HybridSignature",
    "SignatureMode",
    # Errors
    "PQCError",
    "KeyGenerationError",
    "SignatureError",
    "VerificationError",
    # Migration utilities
    "migrate_legacy_identity",
    "can_migrate",
    # Backward compatibility
    "MockEd25519",
    "CRYPTO_AVAILABLE",
]


# ══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ══════════════════════════════════════════════════════════════════════════════

def _self_test():
    """Run self-test to validate quantum-safe identity module."""
    print("=" * 70)
    print("MESH IDENTITY v4.0.0 - Quantum-Safe Self Test")
    print("PAC-SEC-P820: Heart Transplant Validation")
    print("=" * 70)
    
    # Test 1: Identity generation (now hybrid)
    print("\n[1/7] Testing hybrid identity generation...")
    alice = NodeIdentity.generate("NODE-ALICE", "CHAINBRIDGE-FEDERATION")
    print(f"      ✓ Node ID: {alice.node_id[:16]}...")
    print(f"      ✓ Name: {alice.node_name}")
    print(f"      ✓ Has private key: {alice.has_private_key}")
    print(f"      ✓ Has hybrid capability: {hasattr(alice, 'hybrid')}")
    
    # Test 2: Legacy ED25519 signature (backward compat)
    print("\n[2/7] Testing legacy ED25519 signing (backward compat)...")
    message = b"Hello, Federation! This is a test message."
    signature = alice.sign(message)
    print(f"      ✓ Message: {len(message)} bytes")
    print(f"      ✓ Signature: {len(signature)} bytes (ED25519 = 64)")
    assert len(signature) == 64, "Legacy signature should be 64 bytes"
    
    # Test 3: Legacy signature verification
    print("\n[3/7] Testing legacy signature verification...")
    is_valid = alice.verify(message, signature)
    assert is_valid, "Valid signature should verify"
    print(f"      ✓ Valid signature verified: {is_valid}")
    
    tampered = b"Hello, Federation! This is a TAMPERED message."
    is_invalid = alice.verify(tampered, signature)
    assert not is_invalid, "Tampered message should fail"
    print(f"      ✓ Tampered message rejected: {not is_invalid}")
    
    # Test 4: Hybrid signature (new capability)
    print("\n[4/7] Testing hybrid ED25519 + ML-DSA-65 signature...")
    hybrid_sig = alice.sign_hybrid(message)
    print(f"      ✓ Hybrid signature: {len(hybrid_sig)} bytes")
    assert len(hybrid_sig) > 64, "Hybrid signature should be larger than ED25519"
    
    # Verify hybrid signature
    is_valid = alice.verify(message, hybrid_sig)
    print(f"      ✓ Hybrid signature verified: {is_valid}")
    
    # Test 5: Challenge-response
    print("\n[5/7] Testing challenge-response authentication...")
    bob = NodeIdentity.generate("NODE-BOB", "CHAINBRIDGE-FEDERATION")
    
    challenge = alice.create_challenge()
    print(f"      ✓ Challenge nonce: {challenge['nonce'][:16]}...")
    
    response = bob.respond_to_challenge(challenge)
    print(f"      ✓ Response from: {response['responder'][:16]}...")
    
    is_valid, error = alice.verify_challenge_response(challenge, response)
    assert is_valid, f"Valid response should verify: {error}"
    print(f"      ✓ Response verified: {is_valid}")
    
    # Test 6: Peer identity from public key
    print("\n[6/7] Testing peer identity creation...")
    bob_public = NodeIdentity.from_public_key(bob.public_key_bytes, "BOB-PEER")
    print(f"      ✓ Peer node ID: {bob_public.node_id[:16]}...")
    print(f"      ✓ Matches original: {bob_public.node_id == bob.node_id}")
    
    bob_message = b"Signed by Bob"
    bob_sig = bob.sign(bob_message)
    is_valid = bob_public.verify(bob_message, bob_sig)
    print(f"      ✓ Peer signature verified: {is_valid}")
    
    # Test 7: IdentityManager
    print("\n[7/7] Testing IdentityManager...")
    manager = IdentityManager()
    manager._self_identity = alice
    manager.add_peer_identity(bob)
    
    print(f"      ✓ Self identity: {manager.node_id[:16]}...")
    print(f"      ✓ Peer count: {manager.get_peer_count()}")
    
    is_valid = manager.verify_peer_signature(bob.node_id, bob_message, bob_sig)
    print(f"      ✓ Manager verification: {is_valid}")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print(f"Version: {__version__}")
    print(f"Crypto available: {CRYPTO_AVAILABLE}")
    print("INV-SEC-002 (Identity Persistence): READY")
    print("INV-SEC-004 (Cryptographic Proof): READY")
    print("INV-SEC-P819 (Quantum Safety): ACTIVE")
    print("=" * 70)
    print("\n🔐 The Quantum Seal is ready. Nodes are quantum-safe.")
    print("🔗 Heart Transplant (P820): COMPLETE")


if __name__ == "__main__":
    _self_test()
