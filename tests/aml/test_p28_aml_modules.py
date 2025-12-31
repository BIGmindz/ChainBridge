# ═══════════════════════════════════════════════════════════════════════════════
# P28 AML Module Smoke Tests
# PAC-BENSON-P28: AML GOVERNED AGENT PROGRAM
# Agent: DAN (GID-07)
# ═══════════════════════════════════════════════════════════════════════════════

"""
Smoke tests verifying P28 AML module imports and enums are correctly defined.

Tests validate:
    - All P28 modules can be imported
    - Core enums have expected values
    - Key classes exist with expected attributes
"""

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE IMPORT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestP28ModuleImports:
    """Verify all P28 modules can be imported."""

    def test_import_case_engine(self):
        from core.aml import case_engine
        assert hasattr(case_engine, 'AMLCaseEngine')
        assert hasattr(case_engine, 'AMLAlert')
        assert hasattr(case_engine, 'CaseDecision')

    def test_import_evidence_graph(self):
        from core.aml import evidence_graph
        assert hasattr(evidence_graph, 'EvidenceGraph')
        assert hasattr(evidence_graph, 'Entity')

    def test_import_tier_router(self):
        from core.aml import tier_router
        assert hasattr(tier_router, 'TierRouter')
        assert hasattr(tier_router, 'RoutingDecision')

    def test_import_pattern_signals(self):
        from core.aml import pattern_signals
        assert hasattr(pattern_signals, 'PatternAnalyzer')
        assert hasattr(pattern_signals, 'PatternType')

    def test_import_typology_library(self):
        from core.aml import typology_library
        assert hasattr(typology_library, 'TypologyLibrary')
        assert hasattr(typology_library, 'TypologyCategory')

    def test_import_tier_guardrails(self):
        from core.aml import tier_guardrails
        assert hasattr(tier_guardrails, 'GuardrailEngine')

    def test_import_aml_proofpack(self):
        from core.governance import aml_proofpack
        assert hasattr(aml_proofpack, 'AMLProofPack')
        assert hasattr(aml_proofpack, 'AMLLedger')

    def test_import_aml_panel(self):
        from core.occ import aml_panel
        assert hasattr(aml_panel, 'AMLOCCPanel')
        assert hasattr(aml_panel, 'PanelType')

    def test_import_aml_threat_model(self):
        from core.security import aml_threat_model
        assert hasattr(aml_threat_model, 'AMLThreatModel')
        assert hasattr(aml_threat_model, 'ThreatCategory')

    def test_import_aml_invariants(self):
        from core.governance import aml_invariants
        assert hasattr(aml_invariants, 'AMLInvariantEngine')


# ═══════════════════════════════════════════════════════════════════════════════
# CASE ENGINE ENUM TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestCaseEngineEnums:
    """Tests for case engine enums."""

    def test_alert_source_enum(self):
        from core.aml.case_engine import AlertSource
        assert AlertSource.SANCTIONS_SCREENING.value == "SANCTIONS_SCREENING"
        assert AlertSource.TRANSACTION_MONITORING.value == "TRANSACTION_MONITORING"
        assert AlertSource.PEP_SCREENING.value == "PEP_SCREENING"

    def test_alert_priority_enum(self):
        from core.aml.case_engine import AlertPriority
        assert AlertPriority.LOW.value == "LOW"
        assert AlertPriority.MEDIUM.value == "MEDIUM"
        assert AlertPriority.HIGH.value == "HIGH"
        assert AlertPriority.CRITICAL.value == "CRITICAL"

    def test_case_status_enum(self):
        from core.aml.case_engine import CaseStatus
        assert CaseStatus.CREATED.value == "CREATED"
        assert CaseStatus.CLEARED.value == "CLEARED"
        assert CaseStatus.ESCALATED.value == "ESCALATED"

    def test_case_tier_enum(self):
        from core.aml.case_engine import CaseTier
        assert CaseTier.TIER_0.value == "TIER_0"
        assert CaseTier.TIER_1.value == "TIER_1"
        assert CaseTier.TIER_2.value == "TIER_2"
        assert CaseTier.TIER_3.value == "TIER_3"
        assert CaseTier.TIER_SAR.value == "TIER_SAR"

    def test_decision_outcome_enum(self):
        from core.aml.case_engine import DecisionOutcome
        assert DecisionOutcome.CLEAR.value == "CLEAR"
        assert DecisionOutcome.ESCALATE.value == "ESCALATE"
        assert DecisionOutcome.SAR_REVIEW.value == "SAR_REVIEW"

    def test_evidence_type_enum(self):
        from core.aml.case_engine import EvidenceType
        assert EvidenceType.KYC_DATA.value == "KYC_DATA"
        assert EvidenceType.TRANSACTION_HISTORY.value == "TRANSACTION_HISTORY"


