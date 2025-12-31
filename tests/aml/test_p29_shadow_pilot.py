# ═══════════════════════════════════════════════════════════════════════════════
# P29 AML Shadow Pilot Test Suite
# PAC-BENSON-P29: AML SHADOW PILOT EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

"""
Test suite for P29 Shadow Pilot components.

Tests:
- Shadow data adapters
- Pattern signal emission
- Typology extensions
- Guardrail enforcement
- Threat validation
- ProofPack ledger
- OCC views
"""

import pytest
from datetime import datetime, timezone


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE IMPORT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestP29ModuleImports:
    """Test that all P29 modules can be imported."""

    def test_import_shadow_pilot(self):
        """Test shadow_pilot module imports."""
        from core.aml.shadow_pilot import (
            ShadowScenario,
            ShadowDataSource,
            ShadowEntity,
            ShadowTransaction,
            ShadowAlertConfig,
            ShadowPilotState,
            ShadowDataGenerator,
            ShadowScenarioRunner,
            ShadowPilotOrchestrator,
        )
        assert ShadowScenario is not None
        assert ShadowDataGenerator is not None
        assert ShadowPilotOrchestrator is not None

    def test_import_shadow_signals(self):
        """Test shadow_signals module imports."""
        from core.aml.shadow_signals import (
            ShadowSignalScenario,
            EmissionMode,
            ShadowSignalBatch,
            SignalExpectation,
            ShadowSignalEmitter,
            ShadowSignalValidator,
        )
        assert ShadowSignalScenario is not None
        assert ShadowSignalEmitter is not None

    def test_import_shadow_typologies(self):
        """Test shadow_typologies module imports."""
        from core.aml.shadow_typologies import (
            FinCENAdvisory,
            FATFHighRisk,
            SectorRisk,
            FinCENTypology,
            SectorIndicator,
            FATFRecommendation,
            ExtendedTypologyLibrary,
        )
        assert FinCENAdvisory is not None
        assert ExtendedTypologyLibrary is not None

    def test_import_shadow_guardrails(self):
        """Test shadow_guardrails module imports."""
        from core.aml.shadow_guardrails import (
            ShadowEnforcementAction,
            ShadowCheckResult,
            ShadowGuardrailCheck,
            EscalationRule,
            ShadowEnforcementResult,
            ShadowGuardrailEnforcer,
        )
        assert ShadowEnforcementAction is not None
        assert ShadowGuardrailEnforcer is not None

    def test_import_shadow_threats(self):
        """Test shadow_threats module imports."""
        from core.aml.shadow_threats import (
            ShadowPilotComponent,
            ThreatApplicability,
            ShadowThreatAssessment,
            ShadowMitigationControl,
            ShadowPilotThreatReport,
            ShadowThreatValidator,
        )
        assert ShadowPilotComponent is not None
        assert ShadowThreatValidator is not None

    def test_import_shadow_ledger(self):
        """Test shadow_ledger module imports."""
        from core.aml.shadow_ledger import (
            ShadowLedgerStatus,
            ShadowAnchorType,
            ShadowLedgerEntry,
            ShadowAnchor,
            ShadowProofPack,
            ShadowMerkleTree,
            ShadowLedgerService,
        )
        assert ShadowLedgerStatus is not None
        assert ShadowLedgerService is not None

    def test_import_shadow_occ(self):
        """Test shadow_occ module imports."""
        from core.aml.shadow_occ import (
            ShadowViewType,
            ViewRefreshMode,
            ShadowCaseView,
            ShadowEvidenceView,
            ShadowDecisionView,
            ShadowPilotMetrics,
            ScenarioResultView,
            ShadowOCCViewRenderer,
        )
        assert ShadowViewType is not None
        assert ShadowOCCViewRenderer is not None


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW DATA GENERATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestShadowDataGenerator:
    """Tests for ShadowDataGenerator."""

    def test_generator_initialization(self):
        """Test generator initializes with seed."""
        from core.aml.shadow_pilot import ShadowDataGenerator
        gen = ShadowDataGenerator(seed=42)
        assert gen._seed == 42

    def test_generator_deterministic(self):
        """Test generator produces deterministic output."""
        from core.aml.shadow_pilot import ShadowDataGenerator
        gen1 = ShadowDataGenerator(seed=42)
        gen2 = ShadowDataGenerator(seed=42)

        entity1 = gen1.generate_entity()
        entity2 = gen2.generate_entity()

        assert entity1.name == entity2.name
        assert entity1.country == entity2.country

    def test_generate_entity(self):
        """Test entity generation."""
        from core.aml.shadow_pilot import ShadowDataGenerator
        gen = ShadowDataGenerator(seed=42)
        entity = gen.generate_entity()

        assert entity.entity_id.startswith("SHENT-")
        assert entity.name is not None
        assert entity.entity_type == "INDIVIDUAL"

    def test_generate_transaction(self):
        """Test transaction generation."""
        from core.aml.shadow_pilot import ShadowDataGenerator
        gen = ShadowDataGenerator(seed=42)
        entity = gen.generate_entity()
        counterparty = gen.generate_entity()

        txn = gen.generate_transaction(
            entity_id=entity.entity_id,
            counterparty_id=counterparty.entity_id,
        )

        assert txn.transaction_id.startswith("SHTXN-")
        assert txn.amount > 0
        assert txn.currency in ["USD", "EUR", "GBP", "JPY", "CNY"]

    def test_generate_alert(self):
        """Test alert generation."""
        from core.aml.shadow_pilot import ShadowDataGenerator, ShadowScenario
        gen = ShadowDataGenerator(seed=42)
        entity = gen.generate_entity()

        alert = gen.generate_alert(
            entity=entity,
            scenario=ShadowScenario.NAME_ONLY_MATCH,
        )

        assert alert.alert_id.startswith("ALERT-")
        assert alert.subject_name == entity.name
        assert alert.metadata.get("shadow_pilot") is True


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW PILOT ORCHESTRATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestShadowPilotOrchestrator:
    """Tests for ShadowPilotOrchestrator."""

    def test_orchestrator_shadow_mode(self):
        """Test orchestrator is always in shadow mode."""
        from core.aml.shadow_pilot import ShadowPilotOrchestrator
        orchestrator = ShadowPilotOrchestrator(seed=42)
        assert orchestrator.is_shadow_mode is True

    def test_start_pilot(self):
        """Test starting a pilot."""
        from core.aml.shadow_pilot import ShadowPilotOrchestrator
        orchestrator = ShadowPilotOrchestrator(seed=42)
        pilot = orchestrator.start_pilot()

        assert pilot.pilot_id.startswith("SHPLT-")
        assert pilot.status == "RUNNING"

    def test_run_tier0_scenarios(self):
        """Test running Tier-0 scenarios."""
        from core.aml.shadow_pilot import ShadowPilotOrchestrator
        orchestrator = ShadowPilotOrchestrator(seed=42)
        orchestrator.start_pilot()

        results = orchestrator.run_tier0_scenarios(count=3)

        assert results["tier"] == "TIER_0"
        assert results["scenarios_run"] > 0

    def test_complete_pilot(self):
        """Test completing a pilot."""
        from core.aml.shadow_pilot import ShadowPilotOrchestrator
        orchestrator = ShadowPilotOrchestrator(seed=42)
        orchestrator.start_pilot()
        orchestrator.run_tier0_scenarios(count=2)

        results = orchestrator.complete_pilot()

        assert results["status"] == "COMPLETED"
        assert "metrics" in results


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW SIGNAL EMITTER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestShadowSignalEmitter:
    """Tests for ShadowSignalEmitter."""

    def test_emitter_shadow_mode(self):
        """Test emitter is always in shadow mode."""
        from core.aml.shadow_signals import ShadowSignalEmitter
        emitter = ShadowSignalEmitter(seed=42)
        assert emitter.is_shadow_mode is True

    def test_emit_structuring_signals(self):
        """Test emitting structuring signals."""
        from core.aml.shadow_signals import ShadowSignalEmitter
        from core.aml.shadow_pilot import ShadowDataGenerator

        gen = ShadowDataGenerator(seed=42)
        entity = gen.generate_entity()

        emitter = ShadowSignalEmitter(seed=42)
        batch = emitter.emit_structuring_signals(entity=entity)

        assert batch.batch_id.startswith("SHBAT-")
        assert batch.signal_count > 0
        assert batch.shadow_mode is True

    def test_emit_velocity_signals(self):
        """Test emitting velocity signals."""
        from core.aml.shadow_signals import ShadowSignalEmitter
        from core.aml.shadow_pilot import ShadowDataGenerator

        gen = ShadowDataGenerator(seed=42)
        entity = gen.generate_entity()

        emitter = ShadowSignalEmitter(seed=42)
        batch = emitter.emit_velocity_signals(entity=entity)

        assert batch.signal_count > 0


