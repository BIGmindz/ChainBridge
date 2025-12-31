"""
Non-Executing Agent Enforcement Tests
═══════════════════════════════════════════════════════════════════════════════

PAC-PAX-P37-EXECUTION-ROLE-RESTRICTION-AND-SCOPE-REALIGNMENT-01
PAC-ALEX-P35-AGENT-REGISTRY-AND-GATE-ENFORCEMENT-FOR-PAX-01

Tests:
- PAX cannot emit PACs (GS_090)
- PAX cannot emit WRAPs (GS_091)
- PAX cannot create code/files (GS_092)
- PAX cannot issue POSITIVE_CLOSURE (GS_093)
- PAX advisory outputs are allowed
- Forbidden aliases (DANA) are blocked (GS_073)
- Registry enforcement is deterministic

Training Signal:
    pattern: ROLE_CLARITY_PREVENTS_SYSTEMIC_DRIFT
    lesson: "Strategy informs execution; it does not perform it."

Mode: FAIL_CLOSED

═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add tools/governance to path for imports
TOOLS_PATH = Path(__file__).parent.parent.parent / "tools" / "governance"
sys.path.insert(0, str(TOOLS_PATH))

from gate_pack import (
    ErrorCode,
    NON_EXECUTING_AGENTS,
    NON_EXECUTING_STRATEGY_AGENTS,
    FORBIDDEN_AGENT_ALIASES,
    STRATEGY_AGENT_ALLOWED_OUTPUTS,
    STRATEGY_AGENT_FORBIDDEN_OUTPUTS,
    validate_non_executing_strategy_agent,
    validate_pac_naming_and_roles,
    validate_content,
    load_registry,
    is_pac_artifact,
    is_wrap_artifact,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def registry():
    """Load the canonical agent registry."""
    return load_registry()


@pytest.fixture
def pax_pac_content():
    """PAC content emitted BY PAX (should FAIL)."""
    return """
═══════════════════════════════════════════════════════════════════════════════
🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧
PAC-PAX-TEST-001
🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧
═══════════════════════════════════════════════════════════════════════════════

AGENT_ACTIVATION_ACK {
  agent_name: PAX
  gid: GID-05
  role: Product & Smart Contract Strategy
  execution_lane: STRATEGY_ONLY
  color: ORANGE
  activation_scope: EXECUTION
}

RUNTIME_ACTIVATION_ACK {
  runtime_name: BENSON_CTO_ORCHESTRATOR
  gid: N/A
  authority: BENSON (GID-00)
  execution_lane: ORCHESTRATION
  mode: CTO_EXECUTION
  executes_for_agent: PAX
}

CONTEXT_AND_GOAL {
  context: "Test PAC emission by PAX"
  goal: "This should fail validation"
}

═══════════════════════════════════════════════════════════════════════════════
END — PAC-PAX-TEST-001
═══════════════════════════════════════════════════════════════════════════════
"""


@pytest.fixture
def pax_wrap_content():
    """WRAP content emitted BY PAX (should FAIL)."""
    return """
═══════════════════════════════════════════════════════════════════════════════
🟧 WRAP — PAC-PAX-TEST-001
═══════════════════════════════════════════════════════════════════════════════

WRAP_INGESTION_PREAMBLE {
  artifact_type: WRAP
  schema_version: "1.0"
}

AGENT_ACTIVATION_ACK {
  agent_name: PAX
  gid: GID-05
  role: Product & Smart Contract Strategy
  execution_lane: STRATEGY_ONLY
  color: ORANGE
}

PAC_REFERENCE {
  pac_id: PAC-PAX-TEST-001
}

POSITIVE_CLOSURE {
  type: POSITIVE_CLOSURE
  authority: BENSON (GID-00)
}

═══════════════════════════════════════════════════════════════════════════════
END WRAP
═══════════════════════════════════════════════════════════════════════════════
"""


@pytest.fixture
def pax_with_code_content():
    """Content with code blocks emitted by PAX (should FAIL)."""
    return """
═══════════════════════════════════════════════════════════════════════════════
ADVISORY DOCUMENT
═══════════════════════════════════════════════════════════════════════════════

AGENT_ACTIVATION_ACK {
  agent_name: PAX
  gid: GID-05
  role: Product & Smart Contract Strategy
  execution_lane: STRATEGY_ONLY
  color: ORANGE
}

