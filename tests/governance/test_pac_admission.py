"""
PAC Admission Gate Tests
════════════════════════════════════════════════════════════════════════════════

Tests for PAC-CODY-CONSTITUTION-ENFORCEMENT-02 Task 1: PAC Admission Gate

Proves:
- PAC without lock acknowledgment fails
- PAC with complete acknowledgment succeeds
- Forbidden zone violations block admission
- Telemetry emitted on all outcomes

════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from core.governance.constitution_engine import (
    ConstitutionEngine,
    ForbiddenZoneError,
    PACAdmissionError,
)
from core.governance.pac_admission import (
    PACAdmissionGate,
    PACAdmissionOutcome,
    PACDeclaration,
    admit_pac,
    get_pac_admission_gate,
    get_required_locks_for_scopes,
    reset_pac_admission_gate,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def test_lock_registry(tmp_path: Path) -> Path:
    """Create a test lock registry."""
    registry = {
        "version": "1.0",
        "locks": [
            {
                "lock_id": "LOCK-TEST-001",
                "description": "Test lock 1",
                "scope": ["gateway"],
                "type": "invariant",
                "enforcement": [{"pac_gate": True}],
                "severity": "CRITICAL",
                "violation_policy": {"action": "HARD_FAIL", "telemetry": "REQUIRED"},
            },
            {
                "lock_id": "LOCK-TEST-002",
                "description": "Test lock 2",
                "scope": ["occ"],
                "type": "invariant",
                "enforcement": [{"pac_gate": True}],
                "severity": "HIGH",
                "violation_policy": {"action": "HARD_FAIL", "telemetry": "REQUIRED"},
            },
            {
                "lock_id": "LOCK-TEST-003",
                "description": "Test lock 3 - no pac_gate",
                "scope": ["gateway"],
                "type": "constraint",
                "enforcement": [{"test_required": "tests/test.py"}],
                "severity": "MEDIUM",
                "violation_policy": {"action": "SOFT_FAIL", "telemetry": "OPTIONAL"},
            },
            {
                "lock_id": "LOCK-TEST-FORBIDDEN-001",
                "description": "Forbidden zone lock",
                "scope": ["governance"],
                "type": "boundary",
                "enforcement": [{"pac_gate": True}],
                "severity": "CRITICAL",
                "violation_policy": {"action": "HARD_FAIL", "telemetry": "REQUIRED"},
                "forbidden_zones": ["forbidden_path/secret.py"],
            },
        ],
    }
    registry_path = tmp_path / "LOCK_REGISTRY.yaml"
    with open(registry_path, "w") as f:
        yaml.dump(registry, f)
    return registry_path


@pytest.fixture
def test_engine(test_lock_registry: Path) -> ConstitutionEngine:
    """Create a Constitution Engine with test registry."""
    engine = ConstitutionEngine(registry_path=test_lock_registry)
    engine.load_registry()
    return engine


@pytest.fixture
def test_gate(test_engine: ConstitutionEngine) -> PACAdmissionGate:
    """Create a PAC Admission Gate with test engine."""
    return PACAdmissionGate(engine=test_engine)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton after each test."""
    yield
    reset_pac_admission_gate()


# ═══════════════════════════════════════════════════════════════════════════════
# PAC DECLARATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPACDeclaration:
    """Tests for PAC declaration validation."""

    def test_valid_declaration(self):
        """Valid PAC declaration creates successfully."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-FEATURE-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
        )
        assert declaration.pac_id == "PAC-TEST-FEATURE-01"
        assert declaration.acknowledged_locks == ("LOCK-TEST-001",)
        assert declaration.affected_scopes == ("gateway",)

    def test_empty_pac_id_fails(self):
        """Empty PAC ID raises ValueError."""
        with pytest.raises(ValueError, match="PAC ID cannot be empty"):
            PACDeclaration(
                pac_id="",
                acknowledged_locks=("LOCK-TEST-001",),
                affected_scopes=("gateway",),
            )

    def test_invalid_pac_id_format_fails(self):
        """Invalid PAC ID format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid PAC ID format"):
            PACDeclaration(
                pac_id="INVALID-ID",
                acknowledged_locks=("LOCK-TEST-001",),
                affected_scopes=("gateway",),
            )

    def test_no_scopes_fails(self):
        """PAC without affected scopes raises ValueError."""
        with pytest.raises(ValueError, match="PAC must declare at least one affected scope"):
            PACDeclaration(
                pac_id="PAC-TEST-FEATURE-01",
                acknowledged_locks=("LOCK-TEST-001",),
                affected_scopes=(),
            )