# ═══════════════════════════════════════════════════════════════════════════════
# TYPOLOGY LIBRARY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtendedTypologyLibrary:
    """Tests for ExtendedTypologyLibrary."""

    def test_library_initialization(self):
        """Test library initializes with defaults."""
        from core.aml.shadow_typologies import ExtendedTypologyLibrary
        library = ExtendedTypologyLibrary()

        stats = library.get_library_stats()
        assert stats["fincen_typologies"] > 0
        assert stats["sector_indicators"] > 0
        assert stats["fatf_recommendations"] > 0

    def test_get_fincen_typology(self):
        """Test retrieving FinCEN typology."""
        from core.aml.shadow_typologies import ExtendedTypologyLibrary
        library = ExtendedTypologyLibrary()

        typ = library.get_fincen_typology("FIN-2020-A008")
        assert typ is not None
        assert typ.name == "Human Trafficking Financial Indicators"

    def test_prohibited_jurisdiction_check(self):
        """Test prohibited jurisdiction check."""
        from core.aml.shadow_typologies import ExtendedTypologyLibrary
        library = ExtendedTypologyLibrary()

        assert library.is_prohibited_jurisdiction("KP") is True  # North Korea
        assert library.is_prohibited_jurisdiction("US") is False


# ═══════════════════════════════════════════════════════════════════════════════
# GUARDRAIL ENFORCER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestShadowGuardrailEnforcer:
    """Tests for ShadowGuardrailEnforcer."""

    def test_enforcer_shadow_mode(self):
        """Test enforcer is always in shadow mode."""
        from core.aml.shadow_guardrails import ShadowGuardrailEnforcer
        enforcer = ShadowGuardrailEnforcer()
        assert enforcer.is_shadow_mode is True

    def test_tier0_auto_clear_eligible(self):
        """Test Tier-0 is eligible for auto-clear."""
        from core.aml.shadow_guardrails import ShadowGuardrailEnforcer, ShadowCheckResult
        enforcer = ShadowGuardrailEnforcer()

        check = enforcer.check_auto_clear_eligibility(
            tier="TIER_0",
            context={"case_id": "TEST-001", "confidence": 0.98},
        )

        assert check.result == ShadowCheckResult.PASS
        assert not check.is_blocked

    def test_tier2_cannot_auto_clear(self):
        """Test Tier-2 cannot auto-clear."""
        from core.aml.shadow_guardrails import ShadowGuardrailEnforcer, ShadowCheckResult
        enforcer = ShadowGuardrailEnforcer()

        check = enforcer.check_auto_clear_eligibility(
            tier="TIER_2",
            context={"case_id": "TEST-002", "confidence": 0.98},
        )

        assert check.result == ShadowCheckResult.FAIL_HARD
        assert check.requires_escalation

    def test_sanctions_hit_escalates(self):
        """Test sanctions hit forces escalation."""
        from core.aml.shadow_guardrails import ShadowGuardrailEnforcer
        enforcer = ShadowGuardrailEnforcer()

        check = enforcer.check_auto_clear_eligibility(
            tier="TIER_0",
            context={"case_id": "TEST-003", "sanctions_hit": True, "confidence": 0.98},
        )

        assert check.requires_escalation
        assert "GR-AML-003" in check.triggered_guardrails

    def test_validate_governance_invariants(self):
        """Test governance invariant validation."""
        from core.aml.shadow_guardrails import ShadowGuardrailEnforcer
        enforcer = ShadowGuardrailEnforcer()

        invariants = enforcer.validate_governance_invariants()

        # All invariants should pass
        for inv in invariants:
            assert inv["passed"] is True, f"Invariant failed: {inv['invariant']}"


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestShadowThreatValidator:
    """Tests for ShadowThreatValidator."""

    def test_validator_initialization(self):
        """Test validator initializes correctly."""
        from core.aml.shadow_threats import ShadowThreatValidator
        validator = ShadowThreatValidator()

        assert len(validator.SHADOW_THREATS) > 0
        assert len(validator.SHADOW_CONTROLS) > 0

    def test_generate_pilot_report(self):
        """Test generating pilot threat report."""
        from core.aml.shadow_threats import ShadowThreatValidator
        validator = ShadowThreatValidator()

        report = validator.generate_pilot_report("SHPLT-00000001")

        assert report.report_id.startswith("SHTRPT-")
        assert report.total_threats > 0
        assert report.recommendation is not None

    def test_validate_mitigation_coverage(self):
        """Test mitigation coverage validation."""
        from core.aml.shadow_threats import ShadowThreatValidator
        validator = ShadowThreatValidator()

        coverage = validator.validate_mitigation_coverage()

        assert coverage["coverage_rate"] > 0.8  # At least 80% coverage


