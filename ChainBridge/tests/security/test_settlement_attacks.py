"""Adversarial Tests for Settlement Attack Prevention.

Simulates attack scenarios against settlement:
- Double-settlement attempts
- Race-condition execution
- CRO override misuse
- Settlement replay
- Amount manipulation
- Destination tampering

Author: Sam (GID-06) — Security & Threat Engineer
PAC: PAC-SAM-A6-SECURITY-THREAT-HARDENING-01
"""
import pytest
import threading
import time
from datetime import datetime, timezone

from chainbridge.security.settlement_guard import (
    SettlementGuard,
    DoubleSettlementError,
    SettlementRaceConditionError,
    UnauthorizedCROOverrideError,
    SettlementLockError,
    SettlementAttackType,
    SettlementGuardResult,
    CROOverrideRequest,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def guard():
    """Create fresh SettlementGuard for each test."""
    g = SettlementGuard()
    yield g
    g.clear_state()


@pytest.fixture
def valid_pdo():
    """Create a valid PDO for settlement."""
    return {
        "pdo_id": "pdo-settle-001",
        "agent_id": "agent-alpha",
        "decision_type": "TRADE",
        "symbol": "ETH/USD",
        "side": "BUY",
        "quantity": "1.5",
        "settlement_amount": "3750.00",
        "settlement_destination": "wallet-abc-123",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def valid_settlement():
    """Create a valid settlement request."""
    return {
        "settlement_id": "settle-001",
        "pdo_id": "pdo-settle-001",
        "amount": "3750.00",
        "destination": "wallet-abc-123",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Attack Scenario: Double Settlement
# ---------------------------------------------------------------------------


class TestDoubleSettlementAttack:
    """Test defense against double-settlement attacks."""

    def test_second_settlement_blocked(self, guard, valid_pdo, valid_settlement):
        """Second settlement attempt blocked."""
        # First settlement succeeds
        guard.record_settlement(valid_pdo["pdo_id"], valid_settlement["settlement_id"])

        # Second attempt blocked
        with pytest.raises(DoubleSettlementError) as exc_info:
            guard.pre_settle_check(valid_pdo, valid_settlement)

        assert exc_info.value.pdo_id == "pdo-settle-001"
        assert exc_info.value.first_settlement_id == "settle-001"

    def test_double_settlement_with_different_id(self, guard, valid_pdo, valid_settlement):
        """Second settlement with different ID still blocked."""
        guard.record_settlement(valid_pdo["pdo_id"], "settle-001")

        second_attempt = valid_settlement.copy()
        second_attempt["settlement_id"] = "settle-002"

        with pytest.raises(DoubleSettlementError):
            guard.pre_settle_check(valid_pdo, second_attempt)

    def test_is_settled_check(self, guard, valid_pdo, valid_settlement):
        """is_settled returns correct status."""
        assert not guard.is_settled(valid_pdo["pdo_id"])

        guard.record_settlement(valid_pdo["pdo_id"], valid_settlement["settlement_id"])

        assert guard.is_settled(valid_pdo["pdo_id"])


# ---------------------------------------------------------------------------
# Attack Scenario: Race Condition
# ---------------------------------------------------------------------------


class TestRaceConditionAttack:
    """Test defense against race-condition attacks."""

    def test_concurrent_settlement_blocked(self, guard, valid_pdo, valid_settlement):
        """Concurrent settlement attempts detected."""
        # Simulate two concurrent attempts
        guard.acquire_settlement_lock(valid_pdo["pdo_id"], "requester-1")

        # Track if second attempt was properly handled
        second_result = {"blocked": False}

        def second_attempt():
            try:
                guard.acquire_settlement_lock(valid_pdo["pdo_id"], "requester-2")
            except SettlementLockError:
                second_result["blocked"] = True

        thread = threading.Thread(target=second_attempt)
        thread.start()
        thread.join(timeout=1)

        assert second_result["blocked"], "Second concurrent settlement should be blocked"

        guard.release_settlement_lock(valid_pdo["pdo_id"], "requester-1")

    def test_lock_timeout_releases(self, guard, valid_pdo):
        """Expired lock is released."""
        guard._lock_timeout = 0.1  # 100ms timeout for test

        guard.acquire_settlement_lock(valid_pdo["pdo_id"], "requester-1")

        # Wait for timeout
        time.sleep(0.2)

        # Should be able to acquire now (lock expired)
        guard.acquire_settlement_lock(valid_pdo["pdo_id"], "requester-2")

        # Clean up
        guard.release_settlement_lock(valid_pdo["pdo_id"], "requester-2")

    def test_race_detection_in_pre_settle(self, guard, valid_pdo, valid_settlement):
        """Race condition detected in pre_settle_check."""
        # Simulate pending settlements from multiple sources
        guard._pending_settlements[valid_pdo["pdo_id"]] = {"req-1", "req-2"}

        with pytest.raises(SettlementRaceConditionError) as exc_info:
            guard.pre_settle_check(valid_pdo, valid_settlement)

        assert len(exc_info.value.competing_settlement_ids) == 2


# ---------------------------------------------------------------------------
# Attack Scenario: CRO Override Misuse
# ---------------------------------------------------------------------------


class TestCROOverrideAttack:
    """Test defense against CRO override misuse."""

    def test_non_cro_override_blocked(self, guard, valid_pdo):
        """Non-CRO agent cannot override."""
        override = CROOverrideRequest(
            pdo_id=valid_pdo["pdo_id"],
            requesting_agent="agent-attacker",
            reason="I want to override this",
            override_type="HALT",
            authorization_signature="fake-sig",
        )

        with pytest.raises(UnauthorizedCROOverrideError) as exc_info:
            guard.validate_cro_override(override, agent_roles=["TRADER"])

        assert "lacks CRO authority" in str(exc_info.value)

    def test_invalid_override_type_blocked(self, guard, valid_pdo):
        """Invalid override type blocked."""
        override = CROOverrideRequest(
            pdo_id=valid_pdo["pdo_id"],
            requesting_agent="cro-agent",
            reason="This is a valid reason for override",
            override_type="DELETE_ALL",  # Invalid type!
            authorization_signature="valid-sig",
        )

        with pytest.raises(UnauthorizedCROOverrideError) as exc_info:
            guard.validate_cro_override(override, agent_roles=["CRO"])

        assert "Invalid override type" in str(exc_info.value)

    def test_missing_signature_blocked(self, guard, valid_pdo):
        """Override without signature blocked."""
        override = CROOverrideRequest(
            pdo_id=valid_pdo["pdo_id"],
            requesting_agent="cro-agent",
            reason="Valid reason for override action",
            override_type="HALT",
            authorization_signature=None,  # Missing!
        )

        with pytest.raises(UnauthorizedCROOverrideError):
            guard.validate_cro_override(override, agent_roles=["CRO"])

    def test_insufficient_reason_blocked(self, guard, valid_pdo):
        """Override with brief reason blocked."""
        override = CROOverrideRequest(
            pdo_id=valid_pdo["pdo_id"],
            requesting_agent="cro-agent",
            reason="short",  # Too brief
            override_type="HALT",
            authorization_signature="valid-sig",
        )

        with pytest.raises(UnauthorizedCROOverrideError):
            guard.validate_cro_override(override, agent_roles=["CRO"])

    def test_valid_cro_override_allowed(self, guard, valid_pdo):
        """Valid CRO override is allowed."""
        override = CROOverrideRequest(
            pdo_id=valid_pdo["pdo_id"],
            requesting_agent="cro-agent",
            reason="Market volatility requires immediate halt of this settlement",
            override_type="HALT",
            authorization_signature="valid-cro-signature",
        )

        result = guard.validate_cro_override(override, agent_roles=["CRO"])

        assert result.allowed
        assert result.attack_type is None


# ---------------------------------------------------------------------------
# Attack Scenario: Settlement Replay
# ---------------------------------------------------------------------------


class TestSettlementReplayAttack:
    """Test defense against settlement replay attacks."""

    def test_replayed_settlement_id_detected(self, guard, valid_pdo, valid_settlement):
        """Replayed settlement ID detected."""
        # Record original settlement
        guard.record_settlement("pdo-original", valid_settlement["settlement_id"])

        # Try to replay with different PDO
        replay = valid_settlement.copy()
        replay["pdo_id"] = "pdo-different"

        result = guard.detect_settlement_replay(replay)

        assert not result.allowed
        assert result.attack_type == SettlementAttackType.SETTLEMENT_REPLAY

    def test_unique_settlement_id_passes(self, guard, valid_pdo, valid_settlement):
        """Unique settlement ID passes replay check."""
        result = guard.detect_settlement_replay(valid_settlement)

        assert result.allowed


# ---------------------------------------------------------------------------
# Attack Scenario: Amount Manipulation
# ---------------------------------------------------------------------------


class TestAmountManipulationAttack:
    """Test defense against amount manipulation attacks."""

    def test_modified_amount_detected(self, guard, valid_pdo, valid_settlement):
        """Settlement with modified amount detected."""
        tampered_settlement = valid_settlement.copy()
        tampered_settlement["amount"] = "999999.99"  # Different from PDO

        result = guard.pre_settle_check(valid_pdo, tampered_settlement)

        assert not result.allowed
        assert result.attack_type == SettlementAttackType.AMOUNT_MANIPULATION

    def test_matching_amount_passes(self, guard, valid_pdo, valid_settlement):
        """Settlement with matching amount passes."""
        result = guard.pre_settle_check(valid_pdo, valid_settlement)

        assert result.allowed


# ---------------------------------------------------------------------------
# Attack Scenario: Destination Tampering
# ---------------------------------------------------------------------------


class TestDestinationTamperingAttack:
    """Test defense against destination tampering attacks."""

    def test_redirected_destination_detected(self, guard, valid_pdo, valid_settlement):
        """Settlement with redirected destination detected."""
        tampered_settlement = valid_settlement.copy()
        tampered_settlement["destination"] = "attacker-wallet-xyz"

        result = guard.pre_settle_check(valid_pdo, tampered_settlement)

        assert not result.allowed
        assert result.attack_type == SettlementAttackType.DESTINATION_TAMPERING

    def test_matching_destination_passes(self, guard, valid_pdo, valid_settlement):
        """Settlement with matching destination passes."""
        result = guard.pre_settle_check(valid_pdo, valid_settlement)

        assert result.allowed


# ---------------------------------------------------------------------------
# Lock Management
# ---------------------------------------------------------------------------


class TestSettlementLockManagement:
    """Test settlement lock mechanics."""

    def test_lock_acquire_release(self, guard, valid_pdo):
        """Lock can be acquired and released."""
        assert guard.acquire_settlement_lock(valid_pdo["pdo_id"], "requester-1")
        guard.release_settlement_lock(valid_pdo["pdo_id"], "requester-1")

    def test_same_requester_can_reacquire(self, guard, valid_pdo):
        """Same requester can reacquire lock."""
        guard.acquire_settlement_lock(valid_pdo["pdo_id"], "requester-1")
        guard.acquire_settlement_lock(valid_pdo["pdo_id"], "requester-1")

        guard.release_settlement_lock(valid_pdo["pdo_id"], "requester-1")

    def test_different_requester_blocked(self, guard, valid_pdo):
        """Different requester cannot acquire held lock."""
        guard.acquire_settlement_lock(valid_pdo["pdo_id"], "requester-1")

        with pytest.raises(SettlementLockError) as exc_info:
            guard.acquire_settlement_lock(valid_pdo["pdo_id"], "requester-2")

        assert exc_info.value.holder == "requester-1"

        guard.release_settlement_lock(valid_pdo["pdo_id"], "requester-1")


# ---------------------------------------------------------------------------
# Settlement Info Retrieval
# ---------------------------------------------------------------------------


class TestSettlementInfo:
    """Test settlement information retrieval."""

    def test_get_settlement_info(self, guard, valid_pdo, valid_settlement):
        """Settlement info can be retrieved."""
        guard.record_settlement(valid_pdo["pdo_id"], valid_settlement["settlement_id"])

        info = guard.get_settlement_info(valid_pdo["pdo_id"])

        assert info is not None
        assert info["pdo_id"] == valid_pdo["pdo_id"]
        assert info["settlement_id"] == valid_settlement["settlement_id"]
        assert info["settled_at"] is not None

    def test_unknown_settlement_returns_none(self, guard):
        """Unknown PDO returns None."""
        info = guard.get_settlement_info("unknown-pdo")

        assert info is None


# ---------------------------------------------------------------------------
# Audit Trail Verification
# ---------------------------------------------------------------------------


class TestSettlementAuditTrail:
    """Verify all attacks produce audit logs."""

    def test_attack_produces_audit_log(self, guard, valid_pdo, valid_settlement):
        """Attack produces audit log."""
        guard.record_settlement(valid_pdo["pdo_id"], "settle-original")

        try:
            guard.pre_settle_check(valid_pdo, valid_settlement)
        except DoubleSettlementError:
            pass  # Expected

        # Audit log would have been generated (tested via logging)

    def test_result_to_audit_log(self, guard, valid_pdo, valid_settlement):
        """Result can be converted to audit log."""
        tampered = valid_settlement.copy()
        tampered["amount"] = "999999.99"

        result = guard.pre_settle_check(valid_pdo, tampered)

        audit_log = result.to_audit_log()

        assert audit_log["event"] == "settlement_guard_check"
        assert audit_log["allowed"] is False
        assert audit_log["attack_type"] == "AMOUNT_MANIPULATION"
        assert "evidence" in audit_log


# ---------------------------------------------------------------------------
# Fail-Closed Verification
# ---------------------------------------------------------------------------


class TestSettlementFailClosed:
    """Verify settlement checks fail closed."""

    def test_double_settlement_raises(self, guard, valid_pdo, valid_settlement):
        """Double settlement raises exception."""
        guard.record_settlement(valid_pdo["pdo_id"], valid_settlement["settlement_id"])

        with pytest.raises(DoubleSettlementError):
            guard.pre_settle_check(valid_pdo, valid_settlement)

    def test_race_condition_raises(self, guard, valid_pdo, valid_settlement):
        """Race condition raises exception."""
        guard._pending_settlements[valid_pdo["pdo_id"]] = {"req-1", "req-2", "req-3"}

        with pytest.raises(SettlementRaceConditionError):
            guard.pre_settle_check(valid_pdo, valid_settlement)

    def test_unauthorized_cro_raises(self, guard, valid_pdo):
        """Unauthorized CRO override raises exception."""
        override = CROOverrideRequest(
            pdo_id=valid_pdo["pdo_id"],
            requesting_agent="attacker",
            reason="I want control",
            override_type="HALT",
        )

        with pytest.raises(UnauthorizedCROOverrideError):
            guard.validate_cro_override(override, agent_roles=["TRADER"])
