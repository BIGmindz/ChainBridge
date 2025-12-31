"""
Test Suite for Decision Confidence Engine.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-031
Agent: GID-10 (Maggie) — ML / RISK
Deliverable: ≥40 tests for Decision Confidence Engine
"""

import pytest
import hashlib
from datetime import datetime, timezone

from core.decisions.confidence_engine import (
    # Constants
    ENGINE_VERSION,
    DEFAULT_CONFIDENCE_THRESHOLD,
    # Enums
    ConfidenceLevel,
    ProofType,
    FactorCategory,
    DecisionType,
    # Exceptions
    ConfidenceError,
    InsufficientEvidenceError,
    InvalidProofError,
    CalculationError,
    ThresholdNotMetError,
    # Data Classes
    ProofArtifact,
    ConfidenceFactor,
    ConfidenceInterval,
    ReasoningStep,
    ConfidenceResult,
    # Core Classes
    ConfidenceCalculator,
    ExplanationGenerator,
    DecisionConfidenceEngine,
    # Factory Functions
    create_engine,
    create_proof,
    create_factor,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def engine() -> DecisionConfidenceEngine:
    """Create a fresh engine for testing."""
    return create_engine(min_evidence=1)


@pytest.fixture
def verified_proof() -> ProofArtifact:
    """Create a verified proof artifact."""
    content = "test content"
    proof = create_proof(
        ProofType.TEST_RESULT,
        source="test_suite",
        weight=1.0,
        content=content,
    )
    proof.verify(content)
    return proof


@pytest.fixture
def sample_factors() -> list[ConfidenceFactor]:
    """Create sample confidence factors."""
    return [
        create_factor("Test Coverage", FactorCategory.PROOF, 0.85, 1.0),
        create_factor("Code Review", FactorCategory.AUTHORITY, 0.90, 0.8),
        create_factor("Historical Success", FactorCategory.HISTORY, 0.75, 0.6),
    ]


# =============================================================================
# TEST: ENUMS
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_confidence_levels(self):
        """Test all confidence levels exist."""
        assert ConfidenceLevel.VERY_LOW.value == "VERY_LOW"
        assert ConfidenceLevel.LOW.value == "LOW"
        assert ConfidenceLevel.MEDIUM.value == "MEDIUM"
        assert ConfidenceLevel.HIGH.value == "HIGH"
        assert ConfidenceLevel.VERY_HIGH.value == "VERY_HIGH"
    
    def test_proof_types(self):
        """Test proof type enumeration."""
        assert ProofType.TEST_RESULT.value == "TEST_RESULT"
        assert ProofType.HASH_VERIFICATION.value == "HASH_VERIFICATION"
        assert ProofType.SIGNATURE.value == "SIGNATURE"
    
    def test_factor_categories(self):
        """Test factor category enumeration."""
        assert FactorCategory.PROOF.value == "PROOF"
        assert FactorCategory.CONTEXT.value == "CONTEXT"
        assert FactorCategory.CONSENSUS.value == "CONSENSUS"
    
    def test_decision_types(self):
        """Test decision type enumeration."""
        assert DecisionType.PAC_APPROVAL.value == "PAC_APPROVAL"
        assert DecisionType.BER_ISSUANCE.value == "BER_ISSUANCE"
        assert DecisionType.CLOSURE_VALIDATION.value == "CLOSURE_VALIDATION"


# =============================================================================
# TEST: EXCEPTIONS
# =============================================================================

class TestExceptions:
    """Test exception hierarchy."""
    
    def test_confidence_error_base(self):
        """Test base exception."""
        err = ConfidenceError("test")
        assert str(err) == "test"
    
    def test_insufficient_evidence_error(self):
        """Test insufficient evidence exception."""
        err = InsufficientEvidenceError(required=5, provided=2)
        assert err.required == 5
        assert err.provided == 2
        assert "required 5" in str(err)
    
    def test_invalid_proof_error(self):
        """Test invalid proof exception."""
        err = InvalidProofError("P-001", "hash mismatch")
        assert err.proof_id == "P-001"
        assert err.reason == "hash mismatch"
    
    def test_calculation_error(self):
        """Test calculation error."""
        err = CalculationError("aggregation", "division by zero")
        assert err.stage == "aggregation"
        assert err.reason == "division by zero"
    
    def test_threshold_not_met_error(self):
        """Test threshold not met exception."""
        err = ThresholdNotMetError(threshold=0.7, actual=0.5)
        assert err.threshold == 0.7
        assert err.actual == 0.5


# =============================================================================
# TEST: PROOF ARTIFACT
# =============================================================================

class TestProofArtifact:
    """Test ProofArtifact data class."""
    
    def test_proof_creation(self):
        """Test creating proof artifact."""
        proof = ProofArtifact(
            proof_id="P-001",
            proof_type=ProofType.TEST_RESULT,
            source="pytest",
            timestamp="2025-01-01T00:00:00Z",
            weight=0.8,
        )
        assert proof.proof_id == "P-001"
        assert proof.weight == 0.8
        assert proof.verified is False
    
    def test_proof_weight_validation(self):
        """Test weight must be 0.0-1.0."""
        with pytest.raises(ValueError):
            ProofArtifact(
                proof_id="P-001",
                proof_type=ProofType.TEST_RESULT,
                source="test",
                timestamp="2025-01-01T00:00:00Z",
                weight=1.5,  # Invalid
            )
    
    def test_proof_verification_success(self):
        """Test successful proof verification."""
        content = "test content"
        hash_val = hashlib.sha256(content.encode()).hexdigest()
        
        proof = ProofArtifact(
            proof_id="P-001",
            proof_type=ProofType.HASH_VERIFICATION,
            source="test",
            timestamp="2025-01-01T00:00:00Z",
            hash_value=hash_val,
        )
        
        assert proof.verify(content) is True
        assert proof.verified is True
    
    def test_proof_verification_failure(self):
        """Test failed proof verification."""
        proof = ProofArtifact(
            proof_id="P-001",
            proof_type=ProofType.HASH_VERIFICATION,
            source="test",
            timestamp="2025-01-01T00:00:00Z",
            hash_value="incorrect_hash",
        )
        
        assert proof.verify("content") is False
        assert proof.verified is False
    
    def test_proof_verification_no_hash(self):
        """Test verification with no hash returns False."""
        proof = ProofArtifact(
            proof_id="P-001",
            proof_type=ProofType.TEST_RESULT,
            source="test",
            timestamp="2025-01-01T00:00:00Z",
        )
        assert proof.verify("content") is False


# =============================================================================
# TEST: CONFIDENCE FACTOR
# =============================================================================

class TestConfidenceFactor:
    """Test ConfidenceFactor data class."""
    
    def test_factor_creation(self):
        """Test creating confidence factor."""
        factor = ConfidenceFactor(
            factor_id="F-001",
            name="Test Coverage",
            category=FactorCategory.PROOF,
            value=0.85,
            weight=1.0,
            explanation="Based on test results",
        )
        assert factor.name == "Test Coverage"
        assert factor.value == 0.85
    
    def test_factor_value_validation(self):
        """Test value must be 0.0-1.0."""
        with pytest.raises(ValueError):
            ConfidenceFactor(
                factor_id="F-001",
                name="Test",
                category=FactorCategory.PROOF,
                value=1.5,  # Invalid
                weight=1.0,
                explanation="test",
            )


# =============================================================================
# TEST: CONFIDENCE INTERVAL
# =============================================================================

class TestConfidenceInterval:
    """Test ConfidenceInterval data class."""
    
    def test_interval_creation(self):
        """Test creating confidence interval."""
        interval = ConfidenceInterval(
            lower=0.65,
            point_estimate=0.75,
            upper=0.85,
        )
        assert interval.point_estimate == 0.75
        assert interval.confidence_percentage == 95.0
    
    def test_interval_validation(self):
        """Test interval ordering validation."""
        with pytest.raises(ValueError):
            ConfidenceInterval(
                lower=0.8,
                point_estimate=0.5,  # Invalid: less than lower
                upper=0.9,
            )
    
    def test_interval_width(self):
        """Test interval width calculation."""
        interval = ConfidenceInterval(0.6, 0.75, 0.9)
        assert abs(interval.width - 0.3) < 1e-10  # Use approximate comparison for float
    
    def test_interval_contains(self):
        """Test interval containment check."""
        interval = ConfidenceInterval(0.6, 0.75, 0.9)
        assert interval.contains(0.75) is True
        assert interval.contains(0.5) is False
        assert interval.contains(0.95) is False


# =============================================================================
# TEST: REASONING STEP
# =============================================================================

class TestReasoningStep:
    """Test ReasoningStep data class."""
    
    def test_step_creation(self):
        """Test creating reasoning step."""
        step = ReasoningStep(
            step_number=1,
            description="Aggregate factors",
            input_values={"a": 0.8, "b": 0.9},
            output_value=0.85,
            formula="mean(a, b)",
        )
        assert step.step_number == 1
        assert step.output_value == 0.85
    
    def test_step_explanation(self):
        """Test step explanation generation."""
        step = ReasoningStep(
            step_number=1,
            description="Test step",
            input_values={"x": 0.5},
            output_value=0.5,
            formula="identity(x)",
        )
        explanation = step.to_explanation()
        assert "Step 1" in explanation
        assert "x=0.500" in explanation


# =============================================================================
# TEST: CONFIDENCE CALCULATOR
# =============================================================================

class TestConfidenceCalculator:
    """Test ConfidenceCalculator class."""
    
    def test_weighted_average_basic(self):
        """Test basic weighted average."""
        calc = ConfidenceCalculator()
        factors = [
            create_factor("A", FactorCategory.PROOF, 0.8, 1.0),
            create_factor("B", FactorCategory.PROOF, 0.6, 1.0),
        ]
        result = calc.calculate_weighted_average(factors)
        assert result == 0.7
    
    def test_weighted_average_empty(self):
        """Test weighted average with no factors."""
        calc = ConfidenceCalculator()
        result = calc.calculate_weighted_average([])
        assert result == 0.0
    
    def test_weighted_average_with_weights(self):
        """Test weighted average with different weights."""
        calc = ConfidenceCalculator()
        factors = [
            create_factor("A", FactorCategory.PROOF, 1.0, 2.0),  # weight 2
            create_factor("B", FactorCategory.PROOF, 0.0, 1.0),  # weight 1
        ]
        result = calc.calculate_weighted_average(factors)
        # (1.0 * 2 + 0.0 * 1) / 3 = 0.667
        assert abs(result - 0.667) < 0.01
    
    def test_bayesian_no_proofs(self):
        """Test Bayesian with no proofs returns prior."""
        calc = ConfidenceCalculator()
        result = calc.calculate_bayesian(0.5, [])
        assert result == 0.5
    
    def test_bayesian_with_verified_proofs(self):
        """Test Bayesian update with verified proofs."""
        calc = ConfidenceCalculator()
        
        proof = create_proof(ProofType.TEST_RESULT, "test", content="data")
        proof.verify("data")
        
        result = calc.calculate_bayesian(0.5, [proof])
        assert result > 0.5  # Should increase with verified proof
    
    def test_dempster_shafer_single_belief(self):
        """Test Dempster-Shafer with single belief."""
        calc = ConfidenceCalculator()
        beliefs = [(0.7, 0.9)]
        belief, plausibility = calc.calculate_dempster_shafer(beliefs)
        assert belief == 0.7
        assert plausibility == 0.9
    
    def test_dempster_shafer_empty(self):
        """Test Dempster-Shafer with no beliefs."""
        calc = ConfidenceCalculator()
        belief, plausibility = calc.calculate_dempster_shafer([])
        assert belief == 0.0
        assert plausibility == 1.0
    
    def test_confidence_interval_calculation(self):
        """Test confidence interval calculation."""
        calc = ConfidenceCalculator()
        interval = calc.calculate_confidence_interval(0.75, 100)
        
        assert interval.point_estimate == 0.75
        assert interval.lower < 0.75
        assert interval.upper > 0.75
    
    def test_score_to_level_very_low(self):
        """Test score to VERY_LOW level."""
        calc = ConfidenceCalculator()
        assert calc.score_to_level(0.1) == ConfidenceLevel.VERY_LOW
    
    def test_score_to_level_low(self):
        """Test score to LOW level."""
        calc = ConfidenceCalculator()
        assert calc.score_to_level(0.3) == ConfidenceLevel.LOW
    
    def test_score_to_level_medium(self):
        """Test score to MEDIUM level."""
        calc = ConfidenceCalculator()
        assert calc.score_to_level(0.5) == ConfidenceLevel.MEDIUM
    
    def test_score_to_level_high(self):
        """Test score to HIGH level."""
        calc = ConfidenceCalculator()
        assert calc.score_to_level(0.7) == ConfidenceLevel.HIGH
    
    def test_score_to_level_very_high(self):
        """Test score to VERY_HIGH level."""
        calc = ConfidenceCalculator()
        assert calc.score_to_level(0.9) == ConfidenceLevel.VERY_HIGH


# =============================================================================
# TEST: EXPLANATION GENERATOR
# =============================================================================

class TestExplanationGenerator:
    """Test ExplanationGenerator class."""
    
    def test_generate_very_high_explanation(self, sample_factors, verified_proof):
        """Test VERY_HIGH explanation generation."""
        gen = ExplanationGenerator()
        explanation = gen.generate_explanation(
            0.9, ConfidenceLevel.VERY_HIGH, sample_factors, [verified_proof]
        )
        assert "VERY HIGH" in explanation
        assert "90" in explanation
    
    def test_generate_low_explanation(self, sample_factors):
        """Test LOW explanation generation."""
        gen = ExplanationGenerator()
        low_factors = [create_factor("Weak", FactorCategory.PROOF, 0.3, 1.0)]
        explanation = gen.generate_explanation(
            0.3, ConfidenceLevel.LOW, low_factors, []
        )
        assert "LOW" in explanation
    
    def test_generate_reasoning_chain(self, sample_factors):
        """Test reasoning chain generation."""
        gen = ExplanationGenerator()
        chain = gen.generate_reasoning_chain(sample_factors, 0.83)
        
        assert len(chain) > 0
        assert chain[-1].output_value == 0.83


# =============================================================================
# TEST: DECISION CONFIDENCE ENGINE
# =============================================================================

class TestDecisionConfidenceEngine:
    """Test main DecisionConfidenceEngine class."""
    
    def test_engine_creation(self):
        """Test engine creation with defaults."""
        engine = create_engine()
        assert engine._min_evidence == 1
        assert engine._default_threshold == DEFAULT_CONFIDENCE_THRESHOLD
    
    def test_add_proof(self, engine, verified_proof):
        """Test adding proof to engine."""
        engine.add_proof(verified_proof)
        assert verified_proof.proof_id in engine._proofs
    
    def test_verify_proof(self, engine):
        """Test proof verification through engine."""
        content = "test data"
        proof = create_proof(ProofType.HASH_VERIFICATION, "test", content=content)
        engine.add_proof(proof)
        
        result = engine.verify_proof(proof.proof_id, content)
        assert result is True
    
    def test_verify_nonexistent_proof(self, engine):
        """Test verifying nonexistent proof raises error."""
        with pytest.raises(InvalidProofError):
            engine.verify_proof("NONEXISTENT", "content")
    
    def test_get_verified_proofs(self, engine, verified_proof):
        """Test getting verified proofs."""
        unverified = create_proof(ProofType.TEST_RESULT, "test")
        
        engine.add_proof(verified_proof)
        engine.add_proof(unverified)
        
        verified = engine.get_verified_proofs()
        assert len(verified) == 1
        assert verified[0].proof_id == verified_proof.proof_id
    
    def test_add_factor(self, engine):
        """Test adding factor to engine."""
        factor = create_factor("Test", FactorCategory.PROOF, 0.8)
        engine.add_factor(factor)
        assert len(engine._factors) == 1
    
    def test_calculate_confidence_basic(self, engine, sample_factors):
        """Test basic confidence calculation."""
        for f in sample_factors:
            engine.add_factor(f)
        
        result = engine.calculate_confidence(
            DecisionType.PAC_APPROVAL, "PAC-001"
        )
        
        assert result.confidence_score >= 0.0
        assert result.confidence_score <= 1.0
        assert result.result_id.startswith("CR-")
    
    def test_calculate_confidence_insufficient_evidence(self):
        """Test calculation fails with insufficient evidence."""
        engine = create_engine(min_evidence=5)
        
        with pytest.raises(InsufficientEvidenceError):
            engine.calculate_confidence(DecisionType.PAC_APPROVAL, "PAC-001")
    
    def test_calculate_confidence_bayesian(self, engine, verified_proof):
        """Test Bayesian calculation method."""
        engine.add_proof(verified_proof)
        engine.add_factor(create_factor("Test", FactorCategory.PROOF, 0.8))
        
        result = engine.calculate_confidence(
            DecisionType.PAC_APPROVAL, "PAC-001", method="bayesian"
        )
        assert result.confidence_score >= 0.0
    
    def test_require_confidence_passes(self, engine, sample_factors):
        """Test require_confidence when threshold met."""
        for f in sample_factors:
            engine.add_factor(f)
        
        # Should not raise
        result = engine.require_confidence(
            DecisionType.PAC_APPROVAL, "PAC-001", threshold=0.3
        )
        assert result is not None
    
    def test_require_confidence_fails(self, engine):
        """Test require_confidence raises when threshold not met."""
        engine.add_factor(create_factor("Low", FactorCategory.PROOF, 0.1))
        
        with pytest.raises(ThresholdNotMetError):
            engine.require_confidence(
                DecisionType.PAC_APPROVAL, "PAC-001", threshold=0.9
            )
    
    def test_reset(self, engine, verified_proof, sample_factors):
        """Test engine reset."""
        engine.add_proof(verified_proof)
        for f in sample_factors:
            engine.add_factor(f)
        
        engine.reset()
        
        assert len(engine._proofs) == 0
        assert len(engine._factors) == 0
    
    def test_result_meets_threshold(self, engine, sample_factors):
        """Test result threshold checking."""
        for f in sample_factors:
            engine.add_factor(f)
        
        result = engine.calculate_confidence(
            DecisionType.PAC_APPROVAL, "PAC-001"
        )
        
        # Check both property and method
        assert isinstance(result.meets_threshold, bool)
        assert result.check_threshold(0.0) is True
        assert result.check_threshold(1.0) is False
    
    def test_result_to_dict(self, engine, sample_factors):
        """Test result serialization."""
        for f in sample_factors:
            engine.add_factor(f)
        
        result = engine.calculate_confidence(
            DecisionType.PAC_APPROVAL, "PAC-001"
        )
        
        data = result.to_dict()
        assert "result_id" in data
        assert "confidence_score" in data
        assert "explanation" in data


# =============================================================================
# TEST: FACTORY FUNCTIONS
# =============================================================================

class TestFactoryFunctions:
    """Test factory function helpers."""
    
    def test_create_engine(self):
        """Test create_engine factory."""
        engine = create_engine(min_evidence=3, threshold=0.8)
        assert engine._min_evidence == 3
        assert engine._default_threshold == 0.8
    
    def test_create_proof(self):
        """Test create_proof factory."""
        proof = create_proof(
            ProofType.TEST_RESULT, "pytest", weight=0.9, content="data"
        )
        assert proof.proof_id.startswith("P-")
        assert proof.weight == 0.9
        assert proof.hash_value is not None
    
    def test_create_factor(self):
        """Test create_factor factory."""
        factor = create_factor(
            "Coverage", FactorCategory.PROOF, 0.85, 1.0, "Test coverage"
        )
        assert factor.factor_id.startswith("F-")
        assert factor.value == 0.85


# =============================================================================
# SUMMARY
# =============================================================================

"""
Test Summary:
- TestEnums: 4 tests
- TestExceptions: 5 tests
- TestProofArtifact: 5 tests
- TestConfidenceFactor: 2 tests
- TestConfidenceInterval: 4 tests
- TestReasoningStep: 2 tests
- TestConfidenceCalculator: 11 tests
- TestExplanationGenerator: 3 tests
- TestDecisionConfidenceEngine: 14 tests
- TestFactoryFunctions: 3 tests

Total: 53 tests (≥40 requirement met)
"""
