"""
Adversarial Tests for GIE

Per PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-028.
Agent: GID-06 (Sam) — Security Auditor

Features:
- Adversarial agent injection tests
- BER spoof resistance validation
- Proof tampering simulations
- UI output overflow attacks
"""

from __future__ import annotations

import hashlib
import json
import random
import string
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class AttackType(Enum):
    """Types of adversarial attacks."""
    AGENT_INJECTION = "AGENT_INJECTION"     # Unauthorized agent joins PAC
    BER_SPOOF = "BER_SPOOF"                 # Fake BER submission
    WRAP_TAMPERING = "WRAP_TAMPERING"       # Modified WRAP content
    HASH_COLLISION = "HASH_COLLISION"       # Attempt hash collision
    UI_OVERFLOW = "UI_OVERFLOW"             # Exceed emission limits
    CHECKPOINT_SPOOF = "CHECKPOINT_SPOOF"   # Fake checkpoint injection
    PDO_MUTATION = "PDO_MUTATION"           # Attempt to modify sealed PDO
    REPLAY_ATTACK = "REPLAY_ATTACK"         # Replay old valid artifacts


class AttackResult(Enum):
    """Result of attack attempt."""
    BLOCKED = "BLOCKED"           # Attack was blocked
    DETECTED = "DETECTED"         # Attack detected, logged
    MITIGATED = "MITIGATED"       # Attack partially successful but contained
    SUCCEEDED = "SUCCEEDED"       # Attack succeeded (failure)


class DefenseLayer(Enum):
    """Layer where defense operates."""
    AUTHENTICATION = "AUTHENTICATION"  # Identity verification
    AUTHORIZATION = "AUTHORIZATION"    # Permission checking
    VALIDATION = "VALIDATION"          # Input validation
    CRYPTOGRAPHIC = "CRYPTOGRAPHIC"    # Hash/signature verification
    RATE_LIMITING = "RATE_LIMITING"    # Throttling
    AUDIT = "AUDIT"                    # Logging/detection


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AttackScenario:
    """
    An adversarial attack scenario.
    """
    attack_id: str
    attack_type: AttackType
    description: str
    payload: Dict[str, Any]
    expected_defenses: List[DefenseLayer]
    expected_result: AttackResult


@dataclass
class AttackAttempt:
    """
    Record of an attack attempt.
    """
    scenario: AttackScenario
    timestamp: str
    result: AttackResult
    defense_triggered: Optional[DefenseLayer] = None
    error_message: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class SecurityReport:
    """
    Security audit report.
    """
    report_id: str
    pac_id: str
    total_attacks: int = 0
    blocked: int = 0
    detected: int = 0
    mitigated: int = 0
    succeeded: int = 0
    attempts: List[AttackAttempt] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK GIE COMPONENTS (for testing defenses)
# ═══════════════════════════════════════════════════════════════════════════════

class MockGIERegistry:
    """Mock GIE registry for testing."""

    def __init__(self):
        self._registered_agents: Set[str] = set()
        self._active_pacs: Set[str] = set()
        self._pac_agents: Dict[str, Set[str]] = {}
        self._sealed_pdos: Set[str] = set()

    def register_agent(self, gid: str) -> None:
        self._registered_agents.add(gid)

    def is_registered(self, gid: str) -> bool:
        return gid in self._registered_agents

    def activate_pac(self, pac_id: str, agent_gids: List[str]) -> None:
        self._active_pacs.add(pac_id)
        self._pac_agents[pac_id] = set(agent_gids)

    def is_pac_active(self, pac_id: str) -> bool:
        return pac_id in self._active_pacs

    def is_agent_assigned(self, pac_id: str, gid: str) -> bool:
        return gid in self._pac_agents.get(pac_id, set())

    def seal_pdo(self, pdo_id: str) -> None:
        self._sealed_pdos.add(pdo_id)

    def is_sealed(self, pdo_id: str) -> bool:
        return pdo_id in self._sealed_pdos


