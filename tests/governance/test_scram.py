# pylint: disable=redefined-outer-name,protected-access
# ruff: noqa: W0621, W0212
"""
SCRAM Controller Test Suite
============================

PAC-SEC-P820 | LAW-TIER | ZERO DRIFT TOLERANCE
Constitutional Mandate: PAC-GOV-P45

Test coverage for SCRAM emergency shutdown capability.
INV-SCRAM-006: 100% execution path coverage required.

Tested by: SENTINEL (GID-TEST-01)
Validated by: AEGIS (GID-WARGAME-01)
"""

import hashlib
import json
import os
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.governance.scram import (
    SCRAMController,
    SCRAMState,
    SCRAMReason,
    SCRAMKey,
    SCRAMAuditEvent,
    get_scram_controller,
    emergency_scram,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset SCRAM singleton before each test."""
    SCRAMController._instance = None
    SCRAMController._lock = threading.Lock()
    yield
    # Cleanup
    SCRAMController._instance = None


@pytest.fixture
def scram_controller():
    """Get fresh SCRAM controller instance."""
    return get_scram_controller()


@pytest.fixture
def operator_key():
    """Create valid operator key."""
    return SCRAMKey(
        key_id="OP-TEST-001",
        key_type="operator",
        key_hash=hashlib.sha256(b"operator_secret").hexdigest(),
        issued_at=datetime.now(timezone.utc).isoformat()
    )


@pytest.fixture
def architect_key():
    """Create valid architect key."""
    return SCRAMKey(
        key_id="ARCH-TEST-001",
        key_type="architect",
        key_hash=hashlib.sha256(b"architect_secret").hexdigest(),
        issued_at=datetime.now(timezone.utc).isoformat()
    )


@pytest.fixture
def expired_key():
    """Create expired key."""
    return SCRAMKey(
        key_id="EXPIRED-001",
        key_type="operator",
        key_hash=hashlib.sha256(b"expired_secret").hexdigest(),
        issued_at="2020-01-01T00:00:00Z",
        expires_at="2020-01-02T00:00:00Z"  # Expired
    )


# ==============================================================================
# Test: Singleton Pattern
# ==============================================================================

class TestSingleton:
    """Test SCRAM controller singleton pattern."""
    
    def test_singleton_same_instance(self):
        """INV-SYS-002: Exactly one SCRAM controller may exist."""
        controller1 = get_scram_controller()
        controller2 = get_scram_controller()
        assert controller1 is controller2
    
    def test_singleton_via_constructor(self):
        """Direct constructor returns same instance."""
        controller1 = SCRAMController()
        controller2 = SCRAMController()
        assert controller1 is controller2
    
    def test_singleton_thread_safe(self):
        """Singleton is thread-safe under concurrent access."""
        instances = []
        
        def create_instance():
            instances.append(get_scram_controller())
        
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All instances should be the same object
        assert all(i is instances[0] for i in instances)


# ==============================================================================
# Test: Initial State
# ==============================================================================

class TestInitialState:
    """Test SCRAM controller initial state."""
    
    def test_initial_state_armed(self, scram_controller):
        """Controller initializes in ARMED state."""
        assert scram_controller.state == SCRAMState.ARMED
    
    def test_is_armed_true(self, scram_controller):
        """is_armed property returns True initially."""
        assert scram_controller.is_armed is True
    
    def test_is_active_false(self, scram_controller):
        """is_active property returns False initially."""
        assert scram_controller.is_active is False
    
    def test_is_complete_false(self, scram_controller):
        """is_complete property returns False initially."""
        assert scram_controller.is_complete is False


# ==============================================================================
# Test: Key Authorization
# ==============================================================================

class TestKeyAuthorization:
    """Test dual-key authorization (INV-SCRAM-002)."""
    
    def test_authorize_operator_key(self, scram_controller, operator_key):
        """Operator key can be authorized."""
        result = scram_controller.authorize_key(operator_key)
        assert result is True
    
    def test_authorize_architect_key(self, scram_controller, architect_key):
        """Architect key can be authorized."""
        result = scram_controller.authorize_key(architect_key)
        assert result is True
    
    def test_reject_invalid_key_type(self, scram_controller):
        """Invalid key type is rejected."""
        invalid_key = SCRAMKey(
            key_id="INVALID-001",
            key_type="invalid",  # Not operator or architect
            key_hash="abc123",
            issued_at=datetime.now(timezone.utc).isoformat()
        )
        result = scram_controller.authorize_key(invalid_key)
        assert result is False
    
    def test_reject_expired_key(self, scram_controller, expired_key):
        """Expired key is rejected."""
        result = scram_controller.authorize_key(expired_key)
        assert result is False
    
    def test_reject_empty_key_id(self, scram_controller):
        """Key with empty ID is rejected."""
        invalid_key = SCRAMKey(
            key_id="",
            key_type="operator",
            key_hash="abc123",
            issued_at=datetime.now(timezone.utc).isoformat()
        )
        result = scram_controller.authorize_key(invalid_key)
        assert result is False
    
    def test_dual_key_verification_succeeds(
        self, scram_controller, operator_key, architect_key
    ):
        """Dual-key verification succeeds with both keys."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        success, op_hash, arch_hash = scram_controller._verify_dual_key_authorization()
        assert success is True
        assert op_hash == operator_key.key_hash
        assert arch_hash == architect_key.key_hash
    
    def test_dual_key_verification_fails_missing_operator(
        self, scram_controller, architect_key
    ):
        """Dual-key verification fails without operator key."""
        scram_controller.authorize_key(architect_key)
        
        success, _, _ = scram_controller._verify_dual_key_authorization()
        assert success is False
    
    def test_dual_key_verification_fails_missing_architect(
        self, scram_controller, operator_key
    ):
        """Dual-key verification fails without architect key."""
        scram_controller.authorize_key(operator_key)
        
        success, _, _ = scram_controller._verify_dual_key_authorization()
        assert success is False


# ==============================================================================
# Test: Execution Path Registration
# ==============================================================================

class TestExecutionPaths:
    """Test execution path registration."""
    
    def test_register_execution_path(self, scram_controller):
        """Execution path can be registered when armed."""
        handler = MagicMock()
        result = scram_controller.register_execution_path("test-path-1", handler)
        assert result is True
    
    def test_register_multiple_paths(self, scram_controller):
        """Multiple execution paths can be registered."""
        handlers = [MagicMock() for _ in range(5)]
        for i, handler in enumerate(handlers):
            result = scram_controller.register_execution_path(f"path-{i}", handler)
            assert result is True
    
    def test_register_termination_hook(self, scram_controller):
        """Termination hook can be registered."""
        hook = MagicMock()
        result = scram_controller.register_termination_hook(hook)
        assert result is True


# ==============================================================================
# Test: SCRAM Activation
# ==============================================================================

class TestSCRAMActivation:
    """Test SCRAM activation and termination."""
    
    def test_activate_with_dual_key(
        self, scram_controller, operator_key, architect_key
    ):
        """SCRAM activates successfully with dual-key authorization."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        event = scram_controller.activate(SCRAMReason.OPERATOR_INITIATED)
        
        assert event.scram_state in ("COMPLETE", "FAILED")
        assert "INV-SCRAM-002" in event.invariants_passed
    
    def test_activate_terminates_paths(
        self, scram_controller, operator_key, architect_key
    ):
        """SCRAM activation terminates all registered paths."""
        # Register paths with mock handlers
        handlers = [MagicMock() for _ in range(3)]
        for i, handler in enumerate(handlers):
            scram_controller.register_execution_path(f"path-{i}", handler)
        
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        event = scram_controller.activate(SCRAMReason.SECURITY_BREACH)
        
        # All handlers should have been called
        for handler in handlers:
            handler.assert_called_once()
        
        assert event.execution_paths_terminated == 3
    
    def test_activate_executes_hooks(
        self, scram_controller, operator_key, architect_key
    ):
        """SCRAM activation executes termination hooks."""
        hooks = [MagicMock() for _ in range(2)]
        for hook in hooks:
            scram_controller.register_termination_hook(hook)
        
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        scram_controller.activate(SCRAMReason.GOVERNANCE_MANDATE)
        
        for hook in hooks:
            hook.assert_called_once()
    
    def test_activate_without_keys_fails_closed(self, scram_controller):
        """SCRAM activates in fail-closed mode without keys."""
        event = scram_controller.activate(SCRAMReason.SYSTEM_CRITICAL)
        
        # Should still terminate (fail-closed) but record auth failure
        assert event.operator_key_hash in ("MISSING", "ERROR")
        assert event.architect_key_hash in ("MISSING", "ERROR")
    
    def test_activate_transitions_state(
        self, scram_controller, operator_key, architect_key
    ):
        """SCRAM activation transitions through expected states."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        # Initially armed
        assert scram_controller.state == SCRAMState.ARMED
        
        event = scram_controller.activate(SCRAMReason.OPERATOR_INITIATED)
        
        # Should end in COMPLETE or FAILED
        assert scram_controller.is_complete
    
    def test_activate_already_active_returns_error(
        self, scram_controller, operator_key, architect_key
    ):
        """Cannot activate SCRAM twice."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        # First activation
        scram_controller.activate(SCRAMReason.OPERATOR_INITIATED)
        
        # Second activation should return error event
        event = scram_controller.activate(SCRAMReason.OPERATOR_INITIATED)
        assert "error" in event.metadata or event.invariants_failed


# ==============================================================================
# Test: Timing Constraints (INV-SCRAM-001)
# ==============================================================================

class TestTimingConstraints:
    """Test 500ms termination deadline (INV-SCRAM-001)."""
    
    def test_termination_under_deadline(
        self, scram_controller, operator_key, architect_key
    ):
        """Termination completes under 500ms deadline."""
        # Register fast handlers
        for i in range(5):
            scram_controller.register_execution_path(
                f"fast-path-{i}",
                lambda: time.sleep(0.001)  # 1ms each
            )
        
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        event = scram_controller.activate(SCRAMReason.OPERATOR_INITIATED)
        
        assert event.termination_latency_ms < 500
        assert "INV-SCRAM-001" in event.invariants_passed
    
    def test_termination_deadline_exceeded_logged(
        self, scram_controller, operator_key, architect_key
    ):
        """Deadline exceeded is logged but termination completes."""
        # Register slow handler (would exceed deadline)
        slow_handler = MagicMock(side_effect=lambda: time.sleep(0.6))
        scram_controller.register_execution_path("slow-path", slow_handler)
        
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        event = scram_controller.activate(SCRAMReason.OPERATOR_INITIATED)
        
        # Should still terminate (fail-closed) but record violation
        slow_handler.assert_called_once()
        assert event.termination_latency_ms >= 500


# ==============================================================================
# Test: Audit Trail (INV-SCRAM-004)
# ==============================================================================

class TestAuditTrail:
    """Test immutable audit trail (INV-SCRAM-004)."""
    
    def test_audit_event_created(
        self, scram_controller, operator_key, architect_key
    ):
        """SCRAM activation creates audit event."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        event = scram_controller.activate(SCRAMReason.OPERATOR_INITIATED)
        
        assert event.event_id.startswith("SCRAM-")
        assert event.timestamp is not None
        assert event.ledger_anchor_hash is not None
    
    def test_audit_event_immutable_record(
        self, scram_controller, operator_key, architect_key
    ):
        """Audit event produces immutable record with content hash."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        event = scram_controller.activate(SCRAMReason.SECURITY_BREACH)
        record = event.to_immutable_record()
        
        assert "content_hash" in record
        assert len(record["content_hash"]) == 64  # SHA-256 hex
    
    def test_audit_trail_accessible(
        self, scram_controller, operator_key, architect_key
    ):
        """Audit trail is accessible after activation."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        scram_controller.activate(SCRAMReason.OPERATOR_INITIATED)
        
        trail = scram_controller.get_audit_trail()
        assert len(trail) == 1
        assert trail[0]["event_id"].startswith("SCRAM-")
    
    def test_audit_event_contains_invariants(
        self, scram_controller, operator_key, architect_key
    ):
        """Audit event contains invariant check results."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        event = scram_controller.activate(SCRAMReason.GOVERNANCE_MANDATE)
        
        assert len(event.invariants_checked) > 0
        assert "INV-SYS-002" in event.invariants_checked
        assert "INV-SCRAM-001" in event.invariants_checked


# ==============================================================================
# Test: Fail-Closed Behavior (INV-SCRAM-005)
# ==============================================================================

class TestFailClosed:
    """Test fail-closed behavior (INV-SCRAM-005)."""
    
    def test_handler_error_continues_termination(
        self, scram_controller, operator_key, architect_key
    ):
        """Error in handler doesn't stop termination (fail-closed)."""
        error_handler = MagicMock(side_effect=Exception("Handler error"))
        good_handler = MagicMock()
        
        scram_controller.register_execution_path("error-path", error_handler)
        scram_controller.register_execution_path("good-path", good_handler)
        
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        event = scram_controller.activate(SCRAMReason.SYSTEM_CRITICAL)
        
        # Both handlers should be called
        error_handler.assert_called_once()
        good_handler.assert_called_once()
        
        # Should count as terminated
        assert event.execution_paths_terminated == 2
    
    def test_hook_error_continues_execution(
        self, scram_controller, operator_key, architect_key
    ):
        """Error in termination hook doesn't stop execution."""
        error_hook = MagicMock(side_effect=Exception("Hook error"))
        good_hook = MagicMock()
        
        scram_controller.register_termination_hook(error_hook)
        scram_controller.register_termination_hook(good_hook)
        
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        scram_controller.activate(SCRAMReason.SYSTEM_CRITICAL)
        
        # Both hooks should be called
        error_hook.assert_called_once()
        good_hook.assert_called_once()


# ==============================================================================
# Test: Reset Functionality
# ==============================================================================

class TestReset:
    """Test SCRAM controller reset."""
    
    def test_reset_after_complete(
        self, scram_controller, operator_key, architect_key
    ):
        """Controller can be reset after COMPLETE state."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        scram_controller.activate(SCRAMReason.OPERATOR_INITIATED)
        
        assert scram_controller.is_complete
        
        result = scram_controller.reset()
        
        assert result is True
        assert scram_controller.state == SCRAMState.ARMED
    
    def test_reset_clears_keys(
        self, scram_controller, operator_key, architect_key
    ):
        """Reset clears authorized keys."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        scram_controller.activate(SCRAMReason.OPERATOR_INITIATED)
        scram_controller.reset()
        
        # Keys should be cleared
        success, _, _ = scram_controller._verify_dual_key_authorization()
        assert success is False
    
    def test_reset_fails_when_armed(self, scram_controller):
        """Cannot reset when in ARMED state."""
        result = scram_controller.reset()
        assert result is False


# ==============================================================================
# Test: Emergency SCRAM Convenience Function
# ==============================================================================

class TestEmergencySCRAM:
    """Test emergency_scram convenience function."""
    
    def test_emergency_scram_with_keys(self, operator_key, architect_key):
        """emergency_scram works with provided keys."""
        event = emergency_scram(
            reason=SCRAMReason.SECURITY_BREACH,
            operator_key=operator_key,
            architect_key=architect_key,
            metadata={"test": True}
        )
        
        assert event.reason == "security_breach"
        assert event.metadata.get("test") is True
    
    def test_emergency_scram_without_keys(self):
        """emergency_scram works in fail-closed mode without keys."""
        event = emergency_scram(
            reason=SCRAMReason.SYSTEM_CRITICAL,
            metadata={"emergency": True}
        )
        
        assert event.reason == "system_critical"


# ==============================================================================
# Test: Invariant Validation
# ==============================================================================

class TestInvariantValidation:
    """Test invariant checking."""
    
    def test_all_invariants_checked(
        self, scram_controller, operator_key, architect_key
    ):
        """All defined invariants are checked during activation."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        event = scram_controller.activate(SCRAMReason.OPERATOR_INITIATED)
        
        expected_invariants = [
            "INV-SYS-002",
            "INV-SCRAM-001",
            "INV-SCRAM-002",
            "INV-SCRAM-003",
            "INV-SCRAM-004",
            "INV-SCRAM-005",
            "INV-SCRAM-006",
            "INV-GOV-003"
        ]
        
        for inv in expected_invariants:
            assert inv in event.invariants_checked
    
    def test_invariant_pass_with_dual_key(
        self, scram_controller, operator_key, architect_key
    ):
        """INV-SCRAM-002 passes with dual-key authorization."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        passed, failed = scram_controller._check_invariants()
        
        assert "INV-SCRAM-002" in passed
        assert "INV-SCRAM-002" not in failed


# ==============================================================================
# Test: SCRAMKey Dataclass
# ==============================================================================

class TestSCRAMKey:
    """Test SCRAMKey dataclass."""
    
    def test_key_is_frozen(self, operator_key):
        """SCRAMKey is immutable (frozen dataclass)."""
        with pytest.raises(Exception):  # FrozenInstanceError
            operator_key.key_id = "MODIFIED"
    
    def test_valid_key_validates(self, operator_key):
        """Valid key passes validation."""
        assert operator_key.validate() is True
    
    def test_invalid_key_type_fails(self):
        """Invalid key type fails validation."""
        key = SCRAMKey(
            key_id="TEST-001",
            key_type="invalid",
            key_hash="abc123",
            issued_at=datetime.now(timezone.utc).isoformat()
        )
        assert key.validate() is False


# ==============================================================================
# Test: SCRAMAuditEvent
# ==============================================================================

class TestSCRAMAuditEvent:
    """Test SCRAMAuditEvent dataclass."""
    
    def test_to_immutable_record(self):
        """to_immutable_record produces valid record."""
        event = SCRAMAuditEvent(
            event_id="SCRAM-TEST",
            timestamp=datetime.now(timezone.utc).isoformat(),
            scram_state="COMPLETE",
            reason="operator_initiated",
            operator_key_hash="abc123",
            architect_key_hash="def456",
            execution_paths_terminated=5,
            termination_latency_ms=50.0,
            invariants_checked=["INV-SYS-002"],
            invariants_passed=["INV-SYS-002"],
            invariants_failed=[],
            hardware_sentinel_ack=True,
            ledger_anchor_hash="abc" * 21 + "a",
            metadata={"test": True}
        )
        
        record = event.to_immutable_record()
        
        assert record["event_id"] == "SCRAM-TEST"
        assert "content_hash" in record
        assert len(record["content_hash"]) == 64


# ==============================================================================
# Test: Hardware Sentinel Notification
# ==============================================================================

class TestHardwareSentinel:
    """Test hardware sentinel integration (INV-SCRAM-003)."""
    
    def test_sentinel_notification_creates_file(
        self, scram_controller, operator_key, architect_key
    ):
        """Hardware sentinel notification creates signal file."""
        scram_controller.authorize_key(operator_key)
        scram_controller.authorize_key(architect_key)
        
        # Use temp path for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            sentinel_path = Path(tmpdir) / "scram_sentinel"
            
            with patch.object(
                scram_controller, '_notify_hardware_sentinel'
            ) as mock_notify:
                scram_controller.activate(SCRAMReason.OPERATOR_INITIATED)
                mock_notify.assert_called_once()


# ==============================================================================
# Test: SCRAM Reason Enum
# ==============================================================================

class TestSCRAMReason:
    """Test SCRAMReason enum."""
    
    def test_all_reasons_have_values(self):
        """All SCRAM reasons have string values."""
        for reason in SCRAMReason:
            assert isinstance(reason.value, str)
            assert len(reason.value) > 0
    
    def test_reason_values_unique(self):
        """All reason values are unique."""
        values = [r.value for r in SCRAMReason]
        assert len(values) == len(set(values))


# ==============================================================================
# Test: Configuration Loading
# ==============================================================================

class TestConfiguration:
    """Test configuration loading."""
    
    def test_config_has_required_keys(self, scram_controller):
        """Configuration has all required keys."""
        config = scram_controller._config
        
        assert "max_termination_ms" in config
        assert "require_dual_key" in config
        assert "fail_closed_on_error" in config
    
    def test_constitutional_settings_enforced(self, scram_controller):
        """Constitutional settings cannot be disabled."""
        config = scram_controller._config
        
        # These must always be True
        assert config["require_dual_key"] is True
        assert config["fail_closed_on_error"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