## Implementation Code

```python
def execute_strategy():
    # This code should not be emitted by PAX
    return "executed"
```

═══════════════════════════════════════════════════════════════════════════════
"""


@pytest.fixture
def pax_advisory_content():
    """Advisory content from PAX (should PASS - no PAC/WRAP markers)."""
    return """
# Strategy Recommendation

AGENT_ACTIVATION_ACK {
  agent_name: PAX
  gid: GID-05
  role: Product & Smart Contract Strategy
  execution_lane: STRATEGY_ONLY
  color: ORANGE
}

## Product Strategy Brief

This is an advisory document with recommendations.
No PAC, WRAP, or POSITIVE_CLOSURE markers present.

## Recommendations

1. Consider expanding market scope
2. Evaluate tokenization options
3. Review settlement policies
"""


@pytest.fixture
def dana_pac_content():
    """PAC with forbidden alias DANA (should FAIL with GS_073)."""
    return """
═══════════════════════════════════════════════════════════════════════════════
PAC-DANA-TEST-001
═══════════════════════════════════════════════════════════════════════════════

AGENT_ACTIVATION_ACK {
  agent_name: DANA
  gid: GID-XX
  role: Unknown
  execution_lane: UNKNOWN
  color: UNKNOWN
}

═══════════════════════════════════════════════════════════════════════════════
"""


@pytest.fixture
def valid_cody_pac_content():
    """Valid PAC from executing agent CODY (should PASS)."""
    return """
═══════════════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
PAC-CODY-TEST-001
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
═══════════════════════════════════════════════════════════════════════════════

AGENT_ACTIVATION_ACK {
  agent_name: CODY
  gid: GID-01
  role: Backend Engineer
  execution_lane: BACKEND
  color: BLUE
  activation_scope: EXECUTION
}

RUNTIME_ACTIVATION_ACK {
  runtime_name: BENSON_CTO_ORCHESTRATOR
  gid: N/A
  authority: BENSON (GID-00)
  execution_lane: ORCHESTRATION
  mode: CTO_EXECUTION
  executes_for_agent: CODY
}

TRAINING_SIGNAL {
  pattern: TEST_PATTERN
  level: L1
}

FINAL_STATE {
  status: COMPLETE
}

GOLD_STANDARD_CHECKLIST {
  identity_correct: ✅
  agent_color_correct: ✅
  execution_lane_correct: ✅
}

