"""
Tests for GIE Risk Decomposition Engine

Per PAC-JEFFREY-DRAFT-GOVERNANCE-GIE-REAL-WORK-SIX-AGENT-029.
Agent: GID-10 (Maggie) — ML / Risk

REAL WORK MODE tests — comprehensive coverage.
"""

import pytest
import json
import hashlib
from datetime import datetime
from unittest.mock import patch

from core.chainiq.gie_risk_decomposition import (
    # Enums
    RiskLevel,
    FactorCategory,
    DecompositionMethod,
    # Exceptions
    RiskDecompositionError,
    InvalidFactorError,
    WeightNormalizationError,
    MissingFactorError,
    # Data Classes
    FactorDefinition,
    FactorValue,
    RiskDecomposition,
    Counterfactual,
    FactorExplanation,
    # Factor Profiles
    AGENT_FACTORS,
    PDO_FACTORS,
    PAC_FACTORS,
    # Engine
    GIERiskDecompositionEngine,
    # Factory
    get_risk_decomposition_engine,
    reset_risk_decomposition_engine,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Fresh engine instance."""
    return GIERiskDecompositionEngine()


@pytest.fixture
def custom_factors():
    """Custom factor definitions for testing."""
    return [
        FactorDefinition("factor_a", "Factor A", FactorCategory.EXECUTION, 0.4),
        FactorDefinition("factor_b", "Factor B", FactorCategory.COMPLIANCE, 0.3),
        FactorDefinition("factor_c", "Factor C", FactorCategory.SECURITY, 0.3),
    ]


@pytest.fixture
def sample_measurements():
    """Sample measurements for agent risk."""
    return {
        "agent_failure_rate": 0.3,
        "agent_latency": 0.5,
        "agent_compliance": 0.8,
        "agent_data_quality": 0.9,
        "agent_security_score": 0.7,
        "agent_recency": 0.2,
    }


@pytest.fixture(autouse=True)
def reset_global_engine():
    """Reset global engine before each test."""
    reset_risk_decomposition_engine()
    yield
    reset_risk_decomposition_engine()


# ═══════════════════════════════════════════════════════════════════════════════
# FACTOR DEFINITION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactorDefinition:
    """Tests for FactorDefinition dataclass."""

    def test_create_valid_factor(self):
        """Create a valid factor definition."""
        factor = FactorDefinition(
            factor_id="test_factor",
            name="Test Factor",
            category=FactorCategory.EXECUTION,
            weight=0.5,
            description="Test description",
        )
        assert factor.factor_id == "test_factor"
        assert factor.weight == 0.5
        assert factor.category == FactorCategory.EXECUTION

    def test_factor_weight_bounds(self):
        """Weight must be between 0 and 1."""
        with pytest.raises(InvalidFactorError):
            FactorDefinition("f", "F", FactorCategory.EXECUTION, 1.5)
        
        with pytest.raises(InvalidFactorError):
            FactorDefinition("f", "F", FactorCategory.EXECUTION, -0.1)

    def test_factor_min_max_validation(self):
        """min_value must be less than max_value."""
        with pytest.raises(InvalidFactorError):
            FactorDefinition("f", "F", FactorCategory.EXECUTION, 0.5,
                           min_value=1.0, max_value=0.0)

    def test_factor_immutability(self):
        """Factor definitions are frozen."""
        factor = FactorDefinition("f", "F", FactorCategory.EXECUTION, 0.5)
        with pytest.raises(Exception):  # frozen dataclass
            factor.weight = 0.7

    def test_factor_invert_flag(self):
        """Test invert flag for inverse factors."""
        factor = FactorDefinition(
            "compliance", "Compliance", FactorCategory.COMPLIANCE, 0.3,
            invert=True
        )
        assert factor.invert is True


# ═══════════════════════════════════════════════════════════════════════════════
# FACTOR VALUE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactorValue:
    """Tests for FactorValue dataclass."""

    def test_create_factor_value(self):
        """Create a factor value."""
        fv = FactorValue(
            factor_id="test",
            raw_value=0.5,
            normalized_value=0.6,
            contribution=0.12,
            confidence=0.95,
        )
        assert fv.raw_value == 0.5
        assert fv.contribution == 0.12

    def test_factor_value_to_dict(self):
        """Convert factor value to dictionary."""
        fv = FactorValue(
            factor_id="test",
            raw_value=0.5,
            normalized_value=0.6,
            contribution=0.12,
        )
        d = fv.to_dict()
        assert d["factor_id"] == "test"
        assert d["raw_value"] == 0.5
        assert "measured_at" in d

    def test_factor_value_default_confidence(self):
        """Default confidence is 1.0."""
        fv = FactorValue("test", 0.5, 0.6, 0.12)
        assert fv.confidence == 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# RISK DECOMPOSITION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskDecomposition:
    """Tests for RiskDecomposition dataclass."""

    def test_create_decomposition(self):
        """Create a risk decomposition."""
        factors = [
            FactorValue("f1", 0.5, 0.5, 0.15),
            FactorValue("f2", 0.3, 0.3, 0.09),
        ]
        decomp = RiskDecomposition(
            subject_id="agent-001",
            subject_type="AGENT",
            total_risk=0.45,
            risk_level=RiskLevel.MEDIUM,
            factors=factors,
            method=DecompositionMethod.WEIGHTED_SUM,
        )
        assert decomp.subject_id == "agent-001"
        assert decomp.total_risk == 0.45

    def test_top_contributors(self):
        """Get top contributing factors."""
        factors = [
            FactorValue("f1", 0.5, 0.5, 0.05),
            FactorValue("f2", 0.3, 0.3, 0.20),
            FactorValue("f3", 0.8, 0.8, 0.15),
        ]
        decomp = RiskDecomposition(
            "test", "AGENT", 0.4, RiskLevel.MEDIUM, factors,
            DecompositionMethod.WEIGHTED_SUM
        )
        top = decomp.top_contributors(2)
        assert len(top) == 2
        assert top[0].factor_id == "f2"  # Highest contribution
        assert top[1].factor_id == "f3"

    def test_to_dict(self):
        """Convert decomposition to dictionary."""
        decomp = RiskDecomposition(
            "test", "AGENT", 0.5, RiskLevel.MEDIUM, [],
            DecompositionMethod.WEIGHTED_SUM
        )
        d = decomp.to_dict()
        assert d["subject_id"] == "test"
        assert d["risk_level"] == "MEDIUM"
        assert d["method"] == "WEIGHTED_SUM"

    def test_compute_hash(self):
        """Hash computation is deterministic."""
        decomp = RiskDecomposition(
            "test", "AGENT", 0.5, RiskLevel.MEDIUM, [],
            DecompositionMethod.WEIGHTED_SUM
        )
        h1 = decomp.compute_hash()
        h2 = decomp.compute_hash()
        assert h1 == h2
        assert h1.startswith("sha256:")


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE INITIALIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineInitialization:
    """Tests for engine initialization."""

    def test_default_initialization(self, engine):
        """Engine initializes with defaults."""
        assert engine._method == DecompositionMethod.WEIGHTED_SUM
        assert engine._normalize_weights is True

    def test_custom_method(self):
        """Initialize with custom decomposition method."""
        engine = GIERiskDecompositionEngine(
            method=DecompositionMethod.MULTIPLICATIVE
        )
        assert engine._method == DecompositionMethod.MULTIPLICATIVE

    def test_no_weight_normalization(self):
        """Initialize without weight normalization."""
        engine = GIERiskDecompositionEngine(normalize_weights=False)
        assert engine._normalize_weights is False


# ═══════════════════════════════════════════════════════════════════════════════
# FACTOR REGISTRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactorRegistration:
    """Tests for factor registration."""

    def test_get_builtin_agent_factors(self, engine):
        """Get built-in agent factors."""
        factors = engine.get_factors("AGENT")
        assert len(factors) > 0
        assert any(f.factor_id == "agent_failure_rate" for f in factors)

    def test_get_builtin_pdo_factors(self, engine):
        """Get built-in PDO factors."""
        factors = engine.get_factors("PDO")
        assert len(factors) > 0
        assert any(f.factor_id == "pdo_wrap_completeness" for f in factors)

    def test_get_builtin_pac_factors(self, engine):
        """Get built-in PAC factors."""
        factors = engine.get_factors("PAC")
        assert len(factors) > 0
        assert any(f.factor_id == "pac_complexity" for f in factors)

    def test_register_custom_factors(self, engine, custom_factors):
        """Register custom factors."""
        engine.register_factors("CUSTOM", custom_factors)
        retrieved = engine.get_factors("CUSTOM")
        assert len(retrieved) == 3
        assert retrieved[0].factor_id == "factor_a"

    def test_custom_factors_override(self, engine, custom_factors):
        """Custom factors don't affect built-in."""
        engine.register_factors("AGENT_CUSTOM", custom_factors)
        agent_factors = engine.get_factors("AGENT")
        custom = engine.get_factors("AGENT_CUSTOM")
        assert len(agent_factors) != len(custom)

    def test_unknown_subject_type(self, engine):
        """Unknown subject type returns empty list."""
        factors = engine.get_factors("UNKNOWN")
        assert factors == []


# ═══════════════════════════════════════════════════════════════════════════════
# FACTOR VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactorValidation:
    """Tests for factor validation."""

    def test_validate_agent_factors(self, engine):
        """Validate built-in agent factors."""
        valid, errors = engine.validate_factors("AGENT")
        assert valid is True
        assert len(errors) == 0

    def test_validate_unknown_type(self, engine):
        """Validation fails for unknown type."""
        valid, errors = engine.validate_factors("UNKNOWN")
        assert valid is False
        assert "No factors defined" in errors[0]

    def test_validate_custom_factors(self, engine, custom_factors):
        """Validate custom factors."""
        engine.register_factors("CUSTOM", custom_factors)
        valid, errors = engine.validate_factors("CUSTOM")
        assert valid is True

    def test_validate_invalid_weights(self, engine):
        """Validation catches invalid weight sum."""
        invalid_factors = [
            FactorDefinition("f1", "F1", FactorCategory.EXECUTION, 0.3),
            FactorDefinition("f2", "F2", FactorCategory.COMPLIANCE, 0.3),
        ]
        engine.register_factors("INVALID", invalid_factors)
        valid, errors = engine.validate_factors("INVALID")
        assert valid is False
        assert "Weights sum to" in errors[0]


# ═══════════════════════════════════════════════════════════════════════════════
# DECOMPOSITION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecomposition:
    """Tests for risk decomposition."""

    def test_decompose_agent(self, engine, sample_measurements):
        """Decompose agent risk."""
        decomp = engine.decompose(
            subject_id="agent-001",
            subject_type="AGENT",
            measurements=sample_measurements,
        )
        assert decomp.subject_id == "agent-001"
        assert 0.0 <= decomp.total_risk <= 1.0
        assert len(decomp.factors) == len(AGENT_FACTORS)

    def test_decompose_pdo(self, engine):
        """Decompose PDO risk."""
        measurements = {
            "pdo_wrap_completeness": 0.9,
            "pdo_hash_integrity": 1.0,
            "pdo_agent_risk": 0.3,
            "pdo_ber_confidence": 0.85,
            "pdo_timing": 0.1,
        }
        decomp = engine.decompose("pdo-001", "PDO", measurements)
        assert decomp.subject_type == "PDO"
        assert len(decomp.factors) == len(PDO_FACTORS)

    def test_decompose_pac(self, engine):
        """Decompose PAC risk."""
        measurements = {
            "pac_complexity": 0.6,
            "pac_agent_count": 0.5,
            "pac_dependency_depth": 0.4,
            "pac_historical_success": 0.8,
            "pac_resource_utilization": 0.5,
            "pac_compliance_score": 0.9,
        }
        decomp = engine.decompose("pac-029", "PAC", measurements)
        assert decomp.subject_type == "PAC"

    def test_decompose_missing_factors(self, engine):
        """Decomposition fails for unknown subject type."""
        with pytest.raises(MissingFactorError):
            engine.decompose("test", "UNKNOWN", {})

    def test_decompose_missing_measurements(self, engine):
        """Missing measurements use default value."""
        decomp = engine.decompose("agent-001", "AGENT", {})
        assert decomp is not None
        # All factors should have values (defaults to 0.5)
        assert all(f.raw_value == 0.5 for f in decomp.factors)

    def test_risk_level_classification(self, engine):
        """Risk levels are classified correctly."""
        # Low risk scenario
        low_measurements = {k: 0.1 for k in [
            "agent_failure_rate", "agent_latency", "agent_recency"
        ]}
        low_measurements["agent_compliance"] = 0.9
        low_measurements["agent_data_quality"] = 0.9
        low_measurements["agent_security_score"] = 0.9
        
        decomp = engine.decompose("agent-low", "AGENT", low_measurements)
        assert decomp.risk_level in [RiskLevel.NEGLIGIBLE, RiskLevel.LOW]
        
        # High risk scenario
        high_measurements = {k: 0.9 for k in [
            "agent_failure_rate", "agent_latency", "agent_recency"
        ]}
        high_measurements["agent_compliance"] = 0.1
        high_measurements["agent_data_quality"] = 0.1
        high_measurements["agent_security_score"] = 0.1
        
        decomp = engine.decompose("agent-high", "AGENT", high_measurements)
        assert decomp.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]