class MockUIOutputManager:
    """Mock UI output manager with emission limits."""

    MAX_EMISSIONS_PER_PAC = 22  # Per UI Output Contract
    MAX_CHARS_PER_EMISSION = 120

    def __init__(self):
        self._emissions: Dict[str, int] = {}

    def emit(self, pac_id: str, message: str) -> Tuple[bool, Optional[str]]:
        """
        Attempt to emit a message.
        
        Returns (success, error_message).
        """
        # Check message length
        if len(message) > self.MAX_CHARS_PER_EMISSION:
            return False, f"Emission exceeds {self.MAX_CHARS_PER_EMISSION} chars"

        # Check emission count
        current = self._emissions.get(pac_id, 0)
        if current >= self.MAX_EMISSIONS_PER_PAC:
            return False, f"PAC {pac_id} exceeded {self.MAX_EMISSIONS_PER_PAC} emissions"

        self._emissions[pac_id] = current + 1
        return True, None

    def get_count(self, pac_id: str) -> int:
        return self._emissions.get(pac_id, 0)


class MockCryptoVerifier:
    """Mock cryptographic verifier."""

    def __init__(self):
        self._known_hashes: Dict[str, str] = {}  # content -> hash

    def register_hash(self, content: str, content_hash: str) -> None:
        self._known_hashes[content] = content_hash

    def verify_hash(self, content: str, claimed_hash: str) -> bool:
        """Verify hash matches content."""
        computed = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
        return computed == claimed_hash

    def compute_hash(self, content: str) -> str:
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