# ═══════════════════════════════════════════════════════════════════════════════
# PAC ADMISSION GATE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPACAdmissionGate:
    """Tests for PAC admission gate enforcement."""

    def test_pac_with_all_locks_admitted(self, test_gate: PACAdmissionGate):
        """PAC with all required locks acknowledged is admitted."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-COMPLETE-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
        )

        event = test_gate.admit(declaration)

        assert event.outcome == PACAdmissionOutcome.ADMITTED
        assert event.pac_id == "PAC-TEST-COMPLETE-01"
        assert len(event.missing_locks) == 0

    def test_pac_without_lock_acknowledgment_fails(self, test_gate: PACAdmissionGate):
        """PAC without required lock acknowledgment is denied."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-INCOMPLETE-01",
            acknowledged_locks=(),  # Missing LOCK-TEST-001
            affected_scopes=("gateway",),
        )

        with pytest.raises(PACAdmissionError) as exc_info:
            test_gate.admit(declaration)

        assert "Missing lock acknowledgments" in str(exc_info.value)
        assert "LOCK-TEST-001" in exc_info.value.missing_locks

    def test_pac_with_partial_acknowledgment_fails(self, test_gate: PACAdmissionGate):
        """PAC with partial lock acknowledgment is denied."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-PARTIAL-01",
            acknowledged_locks=("LOCK-TEST-001",),  # Missing LOCK-TEST-002
            affected_scopes=("gateway", "occ"),  # Requires both locks
        )

        with pytest.raises(PACAdmissionError) as exc_info:
            test_gate.admit(declaration)

        assert "LOCK-TEST-002" in exc_info.value.missing_locks

    def test_pac_with_extra_acknowledgment_succeeds(self, test_gate: PACAdmissionGate):
        """PAC with extra lock acknowledgments is admitted."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-EXTRA-01",
            acknowledged_locks=("LOCK-TEST-001", "LOCK-TEST-002"),  # Extra lock
            affected_scopes=("gateway",),  # Only needs LOCK-TEST-001
        )

        event = test_gate.admit(declaration)

        assert event.outcome == PACAdmissionOutcome.ADMITTED

    def test_non_pac_gate_locks_not_required(self, test_gate: PACAdmissionGate):
        """Locks without pac_gate enforcement are not required for admission."""
        # LOCK-TEST-003 has no pac_gate, so gateway scope only needs LOCK-TEST-001
        declaration = PACDeclaration(
            pac_id="PAC-TEST-NO-PAC-GATE-01",
            acknowledged_locks=("LOCK-TEST-001",),  # Only pac_gate locks required
            affected_scopes=("gateway",),
        )

        event = test_gate.admit(declaration)

        assert event.outcome == PACAdmissionOutcome.ADMITTED


# ═══════════════════════════════════════════════════════════════════════════════
# FORBIDDEN ZONE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestForbiddenZones:
    """Tests for forbidden zone enforcement."""

    def test_forbidden_zone_modification_blocked(self, test_gate: PACAdmissionGate):
        """PAC touching forbidden zone is blocked."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-FORBIDDEN-01",
            acknowledged_locks=("LOCK-TEST-FORBIDDEN-001",),
            affected_scopes=("governance",),
            touched_files=("forbidden_path/secret.py",),  # Forbidden zone
        )

        with pytest.raises(ForbiddenZoneError) as exc_info:
            test_gate.admit(declaration)

        assert "forbidden_path/secret.py" in str(exc_info.value)

    def test_non_forbidden_path_allowed(self, test_gate: PACAdmissionGate):
        """PAC touching non-forbidden paths is allowed."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-SAFE-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            touched_files=("gateway/new_feature.py",),  # Not forbidden
        )

        event = test_gate.admit(declaration)

        assert event.outcome == PACAdmissionOutcome.ADMITTED