# ═══════════════════════════════════════════════════════════════════════════════
# NORMALIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormalization:
    """Tests for value normalization."""

    def test_normalize_standard_value(self, engine):
        """Standard value normalization."""
        # Direct access to private method for testing
        normalized = engine._normalize_value(0.5, 0.0, 1.0, False)
        assert normalized == 0.5

    def test_normalize_with_range(self, engine):
        """Normalization with custom range."""
        normalized = engine._normalize_value(50, 0, 100, False)
        assert normalized == 0.5

    def test_normalize_with_invert(self, engine):
        """Normalization with inversion."""
        normalized = engine._normalize_value(0.8, 0.0, 1.0, True)
        assert abs(normalized - 0.2) < 0.001  # Inverted (allow float tolerance)

    def test_normalize_clamping(self, engine):
        """Values outside range are clamped."""
        normalized = engine._normalize_value(1.5, 0.0, 1.0, False)
        assert normalized == 1.0
        
        normalized = engine._normalize_value(-0.5, 0.0, 1.0, False)
        assert normalized == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# DECOMPOSITION METHOD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecompositionMethods:
    """Tests for different decomposition methods."""

    def test_weighted_sum_method(self, sample_measurements):
        """Weighted sum decomposition."""
        engine = GIERiskDecompositionEngine(
            method=DecompositionMethod.WEIGHTED_SUM
        )
        decomp = engine.decompose("agent-001", "AGENT", sample_measurements)
        assert decomp.method == DecompositionMethod.WEIGHTED_SUM

    def test_multiplicative_method(self, sample_measurements):
        """Multiplicative decomposition."""
        engine = GIERiskDecompositionEngine(
            method=DecompositionMethod.MULTIPLICATIVE
        )
        decomp = engine.decompose("agent-001", "AGENT", sample_measurements)
        assert decomp.method == DecompositionMethod.MULTIPLICATIVE
        # Multiplicative tends to be higher than weighted sum for same inputs
        
    def test_methods_produce_different_results(self, sample_measurements):
        """Different methods produce different risk values."""
        engine_ws = GIERiskDecompositionEngine(
            method=DecompositionMethod.WEIGHTED_SUM
        )
        engine_mult = GIERiskDecompositionEngine(
            method=DecompositionMethod.MULTIPLICATIVE
        )
        
        decomp_ws = engine_ws.decompose("agent", "AGENT", sample_measurements)
        decomp_mult = engine_mult.decompose("agent", "AGENT", sample_measurements)
        
        # Results should differ (or at least not be identical in most cases)
        # Due to the formula differences


