"""
Test Suite — PAC Schema Validation (PAC-019)
════════════════════════════════════════════════════════════════════════════════

Tests for PAC_SCHEMA_LAW_v1.md compliance.

REQUIRED SCENARIOS:
- Fully compliant PAC → PASS
- Missing WRAP obligation → FAIL
- Missing BER obligation → FAIL
- Missing FINAL_STATE → FAIL
- Multiple missing sections → FAIL
- Terminal visibility emissions

════════════════════════════════════════════════════════════════════════════════
"""

import io
import pytest

from core.governance.pac_schema import (
    ALL_REQUIRED_SECTIONS,
    BERObligation,
    BERStatus,
    BODY_SECTIONS,
    HEADER_SECTIONS,
    LOOP_CLOSURE_SECTIONS,
    PACBuilder,
    PACDeliverable,
    PACDiscipline,
    PACDispatch,
    PACFinalState,
    PACHeader,
    PACMode,
    PACSchema,
    PACSection,
    PACStatus,
    SECTION_NAMES,
    WRAPObligation,
    WRAPStatus,
    is_valid_pac_id,
)
from core.governance.pac_schema_validator import (
    InvalidPACIDError,
    MissingBERObligationError,
    MissingFinalStateError,
    MissingWRAPObligationError,
    PACSchemaTerminalRenderer,
    PACSchemaValidator,
    PACSchemaViolationError,
    PACTextParser,
    PACValidationResult,
    get_pac_parser,
    get_pac_validator,
    is_pac_valid,
    parse_pac,
    require_valid_pac,
    reset_pac_validator,
    validate_pac,
    validate_pac_text,
)
from core.governance.orchestration_engine import (
    DispatchResult,
    DispatchStatus,
    GovernanceOrchestrationEngine,
    LoopState,
    OrchestrationTerminalRenderer,
    dispatch_pac,
    dispatch_pac_text,
    get_orchestration_engine,
    is_loop_closed,
    issue_ber,
    receive_wrap,
    reset_orchestration_engine,
)
from core.governance.terminal_gates import TerminalGateRenderer


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_state():
    """Reset singletons before each test."""
    reset_pac_validator()
    reset_orchestration_engine()
    yield
    reset_pac_validator()
    reset_orchestration_engine()


@pytest.fixture
def valid_pac() -> PACSchema:
    """Create a fully compliant PAC."""
    return (
        PACBuilder()
        .with_id("PAC-BENSON-EXEC-GOVERNANCE-TEST-001")
        .with_issuer("Jeffrey (Drafting Surface)")
        .with_target("Benson Execution (GID-00)")
        .with_mode(PACMode.ORCHESTRATION)
        .with_discipline(PACDiscipline.GOLD_STANDARD)
        .with_objective("Test objective")
        .with_execution_plan("1. Step one\n2. Step two")
        .add_deliverable("Test deliverable 1")
        .add_deliverable("Test deliverable 2")
        .add_constraint("FAIL-CLOSED only")
        .add_success_criterion("All tests pass")
        .with_dispatch("GID-01", "Senior Backend Engineer", "GOVERNANCE", PACMode.EXECUTION)
        .with_wrap_obligation()
        .with_ber_obligation()
        .with_final_state()
        .build()
    )


@pytest.fixture
def pac_missing_wrap() -> PACSchema:
    """Create PAC missing WRAP obligation."""
    return (
        PACBuilder()
        .with_id("PAC-BENSON-EXEC-GOVERNANCE-TEST-002")
        .with_issuer("Jeffrey (Drafting Surface)")
        .with_target("Benson Execution (GID-00)")
        .with_mode(PACMode.ORCHESTRATION)
        .with_discipline(PACDiscipline.FAIL_CLOSED)
        .with_objective("Test objective")
        .with_execution_plan("1. Step one")
        .add_deliverable("Test deliverable")
        .add_constraint("Constraint")
        .add_success_criterion("Criterion")
        .with_dispatch("GID-01", "Engineer", "GOVERNANCE", PACMode.EXECUTION)
        # NO .with_wrap_obligation()
        .with_ber_obligation()
        .with_final_state()
        .build()
    )


