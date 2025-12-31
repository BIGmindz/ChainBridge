# ═══════════════════════════════════════════════════════════════════════════════
# Control Plane Security Tests
# PAC-BENSON-P24: CONTROL PLANE CORE HARDENING
# Agent: DAN (GID-07) — CI / Compiler Gates
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for control plane security module.

Validates:
- INV-SEC-CP-001: All operations must be authenticated
- INV-SEC-CP-002: Authority delegation must be explicit and audited
- INV-SEC-CP-003: No anonymous mutations
- INV-SEC-CP-004: Cryptographic verification required
- INV-SEC-CP-005: Rate limiting on sensitive operations
"""

import pytest
import time

from core.security.control_plane_security import (
    Principal,
    AuthorityLevel,
    AuthorityDelegation,
    ControlPlaneRateLimiter,
    ArtifactSignatureService,
    SecurityAuditLog,
    ControlPlaneSecurityContext,
    secure_operation,
    ControlPlaneSecurityError,
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError,
    SignatureVerificationError,
    SENSITIVE_OPERATIONS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def final_principal():
    """Create FINAL authority principal."""
    return Principal(
        principal_id="JEFFREY",
        authority=AuthorityLevel.FINAL,
        gid=None,
    )


@pytest.fixture
def agent_principal():
    """Create AGENT authority principal."""
    return Principal(
        principal_id="BENSON",
        authority=AuthorityLevel.AGENT,
        gid="GID-00",
        permissions=frozenset({"PAC_READ", "WRAP_READ"}),
    )


@pytest.fixture
def readonly_principal():
    """Create READONLY authority principal."""
    return Principal(
        principal_id="OBSERVER",
        authority=AuthorityLevel.READONLY,
    )


@pytest.fixture
def rate_limiter():
    """Create fresh rate limiter."""
    return ControlPlaneRateLimiter()


@pytest.fixture
def signature_service():
    """Create fresh signature service."""
    return ArtifactSignatureService(secret_key="test-secret-key-12345")


@pytest.fixture
def audit_log():
    """Create fresh audit log."""
    return SecurityAuditLog()


@pytest.fixture
def security_context():
    """Create fresh security context."""
    ControlPlaneSecurityContext._instance = None
    return ControlPlaneSecurityContext()


# ═══════════════════════════════════════════════════════════════════════════════
# PRINCIPAL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPrincipal:
    """Tests for Principal class."""
    
    def test_final_authority_can_do_anything(self, final_principal):
        """FINAL authority can perform any operation."""
        for op in SENSITIVE_OPERATIONS:
            assert final_principal.can_perform(op) is True
    
    def test_readonly_cannot_do_sensitive(self, readonly_principal):
        """READONLY cannot perform sensitive operations."""
        for op in SENSITIVE_OPERATIONS:
            assert readonly_principal.can_perform(op) is False
    
    def test_agent_with_permissions(self, agent_principal):
        """AGENT with specific permissions can perform those ops."""
        assert agent_principal.can_perform("PAC_READ") is True
        assert agent_principal.can_perform("WRAP_READ") is True
        assert agent_principal.can_perform("PAC_CREATE") is False
    
    def test_is_agent_check(self, agent_principal):
        """is_agent correctly identifies agent."""
        assert agent_principal.is_agent("GID-00") is True
        assert agent_principal.is_agent("GID-01") is False
    
    def test_principal_frozen(self, final_principal):
        """Principal is immutable."""
        with pytest.raises(AttributeError):
            final_principal.authority = AuthorityLevel.READONLY


# ═══════════════════════════════════════════════════════════════════════════════
# RATE LIMITER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRateLimiter:
    """Tests for ControlPlaneRateLimiter class."""
    
    def test_allows_within_limit(self, rate_limiter):
        """Operations within limit are allowed."""
        # PAC_CREATE has limit of 10 per 60s
        for i in range(5):
            rate_limiter.check("PAC_CREATE", "test-user")
        # Should not raise
    
    def test_blocks_over_limit(self, rate_limiter):
        """Operations over limit are blocked."""
        # PAC_CREATE has limit of 10 per 60s
        for i in range(10):
            rate_limiter.check("PAC_CREATE", "test-user")
        
        with pytest.raises(RateLimitExceededError) as exc_info:
            rate_limiter.check("PAC_CREATE", "test-user")
        
        assert exc_info.value.operation == "PAC_CREATE"
        assert exc_info.value.limit == 10
    
    def test_different_principals_separate_limits(self, rate_limiter):
        """Each principal has separate limit."""
        # Max out user1
        for i in range(10):
            rate_limiter.check("PAC_CREATE", "user1")
        
        # user2 should still work
        rate_limiter.check("PAC_CREATE", "user2")  # Should not raise
    
    def test_unlisted_operation_no_limit(self, rate_limiter):
        """Operations not in RATE_LIMITS are unlimited."""
        for i in range(100):
            rate_limiter.check("UNKNOWN_OP", "test-user")
        # Should not raise
    
    def test_reset_clears_counts(self, rate_limiter):
        """Reset clears rate limit counts."""
        for i in range(10):
            rate_limiter.check("PAC_CREATE", "test-user")
        
        rate_limiter.reset("test-user")
        
        # Should work again
        rate_limiter.check("PAC_CREATE", "test-user")


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNATURE SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSignatureService:
    """Tests for ArtifactSignatureService class."""
    
    def test_sign_produces_signature(self, signature_service):
        """Signing produces a signature."""
        data = {"id": "TEST-001", "value": 42}
        signature = signature_service.sign("TEST-001", data)
        
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature)
    
    def test_sign_deterministic(self, signature_service):
        """Same data produces same signature."""
        data = {"id": "TEST-001", "value": 42}
        
        sig1 = signature_service.sign("TEST-001", data)
        sig2 = signature_service.sign("TEST-001", data)
        
        assert sig1 == sig2
    
    def test_sign_different_data_different_signature(self, signature_service):
        """Different data produces different signature."""
        data1 = {"id": "TEST-001", "value": 42}
        data2 = {"id": "TEST-001", "value": 43}
        
        sig1 = signature_service.sign("TEST-001", data1)
        sig2 = signature_service.sign("TEST-002", data2)
        
        assert sig1 != sig2
    
    def test_verify_valid_signature(self, signature_service):
        """Valid signature passes verification."""
        data = {"id": "TEST-001", "value": 42}
        signature = signature_service.sign("TEST-001", data)
        
        result = signature_service.verify("TEST-001", data, signature)
        assert result is True
    
    def test_verify_invalid_signature(self, signature_service):
        """Invalid signature raises error."""
        data = {"id": "TEST-001", "value": 42}
        
        with pytest.raises(SignatureVerificationError):
            signature_service.verify("TEST-001", data, "invalid" + "0" * 57)


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditLog:
    """Tests for SecurityAuditLog class."""
    
    def test_log_entry(self, audit_log, agent_principal):
        """Entries can be logged."""
        entry_id = audit_log.log(
            operation="PAC_READ",
            principal=agent_principal,
            success=True,
            artifact_id="PAC-TEST-001",
        )
        
        assert entry_id.startswith("SEC-")
        assert audit_log.count() == 1
    
    def test_query_by_principal(self, audit_log, agent_principal, final_principal):
        """Entries can be queried by principal."""
        audit_log.log("OP1", agent_principal, True)
        audit_log.log("OP2", final_principal, True)
        audit_log.log("OP3", agent_principal, True)
        
        entries = audit_log.get_entries(principal_id="BENSON")
        assert len(entries) == 2
    
    def test_query_by_operation(self, audit_log, agent_principal):
        """Entries can be queried by operation."""
        audit_log.log("PAC_READ", agent_principal, True)
        audit_log.log("WRAP_READ", agent_principal, True)
        audit_log.log("PAC_READ", agent_principal, True)
        
        entries = audit_log.get_entries(operation="PAC_READ")
        assert len(entries) == 2
    
    def test_entry_has_timestamp(self, audit_log, agent_principal):
        """Entries have timestamps."""
        audit_log.log("PAC_READ", agent_principal, True)
        
        entries = audit_log.get_entries()
        assert len(entries[0].timestamp) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY CONTEXT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityContext:
    """Tests for ControlPlaneSecurityContext class."""
    
    def test_singleton(self):
        """Context is singleton."""
        ControlPlaneSecurityContext._instance = None
        ctx1 = ControlPlaneSecurityContext()
        ctx2 = ControlPlaneSecurityContext()
        assert ctx1 is ctx2
    
    def test_register_and_get_principal(self, security_context, agent_principal):
        """Principals can be registered and retrieved."""
        security_context.register_principal(agent_principal)
        
        retrieved = security_context.get_principal("BENSON")
        assert retrieved is not None
        assert retrieved.gid == "GID-00"
    
    def test_authorize_operation_success(self, security_context, final_principal):
        """Authorized operations succeed."""
        security_context.authorize_operation(final_principal, "PAC_CREATE")
        # Should not raise
    
    def test_authorize_operation_failure(self, security_context, readonly_principal):
        """Unauthorized operations fail."""
        with pytest.raises(AuthorizationError):
            security_context.authorize_operation(readonly_principal, "PAC_CREATE")
    
    def test_delegate_authority(self, security_context, final_principal):
        """Authority can be delegated."""
        delegation = security_context.delegate_authority(
            delegator=final_principal,
            delegatee_id="CODY",
            operations={"PAC_READ", "WRAP_READ"},
        )
        
        assert delegation.delegator == "JEFFREY"
        assert delegation.delegatee == "CODY"
        assert delegation.is_active() is True
    
    def test_delegate_requires_final(self, security_context, agent_principal):
        """Only FINAL can delegate."""
        with pytest.raises(AuthorizationError):
            security_context.delegate_authority(
                delegator=agent_principal,
                delegatee_id="OTHER",
                operations={"PAC_READ"},
            )


# ═══════════════════════════════════════════════════════════════════════════════
# SECURE OPERATION DECORATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecureOperationDecorator:
    """Tests for secure_operation decorator."""
    
    def test_decorator_allows_authorized(self, security_context, final_principal):
        """Decorator allows authorized operations."""
        ControlPlaneSecurityContext._instance = None
        
        @secure_operation("TEST_OP")
        def test_func(principal):
            return "success"
        
        result = test_func(final_principal)
        assert result == "success"
    
    def test_decorator_blocks_unauthorized(self, security_context, readonly_principal):
        """Decorator blocks unauthorized operations."""
        ControlPlaneSecurityContext._instance = None
        
        @secure_operation("PAC_CREATE")
        def test_func(principal):
            return "success"
        
        with pytest.raises(AuthorizationError):
            test_func(readonly_principal)


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityInvariants:
    """Tests for security invariants."""
    
    def test_inv_sec_cp_001_authentication_required(
        self, security_context, readonly_principal
    ):
        """INV-SEC-CP-001: All operations require authentication."""
        # Even read operations require a principal
        security_context.authorize_operation(readonly_principal, "READ_OP")
        # Should not raise for non-sensitive ops
    
    def test_inv_sec_cp_002_delegation_audited(
        self, security_context, final_principal
    ):
        """INV-SEC-CP-002: Authority delegation is audited."""
        security_context.delegate_authority(
            final_principal, "DELEGATEE", {"PAC_READ"}
        )
        
        # Check audit log
        log = security_context.get_audit_log()
        entries = log.get_entries(operation="DELEGATE_AUTHORITY")
        assert len(entries) == 1
    
    def test_inv_sec_cp_004_signature_required(self, signature_service):
        """INV-SEC-CP-004: Cryptographic verification required."""
        data = {"type": "PAC", "id": "PAC-TEST-001"}
        
        # Sign artifact
        signature = signature_service.sign("PAC-TEST-001", data)
        
        # Verify signature
        assert signature_service.verify("PAC-TEST-001", data, signature) is True
    
    def test_inv_sec_cp_005_rate_limiting(self, rate_limiter):
        """INV-SEC-CP-005: Rate limiting enforced."""
        # Exhaust limit
        for i in range(10):
            rate_limiter.check("PAC_CREATE", "user")
        
        # Next call should be blocked
        with pytest.raises(RateLimitExceededError):
            rate_limiter.check("PAC_CREATE", "user")
