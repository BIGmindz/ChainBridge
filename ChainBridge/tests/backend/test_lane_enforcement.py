"""Backend Lane Enforcement Test Suite.

╔══════════════════════════════════════════════════════════════════════╗
║ EXECUTING AGENT: Cody (GID-01) — Senior Backend Engineer             ║
║ EXECUTING COLOR: 🔵 BLUE                                             ║
║ PAC: PAC-CODY-A6-BACKEND-GUARDRAILS-01                               ║
╚══════════════════════════════════════════════════════════════════════╝

Tests lane-based service boundary enforcement:
- Runtime cannot access agent-only methods
- Public cannot access protected methods
- Settlement requires validated PDO
- All lane violations fail closed

DOCTRINE (FAIL-CLOSED):
Lane violations fail immediately.
No soft bypasses allowed.

Author: Cody (GID-01) — Senior Backend Engineer
"""
from __future__ import annotations

import pytest
from typing import Optional

from app.middleware.lane_guard import (
    LaneGuard,
    LaneGuardResult,
    LaneViolationType,
    ServiceLane,
    require_lane,
    LaneViolationError,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def lane_guard() -> LaneGuard:
    """Provide fresh LaneGuard instance."""
    return LaneGuard()


# ---------------------------------------------------------------------------
# Service Lane Access Tests
# ---------------------------------------------------------------------------


class TestPublicLaneAccess:
    """Tests for PUBLIC lane access."""
    
    def test_public_lane_allows_anyone(self, lane_guard: LaneGuard):
        """PUBLIC lane should allow any caller."""
        result = lane_guard.check_access(ServiceLane.PUBLIC, None)
        assert result.allowed is True
    
    def test_public_lane_allows_runtime(self, lane_guard: LaneGuard):
        """PUBLIC lane should allow runtime callers."""
        result = lane_guard.check_access(ServiceLane.PUBLIC, "copilot_runtime")
        assert result.allowed is True
    
    def test_public_lane_allows_agent(self, lane_guard: LaneGuard):
        """PUBLIC lane should allow agent callers."""
        result = lane_guard.check_access(ServiceLane.PUBLIC, "GID-01")
        assert result.allowed is True


class TestAuthenticatedLaneAccess:
    """Tests for AUTHENTICATED lane access."""
    
    def test_authenticated_requires_identity(self, lane_guard: LaneGuard):
        """AUTHENTICATED lane should require some identity."""
        result = lane_guard.check_access(ServiceLane.AUTHENTICATED, None)
        assert result.allowed is False
        assert result.violation == LaneViolationType.UNAUTHENTICATED_ACCESS
    
    def test_authenticated_allows_any_identity(self, lane_guard: LaneGuard):
        """AUTHENTICATED lane should allow any valid identity."""
        result = lane_guard.check_access(ServiceLane.AUTHENTICATED, "some-user")
        assert result.allowed is True
    
    def test_authenticated_allows_with_auth_header(self, lane_guard: LaneGuard):
        """AUTHENTICATED lane should allow with auth header."""
        result = lane_guard.check_access(
            ServiceLane.AUTHENTICATED,
            None,
            auth_header="Bearer token123",
        )
        assert result.allowed is True


class TestAgentOnlyLaneAccess:
    """Tests for AGENT_ONLY lane access."""
    
    def test_agent_only_blocks_none(self, lane_guard: LaneGuard):
        """AGENT_ONLY lane should block None caller."""
        result = lane_guard.check_access(ServiceLane.AGENT_ONLY, None)
        assert result.allowed is False
        assert result.violation == LaneViolationType.INVALID_CALLER_IDENTITY
    
    def test_agent_only_blocks_runtime(self, lane_guard: LaneGuard):
        """AGENT_ONLY lane should block runtime callers."""
        runtime_identities = [
            "runtime",
            "copilot",
            "copilot_runtime",
            "chatgpt",
            "chatgpt_assistant",
            "system_executor",
            "assistant_bot",
        ]
        for identity in runtime_identities:
            result = lane_guard.check_access(ServiceLane.AGENT_ONLY, identity)
            assert result.allowed is False, f"Runtime '{identity}' should be blocked"
            assert result.violation == LaneViolationType.RUNTIME_CALLS_AGENT_METHOD
    
    def test_agent_only_allows_valid_gid(self, lane_guard: LaneGuard):
        """AGENT_ONLY lane should allow valid GID-XX callers."""
        valid_gids = ["GID-01", "GID-02", "GID-99", "GID-10"]
        for gid in valid_gids:
            result = lane_guard.check_access(ServiceLane.AGENT_ONLY, gid)
            assert result.allowed is True, f"GID '{gid}' should be allowed"
    
    def test_agent_only_allows_gid_in_string(self, lane_guard: LaneGuard):
        """AGENT_ONLY lane should allow caller containing GID."""
        result = lane_guard.check_access(ServiceLane.AGENT_ONLY, "agent-service::GID-01")
        assert result.allowed is True
    
    def test_agent_only_blocks_invalid_gid_format(self, lane_guard: LaneGuard):
        """AGENT_ONLY lane should block invalid GID format."""
        invalid_identities = [
            "GID01",      # Missing dash
            "GID-1",      # Single digit
            "gid-01",     # Lowercase
            "AGENT-01",   # Wrong prefix
            "user-123",   # Not a GID
        ]
        for identity in invalid_identities:
            result = lane_guard.check_access(ServiceLane.AGENT_ONLY, identity)
            assert result.allowed is False, f"Identity '{identity}' should be blocked"


class TestSettlementLaneAccess:
    """Tests for SETTLEMENT lane access."""
    
    def test_settlement_requires_validated_pdo(self, lane_guard: LaneGuard):
        """SETTLEMENT lane should require validated PDO."""
        result = lane_guard.check_access(
            ServiceLane.SETTLEMENT,
            "GID-01",
            pdo_validated=False,
        )
        assert result.allowed is False
        assert result.violation == LaneViolationType.SETTLEMENT_WITHOUT_PDO
    
    def test_settlement_allows_with_validated_pdo(self, lane_guard: LaneGuard):
        """SETTLEMENT lane should allow with validated PDO."""
        result = lane_guard.check_access(
            ServiceLane.SETTLEMENT,
            "GID-01",
            pdo_validated=True,
        )
        assert result.allowed is True
    
    def test_settlement_blocks_runtime_even_with_pdo(self, lane_guard: LaneGuard):
        """SETTLEMENT lane should block runtime even with validated PDO."""
        result = lane_guard.check_access(
            ServiceLane.SETTLEMENT,
            "copilot_runtime",
            pdo_validated=True,
        )
        assert result.allowed is False
        assert result.violation == LaneViolationType.RUNTIME_CALLS_AGENT_METHOD
    
    def test_settlement_allows_internal_services(self, lane_guard: LaneGuard):
        """SETTLEMENT lane should allow internal services."""
        internal_services = [
            "settlement-service",
            "gateway-internal",
            "internal-processor",
        ]
        for service in internal_services:
            result = lane_guard.check_access(
                ServiceLane.SETTLEMENT,
                service,
                pdo_validated=True,
            )
            assert result.allowed is True, f"Service '{service}' should be allowed"


# ---------------------------------------------------------------------------
# Decorator Tests
# ---------------------------------------------------------------------------


class TestRequireLaneDecorator:
    """Tests for @require_lane decorator."""
    
    def test_decorator_allows_valid_caller(self):
        """Decorator should allow function call with valid caller."""
        @require_lane(ServiceLane.AGENT_ONLY)
        def agent_method(caller_identity: str, data: str) -> str:
            return f"processed: {data}"
        
        result = agent_method(caller_identity="GID-01", data="test")
        assert result == "processed: test"
    
    def test_decorator_blocks_invalid_caller(self):
        """Decorator should block function call with invalid caller."""
        @require_lane(ServiceLane.AGENT_ONLY)
        def agent_method(caller_identity: str, data: str) -> str:
            return f"processed: {data}"
        
        with pytest.raises(LaneViolationError):
            agent_method(caller_identity="copilot_runtime", data="test")
    
    def test_decorator_extracts_caller_gid(self):
        """Decorator should extract caller_gid parameter."""
        @require_lane(ServiceLane.AGENT_ONLY)
        def agent_method(caller_gid: str) -> str:
            return f"called by: {caller_gid}"
        
        result = agent_method(caller_gid="GID-02")
        assert result == "called by: GID-02"
    
    def test_decorator_extracts_positional_gid(self):
        """Decorator should extract GID from positional args."""
        @require_lane(ServiceLane.AGENT_ONLY)
        def agent_method(gid: str, data: str) -> str:
            return f"{gid}: {data}"
        
        result = agent_method("GID-01", "test")
        assert result == "GID-01: test"


# ---------------------------------------------------------------------------
# Result Semantics Tests
# ---------------------------------------------------------------------------


class TestResultSemantics:
    """Tests for LaneGuardResult semantics."""
    
    def test_allowed_result_is_truthy(self, lane_guard: LaneGuard):
        """Allowed result should be truthy."""
        result = lane_guard.check_access(ServiceLane.PUBLIC, None)
        assert bool(result) is True
    
    def test_blocked_result_is_falsy(self, lane_guard: LaneGuard):
        """Blocked result should be falsy."""
        result = lane_guard.check_access(ServiceLane.AGENT_ONLY, None)
        assert bool(result) is False
        assert result.allowed is False
    
    def test_result_in_if_statement(self, lane_guard: LaneGuard):
        """Result should work correctly in if statements."""
        result = lane_guard.check_access(ServiceLane.PUBLIC, None)
        if result:
            pass  # Should enter
        else:
            pytest.fail("Should have entered if block for allowed result")
    
    def test_result_includes_timestamp(self, lane_guard: LaneGuard):
        """Result should include check timestamp."""
        result = lane_guard.check_access(ServiceLane.PUBLIC, "test")
        assert result.checked_at is not None
        assert len(result.checked_at) > 0


# ---------------------------------------------------------------------------
# No Bypass Path Tests
# ---------------------------------------------------------------------------


class TestNoBypassPaths:
    """Tests to ensure no bypass paths exist."""
    
    def test_cannot_bypass_with_empty_identity(self, lane_guard: LaneGuard):
        """Cannot bypass AGENT_ONLY with empty identity."""
        result = lane_guard.check_access(ServiceLane.AGENT_ONLY, "")
        assert result.allowed is False
    
    def test_cannot_bypass_with_whitespace_identity(self, lane_guard: LaneGuard):
        """Cannot bypass AGENT_ONLY with whitespace identity."""
        result = lane_guard.check_access(ServiceLane.AGENT_ONLY, "   ")
        assert result.allowed is False
    
    def test_cannot_bypass_with_case_manipulation(self, lane_guard: LaneGuard):
        """Cannot bypass runtime detection with case manipulation."""
        manipulated_runtimes = [
            "COPILOT",
            "CoPiLoT",
            "RUNTIME",
            "RuNtImE",
        ]
        for identity in manipulated_runtimes:
            result = lane_guard.check_access(ServiceLane.AGENT_ONLY, identity)
            assert result.allowed is False, f"'{identity}' should be blocked"
    
    def test_cannot_bypass_settlement_without_pdo_flag(self, lane_guard: LaneGuard):
        """Cannot bypass settlement PDO requirement."""
        # Default pdo_validated is True, but explicit False should block
        result = lane_guard.check_access(
            ServiceLane.SETTLEMENT,
            "GID-01",
            pdo_validated=False,
        )
        assert result.allowed is False


# ---------------------------------------------------------------------------
# Violation Tracking Tests
# ---------------------------------------------------------------------------


class TestViolationTracking:
    """Tests for violation tracking and audit."""
    
    def test_violation_type_included_in_result(self, lane_guard: LaneGuard):
        """Blocked result should include violation type."""
        result = lane_guard.check_access(ServiceLane.AGENT_ONLY, "copilot")
        assert result.violation is not None
        assert isinstance(result.violation, LaneViolationType)
    
    def test_details_included_in_result(self, lane_guard: LaneGuard):
        """Result should include details for debugging."""
        result = lane_guard.check_access(ServiceLane.AGENT_ONLY, "copilot")
        assert result.details is not None
        assert len(result.details) > 0
    
    def test_caller_included_in_result(self, lane_guard: LaneGuard):
        """Result should include caller identity."""
        result = lane_guard.check_access(ServiceLane.PUBLIC, "test-caller")
        assert result.caller == "test-caller"


# ═══════════════════════════════════════════════════════════════════════════
# END — Cody (GID-01) — 🔵
# ═══════════════════════════════════════════════════════════════════════════