# ═══════════════════════════════════════════════════════════════════════════════
# TIER ROUTER ENUM TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestTierRouterEnums:
    """Tests for tier router enums."""

    def test_routing_decision_enum(self):
        from core.aml.tier_router import RoutingDecision
        assert RoutingDecision.AUTO_CLEAR.value == "AUTO_CLEAR"
        assert RoutingDecision.ESCALATE_ANALYST.value == "ESCALATE_ANALYST"
        assert RoutingDecision.ESCALATE_SENIOR.value == "ESCALATE_SENIOR"
        assert RoutingDecision.ESCALATE_SAR.value == "ESCALATE_SAR"

    def test_escalation_reason_enum(self):
        from core.aml.tier_router import EscalationReason
        assert EscalationReason.HIGH_RISK_MATCH.value == "HIGH_RISK_MATCH"
        assert EscalationReason.MULTIPLE_RISK_SIGNALS.value == "MULTIPLE_RISK_SIGNALS"


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN SIGNALS ENUM TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPatternSignalsEnums:
    """Tests for pattern signals enums."""

    def test_pattern_type_enum(self):
        from core.aml.pattern_signals import PatternType
        assert PatternType.STRUCTURING.value == "STRUCTURING"
        assert PatternType.LAYERING.value == "LAYERING"
        assert PatternType.VELOCITY_SPIKE.value == "VELOCITY_SPIKE"

    def test_signal_severity_enum(self):
        from core.aml.pattern_signals import SignalSeverity
        assert SignalSeverity.LOW.value == "LOW"
        assert SignalSeverity.MEDIUM.value == "MEDIUM"
        assert SignalSeverity.HIGH.value == "HIGH"


# ═══════════════════════════════════════════════════════════════════════════════
# TYPOLOGY LIBRARY ENUM TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestTypologyLibraryEnums:
    """Tests for typology library enums."""

    def test_typology_category_enum(self):
        from core.aml.typology_library import TypologyCategory
        assert TypologyCategory.TRADE_BASED.value == "TRADE_BASED"
        assert TypologyCategory.VIRTUAL_ASSETS.value == "VIRTUAL_ASSETS"

    def test_red_flag_category_enum(self):
        from core.aml.typology_library import RedFlagCategory
        assert RedFlagCategory.CUSTOMER.value == "CUSTOMER"
        assert RedFlagCategory.TRANSACTION.value == "TRANSACTION"

    def test_risk_level_enum(self):
        from core.aml.typology_library import RiskLevel
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.HIGH.value == "HIGH"
        assert RiskLevel.PROHIBITED.value == "PROHIBITED"

    def test_jurisdiction_risk_type_enum(self):
        from core.aml.typology_library import JurisdictionRiskType
        assert JurisdictionRiskType.FATF_BLACKLIST.value == "FATF_BLACKLIST"
        assert JurisdictionRiskType.SANCTIONS.value == "SANCTIONS"


# ═══════════════════════════════════════════════════════════════════════════════
# EVIDENCE GRAPH ENUM TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestEvidenceGraphEnums:
    """Tests for evidence graph enums."""

    def test_entity_type_enum(self):
        from core.aml.evidence_graph import EntityType
        assert EntityType.INDIVIDUAL.value == "INDIVIDUAL"
        assert EntityType.ORGANIZATION.value == "ORGANIZATION"

    def test_relation_type_enum(self):
        from core.aml.evidence_graph import RelationType
        assert RelationType.OWNS.value == "OWNS"

    def test_evidence_strength_enum(self):
        from core.aml.evidence_graph import EvidenceStrength
        assert EvidenceStrength.STRONG.value == "STRONG"
        assert EvidenceStrength.WEAK.value == "WEAK"


# ═══════════════════════════════════════════════════════════════════════════════
# PROOFPACK ENUM TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestProofpackEnums:
    """Tests for proofpack enums."""

    def test_proofpack_status_enum(self):
        from core.governance.aml_proofpack import ProofPackStatus
        assert ProofPackStatus.DRAFT.value == "DRAFT"
        assert ProofPackStatus.FINALIZED.value == "FINALIZED"
        assert ProofPackStatus.ANCHORED.value == "ANCHORED"

    def test_ledger_entry_type_enum(self):
        from core.governance.aml_proofpack import LedgerEntryType
        assert LedgerEntryType.CASE_CREATED.value == "CASE_CREATED"
        assert LedgerEntryType.EVIDENCE_ADDED.value == "EVIDENCE_ADDED"

    def test_verification_result_enum(self):
        from core.governance.aml_proofpack import VerificationResult
        assert VerificationResult.VALID.value == "VALID"
        assert VerificationResult.INVALID.value == "INVALID"