@pytest.fixture
def pac_missing_ber() -> PACSchema:
    """Create PAC missing BER obligation."""
    return (
        PACBuilder()
        .with_id("PAC-BENSON-EXEC-GOVERNANCE-TEST-003")
        .with_issuer("Jeffrey (Drafting Surface)")
        .with_target("Benson Execution (GID-00)")
        .with_mode(PACMode.ORCHESTRATION)
        .with_discipline(PACDiscipline.FAIL_CLOSED)
        .with_objective("Test objective")
        .with_execution_plan("1. Step one")
        .add_deliverable("Test deliverable")
        .add_constraint("Constraint")
        .add_success_criterion("Criterion")
        .with_dispatch("GID-01", "Engineer", "GOVERNANCE", PACMode.EXECUTION)
        .with_wrap_obligation()
        # NO .with_ber_obligation()
        .with_final_state()
        .build()
    )


@pytest.fixture
def pac_missing_final_state() -> PACSchema:
    """Create PAC missing FINAL_STATE."""
    return (
        PACBuilder()
        .with_id("PAC-BENSON-EXEC-GOVERNANCE-TEST-004")
        .with_issuer("Jeffrey (Drafting Surface)")
        .with_target("Benson Execution (GID-00)")
        .with_mode(PACMode.ORCHESTRATION)
        .with_discipline(PACDiscipline.FAIL_CLOSED)
        .with_objective("Test objective")
        .with_execution_plan("1. Step one")
        .add_deliverable("Test deliverable")
        .add_constraint("Constraint")
        .add_success_criterion("Criterion")
        .with_dispatch("GID-01", "Engineer", "GOVERNANCE", PACMode.EXECUTION)
        .with_wrap_obligation()
        .with_ber_obligation()
        # NO .with_final_state()
        .build()
    )


@pytest.fixture
def pac_missing_all_loop_closure() -> PACSchema:
    """Create PAC missing all loop closure sections."""
    return (
        PACBuilder()
        .with_id("PAC-BENSON-EXEC-GOVERNANCE-TEST-005")
        .with_issuer("Jeffrey (Drafting Surface)")
        .with_target("Benson Execution (GID-00)")
        .with_mode(PACMode.ORCHESTRATION)
        .with_discipline(PACDiscipline.FAIL_CLOSED)
        .with_objective("Test objective")
        .with_execution_plan("1. Step one")
        .add_deliverable("Test deliverable")
        .add_constraint("Constraint")
        .add_success_criterion("Criterion")
        # NO dispatch, wrap, ber, final_state
        .build()
    )


@pytest.fixture
def buffer():
    """Create StringIO buffer for output capture."""
    return io.StringIO()


@pytest.fixture
def renderer(buffer):
    """Create terminal renderer with buffer."""
    return TerminalGateRenderer(output=buffer)


# ═══════════════════════════════════════════════════════════════════════════════
# PAC ID TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPACIDFormat:
    """Test PAC ID format validation."""
    
    def test_valid_pac_id_format(self):
        """Valid PAC IDs should pass."""
        assert is_valid_pac_id("PAC-BENSON-EXEC-GOVERNANCE-TEST-001")
        assert is_valid_pac_id("PAC-BENSON-EXEC-GOVERNANCE-EXAMPLE-123")
    
    def test_invalid_pac_id_format(self):
        """Invalid PAC IDs should fail."""
        assert not is_valid_pac_id("INVALID")
        assert not is_valid_pac_id("pac-test")
        assert not is_valid_pac_id("")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION CONSTANTS TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSectionConstants:
    """Test section constant definitions."""
    
    def test_all_sections_have_names(self):
        """All sections should have display names."""
        for section in PACSection:
            assert section in SECTION_NAMES
            assert len(SECTION_NAMES[section]) > 0
    
    def test_header_sections_defined(self):
        """Header sections should be defined."""
        assert PACSection.PAC_ID in HEADER_SECTIONS
        assert PACSection.ISSUER in HEADER_SECTIONS
        assert PACSection.TARGET in HEADER_SECTIONS
    
    def test_body_sections_defined(self):
        """Body sections should be defined."""
        assert PACSection.OBJECTIVE in BODY_SECTIONS
        assert PACSection.EXECUTION_PLAN in BODY_SECTIONS
        assert PACSection.REQUIRED_DELIVERABLES in BODY_SECTIONS
    
    def test_loop_closure_sections_defined(self):
        """Loop closure sections should be defined."""
        assert PACSection.DISPATCH in LOOP_CLOSURE_SECTIONS
        assert PACSection.WRAP_OBLIGATION in LOOP_CLOSURE_SECTIONS
        assert PACSection.BER_OBLIGATION in LOOP_CLOSURE_SECTIONS
        assert PACSection.FINAL_STATE in LOOP_CLOSURE_SECTIONS
    
    def test_all_sections_required(self):
        """All sections should be in ALL_REQUIRED_SECTIONS."""
        for section in PACSection:
            assert section in ALL_REQUIRED_SECTIONS


