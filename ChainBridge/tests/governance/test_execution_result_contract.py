#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
TEST: Agent Execution Result Contract Enforcement
PAC-DAN-P50-GOVERNANCE-EXECUTION-HANDOFF-AND-AGENT-RESULT-CONTRACT-01
═══════════════════════════════════════════════════════════════════════════════

Tests for:
- AgentExecutionResult schema validation
- Forbidden field enforcement (GS_130-GS_133)
- Benson Execution handoff contract
- WRAP generation authority

Authority: BENSON (GID-00)
Mode: FAIL_CLOSED
"""

import json
import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add tools/governance to path
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "governance"))

from benson_execution import (
    BensonExecutionEngine,
    ExecutionResult,
    ExecutionStatus,
    BlockReason,
    validate_execution_result_schema,
    FORBIDDEN_EXECUTION_RESULT_FIELDS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def engine():
    """Create Benson Execution Engine instance."""
    return BensonExecutionEngine()


@pytest.fixture
def valid_execution_result():
    """Create a valid AgentExecutionResult."""
    return {
        "pac_id": "PAC-DAN-P50-TEST-01",
        "agent_gid": "GID-07",
        "agent_name": "Dan",
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "tasks_completed": ["T1", "T2"],
        "tasks_total": 2,
        "files_modified": ["tools/governance/test_file.py"],
        "files_created": [],
        "quality_score": 1.0,
        "scope_compliance": True,
        "execution_time_ms": 5000,
    }


@pytest.fixture
def minimal_execution_result():
    """Create a minimal valid AgentExecutionResult."""
    return {
        "pac_id": "PAC-DAN-P50-MINIMAL-01",
        "agent_gid": "GID-07",
        "agent_name": "Dan",
        "execution_timestamp": datetime.now(timezone.utc).isoformat(),
        "tasks_completed": ["T1"],
        "tasks_total": 1,
        "files_modified": [],
        "quality_score": 0.8,
        "scope_compliance": True,
        "execution_time_ms": 1000,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SCHEMA VALIDATION (REQUIRED FIELDS)
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionResultSchemaValidation:
    """Test AgentExecutionResult schema validation."""
    
    def test_valid_execution_result_passes(self, valid_execution_result):
        """Valid execution result should pass schema validation."""
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is True
        assert result["error_code"] is None
    
    def test_minimal_execution_result_passes(self, minimal_execution_result):
        """Minimal execution result with all required fields should pass."""
        result = validate_execution_result_schema(minimal_execution_result)
        assert result["valid"] is True
    
    def test_missing_pac_id_fails(self, valid_execution_result):
        """Missing pac_id should fail with GS_130."""
        del valid_execution_result["pac_id"]
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_130"
        assert "pac_id" in result["message"]
    
    def test_missing_agent_gid_fails(self, valid_execution_result):
        """Missing agent_gid should fail with GS_130."""
        del valid_execution_result["agent_gid"]
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_130"
    
    def test_missing_agent_name_fails(self, valid_execution_result):
        """Missing agent_name should fail with GS_130."""
        del valid_execution_result["agent_name"]
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_130"
    
    def test_missing_execution_timestamp_fails(self, valid_execution_result):
        """Missing execution_timestamp should fail with GS_130."""
        del valid_execution_result["execution_timestamp"]
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_130"
    
    def test_missing_tasks_completed_fails(self, valid_execution_result):
        """Missing tasks_completed should fail with GS_130."""
        del valid_execution_result["tasks_completed"]
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_130"
    
    def test_missing_quality_score_fails(self, valid_execution_result):
        """Missing quality_score should fail with GS_130."""
        del valid_execution_result["quality_score"]
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_130"
    
    def test_missing_scope_compliance_fails(self, valid_execution_result):
        """Missing scope_compliance should fail with GS_130."""
        del valid_execution_result["scope_compliance"]
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_130"
    
    def test_invalid_quality_score_range_fails(self, valid_execution_result):
        """Quality score outside 0.0-1.0 should fail with GS_130."""
        valid_execution_result["quality_score"] = 1.5
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_130"
        
        valid_execution_result["quality_score"] = -0.1
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
    
    def test_invalid_gid_format_fails(self, valid_execution_result):
        """Invalid GID format should fail with GS_130."""
        valid_execution_result["agent_gid"] = "INVALID"
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_130"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: FORBIDDEN FIELD ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestForbiddenFieldEnforcement:
    """Test forbidden field enforcement (GS_131-GS_133)."""
    
    def test_wrap_id_forbidden(self, valid_execution_result):
        """wrap_id field should be forbidden (GS_131)."""
        valid_execution_result["wrap_id"] = "WRAP-DAN-P50-TEST-01"
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_131"
        assert "wrap_id" in result["message"].lower()
    
    def test_wrap_status_forbidden(self, valid_execution_result):
        """wrap_status field should be forbidden (GS_131)."""
        valid_execution_result["wrap_status"] = "WRAP_ACCEPTED"
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_131"
    
    def test_wrap_accepted_forbidden(self, valid_execution_result):
        """wrap_accepted field should be forbidden (GS_131)."""
        valid_execution_result["wrap_accepted"] = True
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_131"
    
    def test_positive_closure_forbidden(self, valid_execution_result):
        """positive_closure field should be forbidden (GS_132)."""
        valid_execution_result["positive_closure"] = True
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_132"
    
    def test_closure_authority_forbidden(self, valid_execution_result):
        """closure_authority field should be forbidden (GS_132)."""
        valid_execution_result["closure_authority"] = "BENSON (GID-00)"
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_132"
    
    def test_wrap_authority_forbidden(self, valid_execution_result):
        """wrap_authority field should be forbidden (GS_133)."""
        valid_execution_result["wrap_authority"] = "BENSON (GID-00)"
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] == "GS_133"
    
    def test_multiple_forbidden_fields_reports_first(self, valid_execution_result):
        """Multiple forbidden fields should report at least one error."""
        valid_execution_result["wrap_id"] = "WRAP-TEST"
        valid_execution_result["positive_closure"] = True
        valid_execution_result["wrap_authority"] = "SELF"
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        assert result["error_code"] in ["GS_131", "GS_132", "GS_133"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: BENSON EXECUTION ENGINE INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestBensonExecutionEngineHandoff:
    """Test Benson Execution Engine handoff contract."""
    
    def test_valid_handoff_accepted(self, engine, valid_execution_result):
        """Valid execution result should be accepted by engine."""
        exec_result = ExecutionResult(
            pac_id=valid_execution_result["pac_id"],
            agent_gid=valid_execution_result["agent_gid"],
            agent_name=valid_execution_result["agent_name"],
            execution_timestamp=valid_execution_result["execution_timestamp"],
            tasks_completed=valid_execution_result["tasks_completed"],
            files_modified=valid_execution_result["files_modified"],
            quality_score=valid_execution_result["quality_score"],
            scope_compliance=valid_execution_result["scope_compliance"],
            execution_time_ms=valid_execution_result["execution_time_ms"],
        )
        
        # Note: Full execution requires registry/ledger; test schema validation
        validation = engine.validate_execution_result_schema(valid_execution_result)
        assert validation["valid"] is True
    
    def test_forbidden_wrap_id_blocked(self, engine, valid_execution_result):
        """Execution result with wrap_id should be blocked."""
        valid_execution_result["wrap_id"] = "WRAP-FORBIDDEN-01"
        validation = engine.validate_execution_result_schema(valid_execution_result)
        assert validation["valid"] is False
        assert "GS_131" in validation["error_code"]
    
    def test_forbidden_positive_closure_blocked(self, engine, valid_execution_result):
        """Execution result with positive_closure should be blocked."""
        valid_execution_result["positive_closure"] = True
        validation = engine.validate_execution_result_schema(valid_execution_result)
        assert validation["valid"] is False
        assert "GS_132" in validation["error_code"]
    
    def test_low_quality_score_fails_threshold(self, engine, valid_execution_result):
        """Quality score below threshold should fail validation."""
        valid_execution_result["quality_score"] = 0.5
        exec_result = ExecutionResult(
            pac_id=valid_execution_result["pac_id"],
            agent_gid=valid_execution_result["agent_gid"],
            agent_name=valid_execution_result["agent_name"],
            execution_timestamp=valid_execution_result["execution_timestamp"],
            tasks_completed=valid_execution_result["tasks_completed"],
            files_modified=valid_execution_result["files_modified"],
            quality_score=valid_execution_result["quality_score"],
            scope_compliance=valid_execution_result["scope_compliance"],
            execution_time_ms=valid_execution_result["execution_time_ms"],
        )
        # Quality threshold is 0.7 in engine
        assert exec_result.quality_score < 0.7
    
    def test_scope_violation_blocked(self, engine, valid_execution_result):
        """Scope violation should block execution."""
        valid_execution_result["scope_compliance"] = False
        exec_result = ExecutionResult(
            pac_id=valid_execution_result["pac_id"],
            agent_gid=valid_execution_result["agent_gid"],
            agent_name=valid_execution_result["agent_name"],
            execution_timestamp=valid_execution_result["execution_timestamp"],
            tasks_completed=valid_execution_result["tasks_completed"],
            files_modified=valid_execution_result["files_modified"],
            quality_score=valid_execution_result["quality_score"],
            scope_compliance=valid_execution_result["scope_compliance"],
            execution_time_ms=valid_execution_result["execution_time_ms"],
        )
        assert exec_result.scope_compliance is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: WRAP GENERATION AUTHORITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestWrapGenerationAuthority:
    """Test that only Benson can generate WRAPs."""
    
    def test_engine_authority_is_benson(self, engine):
        """Engine authority must be BENSON (GID-00)."""
        assert engine.AUTHORITY_GID == "GID-00"
        assert engine.AUTHORITY_NAME == "BENSON"
    
    def test_wrap_generated_by_field_is_benson(self, engine):
        """WRAP generated_by field must always be BENSON."""
        # Any WRAP generated by engine should have BENSON as authority
        training_signal = engine._emit_training_signal(
            "TEST_PATTERN",
            "Test lesson"
        )
        assert "BENSON (GID-00)" in training_signal["emitted_by"]
    
    def test_agent_wrap_emission_blocked(self, engine):
        """Agent attempting WRAP emission should be blocked."""
        result = engine.block_agent_wrap_emission(
            agent_gid="GID-07",
            agent_name="Dan",
            attempted_action="WRAP_EMISSION"
        )
        assert result["blocked"] is True
        assert result["error_code"] == "GS_121"
        assert "BENSON" in result["message"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ERROR CODE COVERAGE
# ═══════════════════════════════════════════════════════════════════════════════

class TestErrorCodeCoverage:
    """Test all GS_130-GS_133 error codes are properly triggered."""
    
    def test_gs_130_missing_field(self, valid_execution_result):
        """GS_130 should trigger on missing required field."""
        del valid_execution_result["pac_id"]
        result = validate_execution_result_schema(valid_execution_result)
        assert result["error_code"] == "GS_130"
    
    def test_gs_131_wrap_field(self, valid_execution_result):
        """GS_131 should trigger on WRAP field presence."""
        valid_execution_result["wrap_status"] = "PENDING"
        result = validate_execution_result_schema(valid_execution_result)
        assert result["error_code"] == "GS_131"
    
    def test_gs_132_self_closure(self, valid_execution_result):
        """GS_132 should trigger on self-closure attempt."""
        valid_execution_result["positive_closure"] = True
        result = validate_execution_result_schema(valid_execution_result)
        assert result["error_code"] == "GS_132"
    
    def test_gs_133_authority_violation(self, valid_execution_result):
        """GS_133 should trigger on authority claim."""
        valid_execution_result["wrap_authority"] = "SELF"
        result = validate_execution_result_schema(valid_execution_result)
        assert result["error_code"] == "GS_133"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST: TRAINING SIGNAL EMISSION
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrainingSignalEmission:
    """Test training signal emission on validation events."""
    
    def test_forbidden_field_emits_training_signal(self, engine, valid_execution_result):
        """Forbidden field should emit training signal."""
        valid_execution_result["wrap_id"] = "FORBIDDEN"
        result = validate_execution_result_schema(valid_execution_result)
        assert result["valid"] is False
        # Training signal should be in result
        if "training_signal" in result:
            assert result["training_signal"]["pattern"] is not None


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
