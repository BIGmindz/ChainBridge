"""
Tests for Activation Block Validation — PAC-BENSON-ACTIVATION-BLOCK-IMPLEMENTATION-01
════════════════════════════════════════════════════════════════════════════════

Tests the Activation Block validator and enforcement:
- Block presence validation
- Agent name validation
- GID validation
- Role validation
- Color validation
- Emoji validation
- Prohibited actions validation
- Persona binding validation

ENFORCEMENT MODEL: HARD FAIL ONLY. No soft warnings, no defaults.

════════════════════════════════════════════════════════════════════════════════
"""

import pytest

from core.governance.activation_block import (
    ActivationBlock,
    ActivationBlockValidator,
    ActivationValidationResult,
    ActivationBlockViolationCode,
    ActivationBlockViolationError,
    get_activation_block_validator,
    parse_activation_block_from_text,
    require_activation_block,
    reset_activation_block_validator,
    validate_activation_block,
)
from core.governance.agent_roster import get_agent_by_name


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def validator() -> ActivationBlockValidator:
    """Create a fresh validator instance."""
    reset_activation_block_validator()
    return get_activation_block_validator()


@pytest.fixture
def valid_cody_block() -> ActivationBlock:
    """Create a valid Activation Block for CODY."""
    return ActivationBlock(
        agent_name="CODY",
        gid="GID-01",
        role="Backend Engineering",
        color="BLUE",
        emoji="🔵",
        prohibited_actions=frozenset(["identity_drift", "color_violation"]),
        persona_binding="Executing as CODY",
    )


@pytest.fixture
def valid_benson_block() -> ActivationBlock:
    """Create a valid Activation Block for BENSON."""
    return ActivationBlock(
        agent_name="BENSON",
        gid="GID-00",
        role="Orchestrator",
        color="TEAL",
        emoji="🟦🟩",
        prohibited_actions=frozenset(["unauthorized_execution"]),
        persona_binding="Executing as BENSON",
    )