# ═══════════════════════════════════════════════════════════════════════════════
# PAC SCHEMA TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPACSchema:
    """Test PACSchema dataclass."""
    
    def test_valid_schema_creation(self, valid_pac):
        """Valid PAC should be created successfully."""
        assert valid_pac.pac_id == "PAC-BENSON-EXEC-GOVERNANCE-TEST-001"
        assert valid_pac.has_wrap_obligation
        assert valid_pac.has_ber_obligation
        assert valid_pac.has_final_state
        assert valid_pac.is_loop_closure_complete
    
    def test_missing_sections_detected(self, pac_missing_wrap):
        """Missing sections should be detected."""
        missing = pac_missing_wrap.missing_sections
        assert PACSection.WRAP_OBLIGATION in missing
    
    def test_loop_closure_incomplete(self, pac_missing_wrap):
        """Loop closure should be incomplete when sections missing."""
        assert not pac_missing_wrap.is_loop_closure_complete


# ═══════════════════════════════════════════════════════════════════════════════
# PAC BUILDER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPACBuilder:
    """Test PACBuilder fluent API."""
    
    def test_builder_creates_valid_pac(self):
        """Builder should create valid PAC."""
        pac = (
            PACBuilder()
            .with_id("PAC-TEST-EXEC-CORE-BUILDER-001")
            .with_issuer("Test")
            .with_target("Test Target")
            .with_mode(PACMode.EXECUTION)
            .with_discipline(PACDiscipline.FAIL_CLOSED)
            .with_objective("Test objective")
            .with_execution_plan("Test plan")
            .add_deliverable("Deliverable 1")
            .add_constraint("Constraint 1")
            .add_success_criterion("Criterion 1")
            .with_dispatch("GID-01", "Role", "LANE", PACMode.EXECUTION)
            .with_wrap_obligation()
            .with_ber_obligation()
            .with_final_state()
            .build()
        )
        
        assert pac.pac_id == "PAC-TEST-EXEC-CORE-BUILDER-001"
        assert pac.is_loop_closure_complete
    
    def test_builder_without_loop_closure(self):
        """Builder without loop closure creates incomplete PAC."""
        pac = (
            PACBuilder()
            .with_id("PAC-TEST-EXEC-CORE-INCOMPLETE-001")
            .with_issuer("Test")
            .with_target("Test Target")
            .with_mode(PACMode.EXECUTION)
            .with_discipline(PACDiscipline.FAIL_CLOSED)
            .with_objective("Test")
            .with_execution_plan("Test")
            .add_deliverable("Test")
            .add_constraint("Test")
            .add_success_criterion("Test")
            # No loop closure sections
            .build()
        )
        
        assert not pac.is_loop_closure_complete


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS — POSITIVE
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidatorPositive:
    """Test validator with valid PACs."""
    
    def test_valid_pac_passes(self, valid_pac):
        """Valid PAC should pass validation."""
        validator = PACSchemaValidator(emit_terminal=False)
        result = validator.validate(valid_pac)
        
        assert result.valid
        assert len(result.missing_sections) == 0
        assert len(result.errors) == 0
    
    def test_is_valid_returns_true(self, valid_pac):
        """is_valid should return True for valid PAC."""
        validator = PACSchemaValidator(emit_terminal=False)
        assert validator.is_valid(valid_pac)
    
    def test_validate_and_raise_succeeds(self, valid_pac):
        """validate_and_raise should not raise for valid PAC."""
        validator = PACSchemaValidator(emit_terminal=False)
        # Should not raise
        validator.validate_and_raise(valid_pac)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS — NEGATIVE (MISSING WRAP)
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidatorMissingWRAP:
    """Test validator with PAC missing WRAP obligation."""
    
    def test_missing_wrap_fails(self, pac_missing_wrap):
        """PAC missing WRAP should fail validation."""
        validator = PACSchemaValidator(emit_terminal=False)
        result = validator.validate(pac_missing_wrap)
        
        assert not result.valid
        assert PACSection.WRAP_OBLIGATION in result.missing_sections
    
    def test_missing_wrap_raises(self, pac_missing_wrap):
        """Missing WRAP should raise MissingWRAPObligationError."""
        validator = PACSchemaValidator(emit_terminal=False)
        
        with pytest.raises(MissingWRAPObligationError):
            validator.validate_and_raise(pac_missing_wrap)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS — NEGATIVE (MISSING BER)
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidatorMissingBER:
    """Test validator with PAC missing BER obligation."""
    
    def test_missing_ber_fails(self, pac_missing_ber):
        """PAC missing BER should fail validation."""
        validator = PACSchemaValidator(emit_terminal=False)
        result = validator.validate(pac_missing_ber)
        
        assert not result.valid
        assert PACSection.BER_OBLIGATION in result.missing_sections
    
    def test_missing_ber_raises(self, pac_missing_ber):
        """Missing BER should raise MissingBERObligationError."""
        validator = PACSchemaValidator(emit_terminal=False)
        
        with pytest.raises(MissingBERObligationError):
            validator.validate_and_raise(pac_missing_ber)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS — NEGATIVE (MISSING FINAL_STATE)
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidatorMissingFinalState:
    """Test validator with PAC missing FINAL_STATE."""
    
    def test_missing_final_state_fails(self, pac_missing_final_state):
        """PAC missing FINAL_STATE should fail validation."""
        validator = PACSchemaValidator(emit_terminal=False)
        result = validator.validate(pac_missing_final_state)
        
        assert not result.valid
        assert PACSection.FINAL_STATE in result.missing_sections
    
    def test_missing_final_state_raises(self, pac_missing_final_state):
        """Missing FINAL_STATE should raise MissingFinalStateError."""
        validator = PACSchemaValidator(emit_terminal=False)
        
        with pytest.raises(MissingFinalStateError):
            validator.validate_and_raise(pac_missing_final_state)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATOR TESTS — NEGATIVE (MULTIPLE MISSING)
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidatorMultipleMissing:
    """Test validator with multiple missing sections."""
    
    def test_multiple_missing_detected(self, pac_missing_all_loop_closure):
        """All missing loop closure sections should be detected."""
        validator = PACSchemaValidator(emit_terminal=False)
        result = validator.validate(pac_missing_all_loop_closure)
        
        assert not result.valid
        assert PACSection.DISPATCH in result.missing_sections
        assert PACSection.WRAP_OBLIGATION in result.missing_sections
        assert PACSection.BER_OBLIGATION in result.missing_sections
        assert PACSection.FINAL_STATE in result.missing_sections
    
    def test_multiple_missing_raises_first(self, pac_missing_all_loop_closure):
        """validate_and_raise should raise for first loop closure violation."""
        validator = PACSchemaValidator(emit_terminal=False)
        
        # Should raise one of the missing errors
        with pytest.raises(PACSchemaViolationError):
            validator.validate_and_raise(pac_missing_all_loop_closure)