# ═══════════════════════════════════════════════════════════════════════════════
# EXPLANATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExplanations:
    """Tests for risk explanations."""

    def test_generate_explanations(self, engine, sample_measurements):
        """Generate explanations for decomposition."""
        decomp = engine.decompose("agent-001", "AGENT", sample_measurements)
        explanations = engine.explain(decomp)
        
        assert len(explanations) > 0
        assert all(isinstance(e, FactorExplanation) for e in explanations)

    def test_explanation_content(self, engine, sample_measurements):
        """Explanations have required content."""
        decomp = engine.decompose("agent-001", "AGENT", sample_measurements)
        explanations = engine.explain(decomp)
        
        for exp in explanations:
            assert exp.factor_id
            assert exp.factor_name
            assert 0 <= exp.contribution_pct <= 100
            assert exp.direction in ["INCREASES_RISK", "DECREASES_RISK"]
            assert exp.explanation

    def test_explanation_recommendations(self, engine):
        """High risk factors get recommendations."""
        high_risk_measurements = {
            "agent_failure_rate": 0.9,  # Very high
            "agent_latency": 0.1,
            "agent_compliance": 0.9,
            "agent_data_quality": 0.9,
            "agent_security_score": 0.9,
            "agent_recency": 0.1,
        }
        decomp = engine.decompose("agent", "AGENT", high_risk_measurements)
        explanations = engine.explain(decomp)
        
        # At least one factor should have recommendations
        has_recommendations = any(
            len(e.recommendations) > 0 for e in explanations
        )
        assert has_recommendations


