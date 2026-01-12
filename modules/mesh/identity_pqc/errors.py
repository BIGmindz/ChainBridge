#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         PQC ERROR HIERARCHY                                  ║
║                    PAC-SEC-P819 Implementation                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Typed exception hierarchy for PQC identity operations.
Each exception includes:
  - Error code for programmatic handling
  - Human-readable message
  - Recovery hints where applicable

Security Note: Exceptions NEVER include key material.
"""

from typing import Optional, Dict, Any


class PQCError(Exception):
    """
    Base exception for all PQC identity errors.
    
    Attributes:
        code: Machine-readable error code
        message: Human-readable error message
        details: Additional context (sanitized)
        recovery_hint: Suggested recovery action
    """
    
    code: str = "PQC_ERROR"
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None,
    ):
        self.message = message
        self.details = details or {}
        self.recovery_hint = recovery_hint
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format exception message."""
        parts = [f"[{self.code}] {self.message}"]
        if self.recovery_hint:
            parts.append(f"Recovery: {self.recovery_hint}")
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/API responses."""
        return {
            "error_code": self.code,
            "message": self.message,
            "details": self.details,
            "recovery_hint": self.recovery_hint,
        }


# ══════════════════════════════════════════════════════════════════════════════
# KEY GENERATION ERRORS
# ══════════════════════════════════════════════════════════════════════════════

class KeyGenerationError(PQCError):
    """Error during key pair generation."""
    
    code = "KEY_GENERATION_ERROR"
    
    def __init__(
        self,
        message: str = "Failed to generate key pair",
        algorithm: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if algorithm:
            details["algorithm"] = algorithm
        super().__init__(
            message=message,
            details=details,
            recovery_hint=kwargs.get("recovery_hint", "Check entropy source and retry"),
        )


class InsufficientEntropyError(KeyGenerationError):
    """Insufficient entropy for secure key generation."""
    
    code = "INSUFFICIENT_ENTROPY"
    
    def __init__(self, message: str = "Insufficient entropy for key generation"):
        super().__init__(
            message=message,
            recovery_hint="Ensure system entropy pool is available (e.g., /dev/urandom)",
        )


# ══════════════════════════════════════════════════════════════════════════════
# SIGNATURE ERRORS
# ══════════════════════════════════════════════════════════════════════════════

class SignatureError(PQCError):
    """Error during signature creation."""
    
    code = "SIGNATURE_ERROR"
    
    def __init__(
        self,
        message: str = "Failed to create signature",
        algorithm: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if algorithm:
            details["algorithm"] = algorithm
        super().__init__(
            message=message,
            details=details,
            recovery_hint=kwargs.get("recovery_hint"),
        )


class NoPrivateKeyError(SignatureError):
    """Attempted to sign without private key."""
    
    code = "NO_PRIVATE_KEY"
    
    def __init__(self, message: str = "Cannot sign: no private key available"):
        super().__init__(
            message=message,
            recovery_hint="Load identity with private key or generate new identity",
        )


class MessageTooLargeError(SignatureError):
    """Message exceeds maximum allowed size."""
    
    code = "MESSAGE_TOO_LARGE"
    
    def __init__(self, actual_size: int, max_size: int):
        super().__init__(
            message=f"Message size {actual_size} exceeds maximum {max_size}",
            details={"actual_size": actual_size, "max_size": max_size},
            recovery_hint="Split message into smaller chunks",
        )


# ══════════════════════════════════════════════════════════════════════════════
# VERIFICATION ERRORS
# ══════════════════════════════════════════════════════════════════════════════

class VerificationError(PQCError):
    """Error during signature verification."""
    
    code = "VERIFICATION_ERROR"
    
    def __init__(
        self,
        message: str = "Signature verification failed",
        reason: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.pop("details", {})
        if reason:
            details["reason"] = reason
        super().__init__(
            message=message,
            details=details,
            recovery_hint=kwargs.get("recovery_hint"),
        )


class InvalidSignatureError(VerificationError):
    """Signature is cryptographically invalid."""
    
    code = "INVALID_SIGNATURE"
    
    def __init__(self, reason: str = "Signature does not match message"):
        super().__init__(
            message="Invalid signature",
            reason=reason,
        )


class SignatureMalformedError(VerificationError):
    """Signature format is malformed."""
    
    code = "SIGNATURE_MALFORMED"
    
    def __init__(self, expected_size: int, actual_size: int):
        super().__init__(
            message=f"Malformed signature: expected {expected_size} bytes, got {actual_size}",
            details={"expected_size": expected_size, "actual_size": actual_size},
            recovery_hint="Ensure signature was not truncated or corrupted",
        )


class SignatureModeError(VerificationError):
    """Signature mode mismatch or unsupported."""
    
    code = "SIGNATURE_MODE_ERROR"
    
    def __init__(self, expected: str, actual: str):
        super().__init__(
            message=f"Signature mode mismatch: expected {expected}, got {actual}",
            details={"expected_mode": expected, "actual_mode": actual},
        )


# ══════════════════════════════════════════════════════════════════════════════
# SERIALIZATION ERRORS
# ══════════════════════════════════════════════════════════════════════════════

class SerializationError(PQCError):
    """Error during identity serialization/deserialization."""
    
    code = "SERIALIZATION_ERROR"


class InvalidVersionError(SerializationError):
    """Unsupported identity format version."""
    
    code = "INVALID_VERSION"
    
    def __init__(self, version: str, supported_versions: list):
        super().__init__(
            message=f"Unsupported identity version: {version}",
            details={"version": version, "supported": supported_versions},
            recovery_hint="Upgrade ChainBridge to support this version",
        )


class MissingFieldError(SerializationError):
    """Required field missing from serialized identity."""
    
    code = "MISSING_FIELD"
    
    def __init__(self, field_name: str):
        super().__init__(
            message=f"Missing required field: {field_name}",
            details={"field": field_name},
        )


class CorruptedDataError(SerializationError):
    """Identity data is corrupted."""
    
    code = "CORRUPTED_DATA"
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Identity data corrupted: {reason}",
            recovery_hint="Restore from backup or regenerate identity",
        )


# ══════════════════════════════════════════════════════════════════════════════
# MIGRATION ERRORS
# ══════════════════════════════════════════════════════════════════════════════

class MigrationError(PQCError):
    """Error during identity migration."""
    
    code = "MIGRATION_ERROR"


class UnsupportedMigrationError(MigrationError):
    """Migration path not supported."""
    
    code = "UNSUPPORTED_MIGRATION"
    
    def __init__(self, from_version: str, to_version: str):
        super().__init__(
            message=f"Cannot migrate from {from_version} to {to_version}",
            details={"from_version": from_version, "to_version": to_version},
        )


class MigrationIntegrityError(MigrationError):
    """Migration would break identity integrity."""
    
    code = "MIGRATION_INTEGRITY_ERROR"
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Migration failed integrity check: {reason}",
            recovery_hint="Keep original identity file as backup",
        )


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION ERRORS
# ══════════════════════════════════════════════════════════════════════════════

class ValidationError(PQCError):
    """Input validation error."""
    
    code = "VALIDATION_ERROR"


class InvalidPublicKeyError(ValidationError):
    """Public key validation failed."""
    
    code = "INVALID_PUBLIC_KEY"
    
    def __init__(self, reason: str, key_type: Optional[str] = None):
        details = {"reason": reason}
        if key_type:
            details["key_type"] = key_type
        super().__init__(
            message=f"Invalid public key: {reason}",
            details=details,
        )


class InvalidNodeIdError(ValidationError):
    """Node ID validation failed."""
    
    code = "INVALID_NODE_ID"
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid node ID: {reason}",
            details={"reason": reason},
        )


class InvalidNodeNameError(ValidationError):
    """Node name validation failed."""
    
    code = "INVALID_NODE_NAME"
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid node name: {reason}",
            details={"reason": reason},
        )


# ══════════════════════════════════════════════════════════════════════════════
# BACKEND ERRORS
# ══════════════════════════════════════════════════════════════════════════════

class BackendError(PQCError):
    """Crypto backend error."""
    
    code = "BACKEND_ERROR"


class BackendNotAvailableError(BackendError):
    """Required crypto backend not available."""
    
    code = "BACKEND_NOT_AVAILABLE"
    
    def __init__(self, backend_name: str, install_hint: Optional[str] = None):
        recovery = install_hint or f"Install {backend_name} package"
        super().__init__(
            message=f"Crypto backend not available: {backend_name}",
            details={"backend": backend_name},
            recovery_hint=recovery,
        )


class BackendOperationError(BackendError):
    """Backend operation failed."""
    
    code = "BACKEND_OPERATION_ERROR"
    
    def __init__(self, operation: str, backend: str, reason: str):
        super().__init__(
            message=f"Backend {backend} failed on {operation}: {reason}",
            details={"operation": operation, "backend": backend, "reason": reason},
        )
