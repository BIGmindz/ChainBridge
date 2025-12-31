"""
Unit Tests for ChainBridge Identity & Mode Law Enforcement
════════════════════════════════════════════════════════════════════════════════

Tests all enforcement paths:
- Unknown GID rejection
- Invalid MODE rejection
- Tool stripping correctness
- WRAP schema failure paths
- Echo-back handshake validation

PAC Reference: PAC-BENSON-CTO-EXEC-CODY-IDENTITY-MODE-LAW-011
Effective Date: 2025-12-26

════════════════════════════════════════════════════════════════════════════════
"""

import pytest
from datetime import datetime, timezone

# Import enforcement modules
from core.governance.gid_registry import (
    GID,
    Mode,
    AgentIdentity,
    GIDRegistry,
    GIDEnforcementError,
    UnknownGIDError,
    InvalidGIDFormatError,
    ModeNotPermittedError,
    LaneNotPermittedError,
    PACAuthorityError,
    format_echo_handshake,
    validate_echo_handshake,
    validate_agent_gid,
    validate_agent_mode,
    validate_agent_lane,
    validate_full_identity,
)
from core.governance.mode_schema import (
    ModeDeclaration,
    ModeSchemaError,
    MissingFieldError,
    MalformedFieldError,
    RoleMismatchError,
    ModeSchemaValidator,
    validate_mode_declaration,
    create_mode_declaration,
)
from core.governance.tool_matrix import (
    ToolCategory,
    ToolMatrix,
    ToolMatrixResult,
    evaluate_tools,
    strip_disallowed_tools,
    is_tool_permitted,
    is_path_permitted,
)
from core.governance.wrap_validator import (
    WRAPValidationError,
    WRAPMissingBlockError,
    WRAPMalformedBlockError,
    validate_wrap,
    is_wrap_valid,
    check_ber_eligibility,
)
from core.governance.enforcement import (
    Enforcer,
    EnforcementContext,
    EnforcementError,
    EnforcementChainError,
    ToolDeniedError,
    PathDeniedError,
    EchoHandshakeError,
    enforce,
    get_current_context,
    require_context,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GID REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestGIDRegistry:
    """Tests for GID registry validation."""
    
    def test_valid_gid_accepted(self):
        """Valid GIDs are accepted."""
        agent = validate_agent_gid("GID-00")
        assert agent.gid == "GID-00"
        assert agent.name == "BENSON"
    
    def test_unknown_gid_rejected(self):
        """Unknown GIDs are HARD FAIL."""
        with pytest.raises(UnknownGIDError) as exc_info:
            validate_agent_gid("GID-99")
        
        assert "GID-99" in str(exc_info.value)
        assert "HARD FAIL" in str(exc_info.value)
    
    def test_invalid_gid_format_rejected(self):
        """Invalid GID format is HARD FAIL."""
        with pytest.raises(InvalidGIDFormatError):
            validate_agent_gid("INVALID")
        
        with pytest.raises(InvalidGIDFormatError):
            validate_agent_gid("GID-ABC")
        
        with pytest.raises(InvalidGIDFormatError):
            validate_agent_gid("gid-01")  # lowercase
    
    def test_all_registered_gids(self):
        """All registered GIDs are valid."""
        registry = GIDRegistry()
        
        for gid in [
            "GID-00", "GID-01", "GID-02", "GID-03", "GID-04",
            "GID-05", "GID-06", "GID-07", "GID-08", "GID-09",
            "GID-10", "GID-11", "GID-12",
        ]:
            agent = registry.get_agent(gid)
            assert agent is not None
            assert agent.gid == gid


class TestModeValidation:
    """Tests for mode validation."""
    
    def test_permitted_mode_accepted(self):
        """Permitted modes are accepted."""
        agent = validate_agent_gid("GID-01")  # CODY
        agent.validate_mode("EXECUTION")  # Should not raise
    
    def test_non_permitted_mode_rejected(self):
        """Non-permitted modes are HARD FAIL."""
        agent = validate_agent_gid("GID-01")  # CODY
        
        with pytest.raises(ModeNotPermittedError) as exc_info:
            agent.validate_mode("ORCHESTRATION")  # Not in CODY's modes
        
        assert "ORCHESTRATION" in str(exc_info.value)
        assert "HARD FAIL" in str(exc_info.value)
    
    def test_benson_has_all_modes(self):
        """BENSON (GID-00) can use permitted modes."""
        agent = validate_agent_gid("GID-00")
        
        # BENSON's permitted modes per gid_registry.json
        for mode in ["ORCHESTRATION", "SYNTHESIS", "REVIEW"]:
            agent.validate_mode(mode)  # Should not raise


class TestLaneValidation:
    """Tests for lane validation."""
    
    def test_permitted_lane_accepted(self):
        """Permitted lanes are accepted."""
        agent = validate_agent_gid("GID-01")  # CODY
        agent.validate_lane("CORE")  # Should not raise
        agent.validate_lane("GOVERNANCE")  # Should not raise
    
    def test_non_permitted_lane_rejected(self):
        """Non-permitted lanes are HARD FAIL."""
        agent = validate_agent_gid("GID-03")  # MIRA-R (RESEARCH lane only)
        
        with pytest.raises(LaneNotPermittedError) as exc_info:
            agent.validate_lane("BACKEND")  # Not in MIRA-R's lanes
        
        assert "BACKEND" in str(exc_info.value)
    
    def test_benson_has_all_access(self):
        """BENSON (GID-00) has ALL lane access."""
        agent = validate_agent_gid("GID-00")
        
        # ALL should accept any lane
        agent.validate_lane("CORE")
        agent.validate_lane("FRONTEND")
        agent.validate_lane("RANDOM_LANE")


class TestFullIdentityValidation:
    """Tests for full identity validation chain."""
    
    def test_valid_full_identity(self):
        """Valid GID + MODE + LANE is accepted."""
        agent = validate_full_identity("GID-01", "EXECUTION", "CORE")
        
        assert agent.gid == "GID-01"
        assert agent.name == "CODY"
    
    def test_invalid_gid_in_chain(self):
        """Invalid GID fails the chain."""
        with pytest.raises(UnknownGIDError):
            validate_full_identity("GID-99", "EXECUTION", "CORE")
    
    def test_invalid_mode_in_chain(self):
        """Invalid MODE fails the chain."""
        with pytest.raises(ModeNotPermittedError):
            validate_full_identity("GID-01", "ORCHESTRATION", "CORE")
    
    def test_invalid_lane_in_chain(self):
        """Invalid LANE fails the chain."""
        # GID-03 (MIRA-R) has modes: RESEARCH, ANALYSIS, REVIEW
        # and lanes: RESEARCH, INTELLIGENCE, VALIDATION
        # Using a valid mode but invalid lane
        with pytest.raises(LaneNotPermittedError):
            validate_full_identity("GID-03", "RESEARCH", "BACKEND")


# ═══════════════════════════════════════════════════════════════════════════════
# MODE SCHEMA TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestModeDeclaration:
    """Tests for mode declaration validation."""
    
    def test_valid_declaration_accepted(self):
        """Valid declarations are accepted."""
        decl = create_mode_declaration(
            gid="GID-01",
            role="Backend Code Agent",
            mode="EXECUTION",
            execution_lane="CORE",
        )
        
        assert decl.gid == "GID-01"
        assert decl.mode == "EXECUTION"
    
    def test_missing_field_rejected(self):
        """Missing mandatory fields are HARD FAIL."""
        validator = ModeSchemaValidator()
        
        with pytest.raises(MissingFieldError) as exc_info:
            validator.validate_raw_input({
                "GID": "GID-01",
                # Missing ROLE, MODE, EXECUTION_LANE
            })
        
        assert "mandatory field" in str(exc_info.value).lower()
    
    def test_malformed_field_rejected(self):
        """Malformed fields are HARD FAIL."""
        validator = ModeSchemaValidator()
        
        with pytest.raises(MalformedFieldError):
            validator.validate_raw_input({
                "GID": 123,  # Should be string
                "ROLE": "Test",
                "MODE": "EXECUTION",
                "EXECUTION_LANE": "CORE",
            })


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL MATRIX TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestToolMatrix:
    """Tests for tool matrix evaluation."""
    
    def test_execution_mode_has_write_tools(self):
        """EXECUTION mode includes write tools."""
        result = evaluate_tools("EXECUTION", "CORE")
        
        assert ToolCategory.WRITE_FILE in result.allowed_tools
        assert ToolCategory.EDIT_FILE in result.allowed_tools
        assert ToolCategory.RUN_TERMINAL in result.allowed_tools
    
    def test_review_mode_is_read_only(self):
        """REVIEW mode is read-only."""
        result = evaluate_tools("REVIEW", "CORE")
        
        assert ToolCategory.READ_FILE in result.allowed_tools
        assert ToolCategory.WRITE_FILE not in result.allowed_tools
        assert ToolCategory.EDIT_FILE not in result.allowed_tools
        assert ToolCategory.RUN_TERMINAL not in result.allowed_tools
    
    def test_orchestration_has_authority_tools(self):
        """ORCHESTRATION mode has authority tools."""
        result = evaluate_tools("ORCHESTRATION", "ALL")
        
        assert ToolCategory.RUN_SUBAGENT in result.allowed_tools
    
    def test_tool_stripping(self):
        """Disallowed tools are stripped silently."""
        tools = ["read_file", "write_file", "run_in_terminal", "create_pac"]
        
        # REVIEW mode should strip write tools
        allowed = strip_disallowed_tools(tools, "REVIEW", "CORE")
        
        assert "read_file" in allowed
        assert "write_file" not in allowed
        assert "run_in_terminal" not in allowed
    
    def test_path_restrictions_by_lane(self):
        """Lanes restrict file paths."""
        # FRONTEND lane should allow frontend paths
        assert is_path_permitted("/chainboard-ui/src/App.tsx", "FRONTEND")
        assert is_path_permitted("/frontend/index.js", "FRONTEND")
        
        # CORE lane should allow core paths
        assert is_path_permitted("/core/engine.py", "CORE")
        
        # ALL lane has no restrictions
        assert is_path_permitted("/anything/anywhere.py", "ALL")


class TestToolPermissions:
    """Tests for individual tool permission checks."""
    
    def test_is_tool_permitted(self):
        """Tool permission check works correctly."""
        # EXECUTION mode permits write
        assert is_tool_permitted("write_file", "EXECUTION", "CORE") is True
        
        # REVIEW mode denies write
        assert is_tool_permitted("write_file", "REVIEW", "CORE") is False
        
        # Unknown tool is denied (FAIL-CLOSED)
        assert is_tool_permitted("unknown_tool", "EXECUTION", "CORE") is False


# ═══════════════════════════════════════════════════════════════════════════════
# WRAP VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestWRAPValidation:
    """Tests for WRAP document validation."""
    
    @pytest.fixture
    def valid_wrap_text(self):
        """Sample valid WRAP document."""
        return """
# WRAP HEADER
WRAP_ID: WRAP-TEST-001
PAC_ID: PAC-TEST-001
GID: GID-01
ROLE: Backend Code Agent
MODE: EXECUTION
EXECUTION_LANE: CORE

# PROOF BLOCK
ARTIFACTS_CREATED:
- core/test.py
- tests/test_test.py

COMMANDS:
- pytest tests/

VERIFICATION:
- All tests pass

# DECISION BLOCK
ACTION_SUMMARY: Implemented test module
RATIONALE: Required by PAC

# OUTCOME BLOCK
STATUS: COMPLETE
DELIVERABLES:
- core/test.py
- tests/test_test.py

# ATTESTATION
ATTESTED_BY: GID-01
TIMESTAMP: 2025-12-26T12:00:00Z
BER_ELIGIBLE: YES
"""
    
    def test_valid_wrap_accepted(self, valid_wrap_text):
        """Valid WRAP is accepted."""
        is_valid, error = is_wrap_valid(valid_wrap_text)
        assert is_valid is True
        assert error is None
    
    def test_missing_block_rejected(self):
        """Missing mandatory block is HARD FAIL."""
        incomplete_wrap = """
# WRAP HEADER
WRAP_ID: WRAP-TEST-001
PAC_ID: PAC-TEST-001
GID: GID-01

# PROOF BLOCK (only)
ARTIFACTS_CREATED:
- test.py
"""
        
        with pytest.raises(WRAPMissingBlockError):
            validate_wrap(incomplete_wrap)
    
    def test_malformed_header_rejected(self):
        """Malformed header is HARD FAIL."""
        malformed_wrap = """
# WRAP HEADER
WRAP_ID: WRAP-TEST-001
# Missing PAC_ID and GID!

# PROOF BLOCK
ARTIFACTS_CREATED:
- test.py
"""
        
        is_valid, error = is_wrap_valid(malformed_wrap)
        assert is_valid is False
        assert error is not None


# ═══════════════════════════════════════════════════════════════════════════════
# ECHO-BACK HANDSHAKE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEchoHandshake:
    """Tests for echo-back handshake validation."""
    
    def test_valid_handshake_format(self):
        """Valid handshake format is generated."""
        handshake = format_echo_handshake("GID-01", "EXECUTION", "CORE")
        
        assert "GID-01" in handshake
        assert "EXECUTION" in handshake
        assert "CORE" in handshake
    
    def test_handshake_validation_success(self):
        """Valid handshake passes validation."""
        response = """GID-01 | MODE: EXECUTION | ROLE: Backend Code Agent
        
Here is my work..."""
        
        is_valid, error = validate_echo_handshake(response, "GID-01", "EXECUTION")
        assert is_valid is True
    
    def test_handshake_validation_failure(self):
        """Invalid handshake fails validation."""
        response = """Here is my work without proper handshake..."""
        
        is_valid, error = validate_echo_handshake(response, "GID-01", "EXECUTION")
        assert is_valid is False
        assert error is not None
    
    def test_wrong_gid_in_handshake(self):
        """Wrong GID in handshake fails validation."""
        response = """GID-02 | MODE: EXECUTION | ROLE: Test
        
Here is my work..."""
        
        is_valid, error = validate_echo_handshake(response, "GID-01", "EXECUTION")
        assert is_valid is False


# ═══════════════════════════════════════════════════════════════════════════════
# ENFORCEMENT ORCHESTRATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnforcer:
    """Tests for enforcement orchestrator."""
    
    def test_enforce_creates_context(self):
        """Enforcement creates valid context."""
        ctx = enforce(
            gid="GID-01",
            role="Backend Code Agent",
            mode="EXECUTION",
            execution_lane="CORE",
        )
        
        assert isinstance(ctx, EnforcementContext)
        assert ctx.gid == "GID-01"
        assert ctx.mode == "EXECUTION"
    
    def test_enforce_invalid_gid_fails(self):
        """Invalid GID fails enforcement chain."""
        with pytest.raises(EnforcementChainError) as exc_info:
            enforce(
                gid="GID-99",
                role="Unknown",
                mode="EXECUTION",
                execution_lane="CORE",
            )
        
        assert "GID_VALIDATION" in str(exc_info.value)
    
    def test_enforce_invalid_mode_fails(self):
        """Invalid mode fails enforcement chain."""
        with pytest.raises(EnforcementChainError) as exc_info:
            enforce(
                gid="GID-01",
                role="Backend Code Agent",
                mode="ORCHESTRATION",  # Not allowed for CODY
                execution_lane="CORE",
            )
        
        assert "GID_VALIDATION" in str(exc_info.value) or "MODE" in str(exc_info.value)
    
    def test_context_tool_assertions(self):
        """Context correctly asserts tool permissions."""
        ctx = enforce(
            gid="GID-01",
            role="Backend Code Agent",
            mode="EXECUTION",
            execution_lane="CORE",
        )
        
        # Should not raise
        ctx.assert_tool_allowed("write_file")
        ctx.assert_tool_allowed("read_file")
        
        # Should raise for authority tools
        with pytest.raises(ToolDeniedError):
            ctx.assert_tool_allowed("create_pac")


# ═══════════════════════════════════════════════════════════════════════════════
# BER ELIGIBILITY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBEReligibility:
    """Tests for BER eligibility checks."""
    
    @pytest.fixture
    def complete_wrap(self):
        """WRAP marked as complete and BER-eligible."""
        return """
# WRAP HEADER
WRAP_ID: WRAP-TEST-001
PAC_ID: PAC-TEST-001
GID: GID-01
ROLE: Backend Code Agent

# PROOF BLOCK
ARTIFACTS_CREATED:
- test.py

# DECISION BLOCK
ACTION_SUMMARY: Completed task

# OUTCOME BLOCK
STATUS: COMPLETE
DELIVERABLES:
- test.py

# ATTESTATION
ATTESTED_BY: GID-01
TIMESTAMP: 2025-12-26T12:00:00Z
BER_ELIGIBLE: YES
"""
    
    @pytest.fixture
    def incomplete_wrap(self):
        """WRAP marked as partial."""
        return """
# WRAP HEADER
WRAP_ID: WRAP-TEST-002
PAC_ID: PAC-TEST-002
GID: GID-01
ROLE: Backend Code Agent

# PROOF BLOCK
ARTIFACTS_CREATED:
- partial.py

# DECISION BLOCK
ACTION_SUMMARY: Partial completion

# OUTCOME BLOCK
STATUS: PARTIAL
BLOCKERS:
- Awaiting dependencies

# ATTESTATION
ATTESTED_BY: GID-01
TIMESTAMP: 2025-12-26T12:00:00Z
BER_ELIGIBLE: NO
"""
    
    def test_complete_wrap_is_ber_eligible(self, complete_wrap):
        """Complete WRAP is BER-eligible."""
        eligible, reason = check_ber_eligibility(complete_wrap)
        assert eligible is True
        assert reason is None
    
    def test_incomplete_wrap_not_ber_eligible(self, incomplete_wrap):
        """Incomplete WRAP is not BER-eligible."""
        eligible, reason = check_ber_eligibility(incomplete_wrap)
        assert eligible is False
        assert reason is not None


# ═══════════════════════════════════════════════════════════════════════════════
# FAIL-CLOSED TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFailClosed:
    """Tests that verify FAIL-CLOSED behavior."""
    
    def test_unknown_mode_treated_as_advisory(self):
        """Unknown modes default to most restrictive (ADVISORY)."""
        result = evaluate_tools("UNKNOWN_MODE", "ALL")
        
        # Should have only read-only tools
        assert ToolCategory.READ_FILE in result.allowed_tools
        assert ToolCategory.WRITE_FILE not in result.allowed_tools
    
    def test_no_context_denies_all_tools(self):
        """Without context, all tools are denied."""
        enforcer = Enforcer()
        enforcer.clear_context()
        
        tools = ["read_file", "write_file"]
        result = enforcer.strip_tools(tools)
        
        # No context → empty list (all denied)
        assert result == []
