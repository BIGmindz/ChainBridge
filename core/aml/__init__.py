# ═══════════════════════════════════════════════════════════════════════════════
# AML Module — Anti-Money Laundering Governed Agent Program
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# ═══════════════════════════════════════════════════════════════════════════════

"""
AML Module Exports

This module provides the core AML (Anti-Money Laundering) infrastructure for
ChainBridge's governed agent program. All components operate in SHADOW mode
with FAIL-CLOSED governance.

SCOPE:
    - Tier-0 / Tier-1 False Positive Automation ONLY
    - No autonomous Tier-2+ clearance
    - No unsupervised SAR filing
    - No live neural learning

COMPONENTS:
    - Case Engine: Alert intake, case management, tier routing
    - Evidence Graph: KYC, transactions, adverse media correlation
    - Typology Library: AML patterns and red flags
    - Pattern Signals: Behavioral analysis (SHADOW MODE)
    - Tier Router: Decision proposal engine
"""

from core.aml.case_engine import (
    # Enums
    AlertSource,
    AlertPriority,
    CaseStatus,
    CaseTier,
    DecisionOutcome,
    EvidenceType,
    # Data Classes
    AMLAlert,
    AMLCase,
    CaseEvidence,
    CaseDecision,
    CaseNarrative,
    # Services
    AMLCaseEngine,
)

from core.aml.evidence_graph import (
    # Enums
    EntityType,
    RelationType,
    EvidenceStrength,
    RiskIndicator,
    # Data Classes
    Entity,
    Relationship,
    EvidenceNode,
    RiskSignal,
    # Services
    EvidenceGraph,
    EvidenceGraphService,
)

from core.aml.tier_router import (
    # Enums
    RoutingDecision,
    EscalationReason,
    # Data Classes
    TierCriteria,
    RoutingResult,
    EscalationContext,
    # Services
    TierRouter,
)

from core.aml.pattern_signals import (
    # Enums
    PatternType,
    SignalSeverity,
    DetectionMethod,
    # Data Classes
    PatternRule,
    PatternSignal,
    TransactionMetrics,
    # Services
    PatternAnalyzer,
)

from core.aml.typology_library import (
    # Enums
    TypologyCategory,
    RedFlagCategory,
    RiskLevel,
    JurisdictionRiskType,
    # Data Classes
    Typology,
    RedFlag,
    JurisdictionRisk,
    # Services
    TypologyLibrary,
)

from core.aml.tier_guardrails import (
    # Enums
    GuardrailType,
    ViolationSeverity,
    ProductScope,
    # Data Classes
    Guardrail,
    GuardrailViolation,
    TierBoundary,
    # Services
    GuardrailEngine,
)

__all__ = [
    # Case Engine
    "AlertSource",
    "AlertPriority",
    "CaseStatus",
    "CaseTier",
    "DecisionOutcome",
    "EvidenceType",
    "AMLAlert",
    "AMLCase",
    "CaseEvidence",
    "CaseDecision",
    "CaseNarrative",
    "AMLCaseEngine",
    # Evidence Graph
    "EntityType",
    "RelationType",
    "EvidenceStrength",
    "RiskIndicator",
    "Entity",
    "Relationship",
    "EvidenceNode",
    "RiskSignal",
    "EvidenceGraph",
    "EvidenceGraphService",
    # Tier Router
    "RoutingDecision",
    "EscalationReason",
    "TierCriteria",
    "RoutingResult",
    "EscalationContext",
    "TierRouter",
    # Pattern Signals
    "PatternType",
    "SignalSeverity",
    "DetectionMethod",
    "PatternRule",
    "PatternSignal",
    "TransactionMetrics",
    "PatternAnalyzer",
    # Typology Library
    "TypologyCategory",
    "RedFlagCategory",
    "RiskLevel",
    "JurisdictionRiskType",
    "Typology",
    "RedFlag",
    "JurisdictionRisk",
    "TypologyLibrary",
    # Tier Guardrails
    "GuardrailType",
    "ViolationSeverity",
    "ProductScope",
    "Guardrail",
    "GuardrailViolation",
    "TierBoundary",
    "GuardrailEngine",
]