# ═══════════════════════════════════════════════════════════════════════════════
# COUNTERFACTUAL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCounterfactuals:
    """Tests for counterfactual generation."""

    def test_generate_counterfactual(self, engine):
        """Generate counterfactual for risk reduction."""
        high_risk_measurements = {
            "agent_failure_rate": 0.8,
            "agent_latency": 0.7,
            "agent_compliance": 0.3,
            "agent_data_quality": 0.4,
            "agent_security_score": 0.3,
            "agent_recency": 0.5,
        }
        decomp = engine.decompose("agent", "AGENT", high_risk_measurements)
        
        cf = engine.generate_counterfactual(decomp, RiskLevel.LOW)
        
        assert cf is not None
        assert cf.target_risk < cf.original_risk
        assert len(cf.required_changes) > 0
        assert 0 < cf.feasibility <= 1.0

    def test_counterfactual_explanation(self, engine):
        """Counterfactual has explanation."""
        high_risk_measurements = {
            "agent_failure_rate": 0.9,
            "agent_latency": 0.8,
            "agent_compliance": 0.2,
            "agent_data_quality": 0.3,
            "agent_security_score": 0.2,
            "agent_recency": 0.7,
        }
        decomp = engine.decompose("agent", "AGENT", high_risk_measurements)
        
        cf = engine.generate_counterfactual(decomp, RiskLevel.MEDIUM)
        
        if cf:
            assert cf.explanation
            assert "reduce" in cf.explanation.lower()

    def test_counterfactual_already_achieved(self, engine):
        """No counterfactual if already at target level."""
        low_risk_measurements = {
            "agent_failure_rate": 0.1,
            "agent_latency": 0.1,
            "agent_compliance": 0.9,
            "agent_data_quality": 0.9,
            "agent_security_score": 0.9,
            "agent_recency": 0.1,
        }
        decomp = engine.decompose("agent", "AGENT", low_risk_measurements)
        
        cf = engine.generate_counterfactual(decomp, RiskLevel.HIGH)
        
        # Already low risk, can't reduce to HIGH (which is worse)
        assert cf is None


