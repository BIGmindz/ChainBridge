"""
Tests for PAC-020: PDO Artifact Engine
════════════════════════════════════════════════════════════════════════════════

Tests that validate:
- PDO created iff BER emitted
- Missing Proof/Decision/Outcome → FAIL
- Agent cannot create PDO
- Drafting surface cannot create PDO
- Hash immutability enforced
- One-to-one: PAC → BER → PDO

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-PDO-ARTIFACT-ENGINE-020
Effective Date: 2025-12-26
"""

import hashlib
import json
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from core.governance.pdo_artifact import (
    PDOArtifact,
    PDOArtifactFactory,
    PDOAuthorityError,
    PDOCreationError,
    PDODuplicateError,
    PDOIncompleteError,
    PDOInvalidOutcomeError,
    PDO_AUTHORITY,
    VALID_OUTCOMES,
    compute_hash,
    compute_proof_hash,
    compute_decision_hash,
    compute_outcome_hash,
    compute_pdo_hash,
    verify_pdo_chain,
    verify_pdo_full,
)
from core.governance.pdo_registry import (
    PDORegistry,
    PDONotFoundError,
    PDORegistryError,
    get_pdo_registry,
    reset_pdo_registry,
)
from core.governance.pac_schema import (
    BERStatus,
    PACBuilder,
    PACDiscipline,
    PACMode,
    WRAPStatus,
)
from core.governance.orchestration_engine import (
    GovernanceOrchestrationEngine,
    get_orchestration_engine,
    reset_orchestration_engine,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test."""
    reset_pdo_registry()
    reset_orchestration_engine()
    yield
    reset_pdo_registry()
    reset_orchestration_engine()


@pytest.fixture
def sample_wrap_data():
    """Sample WRAP data for testing."""
    return {
        "pac_id": "PAC-TEST-001",
        "status": "COMPLETE",
        "from_gid": "GID-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "proof": {"work_done": True, "artifacts": ["file1.py", "file2.py"]},
    }


@pytest.fixture
def sample_ber_data():
    """Sample BER data for testing."""
    return {
        "pac_id": "PAC-TEST-001",
        "status": "APPROVE",
        "issuer": "GID-00",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": "ACCEPTED",
    }


@pytest.fixture
def valid_pac():
    """Create a valid PAC for testing."""
    return (
        PACBuilder()
        .with_id("PAC-TEST-PDO-001")
        .with_issuer("Jeffrey")
        .with_target("BENSON")
        .with_objective("Test PDO creation")
        .with_mode(PACMode.EXECUTION)
        .with_discipline(PACDiscipline.GOLD_STANDARD)
        .with_execution_plan("Execute PDO artifact tests")
        .add_deliverable("Create PDO artifact")
        .add_constraint("PDO must be immutable")
        .add_success_criterion("All tests pass")
        .with_dispatch("GID-01", "TEST_AGENT", "testing", PACMode.EXECUTION)
        .with_wrap_obligation()
        .with_ber_obligation()
        .with_final_state()
        .build()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDO ARTIFACT STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOArtifactStructure:
    """Tests for PDOArtifact dataclass structure."""
    
    def test_pdo_artifact_is_frozen(self, sample_wrap_data, sample_ber_data):
        """INV-PDO-003: PDO is immutable after creation."""
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        # Attempt to modify should raise
        with pytest.raises(AttributeError):
            pdo.pac_id = "PAC-MODIFIED"
        
        with pytest.raises(AttributeError):
            pdo.pdo_hash = "modified_hash"
    
    def test_pdo_artifact_has_required_fields(self, sample_wrap_data, sample_ber_data):
        """PDOArtifact has all required fields."""
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        # Identity
        assert pdo.pdo_id.startswith("pdo_")
        assert pdo.pac_id == "PAC-001"
        
        # Component IDs
        assert pdo.wrap_id == "wrap_001"
        assert pdo.ber_id == "ber_001"
        
        # Authority
        assert pdo.issuer == "GID-00"
        
        # Hash chain
        assert len(pdo.proof_hash) == 64
        assert len(pdo.decision_hash) == 64
        assert len(pdo.outcome_hash) == 64
        assert len(pdo.pdo_hash) == 64
        
        # Timestamps
        assert pdo.proof_at
        assert pdo.decision_at
        assert pdo.outcome_at
        assert pdo.created_at
        
        # Status
        assert pdo.outcome_status == "ACCEPTED"
    
    def test_pdo_artifact_properties(self, sample_wrap_data, sample_ber_data):
        """PDOArtifact properties work correctly."""
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        assert pdo.is_accepted is True
        assert pdo.is_corrective is False
        assert pdo.is_rejected is False
        assert pdo.is_valid is True
    
    def test_pdo_artifact_serialization(self, sample_wrap_data, sample_ber_data):
        """PDOArtifact serializes to dict and JSON."""
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        # To dict
        d = pdo.to_dict()
        assert d["pac_id"] == "PAC-001"
        assert d["issuer"] == "GID-00"
        
        # To JSON
        j = pdo.to_json()
        parsed = json.loads(j)
        assert parsed["pac_id"] == "PAC-001"
        
        # Round-trip
        restored = PDOArtifact.from_dict(d)
        assert restored.pdo_id == pdo.pdo_id
        assert restored.pdo_hash == pdo.pdo_hash


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDO AUTHORITY (INV-PDO-002)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOAuthority:
    """Tests for INV-PDO-002: Only GID-00 may create PDO."""
    
    def test_gid00_can_create_pdo(self, sample_wrap_data, sample_ber_data):
        """GID-00 (ORCHESTRATION_ENGINE) can create PDO."""
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer="GID-00",
        )
        
        assert pdo.issuer == "GID-00"
    
    def test_agent_cannot_create_pdo(self, sample_wrap_data, sample_ber_data):
        """Agent (GID-01+) cannot create PDO."""
        with pytest.raises(PDOAuthorityError) as exc_info:
            PDOArtifactFactory.create(
                pac_id="PAC-001",
                wrap_id="wrap_001",
                wrap_data=sample_wrap_data,
                ber_id="ber_001",
                ber_data=sample_ber_data,
                outcome_status="ACCEPTED",
                issuer="GID-01",  # Agent!
            )
        
        assert "GID-01" in str(exc_info.value)
        assert "GID-00" in str(exc_info.value)
    
    def test_drafting_surface_cannot_create_pdo(self, sample_wrap_data, sample_ber_data):
        """Drafting surface (Jeffrey) cannot create PDO."""
        with pytest.raises(PDOAuthorityError) as exc_info:
            PDOArtifactFactory.create(
                pac_id="PAC-001",
                wrap_id="wrap_001",
                wrap_data=sample_wrap_data,
                ber_id="ber_001",
                ber_data=sample_ber_data,
                outcome_status="ACCEPTED",
                issuer="DRAFTING_SURFACE",
            )
        
        assert "DRAFTING_SURFACE" in str(exc_info.value)
    
    def test_arbitrary_issuer_cannot_create_pdo(self, sample_wrap_data, sample_ber_data):
        """Arbitrary issuer cannot create PDO."""
        for bad_issuer in ["GID-02", "BENSON", "USER", "SYSTEM", "", None]:
            if bad_issuer is None:
                # None will fail completeness check first
                continue
            
            with pytest.raises(PDOAuthorityError):
                PDOArtifactFactory.create(
                    pac_id="PAC-001",
                    wrap_id="wrap_001",
                    wrap_data=sample_wrap_data,
                    ber_id="ber_001",
                    ber_data=sample_ber_data,
                    outcome_status="ACCEPTED",
                    issuer=bad_issuer,
                )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDO COMPLETENESS (INV-PDO-006)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDOCompleteness:
    """Tests for INV-PDO-006: All components required."""
    
    def test_missing_pac_id_fails(self, sample_wrap_data, sample_ber_data):
        """Missing pac_id raises PDOIncompleteError."""
        with pytest.raises(PDOIncompleteError) as exc_info:
            PDOArtifactFactory.create(
                pac_id="",  # Empty!
                wrap_id="wrap_001",
                wrap_data=sample_wrap_data,
                ber_id="ber_001",
                ber_data=sample_ber_data,
                outcome_status="ACCEPTED",
                issuer=PDO_AUTHORITY,
            )
        
        assert "pac_id" in str(exc_info.value)
    
    def test_missing_wrap_id_fails(self, sample_wrap_data, sample_ber_data):
        """Missing wrap_id raises PDOIncompleteError."""
        with pytest.raises(PDOIncompleteError) as exc_info:
            PDOArtifactFactory.create(
                pac_id="PAC-001",
                wrap_id="",  # Empty!
                wrap_data=sample_wrap_data,
                ber_id="ber_001",
                ber_data=sample_ber_data,
                outcome_status="ACCEPTED",
                issuer=PDO_AUTHORITY,
            )
        
        assert "wrap_id" in str(exc_info.value)
    
    def test_missing_wrap_data_fails(self, sample_ber_data):
        """Missing wrap_data raises PDOIncompleteError."""
        with pytest.raises(PDOIncompleteError) as exc_info:
            PDOArtifactFactory.create(
                pac_id="PAC-001",
                wrap_id="wrap_001",
                wrap_data={},  # Empty dict
                ber_id="ber_001",
                ber_data=sample_ber_data,
                outcome_status="ACCEPTED",
                issuer=PDO_AUTHORITY,
            )
        
        assert "wrap_data" in str(exc_info.value)
    
    def test_missing_ber_id_fails(self, sample_wrap_data, sample_ber_data):
        """Missing ber_id raises PDOIncompleteError."""
        with pytest.raises(PDOIncompleteError) as exc_info:
            PDOArtifactFactory.create(
                pac_id="PAC-001",
                wrap_id="wrap_001",
                wrap_data=sample_wrap_data,
                ber_id="",  # Empty!
                ber_data=sample_ber_data,
                outcome_status="ACCEPTED",
                issuer=PDO_AUTHORITY,
            )
        
        assert "ber_id" in str(exc_info.value)
    
    def test_missing_ber_data_fails(self, sample_wrap_data):
        """Missing ber_data raises PDOIncompleteError."""
        with pytest.raises(PDOIncompleteError) as exc_info:
            PDOArtifactFactory.create(
                pac_id="PAC-001",
                wrap_id="wrap_001",
                wrap_data=sample_wrap_data,
                ber_id="ber_001",
                ber_data={},  # Empty dict
                outcome_status="ACCEPTED",
                issuer=PDO_AUTHORITY,
            )
        
        assert "ber_data" in str(exc_info.value)
    
    def test_missing_outcome_status_fails(self, sample_wrap_data, sample_ber_data):
        """Missing outcome_status raises PDOIncompleteError."""
        with pytest.raises(PDOIncompleteError) as exc_info:
            PDOArtifactFactory.create(
                pac_id="PAC-001",
                wrap_id="wrap_001",
                wrap_data=sample_wrap_data,
                ber_id="ber_001",
                ber_data=sample_ber_data,
                outcome_status="",  # Empty!
                issuer=PDO_AUTHORITY,
            )
        
        assert "outcome_status" in str(exc_info.value)
    
    def test_invalid_outcome_status_fails(self, sample_wrap_data, sample_ber_data):
        """Invalid outcome_status raises PDOInvalidOutcomeError."""
        with pytest.raises(PDOInvalidOutcomeError) as exc_info:
            PDOArtifactFactory.create(
                pac_id="PAC-001",
                wrap_id="wrap_001",
                wrap_data=sample_wrap_data,
                ber_id="ber_001",
                ber_data=sample_ber_data,
                outcome_status="INVALID_STATUS",
                issuer=PDO_AUTHORITY,
            )
        
        assert "INVALID_STATUS" in str(exc_info.value)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: HASH CHAIN INTEGRITY (INV-PDO-004)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHashChainIntegrity:
    """Tests for INV-PDO-004: Hash chain binds Proof → Decision → Outcome."""
    
    def test_proof_hash_computed_from_wrap_data(self, sample_wrap_data, sample_ber_data):
        """Proof hash is computed from WRAP data."""
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        expected_proof_hash = compute_proof_hash(sample_wrap_data)
        assert pdo.proof_hash == expected_proof_hash
    
    def test_decision_hash_includes_proof_hash(self, sample_wrap_data, sample_ber_data):
        """Decision hash is computed from proof_hash + BER data."""
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        expected_decision_hash = compute_decision_hash(pdo.proof_hash, sample_ber_data)
        assert pdo.decision_hash == expected_decision_hash
    
    def test_different_wrap_data_produces_different_hashes(self, sample_ber_data):
        """Different WRAP data produces different proof hashes."""
        wrap_data_1 = {"data": "version1"}
        wrap_data_2 = {"data": "version2"}
        
        pdo1 = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=wrap_data_1,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        pdo2 = PDOArtifactFactory.create(
            pac_id="PAC-002",
            wrap_id="wrap_002",
            wrap_data=wrap_data_2,
            ber_id="ber_002",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        assert pdo1.proof_hash != pdo2.proof_hash
        assert pdo1.decision_hash != pdo2.decision_hash
        assert pdo1.pdo_hash != pdo2.pdo_hash
    
    def test_hash_verification_succeeds_for_valid_pdo(self, sample_wrap_data, sample_ber_data):
        """Hash chain verification succeeds for valid PDO."""
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        # Structural verification
        assert verify_pdo_chain(pdo) is True
        
        # Full verification with original data
        assert verify_pdo_full(pdo, sample_wrap_data, sample_ber_data) is True
    
    def test_hash_verification_fails_for_wrong_wrap_data(self, sample_wrap_data, sample_ber_data):
        """Hash verification fails when WRAP data doesn't match."""
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        wrong_wrap_data = {"wrong": "data"}
        assert verify_pdo_full(pdo, wrong_wrap_data, sample_ber_data) is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PDO REGISTRY (INV-PDO-001)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPDORegistry:
    """Tests for INV-PDO-001: One PDO per PAC."""
    
    def test_register_pdo(self, sample_wrap_data, sample_ber_data):
        """PDO can be registered."""
        registry = get_pdo_registry()
        
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        registry.register(pdo)
        
        assert registry.count == 1
        assert registry.has_pac("PAC-001")
    
    def test_retrieve_pdo_by_pac_id(self, sample_wrap_data, sample_ber_data):
        """PDO can be retrieved by PAC ID."""
        registry = get_pdo_registry()
        
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        registry.register(pdo)
        
        retrieved = registry.get_by_pac_id("PAC-001")
        assert retrieved is not None
        assert retrieved.pdo_id == pdo.pdo_id
    
    def test_duplicate_pdo_for_pac_fails(self, sample_wrap_data, sample_ber_data):
        """Cannot register two PDOs for same PAC."""
        registry = get_pdo_registry()
        
        pdo1 = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        pdo2 = PDOArtifactFactory.create(
            pac_id="PAC-001",  # Same PAC!
            wrap_id="wrap_002",
            wrap_data=sample_wrap_data,
            ber_id="ber_002",
            ber_data=sample_ber_data,
            outcome_status="CORRECTIVE",
            issuer=PDO_AUTHORITY,
        )
        
        registry.register(pdo1)
        
        with pytest.raises(PDODuplicateError) as exc_info:
            registry.register(pdo2)
        
        assert "PAC-001" in str(exc_info.value)
    
    def test_registry_filtering_by_outcome(self, sample_wrap_data, sample_ber_data):
        """Registry can filter by outcome status."""
        registry = get_pdo_registry()
        
        for i, outcome in enumerate(["ACCEPTED", "CORRECTIVE", "REJECTED"]):
            pdo = PDOArtifactFactory.create(
                pac_id=f"PAC-00{i+1}",
                wrap_id=f"wrap_00{i+1}",
                wrap_data=sample_wrap_data,
                ber_id=f"ber_00{i+1}",
                ber_data=sample_ber_data,
                outcome_status=outcome,
                issuer=PDO_AUTHORITY,
            )
            registry.register(pdo)
        
        assert len(registry.get_accepted()) == 1
        assert len(registry.get_corrective()) == 1
        assert len(registry.get_rejected()) == 1
    
    def test_registry_audit_summary(self, sample_wrap_data, sample_ber_data):
        """Registry provides audit summary."""
        registry = get_pdo_registry()
        
        for i in range(3):
            pdo = PDOArtifactFactory.create(
                pac_id=f"PAC-00{i+1}",
                wrap_id=f"wrap_00{i+1}",
                wrap_data=sample_wrap_data,
                ber_id=f"ber_00{i+1}",
                ber_data=sample_ber_data,
                outcome_status="ACCEPTED",
                issuer=PDO_AUTHORITY,
            )
            registry.register(pdo)
        
        summary = registry.get_audit_summary()
        assert summary["total"] == 3
        assert summary["accepted"] == 3
        assert len(summary["pac_ids"]) == 3


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ORCHESTRATION ENGINE PDO EMISSION
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrchestrationEnginePDO:
    """Tests for PDO emission via Orchestration Engine."""
    
    def test_receive_wrap_returns_pdo(self, valid_pac):
        """receive_wrap() returns PDOArtifact."""
        engine = get_orchestration_engine()
        engine.dispatch(valid_pac)
        
        pdo = engine.receive_wrap(valid_pac.pac_id, WRAPStatus.COMPLETE)
        
        assert isinstance(pdo, PDOArtifact)
        assert pdo.pac_id == valid_pac.pac_id
        assert pdo.outcome_status == "ACCEPTED"
    
    def test_issue_and_emit_ber_returns_pdo(self, valid_pac):
        """issue_and_emit_ber() returns PDOArtifact."""
        engine = get_orchestration_engine()
        engine.dispatch(valid_pac)
        engine.receive_wrap_without_auto_ber(valid_pac.pac_id, WRAPStatus.COMPLETE)
        
        pdo = engine.issue_and_emit_ber(valid_pac.pac_id, BERStatus.APPROVE)
        
        assert isinstance(pdo, PDOArtifact)
        assert pdo.pac_id == valid_pac.pac_id
    
    def test_pdo_registered_on_emission(self, valid_pac):
        """PDO is registered in registry on emission."""
        reset_pdo_registry()
        engine = get_orchestration_engine()
        engine.dispatch(valid_pac)
        
        pdo = engine.receive_wrap(valid_pac.pac_id, WRAPStatus.COMPLETE)
        
        registry = get_pdo_registry()
        assert registry.has_pac(valid_pac.pac_id)
        retrieved = registry.get(valid_pac.pac_id)
        assert retrieved.pdo_id == pdo.pdo_id
    
    def test_loop_closed_requires_pdo(self, valid_pac):
        """Loop is not closed until PDO is emitted."""
        engine = get_orchestration_engine()
        engine.dispatch(valid_pac)
        
        # Before WRAP
        loop = engine.get_loop_state(valid_pac.pac_id)
        assert not loop.is_loop_closed
        
        # After WRAP + BER + PDO
        engine.receive_wrap(valid_pac.pac_id, WRAPStatus.COMPLETE)
        loop = engine.get_loop_state(valid_pac.pac_id)
        assert loop.is_loop_closed
        assert loop.pdo_emitted
    
    def test_different_ber_statuses_produce_correct_outcomes(self, valid_pac):
        """Different BER statuses produce correct PDO outcome statuses."""
        test_cases = [
            (WRAPStatus.COMPLETE, BERStatus.APPROVE, "ACCEPTED"),
            (WRAPStatus.PARTIAL, BERStatus.CORRECTIVE, "CORRECTIVE"),
        ]
        
        for i, (wrap_status, ber_status, expected_outcome) in enumerate(test_cases):
            reset_orchestration_engine()
            reset_pdo_registry()
            
            pac = (
                PACBuilder()
                .with_id(f"PAC-TEST-{i}")
                .with_issuer("Jeffrey")
                .with_target("BENSON")
                .with_objective("Test")
                .with_mode(PACMode.EXECUTION)
                .with_discipline(PACDiscipline.GOLD_STANDARD)
                .with_execution_plan("Execute test")
                .add_deliverable("Test deliverable")
                .add_constraint("Must pass")
                .add_success_criterion("Pass")
                .with_dispatch("GID-01", "TEST_AGENT", "testing", PACMode.EXECUTION)
                .with_wrap_obligation()
                .with_ber_obligation()
                .with_final_state()
                .build()
            )
            
            engine = get_orchestration_engine()
            engine.dispatch(pac)
            
            pdo = engine.receive_wrap(pac.pac_id, wrap_status)
            
            assert pdo.outcome_status == expected_outcome


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ONE-TO-ONE MAPPING (PAC → BER → PDO)
# ═══════════════════════════════════════════════════════════════════════════════

class TestOneToOneMapping:
    """Tests for one-to-one mapping between PAC, BER, and PDO."""
    
    def test_one_pac_one_pdo(self, valid_pac):
        """One PAC produces exactly one PDO."""
        engine = get_orchestration_engine()
        registry = get_pdo_registry()
        
        engine.dispatch(valid_pac)
        pdo = engine.receive_wrap(valid_pac.pac_id, WRAPStatus.COMPLETE)
        
        assert registry.count == 1
        assert registry.get(valid_pac.pac_id).pdo_id == pdo.pdo_id
    
    def test_multiple_pacs_multiple_pdos(self):
        """Multiple PACs produce multiple PDOs."""
        engine = get_orchestration_engine()
        registry = get_pdo_registry()
        
        pdos = []
        for i in range(3):
            pac = (
                PACBuilder()
                .with_id(f"PAC-MULTI-{i}")
                .with_issuer("Jeffrey")
                .with_target("BENSON")
                .with_objective("Test")
                .with_mode(PACMode.EXECUTION)
                .with_discipline(PACDiscipline.GOLD_STANDARD)
                .with_execution_plan("Execute test")
                .add_deliverable("Test deliverable")
                .add_constraint("Must pass")
                .add_success_criterion("Pass")
                .with_dispatch("GID-01", "TEST_AGENT", "testing", PACMode.EXECUTION)
                .with_wrap_obligation()
                .with_ber_obligation()
                .with_final_state()
                .build()
            )
            engine.dispatch(pac)
            pdo = engine.receive_wrap(pac.pac_id, WRAPStatus.COMPLETE)
            pdos.append(pdo)
        
        assert registry.count == 3
        for pdo in pdos:
            assert registry.has_pac(pdo.pac_id)
    
    def test_pdo_references_pac_wrap_ber(self, valid_pac):
        """PDO contains references to PAC, WRAP, and BER."""
        engine = get_orchestration_engine()
        engine.dispatch(valid_pac)
        
        pdo = engine.receive_wrap(valid_pac.pac_id, WRAPStatus.COMPLETE)
        
        # PDO has PAC reference
        assert pdo.pac_id == valid_pac.pac_id
        
        # PDO has WRAP reference
        assert pdo.wrap_id is not None
        assert pdo.wrap_id.startswith("wrap_")
        
        # PDO has BER reference
        assert pdo.ber_id is not None
        assert pdo.ber_id.startswith("ber_")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: VALID OUTCOMES
# ═══════════════════════════════════════════════════════════════════════════════

class TestValidOutcomes:
    """Tests for valid outcome status values."""
    
    def test_accepted_outcome(self, sample_wrap_data, sample_ber_data):
        """ACCEPTED is a valid outcome."""
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="ACCEPTED",
            issuer=PDO_AUTHORITY,
        )
        
        assert pdo.is_accepted
        assert pdo.outcome_status in VALID_OUTCOMES
    
    def test_corrective_outcome(self, sample_wrap_data, sample_ber_data):
        """CORRECTIVE is a valid outcome."""
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="CORRECTIVE",
            issuer=PDO_AUTHORITY,
        )
        
        assert pdo.is_corrective
        assert pdo.outcome_status in VALID_OUTCOMES
    
    def test_rejected_outcome(self, sample_wrap_data, sample_ber_data):
        """REJECTED is a valid outcome."""
        pdo = PDOArtifactFactory.create(
            pac_id="PAC-001",
            wrap_id="wrap_001",
            wrap_data=sample_wrap_data,
            ber_id="ber_001",
            ber_data=sample_ber_data,
            outcome_status="REJECTED",
            issuer=PDO_AUTHORITY,
        )
        
        assert pdo.is_rejected
        assert pdo.outcome_status in VALID_OUTCOMES


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: HASH UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