# ═══════════════════════════════════════════════════════════════════════════════
# TERMINAL OUTPUT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTerminalOutput:
    """Test terminal visibility emissions."""
    
    def test_accepted_emission(self, valid_pac, buffer, renderer):
        """Valid PAC should emit accepted message."""
        schema_renderer = PACSchemaTerminalRenderer(renderer)
        validator = PACSchemaValidator(renderer=schema_renderer)
        
        validator.validate(valid_pac)
        
        output = buffer.getvalue()
        assert "PAC ACCEPTED" in output
        assert "SCHEMA VALID" in output
    
    def test_rejected_emission(self, pac_missing_wrap, buffer, renderer):
        """Invalid PAC should emit rejected message."""
        schema_renderer = PACSchemaTerminalRenderer(renderer)
        validator = PACSchemaValidator(renderer=schema_renderer)
        
        validator.validate(pac_missing_wrap)
        
        output = buffer.getvalue()
        assert "PAC REJECTED" in output
        assert "SCHEMA VIOLATION" in output
    
    def test_missing_section_enumerated(self, pac_missing_wrap, buffer, renderer):
        """Missing sections should be enumerated."""
        schema_renderer = PACSchemaTerminalRenderer(renderer)
        validator = PACSchemaValidator(renderer=schema_renderer)
        
        validator.validate(pac_missing_wrap)
        
        output = buffer.getvalue()
        assert "MISSING" in output
        assert "WRAP_OBLIGATION" in output


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION ENGINE TESTS — DISPATCH
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrchestrationEngineDispatch:
    """Test PAC dispatch through orchestration engine."""
    
    def test_valid_pac_dispatched(self, valid_pac):
        """Valid PAC should be dispatched."""
        engine = GovernanceOrchestrationEngine()
        # Disable terminal output for testing
        engine._validator = PACSchemaValidator(emit_terminal=False)
        
        result = engine.dispatch(valid_pac)
        
        assert result.success
        assert result.status == DispatchStatus.DISPATCHED
        assert result.pac_id == valid_pac.pac_id
        assert result.target_gid == "GID-01"
    
    def test_invalid_pac_rejected(self, pac_missing_wrap):
        """Invalid PAC should be rejected."""
        engine = GovernanceOrchestrationEngine()
        engine._validator = PACSchemaValidator(emit_terminal=False)
        
        result = engine.dispatch(pac_missing_wrap)
        
        assert result.rejected
        assert result.status == DispatchStatus.REJECTED
        assert result.error is not None


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION ENGINE TESTS — LOOP CLOSURE
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrchestrationEngineLoopClosure:
    """Test loop closure tracking."""
    
    def test_loop_starts_open(self, valid_pac):
        """Loop should start open after dispatch."""
        engine = GovernanceOrchestrationEngine()
        engine._validator = PACSchemaValidator(emit_terminal=False)
        
        engine.dispatch(valid_pac)
        
        assert not engine.is_loop_closed(valid_pac.pac_id)
        loop = engine.get_loop_state(valid_pac.pac_id)
        assert loop.awaiting_wrap
    
    def test_wrap_received(self, valid_pac):
        """WRAP receipt should auto-issue and emit BER (PAC-020/021 enforcement)."""
        engine = GovernanceOrchestrationEngine()
        engine._validator = PACSchemaValidator(emit_terminal=False)
        
        engine.dispatch(valid_pac)
        # PAC-020/021: receive_wrap now auto-issues AND emits BER, returns artifact
        artifact = engine.receive_wrap(valid_pac.pac_id, WRAPStatus.COMPLETE)
        
        # Get loop state separately (PAC-021 changes return type)
        loop = engine.get_loop_state(valid_pac.pac_id)
        
        # Both WRAP and BER should be recorded
        assert loop.wrap_received
        assert loop.wrap_status == WRAPStatus.COMPLETE
        # PAC-020: BER is now synchronously issued
        assert loop.ber_issued
        # PAC-021: BER is now emitted
        assert loop.ber_emitted
        assert loop.is_loop_closed
    
    def test_ber_issued(self, valid_pac):
        """BER issuance should be recorded (now automatic with PAC-020)."""
        engine = GovernanceOrchestrationEngine()
        engine._validator = PACSchemaValidator(emit_terminal=False)
        
        engine.dispatch(valid_pac)
        # PAC-020: receive_wrap auto-issues BER, so we use the test method
        engine.receive_wrap_without_auto_ber(valid_pac.pac_id, WRAPStatus.COMPLETE)
        engine.issue_ber(valid_pac.pac_id, BERStatus.APPROVE)
        
        loop = engine.get_loop_state(valid_pac.pac_id)
        assert loop.ber_issued
        assert loop.ber_status == BERStatus.APPROVE
    
    def test_loop_closed_after_ber(self, valid_pac):
        """Loop should be closed after WRAP + BER."""
        engine = GovernanceOrchestrationEngine()
        engine._validator = PACSchemaValidator(emit_terminal=False)
        
        engine.dispatch(valid_pac)
        # PAC-020: receive_wrap now auto-issues BER
        loop = engine.receive_wrap(valid_pac.pac_id, WRAPStatus.COMPLETE)
        
        assert engine.is_loop_closed(valid_pac.pac_id)
        loop = engine.get_loop_state(valid_pac.pac_id)
        assert loop.is_loop_closed
        assert loop.status == DispatchStatus.CLOSED


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_validate_pac(self, valid_pac):
        """validate_pac convenience function."""
        result = validate_pac(valid_pac)
        assert result.valid
    
    def test_is_pac_valid(self, valid_pac, pac_missing_wrap):
        """is_pac_valid convenience function."""
        assert is_pac_valid(valid_pac)
        assert not is_pac_valid(pac_missing_wrap)
    
    def test_require_valid_pac_raises(self, pac_missing_wrap):
        """require_valid_pac should raise for invalid PAC."""
        with pytest.raises(PACSchemaViolationError):
            require_valid_pac(pac_missing_wrap)


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExceptions:
    """Test exception behaviors."""
    
    def test_missing_wrap_error_message(self):
        """MissingWRAPObligationError should have clear message."""
        error = MissingWRAPObligationError("TEST-PAC")
        assert "WRAP_OBLIGATION" in str(error)
        assert "required" in str(error).lower()
    
    def test_missing_ber_error_message(self):
        """MissingBERObligationError should have clear message."""
        error = MissingBERObligationError("TEST-PAC")
        assert "BER_OBLIGATION" in str(error)
        assert "required" in str(error).lower()
    
    def test_missing_final_state_error_message(self):
        """MissingFinalStateError should have clear message."""
        error = MissingFinalStateError("TEST-PAC")
        assert "FINAL_STATE" in str(error)
        assert "required" in str(error).lower()
    
    def test_schema_violation_captures_sections(self):
        """PACSchemaViolationError should capture missing sections."""
        error = PACSchemaViolationError(
            "Test error",
            missing_sections=[PACSection.WRAP_OBLIGATION, PACSection.BER_OBLIGATION],
            pac_id="TEST-PAC",
        )
        assert len(error.missing_sections) == 2
        assert error.pac_id == "TEST-PAC"