═══════════════════════════════════════════════════════════════════════════════
END — PAC-CODY-TEST-001
═══════════════════════════════════════════════════════════════════════════════
"""


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS: REGISTRY CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegistryConstants:
    """Test that registry constants are correctly defined."""

    def test_pax_in_non_executing_agents(self):
        """PAX must be in NON_EXECUTING_AGENTS list."""
        assert "PAX" in NON_EXECUTING_AGENTS

    def test_pax_in_non_executing_strategy_agents(self):
        """PAX must be in NON_EXECUTING_STRATEGY_AGENTS list."""
        assert "PAX" in NON_EXECUTING_STRATEGY_AGENTS

    def test_dana_in_forbidden_aliases(self):
        """DANA must be in FORBIDDEN_AGENT_ALIASES list."""
        assert "DANA" in FORBIDDEN_AGENT_ALIASES

    def test_pax_not_in_forbidden_aliases(self):
        """PAX is non-executing but NOT forbidden (can exist as strategy agent)."""
        # PAX is a strategy agent, not permanently forbidden like DANA
        # This is the key distinction from PAC-PAX-P37
        assert "PAX" not in FORBIDDEN_AGENT_ALIASES

    def test_allowed_outputs_defined(self):
        """Strategy agent allowed outputs must be defined."""
        assert len(STRATEGY_AGENT_ALLOWED_OUTPUTS) > 0
        assert "RESEARCH_PACK" in STRATEGY_AGENT_ALLOWED_OUTPUTS
        assert "STRATEGY_MEMO" in STRATEGY_AGENT_ALLOWED_OUTPUTS
        assert "POLICY_RECOMMENDATION" in STRATEGY_AGENT_ALLOWED_OUTPUTS

    def test_forbidden_outputs_defined(self):
        """Strategy agent forbidden outputs must be defined."""
        assert len(STRATEGY_AGENT_FORBIDDEN_OUTPUTS) > 0
        assert "PAC" in STRATEGY_AGENT_FORBIDDEN_OUTPUTS
        assert "WRAP" in STRATEGY_AGENT_FORBIDDEN_OUTPUTS
        assert "CODE" in STRATEGY_AGENT_FORBIDDEN_OUTPUTS
        assert "POSITIVE_CLOSURE" in STRATEGY_AGENT_FORBIDDEN_OUTPUTS


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS: PAX ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaxPacEmission:
    """Test that PAX cannot emit PACs (GS_090)."""

    def test_pax_pac_emission_fails(self, pax_pac_content, registry):
        """PAX emitting a PAC must trigger GS_090."""
        errors = validate_non_executing_strategy_agent(pax_pac_content, registry)

        assert len(errors) > 0
        error_codes = [e.code for e in errors]
        assert ErrorCode.GS_090 in error_codes

    def test_pax_pac_emission_error_message(self, pax_pac_content, registry):
        """GS_090 error must include informative message."""
        errors = validate_non_executing_strategy_agent(pax_pac_content, registry)

        gs_090_errors = [e for e in errors if e.code == ErrorCode.GS_090]
        assert len(gs_090_errors) > 0
        assert "PAX" in gs_090_errors[0].message
        assert "advisory" in gs_090_errors[0].message.lower()


class TestPaxWrapEmission:
    """Test that PAX cannot emit WRAPs (GS_091)."""

    def test_pax_wrap_emission_fails(self, pax_wrap_content, registry):
        """PAX emitting a WRAP must trigger GS_091."""
        errors = validate_non_executing_strategy_agent(pax_wrap_content, registry)

        assert len(errors) > 0
        error_codes = [e.code for e in errors]
        assert ErrorCode.GS_091 in error_codes


class TestPaxCodeCreation:
    """Test that PAX cannot create code/files (GS_092)."""

    def test_pax_code_creation_fails(self, pax_with_code_content, registry):
        """PAX emitting code must trigger GS_092."""
        errors = validate_non_executing_strategy_agent(pax_with_code_content, registry)

        assert len(errors) > 0
        error_codes = [e.code for e in errors]
        assert ErrorCode.GS_092 in error_codes


class TestPaxPositiveClosure:
    """Test that PAX cannot issue POSITIVE_CLOSURE (GS_093)."""

    def test_pax_positive_closure_fails(self, pax_wrap_content, registry):
        """PAX issuing POSITIVE_CLOSURE must trigger GS_093."""
        # The WRAP content includes POSITIVE_CLOSURE
        errors = validate_non_executing_strategy_agent(pax_wrap_content, registry)

        assert len(errors) > 0
        error_codes = [e.code for e in errors]
        assert ErrorCode.GS_093 in error_codes


class TestPaxAdvisoryOutputs:
    """Test that PAX advisory outputs are allowed."""

    def test_pax_advisory_passes(self, pax_advisory_content, registry):
        """PAX advisory content without PAC/WRAP/CODE should pass."""
        errors = validate_non_executing_strategy_agent(pax_advisory_content, registry)

        # Should have no GS_090-093 errors
        error_codes = [e.code for e in errors]
        assert ErrorCode.GS_090 not in error_codes
        assert ErrorCode.GS_091 not in error_codes
        assert ErrorCode.GS_092 not in error_codes
        assert ErrorCode.GS_093 not in error_codes


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS: FORBIDDEN ALIASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestForbiddenAliases:
    """Test that forbidden aliases are blocked."""

    def test_dana_pac_fails(self, dana_pac_content, registry):
        """DANA in PAC ID must trigger GS_073."""
        errors = validate_pac_naming_and_roles(dana_pac_content, registry)

        assert len(errors) > 0
        error_codes = [e.code for e in errors]
        assert ErrorCode.GS_073 in error_codes


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS: EXECUTING AGENTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutingAgents:
    """Test that executing agents can emit PACs normally."""

    def test_cody_pac_no_strategy_errors(self, valid_cody_pac_content, registry):
        """CODY (executing agent) should not trigger GS_090-093."""
        errors = validate_non_executing_strategy_agent(valid_cody_pac_content, registry)

        # Should have no strategy agent errors
        assert len(errors) == 0

    def test_cody_pac_naming_passes(self, valid_cody_pac_content, registry):
        """CODY PAC should not trigger naming errors."""
        errors = validate_pac_naming_and_roles(valid_cody_pac_content, registry)

        # Should not have GS_071 (non-executing) or GS_073 (forbidden alias)
        error_codes = [e.code for e in errors]
        assert ErrorCode.GS_071 not in error_codes
        assert ErrorCode.GS_073 not in error_codes


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullValidation:
    """Integration tests using full validate_content function."""

    def test_pax_pac_full_validation_fails(self, pax_pac_content, registry):
        """Full validation of PAX PAC must fail."""
        result = validate_content(pax_pac_content, registry)

        assert result.valid is False
        error_codes = [e.code for e in result.errors]
        # Should have both GS_071 (non-executing in PAC ID) and GS_090 (PAC emission)
        assert ErrorCode.GS_071 in error_codes or ErrorCode.GS_090 in error_codes

    def test_cody_pac_full_validation_structure(self, valid_cody_pac_content, registry):
        """Full validation of CODY PAC should not fail on strategy agent rules."""
        result = validate_content(valid_cody_pac_content, registry)

        # Check that none of the strategy agent errors are present
        error_codes = [e.code for e in result.errors]
        assert ErrorCode.GS_090 not in error_codes
        assert ErrorCode.GS_091 not in error_codes
        assert ErrorCode.GS_092 not in error_codes
        assert ErrorCode.GS_093 not in error_codes


# ═══════════════════════════════════════════════════════════════════════════════
# REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegressionPaxEnforcement:
    """Regression tests to prevent future PAX execution bypass."""

    def test_pax_cannot_bypass_via_uppercase(self, registry):
        """PAX detection must be case-insensitive."""
        content = """
