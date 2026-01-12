#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  PAC-SEC-P819: PQC IDENTITY TEST HARNESS                     ║
║                    Comprehensive Test Suite                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Test Configuration and Shared Fixtures for identity_pqc module.
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Generator

# Import from identity_pqc module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.mesh.identity_pqc import (
    HybridIdentity,
    HybridKeyPair,
    ED25519KeyPair,
    PQCKeyPair,
    HybridSignature,
    SignatureMode,
)
from modules.mesh.identity_pqc.constants import (
    ED25519_PUBLIC_KEY_SIZE,
    ED25519_PRIVATE_KEY_SIZE,
    ED25519_SIGNATURE_SIZE,
    MLDSA65_PUBLIC_KEY_SIZE,
    MLDSA65_PRIVATE_KEY_SIZE,
    MLDSA65_SIGNATURE_SIZE,
)
from modules.mesh.identity_pqc.backends.ed25519 import CryptographyED25519Backend
from modules.mesh.identity_pqc.backends.dilithium_py import DilithiumPyBackend


# ══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def ed25519_backend():
    """ED25519 crypto backend."""
    return CryptographyED25519Backend()


@pytest.fixture
def pqc_backend():
    """ML-DSA-65 crypto backend."""
    return DilithiumPyBackend()


@pytest.fixture
def ed25519_keypair(ed25519_backend) -> ED25519KeyPair:
    """Generate ED25519 key pair."""
    public, private = ed25519_backend.keygen()
    return ED25519KeyPair(public_key=public, private_key=private)


@pytest.fixture
def pqc_keypair(pqc_backend) -> PQCKeyPair:
    """Generate ML-DSA-65 key pair."""
    public, private = pqc_backend.keygen()
    return PQCKeyPair(public_key=public, private_key=private)


@pytest.fixture
def hybrid_keypair(ed25519_keypair, pqc_keypair) -> HybridKeyPair:
    """Generate hybrid key pair."""
    return HybridKeyPair(ed25519=ed25519_keypair, pqc=pqc_keypair)


@pytest.fixture
def hybrid_identity() -> HybridIdentity:
    """Generate a fresh hybrid identity."""
    return HybridIdentity.generate("TEST-NODE", "TEST-FEDERATION")


@pytest.fixture
def peer_identity() -> HybridIdentity:
    """Generate a peer identity for testing."""
    return HybridIdentity.generate("TEST-PEER", "TEST-FEDERATION")


@pytest.fixture
def test_message() -> bytes:
    """Standard test message."""
    return b"ChainBridge PAC-SEC-P819 Test Message"


@pytest.fixture
def large_message() -> bytes:
    """Large test message (1MB)."""
    return b"X" * (1024 * 1024)


@pytest.fixture
def empty_message() -> bytes:
    """Empty message for edge case testing."""
    return b""


@pytest.fixture
def temp_identity_dir() -> Generator[str, None, None]:
    """Temporary directory for identity files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_identity_file(temp_identity_dir) -> str:
    """Path for temporary identity file."""
    return os.path.join(temp_identity_dir, "test_identity.json")


# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def create_corrupted_signature(signature: bytes, position: int = 0) -> bytes:
    """Create a corrupted version of a signature."""
    corrupted = bytearray(signature)
    corrupted[position] ^= 0xFF
    return bytes(corrupted)


def create_truncated_data(data: bytes, length: int) -> bytes:
    """Create truncated version of data."""
    return data[:length]


# ══════════════════════════════════════════════════════════════════════════════
# PYTEST CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "security: mark test as security-focused"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance benchmark"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "edge_case: mark test as edge case test"
    )