# ═══════════════════════════════════════════════════════════════════════════════
# ADVERSARIAL TEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class AdversarialTestEngine:
    """
    Engine for running adversarial tests against GIE components.
    """

    def __init__(
        self,
        registry: Optional[MockGIERegistry] = None,
        ui_manager: Optional[MockUIOutputManager] = None,
        crypto_verifier: Optional[MockCryptoVerifier] = None,
    ):
        """Initialize with mock components."""
        self._registry = registry or MockGIERegistry()
        self._ui_manager = ui_manager or MockUIOutputManager()
        self._crypto = crypto_verifier or MockCryptoVerifier()
        self._attack_handlers: Dict[AttackType, Callable] = {
            AttackType.AGENT_INJECTION: self._test_agent_injection,
            AttackType.BER_SPOOF: self._test_ber_spoof,
            AttackType.WRAP_TAMPERING: self._test_wrap_tampering,
            AttackType.HASH_COLLISION: self._test_hash_collision,
            AttackType.UI_OVERFLOW: self._test_ui_overflow,
            AttackType.CHECKPOINT_SPOOF: self._test_checkpoint_spoof,
            AttackType.PDO_MUTATION: self._test_pdo_mutation,
            AttackType.REPLAY_ATTACK: self._test_replay_attack,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Setup Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def setup_valid_pac(
        self,
        pac_id: str,
        agent_gids: List[str],
    ) -> None:
        """Set up a valid PAC for testing."""
        for gid in agent_gids:
            self._registry.register_agent(gid)
        self._registry.activate_pac(pac_id, agent_gids)

    def setup_sealed_pdo(self, pdo_id: str) -> None:
        """Set up a sealed PDO."""
        self._registry.seal_pdo(pdo_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Attack Execution
    # ─────────────────────────────────────────────────────────────────────────

    def run_attack(self, scenario: AttackScenario) -> AttackAttempt:
        """
        Execute an attack scenario.
        
        Returns the attempt record.
        """
        start = time.time()

        handler = self._attack_handlers.get(scenario.attack_type)
        if not handler:
            return AttackAttempt(
                scenario=scenario,
                timestamp=datetime.utcnow().isoformat() + "Z",
                result=AttackResult.BLOCKED,
                error_message="Unknown attack type",
                duration_ms=(time.time() - start) * 1000,
            )

        result, defense, error = handler(scenario.payload)

        return AttackAttempt(
            scenario=scenario,
            timestamp=datetime.utcnow().isoformat() + "Z",
            result=result,
            defense_triggered=defense,
            error_message=error,
            duration_ms=(time.time() - start) * 1000,
        )

    def run_suite(
        self,
        scenarios: List[AttackScenario],
        pac_id: str = "PAC-TEST",
    ) -> SecurityReport:
        """
        Run a full suite of attack scenarios.
        
        Returns security report.
        """
        report_id = f"SEC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        report = SecurityReport(report_id=report_id, pac_id=pac_id)

        for scenario in scenarios:
            attempt = self.run_attack(scenario)
            report.attempts.append(attempt)
            report.total_attacks += 1

            if attempt.result == AttackResult.BLOCKED:
                report.blocked += 1
            elif attempt.result == AttackResult.DETECTED:
                report.detected += 1
            elif attempt.result == AttackResult.MITIGATED:
                report.mitigated += 1
            elif attempt.result == AttackResult.SUCCEEDED:
                report.succeeded += 1
                report.vulnerabilities.append(
                    f"{scenario.attack_type.value}: {scenario.description}"
                )

        return report

    # ─────────────────────────────────────────────────────────────────────────
    # Attack Handlers
    # ─────────────────────────────────────────────────────────────────────────

    def _test_agent_injection(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[AttackResult, Optional[DefenseLayer], Optional[str]]:
        """Test unauthorized agent injection."""
        pac_id = payload.get("pac_id", "PAC-001")
        fake_gid = payload.get("fake_gid", "GID-FAKE-999")

        # Defense 1: Check agent registration
        if not self._registry.is_registered(fake_gid):
            return (
                AttackResult.BLOCKED,
                DefenseLayer.AUTHENTICATION,
                f"Agent {fake_gid} not registered",
            )

        # Defense 2: Check PAC assignment
        if not self._registry.is_agent_assigned(pac_id, fake_gid):
            return (
                AttackResult.BLOCKED,
                DefenseLayer.AUTHORIZATION,
                f"Agent {fake_gid} not assigned to {pac_id}",
            )

        # Attack succeeded
        return (AttackResult.SUCCEEDED, None, None)

    def _test_ber_spoof(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[AttackResult, Optional[DefenseLayer], Optional[str]]:
        """Test BER spoofing."""
        pac_id = payload.get("pac_id", "PAC-001")
        fake_ber = payload.get("fake_ber", {})
        claimed_hash = payload.get("claimed_hash", "sha256:fake")

        # Defense: Verify BER content hash
        ber_content = json.dumps(fake_ber, sort_keys=True)
        if not self._crypto.verify_hash(ber_content, claimed_hash):
            return (
                AttackResult.BLOCKED,
                DefenseLayer.CRYPTOGRAPHIC,
                "BER hash verification failed",
            )

        return (AttackResult.SUCCEEDED, None, None)

    def _test_wrap_tampering(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[AttackResult, Optional[DefenseLayer], Optional[str]]:
        """Test WRAP content tampering."""
        original_hash = payload.get("original_hash", "sha256:original")
        tampered_content = payload.get("tampered_content", "tampered")
        claimed_hash = payload.get("claimed_hash", original_hash)

        # Defense: Verify content matches claimed hash
        if not self._crypto.verify_hash(tampered_content, claimed_hash):
            return (
                AttackResult.BLOCKED,
                DefenseLayer.CRYPTOGRAPHIC,
                "WRAP content hash mismatch",
            )

        return (AttackResult.SUCCEEDED, None, None)

    def _test_hash_collision(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[AttackResult, Optional[DefenseLayer], Optional[str]]:
        """Test hash collision attack."""
        content1 = payload.get("content1", "legitimate")
        content2 = payload.get("content2", "malicious")

        hash1 = self._crypto.compute_hash(content1)
        hash2 = self._crypto.compute_hash(content2)

        # Defense: SHA-256 collision resistance
        if hash1 == hash2 and content1 != content2:
            return (
                AttackResult.SUCCEEDED,
                None,
                "Hash collision found!",
            )

        return (
            AttackResult.BLOCKED,
            DefenseLayer.CRYPTOGRAPHIC,
            "No collision - hashes differ",
        )

    def _test_ui_overflow(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[AttackResult, Optional[DefenseLayer], Optional[str]]:
        """Test UI emission overflow."""
        pac_id = payload.get("pac_id", "PAC-001")
        emission_count = payload.get("emission_count", 50)
        message = payload.get("message", "spam")

        # Attempt to exceed emission limit
        success_count = 0
        for _ in range(emission_count):
            success, error = self._ui_manager.emit(pac_id, message)
            if success:
                success_count += 1
            else:
                return (
                    AttackResult.BLOCKED,
                    DefenseLayer.RATE_LIMITING,
                    f"Blocked after {success_count} emissions: {error}",
                )

        return (AttackResult.SUCCEEDED, None, None)

    def _test_checkpoint_spoof(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[AttackResult, Optional[DefenseLayer], Optional[str]]:
        """Test checkpoint spoofing."""
        fake_checkpoint = payload.get("checkpoint", {})
        agent_gid = payload.get("agent_gid", "GID-FAKE")
        pac_id = payload.get("pac_id", "PAC-001")

        # Defense 1: Agent must be registered and assigned
        if not self._registry.is_registered(agent_gid):
            return (
                AttackResult.BLOCKED,
                DefenseLayer.AUTHENTICATION,
                "Agent not registered",
            )

        if not self._registry.is_agent_assigned(pac_id, agent_gid):
            return (
                AttackResult.BLOCKED,
                DefenseLayer.AUTHORIZATION,
                "Agent not assigned to PAC",
            )

        # Defense 2: Checkpoint must have valid structure
        required_fields = ["checkpoint_type", "timestamp", "agent_gid"]
        for field in required_fields:
            if field not in fake_checkpoint:
                return (
                    AttackResult.BLOCKED,
                    DefenseLayer.VALIDATION,
                    f"Missing required field: {field}",
                )

        return (AttackResult.SUCCEEDED, None, None)

    def _test_pdo_mutation(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[AttackResult, Optional[DefenseLayer], Optional[str]]:
        """Test PDO mutation after sealing."""
        pdo_id = payload.get("pdo_id", "PDO-001")
        mutation = payload.get("mutation", {})

        # Defense: Sealed PDOs are immutable
        if self._registry.is_sealed(pdo_id):
            return (
                AttackResult.BLOCKED,
                DefenseLayer.VALIDATION,
                f"PDO {pdo_id} is sealed and immutable",
            )

        return (AttackResult.SUCCEEDED, None, None)

    def _test_replay_attack(
        self,
        payload: Dict[str, Any],
    ) -> Tuple[AttackResult, Optional[DefenseLayer], Optional[str]]:
        """Test replay attack with old valid artifact."""
        artifact_timestamp = payload.get("timestamp", "2025-01-01T00:00:00Z")
        max_age_seconds = payload.get("max_age_seconds", 300)

        # Defense: Check timestamp freshness
        try:
            artifact_time = datetime.fromisoformat(artifact_timestamp.replace("Z", "+00:00"))
            now = datetime.now(artifact_time.tzinfo)
            age = (now - artifact_time).total_seconds()

            if age > max_age_seconds:
                return (
                    AttackResult.BLOCKED,
                    DefenseLayer.VALIDATION,
                    f"Artifact too old ({age:.0f}s > {max_age_seconds}s)",
                )
        except (ValueError, TypeError):
            return (
                AttackResult.BLOCKED,
                DefenseLayer.VALIDATION,
                "Invalid timestamp format",
            )

        return (AttackResult.SUCCEEDED, None, None)


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_agent_injection_scenarios(count: int = 5) -> List[AttackScenario]:
    """Generate agent injection attack scenarios."""
    scenarios = []
    for i in range(count):
        scenarios.append(AttackScenario(
            attack_id=f"INJ-{i:03d}",
            attack_type=AttackType.AGENT_INJECTION,
            description=f"Inject fake agent GID-FAKE-{i}",
            payload={
                "pac_id": "PAC-001",
                "fake_gid": f"GID-FAKE-{i}",
            },
            expected_defenses=[DefenseLayer.AUTHENTICATION, DefenseLayer.AUTHORIZATION],
            expected_result=AttackResult.BLOCKED,
        ))
    return scenarios


def generate_ber_spoof_scenarios(count: int = 3) -> List[AttackScenario]:
    """Generate BER spoofing scenarios."""
    scenarios = []
    for i in range(count):
        fake_ber = {
            "pac_id": "PAC-001",
            "status": "APPROVE",
            "fake_field": f"fake-{i}",
        }
        scenarios.append(AttackScenario(
            attack_id=f"BER-SPOOF-{i:03d}",
            attack_type=AttackType.BER_SPOOF,
            description=f"Spoof BER with fake content {i}",
            payload={
                "pac_id": "PAC-001",
                "fake_ber": fake_ber,
                "claimed_hash": "sha256:definitely-not-real",
            },
            expected_defenses=[DefenseLayer.CRYPTOGRAPHIC],
            expected_result=AttackResult.BLOCKED,
        ))
    return scenarios


def generate_ui_overflow_scenarios() -> List[AttackScenario]:
    """Generate UI overflow attack scenarios."""
    return [
        AttackScenario(
            attack_id="UI-OVERFLOW-001",
            attack_type=AttackType.UI_OVERFLOW,
            description="Exceed 22 emission limit",
            payload={
                "pac_id": "PAC-OVERFLOW",
                "emission_count": 50,
                "message": "spam message",
            },
            expected_defenses=[DefenseLayer.RATE_LIMITING],
            expected_result=AttackResult.BLOCKED,
        ),
        AttackScenario(
            attack_id="UI-OVERFLOW-002",
            attack_type=AttackType.UI_OVERFLOW,
            description="Emit oversized message",
            payload={
                "pac_id": "PAC-OVERFLOW-2",
                "emission_count": 1,
                "message": "x" * 200,  # Exceeds 120 char limit
            },
            expected_defenses=[DefenseLayer.VALIDATION],
            expected_result=AttackResult.BLOCKED,
        ),
    ]


def generate_full_attack_suite() -> List[AttackScenario]:
    """Generate comprehensive attack suite."""
    suite = []
    suite.extend(generate_agent_injection_scenarios(3))
    suite.extend(generate_ber_spoof_scenarios(2))
    suite.extend(generate_ui_overflow_scenarios())
    suite.append(AttackScenario(
        attack_id="TAMPER-001",
        attack_type=AttackType.WRAP_TAMPERING,
        description="Tamper WRAP content",
        payload={
            "original_hash": "sha256:original",
            "tampered_content": "malicious payload",
            "claimed_hash": "sha256:original",
        },
        expected_defenses=[DefenseLayer.CRYPTOGRAPHIC],
        expected_result=AttackResult.BLOCKED,
    ))
    suite.append(AttackScenario(
        attack_id="COLLISION-001",
        attack_type=AttackType.HASH_COLLISION,
        description="Attempt hash collision",
        payload={
            "content1": "legitimate content",
            "content2": "malicious content",
        },
        expected_defenses=[DefenseLayer.CRYPTOGRAPHIC],
        expected_result=AttackResult.BLOCKED,
    ))
    suite.append(AttackScenario(
        attack_id="PDO-MUTATE-001",
        attack_type=AttackType.PDO_MUTATION,
        description="Mutate sealed PDO",
        payload={
            "pdo_id": "PDO-SEALED-001",
            "mutation": {"status": "tampered"},
        },
        expected_defenses=[DefenseLayer.VALIDATION],
        expected_result=AttackResult.BLOCKED,
    ))
    suite.append(AttackScenario(
        attack_id="REPLAY-001",
        attack_type=AttackType.REPLAY_ATTACK,
        description="Replay old artifact",
        payload={
            "timestamp": "2020-01-01T00:00:00Z",
            "max_age_seconds": 300,
        },
        expected_defenses=[DefenseLayer.VALIDATION],
        expected_result=AttackResult.BLOCKED,
    ))
    return suite
