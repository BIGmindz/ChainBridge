#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    PAC-SEC-P818: PQC COMPATIBILITY TEST HARNESS              ║
║                         ML-DSA-65 (FIPS 204) Validation                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Purpose: Prove ML-DSA-65 digital signatures work in ChainBridge environment ║
║  Library: pqcrypto==0.3.4                                                    ║
║  Target: modules/mesh/identity.py replacement (P819/P820)                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

INVARIANTS TESTED:
  INV-PQC-001: Library supports FIPS 204 ML-DSA-65
  INV-PQC-002: Library installs on Python 3.11+
  INV-PQC-003: Library compatible with cryptography==46.0.1
  INV-PQC-004: Sign/verify cycle executes without error

Usage:
    pytest tests/crypto/test_pqc_compat.py -v
    python tests/crypto/test_pqc_compat.py  # Direct execution
"""

import pytest
import sys
from typing import Tuple

# Attempt to import pqcrypto - this validates INV-PQC-001/002/003
try:
    from pqcrypto.sign import ml_dsa_65
    PQCRYPTO_AVAILABLE = True
except ImportError as e:
    PQCRYPTO_AVAILABLE = False
    IMPORT_ERROR = str(e)


# ══════════════════════════════════════════════════════════════════════════════
# TEST FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def keypair() -> Tuple[bytes, bytes]:
    """Generate ML-DSA-65 keypair for tests."""
    if not PQCRYPTO_AVAILABLE:
        pytest.skip("pqcrypto not available")
    return ml_dsa_65.generate_keypair()


@pytest.fixture
def test_message() -> bytes:
    """Standard test message."""
    return b"ChainBridge PAC-SEC-P818 Test Message - ML-DSA-65 Validation"


# ══════════════════════════════════════════════════════════════════════════════
# IMPORT TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_pqcrypto_import():
    """
    INV-PQC-001: Verify pqcrypto library is importable.
    INV-PQC-002: Verify Python version compatibility.
    INV-PQC-003: Verify no conflicts with existing packages.
    """
    assert PQCRYPTO_AVAILABLE, f"pqcrypto import failed: {IMPORT_ERROR if not PQCRYPTO_AVAILABLE else 'unknown'}"


def test_ml_dsa_65_module_available():
    """INV-PQC-001: Verify ML-DSA-65 module is available."""
    if not PQCRYPTO_AVAILABLE:
        pytest.skip("pqcrypto not available")
    
    assert hasattr(ml_dsa_65, 'generate_keypair'), "generate_keypair function missing"
    assert hasattr(ml_dsa_65, 'sign'), "sign function missing"
    assert hasattr(ml_dsa_65, 'verify'), "verify function missing"


def test_ml_dsa_65_constants():
    """Verify ML-DSA-65 key and signature sizes match FIPS 204 spec."""
    if not PQCRYPTO_AVAILABLE:
        pytest.skip("pqcrypto not available")
    
    # FIPS 204 ML-DSA-65 sizes
    assert ml_dsa_65.PUBLIC_KEY_SIZE == 1952, f"Unexpected public key size: {ml_dsa_65.PUBLIC_KEY_SIZE}"
    assert ml_dsa_65.SECRET_KEY_SIZE == 4032, f"Unexpected secret key size: {ml_dsa_65.SECRET_KEY_SIZE}"
    assert ml_dsa_65.SIGNATURE_SIZE == 3309, f"Unexpected signature size: {ml_dsa_65.SIGNATURE_SIZE}"


# ══════════════════════════════════════════════════════════════════════════════
# KEYGEN TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_mldsa65_keygen():
    """
    INV-PQC-004: Verify ML-DSA-65 keypair generation.
    
    Tests:
      - Keypair generation completes without error
      - Public key has correct size (1952 bytes)
      - Secret key has correct size (4032 bytes)
    """
    if not PQCRYPTO_AVAILABLE:
        pytest.skip("pqcrypto not available")
    
    public_key, secret_key = ml_dsa_65.generate_keypair()
    
    assert isinstance(public_key, bytes), "Public key should be bytes"
    assert isinstance(secret_key, bytes), "Secret key should be bytes"
    assert len(public_key) == 1952, f"Public key size mismatch: {len(public_key)} != 1952"
    assert len(secret_key) == 4032, f"Secret key size mismatch: {len(secret_key)} != 4032"


def test_mldsa65_keygen_unique():
    """Verify each keypair generation produces unique keys."""
    if not PQCRYPTO_AVAILABLE:
        pytest.skip("pqcrypto not available")
    
    pk1, sk1 = ml_dsa_65.generate_keypair()
    pk2, sk2 = ml_dsa_65.generate_keypair()
    
    assert pk1 != pk2, "Public keys should be unique"
    assert sk1 != sk2, "Secret keys should be unique"


# ══════════════════════════════════════════════════════════════════════════════
# SIGN/VERIFY TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_mldsa65_sign_verify(keypair, test_message):
    """
    INV-PQC-004: Verify ML-DSA-65 sign/verify cycle.
    
    Tests:
      - Message signing completes without error
      - Signature has correct size (3309 bytes)
      - Signature verification returns True for valid signature
    """
    public_key, secret_key = keypair
    
    # Sign
    signature = ml_dsa_65.sign(secret_key, test_message)
    assert isinstance(signature, bytes), "Signature should be bytes"
    assert len(signature) == 3309, f"Signature size mismatch: {len(signature)} != 3309"
    
    # Verify
    is_valid = ml_dsa_65.verify(public_key, test_message, signature)
    assert is_valid is True, "Valid signature should verify as True"


def test_mldsa65_invalid_signature_rejection(keypair, test_message):
    """
    INV-PQC-004: Verify invalid signatures are rejected.
    
    Tests:
      - Tampered message fails verification
      - Wrong public key fails verification
    """
    public_key, secret_key = keypair
    
    # Sign original message
    signature = ml_dsa_65.sign(secret_key, test_message)
    
    # Test 1: Tampered message should fail
    tampered_message = b"This is a tampered message"
    result = ml_dsa_65.verify(public_key, tampered_message, signature)
    assert result is False, "Tampered message should fail verification"
    
    # Test 2: Wrong public key should fail
    wrong_pk, _ = ml_dsa_65.generate_keypair()
    result = ml_dsa_65.verify(wrong_pk, test_message, signature)
    assert result is False, "Wrong public key should fail verification"


def test_mldsa65_corrupted_signature_rejection(keypair, test_message):
    """Verify corrupted signatures are rejected."""
    public_key, secret_key = keypair
    
    signature = ml_dsa_65.sign(secret_key, test_message)
    
    # Corrupt the signature by flipping bits
    corrupted_sig = bytearray(signature)
    corrupted_sig[0] ^= 0xFF  # Flip all bits in first byte
    corrupted_sig = bytes(corrupted_sig)
    
    result = ml_dsa_65.verify(public_key, test_message, corrupted_sig)
    assert result is False, "Corrupted signature should fail verification"


# ══════════════════════════════════════════════════════════════════════════════
# EMPTY MESSAGE TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_mldsa65_empty_message(keypair):
    """Verify empty message can be signed and verified."""
    public_key, secret_key = keypair
    
    empty_message = b""
    signature = ml_dsa_65.sign(secret_key, empty_message)
    
    result = ml_dsa_65.verify(public_key, empty_message, signature)
    assert result is True, "Empty message should verify successfully"


# ══════════════════════════════════════════════════════════════════════════════
# LARGE MESSAGE TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_mldsa65_large_message(keypair):
    """Verify large message can be signed and verified."""
    public_key, secret_key = keypair
    
    # 1MB message
    large_message = b"X" * (1024 * 1024)
    signature = ml_dsa_65.sign(secret_key, large_message)
    
    result = ml_dsa_65.verify(public_key, large_message, signature)
    assert result is True, "Large message should verify successfully"


# ══════════════════════════════════════════════════════════════════════════════
# CRYPTOGRAPHY COMPATIBILITY TEST
# ══════════════════════════════════════════════════════════════════════════════

def test_cryptography_coexistence():
    """
    INV-PQC-003: Verify pqcrypto works alongside cryptography package.
    
    Tests that both packages can be imported and used in the same process
    without conflicts.
    """
    if not PQCRYPTO_AVAILABLE:
        pytest.skip("pqcrypto not available")
    
    # Import cryptography
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ed25519
    
    # Generate ED25519 key (current implementation)
    ed_private = ed25519.Ed25519PrivateKey.generate()
    ed_public = ed_private.public_key()
    
    # Sign with ED25519
    ed_message = b"Test message for ED25519"
    ed_signature = ed_private.sign(ed_message)
    
    # Verify ED25519
    ed_public.verify(ed_signature, ed_message)  # Raises if invalid
    
    # Now use ML-DSA-65
    ml_public, ml_secret = ml_dsa_65.generate_keypair()
    ml_message = b"Test message for ML-DSA-65"
    ml_signature = ml_dsa_65.sign(ml_secret, ml_message)
    
    assert ml_dsa_65.verify(ml_public, ml_message, ml_signature) is True
    
    # Both cryptographic systems work in same process
    assert True, "Both ED25519 and ML-DSA-65 work concurrently"


# ══════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("PAC-SEC-P818: ML-DSA-65 PQC Compatibility Test Harness")
    print("=" * 70)
    print()
    
    # Run with pytest
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    
    print()
    print("=" * 70)
    if exit_code == 0:
        print("✅ ALL TESTS PASSED - P818 INVARIANTS SATISFIED")
    else:
        print("❌ SOME TESTS FAILED - P818 INVARIANTS VIOLATED")
    print("=" * 70)
    
    sys.exit(exit_code)