class TestHashUtilities:
    """Tests for hash computation utilities."""
    
    def test_compute_hash_string(self):
        """compute_hash works with strings."""
        h = compute_hash("test string")
        assert len(h) == 64
        assert h == hashlib.sha256("test string".encode()).hexdigest()
    
    def test_compute_hash_dict(self):
        """compute_hash works with dicts (deterministic)."""
        d = {"b": 2, "a": 1}
        h = compute_hash(d)
        
        # Same dict produces same hash
        assert compute_hash({"a": 1, "b": 2}) == h
    
    def test_compute_hash_deterministic(self):
        """Hash computation is deterministic."""
        data = {"key": "value", "number": 42}
        
        h1 = compute_hash(data)
        h2 = compute_hash(data)
        
        assert h1 == h2


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: COMPLETE HAPPY PATH
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompleteHappyPath:
    """Tests for complete happy path through PDO engine."""
    
    def test_full_lifecycle_pac_to_pdo(self, valid_pac):
        """Complete lifecycle from PAC dispatch to PDO emission."""
        engine = get_orchestration_engine()
        registry = get_pdo_registry()
        
        # 1. Dispatch PAC
        result = engine.dispatch(valid_pac)
        assert result.success
        
        # 2. Receive WRAP (auto BER + PDO)
        pdo = engine.receive_wrap(valid_pac.pac_id, WRAPStatus.COMPLETE)
        
        # 3. Verify PDO
        assert pdo is not None
        assert pdo.pac_id == valid_pac.pac_id
        assert pdo.issuer == "GID-00"
        assert pdo.outcome_status == "ACCEPTED"
        
        # 4. Verify hash chain
        assert verify_pdo_chain(pdo)
        
        # 5. Verify registration
        assert registry.has_pac(valid_pac.pac_id)
        
        # 6. Verify loop closed
        loop = engine.get_loop_state(valid_pac.pac_id)
        assert loop.is_loop_closed
        assert loop.wrap_received
        assert loop.ber_issued
        assert loop.ber_emitted
        assert loop.pdo_emitted
