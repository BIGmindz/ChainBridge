# ═══════════════════════════════════════════════════════════════════════════════
# Control Plane Security — Enterprise-Grade Security Primitives
# PAC-BENSON-P24: CONTROL PLANE CORE HARDENING
# Agent: SAM (GID-06) — Control Plane Security
# ═══════════════════════════════════════════════════════════════════════════════

"""
Control Plane Security Module

PURPOSE:
    Provide enterprise-grade security primitives for the control plane.
    Protects PAC, WRAP, BER, and PDO artifacts from tampering.

INVARIANTS:
    INV-SEC-CP-001: All control plane operations must be authenticated
    INV-SEC-CP-002: Authority delegation must be explicit and audited
    INV-SEC-CP-003: No anonymous mutations to control plane state
    INV-SEC-CP-004: Cryptographic verification required for all artifacts
    INV-SEC-CP-005: Rate limiting on sensitive operations

EXECUTION MODE: PARALLEL
LANE: SECURITY (GID-06)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

CONTROL_PLANE_SECURITY_VERSION = "1.0.0"
"""Module version."""

# Authority levels
AUTHORITY_LEVELS: FrozenSet[str] = frozenset({
    "FINAL",       # Full authority (CTO-level)
    "DELEGATED",   # Delegated authority (Lead-level)
    "AGENT",       # Agent authority (GID-level)
    "READONLY",    # Read-only access
})

# Sensitive operations requiring extra validation
SENSITIVE_OPERATIONS: FrozenSet[str] = frozenset({
    "PAC_CREATE",
    "PAC_SUPERSEDE",
    "WRAP_SUBMIT",
    "BER_ISSUE",
    "PDO_CREATE",
    "LEDGER_COMMIT",
    "SCHEMA_REGISTER",
})

# Rate limit windows (operation -> (max_count, window_seconds))
RATE_LIMITS: Dict[str, Tuple[int, int]] = {
    "PAC_CREATE": (10, 60),       # 10 per minute
    "WRAP_SUBMIT": (50, 60),      # 50 per minute
    "BER_ISSUE": (10, 60),        # 10 per minute
    "PDO_CREATE": (50, 60),       # 50 per minute
    "LEDGER_COMMIT": (100, 60),   # 100 per minute
}


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class ControlPlaneSecurityError(Exception):
    """Base exception for control plane security errors."""
    pass


class AuthenticationError(ControlPlaneSecurityError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str, principal: Optional[str] = None):
        self.principal = principal
        super().__init__(
            f"AUTHENTICATION_FAILED: {message}"
            + (f" (principal: {principal})" if principal else "")
        )


class AuthorizationError(ControlPlaneSecurityError):
    """Raised when authorization fails."""
    
    def __init__(
        self, operation: str, required_authority: str, actual_authority: str
    ):
        self.operation = operation
        self.required_authority = required_authority
        self.actual_authority = actual_authority
        super().__init__(
            f"AUTHORIZATION_DENIED: Operation '{operation}' requires "
            f"'{required_authority}' authority, but principal has "
            f"'{actual_authority}' (INV-SEC-CP-001)"
        )


class RateLimitExceededError(ControlPlaneSecurityError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, operation: str, limit: int, window: int):
        self.operation = operation
        self.limit = limit
        self.window = window
        super().__init__(
            f"RATE_LIMIT_EXCEEDED: Operation '{operation}' limited to "
            f"{limit} calls per {window}s (INV-SEC-CP-005)"
        )


class SignatureVerificationError(ControlPlaneSecurityError):
    """Raised when signature verification fails."""
    
    def __init__(self, artifact_id: str, artifact_type: str):
        self.artifact_id = artifact_id
        self.artifact_type = artifact_type
        super().__init__(
            f"SIGNATURE_INVALID: {artifact_type} '{artifact_id}' has invalid "
            f"or missing signature (INV-SEC-CP-004)"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PRINCIPAL & AUTHORITY
# ═══════════════════════════════════════════════════════════════════════════════

class AuthorityLevel(str, Enum):
    """Authority levels for control plane access."""
    FINAL = "FINAL"           # Full authority
    DELEGATED = "DELEGATED"   # Delegated authority
    AGENT = "AGENT"           # Agent-level
    READONLY = "READONLY"     # Read-only


@dataclass(frozen=True)
class Principal:
    """
    Security principal for control plane operations.
    
    Represents an authenticated identity with authority level.
    """
    principal_id: str
    authority: AuthorityLevel
    gid: Optional[str] = None
    delegated_by: Optional[str] = None
    permissions: FrozenSet[str] = field(default_factory=frozenset)
    
    def can_perform(self, operation: str) -> bool:
        """Check if principal can perform operation."""
        # FINAL authority can do anything
        if self.authority == AuthorityLevel.FINAL:
            return True
        
        # READONLY can't do sensitive operations
        if self.authority == AuthorityLevel.READONLY:
            return operation not in SENSITIVE_OPERATIONS
        
        # Check specific permissions
        return operation in self.permissions
    
    def is_agent(self, gid: str) -> bool:
        """Check if principal is a specific agent."""
        return self.gid == gid


@dataclass
class AuthorityDelegation:
    """Record of authority delegation."""
    delegation_id: str
    delegator: str
    delegatee: str
    operations: FrozenSet[str]
    expires_at: Optional[str]
    created_at: str
    revoked: bool = False
    
    def is_active(self) -> bool:
        """Check if delegation is still active."""
        if self.revoked:
            return False
        if self.expires_at:
            expiry = datetime.fromisoformat(self.expires_at)
            if datetime.now(timezone.utc) > expiry:
                return False
        return True


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER
# ═══════════════════════════════════════════════════════════════════════════════

class ControlPlaneRateLimiter:
    """
    Rate limiter for control plane operations.
    
    INV-SEC-CP-005: Rate limiting on sensitive operations
    """
    
    def __init__(self) -> None:
        self._calls: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
    
    def check(self, operation: str, principal_id: str) -> None:
        """
        Check rate limit for operation.
        
        Raises RateLimitExceededError if limit exceeded.
        """
        if operation not in RATE_LIMITS:
            return  # No limit defined
        
        limit, window = RATE_LIMITS[operation]
        key = f"{principal_id}:{operation}"
        now = time.time()
        
        with self._lock:
            if key not in self._calls:
                self._calls[key] = []
            
            # Remove old calls outside window
            self._calls[key] = [
                t for t in self._calls[key]
                if now - t < window
            ]
            
            # Check limit
            if len(self._calls[key]) >= limit:
                raise RateLimitExceededError(operation, limit, window)
            
            # Record this call
            self._calls[key].append(now)
    
    def reset(self, principal_id: Optional[str] = None) -> None:
        """Reset rate limit counters."""
        with self._lock:
            if principal_id:
                self._calls = {
                    k: v for k, v in self._calls.items()
                    if not k.startswith(f"{principal_id}:")
                }
            else:
                self._calls = {}


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNATURE SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class ArtifactSignatureService:
    """
    Cryptographic signature service for control plane artifacts.
    
    INV-SEC-CP-004: Cryptographic verification required for all artifacts
    """
    
    def __init__(self, secret_key: Optional[str] = None) -> None:
        """Initialize with secret key (generates one if not provided)."""
        self._secret_key = (
            secret_key.encode() if secret_key
            else secrets.token_bytes(32)
        )
        self._signatures: Dict[str, str] = {}
        self._lock = threading.Lock()
    
    def sign(self, artifact_id: str, artifact_data: Dict[str, Any]) -> str:
        """
        Sign an artifact and return the signature.
        
        Uses HMAC-SHA256 for signing.
        """
        canonical = json.dumps(artifact_data, sort_keys=True, separators=(",", ":"))
        signature = hmac.new(
            self._secret_key,
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()
        
        with self._lock:
            self._signatures[artifact_id] = signature
        
        return signature
    
    def verify(
        self, artifact_id: str, artifact_data: Dict[str, Any], signature: str
    ) -> bool:
        """
        Verify artifact signature.
        
        Returns True if valid, raises SignatureVerificationError otherwise.
        """
        expected = self.sign(artifact_id, artifact_data)
        
        if not hmac.compare_digest(signature, expected):
            artifact_type = artifact_data.get("type", "UNKNOWN")
            raise SignatureVerificationError(artifact_id, artifact_type)
        
        return True
    
    def get_stored_signature(self, artifact_id: str) -> Optional[str]:
        """Get stored signature for artifact."""
        with self._lock:
            return self._signatures.get(artifact_id)


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SecurityAuditEntry:
    """Security audit log entry."""
    entry_id: str
    timestamp: str
    operation: str
    principal_id: str
    authority: str
    success: bool
    artifact_id: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "operation": self.operation,
            "principal_id": self.principal_id,
            "authority": self.authority,
            "success": self.success,
            "artifact_id": self.artifact_id,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


class SecurityAuditLog:
    """
    Security audit log for control plane operations.
    
    INV-SEC-CP-002: Authority delegation must be explicit and audited
    INV-SEC-CP-003: No anonymous mutations to control plane state
    """
    
    def __init__(self) -> None:
        self._entries: List[SecurityAuditEntry] = []
        self._lock = threading.Lock()
        self._entry_counter = 0
    
    def log(
        self,
        operation: str,
        principal: Principal,
        success: bool,
        artifact_id: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log security event and return entry ID."""
        with self._lock:
            self._entry_counter += 1
            entry_id = f"SEC-{self._entry_counter:08d}"
            
            entry = SecurityAuditEntry(
                entry_id=entry_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                operation=operation,
                principal_id=principal.principal_id,
                authority=principal.authority.value,
                success=success,
                artifact_id=artifact_id,
                error_message=error_message,
                metadata=metadata,
            )
            
            self._entries.append(entry)
            return entry_id
    
    def get_entries(
        self,
        principal_id: Optional[str] = None,
        operation: Optional[str] = None,
        since: Optional[str] = None,
        limit: int = 100,
    ) -> List[SecurityAuditEntry]:
        """Query audit log entries."""
        with self._lock:
            entries = self._entries.copy()
        
        if principal_id:
            entries = [e for e in entries if e.principal_id == principal_id]
        
        if operation:
            entries = [e for e in entries if e.operation == operation]
        
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        
        return entries[-limit:]
    
    def count(self) -> int:
        """Get total entry count."""
        with self._lock:
            return len(self._entries)


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════

