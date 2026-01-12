#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      INPUT VALIDATION                                        ║
║                    PAC-SEC-P819 Implementation                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Input validation utilities for PQC identity operations.
All external inputs must be validated before processing.
"""

from typing import Optional, Tuple
import re

from .constants import (
    ED25519_PUBLIC_KEY_SIZE,
    ED25519_PRIVATE_KEY_SIZE,
    ED25519_SIGNATURE_SIZE,
    MLDSA65_PUBLIC_KEY_SIZE,
    MLDSA65_PRIVATE_KEY_SIZE,
    MLDSA65_SIGNATURE_SIZE,
    NODE_ID_LENGTH,
    MAX_NODE_NAME_LENGTH,
    MAX_FEDERATION_ID_LENGTH,
    MAX_MESSAGE_SIZE,
    HYBRID_SIGNATURE_TOTAL_SIZE,
)
from .errors import (
    ValidationError,
    InvalidPublicKeyError,
    InvalidNodeIdError,
    InvalidNodeNameError,
    MessageTooLargeError,
    SignatureMalformedError,
)


def validate_ed25519_public_key(key: bytes) -> bool:
    """
    Validate ED25519 public key format.
    
    Args:
        key: Candidate public key bytes
        
    Returns:
        True if valid
        
    Raises:
        InvalidPublicKeyError: If invalid
    """
    if not isinstance(key, bytes):
        raise InvalidPublicKeyError("Public key must be bytes", key_type="ED25519")
    if len(key) != ED25519_PUBLIC_KEY_SIZE:
        raise InvalidPublicKeyError(
            f"Size must be {ED25519_PUBLIC_KEY_SIZE} bytes, got {len(key)}",
            key_type="ED25519",
        )
    return True


def validate_pqc_public_key(key: bytes) -> bool:
    """
    Validate ML-DSA-65 public key format.
    
    Args:
        key: Candidate public key bytes
        
    Returns:
        True if valid
        
    Raises:
        InvalidPublicKeyError: If invalid
    """
    if not isinstance(key, bytes):
        raise InvalidPublicKeyError("Public key must be bytes", key_type="ML-DSA-65")
    if len(key) != MLDSA65_PUBLIC_KEY_SIZE:
        raise InvalidPublicKeyError(
            f"Size must be {MLDSA65_PUBLIC_KEY_SIZE} bytes, got {len(key)}",
            key_type="ML-DSA-65",
        )
    return True


def validate_public_key(
    key: bytes,
    key_type: str = "ED25519",
) -> bool:
    """
    Validate public key based on type.
    
    Args:
        key: Candidate public key bytes
        key_type: "ED25519" or "ML-DSA-65"
        
    Returns:
        True if valid
        
    Raises:
        InvalidPublicKeyError: If invalid
    """
    if key_type == "ED25519":
        return validate_ed25519_public_key(key)
    elif key_type in ("ML-DSA-65", "MLDSA65", "PQC"):
        return validate_pqc_public_key(key)
    else:
        raise InvalidPublicKeyError(f"Unknown key type: {key_type}")


def validate_ed25519_signature(signature: bytes) -> bool:
    """
    Validate ED25519 signature format.
    
    Args:
        signature: Candidate signature bytes
        
    Returns:
        True if valid
        
    Raises:
        SignatureMalformedError: If invalid
    """
    if not isinstance(signature, bytes):
        raise SignatureMalformedError(ED25519_SIGNATURE_SIZE, 0)
    if len(signature) != ED25519_SIGNATURE_SIZE:
        raise SignatureMalformedError(ED25519_SIGNATURE_SIZE, len(signature))
    return True


def validate_pqc_signature(signature: bytes) -> bool:
    """
    Validate ML-DSA-65 signature format.
    
    Args:
        signature: Candidate signature bytes
        
    Returns:
        True if valid
        
    Raises:
        SignatureMalformedError: If invalid
    """
    if not isinstance(signature, bytes):
        raise SignatureMalformedError(MLDSA65_SIGNATURE_SIZE, 0)
    if len(signature) != MLDSA65_SIGNATURE_SIZE:
        raise SignatureMalformedError(MLDSA65_SIGNATURE_SIZE, len(signature))
    return True


def validate_signature(signature: bytes) -> Tuple[bool, str]:
    """
    Validate hybrid signature format and detect mode.
    
    Args:
        signature: Candidate signature bytes
        
    Returns:
        Tuple of (is_valid, detected_mode)
        
    Raises:
        SignatureMalformedError: If invalid
    """
    if not isinstance(signature, bytes) or len(signature) < 1:
        raise SignatureMalformedError(1, 0 if not isinstance(signature, bytes) else len(signature))
    
    version = signature[0]
    
    if version == 0x00:
        # Legacy ED25519
        expected = 1 + ED25519_SIGNATURE_SIZE
        if len(signature) != expected:
            raise SignatureMalformedError(expected, len(signature))
        return True, "LEGACY"
    
    elif version == 0x01:
        # Hybrid
        expected = HYBRID_SIGNATURE_TOTAL_SIZE
        if len(signature) != expected:
            raise SignatureMalformedError(expected, len(signature))
        return True, "HYBRID"
    
    elif version == 0x02:
        # PQC-only
        expected = 1 + MLDSA65_SIGNATURE_SIZE
        if len(signature) != expected:
            raise SignatureMalformedError(expected, len(signature))
        return True, "PQC_ONLY"
    
    else:
        raise SignatureMalformedError(0, len(signature))


def validate_node_id(node_id: str) -> bool:
    """
    Validate node ID format.
    
    Args:
        node_id: Candidate node ID
        
    Returns:
        True if valid
        
    Raises:
        InvalidNodeIdError: If invalid
    """
    if not isinstance(node_id, str):
        raise InvalidNodeIdError("Node ID must be a string")
    if len(node_id) != NODE_ID_LENGTH:
        raise InvalidNodeIdError(f"Length must be {NODE_ID_LENGTH}, got {len(node_id)}")
    if not re.match(r'^[0-9a-f]+$', node_id):
        raise InvalidNodeIdError("Must contain only lowercase hex characters")
    return True


def validate_node_name(name: str) -> bool:
    """
    Validate node name format.
    
    Args:
        name: Candidate node name
        
    Returns:
        True if valid
        
    Raises:
        InvalidNodeNameError: If invalid
    """
    if not isinstance(name, str):
        raise InvalidNodeNameError("Node name must be a string")
    if not name:
        raise InvalidNodeNameError("Node name cannot be empty")
    if len(name) > MAX_NODE_NAME_LENGTH:
        raise InvalidNodeNameError(f"Length exceeds maximum {MAX_NODE_NAME_LENGTH}")
    # Basic sanitization - no control characters
    if any(ord(c) < 32 for c in name):
        raise InvalidNodeNameError("Node name contains control characters")
    return True


def validate_federation_id(federation_id: str) -> bool:
    """
    Validate federation ID format.
    
    Args:
        federation_id: Candidate federation ID
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If invalid
    """
    if not isinstance(federation_id, str):
        raise ValidationError("Federation ID must be a string")
    if not federation_id:
        raise ValidationError("Federation ID cannot be empty")
    if len(federation_id) > MAX_FEDERATION_ID_LENGTH:
        raise ValidationError(f"Federation ID exceeds maximum length {MAX_FEDERATION_ID_LENGTH}")
    return True


def validate_message_size(message: bytes) -> bool:
    """
    Validate message size for signing.
    
    Args:
        message: Message to validate
        
    Returns:
        True if valid
        
    Raises:
        MessageTooLargeError: If message exceeds limit
    """
    if not isinstance(message, bytes):
        raise ValidationError("Message must be bytes")
    if len(message) > MAX_MESSAGE_SIZE:
        raise MessageTooLargeError(len(message), MAX_MESSAGE_SIZE)
    return True


def sanitize_for_logging(value: str, max_length: int = 100) -> str:
    """
    Sanitize a value for safe logging.
    
    Args:
        value: Value to sanitize
        max_length: Maximum output length
        
    Returns:
        Sanitized string safe for logging
    """
    if not isinstance(value, str):
        value = str(value)
    # Remove potential control characters
    sanitized = ''.join(c if ord(c) >= 32 else '?' for c in value)
    # Truncate if needed
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized
