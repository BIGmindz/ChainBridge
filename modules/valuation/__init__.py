"""
ChainBridge Valuation Framework
================================

PAC Reference: PAC-VAL-P213-AGENT-UNIVERSITY-STARTUP-VALUATION
Authority: Jeffrey [GID-CONST-01] + BENSON [GID-00]
Lead Agent: SAGE [GID-14]

Constitutional Oversight: SCRAM [GID-13]

This module provides comprehensive startup valuation capabilities for ChainBridge,
enabling investor-ready materials with audit-defensible methodology.

Modules:
- baseline_metrics: Current ARR, revenue composition, growth metrics
- market_analysis: TAM/SAM/SOM calculations with data source citations
- ip_valuation: Post-quantum crypto IP portfolio assessment
- financial_modeling: Multi-method valuation triangulation
- investor_materials: Presentation decks, executive summaries, visualizations
- audit_trail: Complete documentation for due diligence review

Agents:
- SAGE [GID-14]: Strategic lead, overall framework ownership
- ORACLE [GID-15]: Market research, TAM/SAM/SOM analysis
- ARBITER [GID-16]: Legal counsel, IP valuation
- SCRIBE [GID-17]: Content creation, investor materials
- SCRAM [GID-13]: Emergency oversight, governance enforcement
"""

__version__ = "2.0.0"
__author__ = "SAGE [GID-14] + Agent Swarm"
__pac__ = "PAC-VAL-P213-AGENT-UNIVERSITY-STARTUP-VALUATION"

from pathlib import Path

# Module paths
MODULE_ROOT = Path(__file__).parent
REPORTS_DIR = MODULE_ROOT.parent.parent / "reports" / "valuation"
DATA_DIR = MODULE_ROOT / "data"
TEMPLATES_DIR = MODULE_ROOT / "templates"

# Create directories if they don't exist
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Constitutional constraints
CONSERVATIVE_MODELING = True
AUDIT_TRAIL_REQUIRED = True
SCRAM_OVERSIGHT_ACTIVE = True

# Import core modules
from .baseline_metrics import (
    get_verified_baseline,
    RevenueStatus,
    ValuationMethodology,
    BaselineMetrics
)

from .ai_native_economics import (
    get_chainbridge_fte_model,
    calculate_valuation_premium,
    AINativeEconomicsModel,
    INVESTOR_KEY_MESSAGES
)

from .tam_sam_som import (
    get_chainbridge_market_analysis,
    TAMSAMSOMAnalysis,
    CHAINBRIDGE_DIFFERENTIATORS
)

from .ip_portfolio import (
    get_chainbridge_ip_portfolio,
    IPPortfolio,
    CONSTITUTIONAL_AI_MOAT
)

from .pre_revenue_valuation import (
    calculate_chainbridge_valuation,
    ValuationTriangulation,
    ValuationMethod
)

__all__ = [
    # Baseline
    'get_verified_baseline',
    'RevenueStatus',
    'ValuationMethodology',
    'BaselineMetrics',
    
    # AI-Native Economics
    'get_chainbridge_fte_model',
    'calculate_valuation_premium',
    'AINativeEconomicsModel',
    'INVESTOR_KEY_MESSAGES',
    
    # Market Analysis
    'get_chainbridge_market_analysis',
    'TAMSAMSOMAnalysis',
    'CHAINBRIDGE_DIFFERENTIATORS',
    
    # IP Portfolio
    'get_chainbridge_ip_portfolio',
    'IPPortfolio',
    'CONSTITUTIONAL_AI_MOAT',
    
    # Valuation
    'calculate_chainbridge_valuation',
    'ValuationTriangulation',
    'ValuationMethod',
]

# Constitutional compliance check
def _verify_invariants():
    """Verify INV-VAL invariants on module load."""
    baseline = get_verified_baseline()
    assert baseline.revenue_status == RevenueStatus.PRE_REVENUE, \
        "VIOLATION: INV-VAL-004-CORRECTED"
    assert not baseline.revenue_multiple_applicable, \
        "VIOLATION: INV-VAL-007-NEW"
    return True

CONSTITUTIONAL_COMPLIANCE = _verify_invariants()