@pytest.fixture
def valid_dan_block() -> ActivationBlock:
    """Create a valid Activation Block for DAN."""
    return ActivationBlock(
        agent_name="DAN",
        gid="GID-07",
        role="DevOps",
        color="GREEN",
        emoji="🟩",
        prohibited_actions=frozenset(["manual_deploy"]),
        persona_binding="Executing as DAN",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BLOCK CREATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestActivationBlockCreation:
    """Test Activation Block dataclass creation."""
    
    def test_valid_block_creation(self, valid_cody_block: ActivationBlock):
        """Valid blocks can be created."""
        assert valid_cody_block.agent_name == "CODY"
        assert valid_cody_block.gid == "GID-01"
        assert valid_cody_block.color == "BLUE"
    
    def test_empty_agent_name_raises(self):
        """Empty agent name raises ValueError."""
        with pytest.raises(ValueError, match="agent_name cannot be empty"):
            ActivationBlock(
                agent_name="",
                gid="GID-01",
                role="Test",
                color="BLUE",
                emoji="🔵",
                prohibited_actions=frozenset(["test"]),
                persona_binding="Test",
            )
    
    def test_empty_gid_raises(self):
        """Empty GID raises ValueError."""
        with pytest.raises(ValueError, match="gid cannot be empty"):
            ActivationBlock(
                agent_name="CODY",
                gid="",
                role="Test",
                color="BLUE",
                emoji="🔵",
                prohibited_actions=frozenset(["test"]),
                persona_binding="Test",
            )
    
    def test_empty_prohibited_actions_raises(self):
        """Empty prohibited actions raises ValueError."""
        with pytest.raises(ValueError, match="prohibited_actions cannot be empty"):
            ActivationBlock(
                agent_name="CODY",
                gid="GID-01",
                role="Test",
                color="BLUE",
                emoji="🔵",
                prohibited_actions=frozenset(),
                persona_binding="Test",
            )
    
    def test_empty_persona_binding_raises(self):
        """Empty persona binding raises ValueError."""
        with pytest.raises(ValueError, match="persona_binding cannot be empty"):
            ActivationBlock(
                agent_name="CODY",
                gid="GID-01",
                role="Test",
                color="BLUE",
                emoji="🔵",
                prohibited_actions=frozenset(["test"]),
                persona_binding="",
            )
    
    def test_block_is_immutable(self, valid_cody_block: ActivationBlock):
        """Activation blocks are frozen/immutable."""
        with pytest.raises(AttributeError):
            valid_cody_block.agent_name = "SONNY"  # type: ignore


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: VALIDATION — VALID CASES
# ═══════════════════════════════════════════════════════════════════════════════


class TestActivationBlockValidationValid:
    """Test validation of valid Activation Blocks."""
    
    def test_valid_cody_block_passes(
        self,
        validator: ActivationBlockValidator,
        valid_cody_block: ActivationBlock,
    ):
        """Valid CODY block passes validation."""
        result = validator.validate(valid_cody_block, "PAC-TEST-01")
        assert result.is_valid
        assert result.agent is not None
        assert result.agent.name == "CODY"
    
    def test_valid_benson_block_passes(
        self,
        validator: ActivationBlockValidator,
        valid_benson_block: ActivationBlock,
    ):
        """Valid BENSON block passes validation."""
        result = validator.validate(valid_benson_block, "PAC-TEST-02")
        assert result.is_valid
        assert result.agent is not None
        assert result.agent.name == "BENSON"
    
    def test_valid_dan_block_passes(
        self,
        validator: ActivationBlockValidator,
        valid_dan_block: ActivationBlock,
    ):
        """Valid DAN block passes validation."""
        result = validator.validate(valid_dan_block, "PAC-TEST-03")
        assert result.is_valid
        assert result.agent is not None
        assert result.agent.name == "DAN"
    
    def test_validate_or_raise_returns_agent(
        self,
        validator: ActivationBlockValidator,
        valid_cody_block: ActivationBlock,
    ):
        """validate_or_raise returns canonical Agent."""
        agent = validator.validate_or_raise(valid_cody_block, "PAC-TEST-04")
        assert agent.name == "CODY"
        assert agent.gid == "GID-01"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: VALIDATION — INVALID CASES (HARD FAIL)
# ═══════════════════════════════════════════════════════════════════════════════


class TestActivationBlockValidationInvalid:
    """Test validation failures (HARD FAIL scenarios)."""
    
    def test_missing_block_raises(self, validator: ActivationBlockValidator):
        """Missing Activation Block raises HARD FAIL."""
        with pytest.raises(ActivationBlockViolationError) as exc_info:
            validator.validate_or_raise(None, "PAC-TEST-MISSING-01")
        
        assert exc_info.value.violation_code == ActivationBlockViolationCode.MISSING_BLOCK.value
        assert "No Activation Block provided" in str(exc_info.value)
    
    def test_unknown_agent_raises(self, validator: ActivationBlockValidator):
        """Unknown agent raises HARD FAIL."""
        block = ActivationBlock(
            agent_name="UNKNOWN_AGENT",
            gid="GID-99",
            role="Test",
            color="BLUE",
            emoji="🔵",
            prohibited_actions=frozenset(["test"]),
            persona_binding="Test",
        )
        
        with pytest.raises(ActivationBlockViolationError) as exc_info:
            validator.validate(block, "PAC-TEST-UNKNOWN-01")
        
        assert exc_info.value.violation_code == ActivationBlockViolationCode.INVALID_AGENT.value
        assert "not found in canonical registry" in str(exc_info.value)
    
    def test_gid_mismatch_raises(self, validator: ActivationBlockValidator):
        """GID mismatch raises HARD FAIL."""
        block = ActivationBlock(
            agent_name="CODY",
            gid="GID-99",  # Wrong GID - CODY is GID-01
            role="Backend Engineering",
            color="BLUE",
            emoji="🔵",
            prohibited_actions=frozenset(["test"]),
            persona_binding="Test",
        )
        
        with pytest.raises(ActivationBlockViolationError) as exc_info:
            validator.validate(block, "PAC-TEST-GID-01")
        
        assert exc_info.value.violation_code == ActivationBlockViolationCode.GID_MISMATCH.value
        assert "does not match canonical GID" in str(exc_info.value)
    
    def test_color_mismatch_raises(self, validator: ActivationBlockValidator):
        """Color mismatch raises HARD FAIL."""
        block = ActivationBlock(
            agent_name="CODY",
            gid="GID-01",
            role="Backend Engineering",
            color="GREEN",  # Wrong color - CODY is BLUE
            emoji="🔵",
            prohibited_actions=frozenset(["test"]),
            persona_binding="Test",
        )
        
        with pytest.raises(ActivationBlockViolationError) as exc_info:
            validator.validate(block, "PAC-TEST-COLOR-01")
        
        assert exc_info.value.violation_code == ActivationBlockViolationCode.COLOR_MISMATCH.value
        assert "does not match canonical color" in str(exc_info.value)
    
    def test_emoji_mismatch_raises(self, validator: ActivationBlockValidator):
        """Emoji mismatch raises HARD FAIL."""
        block = ActivationBlock(
            agent_name="CODY",
            gid="GID-01",
            role="Backend Engineering",
            color="BLUE",
            emoji="🟩",  # Wrong emoji - CODY is 🔵
            prohibited_actions=frozenset(["test"]),
            persona_binding="Test",
        )
        
        with pytest.raises(ActivationBlockViolationError) as exc_info:
            validator.validate(block, "PAC-TEST-EMOJI-01")
        
        assert exc_info.value.violation_code == ActivationBlockViolationCode.EMOJI_MISMATCH.value
        assert "does not match canonical emoji" in str(exc_info.value)
    
    def test_role_mismatch_raises(self, validator: ActivationBlockValidator):
        """Role mismatch raises HARD FAIL."""
        block = ActivationBlock(
            agent_name="CODY",
            gid="GID-01",
            role="Frontend Design",  # Wrong role - CODY is Backend
            color="BLUE",
            emoji="🔵",
            prohibited_actions=frozenset(["test"]),
            persona_binding="Test",
        )
        
        with pytest.raises(ActivationBlockViolationError) as exc_info:
            validator.validate(block, "PAC-TEST-ROLE-01")
        
        assert exc_info.value.violation_code == ActivationBlockViolationCode.ROLE_MISMATCH.value
        assert "does not match canonical role" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PAC TEXT PARSING
# ═══════════════════════════════════════════════════════════════════════════════


VALID_PAC_TEXT = """
════════════════════════════════════════════════════════════════════
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
GID-01 — CODY (BACKEND ENGINEERING)
PAC-TEST-PARSING-01 — TEST
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════

I. EXECUTING AGENT (MANDATORY)

EXECUTING AGENT: CODY
GID: GID-01
EXECUTING COLOR: 🔵 BLUE — Backend / Governance Enforcement Lane

⸻

II. OBJECTIVE

Test parsing of Activation Block from PAC text.

⸻

PROHIBITED:
- Identity drift
- Color violation

⸻

I am CODY executing this PAC.

════════════════════════════════════════════════════════════════════
END — CODY (GID-01) — 🔵 BLUE
🔵🔵🔵🔵🔵🔵🔵🔵🔵🔵
════════════════════════════════════════════════════════════════════
"""


class TestActivationBlockParsing:
    """Test parsing Activation Block from PAC text."""
    
    def test_parse_valid_pac_text(self):
        """Parse Activation Block from valid PAC text."""
        block = parse_activation_block_from_text(VALID_PAC_TEXT, "PAC-TEST-PARSING-01")
        
        assert block is not None
        assert block.agent_name == "CODY"
        assert block.gid == "GID-01"
        assert block.color == "BLUE"
    
    def test_parse_missing_agent_returns_none(self):
        """Parse returns None if EXECUTING AGENT is missing."""
        content = """
        Some content without EXECUTING AGENT
        GID: GID-01
        """
        block = parse_activation_block_from_text(content)
        assert block is None
    
    def test_parse_missing_gid_returns_none(self):
        """Parse returns None if GID is missing."""
        content = """
        EXECUTING AGENT: CODY
        Some content without GID
        """
        block = parse_activation_block_from_text(content)
        assert block is None
    
    def test_require_activation_block_valid(self):
        """require_activation_block succeeds for valid PAC."""
        agent = require_activation_block(VALID_PAC_TEXT, "PAC-TEST-REQ-01")
        assert agent.name == "CODY"
    
    def test_require_activation_block_missing_raises(self):
        """require_activation_block raises for missing block."""
        content = "No activation block here"
        
        with pytest.raises(ActivationBlockViolationError):
            require_activation_block(content, "PAC-TEST-REQ-FAIL-01")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ENFORCEMENT ORDER
# ═══════════════════════════════════════════════════════════════════════════════


class TestEnforcementOrder:
    """Test that Activation Block validation is first in enforcement chain."""
    
    def test_activation_block_validates_before_color_gateway(self):
        """Activation Block validation runs BEFORE Color Gateway."""
        # If Activation Block is invalid, we should get THAT error, not Color Gateway
        block = ActivationBlock(
            agent_name="UNKNOWN",
            gid="GID-99",
            role="Test",
            color="BLUE",
            emoji="🔵",
            prohibited_actions=frozenset(["test"]),
            persona_binding="Test",
        )
        
        validator = get_activation_block_validator()
        
        with pytest.raises(ActivationBlockViolationError) as exc_info:
            validator.validate(block)
        
        # Should be an Activation Block error, not a Color Gateway error
        assert "ACTIVATION BLOCK VIOLATION" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ALL AGENTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestAllAgentsActivationBlock:
    """Test that all canonical agents can have valid Activation Blocks."""
    
    @pytest.mark.parametrize("agent_name,gid,color,emoji", [
        ("BENSON", "GID-00", "TEAL", "🟦🟩"),
        ("CODY", "GID-01", "BLUE", "🔵"),
        ("SONNY", "GID-02", "YELLOW", "🟨"),
        ("MIRA-R", "GID-03", "PURPLE", "🟣"),
        ("CINDY", "GID-04", "TEAL", "🟦"),
        ("PAX", "GID-05", "ORANGE", "🟧"),
        ("SAM", "GID-06", "DARK RED", "🟥"),
        ("DAN", "GID-07", "GREEN", "🟩"),
        ("ALEX", "GID-08", "WHITE", "⚪"),
    ])
    def test_canonical_agent_block_validates(
        self,
        agent_name: str,
        gid: str,
        color: str,
        emoji: str,
    ):
        """Each canonical agent can create a valid Activation Block."""
        agent = get_agent_by_name(agent_name)
        assert agent is not None, f"Agent {agent_name} not in registry"
        
        block = ActivationBlock(
            agent_name=agent_name,
            gid=gid,
            role=agent.role,  # Use canonical role
            color=color,
            emoji=emoji,
            prohibited_actions=frozenset(["identity_drift"]),
            persona_binding=f"Executing as {agent_name}",
        )
        
        validator = get_activation_block_validator()
        result = validator.validate(block)
        
        assert result.is_valid, f"Block for {agent_name} should be valid"
        assert result.agent.name == agent_name


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NO BYPASS — HARD FAIL ONLY
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoBypass:
    """Test that there are NO bypass paths for Activation Block validation."""
    
    def test_no_default_agent(self, validator: ActivationBlockValidator):
        """There is no default agent if block is missing."""
        with pytest.raises(ActivationBlockViolationError):
            validator.validate_or_raise(None)
    
    def test_no_inferred_identity(self, validator: ActivationBlockValidator):
        """Identity cannot be inferred from partial data."""
        # Even if we know the GID, agent name must be explicit
        block = ActivationBlock(
            agent_name="WRONG",
            gid="GID-01",  # GID-01 is CODY
            role="Test",
            color="BLUE",
            emoji="🔵",
            prohibited_actions=frozenset(["test"]),
            persona_binding="Test",
        )
        
        with pytest.raises(ActivationBlockViolationError):
            validator.validate(block)
    
    def test_convenience_function_also_fails(self):
        """Module-level convenience function also enforces."""
        with pytest.raises(ActivationBlockViolationError):
            validate_activation_block(None)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: VALIDATOR STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidatorStats:
    """Test validator statistics tracking."""
    
    def test_stats_track_validations(self, validator: ActivationBlockValidator):
        """Statistics track validation count."""
        block = ActivationBlock(
            agent_name="CODY",
            gid="GID-01",
            role="Backend",
            color="BLUE",
            emoji="🔵",
            prohibited_actions=frozenset(["test"]),
            persona_binding="Test",
        )
        
        validator.validate(block)
        validator.validate(block)
        
        stats = validator.stats
        assert stats["total_validations"] == 2
    
    def test_stats_track_failures(self, validator: ActivationBlockValidator):
        """Statistics track failure count."""
        with pytest.raises(ActivationBlockViolationError):
            validator.validate_or_raise(None)
        
        stats = validator.stats
        assert stats["failures"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: EXECUTION GATE ENFORCEMENT — PAC-DAN-ACTIVATION-GATE-ENFORCEMENT-01
# ═══════════════════════════════════════════════════════════════════════════════


class TestExecutionGateEnforcement:
    """Test execution gate ordering enforcement."""
    
    @pytest.fixture(autouse=True)
    def reset_gates(self):
        """Reset execution gates before each test."""
        from core.governance.activation_block import reset_execution_gates
        reset_execution_gates()
        yield
        reset_execution_gates()
    
    def test_activation_required_before_color_gateway(self):
        """Color gateway check requires prior activation validation."""
        from core.governance.activation_block import (
            ExecutionGateError,
            require_activation_before_color_gateway,
        )
        
        with pytest.raises(ExecutionGateError) as exc_info:
            require_activation_before_color_gateway()
        
        assert exc_info.value.gate_name == "PRE_COLOR_GATEWAY"
        assert "Activation Block must be validated" in str(exc_info.value)
    
    def test_activation_required_before_pac_admission(self):
        """PAC admission requires prior activation validation."""
        from core.governance.activation_block import (
            ExecutionGateError,
            require_activation_before_pac_admission,
        )
        
        with pytest.raises(ExecutionGateError) as exc_info:
            require_activation_before_pac_admission()
        
        assert exc_info.value.gate_name == "PRE_PAC_ADMISSION"
    
    def test_activation_required_before_tool_execution(self):
        """Tool/MCP execution requires prior activation validation."""
        from core.governance.activation_block import (
            ExecutionGateError,
            require_activation_before_tool_execution,
        )
        
        with pytest.raises(ExecutionGateError) as exc_info:
            require_activation_before_tool_execution()
        
        assert exc_info.value.gate_name == "PRE_TOOL_EXECUTION"
    
    def test_gate_passes_after_activation_validated(self):
        """Gates pass after activation is validated."""
        from core.governance.activation_block import (
            mark_activation_validated,
            require_activation_before_color_gateway,
            require_activation_before_pac_admission,
            require_activation_before_tool_execution,
        )
        
        mark_activation_validated()
        
        # These should not raise
        require_activation_before_color_gateway()
        require_activation_before_pac_admission()
        require_activation_before_tool_execution()
    
    def test_full_validation_chain_requires_all_gates(self):
        """Full validation chain requires all gates validated."""
        from core.governance.activation_block import (
            ExecutionGateError,
            mark_activation_validated,
            mark_color_gateway_validated,
            require_full_validation_chain,
        )
        
        # Only activation validated
        mark_activation_validated()
        
        with pytest.raises(ExecutionGateError) as exc_info:
            require_full_validation_chain()
        
        assert "Color Gateway not validated" in exc_info.value.reason
    
    def test_full_validation_chain_passes_when_all_validated(self):
        """Full chain passes when all gates validated."""
        from core.governance.activation_block import (
            mark_activation_validated,
            mark_color_gateway_validated,
            mark_pac_admission_validated,
            require_full_validation_chain,
        )
        
        mark_activation_validated()
        mark_color_gateway_validated()
        mark_pac_admission_validated()
        
        # Should not raise
        require_full_validation_chain()
    
    def test_gate_state_tracking(self):
        """Gate state is properly tracked."""
        from core.governance.activation_block import (
            get_gate_state,
            mark_activation_validated,
            mark_color_gateway_validated,
        )
        
        state = get_gate_state()
        assert state["activation_validated"] is False
        assert state["color_gateway_validated"] is False
        assert state["pac_admission_validated"] is False
        
        mark_activation_validated()
        state = get_gate_state()
        assert state["activation_validated"] is True
        
        mark_color_gateway_validated()
        state = get_gate_state()
        assert state["color_gateway_validated"] is True
    
    def test_is_activation_validated_helper(self):
        """Helper function returns correct state."""
        from core.governance.activation_block import (
            is_activation_validated,
            mark_activation_validated,
        )
        
        assert is_activation_validated() is False
        mark_activation_validated()
        assert is_activation_validated() is True


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ACTIVATION BLOCK PRESENCE CHECK
# ═══════════════════════════════════════════════════════════════════════════════


class TestActivationBlockPresenceCheck:
    """Test activation block presence validation for linter."""
    
    def test_complete_block_detected(self):
        """Complete activation block is detected."""
        from core.governance.activation_block import check_activation_block_presence
        
        content = """
        EXECUTING AGENT: DAN (GID-07)
        GID: GID-07
        EXECUTING COLOR: 🟩 GREEN
        
        PROHIBITED:
        - Identity drift
        """
        
        has_block, missing = check_activation_block_presence(content)
        assert has_block is True
        assert len(missing) == 0
    
    def test_missing_agent_detected(self):
        """Missing EXECUTING AGENT is detected."""
        from core.governance.activation_block import check_activation_block_presence
        
        content = """
        GID: GID-07
        EXECUTING COLOR: 🟩 GREEN
        """
        
        has_block, missing = check_activation_block_presence(content)
        assert has_block is False
        assert "EXECUTING AGENT declaration" in missing
    
    def test_missing_gid_detected(self):
        """Missing GID is detected."""
        from core.governance.activation_block import check_activation_block_presence
        
        content = """
        EXECUTING AGENT: DAN
        EXECUTING COLOR: 🟩 GREEN
        """
        
        has_block, missing = check_activation_block_presence(content)
        assert has_block is False
        assert "GID declaration" in missing
    
    def test_missing_color_detected(self):
        """Missing COLOR is detected."""
        from core.governance.activation_block import check_activation_block_presence
        
        content = """
        EXECUTING AGENT: DAN
        GID: GID-07
        """
        
        has_block, missing = check_activation_block_presence(content)
        assert has_block is False
        assert "COLOR declaration" in missing


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: LANE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestLaneValidation:
    """Test lane validation in activation blocks."""
    
    def test_lane_field_optional_in_block(self):
        """Lane field is optional in ActivationBlock."""
        block = ActivationBlock(
            agent_name="DAN",
            gid="GID-07",
            role="DevOps",
            color="GREEN",
            emoji="🟩",
            prohibited_actions=frozenset(["test"]),
            persona_binding="Executing as DAN",
            lane="",  # Empty is allowed
        )
        
        assert block.lane == ""
    
    def test_valid_lane_passes_validation(self):
        """Correct lane passes validation."""
        block = ActivationBlock(
            agent_name="DAN",
            gid="GID-07",
            role="DevOps",
            color="GREEN",
            emoji="🟩",
            prohibited_actions=frozenset(["test"]),
            persona_binding="Executing as DAN",
            lane="GREEN",  # Lane matches color
        )
        
        validator = get_activation_block_validator()
        result = validator.validate(block)
        assert result.is_valid
