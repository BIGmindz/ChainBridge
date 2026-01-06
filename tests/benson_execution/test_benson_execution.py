# ═══════════════════════════════════════════════════════════════════════════════
# BensonExecution Tests
# PAC-BENSON-EXEC-C01: BENSON EXECUTION GENESIS & IDENTITY INSTANTIATION
# ═══════════════════════════════════════════════════════════════════════════════

"""
Comprehensive tests for Benson Execution system.

TEST CATEGORIES:
    - PAC Lint Law (LINT-001 through LINT-012)
    - Schema Registry validation
    - Preflight gate enforcement
    - PAC ingress validation
    - Execution engine singleton
    - Audit trail integrity
"""

import pytest
from typing import Any, Dict

# Import after fixture setup to allow singleton reset
import core.benson_execution.execution_engine as execution_engine_module
import core.benson_execution.pac_ingress_validator as ingress_module
import core.benson_execution.preflight_gates as preflight_module
import core.benson_execution.pac_lint_law as lint_module
import core.benson_execution.schema_registry as schema_module
import core.benson_execution.audit_emitter as audit_module


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singletons before each test."""
    # Reset module-level singletons
    execution_engine_module._BENSON_INSTANCE = None
    ingress_module._INGRESS_VALIDATOR_INSTANCE = None
    preflight_module._PREFLIGHT_ENFORCER_INSTANCE = None
    lint_module._LINT_LAW_INSTANCE = None
    schema_module._SCHEMA_REGISTRY_INSTANCE = None
    audit_module._AUDIT_EMITTER_INSTANCE = None
    yield


@pytest.fixture
def valid_pac() -> Dict[str, Any]:
    """Create a valid PAC document that passes all validation."""
    return {
        "metadata": {
            "pac_id": "PAC-BENSON-EXEC-C01",
            "pac_version": "1.0.0",
            "classification": "CONSTITUTIONAL",
            "governance_tier": "LAW",
            "issuer_gid": "GID-00",
            "issuer_role": "Chief Architect",
            "issued_at": "2026-01-05T00:00:00Z",
            "scope": "Benson Execution",
            "supersedes": None,
            "drift_tolerance": "ZERO",
            "fail_closed": True,
            "schema_version": "CHAINBRIDGE_PAC_SCHEMA_v1.0.0",
        },
        "blocks": {
            "0": {"block_name": "METADATA"},
            "1": {
                "block_name": "PAC_ADMISSION_CHECK",
                "admission_decision": "ACCEPTED",
            },
            "2": {
                "block_name": "RUNTIME_ACTIVATION_ACK",
                "runtime_ack": "EXPLICIT",
            },
            "3": {
                "block_name": "GOVERNANCE_MODE_DECLARATION",
                "governance_mode": "LAW",
                "enforcement_engines": ["ALEX", "Lex"],
                "invariant_registry": "LOCKED",
                "downgrade_allowed": False,
            },
            "4": {
                "block_name": "AGENT_ACTIVATION_ACK",
                "identity": {
                    "name": "Benson Execution",
                    "canonical_id": "GID-00-EXEC",
                },
                "acknowledgement": {
                    "agent_ack": "EXPLICIT",
                },
            },
            "5": {
                "block_name": "EXECUTION_LANE",
                "lane": "CORE PLATFORM",
            },
            "6": {
                "block_name": "CONTEXT",
                "description": "Constitutional boundary",
            },
            "7": {
                "block_name": "GOAL_STATE",
                "goal": "Every execution is either proven lawful or blocked",
            },
            "8": {
                "block_name": "CONSTRAINTS_AND_GUARDRAILS",
                "constraints": ["No UI authority", "No agent trust"],
            },
            "9": {
                "block_name": "INVARIANTS_ENFORCED",
                "invariant_registry": "LOCKED",
                "invariants": ["CB-INV-PREFLIGHT-LAW-001"],
            },
            "10": {
                "block_name": "TASKS_AND_PLAN",
                "tasks": ["Bind schema validation"],
            },
            "11": {
                "block_name": "FILE_AND_CODE_TARGETS",
                "targets": ["BensonExecution/schema_registry"],
            },
            "12": {
                "block_name": "INTERFACES_AND_CONTRACTS",
                "interfaces": ["PAC ingestion API"],
            },
            "13": {
                "block_name": "SECURITY_AND_THREAT_MODEL",
                "threats": ["Bypass paths"],
            },
            "14": {
                "block_name": "TESTING_AND_VERIFICATION",
                "tests": ["Invalid PAC rejected"],
            },
            "15": {
                "block_name": "QA_AND_ACCEPTANCE_CRITERIA",
                "criteria": ["Execution impossible without valid PAC"],
            },
            "16": {
                "block_name": "WRAP_REQUIREMENT",
                "wrap_required": False,
            },
            "17": {
                "block_name": "FAILURE_AND_ROLLBACK",
                "failure_mode": "HARD STOP",
            },
            "18": {
                "block_name": "FINAL_STATE_DECLARATION",
                "execution_blocking": True,
                "promotion_eligible": False,
            },
            "19": {
                "block_name": "LEDGER_COMMIT_AND_ATTESTATION",
                "ordering_attested": True,
                "immutability_attested": True,
                "hash_commitment": "REQUIRED",
            },
        },
    }


@pytest.fixture
def invalid_pac_missing_metadata() -> Dict[str, Any]:
    """PAC missing metadata block."""
    return {
        "blocks": {
            "1": {"block_name": "PAC_ADMISSION_CHECK"},
        }
    }


@pytest.fixture
def invalid_pac_bad_version() -> Dict[str, Any]:
    """PAC with invalid version format."""
    return {
        "metadata": {
            "pac_id": "PAC-TEST-001",
            "pac_version": "not-a-version",
            "classification": "CONSTITUTIONAL",
            "governance_tier": "LAW",
            "issuer_gid": "GID-00",
            "issuer_role": "Test",
            "issued_at": "2026-01-05T00:00:00Z",
            "scope": "Test",
            "fail_closed": True,
            "schema_version": "CHAINBRIDGE_PAC_SCHEMA_v1.0.0",
        },
        "blocks": {},
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PAC LINT LAW TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPACLintLaw:
    """Tests for PAC Lint Law enforcement."""
    
    def test_lint_valid_pac_passes(self, valid_pac):
        """Valid PAC should pass all lint rules."""
        from core.benson_execution.pac_lint_law import PACLintLaw
        
        lint_law = PACLintLaw()
        result = lint_law.enforce(valid_pac)
        
        assert result.passed is True
        assert result.violation_count == 0
    
    def test_lint_001_metadata_required(self, invalid_pac_missing_metadata):
        """LINT-001: METADATA block must exist."""
        from core.benson_execution.pac_lint_law import PACLintLaw, LintRuleID
        
        lint_law = PACLintLaw()
        result = lint_law.enforce(invalid_pac_missing_metadata)
        
        assert result.passed is False
        assert any(v.rule_id == LintRuleID.LINT_001 for v in result.violations)
    
    def test_lint_002_pac_id_format(self):
        """LINT-002: pac_id must match canonical format."""
        from core.benson_execution.pac_lint_law import PACLintLaw, LintRuleID
        
        pac = {
            "metadata": {
                "pac_id": "invalid_format",  # Should be PAC-XXX-XXX
                "pac_version": "1.0.0",
                "classification": "CONSTITUTIONAL",
                "governance_tier": "LAW",
                "issuer_gid": "GID-00",
                "issuer_role": "Test",
                "issued_at": "2026-01-05T00:00:00Z",
                "scope": "Test",
                "fail_closed": True,
                "schema_version": "CHAINBRIDGE_PAC_SCHEMA_v1.0.0",
            },
            "blocks": {},
        }
        
        lint_law = PACLintLaw()
        result = lint_law.enforce(pac)
        
        assert result.passed is False
        assert any(v.rule_id == LintRuleID.LINT_002 for v in result.violations)
    
    def test_lint_003_semantic_version(self, invalid_pac_bad_version):
        """LINT-003: pac_version must be semantic version."""
        from core.benson_execution.pac_lint_law import PACLintLaw, LintRuleID
        
        lint_law = PACLintLaw()
        result = lint_law.enforce(invalid_pac_bad_version)
        
        assert result.passed is False
        assert any(v.rule_id == LintRuleID.LINT_003 for v in result.violations)
    
    def test_lint_004_classification_enum(self):
        """LINT-004: classification must be valid enum."""
        from core.benson_execution.pac_lint_law import PACLintLaw, LintRuleID
        
        pac = {
            "metadata": {
                "pac_id": "PAC-TEST-001",
                "pac_version": "1.0.0",
                "classification": "INVALID_CLASSIFICATION",
                "governance_tier": "LAW",
                "issuer_gid": "GID-00",
                "issuer_role": "Test",
                "issued_at": "2026-01-05T00:00:00Z",
                "scope": "Test",
                "fail_closed": True,
                "schema_version": "CHAINBRIDGE_PAC_SCHEMA_v1.0.0",
            },
            "blocks": {},
        }
        
        lint_law = PACLintLaw()
        result = lint_law.enforce(pac)
        
        assert result.passed is False
        assert any(v.rule_id == LintRuleID.LINT_004 for v in result.violations)
    
    def test_lint_008_fail_closed_for_law_tier(self):
        """LINT-008: fail_closed must be true for LAW tier."""
        from core.benson_execution.pac_lint_law import PACLintLaw, LintRuleID
        
        pac = {
            "metadata": {
                "pac_id": "PAC-TEST-001",
                "pac_version": "1.0.0",
                "classification": "CONSTITUTIONAL",
                "governance_tier": "LAW",  # LAW tier
                "issuer_gid": "GID-00",
                "issuer_role": "Test",
                "issued_at": "2026-01-05T00:00:00Z",
                "scope": "Test",
                "fail_closed": False,  # Should be True for LAW
                "schema_version": "CHAINBRIDGE_PAC_SCHEMA_v1.0.0",
            },
            "blocks": {},
        }
        
        lint_law = PACLintLaw()
        result = lint_law.enforce(pac)
        
        assert result.passed is False
        assert any(v.rule_id == LintRuleID.LINT_008 for v in result.violations)
    
    def test_lint_009_all_blocks_required(self, valid_pac):
        """LINT-009: All numbered blocks (0-19) must be present."""
        from core.benson_execution.pac_lint_law import PACLintLaw, LintRuleID
        
        # Remove a required block
        pac = valid_pac.copy()
        pac["blocks"] = {k: v for k, v in pac["blocks"].items() if k != "10"}
        
        lint_law = PACLintLaw()
        result = lint_law.enforce(pac)
        
        assert result.passed is False
        assert any(v.rule_id == LintRuleID.LINT_009 for v in result.violations)
    
    def test_lint_011_final_state_required(self, valid_pac):
        """LINT-011: FINAL_STATE_DECLARATION must exist with required fields."""
        from core.benson_execution.pac_lint_law import PACLintLaw, LintRuleID
        
        # Remove required field from FINAL_STATE
        pac = valid_pac.copy()
        pac["blocks"] = pac["blocks"].copy()
        pac["blocks"]["18"] = {"block_name": "FINAL_STATE_DECLARATION"}  # Missing fields
        
        lint_law = PACLintLaw()
        result = lint_law.enforce(pac)
        
        assert result.passed is False
        assert any(v.rule_id == LintRuleID.LINT_011 for v in result.violations)
    
    def test_lint_012_ledger_commit_required(self, valid_pac):
        """LINT-012: LEDGER_COMMIT_AND_ATTESTATION must exist."""
        from core.benson_execution.pac_lint_law import PACLintLaw, LintRuleID
        
        # Remove required field from LEDGER_COMMIT
        pac = valid_pac.copy()
        pac["blocks"] = pac["blocks"].copy()
        pac["blocks"]["19"] = {"block_name": "LEDGER_COMMIT"}  # Missing attestation fields
        
        lint_law = PACLintLaw()
        result = lint_law.enforce(pac)
        
        assert result.passed is False
        assert any(v.rule_id == LintRuleID.LINT_012 for v in result.violations)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBensonSchemaRegistry:
    """Tests for Benson Schema Registry."""
    
    def test_valid_pac_passes_schema(self, valid_pac):
        """Valid PAC should pass schema validation."""
        from core.benson_execution.schema_registry import BensonSchemaRegistry
        
        registry = BensonSchemaRegistry()
        result = registry.validate(valid_pac)
        
        assert result.is_valid is True
        assert result.error_count == 0
    
    def test_missing_schema_ref_rejected(self):
        """PAC without schema_version is rejected."""
        from core.benson_execution.schema_registry import (
            BensonSchemaRegistry,
            SchemaValidationStatus,
        )
        
        pac = {
            "metadata": {
                "pac_id": "PAC-TEST-001",
                # Missing schema_version
            }
        }
        
        registry = BensonSchemaRegistry()
        result = registry.validate(pac)
        
        assert result.status == SchemaValidationStatus.MISSING_SCHEMA_REF
    
    def test_unknown_schema_rejected(self):
        """PAC with unknown schema version is rejected."""
        from core.benson_execution.schema_registry import (
            BensonSchemaRegistry,
            SchemaValidationStatus,
        )
        
        pac = {
            "metadata": {
                "pac_id": "PAC-TEST-001",
                "schema_version": "UNKNOWN_SCHEMA_v99.99.99",
            }
        }
        
        registry = BensonSchemaRegistry()
        result = registry.validate(pac)
        
        assert result.status == SchemaValidationStatus.UNKNOWN_SCHEMA
    
    def test_schema_hash_computed(self):
        """Schema hash should be computed and included in result."""
        from core.benson_execution.schema_registry import (
            BensonSchemaRegistry,
            CURRENT_PAC_SCHEMA_ID,
        )
        
        registry = BensonSchemaRegistry()
        schema_hash = registry.get_schema_hash(CURRENT_PAC_SCHEMA_ID)
        
        assert schema_hash is not None
        assert len(schema_hash) == 16  # First 16 chars of SHA256
    
    def test_supported_schemas_immutable(self):
        """Supported schemas should be a frozen set."""
        from core.benson_execution.schema_registry import BensonSchemaRegistry
        
        registry = BensonSchemaRegistry()
        schemas = registry.supported_schemas
        
        assert isinstance(schemas, frozenset)
        assert len(schemas) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# PREFLIGHT GATE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPreflightGates:
    """Tests for preflight gate enforcement."""
    
    def test_valid_pac_passes_all_gates(self, valid_pac):
        """Valid PAC should pass all preflight gates."""
        from core.benson_execution.preflight_gates import PreflightEnforcer
        
        enforcer = PreflightEnforcer()
        result = enforcer.enforce(valid_pac)
        
        assert result.passed is True
        assert result.halted_at is None
        assert result.gates_passed == 6  # All 6 gates
    
    def test_gate_execution_order_fixed(self):
        """Gates must execute in fixed canonical order."""
        from core.benson_execution.preflight_gates import (
            PreflightEnforcer,
            GATE_EXECUTION_ORDER,
        )
        
        enforcer = PreflightEnforcer()
        
        for i, gate in enumerate(enforcer._gates):
            assert gate.gate_id == GATE_EXECUTION_ORDER[i]
    
    def test_failure_halts_execution(self, invalid_pac_missing_metadata):
        """Gate failure should halt remaining gates."""
        from core.benson_execution.preflight_gates import (
            PreflightEnforcer,
            GateStatus,
        )
        
        enforcer = PreflightEnforcer()
        result = enforcer.enforce(invalid_pac_missing_metadata)
        
        assert result.passed is False
        assert result.halted_at is not None
        
        # Gates after failure should be SKIPPED
        found_failure = False
        for gate_result in result.gate_results:
            if gate_result.failed:
                found_failure = True
            elif found_failure:
                assert gate_result.status == GateStatus.SKIPPED
    
    def test_governance_gate_rejects_invalid_mode(self, valid_pac):
        """Governance gate should reject invalid governance mode."""
        from core.benson_execution.preflight_gates import GovernanceGate, GateStatus
        
        pac = valid_pac.copy()
        pac["blocks"] = pac["blocks"].copy()
        pac["blocks"]["3"] = {
            "governance_mode": "INVALID_MODE",
        }
        
        gate = GovernanceGate()
        result = gate.execute(pac)
        
        assert result.status == GateStatus.FAILED
    
    def test_governance_gate_rejects_law_downgrade(self, valid_pac):
        """LAW tier cannot allow downgrade."""
        from core.benson_execution.preflight_gates import GovernanceGate, GateStatus
        
        pac = valid_pac.copy()
        pac["blocks"] = pac["blocks"].copy()
        pac["blocks"]["3"] = {
            "governance_mode": "LAW",
            "downgrade_allowed": True,  # Not allowed for LAW
        }
        
        gate = GovernanceGate()
        result = gate.execute(pac)
        
        assert result.status == GateStatus.FAILED
    
    def test_invariant_gate_requires_locked_for_law(self, valid_pac):
        """LAW tier requires invariant_registry to be LOCKED."""
        from core.benson_execution.preflight_gates import InvariantGate, GateStatus
        
        pac = valid_pac.copy()
        pac["blocks"] = pac["blocks"].copy()
        pac["blocks"]["9"] = {
            "invariant_registry": "UNLOCKED",  # Should be LOCKED for LAW
        }
        
        gate = InvariantGate()
        result = gate.execute(pac)
        
        assert result.status == GateStatus.FAILED


# ═══════════════════════════════════════════════════════════════════════════════
# PAC INGRESS VALIDATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestPACIngressValidator:
    """Tests for PAC ingress validation."""
    
    def test_valid_pac_admitted(self, valid_pac):
        """Valid PAC should be admitted."""
        from core.benson_execution.pac_ingress_validator import (
            PACIngressValidator,
            IngressDecision,
        )
        
        validator = PACIngressValidator()
        result = validator.validate(valid_pac)
        
        assert result.decision == IngressDecision.ADMIT
    
    def test_invalid_pac_rejected(self, invalid_pac_missing_metadata):
        """Invalid PAC should be rejected."""
        from core.benson_execution.pac_ingress_validator import (
            PACIngressValidator,
            IngressDecision,
        )
        
        validator = PACIngressValidator()
        result = validator.validate(invalid_pac_missing_metadata)
        
        assert result.decision == IngressDecision.REJECT
    
    def test_duplicate_pac_rejected(self, valid_pac):
        """Same PAC cannot be validated twice."""
        from core.benson_execution.pac_ingress_validator import (
            PACIngressValidator,
            IngressDecision,
            RejectReason,
        )
        
        validator = PACIngressValidator()
        
        # First validation succeeds
        result1 = validator.validate(valid_pac)
        assert result1.decision == IngressDecision.ADMIT
        
        # Second validation of same PAC is rejected
        result2 = validator.validate(valid_pac)
        assert result2.decision == IngressDecision.REJECT
        assert result2.reason == RejectReason.DUPLICATE_PAC
    
    def test_validation_cache_reset(self, valid_pac):
        """Validation cache can be reset for testing."""
        from core.benson_execution.pac_ingress_validator import PACIngressValidator
        
        validator = PACIngressValidator()
        
        validator.validate(valid_pac)
        assert validator.validated_pac_count == 1
        
        validator.reset_validation_cache()
        assert validator.validated_pac_count == 0


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBensonExecution:
    """Tests for Benson Execution engine."""
    
    def test_singleton_enforcement(self):
        """Only one BensonExecution instance allowed."""
        from core.benson_execution.execution_engine import (
            BensonExecution,
            DuplicateInstanceError,
            get_benson_execution,
        )
        
        # Get first instance
        benson1 = get_benson_execution()
        assert benson1 is not None
        
        # Direct instantiation should fail
        with pytest.raises(DuplicateInstanceError):
            BensonExecution()
        
        # get_benson_execution returns same instance
        benson2 = get_benson_execution()
        assert benson1 is benson2
    
    def test_valid_pac_admitted(self, valid_pac):
        """Valid PAC should be admitted for execution."""
        from core.benson_execution.execution_engine import (
            get_benson_execution,
            ExecutionStatus,
        )
        
        benson = get_benson_execution()
        result = benson.admit(valid_pac)
        
        assert result.is_admitted is True
        assert result.status == ExecutionStatus.ADMITTED
        assert result.execution_token is not None
    
    def test_invalid_pac_rejected(self, invalid_pac_missing_metadata):
        """Invalid PAC should be rejected from execution."""
        from core.benson_execution.execution_engine import (
            get_benson_execution,
            ExecutionStatus,
        )
        
        benson = get_benson_execution()
        result = benson.admit(invalid_pac_missing_metadata)
        
        assert result.is_admitted is False
        assert result.status == ExecutionStatus.REJECTED
    
    def test_execution_lifecycle(self, valid_pac):
        """Test full execution lifecycle: admit → start → complete."""
        from core.benson_execution.execution_engine import (
            get_benson_execution,
            ExecutionStatus,
        )
        
        benson = get_benson_execution()
        
        # Admit
        result = benson.admit(valid_pac)
        token = result.execution_token
        
        assert benson.get_execution_status(token) == ExecutionStatus.ADMITTED
        
        # Start
        assert benson.mark_execution_started(token) is True
        assert benson.get_execution_status(token) == ExecutionStatus.EXECUTING
        
        # Complete
        assert benson.mark_execution_completed(token) is True
        assert benson.get_execution_status(token) == ExecutionStatus.COMPLETED
    
    def test_execution_halt(self, valid_pac):
        """Test execution halt (fail-closed)."""
        from core.benson_execution.execution_engine import (
            get_benson_execution,
            ExecutionStatus,
        )
        
        benson = get_benson_execution()
        
        result = benson.admit(valid_pac)
        token = result.execution_token
        
        benson.mark_execution_started(token)
        benson.mark_execution_halted(token, "Test halt reason")
        
        assert benson.get_execution_status(token) == ExecutionStatus.HALTED
    
    def test_identity_correct(self):
        """Benson identity should match PAC specification."""
        from core.benson_execution.execution_engine import get_benson_execution
        
        benson = get_benson_execution()
        identity = benson.identity
        
        assert identity["name"] == "Benson Execution"
        assert identity["gid"] == "GID-00-EXEC"
        assert identity["type"] == "Deterministic Execution Engine"
        assert identity["learning"] is False
        assert identity["reasoning"] is False
        assert identity["decision_making"] is False
        assert identity["interpretation"] is False
        assert identity["optimization"] is False
        assert identity["override_allowed"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT EMITTER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBensonAuditEmitter:
    """Tests for audit trail integrity."""
    
    def test_audit_chain_integrity(self):
        """Audit events should form valid hash chain."""
        from core.benson_execution.audit_emitter import (
            BensonAuditEmitter,
            AuditEventType,
        )
        
        emitter = BensonAuditEmitter()
        
        # Emit several events
        emitter.emit(AuditEventType.BENSON_INITIALIZED)
        emitter.emit(AuditEventType.PAC_INGRESS_RECEIVED, pac_id="PAC-TEST-001")
        emitter.emit(AuditEventType.PAC_ADMITTED, pac_id="PAC-TEST-001")
        
        # Verify chain integrity
        assert emitter.verify_chain() is True
    
    def test_events_are_immutable(self):
        """Audit events should be immutable (frozen dataclass)."""
        from core.benson_execution.audit_emitter import (
            BensonAuditEmitter,
            AuditEventType,
        )
        
        emitter = BensonAuditEmitter()
        event = emitter.emit(AuditEventType.BENSON_INITIALIZED)
        
        # Attempting to modify should raise
        with pytest.raises(Exception):  # FrozenInstanceError
            event.pac_id = "modified"
    
    def test_events_queryable_by_pac(self):
        """Events should be queryable by PAC ID."""
        from core.benson_execution.audit_emitter import (
            BensonAuditEmitter,
            AuditEventType,
        )
        
        emitter = BensonAuditEmitter()
        
        emitter.emit(AuditEventType.PAC_INGRESS_RECEIVED, pac_id="PAC-001")
        emitter.emit(AuditEventType.PAC_INGRESS_RECEIVED, pac_id="PAC-002")
        emitter.emit(AuditEventType.PAC_ADMITTED, pac_id="PAC-001")
        
        pac_001_events = emitter.get_events_for_pac("PAC-001")
        
        assert len(pac_001_events) == 2
        assert all(e.pac_id == "PAC-001" for e in pac_001_events)
    
    def test_events_queryable_by_type(self):
        """Events should be queryable by event type."""
        from core.benson_execution.audit_emitter import (
            BensonAuditEmitter,
            AuditEventType,
        )
        
        emitter = BensonAuditEmitter()
        
        emitter.emit(AuditEventType.PAC_INGRESS_RECEIVED, pac_id="PAC-001")
        emitter.emit(AuditEventType.PAC_ADMITTED, pac_id="PAC-001")
        emitter.emit(AuditEventType.PAC_INGRESS_RECEIVED, pac_id="PAC-002")
        
        ingress_events = emitter.get_events_by_type(AuditEventType.PAC_INGRESS_RECEIVED)
        
        assert len(ingress_events) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBensonExecutionIntegration:
    """End-to-end integration tests."""
    
    def test_full_valid_pac_flow(self, valid_pac):
        """Test complete flow: PAC → validation → admit → execute → complete."""
        from core.benson_execution.execution_engine import (
            get_benson_execution,
            ExecutionStatus,
        )
        from core.benson_execution.audit_emitter import AuditEventType
        
        benson = get_benson_execution()
        
        # Admit PAC
        result = benson.admit(valid_pac)
        assert result.is_admitted is True
        
        token = result.execution_token
        
        # Start execution
        benson.mark_execution_started(token)
        
        # Complete execution
        benson.mark_execution_completed(token)
        
        # Verify audit trail
        trail = benson.audit_trail
        
        # Should have: INIT, INGRESS_RECEIVED, ADMITTED, STARTED, COMPLETED
        event_types = [e.event_type for e in trail]
        
        assert AuditEventType.BENSON_INITIALIZED in event_types
        assert AuditEventType.PAC_INGRESS_RECEIVED in event_types
        assert AuditEventType.PAC_ADMITTED in event_types
        assert AuditEventType.EXECUTION_STARTED in event_types
        assert AuditEventType.EXECUTION_COMPLETED in event_types
    
    def test_invalid_pac_blocked_completely(self, invalid_pac_missing_metadata):
        """Invalid PAC should be completely blocked with audit trail."""
        from core.benson_execution.execution_engine import get_benson_execution
        from core.benson_execution.audit_emitter import AuditEventType
        
        benson = get_benson_execution()
        
        # Attempt to admit invalid PAC
        result = benson.admit(invalid_pac_missing_metadata)
        
        assert result.is_admitted is False
        
        # Verify rejection in audit trail
        trail = benson.audit_trail
        event_types = [e.event_type for e in trail]
        
        assert AuditEventType.PAC_REJECTED in event_types
        assert AuditEventType.PAC_ADMITTED not in event_types