# ═══════════════════════════════════════════════════════════════════════════════
# TELEMETRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPACAdmissionTelemetry:
    """Tests for PAC admission telemetry."""

    def test_telemetry_emitted_on_admission(self, test_gate: PACAdmissionGate):
        """Telemetry event emitted on successful admission."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-TELEMETRY-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
        )

        event = test_gate.admit(declaration)

        # Check event in gate's event list
        events = test_gate.get_events()
        assert len(events) == 1
        assert events[0].outcome == PACAdmissionOutcome.ADMITTED

    def test_telemetry_emitted_on_denial(self, test_gate: PACAdmissionGate):
        """Telemetry event emitted on admission denial."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-DENIAL-01",
            acknowledged_locks=(),
            affected_scopes=("gateway",),
        )

        with pytest.raises(PACAdmissionError):
            test_gate.admit(declaration)

        events = test_gate.get_events()
        assert len(events) == 1
        assert events[0].outcome == PACAdmissionOutcome.DENIED_MISSING_LOCKS

    def test_event_to_dict_format(self, test_gate: PACAdmissionGate):
        """Telemetry event converts to proper dict format."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-FORMAT-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
        )

        event = test_gate.admit(declaration)
        event_dict = event.to_dict()

        assert event_dict["event"] == "PAC_ADMISSION"
        assert event_dict["pac_id"] == "PAC-TEST-FORMAT-01"
        assert event_dict["outcome"] == "ADMITTED"
        assert "timestamp" in event_dict


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE CONVENIENCE FUNCTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_required_locks_for_scopes(self, test_engine: ConstitutionEngine):
        """get_required_locks_for_scopes returns correct locks."""
        with patch("core.governance.pac_admission.get_constitution_engine", return_value=test_engine):
            reset_pac_admission_gate()

            locks = get_required_locks_for_scopes(["gateway"])
            assert "LOCK-TEST-001" in locks
            assert "LOCK-TEST-003" not in locks  # No pac_gate

    def test_admit_pac_function(self, test_engine: ConstitutionEngine):
        """admit_pac convenience function works."""
        with patch("core.governance.pac_admission.get_constitution_engine", return_value=test_engine):
            reset_pac_admission_gate()

            declaration = PACDeclaration(
                pac_id="PAC-TEST-CONVENIENCE-01",
                acknowledged_locks=("LOCK-TEST-001",),
                affected_scopes=("gateway",),
            )

            event = admit_pac(declaration)
            assert event.outcome == PACAdmissionOutcome.ADMITTED


# ═══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED BEHAVIOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFailClosedBehavior:
    """Tests proving fail-closed enforcement."""

    def test_admission_is_non_optional(self, test_gate: PACAdmissionGate):
        """Lock acknowledgment cannot be bypassed."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-BYPASS-01",
            acknowledged_locks=(),
            affected_scopes=("gateway",),
        )

        # Must raise - no way to bypass
        with pytest.raises(PACAdmissionError):
            test_gate.admit(declaration)

    def test_no_warn_only_mode(self, test_gate: PACAdmissionGate):
        """There is no warn-only mode - always fail-closed."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-WARN-01",
            acknowledged_locks=(),
            affected_scopes=("gateway",),
        )

        # No warning mode exists - must raise
        with pytest.raises(PACAdmissionError):
            test_gate.admit(declaration)

        # Verify event shows denial, not warning
        events = test_gate.get_events()
        assert events[0].outcome == PACAdmissionOutcome.DENIED_MISSING_LOCKS

    def test_multiple_scopes_require_all_locks(self, test_gate: PACAdmissionGate):
        """Multiple scopes require all applicable locks."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-MULTI-01",
            acknowledged_locks=("LOCK-TEST-001",),  # Missing LOCK-TEST-002
            affected_scopes=("gateway", "occ"),
        )

        with pytest.raises(PACAdmissionError) as exc_info:
            test_gate.admit(declaration)

        # Both locks required for both scopes
        assert "LOCK-TEST-002" in exc_info.value.missing_locks


