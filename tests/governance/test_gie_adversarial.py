"""
Test Adversarial Security Suite

Per PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-028.
Agent: GID-06 (Sam) — Security Auditor
"""

import pytest
from datetime import datetime, timezone, timedelta

from core.governance.adversarial_tests import (
    # Enums
    AttackType,
    AttackResult,
    DefenseLayer,
    
    # Data classes
    AttackScenario,
    AttackAttempt,
    SecurityReport,
    
    # Mock components
    MockGIERegistry,
    MockUIOutputManager,
    MockCryptoVerifier,
    
    # Engine
    AdversarialTestEngine,
    
    # Generators
    generate_agent_injection_scenarios,
    generate_ber_spoof_scenarios,
    generate_ui_overflow_scenarios,
    generate_full_attack_suite,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def registry():
    """Provide mock registry."""
    return MockGIERegistry()


@pytest.fixture
def ui_manager():
    """Provide mock UI manager."""
    return MockUIOutputManager()


@pytest.fixture
def crypto():
    """Provide mock crypto verifier."""
    return MockCryptoVerifier()


@pytest.fixture
def engine():
    """Provide adversarial test engine."""
    return AdversarialTestEngine()


@pytest.fixture
def configured_engine():
    """Provide engine with pre-configured PAC."""
    engine = AdversarialTestEngine()
    engine.setup_valid_pac("PAC-001", ["GID-01", "GID-02", "GID-03"])
    engine.setup_sealed_pdo("PDO-SEALED-001")
    return engine


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Mock Components
# ═══════════════════════════════════════════════════════════════════════════════

class TestMockGIERegistry:
    """Tests for MockGIERegistry."""

    def test_agent_registration(self, registry):
        """Can register agents."""
        assert not registry.is_registered("GID-01")
        registry.register_agent("GID-01")
        assert registry.is_registered("GID-01")

    def test_pac_activation(self, registry):
        """Can activate PAC with agents."""
        registry.register_agent("GID-01")
        registry.activate_pac("PAC-001", ["GID-01"])
        
        assert registry.is_pac_active("PAC-001")
        assert registry.is_agent_assigned("PAC-001", "GID-01")
        assert not registry.is_agent_assigned("PAC-001", "GID-02")

    def test_pdo_sealing(self, registry):
        """Can seal PDOs."""
        assert not registry.is_sealed("PDO-001")
        registry.seal_pdo("PDO-001")
        assert registry.is_sealed("PDO-001")


class TestMockUIOutputManager:
    """Tests for MockUIOutputManager."""

    def test_basic_emission(self, ui_manager):
        """Can emit messages."""
        success, error = ui_manager.emit("PAC-001", "Hello")
        assert success
        assert error is None

    def test_emission_limit(self, ui_manager):
        """Enforces emission limit."""
        pac_id = "PAC-LIMIT"
        
        for i in range(22):
            success, _ = ui_manager.emit(pac_id, f"msg-{i}")
            assert success
        
        # 23rd emission should fail
        success, error = ui_manager.emit(pac_id, "overflow")
        assert not success
        assert "exceeded" in error

    def test_message_length_limit(self, ui_manager):
        """Enforces message length limit."""
        long_message = "x" * 150
        success, error = ui_manager.emit("PAC-001", long_message)
        assert not success
        assert "120 chars" in error


class TestMockCryptoVerifier:
    """Tests for MockCryptoVerifier."""

    def test_hash_computation(self, crypto):
        """Can compute hashes."""
        hash1 = crypto.compute_hash("content")
        assert hash1.startswith("sha256:")
        
        # Deterministic
        hash2 = crypto.compute_hash("content")
        assert hash1 == hash2

    def test_hash_verification(self, crypto):
        """Can verify hashes."""
        content = "test content"
        correct_hash = crypto.compute_hash(content)
        
        assert crypto.verify_hash(content, correct_hash)
        assert not crypto.verify_hash(content, "sha256:wrong")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Attack Scenarios
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentInjection:
    """Tests for agent injection attacks."""

    def test_unregistered_agent_blocked(self, configured_engine):
        """Unregistered agent is blocked."""
        scenario = AttackScenario(
            attack_id="INJ-001",
            attack_type=AttackType.AGENT_INJECTION,
            description="Inject unregistered agent",
            payload={"pac_id": "PAC-001", "fake_gid": "GID-FAKE-999"},
            expected_defenses=[DefenseLayer.AUTHENTICATION],
            expected_result=AttackResult.BLOCKED,
        )
        
        attempt = configured_engine.run_attack(scenario)
        assert attempt.result == AttackResult.BLOCKED
        assert attempt.defense_triggered == DefenseLayer.AUTHENTICATION

    def test_registered_but_unassigned_blocked(self, configured_engine):
        """Registered but unassigned agent is blocked."""
        # Register agent but don't assign to PAC
        configured_engine._registry.register_agent("GID-OUTSIDER")
        
        scenario = AttackScenario(
            attack_id="INJ-002",
            attack_type=AttackType.AGENT_INJECTION,
            description="Inject registered but unassigned agent",
            payload={"pac_id": "PAC-001", "fake_gid": "GID-OUTSIDER"},
            expected_defenses=[DefenseLayer.AUTHORIZATION],
            expected_result=AttackResult.BLOCKED,
        )
        
        attempt = configured_engine.run_attack(scenario)
        assert attempt.result == AttackResult.BLOCKED
        assert attempt.defense_triggered == DefenseLayer.AUTHORIZATION

    def test_valid_agent_passes(self, configured_engine):
        """Valid assigned agent is not blocked."""
        scenario = AttackScenario(
            attack_id="INJ-003",
            attack_type=AttackType.AGENT_INJECTION,
            description="Valid agent check",
            payload={"pac_id": "PAC-001", "fake_gid": "GID-01"},
            expected_defenses=[],
            expected_result=AttackResult.SUCCEEDED,
        )
        
        attempt = configured_engine.run_attack(scenario)
        assert attempt.result == AttackResult.SUCCEEDED


class TestBERSpoof:
    """Tests for BER spoofing attacks."""

    def test_fake_hash_blocked(self, engine):
        """BER with fake hash is blocked."""
        scenario = AttackScenario(
            attack_id="BER-001",
            attack_type=AttackType.BER_SPOOF,
            description="BER with fake hash",
            payload={
                "pac_id": "PAC-001",
                "fake_ber": {"status": "APPROVE"},
                "claimed_hash": "sha256:definitely-fake",
            },
            expected_defenses=[DefenseLayer.CRYPTOGRAPHIC],
            expected_result=AttackResult.BLOCKED,
        )
        
        attempt = engine.run_attack(scenario)
        assert attempt.result == AttackResult.BLOCKED
        assert attempt.defense_triggered == DefenseLayer.CRYPTOGRAPHIC


class TestWRAPTampering:
    """Tests for WRAP tampering attacks."""

    def test_tampered_content_blocked(self, engine):
        """Tampered WRAP content is blocked."""
        scenario = AttackScenario(
            attack_id="TAMPER-001",
            attack_type=AttackType.WRAP_TAMPERING,
            description="WRAP with tampered content",
            payload={
                "original_hash": "sha256:original",
                "tampered_content": "malicious payload",
                "claimed_hash": "sha256:original",
            },
            expected_defenses=[DefenseLayer.CRYPTOGRAPHIC],
            expected_result=AttackResult.BLOCKED,
        )
        
        attempt = engine.run_attack(scenario)
        assert attempt.result == AttackResult.BLOCKED


class TestHashCollision:
    """Tests for hash collision attacks."""

    def test_different_content_different_hash(self, engine):
        """Different content produces different hashes."""
        scenario = AttackScenario(
            attack_id="COLLISION-001",
            attack_type=AttackType.HASH_COLLISION,
            description="Attempt hash collision",
            payload={
                "content1": "legitimate content",
                "content2": "malicious content",
            },
            expected_defenses=[DefenseLayer.CRYPTOGRAPHIC],
            expected_result=AttackResult.BLOCKED,
        )
        
        attempt = engine.run_attack(scenario)
        assert attempt.result == AttackResult.BLOCKED


class TestUIOverflow:
    """Tests for UI overflow attacks."""

    def test_emission_count_exceeded(self, engine):
        """Exceeding emission count is blocked."""
        scenario = AttackScenario(
            attack_id="UI-OVERFLOW-001",
            attack_type=AttackType.UI_OVERFLOW,
            description="Exceed emission limit",
            payload={
                "pac_id": "PAC-OVERFLOW",
                "emission_count": 50,
                "message": "spam",
            },
            expected_defenses=[DefenseLayer.RATE_LIMITING],
            expected_result=AttackResult.BLOCKED,
        )
        
        attempt = engine.run_attack(scenario)
        assert attempt.result == AttackResult.BLOCKED

    def test_oversized_message_blocked(self, engine):
        """Oversized message is blocked."""
        scenario = AttackScenario(
            attack_id="UI-OVERFLOW-002",
            attack_type=AttackType.UI_OVERFLOW,
            description="Emit oversized message",
            payload={
                "pac_id": "PAC-OVERFLOW-2",
                "emission_count": 1,
                "message": "x" * 200,
            },
            expected_defenses=[DefenseLayer.VALIDATION],
            expected_result=AttackResult.BLOCKED,
        )
        
        attempt = engine.run_attack(scenario)
        assert attempt.result == AttackResult.BLOCKED


class TestCheckpointSpoof:
    """Tests for checkpoint spoofing attacks."""

    def test_unregistered_agent_blocked(self, engine):
        """Checkpoint from unregistered agent blocked."""
        scenario = AttackScenario(
            attack_id="CP-001",
            attack_type=AttackType.CHECKPOINT_SPOOF,
            description="Checkpoint from fake agent",
            payload={
                "pac_id": "PAC-001",
                "agent_gid": "GID-FAKE",
                "checkpoint": {
                    "checkpoint_type": "WRAP_RECEIVED",
                    "timestamp": datetime.utcnow().isoformat(),
                    "agent_gid": "GID-FAKE",
                },
            },
            expected_defenses=[DefenseLayer.AUTHENTICATION],
            expected_result=AttackResult.BLOCKED,
        )
        
        attempt = engine.run_attack(scenario)
        assert attempt.result == AttackResult.BLOCKED

    def test_missing_fields_blocked(self, configured_engine):
        """Checkpoint with missing fields blocked."""
        scenario = AttackScenario(
            attack_id="CP-002",
            attack_type=AttackType.CHECKPOINT_SPOOF,
            description="Checkpoint missing fields",
            payload={
                "pac_id": "PAC-001",
                "agent_gid": "GID-01",  # Valid agent
                "checkpoint": {
                    "checkpoint_type": "WRAP_RECEIVED",
                    # Missing timestamp and agent_gid
                },
            },
            expected_defenses=[DefenseLayer.VALIDATION],
            expected_result=AttackResult.BLOCKED,
        )
        
        attempt = configured_engine.run_attack(scenario)
        assert attempt.result == AttackResult.BLOCKED


class TestPDOMutation:
    """Tests for PDO mutation attacks."""

    def test_sealed_pdo_immutable(self, configured_engine):
        """Sealed PDO cannot be mutated."""
        scenario = AttackScenario(
            attack_id="PDO-001",
            attack_type=AttackType.PDO_MUTATION,
            description="Mutate sealed PDO",
            payload={
                "pdo_id": "PDO-SEALED-001",
                "mutation": {"status": "tampered"},
            },
            expected_defenses=[DefenseLayer.VALIDATION],
            expected_result=AttackResult.BLOCKED,
        )
        
        attempt = configured_engine.run_attack(scenario)
        assert attempt.result == AttackResult.BLOCKED

    def test_unsealed_pdo_vulnerable(self, configured_engine):
        """Unsealed PDO can be mutated (vulnerability)."""
        scenario = AttackScenario(
            attack_id="PDO-002",
            attack_type=AttackType.PDO_MUTATION,
            description="Mutate unsealed PDO",
            payload={
                "pdo_id": "PDO-UNSEALED",
                "mutation": {"status": "tampered"},
            },
            expected_defenses=[],
            expected_result=AttackResult.SUCCEEDED,
        )
        
        attempt = configured_engine.run_attack(scenario)
        assert attempt.result == AttackResult.SUCCEEDED


class TestReplayAttack:
    """Tests for replay attacks."""

    def test_old_artifact_blocked(self, engine):
        """Old artifact is blocked."""
        scenario = AttackScenario(
            attack_id="REPLAY-001",
            attack_type=AttackType.REPLAY_ATTACK,
            description="Replay old artifact",
            payload={
                "timestamp": "2020-01-01T00:00:00Z",
                "max_age_seconds": 300,
            },
            expected_defenses=[DefenseLayer.VALIDATION],
            expected_result=AttackResult.BLOCKED,
        )
        
        attempt = engine.run_attack(scenario)
        assert attempt.result == AttackResult.BLOCKED

    def test_invalid_timestamp_blocked(self, engine):
        """Invalid timestamp is blocked."""
        scenario = AttackScenario(
            attack_id="REPLAY-002",
            attack_type=AttackType.REPLAY_ATTACK,
            description="Invalid timestamp format",
            payload={
                "timestamp": "not-a-timestamp",
                "max_age_seconds": 300,
            },
            expected_defenses=[DefenseLayer.VALIDATION],
            expected_result=AttackResult.BLOCKED,
        )
        
        attempt = engine.run_attack(scenario)
        assert attempt.result == AttackResult.BLOCKED


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Security Report
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityReport:
    """Tests for security reporting."""

    def test_run_full_suite(self, configured_engine):
        """Can run full attack suite."""
        suite = generate_full_attack_suite()
        report = configured_engine.run_suite(suite, pac_id="PAC-001")
        
        assert report.total_attacks == len(suite)
        assert report.blocked > 0

    def test_report_tracks_attempts(self, engine):
        """Report tracks all attempts."""
        scenarios = generate_agent_injection_scenarios(3)
        report = engine.run_suite(scenarios)
        
        assert len(report.attempts) == 3
        assert report.total_attacks == 3

    def test_report_identifies_vulnerabilities(self, configured_engine):
        """Report identifies vulnerabilities."""
        # Create a scenario that will succeed (vulnerability)
        scenarios = [
            AttackScenario(
                attack_id="VULN-001",
                attack_type=AttackType.PDO_MUTATION,
                description="Test vulnerability",
                payload={"pdo_id": "PDO-NOT-SEALED", "mutation": {}},
                expected_defenses=[],
                expected_result=AttackResult.SUCCEEDED,
            ),
        ]
        
        report = configured_engine.run_suite(scenarios)
        
        assert report.succeeded == 1
        assert len(report.vulnerabilities) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Scenario Generators
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenarioGenerators:
    """Tests for scenario generators."""

    def test_generate_agent_injection_scenarios(self):
        """Can generate injection scenarios."""
        scenarios = generate_agent_injection_scenarios(5)
        assert len(scenarios) == 5
        assert all(s.attack_type == AttackType.AGENT_INJECTION for s in scenarios)

    def test_generate_ber_spoof_scenarios(self):
        """Can generate BER spoof scenarios."""
        scenarios = generate_ber_spoof_scenarios(3)
        assert len(scenarios) == 3
        assert all(s.attack_type == AttackType.BER_SPOOF for s in scenarios)

    def test_generate_ui_overflow_scenarios(self):
        """Can generate UI overflow scenarios."""
        scenarios = generate_ui_overflow_scenarios()
        assert len(scenarios) == 2
        assert all(s.attack_type == AttackType.UI_OVERFLOW for s in scenarios)

    def test_generate_full_suite(self):
        """Can generate full attack suite."""
        suite = generate_full_attack_suite()
        
        # Should have multiple attack types
        attack_types = set(s.attack_type for s in suite)
        assert len(attack_types) >= 5

    def test_full_suite_all_blocked(self, configured_engine):
        """Full suite should have most attacks blocked."""
        suite = generate_full_attack_suite()
        report = configured_engine.run_suite(suite)
        
        # Most attacks should be blocked (some PDO mutation may succeed if not sealed)
        block_rate = (report.blocked + report.detected) / report.total_attacks
        assert block_rate >= 0.8
