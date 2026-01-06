"""
Testing Module Initialization

PAC Reference: PAC-JEFFREY-P48
Provides test intelligence and optimization capabilities.
"""

from core.occ.testing.test_intelligence import (
    TestIntelligenceEngine,
    TestIntelligenceScore,
    TestExecutionRecord,
    RiskTier,
    BlastRadiusCategory,
    get_test_intelligence_engine,
    reset_test_intelligence_engine,
    generate_pre_ber_risk_brief,
)

from core.occ.testing.pytest_optimizer import (
    PyTestOptimizer,
    TestMetadata,
    OptimizationPlan,
    OptimizationStrategy,
    ParallelGroup,
    get_pytest_optimizer,
    reset_pytest_optimizer,
)

__all__ = [
    # Test Intelligence
    "TestIntelligenceEngine",
    "TestIntelligenceScore",
    "TestExecutionRecord",
    "RiskTier",
    "BlastRadiusCategory",
    "get_test_intelligence_engine",
    "reset_test_intelligence_engine",
    "generate_pre_ber_risk_brief",
    # PyTest Optimizer
    "PyTestOptimizer",
    "TestMetadata",
    "OptimizationPlan",
    "OptimizationStrategy",
    "ParallelGroup",
    "get_pytest_optimizer",
    "reset_pytest_optimizer",
]