# ═══════════════════════════════════════════════════════════════════════════════
# SHADOW LEDGER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestShadowLedgerService:
    """Tests for ShadowLedgerService."""

    def test_ledger_shadow_mode(self):
        """Test ledger is always in shadow mode."""
        from core.aml.shadow_ledger import ShadowLedgerService
        ledger = ShadowLedgerService(pilot_id="SHPLT-00000001")
        assert ledger.is_shadow_mode is True

    def test_create_entry(self):
        """Test creating ledger entry."""
        from core.aml.shadow_ledger import ShadowLedgerService
        from core.governance.aml_proofpack import LedgerEntryType

        ledger = ShadowLedgerService(pilot_id="SHPLT-00000001")
        entry = ledger.create_entry(
            entry_type=LedgerEntryType.CASE_CREATED,
            case_id="CASE-001",
            actor="SHADOW_PILOT",
            description="Test case created",
            data={"test": True},
        )

        assert entry.entry_id.startswith("SHLE-")
        assert entry.shadow_mode is True
        assert entry.verify_hash() is True

    def test_create_and_anchor_proofpack(self):
        """Test creating and anchoring ProofPack."""
        from core.aml.shadow_ledger import ShadowLedgerService
        from core.governance.aml_proofpack import ProofPackStatus

        ledger = ShadowLedgerService(pilot_id="SHPLT-00000001")

        # Create ProofPack
        pp = ledger.create_proofpack(case_id="CASE-001")
        assert pp.proofpack_id.startswith("SHPP-")
        assert pp.status == ProofPackStatus.DRAFT

        # Add artifact
        artifact = ledger.add_artifact_to_proofpack(
            proofpack_id=pp.proofpack_id,
            artifact_type="EVIDENCE",
            name="Test Evidence",
            content="Test content",
        )
        assert artifact.artifact_id.startswith("ART-SH-")

        # Finalize
        merkle_root = ledger.finalize_proofpack(pp.proofpack_id)
        assert merkle_root is not None
        assert pp.status == ProofPackStatus.FINALIZED

        # Anchor
        anchor = ledger.anchor_proofpack(pp.proofpack_id)
        assert anchor.anchor_id.startswith("SHANC-")
        assert pp.status == ProofPackStatus.ANCHORED

    def test_verify_ledger_integrity(self):
        """Test ledger integrity verification."""
        from core.aml.shadow_ledger import ShadowLedgerService, VerificationResult
        from core.governance.aml_proofpack import LedgerEntryType

        ledger = ShadowLedgerService(pilot_id="SHPLT-00000001")

        # Add some entries
        for i in range(5):
            ledger.create_entry(
                entry_type=LedgerEntryType.CASE_CREATED,
                case_id=f"CASE-{i:03d}",
                actor="SHADOW_PILOT",
                description=f"Test case {i}",
                data={"index": i},
            )

        # Verify integrity
        from core.governance.aml_proofpack import VerificationResult
        result = ledger.verify_ledger_integrity()
        assert result == VerificationResult.VALID


