"""
Test GIE Risk Attribution

Per PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-028.
Agent: GID-10 (Maggie) — ML/AI Lead
"""

import pytest
from typing import List

from core.chainiq.gie_risk_attribution import (
    # Enums
    RiskLevel,
    RiskCategory,
    ExplanationType,
    
    # Data classes
    RiskFactor,
    RiskExplanation,
    AgentRiskProfile,
    PDORiskAttribution,
    
    # Engine
    GIERiskAttributionEngine,
    get_risk_engine,
    reset_risk_engine,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Provide fresh risk engine."""
    reset_risk_engine()
    return GIERiskAttributionEngine()


@pytest.fixture
def sample_factors():
    """Provide sample risk factors."""
    return [
        RiskFactor(
            factor_id="RF-001",
            category=RiskCategory.EXECUTION,
            name="Execution Risk",
            description="Test",
            weight=0.3,
            raw_score=0.5,
        ),
        RiskFactor(
            factor_id="RF-002",
            category=RiskCategory.INTEGRITY,
            name="Integrity Risk",
            description="Test",
            weight=0.4,
            raw_score=0.3,
        ),
    ]


@pytest.fixture
def sample_profile(sample_factors):
    """Provide sample agent profile."""
    return AgentRiskProfile(
        agent_gid="GID-01",
        task_type="backend_task",
        factors=sample_factors,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: RiskLevel Enum
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_all_levels_defined(self):
        """All risk levels are defined."""
        levels = [l.value for l in RiskLevel]
        assert "MINIMAL" in levels
        assert "LOW" in levels
        assert "MODERATE" in levels
        assert "HIGH" in levels
        assert "CRITICAL" in levels


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: RiskFactor
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskFactor:
    """Tests for RiskFactor dataclass."""

    def test_weighted_score_computed(self):
        """Weighted score is auto-computed."""
        factor = RiskFactor(
            factor_id="RF-001",
            category=RiskCategory.EXECUTION,
            name="Test",
            description="Test",
            weight=0.5,
            raw_score=0.8,
        )
        assert factor.weighted_score == 0.4  # 0.5 * 0.8

    def test_to_dict(self):
        """Can convert to dictionary."""
        factor = RiskFactor(
            factor_id="RF-001",
            category=RiskCategory.GOVERNANCE,
            name="Test",
            description="Test",
            weight=0.3,
            raw_score=0.5,
        )
        result = factor.to_dict()
        assert result["factor_id"] == "RF-001"
        assert result["category"] == "GOVERNANCE"
        assert result["weighted_score"] == 0.15


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: AgentRiskProfile
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentRiskProfile:
    """Tests for AgentRiskProfile."""

    def test_overall_score_computed(self, sample_profile):
        """Overall score is computed from factors."""
        # Factor 1: weight=0.3, raw=0.5 -> weighted=0.15
        # Factor 2: weight=0.4, raw=0.3 -> weighted=0.12
        # Overall: (0.15 + 0.12) / (0.3 + 0.4) = 0.27 / 0.7 ≈ 0.386
        assert 0.38 < sample_profile.overall_score < 0.40

    def test_risk_level_assigned(self, sample_profile):
        """Risk level is assigned based on score."""
        # Score ~0.39 -> LOW
        assert sample_profile.risk_level == RiskLevel.LOW

    def test_minimal_risk_level(self):
        """Score < 0.2 -> MINIMAL."""
        profile = AgentRiskProfile(
            agent_gid="TEST",
            task_type="test",
            factors=[
                RiskFactor("RF-1", RiskCategory.EXECUTION, "Test", "", 1.0, 0.1)
            ],
        )
        assert profile.risk_level == RiskLevel.MINIMAL

    def test_critical_risk_level(self):
        """Score >= 0.8 -> CRITICAL."""
        profile = AgentRiskProfile(
            agent_gid="TEST",
            task_type="test",
            factors=[
                RiskFactor("RF-1", RiskCategory.EXECUTION, "Test", "", 1.0, 0.9)
            ],
        )
        assert profile.risk_level == RiskLevel.CRITICAL

    def test_empty_factors_zero_score(self):
        """Empty factors list results in zero score."""
        profile = AgentRiskProfile(
            agent_gid="TEST",
            task_type="test",
            factors=[],
        )
        assert profile.overall_score == 0.0
        assert profile.risk_level == RiskLevel.MINIMAL

    def test_to_dict(self, sample_profile):
        """Can convert to dictionary."""
        result = sample_profile.to_dict()
        assert result["agent_gid"] == "GID-01"
        assert result["task_type"] == "backend_task"
        assert len(result["factors"]) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDORiskAttribution
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDORiskAttribution:
    """Tests for PDORiskAttribution."""

    def test_aggregate_score_computed(self, sample_profile):
        """Aggregate score uses max of agent scores."""
        another_profile = AgentRiskProfile(
            agent_gid="GID-02",
            task_type="task",
            factors=[
                RiskFactor("RF-3", RiskCategory.INTEGRITY, "High", "", 1.0, 0.7)
            ],
        )
        
        attribution = PDORiskAttribution(
            pdo_id="PDO-001",
            agent_profiles=[sample_profile, another_profile],
        )
        
        # Max score should be from GID-02
        assert attribution.aggregate_score == 0.7

    def test_category_breakdown(self, sample_profile):
        """Category breakdown computed correctly."""
        attribution = PDORiskAttribution(
            pdo_id="PDO-001",
            agent_profiles=[sample_profile],
        )
        
        assert RiskCategory.EXECUTION.value in attribution.category_breakdown
        assert RiskCategory.INTEGRITY.value in attribution.category_breakdown

    def test_hash_computed(self, sample_profile):
        """Hash reference is computed."""
        attribution = PDORiskAttribution(
            pdo_id="PDO-001",
            agent_profiles=[sample_profile],
        )
        
        assert attribution.hash_ref.startswith("sha256:")

    def test_to_dict(self, sample_profile):
        """Can convert to dictionary."""
        attribution = PDORiskAttribution(
            pdo_id="PDO-001",
            agent_profiles=[sample_profile],
        )
        
        result = attribution.to_dict()
        assert result["pdo_id"] == "PDO-001"
        assert len(result["agent_profiles"]) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GIERiskAttributionEngine - Factor Assessment
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineFactorAssessment:
    """Tests for risk factor assessment."""

    def test_execution_risk_low_complexity(self, engine):
        """Low complexity results in low execution risk."""
        factor = engine.assess_execution_risk(
            task_complexity=0.1,
            estimated_duration=30,
            historical_success_rate=0.99,
        )
        assert factor.category == RiskCategory.EXECUTION
        assert factor.raw_score < 0.2

    def test_execution_risk_high_complexity(self, engine):
        """High complexity results in high execution risk."""
        factor = engine.assess_execution_risk(
            task_complexity=0.9,
            estimated_duration=3600,
            historical_success_rate=0.5,
        )
        assert factor.raw_score > 0.6

    def test_dependency_risk_no_deps(self, engine):
        """No dependencies results in low risk."""
        factor = engine.assess_dependency_risk(
            dependency_count=0,
            critical_dependencies=0,
            parallel_factor=1.0,
        )
        assert factor.raw_score < 0.1

    def test_dependency_risk_many_deps(self, engine):
        """Many dependencies results in higher risk."""
        factor = engine.assess_dependency_risk(
            dependency_count=15,
            critical_dependencies=5,
            parallel_factor=0.0,
        )
        assert factor.raw_score > 0.7

    def test_integrity_risk_with_proof(self, engine):
        """Having proof reduces integrity risk."""
        factor = engine.assess_integrity_risk(
            has_proof=True,
            proof_freshness=1.0,
            validation_depth=3,
        )
        assert factor.raw_score < 0.2

    def test_integrity_risk_no_proof(self, engine):
        """No proof increases integrity risk."""
        factor = engine.assess_integrity_risk(
            has_proof=False,
            proof_freshness=0.0,
            validation_depth=0,
        )
        assert factor.raw_score > 0.5

    def test_governance_risk_compliant(self, engine):
        """Full compliance results in low risk."""
        factor = engine.assess_governance_risk(
            policy_violations=0,
            audit_coverage=1.0,
            approval_status=True,
        )
        assert factor.raw_score < 0.1

    def test_governance_risk_violations(self, engine):
        """Violations increase governance risk."""
        factor = engine.assess_governance_risk(
            policy_violations=5,
            audit_coverage=0.3,
            approval_status=False,
        )
        assert factor.raw_score > 0.6


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GIERiskAttributionEngine - Explanations
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineExplanations:
    """Tests for explanation generation."""

    def test_factor_explanation(self, engine, sample_profile):
        """Can generate factor contribution explanation."""
        explanation = engine.generate_factor_explanation(sample_profile)
        
        assert explanation.explanation_type == ExplanationType.FACTOR_CONTRIBUTION
        assert len(explanation.summary) > 0
        assert len(explanation.contributing_factors) > 0
        assert 0 < explanation.confidence <= 1.0

    def test_counterfactual_already_low(self, engine):
        """Counterfactual for already low-risk profile."""
        profile = AgentRiskProfile(
            agent_gid="TEST",
            task_type="test",
            factors=[
                RiskFactor("RF-1", RiskCategory.EXECUTION, "Test", "", 1.0, 0.1)
            ],
        )
        
        explanation = engine.generate_counterfactual(profile, RiskLevel.LOW)
        
        assert "Already at" in explanation.summary
        assert explanation.explanation_type == ExplanationType.COUNTERFACTUAL

    def test_counterfactual_needs_reduction(self, engine):
        """Counterfactual for high-risk profile."""
        profile = AgentRiskProfile(
            agent_gid="TEST",
            task_type="test",
            factors=[
                RiskFactor("RF-1", RiskCategory.EXECUTION, "Test", "", 1.0, 0.8)
            ],
        )
        
        explanation = engine.generate_counterfactual(profile, RiskLevel.LOW)
        
        assert "reduce" in explanation.summary.lower()
        assert "suggested_changes" in explanation.details


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: GIERiskAttributionEngine - Full Assessment
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineFullAssessment:
    """Tests for full agent assessment."""

    def test_assess_agent_basic(self, engine):
        """Can assess agent with basic metrics."""
        profile = engine.assess_agent(
            agent_gid="GID-01",
            task_type="backend",
            metrics={
                "task_complexity": 0.5,
                "estimated_duration": 120,
                "success_rate": 0.9,
            },
        )
        
        assert profile.agent_gid == "GID-01"
        assert profile.task_type == "backend"
        assert len(profile.factors) == 1
        assert profile.explanation is not None

    def test_assess_agent_full_metrics(self, engine):
        """Can assess agent with all metrics."""
        profile = engine.assess_agent(
            agent_gid="GID-07",
            task_type="data_pipeline",
            metrics={
                "task_complexity": 0.7,
                "estimated_duration": 300,
                "success_rate": 0.85,
                "dependency_count": 5,
                "critical_deps": 2,
                "parallel_factor": 0.6,
                "has_proof": True,
                "proof_freshness": 0.9,
                "validation_depth": 2,
                "policy_violations": 0,
                "audit_coverage": 0.95,
                "approved": True,
            },
        )
        
        assert profile.agent_gid == "GID-07"
        assert len(profile.factors) == 4  # All 4 categories
        assert profile.explanation is not None

    def test_assess_pdo(self, engine):
        """Can create PDO risk attribution."""
        profile1 = engine.assess_agent(
            "GID-01", "task1",
            {"task_complexity": 0.3, "success_rate": 0.95},
        )
        profile2 = engine.assess_agent(
            "GID-02", "task2",
            {"task_complexity": 0.7, "success_rate": 0.8},
        )
        
        attribution = engine.assess_pdo(
            pdo_id="PDO-028",
            agent_profiles=[profile1, profile2],
        )
        
        assert attribution.pdo_id == "PDO-028"
        assert len(attribution.agent_profiles) == 2
        assert len(attribution.recommendations) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Recommendations
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecommendations:
    """Tests for recommendation generation."""

    def test_low_risk_recommendations(self, engine):
        """Low risk gets positive recommendation."""
        profile = AgentRiskProfile(
            agent_gid="TEST",
            task_type="test",
            factors=[
                RiskFactor("RF-1", RiskCategory.EXECUTION, "Test", "", 1.0, 0.1)
            ],
        )
        
        attribution = engine.assess_pdo("PDO-TEST", [profile])
        
        assert any("acceptable" in r.lower() for r in attribution.recommendations)

    def test_high_risk_recommendations(self, engine):
        """High risk gets manual review recommendation."""
        profile = AgentRiskProfile(
            agent_gid="TEST",
            task_type="test",
            factors=[
                RiskFactor("RF-1", RiskCategory.EXECUTION, "Test", "", 1.0, 0.9)
            ],
        )
        
        attribution = engine.assess_pdo("PDO-TEST", [profile])
        
        assert any("manual review" in r.lower() for r in attribution.recommendations)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Singleton
# ═══════════════════════════════════════════════════════════════════════════════

class TestSingleton:
    """Tests for singleton management."""

    def test_get_returns_same_instance(self):
        """get_risk_engine returns same instance."""
        reset_risk_engine()
        engine1 = get_risk_engine()
        engine2 = get_risk_engine()
        assert engine1 is engine2
        reset_risk_engine()

    def test_reset_clears_instance(self):
        """reset_risk_engine clears singleton."""
        reset_risk_engine()
        engine1 = get_risk_engine()
        reset_risk_engine()
        engine2 = get_risk_engine()
        assert engine1 is not engine2
        reset_risk_engine()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_weight_factors(self, engine):
        """Zero weight factors don't cause division errors."""
        profile = AgentRiskProfile(
            agent_gid="TEST",
            task_type="test",
            factors=[
                RiskFactor("RF-1", RiskCategory.EXECUTION, "Test", "", 0.0, 0.5)
            ],
        )
        
        assert profile.overall_score == 0.0

    def test_boundary_scores(self, engine):
        """Boundary scores handled correctly."""
        # Exactly 0.2 should be LOW (not MINIMAL)
        profile = AgentRiskProfile(
            agent_gid="TEST",
            task_type="test",
            factors=[
                RiskFactor("RF-1", RiskCategory.EXECUTION, "Test", "", 1.0, 0.2)
            ],
        )
        assert profile.risk_level == RiskLevel.LOW
        
        # Exactly 0.8 should be CRITICAL
        profile2 = AgentRiskProfile(
            agent_gid="TEST",
            task_type="test",
            factors=[
                RiskFactor("RF-1", RiskCategory.EXECUTION, "Test", "", 1.0, 0.8)
            ],
        )
        assert profile2.risk_level == RiskLevel.CRITICAL

    def test_empty_metrics(self, engine):
        """Empty metrics produces empty factors."""
        profile = engine.assess_agent("TEST", "test", {})
        assert len(profile.factors) == 0
        assert profile.overall_score == 0.0