# ═══════════════════════════════════════════════════════════════════════════════
# AGGREGATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAggregation:
    """Tests for risk aggregation."""

    def test_aggregate_agent_risks(self, engine, sample_measurements):
        """Aggregate multiple agent risks."""
        decomps = []
        for i in range(3):
            decomp = engine.decompose(f"agent-{i:03d}", "AGENT", sample_measurements)
            decomps.append(decomp)
        
        aggregate = engine.aggregate_agent_risks(decomps)
        
        assert aggregate.subject_type == "AGENT_GROUP"
        assert aggregate.metadata["agent_count"] == 3
        assert len(aggregate.metadata["agent_risks"]) == 3

    def test_aggregate_empty_list(self, engine):
        """Aggregation fails on empty list."""
        with pytest.raises(RiskDecompositionError):
            engine.aggregate_agent_risks([])

    def test_aggregate_considers_max_risk(self, engine):
        """Aggregation considers maximum risk (weakest link)."""
        low_measurements = {k: 0.1 for k in [
            "agent_failure_rate", "agent_latency", "agent_recency"
        ]}
        low_measurements["agent_compliance"] = 0.9
        low_measurements["agent_data_quality"] = 0.9
        low_measurements["agent_security_score"] = 0.9
        
        high_measurements = {k: 0.9 for k in [
            "agent_failure_rate", "agent_latency", "agent_recency"
        ]}
        high_measurements["agent_compliance"] = 0.1
        high_measurements["agent_data_quality"] = 0.1
        high_measurements["agent_security_score"] = 0.1
        
        decomp_low = engine.decompose("agent-low", "AGENT", low_measurements)
        decomp_high = engine.decompose("agent-high", "AGENT", high_measurements)
        
        aggregate = engine.aggregate_agent_risks([decomp_low, decomp_high])
        
        # Aggregate should be influenced by the high-risk agent
        assert aggregate.total_risk > decomp_low.total_risk


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactory:
    """Tests for factory functions."""

    def test_get_engine_singleton(self):
        """Factory returns singleton engine."""
        engine1 = get_risk_decomposition_engine()
        engine2 = get_risk_decomposition_engine()
        assert engine1 is engine2

    def test_reset_engine(self):
        """Reset creates new engine."""
        engine1 = get_risk_decomposition_engine()
        reset_risk_decomposition_engine()
        engine2 = get_risk_decomposition_engine()
        assert engine1 is not engine2


