# ═══════════════════════════════════════════════════════════════════════════════
# Security Hardening Tests — PAC-BENSON-P23-C
#
# Tests for security hardening module.
# Validates input sanitization, threat detection, and audit logging.
#
# Authors:
# - SAM (GID-06) — Security Hardener
# - DAN (GID-07) — CI/Testing Lead
# ═══════════════════════════════════════════════════════════════════════════════

import pytest
from datetime import datetime, timezone

from core.security.hardening import (
    ThreatSeverity,
    ThreatPattern,
    THREAT_PATTERNS,
    InputSanitizer,
    SanitizationResult,
    get_security_headers,
    SECURITY_HEADERS,
    SecurityAuditEvent,
    SecurityAuditLogger,
    RateLimitContext,
)


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT SANITIZER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInputSanitizer:
    """Tests for InputSanitizer."""

    @pytest.fixture
    def sanitizer(self):
        return InputSanitizer()

    def test_basic_sanitization(self, sanitizer):
        """Basic strings pass through sanitized."""
        result = sanitizer.sanitize("Hello World")
        assert result.sanitized == "Hello World"
        assert not result.blocked
        assert len(result.threats_detected) == 0

    def test_html_escape(self, sanitizer):
        """HTML characters are escaped."""
        result = sanitizer.sanitize("<div>Test</div>")
        assert "&lt;div&gt;" in result.sanitized
        assert "&lt;/div&gt;" in result.sanitized

    def test_sql_injection_detected(self, sanitizer):
        """SQL injection patterns are detected."""
        result = sanitizer.sanitize("SELECT * FROM users WHERE id='1' OR '1'='1'--")
        assert result.blocked
        assert any(t.pattern_id == "TP-001" for t in result.threats_detected)

    def test_xss_script_tag_detected(self, sanitizer):
        """XSS script tags are detected."""
        result = sanitizer.sanitize("<script>alert('xss')</script>")
        assert result.blocked
        assert any(t.pattern_id == "TP-002" for t in result.threats_detected)

    def test_xss_event_handler_detected(self, sanitizer):
        """XSS event handlers are detected."""
        result = sanitizer.sanitize('<img onerror="alert(1)" src=x>')
        assert result.blocked
        assert any(t.pattern_id == "TP-003" for t in result.threats_detected)

    def test_path_traversal_detected(self, sanitizer):
        """Path traversal patterns are detected."""
        result = sanitizer.sanitize("../../../etc/passwd")
        assert result.blocked
        assert any(t.pattern_id == "TP-004" for t in result.threats_detected)

    def test_command_injection_detected(self, sanitizer):
        """Command injection patterns are detected."""
        result = sanitizer.sanitize("test; rm -rf /")
        assert result.blocked
        assert any(t.pattern_id == "TP-005" for t in result.threats_detected)

    def test_max_length_truncation(self, sanitizer):
        """Long inputs are truncated."""
        long_input = "a" * 20000
        result = sanitizer.sanitize(long_input)
        assert len(result.sanitized) == sanitizer.max_length

    def test_null_byte_removal(self, sanitizer):
        """Null bytes are removed."""
        result = sanitizer.sanitize("test\x00value")
        assert "\x00" not in result.sanitized

    def test_whitespace_normalization(self, sanitizer):
        """Excessive whitespace is normalized."""
        result = sanitizer.sanitize("test   multiple   spaces")
        assert result.sanitized == "test multiple spaces"

    def test_is_safe_returns_bool(self, sanitizer):
        """is_safe returns boolean."""
        assert sanitizer.is_safe("Hello World") is True
        assert sanitizer.is_safe("<script>") is False


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY HEADERS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityHeaders:
    """Tests for security headers."""

    def test_default_headers_present(self):
        """All default security headers are present."""
        headers = get_security_headers()
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers
        assert "Referrer-Policy" in headers

    def test_x_frame_options_deny_by_default(self):
        """X-Frame-Options is DENY by default."""
        headers = get_security_headers()
        assert headers["X-Frame-Options"] == "DENY"

    def test_x_frame_options_sameorigin_when_allowed(self):
        """X-Frame-Options is SAMEORIGIN when frames allowed."""
        headers = get_security_headers(allow_frames=True)
        assert headers["X-Frame-Options"] == "SAMEORIGIN"

    def test_csp_nonce_injection(self):
        """CSP nonce is injected correctly."""
        nonce = "abc123"
        headers = get_security_headers(csp_nonce=nonce)
        assert f"'nonce-{nonce}'" in headers["Content-Security-Policy"]

    def test_cache_control_no_store(self):
        """Cache-Control prevents caching."""
        headers = get_security_headers()
        assert "no-store" in headers["Cache-Control"]


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY AUDIT LOGGER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityAuditLogger:
    """Tests for SecurityAuditLogger."""

    @pytest.fixture
    def logger(self):
        return SecurityAuditLogger()

    def test_log_threat(self, logger):
        """Threats are logged correctly."""
        threat = THREAT_PATTERNS[0]  # SQL Injection
        event = logger.log_threat(
            threat,
            source_ip="192.168.1.1",
            endpoint="/api/test",
        )
        
        assert event.event_type == "threat_detected"
        assert event.severity == threat.severity
        assert event.details["pattern_id"] == threat.pattern_id

    def test_log_access_denied(self, logger):
        """Access denied events are logged."""
        event = logger.log_access_denied(
            reason="Invalid token",
            source_ip="10.0.0.1",
            user_id="user123",
        )
        
        assert event.event_type == "access_denied"
        assert event.details["reason"] == "Invalid token"

    def test_evidence_hash_generated(self, logger):
        """Evidence hash is generated for events."""
        event = logger.log_access_denied(reason="Test")
        assert event.evidence_hash is not None
        assert len(event.evidence_hash) == 16

    def test_get_recent_events(self, logger):
        """Recent events are retrievable."""
        for i in range(5):
            logger.log_access_denied(reason=f"Reason {i}")
        
        events = logger.get_recent_events(limit=3)
        assert len(events) == 3

    def test_get_events_by_severity(self, logger):
        """Events can be filtered by severity."""
        threat = THREAT_PATTERNS[0]
        logger.log_threat(threat)
        logger.log_access_denied(reason="Test")
        
        critical_events = logger.get_events_by_severity(ThreatSeverity.CRITICAL)
        assert len(critical_events) == 1
        assert critical_events[0].severity == ThreatSeverity.CRITICAL


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMIT CONTEXT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRateLimitContext:
    """Tests for RateLimitContext."""

    def test_rate_limit_key_by_ip(self):
        """Rate limit key uses IP when no user/agent."""
        ctx = RateLimitContext(client_ip="192.168.1.1")
        assert ctx.rate_limit_key == "ip:192.168.1.1"

    def test_rate_limit_key_by_user(self):
        """Rate limit key prefers user ID."""
        ctx = RateLimitContext(client_ip="192.168.1.1", user_id="user123")
        assert ctx.rate_limit_key == "user:user123"

    def test_rate_limit_key_by_agent(self):
        """Rate limit key uses agent ID if no user."""
        ctx = RateLimitContext(client_ip="192.168.1.1", agent_id="GID-01")
        assert ctx.rate_limit_key == "agent:GID-01"


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT PATTERN TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestThreatPatterns:
    """Tests for threat pattern definitions."""

    def test_all_patterns_have_ids(self):
        """All threat patterns have unique IDs."""
        ids = [p.pattern_id for p in THREAT_PATTERNS]
        assert len(ids) == len(set(ids))

    def test_critical_patterns_blocked(self):
        """Critical severity patterns are blocked."""
        for pattern in THREAT_PATTERNS:
            if pattern.severity == ThreatSeverity.CRITICAL:
                assert pattern.blocked is True, f"{pattern.pattern_id} should be blocked"

    def test_patterns_are_compiled_regex(self):
        """All patterns are valid compiled regex."""
        import re
        for pattern in THREAT_PATTERNS:
            assert hasattr(pattern.pattern, 'search')
            assert callable(pattern.pattern.search)