# ═══════════════════════════════════════════════════════════════════════════════
# OCC PANEL ENUM TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestOCCPanelEnums:
    """Tests for OCC panel enums."""

    def test_panel_type_enum(self):
        from core.occ.aml_panel import PanelType
        assert PanelType.QUEUE_STATUS.value == "QUEUE_STATUS"
        assert PanelType.TIER_DISTRIBUTION.value == "TIER_DISTRIBUTION"

    def test_alert_level_enum(self):
        from core.occ.aml_panel import AlertLevel
        assert AlertLevel.NORMAL.value == "NORMAL"
        assert AlertLevel.WARNING.value == "WARNING"
        assert AlertLevel.CRITICAL.value == "CRITICAL"

    def test_metric_trend_enum(self):
        from core.occ.aml_panel import MetricTrend
        assert MetricTrend.UP.value == "UP"
        assert MetricTrend.DOWN.value == "DOWN"
        assert MetricTrend.STABLE.value == "STABLE"

    def test_accessibility_role_enum(self):
        from core.occ.aml_panel import AccessibilityRole
        assert AccessibilityRole.STATUS.value == "status"
        assert AccessibilityRole.TABLE.value == "table"


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT MODEL ENUM TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestThreatModelEnums:
    """Tests for threat model enums."""

    def test_threat_category_enum(self):
        from core.security.aml_threat_model import ThreatCategory
        assert ThreatCategory.DECISION_INTEGRITY.value == "DECISION_INTEGRITY"
        assert ThreatCategory.DATA_INTEGRITY.value == "DATA_INTEGRITY"

    def test_threat_severity_enum(self):
        from core.security.aml_threat_model import ThreatSeverity
        assert ThreatSeverity.CRITICAL.value == "CRITICAL"
        assert ThreatSeverity.HIGH.value == "HIGH"
        assert ThreatSeverity.LOW.value == "LOW"

    def test_mitigation_status_enum(self):
        from core.security.aml_threat_model import MitigationStatus
        assert MitigationStatus.IMPLEMENTED.value == "IMPLEMENTED"
        assert MitigationStatus.PLANNED.value == "PLANNED"


# ═══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestP28GovernanceInvariants:
    """Tests for P28 governance invariants."""

    def test_tier_0_and_tier_1_auto_clearable(self):
        """Verify Tier-0 and Tier-1 are the only auto-clearable tiers."""
        from core.aml.case_engine import CaseTier, CaseDecision, DecisionOutcome
        from datetime import datetime, timezone

        # Tier-0 with high confidence should be auto-clearable
        decision_t0 = CaseDecision(
            decision_id="DEC-00000001",
            case_id="CASE-001",
            outcome=DecisionOutcome.CLEAR,
            tier=CaseTier.TIER_0,
            narrative_id="NARR-001",
            confidence=0.98,
            decided_at=datetime.now(timezone.utc).isoformat(),
            decided_by="SYSTEM",
        )
        assert decision_t0.is_auto_clearable is True

        # Tier-2 should NOT be auto-clearable
        decision_t2 = CaseDecision(
            decision_id="DEC-00000002",
            case_id="CASE-002",
            outcome=DecisionOutcome.CLEAR,
            tier=CaseTier.TIER_2,
            narrative_id="NARR-002",
            confidence=0.98,
            decided_at=datetime.now(timezone.utc).isoformat(),
            decided_by="SYSTEM",
        )
        assert decision_t2.is_auto_clearable is False
        assert decision_t2.requires_human_review is True

    def test_tier_sar_requires_human_review(self):
        """Verify Tier-SAR always requires human review."""
        from core.aml.case_engine import CaseTier, CaseDecision, DecisionOutcome
        from datetime import datetime, timezone

        decision = CaseDecision(
            decision_id="DEC-00000003",
            case_id="CASE-003",
            outcome=DecisionOutcome.SAR_REVIEW,
            tier=CaseTier.TIER_SAR,
            narrative_id="NARR-003",
            confidence=0.75,
            decided_at=datetime.now(timezone.utc).isoformat(),
            decided_by="SYSTEM",
        )
        assert decision.requires_human_review is True
        assert decision.is_auto_clearable is False

    def test_low_confidence_blocks_auto_clear(self):
        """Verify low confidence blocks auto-clearance even for Tier-0."""
        from core.aml.case_engine import CaseTier, CaseDecision, DecisionOutcome
        from datetime import datetime, timezone

        decision = CaseDecision(
            decision_id="DEC-00000004",
            case_id="CASE-004",
            outcome=DecisionOutcome.CLEAR,
            tier=CaseTier.TIER_0,
            narrative_id="NARR-004",
            confidence=0.90,  # Below 0.95 threshold
            decided_at=datetime.now(timezone.utc).isoformat(),
            decided_by="SYSTEM",
        )
        assert decision.is_auto_clearable is False