# ═══════════════════════════════════════════════════════════════════════════════
# MERKLE TREE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestShadowMerkleTree:
    """Tests for ShadowMerkleTree."""

    def test_empty_tree(self):
        """Test empty tree has deterministic root."""
        from core.aml.shadow_ledger import ShadowMerkleTree
        tree = ShadowMerkleTree()
        root = tree.compute_root()
        assert root is not None

    def test_single_leaf(self):
        """Test tree with single leaf."""
        from core.aml.shadow_ledger import ShadowMerkleTree
        tree = ShadowMerkleTree()
        tree.add_leaf("test_hash_1")
        root = tree.compute_root()
        assert root is not None

    def test_multiple_leaves(self):
        """Test tree with multiple leaves."""
        from core.aml.shadow_ledger import ShadowMerkleTree
        tree = ShadowMerkleTree()
        tree.add_leaf("hash1")
        tree.add_leaf("hash2")
        tree.add_leaf("hash3")

        root = tree.compute_root()
        assert tree.leaf_count == 3
        assert root is not None

    def test_proof_verification(self):
        """Test Merkle proof verification."""
        from core.aml.shadow_ledger import ShadowMerkleTree
        tree = ShadowMerkleTree()
        tree.add_leaf("hash1")
        tree.add_leaf("hash2")
        tree.add_leaf("hash3")
        tree.add_leaf("hash4")

        root = tree.compute_root()
        proof = tree.get_proof(1)  # Proof for second leaf

        assert tree.verify_proof("hash2", proof, root) is True


