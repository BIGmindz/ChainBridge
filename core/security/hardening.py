# ═══════════════════════════════════════════════════════════════════════════════
# Security Hardening Module — Platform-Wide Security Enforcement
# PAC-BENSON-P23-C: Parallel Platform Hardening (Corrective)
#
# Provides security utilities and validators for the ChainBridge platform:
# - Input sanitization
# - Rate limiting helpers
# - Security headers enforcement
# - Threat pattern detection
# - Audit logging
#
# INVARIANTS:
# - INV-SEC-001: No unbounded attack surface
# - INV-SEC-002: All inputs sanitized
# - INV-SEC-003: Security headers enforced
#
# Author: SAM (GID-06) — Security Hardener
# ═══════════════════════════════════════════════════════════════════════════════

from __future__ import annotations

import hashlib
import html
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Pattern, Set

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT SEVERITY
# ═══════════════════════════════════════════════════════════════════════════════

class ThreatSeverity(str, Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ThreatPattern:
    """Definition of a security threat pattern."""
    pattern_id: str
    name: str
    pattern: Pattern[str]
    severity: ThreatSeverity
    description: str
    blocked: bool = True


# Compiled threat patterns for input validation
THREAT_PATTERNS: List[ThreatPattern] = [
    ThreatPattern(
        pattern_id="TP-001",
        name="SQL Injection",
        pattern=re.compile(r"('|--|;|/\*|\*/|xp_|sp_|0x)", re.IGNORECASE),
        severity=ThreatSeverity.CRITICAL,
        description="SQL injection attempt detected",
    ),
    ThreatPattern(
        pattern_id="TP-002",
        name="XSS Script Tag",
        pattern=re.compile(r"<script[^>]*>", re.IGNORECASE),
        severity=ThreatSeverity.CRITICAL,
        description="Cross-site scripting attempt detected",
    ),
    ThreatPattern(
        pattern_id="TP-003",
        name="XSS Event Handler",
        pattern=re.compile(r"on\w+\s*=", re.IGNORECASE),
        severity=ThreatSeverity.HIGH,
        description="XSS event handler injection attempt",
    ),
    ThreatPattern(
        pattern_id="TP-004",
        name="Path Traversal",
        pattern=re.compile(r"\.\./|\.\.\\", re.IGNORECASE),
        severity=ThreatSeverity.HIGH,
        description="Path traversal attempt detected",
    ),
    ThreatPattern(
        pattern_id="TP-005",
        name="Command Injection",
        pattern=re.compile(r"[;&|`$]|\$\(|\$\{", re.IGNORECASE),
        severity=ThreatSeverity.CRITICAL,
        description="Command injection attempt detected",
    ),
    ThreatPattern(
        pattern_id="TP-006",
        name="LDAP Injection",
        pattern=re.compile(r"[)(|*\\]", re.IGNORECASE),
        severity=ThreatSeverity.HIGH,
        description="LDAP injection attempt detected",
        blocked=False,  # May have false positives
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT SANITIZER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SanitizationResult:
    """Result of input sanitization."""
    original: str
    sanitized: str
    threats_detected: List[ThreatPattern] = field(default_factory=list)
    blocked: bool = False
    sanitized_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class InputSanitizer:
    """
    Input sanitizer with threat detection.
    
    INV-SEC-002: All inputs sanitized
    """
    
    def __init__(
        self,
        max_length: int = 10000,
        allow_html: bool = False,
        custom_patterns: Optional[List[ThreatPattern]] = None,
    ):
        self.max_length = max_length
        self.allow_html = allow_html
        self.patterns = THREAT_PATTERNS + (custom_patterns or [])
    
    def sanitize(self, value: str) -> SanitizationResult:
        """Sanitize input and detect threats."""
        if not isinstance(value, str):
            value = str(value)
        
        threats: List[ThreatPattern] = []
        blocked = False
        
        # Check length
        if len(value) > self.max_length:
            value = value[:self.max_length]
            logger.warning(f"Input truncated to {self.max_length} characters")
        
        # Check for threat patterns
        for pattern in self.patterns:
            if pattern.pattern.search(value):
                threats.append(pattern)
                if pattern.blocked:
                    blocked = True
                    logger.warning(
                        f"Threat detected: {pattern.pattern_id} - {pattern.name}",
                        extra={"threat_id": pattern.pattern_id}
                    )
        
        # Sanitize HTML if not allowed
        sanitized = value
        if not self.allow_html:
            sanitized = html.escape(value)
        
        # Remove null bytes
        sanitized = sanitized.replace('\x00', '')
        
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        
        return SanitizationResult(
            original=value,
            sanitized=sanitized,
            threats_detected=threats,
            blocked=blocked,
        )
    
    def is_safe(self, value: str) -> bool:
        """Check if input is safe without sanitizing."""
        result = self.sanitize(value)
        return not result.blocked


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY HEADERS
# ═══════════════════════════════════════════════════════════════════════════════

SECURITY_HEADERS: Dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
    "Pragma": "no-cache",
}


def get_security_headers(
    csp_nonce: Optional[str] = None,
    allow_frames: bool = False,
) -> Dict[str, str]:
    """
    Get security headers for response.
    
    INV-SEC-003: Security headers enforced
    """
    headers = SECURITY_HEADERS.copy()
    
    if allow_frames:
        headers["X-Frame-Options"] = "SAMEORIGIN"
    
    if csp_nonce:
        headers["Content-Security-Policy"] = headers["Content-Security-Policy"].replace(
            "script-src 'self'",
            f"script-src 'self' 'nonce-{csp_nonce}'"
        )
    
    return headers


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOGGER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SecurityAuditEvent:
    """Security audit event."""
    event_id: str
    event_type: Literal["threat_detected", "access_denied", "rate_limited", "auth_failure", "input_sanitized"]
    severity: ThreatSeverity
    timestamp: datetime
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    endpoint: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    evidence_hash: Optional[str] = None
    
    def __post_init__(self):
        """Generate evidence hash."""
        if not self.evidence_hash:
            content = f"{self.event_id}:{self.event_type}:{self.timestamp.isoformat()}"
            self.evidence_hash = hashlib.sha256(content.encode()).hexdigest()[:16]


class SecurityAuditLogger:
    """
    Security audit logger with evidence hashing.
    
    Provides immutable audit trail per INV-OCC-005.
    """
    
    def __init__(self):
        self._events: List[SecurityAuditEvent] = []
        self._event_counter = 0
    
    def log_threat(
        self,
        threat: ThreatPattern,
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> SecurityAuditEvent:
        """Log a detected threat."""
        self._event_counter += 1
        event = SecurityAuditEvent(
            event_id=f"SEC-{self._event_counter:06d}",
            event_type="threat_detected",
            severity=threat.severity,
            timestamp=datetime.now(timezone.utc),
            source_ip=source_ip,
            user_id=user_id,
            endpoint=endpoint,
            details={
                "pattern_id": threat.pattern_id,
                "pattern_name": threat.name,
                "blocked": threat.blocked,
            },
        )
        self._events.append(event)
        logger.warning(
            f"Security threat logged: {event.event_id}",
            extra={"event": event.__dict__}
        )
        return event
    
    def log_access_denied(
        self,
        reason: str,
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> SecurityAuditEvent:
        """Log access denied event."""
        self._event_counter += 1
        event = SecurityAuditEvent(
            event_id=f"SEC-{self._event_counter:06d}",
            event_type="access_denied",
            severity=ThreatSeverity.MEDIUM,
            timestamp=datetime.now(timezone.utc),
            source_ip=source_ip,
            user_id=user_id,
            endpoint=endpoint,
            details={"reason": reason},
        )
        self._events.append(event)
        logger.info(f"Access denied: {event.event_id} - {reason}")
        return event
    
    def get_recent_events(self, limit: int = 100) -> List[SecurityAuditEvent]:
        """Get recent security events."""
        return self._events[-limit:]
    
    def get_events_by_severity(self, severity: ThreatSeverity) -> List[SecurityAuditEvent]:
        """Get events by severity."""
        return [e for e in self._events if e.severity == severity]


# Global audit logger instance
security_audit_logger = SecurityAuditLogger()


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMIT CONTEXT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RateLimitContext:
    """Context for rate limiting decisions."""
    client_ip: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    endpoint: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def rate_limit_key(self) -> str:
        """Generate rate limit key."""
        if self.user_id:
            return f"user:{self.user_id}"
        if self.agent_id:
            return f"agent:{self.agent_id}"
        return f"ip:{self.client_ip}"


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "ThreatSeverity",
    "ThreatPattern",
    "THREAT_PATTERNS",
    "SanitizationResult",
    "InputSanitizer",
    "SECURITY_HEADERS",
    "get_security_headers",
    "SecurityAuditEvent",
    "SecurityAuditLogger",
    "security_audit_logger",
    "RateLimitContext",
]