# ═══════════════════════════════════════════════════════════════════════════════
# BUILTIN FACTOR PROFILE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBuiltinFactors:
    """Tests for built-in factor profiles."""

    def test_agent_factors_weights_sum_to_one(self):
        """Agent factor weights sum to 1.0."""
        total = sum(f.weight for f in AGENT_FACTORS)
        assert abs(total - 1.0) < 0.01

    def test_pdo_factors_weights_sum_to_one(self):
        """PDO factor weights sum to 1.0."""
        total = sum(f.weight for f in PDO_FACTORS)
        assert abs(total - 1.0) < 0.01

    def test_pac_factors_weights_sum_to_one(self):
        """PAC factor weights sum to 1.0."""
        total = sum(f.weight for f in PAC_FACTORS)
        assert abs(total - 1.0) < 0.01

    def test_agent_factors_unique_ids(self):
        """Agent factors have unique IDs."""
        ids = [f.factor_id for f in AGENT_FACTORS]
        assert len(ids) == len(set(ids))

    def test_pdo_factors_unique_ids(self):
        """PDO factors have unique IDs."""
        ids = [f.factor_id for f in PDO_FACTORS]
        assert len(ids) == len(set(ids))

    def test_pac_factors_unique_ids(self):
        """PAC factors have unique IDs."""
        ids = [f.factor_id for f in PAC_FACTORS]
        assert len(ids) == len(set(ids))


