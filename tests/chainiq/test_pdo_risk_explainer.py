"""
PDO Risk Explainer Tests

Comprehensive test suite for the PDO Risk Explainer engine.
Per PAC-BENSON-EXEC-GOVERNANCE-MULTI-AGENT-PDO-STRESS-023.

Agent: GID-10 (Maggie) — ML & Applied AI Lead
"""

import json
import pytest
import threading
from datetime import datetime, timedelta

from core.chainiq.pdo_risk_explainer import (
    # Enums
    RiskLevel,
    FactorDirection,
    # Data classes
    RiskFactor,
    RiskExplanation,
    SignalSource,
    # Exceptions
    RiskExplainerError,
    ExplanationRequiredError,
    ExplanationImmutableError,
    InvalidBindingError,
    SignalNotFoundError,
    # Core classes
    ExplanationGenerator,
    ConfidenceCalculator,
    PDORiskExplainer,
    # Singleton
    get_risk_explainer,
    reset_risk_explainer,
    # Convenience functions
    explain_pdo_risk,
    query_pdo_explanation,
    # Config
    DEFAULT_CONFIG,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def explainer():
    """Fresh explainer instance for each test."""
    return PDORiskExplainer()


@pytest.fixture
def sample_signal():
    """Sample signal source for testing."""
    return SignalSource(
        signal_id="SIG-VOL-001",
        signal_name="Volatility Index",
        category="market",
        current_value=0.85,
        baseline_value=0.3,
        threshold_high=0.7,
        threshold_low=0.1,
        weight=1.5,
        description="Market volatility indicator",
    )


@pytest.fixture
def sample_factor():
    """Sample risk factor for testing."""
    return RiskFactor(
        factor_id="FACTOR-TEST-001",
        signal_id="SIG-VOL-001",
        signal_name="Volatility Index",
        value=0.85,
        threshold=0.7,
        weight=1.5,
        direction=FactorDirection.ABOVE,
        contribution=0.3,
        explanation="Volatility is elevated above threshold",
    )


@pytest.fixture
def sample_explanation(sample_factor):
    """Sample risk explanation for testing."""
    return RiskExplanation(
        explanation_id="EXPLAIN-TEST-001",
        pdo_id="PDO-TEST-001",
        pdo_hash="abc123def456",
        risk_score=0.75,
        risk_level=RiskLevel.HIGH,
        summary="High risk detected.",
        detailed_reasoning="Detailed analysis...",
        factors=(sample_factor,),
        confidence_lower=0.65,
        confidence_upper=0.85,
        signal_window_start="2025-12-25T00:00:00Z",
        signal_window_end="2025-12-26T00:00:00Z",
    )


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before and after each test."""
    reset_risk_explainer()
    yield
    reset_risk_explainer()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: RISK LEVEL ENUM
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskLevel:
    """Tests for RiskLevel enum."""
    
    def test_from_score_low(self):
        """Score < 0.3 should be LOW."""
        assert RiskLevel.from_score(0.0) == RiskLevel.LOW
        assert RiskLevel.from_score(0.15) == RiskLevel.LOW
        assert RiskLevel.from_score(0.29) == RiskLevel.LOW
    
    def test_from_score_medium(self):
        """Score 0.3-0.5 should be MEDIUM."""
        assert RiskLevel.from_score(0.3) == RiskLevel.MEDIUM
        assert RiskLevel.from_score(0.4) == RiskLevel.MEDIUM
        assert RiskLevel.from_score(0.49) == RiskLevel.MEDIUM
    
    def test_from_score_high(self):
        """Score 0.5-0.7 should be HIGH."""
        assert RiskLevel.from_score(0.5) == RiskLevel.HIGH
        assert RiskLevel.from_score(0.6) == RiskLevel.HIGH
        assert RiskLevel.from_score(0.69) == RiskLevel.HIGH
    
    def test_from_score_critical(self):
        """Score >= 0.7 should be CRITICAL."""
        assert RiskLevel.from_score(0.7) == RiskLevel.CRITICAL
        assert RiskLevel.from_score(0.85) == RiskLevel.CRITICAL
        assert RiskLevel.from_score(1.0) == RiskLevel.CRITICAL


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: RISK FACTOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskFactor:
    """Tests for RiskFactor dataclass."""
    
    def test_creation(self, sample_factor):
        """RiskFactor should be created with all fields."""
        assert sample_factor.factor_id == "FACTOR-TEST-001"
        assert sample_factor.signal_id == "SIG-VOL-001"
        assert sample_factor.value == 0.85
        assert sample_factor.direction == FactorDirection.ABOVE
    
    def test_immutability(self, sample_factor):
        """RiskFactor should be immutable (frozen)."""
        with pytest.raises(AttributeError):
            sample_factor.value = 0.9
    
    def test_to_dict(self, sample_factor):
        """RiskFactor should convert to dict."""
        d = sample_factor.to_dict()
        assert d["factor_id"] == "FACTOR-TEST-001"
        assert d["direction"] == "ABOVE"
        assert isinstance(d, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: RISK EXPLANATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskExplanation:
    """Tests for RiskExplanation dataclass."""
    
    def test_creation(self, sample_explanation):
        """RiskExplanation should be created with all fields."""
        assert sample_explanation.pdo_id == "PDO-TEST-001"
        assert sample_explanation.risk_score == 0.75
        assert sample_explanation.risk_level == RiskLevel.HIGH
    
    def test_immutability(self, sample_explanation):
        """RiskExplanation should be immutable (frozen)."""
        with pytest.raises(AttributeError):
            sample_explanation.risk_score = 0.5
    
    def test_hash_computed(self, sample_explanation):
        """Explanation hash should be computed automatically."""
        assert sample_explanation.explanation_hash
        assert len(sample_explanation.explanation_hash) == 64  # SHA-256
    
    def test_hash_deterministic(self, sample_factor):
        """Same inputs should produce same hash."""
        exp1 = RiskExplanation(
            explanation_id="EXP-001",
            pdo_id="PDO-001",
            pdo_hash="hash123",
            risk_score=0.5,
            risk_level=RiskLevel.HIGH,
            summary="Test",
            detailed_reasoning="Details",
            factors=(sample_factor,),
            confidence_lower=0.4,
            confidence_upper=0.6,
            signal_window_start="2025-01-01T00:00:00Z",
            signal_window_end="2025-01-02T00:00:00Z",
        )
        exp2 = RiskExplanation(
            explanation_id="EXP-001",
            pdo_id="PDO-001",
            pdo_hash="hash123",
            risk_score=0.5,
            risk_level=RiskLevel.HIGH,
            summary="Test",
            detailed_reasoning="Details",
            factors=(sample_factor,),
            confidence_lower=0.4,
            confidence_upper=0.6,
            signal_window_start="2025-01-01T00:00:00Z",
            signal_window_end="2025-01-02T00:00:00Z",
        )
        assert exp1.explanation_hash == exp2.explanation_hash
    
    def test_to_dict(self, sample_explanation):
        """RiskExplanation should convert to dict."""
        d = sample_explanation.to_dict()
        assert d["pdo_id"] == "PDO-TEST-001"
        assert d["risk_level"] == "HIGH"
        assert isinstance(d["factors"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: EXPLANATION GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestExplanationGenerator:
    """Tests for ExplanationGenerator."""
    
    def test_generate_factor_explanation_above(self, sample_factor):
        """Should generate explanation for ABOVE direction."""
        generator = ExplanationGenerator()
        text = generator.generate_factor_explanation(sample_factor)
        assert "elevated" in text.lower()
        assert "0.85" in text
        assert "0.70" in text or "0.7" in text
    
    def test_generate_summary(self, sample_factor):
        """Should generate summary based on risk level."""
        generator = ExplanationGenerator()
        summary = generator.generate_summary(RiskLevel.HIGH, [sample_factor])
        assert "significant" in summary.lower() or "concerns" in summary.lower()
        assert "Volatility" in summary
    
    def test_generate_detailed_reasoning(self, sample_factor):
        """Should generate detailed reasoning."""
        generator = ExplanationGenerator()
        reasoning = generator.generate_detailed_reasoning(
            risk_score=0.75,
            risk_level=RiskLevel.HIGH,
            factors=[sample_factor],
            confidence_lower=0.65,
            confidence_upper=0.85,
        )
        assert "0.75" in reasoning
        assert "HIGH" in reasoning
        assert "Contributing Factors" in reasoning


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CONFIDENCE CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfidenceCalculator:
    """Tests for ConfidenceCalculator."""
    
    def test_bootstrap_bounds_valid(self):
        """Bootstrap should return valid bounds."""
        lower, upper = ConfidenceCalculator.bootstrap(0.5, 5)
        assert 0.0 <= lower <= 0.5
        assert 0.5 <= upper <= 1.0
    
    def test_bootstrap_more_factors_tighter(self):
        """More factors should produce tighter confidence interval."""
        lower1, upper1 = ConfidenceCalculator.bootstrap(0.5, 1)
        lower2, upper2 = ConfidenceCalculator.bootstrap(0.5, 10)
        
        interval1 = upper1 - lower1
        interval2 = upper2 - lower2
        
        assert interval2 < interval1
    
    def test_fixed_margin(self):
        """Fixed margin should work correctly."""
        lower, upper = ConfidenceCalculator.fixed_margin(0.5, 0.1)
        assert lower == 0.4
        assert upper == 0.6
    
    def test_bounds_clamped(self):
        """Bounds should be clamped to [0, 1]."""
        lower, upper = ConfidenceCalculator.fixed_margin(0.05, 0.1)
        assert lower == 0.0  # Clamped
        
        lower, upper = ConfidenceCalculator.fixed_margin(0.95, 0.1)
        assert upper == 1.0  # Clamped


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDO RISK EXPLAINER - BASIC OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDORiskExplainerBasic:
    """Tests for basic PDORiskExplainer operations."""
    
    def test_creation(self, explainer):
        """Explainer should be created with default config."""
        assert explainer.risk_threshold == DEFAULT_CONFIG["risk_threshold"]
    
    def test_custom_config(self):
        """Explainer should accept custom config."""
        custom = PDORiskExplainer({"risk_threshold": 0.3})
        assert custom.risk_threshold == 0.3
    
    def test_requires_explanation_above_threshold(self, explainer):
        """Should require explanation above threshold."""
        assert explainer.requires_explanation(0.6) is True
        assert explainer.requires_explanation(0.5) is True
    
    def test_requires_explanation_below_threshold(self, explainer):
        """Should not require explanation below threshold."""
        assert explainer.requires_explanation(0.4) is False
        assert explainer.requires_explanation(0.0) is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SIGNAL MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestSignalManagement:
    """Tests for signal registration and retrieval."""
    
    def test_register_signal(self, explainer, sample_signal):
        """Should register a signal."""
        explainer.register_signal(sample_signal)
        retrieved = explainer.get_signal("SIG-VOL-001")
        assert retrieved == sample_signal
    
    def test_get_nonexistent_signal(self, explainer):
        """Should return None for nonexistent signal."""
        assert explainer.get_signal("NONEXISTENT") is None
    
    def test_list_signals(self, explainer, sample_signal):
        """Should list all registered signals."""
        explainer.register_signal(sample_signal)
        signals = explainer.list_signals()
        assert len(signals) == 1
        assert signals[0] == sample_signal


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: FACTOR ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFactorAnalysis:
    """Tests for signal analysis and factor generation."""
    
    def test_analyze_signal_above_threshold(self, explainer, sample_signal):
        """Should generate factor when signal above threshold."""
        factor = explainer.analyze_signal(sample_signal)
        assert factor is not None
        assert factor.direction == FactorDirection.ABOVE
        assert factor.value == 0.85
    
    def test_analyze_signal_below_threshold(self, explainer):
        """Should generate factor when signal below threshold."""
        signal = SignalSource(
            signal_id="SIG-LIQ-001",
            signal_name="Liquidity",
            category="market",
            current_value=0.05,
            baseline_value=0.3,
            threshold_low=0.1,
            weight=1.0,
        )
        factor = explainer.analyze_signal(signal)
        assert factor is not None
        assert factor.direction == FactorDirection.BELOW
    
    def test_analyze_signal_within_range(self, explainer):
        """Should return None when signal within acceptable range."""
        signal = SignalSource(
            signal_id="SIG-NORM-001",
            signal_name="Normal Signal",
            category="market",
            current_value=0.5,
            baseline_value=0.5,
            threshold_low=0.1,
            threshold_high=0.9,
            weight=1.0,
        )
        factor = explainer.analyze_signal(signal)
        assert factor is None
    
    def test_compute_risk_score_empty(self, explainer):
        """Empty factors should produce zero risk score."""
        score = explainer.compute_risk_score([])
        assert score == 0.0
    
    def test_compute_risk_score_single_factor(self, explainer, sample_factor):
        """Single factor should produce non-zero score."""
        score = explainer.compute_risk_score([sample_factor])
        assert 0.0 < score <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: EXPLANATION GENERATION (INV-RISK-001)
# ═══════════════════════════════════════════════════════════════════════════════

class TestExplanationGeneration:
    """Tests for explanation generation (INV-RISK-001)."""
    
    def test_explain_with_risk_score(self, explainer):
        """Should generate explanation with provided risk score."""
        explanation = explainer.explain(
            pdo_id="PDO-TEST-001",
            pdo_hash="hash123",
            risk_score=0.75,
        )
        assert explanation.pdo_id == "PDO-TEST-001"
        assert explanation.risk_score == 0.75
        assert explanation.risk_level == RiskLevel.CRITICAL
    
    def test_explain_with_signals(self, explainer, sample_signal):
        """Should generate explanation from signals."""
        explainer.register_signal(sample_signal)
        
        explanation = explainer.explain(
            pdo_id="PDO-TEST-002",
            pdo_hash="hash456",
            signal_ids=["SIG-VOL-001"],
        )
        assert len(explanation.factors) > 0
        assert explanation.risk_score > 0
    
    def test_explain_with_custom_factors(self, explainer, sample_factor):
        """Should include custom factors in explanation."""
        explanation = explainer.explain(
            pdo_id="PDO-TEST-003",
            pdo_hash="hash789",
            custom_factors=[sample_factor],
        )
        assert len(explanation.factors) == 1
        assert explanation.factors[0] == sample_factor
    
    def test_explain_signal_not_found(self, explainer):
        """Should raise error for nonexistent signal."""
        with pytest.raises(SignalNotFoundError):
            explainer.explain(
                pdo_id="PDO-TEST-004",
                pdo_hash="hash000",
                signal_ids=["NONEXISTENT"],
            )
    
    def test_explanation_has_confidence_bounds(self, explainer):
        """Explanation should have confidence bounds (INV-RISK-005)."""
        explanation = explainer.explain(
            pdo_id="PDO-TEST-005",
            pdo_hash="hash111",
            risk_score=0.6,
        )
        assert 0.0 <= explanation.confidence_lower <= explanation.risk_score
        assert explanation.risk_score <= explanation.confidence_upper <= 1.0
    
    def test_explanation_has_signal_window(self, explainer):
        """Explanation should have signal window (INV-RISK-006)."""
        explanation = explainer.explain(
            pdo_id="PDO-TEST-006",
            pdo_hash="hash222",
            risk_score=0.5,
        )
        assert explanation.signal_window_start
        assert explanation.signal_window_end
        # End should be after start
        start = datetime.fromisoformat(explanation.signal_window_start.rstrip("Z"))
        end = datetime.fromisoformat(explanation.signal_window_end.rstrip("Z"))
        assert end > start


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ATTACH AND QUERY
# ═══════════════════════════════════════════════════════════════════════════════

class TestAttachAndQuery:
    """Tests for attach and query operations."""
    
    def test_attach_and_query(self, explainer, sample_explanation):
        """Should attach and query explanation."""
        explainer.attach("PDO-TEST-001", sample_explanation)
        retrieved = explainer.query("PDO-TEST-001")
        assert retrieved == sample_explanation
    
    def test_query_nonexistent(self, explainer):
        """Should return None for nonexistent PDO."""
        assert explainer.query("NONEXISTENT") is None
    
    def test_attach_mismatched_pdo_id(self, explainer, sample_explanation):
        """Should raise error for mismatched PDO ID (INV-RISK-003)."""
        with pytest.raises(InvalidBindingError):
            explainer.attach("WRONG-PDO-ID", sample_explanation)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: IMMUTABILITY (INV-RISK-002)
# ═══════════════════════════════════════════════════════════════════════════════

class TestImmutability:
    """Tests for explanation immutability (INV-RISK-002)."""
    
    def test_cannot_attach_twice(self, explainer, sample_explanation):
        """Should not allow attaching twice (INV-RISK-002)."""
        explainer.attach("PDO-TEST-001", sample_explanation)
        
        with pytest.raises(ExplanationImmutableError):
            explainer.attach("PDO-TEST-001", sample_explanation)
    
    def test_modify_forbidden(self, explainer):
        """modify_explanation should be forbidden."""
        with pytest.raises(ExplanationImmutableError):
            explainer.modify_explanation("PDO-TEST-001", risk_score=0.9)
    
    def test_detach_forbidden(self, explainer):
        """detach_explanation should be forbidden."""
        with pytest.raises(ExplanationImmutableError):
            explainer.detach_explanation("PDO-TEST-001")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidation:
    """Tests for explanation validation."""
    
    def test_validate_valid_explanation(self, explainer, sample_explanation):
        """Should validate a valid explanation."""
        assert explainer.validate(sample_explanation) is True
    
    def test_validate_invalid_confidence_bounds(self, explainer, sample_factor):
        """Should reject invalid confidence bounds."""
        explanation = RiskExplanation(
            explanation_id="EXP-INVALID",
            pdo_id="PDO-INVALID",
            pdo_hash="hash",
            risk_score=0.5,
            risk_level=RiskLevel.HIGH,
            summary="Test",
            detailed_reasoning="Details",
            factors=(sample_factor,),
            confidence_lower=0.8,  # Lower > upper = invalid
            confidence_upper=0.2,
            signal_window_start="2025-01-01T00:00:00Z",
            signal_window_end="2025-01-02T00:00:00Z",
        )
        assert explainer.validate(explanation) is False
    
    def test_validate_invalid_temporal_window(self, explainer, sample_factor):
        """Should reject invalid temporal window."""
        explanation = RiskExplanation(
            explanation_id="EXP-INVALID-TIME",
            pdo_id="PDO-INVALID-TIME",
            pdo_hash="hash",
            risk_score=0.5,
            risk_level=RiskLevel.HIGH,
            summary="Test",
            detailed_reasoning="Details",
            factors=(sample_factor,),
            confidence_lower=0.4,
            confidence_upper=0.6,
            signal_window_start="2025-01-02T00:00:00Z",  # Start > End = invalid
            signal_window_end="2025-01-01T00:00:00Z",
        )
        assert explainer.validate(explanation) is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

class TestExport:
    """Tests for export functionality."""
    
    def test_export_json(self, explainer, sample_explanation):
        """Should export as JSON."""
        explainer.attach("PDO-TEST-001", sample_explanation)
        
        json_str = explainer.export_json()
        data = json.loads(json_str)
        
        assert "export_id" in data
        assert "export_timestamp" in data
        assert data["pdo_count"] == 1
        assert len(data["explanations"]) == 1
    
    def test_export_json_filtered(self, explainer, sample_explanation):
        """Should export filtered PDOs."""
        explainer.attach("PDO-TEST-001", sample_explanation)
        
        json_str = explainer.export_json(pdo_ids=["PDO-TEST-001"])
        data = json.loads(json_str)
        
        assert len(data["explanations"]) == 1
    
    def test_export_csv(self, explainer, sample_explanation):
        """Should export as CSV."""
        explainer.attach("PDO-TEST-001", sample_explanation)
        
        csv_str = explainer.export_csv_summary()
        lines = csv_str.strip().split("\n")
        
        assert len(lines) == 2  # Header + 1 row
        assert "pdo_id" in lines[0]
        assert "PDO-TEST-001" in lines[1]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: STATISTICS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatistics:
    """Tests for statistics functionality."""
    
    def test_empty_statistics(self, explainer):
        """Should return zero stats when empty."""
        stats = explainer.get_statistics()
        assert stats["total_explanations"] == 0
        assert stats["average_risk_score"] == 0.0
    
    def test_statistics_with_data(self, explainer, sample_explanation):
        """Should compute correct statistics."""
        explainer.attach("PDO-TEST-001", sample_explanation)
        
        stats = explainer.get_statistics()
        assert stats["total_explanations"] == 1
        assert stats["average_risk_score"] == 0.75
        assert stats["by_risk_level"]["HIGH"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_same_instance(self):
        """Should return same instance."""
        exp1 = get_risk_explainer()
        exp2 = get_risk_explainer()
        assert exp1 is exp2
    
    def test_reset_creates_new_instance(self):
        """Reset should create new instance."""
        exp1 = get_risk_explainer()
        reset_risk_explainer()
        exp2 = get_risk_explainer()
        assert exp1 is not exp2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_explain_pdo_risk(self):
        """Should generate and attach explanation."""
        explanation = explain_pdo_risk(
            pdo_id="PDO-CONV-001",
            pdo_hash="convhash",
            risk_score=0.65,
        )
        
        assert explanation.pdo_id == "PDO-CONV-001"
        
        # Should be queryable
        retrieved = query_pdo_explanation("PDO-CONV-001")
        assert retrieved == explanation
    
    def test_query_pdo_explanation_not_found(self):
        """Should return None for not found."""
        assert query_pdo_explanation("NONEXISTENT") is None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: THREAD SAFETY
# ═══════════════════════════════════════════════════════════════════════════════

class TestThreadSafety:
    """Tests for thread safety."""
    
    def test_concurrent_explain_and_attach(self, explainer):
        """Should handle concurrent operations safely."""
        results = []
        errors = []
        
        def worker(i):
            try:
                explanation = explainer.explain(
                    pdo_id=f"PDO-THREAD-{i}",
                    pdo_hash=f"hash-{i}",
                    risk_score=0.5 + (i * 0.01),
                )
                explainer.attach(f"PDO-THREAD-{i}", explanation)
                results.append(i)
            except Exception as e:
                errors.append(str(e))
        
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert len(results) == 20
    
    def test_concurrent_register_signals(self, explainer):
        """Should handle concurrent signal registration."""
        def worker(i):
            signal = SignalSource(
                signal_id=f"SIG-THREAD-{i}",
                signal_name=f"Thread Signal {i}",
                category="test",
                current_value=0.5,
                baseline_value=0.5,
            )
            explainer.register_signal(signal)
        
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(explainer.list_signals()) == 20


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_zero_risk_score(self, explainer):
        """Should handle zero risk score."""
        explanation = explainer.explain(
            pdo_id="PDO-ZERO",
            pdo_hash="zero",
            risk_score=0.0,
        )
        assert explanation.risk_score == 0.0
        assert explanation.risk_level == RiskLevel.LOW
    
    def test_max_risk_score(self, explainer):
        """Should handle max risk score."""
        explanation = explainer.explain(
            pdo_id="PDO-MAX",
            pdo_hash="max",
            risk_score=1.0,
        )
        assert explanation.risk_score == 1.0
        assert explanation.risk_level == RiskLevel.CRITICAL
    
    def test_empty_summary_and_reasoning(self, explainer):
        """Should handle empty factors gracefully."""
        explanation = explainer.explain(
            pdo_id="PDO-EMPTY",
            pdo_hash="empty",
            risk_score=0.0,
            custom_factors=[],
        )
        assert explanation.summary  # Should still have summary
        assert len(explanation.factors) == 0
    
    def test_long_detailed_reasoning_truncated(self, explainer):
        """Long reasoning should be truncated."""
        # Create many factors to generate long reasoning
        factors = [
            RiskFactor(
                factor_id=f"FACTOR-{i}",
                signal_id=f"SIG-{i}",
                signal_name=f"Signal {i} with a very long name for testing",
                value=0.8,
                threshold=0.5,
                weight=1.0,
                direction=FactorDirection.ABOVE,
                contribution=0.1,
                explanation="A detailed explanation " * 10,
            )
            for i in range(50)
        ]
        
        explanation = explainer.explain(
            pdo_id="PDO-LONG",
            pdo_hash="long",
            risk_score=0.9,
            custom_factors=factors,
        )
        
        max_length = explainer.config["explanation_max_length"]
        assert len(explanation.detailed_reasoning) <= max_length


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests for full workflow."""
    
    def test_full_workflow(self, explainer):
        """Test complete workflow: register signals, explain, attach, query, export."""
        # 1. Register signals
        signals = [
            SignalSource(
                signal_id="SIG-INT-VOL",
                signal_name="Volatility",
                category="market",
                current_value=0.9,
                baseline_value=0.3,
                threshold_high=0.7,
                weight=1.5,
            ),
            SignalSource(
                signal_id="SIG-INT-LIQ",
                signal_name="Liquidity",
                category="market",
                current_value=0.05,
                baseline_value=0.3,
                threshold_low=0.1,
                weight=1.2,
            ),
        ]
        for s in signals:
            explainer.register_signal(s)
        
        # 2. Generate explanation from signals
        explanation = explainer.explain(
            pdo_id="PDO-INT-001",
            pdo_hash="integration-hash-001",
            signal_ids=["SIG-INT-VOL", "SIG-INT-LIQ"],
        )
        
        # 3. Verify explanation content
        assert len(explanation.factors) == 2
        assert explanation.risk_score > 0
        assert explainer.validate(explanation) is True
        
        # 4. Attach and query
        explainer.attach("PDO-INT-001", explanation)
        retrieved = explainer.query("PDO-INT-001")
        assert retrieved == explanation
        
        # 5. Export and verify
        json_export = explainer.export_json()
        data = json.loads(json_export)
        assert data["pdo_count"] == 1
        assert len(data["explanations"]) == 1
        
        # 6. Check statistics
        stats = explainer.get_statistics()
        assert stats["total_explanations"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
