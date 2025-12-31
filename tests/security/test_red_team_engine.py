"""
Test Suite for Governance Red-Team Engine v2.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-031
Agent: GID-06 (Sam) — SECURITY
Deliverable: ≥30 tests for Governance Red-Team Engine v2
"""

import pytest
from typing import Any, Dict, Tuple

from core.security.red_team_engine import (
    # Constants
    ENGINE_VERSION,
    # Enums
    ArtifactType,
    MutationType,
    VulnerabilityLevel,
    AttackVector,
    TestResult,
    # Exceptions
    RedTeamError,
    MutationError,
    VulnerabilityFound,
    # Data Classes
    Mutation,
    MutationTestCase,
    TestExecution,
    Vulnerability,
    RedTeamReport,
    # Core Classes
    MutationGenerator,
    RedTeamEngine,
    # Factory Functions
    create_red_team_engine,
    create_sample_pac,
    create_sample_wrap,
    create_sample_ber,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def engine() -> RedTeamEngine:
    """Create a fresh red team engine."""
    return create_red_team_engine(seed=42)


@pytest.fixture
def generator() -> MutationGenerator:
    """Create a mutation generator."""
    return MutationGenerator(seed=42)


@pytest.fixture
def sample_pac() -> Dict[str, Any]:
    """Create sample PAC."""
    return create_sample_pac()


@pytest.fixture
def sample_wrap() -> Dict[str, Any]:
    """Create sample WRAP."""
    return create_sample_wrap()


def strict_validator(artifact: Dict[str, Any], artifact_type: ArtifactType) -> Tuple[bool, str]:
    """Validator that rejects all mutations (strict)."""
    return False, "Validation failed"


def permissive_validator(artifact: Dict[str, Any], artifact_type: ArtifactType) -> Tuple[bool, str]:
    """Validator that accepts all inputs (vulnerable)."""
    return True, "Accepted"


# =============================================================================
# TEST: ENUMS
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_artifact_types(self):
        """Test artifact type enum."""
        assert ArtifactType.PAC.value == "PAC"
        assert ArtifactType.WRAP.value == "WRAP"
        assert ArtifactType.BER.value == "BER"
    
    def test_mutation_types(self):
        """Test mutation type enum."""
        assert MutationType.FIELD_REMOVAL.value == "FIELD_REMOVAL"
        assert MutationType.HASH_TAMPERING.value == "HASH_TAMPERING"
        assert MutationType.STATE_INJECTION.value == "STATE_INJECTION"
    
    def test_vulnerability_levels(self):
        """Test vulnerability level enum."""
        assert VulnerabilityLevel.CRITICAL.value == "CRITICAL"
        assert VulnerabilityLevel.HIGH.value == "HIGH"
        assert VulnerabilityLevel.LOW.value == "LOW"
    
    def test_attack_vectors(self):
        """Test attack vector enum."""
        assert AttackVector.DATA_INTEGRITY.value == "DATA_INTEGRITY"
        assert AttackVector.STATE_MANIPULATION.value == "STATE_MANIPULATION"
    
    def test_test_results(self):
        """Test result enum."""
        assert TestResult.PASSED.value == "PASSED"
        assert TestResult.FAILED.value == "FAILED"


# =============================================================================
# TEST: EXCEPTIONS
# =============================================================================

class TestExceptions:
    """Test exception hierarchy."""
    
    def test_red_team_error_base(self):
        """Test base exception."""
        err = RedTeamError("test")
        assert str(err) == "test"
    
    def test_mutation_error(self):
        """Test mutation error."""
        err = MutationError(MutationType.FIELD_REMOVAL, "no fields")
        assert err.mutation_type == MutationType.FIELD_REMOVAL
    
    def test_vulnerability_found(self):
        """Test vulnerability found exception."""
        err = VulnerabilityFound("VULN-001", "Critical issue")
        assert err.vulnerability_id == "VULN-001"


# =============================================================================
# TEST: MUTATION GENERATOR
# =============================================================================

class TestMutationGenerator:
    """Test MutationGenerator class."""
    
    def test_generate_field_removal(self, generator, sample_pac):
        """Test field removal mutation."""
        mutation = generator.generate_field_removal(sample_pac, "title")
        
        assert mutation.mutation_type == MutationType.FIELD_REMOVAL
        assert mutation.target_field == "title"
        assert mutation.mutated_value is None
    
    def test_generate_type_change_string(self, generator, sample_pac):
        """Test type change for string field."""
        mutation = generator.generate_type_change(sample_pac, "title")
        
        assert mutation.mutation_type == MutationType.TYPE_CHANGE
        assert isinstance(mutation.mutated_value, int)
    
    def test_generate_type_change_int(self, generator):
        """Test type change for int field."""
        artifact = {"count": 5}
        mutation = generator.generate_type_change(artifact, "count")
        
        assert isinstance(mutation.mutated_value, str)
    
    def test_generate_hash_tampering(self, generator, sample_pac):
        """Test hash tampering mutation."""
        mutation = generator.generate_hash_tampering(sample_pac, "hash")
        
        assert mutation.mutation_type == MutationType.HASH_TAMPERING
        assert len(mutation.mutated_value) == 64
    
    def test_generate_timestamp_manipulation(self, generator, sample_pac):
        """Test timestamp manipulation."""
        mutation = generator.generate_timestamp_manipulation(sample_pac, "timestamp")
        
        assert mutation.mutation_type == MutationType.TIMESTAMP_MANIPULATION
        assert mutation.mutated_value != mutation.original_value
    
    def test_generate_id_collision(self, generator, sample_pac):
        """Test ID collision mutation."""
        mutation = generator.generate_id_collision(sample_pac, "pac_id", "COLLISION")
        
        assert mutation.mutation_type == MutationType.ID_COLLISION
        assert mutation.mutated_value == "COLLISION"
    
    def test_generate_state_injection(self, generator, sample_pac):
        """Test state injection mutation."""
        mutation = generator.generate_state_injection(sample_pac, "state", "HIJACKED")
        
        assert mutation.mutation_type == MutationType.STATE_INJECTION
        assert mutation.mutated_value == "HIJACKED"
    
    def test_generate_overflow(self, generator, sample_pac):
        """Test overflow mutation."""
        mutation = generator.generate_overflow(sample_pac, "title")
        
        assert mutation.mutation_type == MutationType.OVERFLOW
        assert len(mutation.mutated_value) == 1000000
    
    def test_generate_empty_value_string(self, generator, sample_pac):
        """Test empty value for string."""
        mutation = generator.generate_empty_value(sample_pac, "title")
        
        assert mutation.mutation_type == MutationType.EMPTY_VALUE
        assert mutation.mutated_value == ""
    
    def test_generate_empty_value_list(self, generator, sample_pac):
        """Test empty value for list."""
        mutation = generator.generate_empty_value(sample_pac, "agents")
        
        assert mutation.mutated_value == []
    
    def test_generate_invalid_reference(self, generator, sample_pac):
        """Test invalid reference mutation."""
        mutation = generator.generate_invalid_reference(sample_pac, "pac_id")
        
        assert mutation.mutation_type == MutationType.INVALID_REFERENCE
        assert mutation.mutated_value.startswith("INVALID-")
    
    def test_generate_random_mutation(self, generator, sample_pac):
        """Test random mutation generation."""
        mutation = generator.generate_random_mutation(sample_pac)
        
        assert mutation.mutation_id.startswith("MUT-")
        assert mutation.target_field in sample_pac


# =============================================================================
# TEST: RED TEAM ENGINE - TEST GENERATION
# =============================================================================

class TestRedTeamEngineGeneration:
    """Test test case generation."""
    
    def test_generate_test_cases(self, engine, sample_pac):
        """Test generating test cases."""
        cases = engine.generate_test_cases(sample_pac, ArtifactType.PAC, 10)
        
        assert len(cases) == 10
        assert all(c.artifact_type == ArtifactType.PAC for c in cases)
    
    def test_test_case_has_mutation(self, engine, sample_pac):
        """Test that test cases have mutations."""
        cases = engine.generate_test_cases(sample_pac, ArtifactType.PAC, 5)
        
        for case in cases:
            assert case.mutation is not None
            assert case.mutated_artifact != case.original_artifact
    
    def test_test_case_expected_result(self, engine, sample_pac):
        """Test expected result is set."""
        cases = engine.generate_test_cases(sample_pac, ArtifactType.PAC, 5)
        
        for case in cases:
            assert case.expected_result == TestResult.PASSED


# =============================================================================
# TEST: RED TEAM ENGINE - EXECUTION
# =============================================================================

class TestRedTeamEngineExecution:
    """Test test execution."""
    
    def test_execute_with_strict_validator(self, engine, sample_pac):
        """Test execution with strict validator."""
        engine.generate_test_cases(sample_pac, ArtifactType.PAC, 10)
        executions = engine.execute_tests(strict_validator)
        
        assert len(executions) == 10
        assert all(e.actual_result == TestResult.PASSED for e in executions)
    
    def test_execute_with_permissive_validator(self, engine, sample_pac):
        """Test execution with permissive (vulnerable) validator."""
        engine.generate_test_cases(sample_pac, ArtifactType.PAC, 10)
        executions = engine.execute_tests(permissive_validator)
        
        # All should fail (vulnerability detected)
        assert all(e.actual_result == TestResult.FAILED for e in executions)
    
    def test_execution_records_vulnerability(self, engine, sample_pac):
        """Test vulnerability recording."""
        engine.generate_test_cases(sample_pac, ArtifactType.PAC, 5)
        engine.execute_tests(permissive_validator)
        
        vulns = engine.get_vulnerabilities()
        assert len(vulns) > 0
    
    def test_execution_timing(self, engine, sample_pac):
        """Test execution timing is recorded."""
        engine.generate_test_cases(sample_pac, ArtifactType.PAC, 3)
        executions = engine.execute_tests(strict_validator)
        
        for e in executions:
            assert e.execution_time_ms >= 0


# =============================================================================
# TEST: RED TEAM ENGINE - FUZZING
# =============================================================================

class TestRedTeamEngineFuzzing:
    """Test fuzzing functionality."""
    
    def test_fuzz_artifact(self, engine, sample_pac):
        """Test fuzzing an artifact."""
        executions = engine.fuzz_artifact(
            sample_pac,
            ArtifactType.PAC,
            strict_validator,
            iterations=10,
        )
        
        assert len(executions) == 10
    
    def test_fuzz_finds_vulnerabilities(self, engine, sample_pac):
        """Test fuzzing finds vulnerabilities."""
        engine.fuzz_artifact(
            sample_pac,
            ArtifactType.PAC,
            permissive_validator,
            iterations=5,
        )
        
        vulns = engine.get_vulnerabilities()
        assert len(vulns) > 0


# =============================================================================
# TEST: RED TEAM ENGINE - REPORTING
# =============================================================================

class TestRedTeamEngineReporting:
    """Test reporting functionality."""
    
    def test_generate_report(self, engine, sample_pac):
        """Test report generation."""
        engine.generate_test_cases(sample_pac, ArtifactType.PAC, 10)
        engine.execute_tests(strict_validator)
        
        report = engine.generate_report()
        
        assert report.report_id.startswith("RT-")
        assert report.total_tests == 10
    
    def test_report_pass_rate(self, engine, sample_pac):
        """Test pass rate calculation."""
        engine.generate_test_cases(sample_pac, ArtifactType.PAC, 10)
        engine.execute_tests(strict_validator)
        
        report = engine.generate_report()
        assert report.pass_rate == 1.0
    
    def test_report_to_dict(self, engine, sample_pac):
        """Test report serialization."""
        engine.generate_test_cases(sample_pac, ArtifactType.PAC, 5)
        engine.execute_tests(strict_validator)
        
        report = engine.generate_report()
        data = report.to_dict()
        
        assert "total_tests" in data
        assert "vulnerabilities" in data
    
    def test_get_vulnerabilities_by_level(self, engine, sample_pac):
        """Test filtering vulnerabilities by level."""
        engine.generate_test_cases(sample_pac, ArtifactType.PAC, 10)
        engine.execute_tests(permissive_validator)
        
        high_vulns = engine.get_vulnerabilities(VulnerabilityLevel.HIGH)
        all_vulns = engine.get_vulnerabilities(VulnerabilityLevel.LOW)
        
        assert len(high_vulns) <= len(all_vulns)


# =============================================================================
# TEST: DATA CLASSES
# =============================================================================

class TestDataClasses:
    """Test data class functionality."""
    
    def test_mutation_to_dict(self):
        """Test mutation serialization."""
        mutation = Mutation(
            mutation_id="MUT-001",
            mutation_type=MutationType.FIELD_REMOVAL,
            target_field="title",
            original_value="Test",
            mutated_value=None,
            description="Remove title",
        )
        
        data = mutation.to_dict()
        assert data["mutation_id"] == "MUT-001"
    
    def test_test_execution_passed(self):
        """Test execution passed check."""
        test_case = MutationTestCase(
            test_id="TC-001",
            artifact_type=ArtifactType.PAC,
            original_artifact={},
            mutated_artifact={},
            mutation=Mutation("M", MutationType.FIELD_REMOVAL, "f", None, None, ""),
            expected_result=TestResult.PASSED,
            attack_vector=AttackVector.DATA_INTEGRITY,
        )
        
        execution = TestExecution(
            test_case=test_case,
            actual_result=TestResult.PASSED,
            execution_time_ms=1.0,
        )
        
        assert execution.passed is True
    
    def test_vulnerability_to_dict(self):
        """Test vulnerability serialization."""
        vuln = Vulnerability(
            vulnerability_id="VULN-001",
            level=VulnerabilityLevel.HIGH,
            attack_vector=AttackVector.DATA_INTEGRITY,
            artifact_type=ArtifactType.PAC,
            mutation_type=MutationType.HASH_TAMPERING,
            description="Hash bypass",
            reproduction_steps=["Step 1"],
            affected_fields=["hash"],
            recommendation="Add validation",
            discovered_at="2025-01-01T00:00:00Z",
        )
        
        data = vuln.to_dict()
        assert data["level"] == "HIGH"


# =============================================================================
# TEST: FACTORY FUNCTIONS
# =============================================================================

class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_red_team_engine(self):
        """Test engine creation."""
        engine = create_red_team_engine()
        assert isinstance(engine, RedTeamEngine)
    
    def test_create_sample_pac(self):
        """Test sample PAC creation."""
        pac = create_sample_pac()
        assert "pac_id" in pac
        assert "hash" in pac
    
    def test_create_sample_wrap(self):
        """Test sample WRAP creation."""
        wrap = create_sample_wrap()
        assert "wrap_id" in wrap
        assert "content_hash" in wrap
    
    def test_create_sample_ber(self):
        """Test sample BER creation."""
        ber = create_sample_ber()
        assert "ber_id" in ber
        assert "closure_id" in ber


# =============================================================================
# TEST: ENGINE RESET
# =============================================================================

class TestEngineReset:
    """Test engine reset."""
    
    def test_reset_clears_state(self, engine, sample_pac):
        """Test reset clears all state."""
        engine.generate_test_cases(sample_pac, ArtifactType.PAC, 5)
        engine.execute_tests(strict_validator)
        
        engine.reset()
        
        assert len(engine._test_cases) == 0
        assert len(engine._executions) == 0
        assert len(engine._vulnerabilities) == 0


# =============================================================================
# SUMMARY
# =============================================================================

"""
Test Summary:
- TestEnums: 5 tests
- TestExceptions: 3 tests
- TestMutationGenerator: 12 tests
- TestRedTeamEngineGeneration: 3 tests
- TestRedTeamEngineExecution: 4 tests
- TestRedTeamEngineFuzzing: 2 tests
- TestRedTeamEngineReporting: 4 tests
- TestDataClasses: 3 tests
- TestFactoryFunctions: 4 tests
- TestEngineReset: 1 test

Total: 41 tests (≥30 requirement met)
"""