# ═══════════════════════════════════════════════════════════════════════════════
# OCC VIEW RENDERER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestShadowOCCViewRenderer:
    """Tests for ShadowOCCViewRenderer."""

    def test_renderer_shadow_mode(self):
        """Test renderer is always in shadow mode."""
        from core.aml.shadow_occ import ShadowOCCViewRenderer
        renderer = ShadowOCCViewRenderer(pilot_id="SHPLT-00000001")
        assert renderer.is_shadow_mode is True

    def test_render_pilot_dashboard(self):
        """Test rendering pilot dashboard."""
        from core.aml.shadow_occ import ShadowOCCViewRenderer, ShadowViewType
        renderer = ShadowOCCViewRenderer(pilot_id="SHPLT-00000001")

        dashboard = renderer.render_pilot_dashboard()

        assert dashboard["view_type"] == ShadowViewType.PILOT_DASHBOARD.value
        assert dashboard["shadow_mode"] is True
        assert "metrics" in dashboard

    def test_render_case_queue(self):
        """Test rendering case queue."""
        from core.aml.shadow_occ import ShadowOCCViewRenderer, ShadowCaseView
        renderer = ShadowOCCViewRenderer(pilot_id="SHPLT-00000001")

        # Register a case
        case = ShadowCaseView(
            case_id="CASE-001",
            entity_name="Test Entity",
            tier="TIER_0",
            status="OPEN",
            scenario="NAME_ONLY_MATCH",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        renderer.register_case(case)

        queue = renderer.render_case_queue()

        assert queue["total_cases"] == 1
        assert len(queue["cases"]) == 1

    def test_render_tier_breakdown(self):
        """Test rendering tier breakdown."""
        from core.aml.shadow_occ import ShadowOCCViewRenderer, ShadowCaseView
        renderer = ShadowOCCViewRenderer(pilot_id="SHPLT-00000001")

        # Register cases for each tier
        for tier in ["TIER_0", "TIER_1", "TIER_2"]:
            case = ShadowCaseView(
                case_id=f"CASE-{tier}",
                entity_name=f"Entity {tier}",
                tier=tier,
                status="OPEN",
                scenario="TEST",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            renderer.register_case(case)

        breakdown = renderer.render_tier_breakdown()

        assert breakdown["total_cases"] == 3
        assert len(breakdown["breakdown"]) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# GOVERNANCE INVARIANT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestP29GovernanceInvariants:
    """Tests for P29 governance invariants."""

    def test_tier2_never_auto_clears(self):
        """CRITICAL: Tier-2+ cases must never auto-clear."""
        from core.aml.shadow_guardrails import ShadowGuardrailEnforcer

        enforcer = ShadowGuardrailEnforcer()

        for tier in ["TIER_2", "TIER_3", "TIER_SAR"]:
            check = enforcer.check_auto_clear_eligibility(
                tier=tier,
                context={"case_id": "TEST", "confidence": 0.99},
            )
            assert check.requires_escalation, f"{tier} should require escalation"

    def test_shadow_mode_always_enabled(self):
        """CRITICAL: Shadow mode must always be enabled."""
        from core.aml.shadow_pilot import ShadowPilotOrchestrator
        from core.aml.shadow_signals import ShadowSignalEmitter
        from core.aml.shadow_guardrails import ShadowGuardrailEnforcer
        from core.aml.shadow_ledger import ShadowLedgerService
        from core.aml.shadow_occ import ShadowOCCViewRenderer

        assert ShadowPilotOrchestrator(seed=42).is_shadow_mode is True
        assert ShadowSignalEmitter(seed=42).is_shadow_mode is True
        assert ShadowGuardrailEnforcer().is_shadow_mode is True
        assert ShadowLedgerService("TEST").is_shadow_mode is True
        assert ShadowOCCViewRenderer("TEST").is_shadow_mode is True

    def test_sanctions_hit_always_escalates(self):
        """CRITICAL: Sanctions hit must always trigger escalation."""
        from core.aml.shadow_guardrails import ShadowGuardrailEnforcer

        enforcer = ShadowGuardrailEnforcer()

        # Even Tier-0 with sanctions hit must escalate
        check = enforcer.check_auto_clear_eligibility(
            tier="TIER_0",
            context={"case_id": "TEST", "sanctions_hit": True, "confidence": 0.99},
        )
        assert check.requires_escalation

    def test_pep_hit_always_escalates(self):
        """CRITICAL: PEP hit must always trigger escalation."""
        from core.aml.shadow_guardrails import ShadowGuardrailEnforcer

        enforcer = ShadowGuardrailEnforcer()

        check = enforcer.check_auto_clear_eligibility(
            tier="TIER_0",
            context={"case_id": "TEST", "pep_hit": True, "confidence": 0.99},
        )
        assert check.requires_escalation

    def test_low_confidence_escalates(self):
        """CRITICAL: Low confidence must trigger escalation."""
        from core.aml.shadow_guardrails import ShadowGuardrailEnforcer

        enforcer = ShadowGuardrailEnforcer()

        check = enforcer.check_auto_clear_eligibility(
            tier="TIER_0",
            context={"case_id": "TEST", "confidence": 0.80},
        )
        assert check.requires_escalation
        assert "GR-AML-007" in check.triggered_guardrails