# ═══════════════════════════════════════════════════════════════════════════════
# COLOR GATEWAY INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestColorGatewayIntegration:
    """Test Color Gateway enforcement in PAC admission."""

    def test_valid_agent_color_admitted(self, test_gate: PACAdmissionGate):
        """PAC with valid agent/color is admitted (after lock check)."""
        declaration = PACDeclaration(
            pac_id="PAC-CODY-TEST-COLOR-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
        )

        event = test_gate.admit(declaration)
        assert event.outcome == PACAdmissionOutcome.ADMITTED

    def test_color_mismatch_denied(self, test_gate: PACAdmissionGate):
        """PAC with agent/color mismatch is denied by Color Gateway."""
        from core.governance.color_gateway import ColorMismatchError

        declaration = PACDeclaration(
            pac_id="PAC-CODY-TEST-MISMATCH-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="YELLOW",  # Wrong color for CODY
        )

        with pytest.raises(ColorMismatchError):
            test_gate.admit(declaration)

        # Verify telemetry
        events = test_gate.get_events()
        assert events[-1].outcome == PACAdmissionOutcome.DENIED_COLOR_GATEWAY

    def test_teal_execution_denied(self, test_gate: PACAdmissionGate):
        """PAC with TEAL as executing color is denied."""
        from core.governance.color_gateway import TealExecutionError

        declaration = PACDeclaration(
            pac_id="PAC-BENSON-TEST-TEAL-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="BENSON",
            executing_gid="GID-00",
            executing_color="TEAL",  # TEAL cannot be executing lane
        )

        with pytest.raises(TealExecutionError) as exc_info:
            test_gate.admit(declaration)

        assert "orchestration-only" in str(exc_info.value)

        # Verify telemetry
        events = test_gate.get_events()
        assert events[-1].outcome == PACAdmissionOutcome.DENIED_COLOR_GATEWAY

    def test_no_color_info_skips_color_check(self, test_gate: PACAdmissionGate):
        """PAC without color info skips Color Gateway (backward compat)."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-NOCOLOR-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            # No executing_agent/gid/color provided
        )

        # Should pass if locks are acknowledged
        event = test_gate.admit(declaration)
        assert event.outcome == PACAdmissionOutcome.ADMITTED

    def test_color_check_before_lock_check(self, test_gate: PACAdmissionGate):
        """Color Gateway check runs before lock acknowledgment check."""
        from core.governance.color_gateway import ColorMismatchError

        declaration = PACDeclaration(
            pac_id="PAC-TEST-ORDER-01",
            acknowledged_locks=(),  # Would fail lock check
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="YELLOW",  # Color mismatch (first failure)
        )

        # Should fail with ColorMismatchError, not PACAdmissionError
        with pytest.raises(ColorMismatchError):
            test_gate.admit(declaration)


# ═══════════════════════════════════════════════════════════════════════════════
# END BANNER ENFORCEMENT TESTS — PAC-BENSON-CODY-END-BANNER-LINT-ENFORCEMENT-01
# ═══════════════════════════════════════════════════════════════════════════════


class TestEndBannerEnforcement:
    """Test END banner enforcement in PAC admission."""

    def test_valid_end_banner_admitted(self, test_gate: PACAdmissionGate):
        """PAC with valid END banner is admitted."""
        declaration = PACDeclaration(
            pac_id="PAC-CODY-TEST-BANNER-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            end_banner_agent="CODY",
            end_banner_gid="GID-01",
            end_banner_color="BLUE",
        )

        event = test_gate.admit(declaration)
        assert event.outcome == PACAdmissionOutcome.ADMITTED

    def test_mismatched_end_banner_agent_denied(self, test_gate: PACAdmissionGate):
        """PAC with END banner agent mismatch is denied."""
        from core.governance.pac_admission import EndBannerViolationError

        declaration = PACDeclaration(
            pac_id="PAC-CODY-TEST-BANNER-02",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            end_banner_agent="DAN",  # Wrong agent!
            end_banner_gid="GID-01",
            end_banner_color="BLUE",
        )

        with pytest.raises(EndBannerViolationError) as exc_info:
            test_gate.admit(declaration)

        assert "DAN" in str(exc_info.value)
        assert "CODY" in str(exc_info.value)

        # Verify telemetry
        events = test_gate.get_events()
        assert events[-1].outcome == PACAdmissionOutcome.DENIED_END_BANNER

    def test_mismatched_end_banner_gid_denied(self, test_gate: PACAdmissionGate):
        """PAC with END banner GID mismatch is denied."""
        from core.governance.pac_admission import EndBannerViolationError

        declaration = PACDeclaration(
            pac_id="PAC-CODY-TEST-BANNER-03",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            end_banner_agent="CODY",
            end_banner_gid="GID-07",  # Wrong GID!
            end_banner_color="BLUE",
        )

        with pytest.raises(EndBannerViolationError) as exc_info:
            test_gate.admit(declaration)

        assert "GID-07" in str(exc_info.value)
        assert "GID-01" in str(exc_info.value)

        # Verify telemetry
        events = test_gate.get_events()
        assert events[-1].outcome == PACAdmissionOutcome.DENIED_END_BANNER

    def test_mismatched_end_banner_color_denied(self, test_gate: PACAdmissionGate):
        """PAC with END banner color mismatch is denied."""
        from core.governance.pac_admission import EndBannerViolationError

        declaration = PACDeclaration(
            pac_id="PAC-CODY-TEST-BANNER-04",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            end_banner_agent="CODY",
            end_banner_gid="GID-01",
            end_banner_color="GREEN",  # Wrong color!
        )

        with pytest.raises(EndBannerViolationError) as exc_info:
            test_gate.admit(declaration)

        assert "GREEN" in str(exc_info.value)
        assert "BLUE" in str(exc_info.value)

        # Verify telemetry
        events = test_gate.get_events()
        assert events[-1].outcome == PACAdmissionOutcome.DENIED_END_BANNER

    def test_no_end_banner_info_skips_check(self, test_gate: PACAdmissionGate):
        """PAC without END banner info skips END banner check (backward compat)."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-NOBANNER-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            # No end_banner_* fields
        )

        # Should pass if other checks pass
        event = test_gate.admit(declaration)
        assert event.outcome == PACAdmissionOutcome.ADMITTED

    def test_end_banner_check_before_lock_check(self, test_gate: PACAdmissionGate):
        """END banner check runs before lock acknowledgment check."""
        from core.governance.pac_admission import EndBannerViolationError

        declaration = PACDeclaration(
            pac_id="PAC-TEST-ORDER-02",
            acknowledged_locks=(),  # Would fail lock check
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            end_banner_agent="DAN",  # END banner mismatch (first failure after color)
            end_banner_gid="GID-01",
            end_banner_color="BLUE",
        )

        # Should fail with EndBannerViolationError, not PACAdmissionError
        with pytest.raises(EndBannerViolationError):
            test_gate.admit(declaration)

    def test_unknown_agent_in_end_banner_denied(self, test_gate: PACAdmissionGate):
        """END banner with unknown agent is denied."""
        from core.governance.pac_admission import EndBannerViolationError

        declaration = PACDeclaration(
            pac_id="PAC-TEST-UNKNOWN-BANNER-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            end_banner_agent="UNKNOWN_AGENT",  # Unknown agent
            end_banner_gid="GID-99",
            end_banner_color="BLUE",
        )

        with pytest.raises(EndBannerViolationError) as exc_info:
            test_gate.admit(declaration)

        # Unknown agent fails because it doesn't match EXECUTING AGENT
        assert "does not match EXECUTING AGENT" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVATION BLOCK ENFORCEMENT — PAC-BENSON-ACTIVATION-BLOCK-IMPLEMENTATION-01
