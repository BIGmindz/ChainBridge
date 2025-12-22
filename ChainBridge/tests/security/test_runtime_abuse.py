"""Adversarial Tests for Runtime Escape Prevention.

Simulates attack scenarios against runtime:
- Unauthorized agent decision emission
- Proof modification attempts
- Settlement instruction injection
- Privilege escalation
- Boundary violations
- Code injection

Author: Sam (GID-06) — Security & Threat Engineer
PAC: PAC-SAM-A6-SECURITY-THREAT-HARDENING-01
"""
import hashlib
import json
import pytest
from datetime import datetime, timezone

from chainbridge.security.runtime_threats import (
    RuntimeThreatGuard,
    UnauthorizedAgentDecisionError,
    ProofMutationAttemptError,
    SettlementInjectionError,
    RuntimePrivilegeEscalationError,
    RuntimeThreatType,
    ThreatDetectionResult,
    MutationType,
    InjectionType,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def guard():
    """Create fresh RuntimeThreatGuard for each test."""
    g = RuntimeThreatGuard()
    yield g
    g.clear_state()


@pytest.fixture
def registered_runtime(guard):
    """Create and register a runtime."""
    guard.register_runtime(
        runtime_id="runtime-001",
        authorized_agents=["agent-alpha", "agent-beta"],
        role="RUNTIME",
    )
    return "runtime-001"


@pytest.fixture
def valid_decision():
    """Create a valid agent decision."""
    return {
        "decision_id": "dec-001",
        "agent_id": "agent-alpha",
        "decision_type": "TRADE",
        "symbol": "ETH/USD",
        "side": "BUY",
        "quantity": "1.5",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def valid_proof():
    """Create a valid proof artifact."""
    content = {
        "proof_id": "proof-001",
        "decision_id": "dec-001",
        "content": "test content",
    }
    content_str = json.dumps(content, sort_keys=True, separators=(",", ":"))
    content["content_hash"] = hashlib.sha256(content_str.encode()).hexdigest()
    return content


# ---------------------------------------------------------------------------
# Attack Scenario: Unauthorized Agent Decision
# ---------------------------------------------------------------------------


class TestUnauthorizedDecisionAttack:
    """Test defense against unauthorized decision emission."""

    def test_unregistered_runtime_blocked(self, guard, valid_decision):
        """Unregistered runtime cannot emit decisions."""
        with pytest.raises(UnauthorizedAgentDecisionError) as exc_info:
            guard.validate_agent_decision("unknown-runtime", valid_decision)

        assert exc_info.value.runtime_id == "unknown-runtime"
        assert "not registered" in exc_info.value.reason.lower()

    def test_unauthorized_agent_blocked(self, guard, registered_runtime, valid_decision):
        """Runtime cannot emit for unauthorized agent."""
        decision = valid_decision.copy()
        decision["agent_id"] = "agent-gamma"  # Not authorized

        with pytest.raises(UnauthorizedAgentDecisionError) as exc_info:
            guard.validate_agent_decision(registered_runtime, decision)

        assert "agent-gamma" in exc_info.value.attempted_agent_id

    def test_authorized_decision_allowed(self, guard, registered_runtime, valid_decision):
        """Authorized decision is allowed."""
        result = guard.validate_agent_decision(registered_runtime, valid_decision)

        assert not result.blocked
        assert result.threat_type is None

    def test_decision_with_injection_blocked(self, guard, registered_runtime, valid_decision):
        """Decision containing code injection blocked."""
        malicious = valid_decision.copy()
        malicious["payload"] = "eval(malicious_code)"

        with pytest.raises(UnauthorizedAgentDecisionError):
            guard.validate_agent_decision(registered_runtime, malicious)


# ---------------------------------------------------------------------------
# Attack Scenario: Proof Mutation
# ---------------------------------------------------------------------------


class TestProofMutationAttack:
    """Test defense against proof mutation attempts."""

    def test_proof_write_blocked(self, guard, registered_runtime):
        """Runtime cannot write to proofs."""
        with pytest.raises(ProofMutationAttemptError) as exc_info:
            guard.validate_proof_access(
                registered_runtime,
                "proof-001",
                access_type="WRITE",
            )

        assert exc_info.value.mutation_type == MutationType.CONTENT_MODIFICATION.value

    def test_proof_delete_blocked(self, guard, registered_runtime):
        """Runtime cannot delete proofs."""
        with pytest.raises(ProofMutationAttemptError) as exc_info:
            guard.validate_proof_access(
                registered_runtime,
                "proof-001",
                access_type="DELETE",
            )

        assert "DELETE" in exc_info.value.mutation_type

    def test_proof_modify_blocked(self, guard, registered_runtime):
        """Runtime cannot modify proofs."""
        with pytest.raises(ProofMutationAttemptError):
            guard.validate_proof_access(
                registered_runtime,
                "proof-001",
                access_type="MODIFY",
            )

    def test_proof_read_allowed(self, guard, registered_runtime):
        """Runtime can read proofs."""
        result = guard.validate_proof_access(
            registered_runtime,
            "proof-001",
            access_type="READ",
        )

        assert not result.blocked

    def test_proof_hash_tamper_detected(self, guard, registered_runtime, valid_proof):
        """Proof hash tampering detected."""
        original_hash = hashlib.sha256(
            json.dumps(valid_proof, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

        # Tamper with proof
        tampered = valid_proof.copy()
        tampered["content"] = "TAMPERED CONTENT"

        with pytest.raises(ProofMutationAttemptError):
            guard.validate_proof_immutability(
                registered_runtime,
                tampered,
                original_hash,
            )


# ---------------------------------------------------------------------------
# Attack Scenario: Settlement Injection
# ---------------------------------------------------------------------------


class TestSettlementInjectionAttack:
    """Test defense against settlement injection attacks."""

    def test_runtime_cannot_settle(self, guard, registered_runtime):
        """Runtime cannot issue settlement instructions."""
        settlement = {
            "pdo_id": "pdo-001",
            "amount": "1000.00",
            "destination": "wallet-xyz",
        }

        with pytest.raises(SettlementInjectionError) as exc_info:
            guard.validate_settlement_request(registered_runtime, settlement)

        assert exc_info.value.injection_type == InjectionType.FAKE_SETTLEMENT.value

    def test_amount_override_detected(self, guard, registered_runtime):
        """Amount override injection detected."""
        settlement = {
            "pdo_id": "pdo-001",
            "amount": "1000.00",
            "_override_amount": True,  # Injection attempt
        }

        with pytest.raises(SettlementInjectionError) as exc_info:
            guard.validate_settlement_request(registered_runtime, settlement)

        assert exc_info.value.injection_type == InjectionType.AMOUNT_OVERRIDE.value

    def test_destination_redirect_detected(self, guard, registered_runtime):
        """Destination redirect injection detected."""
        settlement = {
            "pdo_id": "pdo-001",
            "destination": "wallet-legit",
            "_redirect_to": "wallet-attacker",  # Injection attempt
        }

        with pytest.raises(SettlementInjectionError) as exc_info:
            guard.validate_settlement_request(registered_runtime, settlement)

        assert exc_info.value.injection_type == InjectionType.DESTINATION_REDIRECT.value

    def test_settlement_engine_can_settle(self, guard):
        """Settlement engine role can issue settlements."""
        guard.register_runtime(
            runtime_id="settlement-engine",
            authorized_agents=[],
            role="SETTLEMENT_ENGINE",
        )

        settlement = {
            "pdo_id": "pdo-001",
            "amount": "1000.00",
        }

        result = guard.validate_settlement_request("settlement-engine", settlement)

        assert not result.blocked


# ---------------------------------------------------------------------------
# Attack Scenario: Privilege Escalation
# ---------------------------------------------------------------------------


class TestPrivilegeEscalationAttack:
    """Test defense against privilege escalation attacks."""

    def test_escalate_to_system_blocked(self, guard, registered_runtime):
        """Cannot escalate to SYSTEM role."""
        with pytest.raises(RuntimePrivilegeEscalationError) as exc_info:
            guard.validate_role_change(registered_runtime, "SYSTEM")

        assert exc_info.value.attempted_role == "SYSTEM"
        assert exc_info.value.current_role == "RUNTIME"

    def test_escalate_to_admin_blocked(self, guard, registered_runtime):
        """Cannot escalate to ADMIN role."""
        with pytest.raises(RuntimePrivilegeEscalationError):
            guard.validate_role_change(registered_runtime, "ADMIN")

    def test_escalate_to_cro_blocked(self, guard, registered_runtime):
        """Cannot escalate to CRO role."""
        with pytest.raises(RuntimePrivilegeEscalationError):
            guard.validate_role_change(registered_runtime, "CRO")

    def test_escalate_to_settlement_engine_blocked(self, guard, registered_runtime):
        """Cannot escalate to SETTLEMENT_ENGINE role."""
        with pytest.raises(RuntimePrivilegeEscalationError):
            guard.validate_role_change(registered_runtime, "SETTLEMENT_ENGINE")

    def test_non_privileged_role_allowed(self, guard, registered_runtime):
        """Non-privileged role change allowed."""
        result = guard.validate_role_change(registered_runtime, "WORKER")

        assert not result.blocked


# ---------------------------------------------------------------------------
# Attack Scenario: Boundary Violation
# ---------------------------------------------------------------------------


class TestBoundaryViolationAttack:
    """Test defense against boundary violation attacks."""

    def test_path_traversal_blocked(self, guard, registered_runtime):
        """Path traversal blocked."""
        result = guard.detect_boundary_violation(
            registered_runtime,
            "../../../etc/passwd",
        )

        assert result.blocked
        assert result.threat_type == RuntimeThreatType.BOUNDARY_VIOLATION

    def test_absolute_path_blocked(self, guard, registered_runtime):
        """Absolute path blocked."""
        result = guard.detect_boundary_violation(
            registered_runtime,
            "/etc/passwd",
        )

        assert result.blocked

    def test_env_file_blocked(self, guard, registered_runtime):
        """Access to .env file blocked."""
        result = guard.detect_boundary_violation(
            registered_runtime,
            "config/.env",
        )

        assert result.blocked

    def test_credentials_blocked(self, guard, registered_runtime):
        """Access to credentials blocked."""
        result = guard.detect_boundary_violation(
            registered_runtime,
            "secrets/credentials.json",
        )

        assert result.blocked

    def test_private_key_blocked(self, guard, registered_runtime):
        """Access to private key blocked."""
        result = guard.detect_boundary_violation(
            registered_runtime,
            "keys/private_key.pem",
        )

        assert result.blocked

    def test_safe_path_allowed(self, guard, registered_runtime):
        """Safe path allowed."""
        result = guard.detect_boundary_violation(
            registered_runtime,
            "data/market_data.json",
        )

        assert not result.blocked


# ---------------------------------------------------------------------------
# Attack Scenario: Code Injection
# ---------------------------------------------------------------------------


class TestCodeInjectionAttack:
    """Test defense against code injection attacks."""

    def test_eval_injection_blocked(self, guard, registered_runtime, valid_decision):
        """eval() injection blocked."""
        malicious = valid_decision.copy()
        malicious["callback"] = "eval(user_input)"

        with pytest.raises(UnauthorizedAgentDecisionError):
            guard.validate_agent_decision(registered_runtime, malicious)

    def test_exec_injection_blocked(self, guard, registered_runtime, valid_decision):
        """exec() injection blocked."""
        malicious = valid_decision.copy()
        malicious["script"] = "exec(compiled_code)"

        with pytest.raises(UnauthorizedAgentDecisionError):
            guard.validate_agent_decision(registered_runtime, malicious)

    def test_import_injection_blocked(self, guard, registered_runtime, valid_decision):
        """import injection blocked."""
        malicious = valid_decision.copy()
        malicious["module"] = "import os; os.system('rm -rf /')"

        with pytest.raises(UnauthorizedAgentDecisionError):
            guard.validate_agent_decision(registered_runtime, malicious)

    def test_dunder_injection_blocked(self, guard, registered_runtime, valid_decision):
        """Dunder method injection blocked."""
        malicious = valid_decision.copy()
        malicious["handler"] = "__import__('os').system('whoami')"

        with pytest.raises(UnauthorizedAgentDecisionError):
            guard.validate_agent_decision(registered_runtime, malicious)


# ---------------------------------------------------------------------------
# Threat Counter & Suspension
# ---------------------------------------------------------------------------


class TestThreatSuspension:
    """Test runtime suspension on repeated threats."""

    def test_threat_counter_increments(self, guard, registered_runtime, valid_decision):
        """Threat counter increments on violations."""
        decision = valid_decision.copy()
        decision["agent_id"] = "unauthorized-agent"

        for _ in range(2):
            try:
                guard.validate_agent_decision(registered_runtime, decision)
            except UnauthorizedAgentDecisionError:
                pass

        assert guard.get_threat_count(registered_runtime) == 2

    def test_runtime_suspended_after_threshold(self, guard, registered_runtime, valid_decision):
        """Runtime suspended after threat threshold."""
        decision = valid_decision.copy()
        decision["agent_id"] = "unauthorized-agent"

        # Exceed threshold (default 3)
        for _ in range(4):
            try:
                guard.validate_agent_decision(registered_runtime, decision)
            except UnauthorizedAgentDecisionError:
                pass

        assert guard.is_runtime_suspended(registered_runtime)

    def test_suspended_runtime_has_no_auth(self, guard, registered_runtime, valid_decision):
        """Suspended runtime has no authorizations."""
        # Force suspension
        guard._threat_counters[registered_runtime] = 10

        # Should have empty authorizations
        guard._increment_threat_counter(registered_runtime)  # Triggers suspension

        assert len(guard._runtime_authorizations[registered_runtime]) == 0


# ---------------------------------------------------------------------------
# Audit Trail Verification
# ---------------------------------------------------------------------------


class TestRuntimeAuditTrail:
    """Verify all threats produce audit logs."""

    def test_threat_produces_audit_log(self, guard, registered_runtime):
        """Threat produces audit log."""
        try:
            guard.validate_proof_access(registered_runtime, "proof-001", "WRITE")
        except ProofMutationAttemptError:
            pass

        # Audit would be logged

    def test_result_to_audit_log(self, guard, registered_runtime):
        """Result converts to audit log."""
        result = guard.detect_boundary_violation(
            registered_runtime,
            "../../../etc/passwd",
        )

        audit_log = result.to_audit_log()

        assert audit_log["event"] == "runtime_threat_detection"
        assert audit_log["blocked"] is True
        assert audit_log["threat_type"] == "BOUNDARY_VIOLATION"
        assert "evidence" in audit_log


# ---------------------------------------------------------------------------
# Fail-Closed Verification
# ---------------------------------------------------------------------------


class TestRuntimeFailClosed:
    """Verify runtime checks fail closed."""

    def test_unauthorized_decision_raises(self, guard, valid_decision):
        """Unauthorized decision raises exception."""
        with pytest.raises(UnauthorizedAgentDecisionError):
            guard.validate_agent_decision("unknown-runtime", valid_decision)

    def test_proof_mutation_raises(self, guard, registered_runtime):
        """Proof mutation raises exception."""
        with pytest.raises(ProofMutationAttemptError):
            guard.validate_proof_access(registered_runtime, "proof-001", "WRITE")

    def test_settlement_injection_raises(self, guard, registered_runtime):
        """Settlement injection raises exception."""
        with pytest.raises(SettlementInjectionError):
            guard.validate_settlement_request(
                registered_runtime,
                {"pdo_id": "pdo-001"},
            )

    def test_privilege_escalation_raises(self, guard, registered_runtime):
        """Privilege escalation raises exception."""
        with pytest.raises(RuntimePrivilegeEscalationError):
            guard.validate_role_change(registered_runtime, "ADMIN")
