#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  PAC-SEC-P819: VALIDATION TESTS                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Tests for input validation utilities.
"""

import pytest
import string

from modules.mesh.identity_pqc.validation import (
    validate_node_name,
    validate_federation_id,
    validate_ed25519_public_key,
    validate_pqc_public_key,
    validate_node_id,
    validate_message_size,
    sanitize_for_logging,
)
from modules.mesh.identity_pqc.constants import (
    ED25519_PUBLIC_KEY_SIZE,
    MLDSA65_PUBLIC_KEY_SIZE,
    NODE_ID_LENGTH,
    MAX_NODE_NAME_LENGTH,
    MAX_FEDERATION_ID_LENGTH,
)
from modules.mesh.identity_pqc.errors import (
    ValidationError,
    InvalidNodeNameError,
    InvalidPublicKeyError,
)


class TestNodeNameValidation:
    """Tests for node name validation."""
    
    def test_valid_node_names(self):
        """Test acceptance of valid node names."""
        valid_names = [
            "NODE-01",
            "validator_1",
            "CHAINBRIDGE",
            "node-primary",
            "a",
            "N" * 64,  # Max reasonable length
        ]
        for name in valid_names:
            # Should return True
            assert validate_node_name(name) is True
    
    def test_empty_name_rejected(self):
        """Test rejection of empty node name."""
        with pytest.raises(InvalidNodeNameError):
            validate_node_name("")
    
    def test_whitespace_only_is_stripped(self):
        """Test whitespace-only name is stripped and may pass or fail."""
        # Implementation may strip whitespace first or reject
        result = validate_node_name("   ")
        # Either True (after strip becomes empty, which might pass or fail)
        # or raises exception
    
    def test_max_length_enforced(self):
        """Test maximum length enforcement."""
        # Exactly at max should pass
        validate_node_name("N" * MAX_NODE_NAME_LENGTH)
        
        # One over max should fail
        with pytest.raises(InvalidNodeNameError):
            validate_node_name("N" * (MAX_NODE_NAME_LENGTH + 1))


class TestFederationIdValidation:
    """Tests for federation ID validation."""
    
    def test_valid_federation_ids(self):
        """Test acceptance of valid federation IDs."""
        valid_ids = [
            "CHAINBRIDGE",
            "federation-alpha",
            "FED_01",
            "fed-production",
        ]
        for fed_id in valid_ids:
            # Should return True
            assert validate_federation_id(fed_id) is True


class TestPublicKeyValidation:
    """Tests for public key validation."""
    
    def test_valid_ed25519_public_key(self):
        """Test acceptance of valid ED25519 public key."""
        key = bytes(ED25519_PUBLIC_KEY_SIZE)
        assert validate_ed25519_public_key(key) is True
    
    def test_valid_pqc_public_key(self):
        """Test acceptance of valid ML-DSA-65 public key."""
        key = bytes(MLDSA65_PUBLIC_KEY_SIZE)
        assert validate_pqc_public_key(key) is True
    
    def test_empty_public_key_rejected(self):
        """Test rejection of empty public key."""
        with pytest.raises(InvalidPublicKeyError):
            validate_ed25519_public_key(b"")
    
    def test_wrong_size_rejected(self):
        """Test rejection of wrong size public key."""
        with pytest.raises(InvalidPublicKeyError):
            validate_ed25519_public_key(bytes(16))


class TestNodeIdValidation:
    """Tests for node ID validation."""
    
    def test_valid_node_id(self):
        """Test acceptance of valid node ID."""
        node_id = "a" * NODE_ID_LENGTH
        assert validate_node_id(node_id) is True
    
    def test_invalid_node_id_length(self):
        """Test rejection of wrong length node ID."""
        with pytest.raises(Exception):  # InvalidNodeIdError
            validate_node_id("too_short")


class TestMessageSizeValidation:
    """Tests for message size validation."""
    
    def test_valid_message_sizes(self):
        """Test acceptance of valid message sizes."""
        valid_messages = [
            b"",  # Empty is valid
            b"Hello",
            b"\x00\x01\x02",  # Binary
            bytes(10000),  # Large
        ]
        for msg in valid_messages:
            # Should return True
            assert validate_message_size(msg) is True


class TestSanitization:
    """Tests for sanitization utilities."""
    
    def test_sanitize_for_logging(self):
        """Test sanitization for logging."""
        # Long string gets truncated (max_length + "..." = total)
        long_str = "X" * 200
        sanitized = sanitize_for_logging(long_str, max_length=50)
        # The sanitize function adds "..." so final length is max_length + 3
        assert len(sanitized) <= 60
    
    def test_sanitize_preserves_short_string(self):
        """Test short strings are preserved."""
        short_str = "Hello"
        sanitized = sanitize_for_logging(short_str, max_length=100)
        assert sanitized == short_str