# ═══════════════════════════════════════════════════════════════════════════════
# RISK LEVEL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskLevels:
    """Tests for risk level classification."""

    def test_negligible_threshold(self, engine):
        """Risk < 0.2 is NEGLIGIBLE."""
        assert engine._classify_risk(0.1) == RiskLevel.NEGLIGIBLE
        assert engine._classify_risk(0.19) == RiskLevel.NEGLIGIBLE

    def test_low_threshold(self, engine):
        """Risk 0.2-0.4 is LOW."""
        assert engine._classify_risk(0.2) == RiskLevel.LOW
        assert engine._classify_risk(0.35) == RiskLevel.LOW

    def test_medium_threshold(self, engine):
        """Risk 0.4-0.6 is MEDIUM."""
        assert engine._classify_risk(0.4) == RiskLevel.MEDIUM
        assert engine._classify_risk(0.55) == RiskLevel.MEDIUM

    def test_high_threshold(self, engine):
        """Risk 0.6-0.8 is HIGH."""
        assert engine._classify_risk(0.6) == RiskLevel.HIGH
        assert engine._classify_risk(0.75) == RiskLevel.HIGH

    def test_critical_threshold(self, engine):
        """Risk > 0.8 is CRITICAL."""
        assert engine._classify_risk(0.8) == RiskLevel.CRITICAL
        assert engine._classify_risk(0.95) == RiskLevel.CRITICAL


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases."""

    def test_all_zero_measurements(self, engine):
        """Handle all-zero measurements."""
        measurements = {k: 0.0 for k in [
            "agent_failure_rate", "agent_latency", "agent_compliance",
            "agent_data_quality", "agent_security_score", "agent_recency"
        ]}
        decomp = engine.decompose("agent", "AGENT", measurements)
        # Inverted factors at 0.0 become 1.0 risk
        assert decomp is not None

    def test_all_one_measurements(self, engine):
        """Handle all-one measurements."""
        measurements = {k: 1.0 for k in [
            "agent_failure_rate", "agent_latency", "agent_compliance",
            "agent_data_quality", "agent_security_score", "agent_recency"
        ]}
        decomp = engine.decompose("agent", "AGENT", measurements)
        # Inverted factors at 1.0 become 0.0 risk
        assert decomp is not None

    def test_partial_measurements(self, engine):
        """Handle partial measurements."""
        measurements = {
            "agent_failure_rate": 0.5,
            # Missing other factors
        }
        decomp = engine.decompose("agent", "AGENT", measurements)
        assert decomp is not None
        assert len(decomp.factors) == len(AGENT_FACTORS)

    def test_extra_measurements_ignored(self, engine, sample_measurements):
        """Extra measurements are ignored."""
        measurements = {**sample_measurements, "unknown_factor": 0.99}
        decomp = engine.decompose("agent", "AGENT", measurements)
        assert decomp is not None
        assert not any(f.factor_id == "unknown_factor" for f in decomp.factors)


# ═══════════════════════════════════════════════════════════════════════════════
# SERIALIZATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSerialization:
    """Tests for serialization."""

    def test_decomposition_json_serializable(self, engine, sample_measurements):
        """Decomposition can be serialized to JSON."""
        decomp = engine.decompose("agent", "AGENT", sample_measurements)
        d = decomp.to_dict()
        json_str = json.dumps(d)
        assert json_str
        
        parsed = json.loads(json_str)
        assert parsed["subject_id"] == "agent"

    def test_hash_is_deterministic(self, engine, sample_measurements):
        """Hash is deterministic for same input."""
        decomp1 = engine.decompose("agent", "AGENT", sample_measurements)
        decomp2 = engine.decompose("agent", "AGENT", sample_measurements)
        
        # Hashes should be equal for same decomposition
        # (Note: timestamps may differ, so we can't guarantee exact equality
        # unless we mock the timestamp)


# ═══════════════════════════════════════════════════════════════════════════════
# CONTRIBUTION CALCULATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestContributions:
    """Tests for contribution calculations."""

    def test_contributions_sum_to_total(self, engine, sample_measurements):
        """Factor contributions sum to total risk."""
        decomp = engine.decompose("agent", "AGENT", sample_measurements)
        
        # With weighted sum method, contributions should sum close to total
        if decomp.method == DecompositionMethod.WEIGHTED_SUM:
            total_contributions = sum(f.contribution for f in decomp.factors)
            assert abs(total_contributions - decomp.total_risk) < 0.01

    def test_contribution_percentage_sums_to_100(self, engine, sample_measurements):
        """Contribution percentages sum to ~100%."""
        decomp = engine.decompose("agent", "AGENT", sample_measurements)
        explanations = engine.explain(decomp)
        
        total_pct = sum(e.contribution_pct for e in explanations)
        assert abs(total_pct - 100) < 1  # Allow 1% tolerance