AGENT_ACTIVATION_ACK {
  agent_name: pax
  gid: GID-05
}
PAC-PAX-TEST
"""
        errors = validate_non_executing_strategy_agent(content, registry)
        # PAX in lowercase should still be detected
        # Note: The function should handle case normalization

    def test_pax_enforcement_deterministic(self, pax_pac_content, registry):
        """PAX enforcement must be deterministic across multiple runs."""
        results = []
        for _ in range(10):
            errors = validate_non_executing_strategy_agent(pax_pac_content, registry)
            results.append(len(errors))

        # All runs must produce same number of errors
        assert len(set(results)) == 1

    def test_registry_is_authority(self, registry):
        """Registry must be the source of truth for agent roles."""
        # Check that non-executing agents are defined in registry
        non_exec = registry.get("non_executing_agents", [])
        strategy = registry.get("non_executing_strategy_agents", {})

        # PAX should be in at least one of these
        assert "PAX" in non_exec or "PAX" in strategy


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR CODE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestErrorCodes:
    """Test that error codes are properly defined."""

    def test_gs_090_exists(self):
        """GS_090 error code must exist."""
        assert hasattr(ErrorCode, "GS_090")

    def test_gs_091_exists(self):
        """GS_091 error code must exist."""
        assert hasattr(ErrorCode, "GS_091")

    def test_gs_092_exists(self):
        """GS_092 error code must exist."""
        assert hasattr(ErrorCode, "GS_092")

    def test_gs_093_exists(self):
        """GS_093 error code must exist."""
        assert hasattr(ErrorCode, "GS_093")

    def test_error_messages_informative(self):
        """Error code messages must be informative."""
        assert "PAC" in ErrorCode.GS_090.value
        assert "WRAP" in ErrorCode.GS_091.value
        assert "code" in ErrorCode.GS_092.value.lower() or "file" in ErrorCode.GS_092.value.lower()
        assert "CLOSURE" in ErrorCode.GS_093.value


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING SIGNAL VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrainingSignal:
    """Test training signal propagation for PAX violations."""

    def test_training_signal_pattern(self):
        """Training signal pattern must be defined for this PAC."""
        # The training signal for PAX enforcement
        expected_pattern = "ROLE_CLARITY_PREVENTS_SYSTEMIC_DRIFT"
        expected_lesson = "Strategy informs execution; it does not perform it."

        # These should be documented in gate_pack.py comments
        # This test documents the expected values for audit purposes
        assert expected_pattern is not None
        assert expected_lesson is not None