class ControlPlaneSecurityContext:
    """
    Central security context for control plane operations.
    
    Combines authentication, authorization, rate limiting, and auditing.
    """
    
    _instance: Optional["ControlPlaneSecurityContext"] = None
    
    def __new__(cls) -> "ControlPlaneSecurityContext":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._rate_limiter = ControlPlaneRateLimiter()
            cls._instance._signature_service = ArtifactSignatureService()
            cls._instance._audit_log = SecurityAuditLog()
            cls._instance._principals: Dict[str, Principal] = {}
            cls._instance._delegations: List[AuthorityDelegation] = []
        return cls._instance
    
    def register_principal(self, principal: Principal) -> None:
        """Register a security principal."""
        self._principals[principal.principal_id] = principal
    
    def get_principal(self, principal_id: str) -> Optional[Principal]:
        """Get registered principal."""
        return self._principals.get(principal_id)
    
    def authorize_operation(
        self,
        principal: Principal,
        operation: str,
        artifact_id: Optional[str] = None,
    ) -> None:
        """
        Authorize operation for principal.
        
        Raises AuthorizationError if not authorized.
        """
        # Check rate limit
        self._rate_limiter.check(operation, principal.principal_id)
        
        # Check authorization
        if not principal.can_perform(operation):
            required = "FINAL" if operation in SENSITIVE_OPERATIONS else "AGENT"
            self._audit_log.log(
                operation=operation,
                principal=principal,
                success=False,
                artifact_id=artifact_id,
                error_message=f"Insufficient authority for {operation}",
            )
            raise AuthorizationError(
                operation, required, principal.authority.value
            )
        
        # Log successful authorization
        self._audit_log.log(
            operation=operation,
            principal=principal,
            success=True,
            artifact_id=artifact_id,
        )
    
    def sign_artifact(
        self, artifact_id: str, artifact_data: Dict[str, Any]
    ) -> str:
        """Sign artifact and return signature."""
        return self._signature_service.sign(artifact_id, artifact_data)
    
    def verify_artifact(
        self, artifact_id: str, artifact_data: Dict[str, Any], signature: str
    ) -> bool:
        """Verify artifact signature."""
        return self._signature_service.verify(artifact_id, artifact_data, signature)
    
    def get_audit_log(self) -> SecurityAuditLog:
        """Get security audit log."""
        return self._audit_log
    
    def delegate_authority(
        self,
        delegator: Principal,
        delegatee_id: str,
        operations: Set[str],
        expires_at: Optional[str] = None,
    ) -> AuthorityDelegation:
        """
        Delegate authority to another principal.
        
        INV-SEC-CP-002: Authority delegation must be explicit and audited
        """
        # Only FINAL authority can delegate
        if delegator.authority != AuthorityLevel.FINAL:
            raise AuthorizationError(
                "DELEGATE_AUTHORITY", "FINAL", delegator.authority.value
            )
        
        delegation = AuthorityDelegation(
            delegation_id=secrets.token_hex(8),
            delegator=delegator.principal_id,
            delegatee=delegatee_id,
            operations=frozenset(operations),
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        self._delegations.append(delegation)
        
        # Audit the delegation
        self._audit_log.log(
            operation="DELEGATE_AUTHORITY",
            principal=delegator,
            success=True,
            metadata={
                "delegatee": delegatee_id,
                "operations": list(operations),
            },
        )
        
        return delegation


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY DECORATOR
# ═══════════════════════════════════════════════════════════════════════════════

T = TypeVar("T")


def secure_operation(operation_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to enforce security on control plane operations.
    
    Requires principal as first argument to decorated function.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(principal: Principal, *args: Any, **kwargs: Any) -> T:
            ctx = ControlPlaneSecurityContext()
            
            # Extract artifact_id if present
            artifact_id = kwargs.get("artifact_id") or (
                args[0] if args and isinstance(args[0], str) else None
            )
            
            # Authorize operation
            ctx.authorize_operation(principal, operation_name, artifact_id)
            
            # Execute operation
            return func(principal, *args, **kwargs)
        
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Version
    "CONTROL_PLANE_SECURITY_VERSION",
    
    # Constants
    "AUTHORITY_LEVELS",
    "SENSITIVE_OPERATIONS",
    "RATE_LIMITS",
    
    # Exceptions
    "ControlPlaneSecurityError",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitExceededError",
    "SignatureVerificationError",
    
    # Principal & Authority
    "AuthorityLevel",
    "Principal",
    "AuthorityDelegation",
    
    # Components
    "ControlPlaneRateLimiter",
    "ArtifactSignatureService",
    "SecurityAuditEntry",
    "SecurityAuditLog",
    "ControlPlaneSecurityContext",
    
    # Decorator
    "secure_operation",
]