# ═══════════════════════════════════════════════════════════════════════════════


class TestActivationBlockEnforcement:
    """Test Activation Block enforcement in PAC admission."""

    def test_valid_activation_block_passes(self, test_gate: PACAdmissionGate):
        """Valid Activation Block passes admission."""
        from core.governance.activation_block import ActivationBlock

        block = ActivationBlock(
            agent_name="CODY",
            gid="GID-01",
            role="Backend Engineering",
            color="BLUE",
            emoji="🔵",
            prohibited_actions=frozenset(["identity_drift"]),
            persona_binding="Executing as CODY",
        )

        declaration = PACDeclaration(
            pac_id="PAC-TEST-ACTIVATION-VALID-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            activation_block=block,
        )

        event = test_gate.admit(declaration)
        assert event.outcome == PACAdmissionOutcome.ADMITTED

    def test_invalid_activation_block_gid_mismatch_denied(self, test_gate: PACAdmissionGate):
        """Activation Block with GID mismatch is denied."""
        from core.governance.activation_block import ActivationBlock, ActivationBlockViolationError

        block = ActivationBlock(
            agent_name="CODY",
            gid="GID-99",  # Wrong GID
            role="Backend Engineering",
            color="BLUE",
            emoji="🔵",
            prohibited_actions=frozenset(["identity_drift"]),
            persona_binding="Executing as CODY",
        )

        declaration = PACDeclaration(
            pac_id="PAC-TEST-ACTIVATION-GID-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            activation_block=block,
        )

        with pytest.raises(ActivationBlockViolationError) as exc_info:
            test_gate.admit(declaration)

        assert "does not match canonical GID" in str(exc_info.value)

        # Verify telemetry
        events = test_gate.get_events()
        assert events[-1].outcome == PACAdmissionOutcome.DENIED_ACTIVATION_BLOCK

    def test_invalid_activation_block_color_mismatch_denied(self, test_gate: PACAdmissionGate):
        """Activation Block with color mismatch is denied."""
        from core.governance.activation_block import ActivationBlock, ActivationBlockViolationError

        block = ActivationBlock(
            agent_name="CODY",
            gid="GID-01",
            role="Backend Engineering",
            color="GREEN",  # Wrong color
            emoji="🔵",
            prohibited_actions=frozenset(["identity_drift"]),
            persona_binding="Executing as CODY",
        )

        declaration = PACDeclaration(
            pac_id="PAC-TEST-ACTIVATION-COLOR-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            activation_block=block,
        )

        with pytest.raises(ActivationBlockViolationError) as exc_info:
            test_gate.admit(declaration)

        assert "does not match canonical color" in str(exc_info.value)

    def test_activation_block_before_color_gateway(self, test_gate: PACAdmissionGate):
        """Activation Block validation runs BEFORE Color Gateway check."""
        from core.governance.activation_block import ActivationBlock, ActivationBlockViolationError

        # Block with invalid agent - should fail at Activation Block level
        block = ActivationBlock(
            agent_name="UNKNOWN_AGENT",
            gid="GID-99",
            role="Test",
            color="BLUE",
            emoji="🔵",
            prohibited_actions=frozenset(["test"]),
            persona_binding="Test",
        )

        declaration = PACDeclaration(
            pac_id="PAC-TEST-ACTIVATION-ORDER-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="GREEN",  # Would fail Color Gateway
            activation_block=block,  # Should fail here first
        )

        # Should fail with ActivationBlockViolationError, not ColorGatewayViolation
        with pytest.raises(ActivationBlockViolationError):
            test_gate.admit(declaration)

    def test_activation_block_before_end_banner(self, test_gate: PACAdmissionGate):
        """Activation Block validation runs BEFORE END banner check."""
        from core.governance.activation_block import ActivationBlock, ActivationBlockViolationError

        # Block with invalid GID - should fail at Activation Block level
        block = ActivationBlock(
            agent_name="CODY",
            gid="GID-99",  # Wrong GID
            role="Backend Engineering",
            color="BLUE",
            emoji="🔵",
            prohibited_actions=frozenset(["test"]),
            persona_binding="Test",
        )

        declaration = PACDeclaration(
            pac_id="PAC-TEST-ACTIVATION-ORDER-02",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            end_banner_agent="DAN",  # Would fail END banner
            end_banner_gid="GID-07",
            end_banner_color="GREEN",
            activation_block=block,  # Should fail here first
        )

        # Should fail with ActivationBlockViolationError, not EndBannerViolationError
        with pytest.raises(ActivationBlockViolationError):
            test_gate.admit(declaration)

    def test_no_activation_block_backward_compat(self, test_gate: PACAdmissionGate):
        """PAC without Activation Block still works (backward compat)."""
        declaration = PACDeclaration(
            pac_id="PAC-TEST-NO-ACTIVATION-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            # No activation_block
        )

        # Should pass if other checks pass
        event = test_gate.admit(declaration)
        assert event.outcome == PACAdmissionOutcome.ADMITTED

    def test_activation_block_emoji_mismatch_denied(self, test_gate: PACAdmissionGate):
        """Activation Block with emoji mismatch is denied."""
        from core.governance.activation_block import ActivationBlock, ActivationBlockViolationError

        block = ActivationBlock(
            agent_name="CODY",
            gid="GID-01",
            role="Backend Engineering",
            color="BLUE",
            emoji="🟩",  # Wrong emoji
            prohibited_actions=frozenset(["identity_drift"]),
            persona_binding="Executing as CODY",
        )

        declaration = PACDeclaration(
            pac_id="PAC-TEST-ACTIVATION-EMOJI-01",
            acknowledged_locks=("LOCK-TEST-001",),
            affected_scopes=("gateway",),
            executing_agent="CODY",
            executing_gid="GID-01",
            executing_color="BLUE",
            activation_block=block,
        )

        with pytest.raises(ActivationBlockViolationError) as exc_info:
            test_gate.admit(declaration)

        assert "does not match canonical emoji" in str(exc_info.value)