# ═══════════════════════════════════════════════════════════════════════════════
# INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvariants:
    """Test schema law invariants."""
    
    def test_inv_pac_001_no_dispatch_without_validation(self, pac_missing_wrap):
        """INV-PAC-001: No PAC dispatch without schema validation."""
        engine = GovernanceOrchestrationEngine()
        engine._validator = PACSchemaValidator(emit_terminal=False)
        
        # Invalid PAC should be rejected, not dispatched
        result = engine.dispatch(pac_missing_wrap)
        
        assert result.rejected
        assert result.validation_result is not None
        assert not result.validation_result.valid
    
    def test_inv_pac_002_missing_wrap_rejected(self, pac_missing_wrap):
        """INV-PAC-002: Missing WRAP obligation = REJECT."""
        validator = PACSchemaValidator(emit_terminal=False)
        result = validator.validate(pac_missing_wrap)
        
        assert not result.valid
        assert PACSection.WRAP_OBLIGATION in result.missing_sections
    
    def test_inv_pac_003_missing_ber_rejected(self, pac_missing_ber):
        """INV-PAC-003: Missing BER obligation = REJECT."""
        validator = PACSchemaValidator(emit_terminal=False)
        result = validator.validate(pac_missing_ber)
        
        assert not result.valid
        assert PACSection.BER_OBLIGATION in result.missing_sections
    
    def test_inv_pac_004_missing_final_state_rejected(self, pac_missing_final_state):
        """INV-PAC-004: Missing FINAL_STATE = REJECT."""
        validator = PACSchemaValidator(emit_terminal=False)
        result = validator.validate(pac_missing_final_state)
        
        assert not result.valid
        assert PACSection.FINAL_STATE in result.missing_sections
    
    def test_inv_pac_006_loop_closure_guaranteed(self, valid_pac):
        """INV-PAC-006: Loop closure mechanically guaranteed."""
        engine = GovernanceOrchestrationEngine()
        engine._validator = PACSchemaValidator(emit_terminal=False)
        
        # Dispatch valid PAC
        engine.dispatch(valid_pac)
        
        # Record WRAP
        engine.receive_wrap(valid_pac.pac_id, WRAPStatus.COMPLETE)
        
        # Issue BER
        engine.issue_ber(valid_pac.pac_id, BERStatus.APPROVE)
        
        # Loop must be closed
        assert engine.is_loop_closed(valid_pac.pac_id)
