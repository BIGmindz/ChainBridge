"""
Unit Tests for ML Explainability Module.

Tests cover:
- DecisionExplainer (explanations, counterfactuals, rules)
- ConfidenceEstimator (intervals, calibration)
- FeatureAttributor (SHAP, LIME, permutation)
- AuditableModel (audit trail, predictions)
- ExplanationRenderer (multi-format)
- ModelCardGenerator (governance)
- BiasAnalyzer (fairness)
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from core.gie.ml.explainability import (
    EXPLAINABILITY_VERSION,
    ExplanationType,
    ConfidenceMethod,
    AttributionMethod,
    RenderFormat,
    BiasType,
    RiskLevel,
    ExplainabilityError,
    ConfidenceError,
    Explanation,
    ConfidenceInterval,
    FeatureAttribution,
    AuditRecord,
    ModelCard,
    BiasReport,
    DecisionExplainer,
    ConfidenceEstimator,
    FeatureAttributor,
    AuditableModel,
    ExplanationRenderer,
    ModelCardGenerator,
    BiasAnalyzer,
    compute_wrap_hash,
)


# =============================================================================
# MOCK MODEL
# =============================================================================

class MockModel:
    """Mock predictive model for testing."""
    
    def predict(self, features: Dict[str, Any]) -> float:
        """Simple prediction based on features."""
        score = 0.0
        for k, v in features.items():
            if isinstance(v, (int, float)):
                score += v * 0.1
            elif isinstance(v, bool):
                score += 0.5 if v else 0.0
        return min(max(score, 0.0), 1.0)
    
    def predict_proba(self, features: Dict[str, Any]) -> Dict[str, float]:
        """Get prediction probabilities."""
        score = self.predict(features)
        return {"positive": score, "negative": 1 - score}


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_model() -> MockModel:
    """Create a mock model."""
    return MockModel()


@pytest.fixture
def explainer() -> DecisionExplainer:
    """Create a decision explainer."""
    return DecisionExplainer()


@pytest.fixture
def confidence_estimator() -> ConfidenceEstimator:
    """Create a confidence estimator."""
    return ConfidenceEstimator()


@pytest.fixture
def attributor() -> FeatureAttributor:
    """Create a feature attributor."""
    return FeatureAttributor()


@pytest.fixture
def renderer() -> ExplanationRenderer:
    """Create an explanation renderer."""
    return ExplanationRenderer()


@pytest.fixture
def model_card_generator() -> ModelCardGenerator:
    """Create a model card generator."""
    return ModelCardGenerator()


@pytest.fixture
def bias_analyzer() -> BiasAnalyzer:
    """Create a bias analyzer."""
    return BiasAnalyzer()


@pytest.fixture
def sample_features() -> Dict[str, Any]:
    """Sample feature dictionary."""
    return {
        "age": 30,
        "income": 50000,
        "is_premium": True,
        "category": "A",
    }


# =============================================================================
# TEST ENUMS
# =============================================================================

class TestEnums:
    """Tests for enumeration types."""
    
    def test_explanation_type_values(self) -> None:
        """Test ExplanationType enum values."""
        assert ExplanationType.FEATURE_IMPORTANCE.value == "FEATURE_IMPORTANCE"
        assert ExplanationType.COUNTERFACTUAL.value == "COUNTERFACTUAL"
        assert ExplanationType.RULE_BASED.value == "RULE_BASED"
    
    def test_confidence_method_values(self) -> None:
        """Test ConfidenceMethod enum values."""
        assert ConfidenceMethod.ENSEMBLE.value == "ENSEMBLE"
        assert ConfidenceMethod.CALIBRATED.value == "CALIBRATED"
        assert ConfidenceMethod.CONFORMAL.value == "CONFORMAL"
    
    def test_attribution_method_values(self) -> None:
        """Test AttributionMethod enum values."""
        assert AttributionMethod.PERMUTATION.value == "PERMUTATION"
        assert AttributionMethod.SHAP.value == "SHAP"
        assert AttributionMethod.LIME.value == "LIME"
    
    def test_render_format_values(self) -> None:
        """Test RenderFormat enum values."""
        assert RenderFormat.TEXT.value == "TEXT"
        assert RenderFormat.HTML.value == "HTML"
        assert RenderFormat.JSON.value == "JSON"
        assert RenderFormat.MARKDOWN.value == "MARKDOWN"
    
    def test_bias_type_values(self) -> None:
        """Test BiasType enum values."""
        assert BiasType.DEMOGRAPHIC.value == "DEMOGRAPHIC"
        assert BiasType.SELECTION.value == "SELECTION"
    
    def test_risk_level_values(self) -> None:
        """Test RiskLevel enum values."""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"
        assert RiskLevel.CRITICAL.value == "CRITICAL"


# =============================================================================
# TEST DATA CLASSES
# =============================================================================

class TestExplanation:
    """Tests for Explanation dataclass."""
    
    def test_create_explanation(self) -> None:
        """Test creating an explanation."""
        now = datetime.now(timezone.utc)
        exp = Explanation(
            explanation_id="EXP-001",
            explanation_type=ExplanationType.FEATURE_IMPORTANCE,
            prediction_id="PRED-001",
            model_id="MODEL-001",
            input_features={"x": 1},
            output_prediction=0.7,
            confidence=0.9,
            feature_attributions={"x": 0.5},
            counterfactuals=[],
            rules=["IF x > 0 THEN high"],
            generated_at=now,
        )
        
        assert exp.explanation_id == "EXP-001"
        assert exp.confidence == 0.9
    
    def test_explanation_to_dict(self) -> None:
        """Test converting explanation to dict."""
        now = datetime.now(timezone.utc)
        exp = Explanation(
            explanation_id="EXP-002",
            explanation_type=ExplanationType.COUNTERFACTUAL,
            prediction_id="PRED-002",
            model_id="MODEL-002",
            input_features={"y": 2},
            output_prediction="positive",
            confidence=0.85,
            feature_attributions={"y": 0.3},
            counterfactuals=[{"y": 1}],
            rules=[],
            generated_at=now,
        )
        
        d = exp.to_dict()
        assert d["explanation_id"] == "EXP-002"
        assert d["explanation_type"] == "COUNTERFACTUAL"


class TestConfidenceInterval:
    """Tests for ConfidenceInterval dataclass."""
    
    def test_create_interval(self) -> None:
        """Test creating a confidence interval."""
        ci = ConfidenceInterval(
            point_estimate=0.5,
            lower_bound=0.3,
            upper_bound=0.7,
            confidence_level=0.95,
            method=ConfidenceMethod.ENSEMBLE,
        )
        
        assert abs(ci.width - 0.4) < 1e-10  # Use approximate comparison for floats
        assert ci.contains(0.5)
        assert not ci.contains(0.1)
    
    def test_interval_to_dict(self) -> None:
        """Test converting interval to dict."""
        ci = ConfidenceInterval(
            point_estimate=0.6,
            lower_bound=0.4,
            upper_bound=0.8,
            confidence_level=0.90,
            method=ConfidenceMethod.CALIBRATED,
            calibrated=True,
        )
        
        d = ci.to_dict()
        assert d["point_estimate"] == 0.6
        assert d["calibrated"] is True


class TestFeatureAttribution:
    """Tests for FeatureAttribution dataclass."""
    
    def test_create_attribution(self) -> None:
        """Test creating a feature attribution."""
        attr = FeatureAttribution(
            feature_name="income",
            attribution_value=0.25,
            base_value=0.5,
            method=AttributionMethod.SHAP,
            importance_rank=1,
            direction="positive",
        )
        
        assert attr.feature_name == "income"
        assert attr.direction == "positive"
    
    def test_attribution_to_dict(self) -> None:
        """Test converting attribution to dict."""
        attr = FeatureAttribution(
            feature_name="age",
            attribution_value=-0.1,
            base_value=0.5,
            method=AttributionMethod.PERMUTATION,
            importance_rank=2,
            direction="negative",
        )
        
        d = attr.to_dict()
        assert d["feature_name"] == "age"
        assert d["method"] == "PERMUTATION"


class TestAuditRecord:
    """Tests for AuditRecord dataclass."""
    
    def test_create_audit_record(self) -> None:
        """Test creating an audit record."""
        now = datetime.now(timezone.utc)
        record = AuditRecord(
            audit_id="AUD-001",
            model_id="MODEL-001",
            timestamp=now,
            input_hash="abc123",
            output_hash="def456",
            explanation_id="EXP-001",
            decision="approved",
            confidence=0.95,
            user_id="user-001",
            session_id="sess-001",
            latency_ms=50.5,
        )
        
        assert record.audit_id == "AUD-001"
        assert record.latency_ms == 50.5


# =============================================================================
# TEST DECISION EXPLAINER
# =============================================================================

class TestDecisionExplainer:
    """Tests for DecisionExplainer."""
    
    def test_explain_prediction(
        self,
        explainer: DecisionExplainer,
        sample_features: Dict[str, Any],
    ) -> None:
        """Test generating an explanation."""
        explanation = explainer.explain(
            model_id="test-model",
            prediction_id="pred-001",
            features=sample_features,
            prediction=0.75,
            confidence=0.9,
        )
        
        assert explanation.explanation_id.startswith("EXP-")
        assert explanation.model_id == "test-model"
        assert len(explanation.feature_attributions) == len(sample_features)
    
    def test_explain_generates_counterfactuals(
        self,
        explainer: DecisionExplainer,
        sample_features: Dict[str, Any],
    ) -> None:
        """Test that counterfactuals are generated."""
        explanation = explainer.explain(
            model_id="cf-model",
            prediction_id="pred-002",
            features=sample_features,
            prediction="positive",
            confidence=0.85,
        )
        
        assert len(explanation.counterfactuals) > 0
        assert "modified_feature" in explanation.counterfactuals[0]
    
    def test_explain_generates_rules(
        self,
        explainer: DecisionExplainer,
        sample_features: Dict[str, Any],
    ) -> None:
        """Test that rules are generated."""
        explanation = explainer.explain(
            model_id="rule-model",
            prediction_id="pred-003",
            features=sample_features,
            prediction=1.0,
            confidence=0.99,
        )
        
        assert len(explanation.rules) > 0
        assert "IF" in explanation.rules[0]
    
    def test_get_explanation(
        self,
        explainer: DecisionExplainer,
        sample_features: Dict[str, Any],
    ) -> None:
        """Test retrieving an explanation."""
        explanation = explainer.explain(
            model_id="retrieve-model",
            prediction_id="pred-004",
            features=sample_features,
            prediction=0.5,
            confidence=0.7,
        )
        
        retrieved = explainer.get_explanation(explanation.explanation_id)
        assert retrieved is not None
        assert retrieved.explanation_id == explanation.explanation_id
    
    def test_summarize(
        self,
        explainer: DecisionExplainer,
        sample_features: Dict[str, Any],
    ) -> None:
        """Test summarizing an explanation."""
        explanation = explainer.explain(
            model_id="summary-model",
            prediction_id="pred-005",
            features=sample_features,
            prediction="approved",
            confidence=0.92,
        )
        
        summary = explainer.summarize(explanation)
        
        assert "approved" in summary
        assert "92" in summary  # confidence percentage


# =============================================================================
# TEST CONFIDENCE ESTIMATOR
# =============================================================================

class TestConfidenceEstimator:
    """Tests for ConfidenceEstimator."""
    
    def test_estimate_heuristic(self, confidence_estimator: ConfidenceEstimator) -> None:
        """Test heuristic confidence estimation."""
        ci = confidence_estimator.estimate(
            prediction=0.7,
            confidence_level=0.95,
        )
        
        assert ci.point_estimate == 0.7
        assert ci.lower_bound < ci.point_estimate
        assert ci.upper_bound > ci.point_estimate
    
    def test_estimate_ensemble(self, confidence_estimator: ConfidenceEstimator) -> None:
        """Test ensemble confidence estimation."""
        ensemble = [0.65, 0.68, 0.72, 0.75, 0.78]
        
        ci = confidence_estimator.estimate(
            prediction=0.7,
            predictions_ensemble=ensemble,
            confidence_level=0.95,
            method=ConfidenceMethod.ENSEMBLE,
        )
        
        assert ci.method == ConfidenceMethod.ENSEMBLE
        assert ci.lower_bound >= min(ensemble)
        assert ci.upper_bound <= max(ensemble)
    
    def test_estimate_temperature(self, confidence_estimator: ConfidenceEstimator) -> None:
        """Test temperature-scaled confidence estimation."""
        ci = confidence_estimator.estimate(
            prediction=0.8,
            confidence_level=0.95,
            method=ConfidenceMethod.SOFTMAX_TEMPERATURE,
        )
        
        assert ci.method == ConfidenceMethod.SOFTMAX_TEMPERATURE
    
    def test_calibrate(self, confidence_estimator: ConfidenceEstimator) -> None:
        """Test calibration."""
        predictions = [0.8, 0.7, 0.9, 0.6, 0.85]
        actuals = [0.75, 0.72, 0.88, 0.58, 0.82]
        
        error = confidence_estimator.calibrate(predictions, actuals)
        
        assert 0 <= error <= 1
        assert confidence_estimator.get_calibration_error() == error
    
    def test_calibrate_invalid_data(self, confidence_estimator: ConfidenceEstimator) -> None:
        """Test calibration with invalid data."""
        with pytest.raises(ConfidenceError):
            confidence_estimator.calibrate([], [])
    
    def test_calibrated_interval(self, confidence_estimator: ConfidenceEstimator) -> None:
        """Test calibrated interval after calibration."""
        # Calibrate first
        predictions = [0.5] * 10
        actuals = [0.5] * 10
        confidence_estimator.calibrate(predictions, actuals)
        
        ci = confidence_estimator.estimate(
            prediction=0.6,
            method=ConfidenceMethod.CALIBRATED,
        )
        
        assert ci.calibrated is True


# =============================================================================
# TEST FEATURE ATTRIBUTOR
# =============================================================================

class TestFeatureAttributor:
    """Tests for FeatureAttributor."""
    
    def test_permutation_attribution(
        self,
        attributor: FeatureAttributor,
        mock_model: MockModel,
        sample_features: Dict[str, Any],
    ) -> None:
        """Test permutation-based attribution."""
        attributions = attributor.attribute(
            model=mock_model,
            features=sample_features,
            method=AttributionMethod.PERMUTATION,
        )
        
        assert len(attributions) == len(sample_features)
        assert all(isinstance(a, FeatureAttribution) for a in attributions)
        
        # Check ranks are set
        ranks = [a.importance_rank for a in attributions]
        assert sorted(ranks) == list(range(1, len(sample_features) + 1))
    
    def test_shap_attribution(
        self,
        attributor: FeatureAttributor,
        mock_model: MockModel,
        sample_features: Dict[str, Any],
    ) -> None:
        """Test SHAP-like attribution."""
        attributions = attributor.attribute(
            model=mock_model,
            features=sample_features,
            method=AttributionMethod.SHAP,
        )
        
        assert len(attributions) == len(sample_features)
        assert all(a.method == AttributionMethod.SHAP for a in attributions)
    
    def test_lime_attribution(
        self,
        attributor: FeatureAttributor,
        mock_model: MockModel,
        sample_features: Dict[str, Any],
    ) -> None:
        """Test LIME-like attribution."""
        attributions = attributor.attribute(
            model=mock_model,
            features=sample_features,
            method=AttributionMethod.LIME,
        )
        
        assert len(attributions) == len(sample_features)
        assert all(a.method == AttributionMethod.LIME for a in attributions)
    
    def test_integrated_gradients(
        self,
        attributor: FeatureAttributor,
        mock_model: MockModel,
        sample_features: Dict[str, Any],
    ) -> None:
        """Test integrated gradients attribution."""
        attributions = attributor.attribute(
            model=mock_model,
            features=sample_features,
            method=AttributionMethod.INTEGRATED_GRADIENTS,
        )
        
        assert len(attributions) == len(sample_features)
    
    def test_global_importance(
        self,
        attributor: FeatureAttributor,
        mock_model: MockModel,
    ) -> None:
        """Test global importance computation."""
        dataset = [
            {"x": 1, "y": 2, "z": 3},
            {"x": 2, "y": 1, "z": 4},
            {"x": 3, "y": 3, "z": 2},
        ]
        
        importance = attributor.compute_global_importance(mock_model, dataset)
        
        assert "x" in importance
        assert "y" in importance
        assert "z" in importance
        
        # Should sum to approximately 1 (normalized)
        assert abs(sum(importance.values()) - 1.0) < 0.01
    
    def test_detect_interactions(
        self,
        attributor: FeatureAttributor,
        mock_model: MockModel,
        sample_features: Dict[str, Any],
    ) -> None:
        """Test feature interaction detection."""
        interactions = attributor.detect_interactions(mock_model, sample_features)
        
        # Should return a list (may be empty if no interactions)
        assert isinstance(interactions, list)


# =============================================================================
# TEST AUDITABLE MODEL
# =============================================================================

class TestAuditableModel:
    """Tests for AuditableModel."""
    
    def test_audited_prediction(self, mock_model: MockModel) -> None:
        """Test making an audited prediction."""
        auditable = AuditableModel(
            model=mock_model,
            model_id="audit-test-001",
        )
        
        prediction, explanation, audit_record = auditable.predict(
            features={"x": 5, "y": 3},
            user_id="user-001",
        )
        
        assert prediction is not None
        assert explanation is not None
        assert audit_record is not None
        assert audit_record.user_id == "user-001"
    
    def test_prediction_without_explanation(self, mock_model: MockModel) -> None:
        """Test prediction without generating explanation."""
        auditable = AuditableModel(
            model=mock_model,
            model_id="no-exp-001",
        )
        
        prediction, explanation, audit_record = auditable.predict(
            features={"x": 1},
            generate_explanation=False,
        )
        
        assert prediction is not None
        assert explanation is None
        assert audit_record.explanation_id == ""
    
    def test_audit_trail(self, mock_model: MockModel) -> None:
        """Test retrieving audit trail."""
        auditable = AuditableModel(
            model=mock_model,
            model_id="trail-test-001",
        )
        
        # Make several predictions
        for i in range(5):
            auditable.predict(features={"x": i}, user_id=f"user-{i % 2}")
        
        trail = auditable.get_audit_trail()
        assert len(trail) == 5
        
        # Filter by user
        user_0_trail = auditable.get_audit_trail(user_id="user-0")
        assert all(r.user_id == "user-0" for r in user_0_trail)
    
    def test_export_audit_trail_json(self, mock_model: MockModel) -> None:
        """Test exporting audit trail as JSON."""
        auditable = AuditableModel(
            model=mock_model,
            model_id="export-json-001",
        )
        
        auditable.predict(features={"x": 1})
        
        export = auditable.export_audit_trail(format="json")
        data = json.loads(export)
        
        assert isinstance(data, list)
        assert len(data) == 1
    
    def test_export_audit_trail_csv(self, mock_model: MockModel) -> None:
        """Test exporting audit trail as CSV."""
        auditable = AuditableModel(
            model=mock_model,
            model_id="export-csv-001",
        )
        
        auditable.predict(features={"x": 1})
        
        export = auditable.export_audit_trail(format="csv")
        
        assert "audit_id" in export
        assert "model_id" in export
    
    def test_get_stats(self, mock_model: MockModel) -> None:
        """Test getting audit statistics."""
        auditable = AuditableModel(
            model=mock_model,
            model_id="stats-test-001",
        )
        
        for i in range(3):
            auditable.predict(features={"x": i}, user_id="user-1")
        
        stats = auditable.get_stats()
        
        assert stats["total_predictions"] == 3
        assert "avg_latency_ms" in stats
        assert stats["unique_users"] == 1


class TestAuditableModelThreadSafety:
    """Thread safety tests for AuditableModel."""
    
    def test_concurrent_predictions(self) -> None:
        """Test concurrent predictions."""
        mock_model = MockModel()
        auditable = AuditableModel(
            model=mock_model,
            model_id="thread-test-001",
        )
        
        errors = []
        
        def make_predictions(count: int, user: str) -> None:
            for i in range(count):
                try:
                    auditable.predict(
                        features={"x": i},
                        user_id=user,
                    )
                except Exception as e:
                    errors.append(str(e))
        
        threads = [
            threading.Thread(target=make_predictions, args=(20, f"user-{t}"))
            for t in range(4)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        
        trail = auditable.get_audit_trail(limit=1000)
        assert len(trail) == 80


# =============================================================================
# TEST EXPLANATION RENDERER
# =============================================================================

class TestExplanationRenderer:
    """Tests for ExplanationRenderer."""
    
    @pytest.fixture
    def sample_explanation(self) -> Explanation:
        """Create a sample explanation."""
        return Explanation(
            explanation_id="RENDER-001",
            explanation_type=ExplanationType.FEATURE_IMPORTANCE,
            prediction_id="PRED-001",
            model_id="MODEL-001",
            input_features={"age": 30, "income": 50000},
            output_prediction="approved",
            confidence=0.85,
            feature_attributions={"age": 0.3, "income": 0.7},
            counterfactuals=[],
            rules=["IF income > 40000 THEN approve"],
            generated_at=datetime.now(timezone.utc),
        )
    
    def test_render_text(
        self,
        renderer: ExplanationRenderer,
        sample_explanation: Explanation,
    ) -> None:
        """Test text rendering."""
        output = renderer.render(sample_explanation, RenderFormat.TEXT)
        
        assert "RENDER-001" in output
        assert "approved" in output
        assert "age" in output
    
    def test_render_html(
        self,
        renderer: ExplanationRenderer,
        sample_explanation: Explanation,
    ) -> None:
        """Test HTML rendering."""
        output = renderer.render(sample_explanation, RenderFormat.HTML)
        
        assert "<div" in output
        assert "RENDER-001" in output
    
    def test_render_json(
        self,
        renderer: ExplanationRenderer,
        sample_explanation: Explanation,
    ) -> None:
        """Test JSON rendering."""
        output = renderer.render(sample_explanation, RenderFormat.JSON)
        
        data = json.loads(output)
        assert data["explanation_id"] == "RENDER-001"
    
    def test_render_markdown(
        self,
        renderer: ExplanationRenderer,
        sample_explanation: Explanation,
    ) -> None:
        """Test Markdown rendering."""
        output = renderer.render(sample_explanation, RenderFormat.MARKDOWN)
        
        assert "# Explanation" in output
        assert "|" in output  # Table
    
    def test_render_latex(
        self,
        renderer: ExplanationRenderer,
        sample_explanation: Explanation,
    ) -> None:
        """Test LaTeX rendering."""
        output = renderer.render(sample_explanation, RenderFormat.LATEX)
        
        assert "\\begin{table}" in output
        assert "\\end{table}" in output
    
    def test_render_attribution_chart(self, renderer: ExplanationRenderer) -> None:
        """Test attribution chart rendering."""
        attributions = [
            FeatureAttribution(
                feature_name="feature_a",
                attribution_value=0.5,
                base_value=0.0,
                method=AttributionMethod.SHAP,
                importance_rank=1,
                direction="positive",
            ),
            FeatureAttribution(
                feature_name="feature_b",
                attribution_value=-0.3,
                base_value=0.0,
                method=AttributionMethod.SHAP,
                importance_rank=2,
                direction="negative",
            ),
        ]
        
        chart = renderer.render_attribution_chart(attributions, RenderFormat.TEXT)
        
        assert "feature_a" in chart
        assert "feature_b" in chart


# =============================================================================
# TEST MODEL CARD GENERATOR
# =============================================================================

class TestModelCardGenerator:
    """Tests for ModelCardGenerator."""
    
    def test_generate_card(self, model_card_generator: ModelCardGenerator) -> None:
        """Test generating a model card."""
        card = model_card_generator.generate(
            model_id="CARD-001",
            model_name="Test Classifier",
            version="1.0.0",
            description="A test classification model",
            intended_use="Binary classification tasks",
            metrics={"accuracy": 0.92, "f1_score": 0.89},
        )
        
        assert card.model_id == "CARD-001"
        assert card.model_name == "Test Classifier"
        assert card.metrics["accuracy"] == 0.92
    
    def test_risk_assessment(self, model_card_generator: ModelCardGenerator) -> None:
        """Test risk level assessment."""
        # High accuracy model
        card_low_risk = model_card_generator.generate(
            model_id="LOW-RISK",
            model_name="Safe Model",
            version="1.0.0",
            description="High accuracy model",
            intended_use="General purpose",
            metrics={"accuracy": 0.98},
        )
        assert card_low_risk.risk_level == RiskLevel.LOW
        
        # Low accuracy model
        card_high_risk = model_card_generator.generate(
            model_id="HIGH-RISK",
            model_name="Risky Model",
            version="1.0.0",
            description="Low accuracy model",
            intended_use="Critical healthcare decisions",
            metrics={"accuracy": 0.65},
        )
        assert card_high_risk.risk_level == RiskLevel.CRITICAL
    
    def test_add_bias_analysis(self, model_card_generator: ModelCardGenerator) -> None:
        """Test adding bias analysis to card."""
        card = model_card_generator.generate(
            model_id="BIAS-TEST",
            model_name="Bias Test Model",
            version="1.0.0",
            description="Testing bias analysis",
            intended_use="Testing",
            metrics={"accuracy": 0.90},
        )
        
        bias_report = BiasReport(
            model_id="BIAS-TEST",
            bias_type=BiasType.DEMOGRAPHIC,
            affected_groups=["group_a", "group_b"],
            disparity_metric=0.75,
            threshold=0.8,
            passed=False,
            recommendations=["Rebalance training data"],
            generated_at=datetime.now(timezone.utc),
        )
        
        updated = model_card_generator.add_bias_analysis("BIAS-TEST", bias_report)
        
        assert updated is not None
        assert BiasType.DEMOGRAPHIC.value in updated.bias_analysis
        assert updated.risk_level == RiskLevel.HIGH  # Due to bias failure
    
    def test_export_card_markdown(self, model_card_generator: ModelCardGenerator) -> None:
        """Test exporting card as Markdown."""
        model_card_generator.generate(
            model_id="EXPORT-MD",
            model_name="Export Test",
            version="1.0.0",
            description="For export testing",
            intended_use="Testing export",
            metrics={"accuracy": 0.85},
        )
        
        md = model_card_generator.export_card("EXPORT-MD", RenderFormat.MARKDOWN)
        
        assert "# Model Card: Export Test" in md
        assert "accuracy" in md
    
    def test_export_card_json(self, model_card_generator: ModelCardGenerator) -> None:
        """Test exporting card as JSON."""
        model_card_generator.generate(
            model_id="EXPORT-JSON",
            model_name="JSON Test",
            version="1.0.0",
            description="For JSON testing",
            intended_use="Testing",
            metrics={"accuracy": 0.90},
        )
        
        json_str = model_card_generator.export_card("EXPORT-JSON", RenderFormat.JSON)
        data = json.loads(json_str)
        
        assert data["model_id"] == "EXPORT-JSON"


# =============================================================================
# TEST BIAS ANALYZER
# =============================================================================

class TestBiasAnalyzer:
    """Tests for BiasAnalyzer."""
    
    def test_analyze_fair_model(self, bias_analyzer: BiasAnalyzer) -> None:
        """Test analyzing a fair model."""
        predictions = [
            {"gender": "male", "prediction": 0.8},
            {"gender": "male", "prediction": 0.75},
            {"gender": "female", "prediction": 0.78},
            {"gender": "female", "prediction": 0.82},
        ]
        
        report = bias_analyzer.analyze(
            model_id="fair-model",
            predictions=predictions,
            protected_attribute="gender",
            threshold=0.8,
        )
        
        assert report.passed is True
        assert report.disparity_metric > 0.8
    
    def test_analyze_biased_model(self, bias_analyzer: BiasAnalyzer) -> None:
        """Test analyzing a biased model."""
        predictions = [
            {"gender": "male", "prediction": 0.9},
            {"gender": "male", "prediction": 0.85},
            {"gender": "female", "prediction": 0.3},
            {"gender": "female", "prediction": 0.25},
        ]
        
        report = bias_analyzer.analyze(
            model_id="biased-model",
            predictions=predictions,
            protected_attribute="gender",
            threshold=0.8,
        )
        
        assert report.passed is False
        assert len(report.recommendations) > 0
    
    def test_get_reports(self, bias_analyzer: BiasAnalyzer) -> None:
        """Test getting bias reports."""
        # Analyze two models
        bias_analyzer.analyze(
            model_id="model-1",
            predictions=[{"group": "a", "prediction": 0.5}],
            protected_attribute="group",
        )
        bias_analyzer.analyze(
            model_id="model-2",
            predictions=[{"group": "b", "prediction": 0.6}],
            protected_attribute="group",
        )
        
        all_reports = bias_analyzer.get_reports()
        assert len(all_reports) == 2
        
        model_1_reports = bias_analyzer.get_reports(model_id="model-1")
        assert len(model_1_reports) == 1


# =============================================================================
# TEST WRAP HASH
# =============================================================================

class TestWrapHash:
    """Tests for WRAP hash computation."""
    
    def test_wrap_hash_format(self) -> None:
        """Test WRAP hash format."""
        wrap_hash = compute_wrap_hash()
        
        assert len(wrap_hash) == 16
        assert all(c in "0123456789abcdef" for c in wrap_hash)
    
    def test_wrap_hash_consistency(self) -> None:
        """Test WRAP hash is consistent."""
        hash_1 = compute_wrap_hash()
        hash_2 = compute_wrap_hash()
        
        assert hash_1 == hash_2


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for explainability components."""
    
    def test_full_explainability_pipeline(self) -> None:
        """Test complete explainability pipeline."""
        # Setup
        model = MockModel()
        explainer = DecisionExplainer()
        estimator = ConfidenceEstimator()
        attributor = FeatureAttributor()
        renderer = ExplanationRenderer()
        card_generator = ModelCardGenerator()
        bias_analyzer = BiasAnalyzer()
        
        # Wrap model for auditing
        auditable = AuditableModel(model, "integration-test-model", explainer)
        
        # Make prediction
        features = {"income": 75000, "age": 35, "premium": True}
        prediction, explanation, audit = auditable.predict(
            features=features,
            user_id="test-user",
        )
        
        # Get confidence interval
        ci = estimator.estimate(prediction, confidence_level=0.95)
        
        # Get detailed attributions
        attributions = attributor.attribute(model, features)
        
        # Render explanation
        rendered = renderer.render(explanation, RenderFormat.MARKDOWN)
        
        # Generate model card
        card = card_generator.generate(
            model_id="integration-test-model",
            model_name="Integration Test Model",
            version="1.0.0",
            description="Model for integration testing",
            intended_use="Testing the explainability pipeline",
            metrics={"accuracy": 0.91},
        )
        
        # Analyze for bias
        predictions = [
            {"group": "A", "prediction": 0.8},
            {"group": "B", "prediction": 0.78},
        ]
        bias_report = bias_analyzer.analyze(
            model_id="integration-test-model",
            predictions=predictions,
            protected_attribute="group",
        )
        
        # Add bias to card
        card_generator.add_bias_analysis("integration-test-model", bias_report)
        
        # Assertions
        assert prediction is not None
        assert explanation is not None
        assert ci.contains(prediction)
        assert len(attributions) == len(features)
        assert "Integration" in rendered or "income" in rendered
        assert card.model_id == "integration-test-model"
        assert bias_report is not None
    
    def test_version_exists(self) -> None:
        """Test version constant exists."""
        assert EXPLAINABILITY_VERSION == "1.0.0"
