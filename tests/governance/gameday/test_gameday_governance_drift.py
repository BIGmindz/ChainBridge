"""
🧪 Gameday Test: G3 — Governance Drift Detection
PAC-GOV-GAMEDAY-01: Governance Failure Simulation

Simulate:
- Governance file modification at runtime
- Fingerprint mismatch scenarios
- Drift detection edge cases

Invariants:
- Operation denied (GovernanceDriftError raised)
- No state mutation
- Event emitted (GOVERNANCE_DRIFT_DETECTED)
- audit_ref present
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.governance.event_sink import GovernanceEventEmitter, InMemorySink
from core.governance.events import GovernanceEvent, GovernanceEventType, governance_drift_event
from core.governance.governance_fingerprint import (
    GovernanceBootError,
    GovernanceDriftError,
    GovernanceFingerprint,
    GovernanceFingerprintEngine,
)

# =============================================================================
# G3.1 — File Modification Drift
# =============================================================================


class TestFileModificationDrift:
    """
    G3.1: Simulate governance drift from file modification.

    Attack scenario: An attacker modifies governance files
    at runtime to weaken security controls.
    """

    @pytest.fixture
    def governance_root(self, tmp_path: Path) -> Path:
        """Create a minimal governance root for testing."""
        # Create required directory structure
        (tmp_path / "config").mkdir()
        (tmp_path / ".github").mkdir()
        (tmp_path / "manifests").mkdir()
        (tmp_path / "core" / "governance").mkdir(parents=True)
        (tmp_path / "docs" / "governance").mkdir(parents=True)

        # Create required files
        (tmp_path / "config" / "agents.json").write_text('{"agents": []}')
        (tmp_path / ".github" / "ALEX_RULES.json").write_text('{"rules": []}')
        (tmp_path / "manifests" / "GID-01_Test.yaml").write_text("agent_id: Test\ngid: GID-01")
        (tmp_path / "core" / "governance" / "drcp.py").write_text("# DRCP module\n")
        (tmp_path / "core" / "governance" / "diggi_corrections.py").write_text("# Diggi corrections\n")
        (tmp_path / "docs" / "governance" / "REPO_SCOPE_MANIFEST.md").write_text("# Repo Scope\n")

        return tmp_path

    def test_agents_json_modification_detected(self, governance_root: Path) -> None:
        """Modification to agents.json should trigger drift error."""
        engine = GovernanceFingerprintEngine(governance_root)
        engine.compute_fingerprint()

        # Modify agents.json (attacker adds rogue agent)
        agents_file = governance_root / "config" / "agents.json"
        agents_file.write_text('{"agents": ["ROGUE-99"]}')

        # Invariant 1: Operation denied
        with pytest.raises(GovernanceDriftError) as exc_info:
            engine.verify_no_drift()

        # Verify error has hash info
        assert exc_info.value.original_hash != exc_info.value.current_hash

    def test_alex_rules_modification_detected(self, governance_root: Path) -> None:
        """Modification to ALEX_RULES.json should trigger drift error."""
        engine = GovernanceFingerprintEngine(governance_root)
        engine.compute_fingerprint()

        # Modify ALEX_RULES.json (attacker weakens rules)
        rules_file = governance_root / ".github" / "ALEX_RULES.json"
        rules_file.write_text('{"rules": ["ALLOW_ALL"]}')

        # Invariant 1: Operation denied
        with pytest.raises(GovernanceDriftError):
            engine.verify_no_drift()

    def test_drcp_modification_detected(self, governance_root: Path) -> None:
        """Modification to DRCP module should trigger drift error."""
        engine = GovernanceFingerprintEngine(governance_root)
        engine.compute_fingerprint()

        # Modify DRCP (attacker adds backdoor)
        drcp_file = governance_root / "core" / "governance" / "drcp.py"
        drcp_file.write_text("# BACKDOOR: bypass all checks\ndef allow_all(): return True\n")

        # Invariant 1: Operation denied
        with pytest.raises(GovernanceDriftError):
            engine.verify_no_drift()


# =============================================================================
# G3.2 — New File Addition Drift
# =============================================================================


class TestNewFileAdditionDrift:
    """
    G3.2: Simulate drift from unauthorized file additions.

    Attack scenario: An attacker adds new governance files
    that might be auto-loaded by the system.
    """

    @pytest.fixture
    def governance_root(self, tmp_path: Path) -> Path:
        """Create a minimal governance root for testing."""
        (tmp_path / "config").mkdir()
        (tmp_path / ".github").mkdir()
        (tmp_path / "manifests").mkdir()
        (tmp_path / "core" / "governance").mkdir(parents=True)
        (tmp_path / "docs" / "governance").mkdir(parents=True)

        (tmp_path / "config" / "agents.json").write_text('{"agents": []}')
        (tmp_path / ".github" / "ALEX_RULES.json").write_text('{"rules": []}')
        (tmp_path / "manifests" / "GID-01_Test.yaml").write_text("agent_id: Test\ngid: GID-01")
        (tmp_path / "core" / "governance" / "drcp.py").write_text("# DRCP module\n")
        (tmp_path / "core" / "governance" / "diggi_corrections.py").write_text("# Diggi corrections\n")
        (tmp_path / "docs" / "governance" / "REPO_SCOPE_MANIFEST.md").write_text("# Repo Scope\n")

        return tmp_path

    def test_new_manifest_detected(self, governance_root: Path) -> None:
        """Adding new manifest file should trigger drift error.

        Note: manifests/*.yaml is a watched glob, so new files ARE detected.
        """
        engine = GovernanceFingerprintEngine(governance_root)
        engine.compute_fingerprint()

        # Add rogue agent manifest
        (governance_root / "manifests" / "GID-99_Rogue.yaml").write_text("agent_id: Rogue\ngid: GID-99\npermissions: [EXECUTE_ALL]")

        # Invariant 1: Operation denied
        with pytest.raises(GovernanceDriftError):
            engine.verify_no_drift()

    def test_new_diggi_module_detected(self, governance_root: Path) -> None:
        """Adding new diggi module should trigger drift error.

        Note: core/governance/diggi_*.py is a watched glob pattern.
        """
        engine = GovernanceFingerprintEngine(governance_root)
        engine.compute_fingerprint()

        # Add rogue diggi module
        (governance_root / "core" / "governance" / "diggi_backdoor.py").write_text("# Backdoor module\ndef bypass(): return True\n")

        # Invariant 1: Operation denied
        with pytest.raises(GovernanceDriftError):
            engine.verify_no_drift()


# =============================================================================
# G3.3 — Fingerprint Tampering
# =============================================================================


class TestFingerprintTampering:
    """
    G3.3: Simulate attempts to tamper with fingerprint state.

    Attack scenario: An attacker tries to manipulate the
    cached fingerprint to mask drift.
    """

    @pytest.fixture
    def governance_root(self, tmp_path: Path) -> Path:
        """Create a minimal governance root for testing."""
        (tmp_path / "config").mkdir()
        (tmp_path / ".github").mkdir()
        (tmp_path / "manifests").mkdir()
        (tmp_path / "core" / "governance").mkdir(parents=True)
        (tmp_path / "docs" / "governance").mkdir(parents=True)

        (tmp_path / "config" / "agents.json").write_text('{"agents": []}')
        (tmp_path / ".github" / "ALEX_RULES.json").write_text('{"rules": []}')
        (tmp_path / "manifests" / "GID-01_Test.yaml").write_text("agent_id: Test\ngid: GID-01")
        (tmp_path / "core" / "governance" / "drcp.py").write_text("# DRCP module\n")
        (tmp_path / "core" / "governance" / "diggi_corrections.py").write_text("# Diggi corrections\n")
        (tmp_path / "docs" / "governance" / "REPO_SCOPE_MANIFEST.md").write_text("# Repo Scope\n")

        return tmp_path

    def test_cannot_verify_before_compute(self, governance_root: Path) -> None:
        """Verify must fail if fingerprint not computed (fail closed)."""
        engine = GovernanceFingerprintEngine(governance_root)

        # Don't compute fingerprint

        # Invariant 1: Operation denied (fail closed)
        with pytest.raises(GovernanceBootError) as exc_info:
            engine.verify_no_drift()

        assert "not computed" in str(exc_info.value).lower()

    def test_recompute_does_not_mask_drift(self, governance_root: Path) -> None:
        """
        Recomputing fingerprint should detect drift in current state.

        The baseline is set at first compute and changes are detected.
        """
        engine = GovernanceFingerprintEngine(governance_root)
        original_fp = engine.compute_fingerprint()
        original_hash = original_fp.composite_hash

        # Modify file
        (governance_root / "config" / "agents.json").write_text('{"agents": ["changed"]}')

        # Verify should still fail (baseline unchanged)
        with pytest.raises(GovernanceDriftError):
            engine.verify_no_drift()

        # Verify the original hash was recorded
        assert engine._fingerprint is not None
        # Original baseline should still be stored
        assert engine._fingerprint.composite_hash == original_hash


# =============================================================================
# G3.4 — Drift Event Emission
# =============================================================================


class TestDriftEventEmission:
    """
    G3.4: Verify drift detection emits proper telemetry events.

    Invariant: GOVERNANCE_DRIFT_DETECTED event must be emitted.
    """

    def test_drift_event_structure(self) -> None:
        """Test governance_drift_event factory produces valid event."""
        event = governance_drift_event(
            original_hash="abc123",
            current_hash="def456",
            message="Drift detected in config/agents.json",
        )

        # Verify event structure
        assert event.event_type == GovernanceEventType.GOVERNANCE_DRIFT_DETECTED.value
        assert event.reason_code == "GOVERNANCE_DRIFT"
        assert event.metadata["original_hash"] == "abc123"
        assert event.metadata["current_hash"] == "def456"

    def test_drift_event_has_audit_ref(self) -> None:
        """Drift event should support metadata for audit tracking."""
        event = governance_drift_event(
            original_hash="abc123",
            current_hash="def456",
            message="Drift in config/agents.json",
            metadata={"audit_ref": "audit-2024-01-01-001"},
        )

        # Invariant 4: audit info present
        assert event.metadata["audit_ref"] == "audit-2024-01-01-001"

    def test_drift_event_captured_by_sink(self) -> None:
        """Drift event should be captured by InMemorySink."""
        sink = InMemorySink()
        emitter = GovernanceEventEmitter()
        emitter.add_sink(sink)

        try:
            event = governance_drift_event(
                original_hash="abc123",
                current_hash="def456",
                message="Drift in config/agents.json",
            )

            # Emit the event
            emitter.emit(event)

            # Invariant 3: Event emitted
            events = sink.get_events()
            assert len(events) == 1
            assert events[0].event_type == GovernanceEventType.GOVERNANCE_DRIFT_DETECTED.value
        finally:
            emitter.remove_sink(sink)


# =============================================================================
# G3.5 — No State Mutation on Drift
# =============================================================================


class TestNoStateMutationOnDrift:
    """
    G3.5: Verify drift detection does not mutate state.

    Invariant: Failed drift detection leaves no side effects.
    """

    @pytest.fixture
    def governance_root(self, tmp_path: Path) -> Path:
        """Create a minimal governance root for testing."""
        (tmp_path / "config").mkdir()
        (tmp_path / ".github").mkdir()
        (tmp_path / "manifests").mkdir()
        (tmp_path / "core" / "governance").mkdir(parents=True)
        (tmp_path / "docs" / "governance").mkdir(parents=True)

        (tmp_path / "config" / "agents.json").write_text('{"agents": []}')
        (tmp_path / ".github" / "ALEX_RULES.json").write_text('{"rules": []}')
        (tmp_path / "manifests" / "GID-01_Test.yaml").write_text("agent_id: Test\ngid: GID-01")
        (tmp_path / "core" / "governance" / "drcp.py").write_text("# DRCP module\n")
        (tmp_path / "core" / "governance" / "diggi_corrections.py").write_text("# Diggi corrections\n")
        (tmp_path / "docs" / "governance" / "REPO_SCOPE_MANIFEST.md").write_text("# Repo Scope\n")

        return tmp_path

    def test_engine_state_unchanged_after_drift(self, governance_root: Path) -> None:
        """Engine state should remain unchanged after drift detection."""
        engine = GovernanceFingerprintEngine(governance_root)
        fp = engine.compute_fingerprint()

        # Capture state
        original_hash = fp.composite_hash
        original_initialized = engine.is_initialized()

        # Modify file
        (governance_root / "config" / "agents.json").write_text('{"agents": ["drift"]}')

        # Trigger drift (should raise)
        with pytest.raises(GovernanceDriftError):
            engine.verify_no_drift()

        # Invariant 2: No state mutation
        # Engine should still be initialized
        assert engine.is_initialized() == original_initialized

        # Baseline should still be the same
        # (internal _fingerprint stores original baseline)
        assert engine._fingerprint is not None
        assert engine._fingerprint.composite_hash == original_hash

    def test_multiple_drift_checks_consistent(self, governance_root: Path) -> None:
        """Multiple drift checks should produce consistent results."""
        engine = GovernanceFingerprintEngine(governance_root)
        engine.compute_fingerprint()

        # Modify file
        (governance_root / "config" / "agents.json").write_text('{"agents": ["drift"]}')

        # Multiple checks should all fail consistently
        for _ in range(3):
            with pytest.raises(GovernanceDriftError):
                engine.verify_no_drift()
