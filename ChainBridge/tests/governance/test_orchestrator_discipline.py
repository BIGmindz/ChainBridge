#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════
PAC-BENSON-P45 REGRESSION TESTS
ORCHESTRATOR DISCIPLINE — IDENTITY, GATEWAY & RESPONSE DISCIPLINE
══════════════════════════════════════════════════════════════════════════════

Tests for:
- GS_116: GATEWAY_BYPASS
- GS_117: AGENT_SELF_ACTIVATION
- GS_118: IDENTITY_DRIFT
- GS_119: UNSOLICITED_EXECUTION

══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import sys
from pathlib import Path

# Ensure tools is in path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.governance.orchestrator_guard import (
    OrchestratorGuard,
    GatewayState,
    ActivationState,
    GatewayCheck,
    ActivationCheck,
    IdentityCheck,
    validate_gateway,
    validate_activation,
    validate_identity,
    validate_execution_request,
    VALID_AGENT_GIDS,
    EXECUTION_LANES,
    ORCHESTRATOR_GID,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def guard():
    """Create fresh OrchestratorGuard instance."""
    return OrchestratorGuard()


@pytest.fixture
def valid_pac_content():
    """Valid PAC content with all required blocks."""
    return """
---
artifact_type: PAC
artifact_id: PAC-TEST-001
artifact_status: ISSUED
mode: ADVISORY

AGENT_ACTIVATION_ACK:
  agent_name: SONNY
  gid: GID-01
  activated_by: GID-00
  timestamp: 2025-06-18T10:00:00Z

GATEWAY_CHECKS:
  governance:
    - FAIL_CLOSED
    - BENSON_SEQUENCING
  assumptions:
    - All imports resolved locally
---

## TASK_BLOCK
- Test task 1
- Test task 2
"""


@pytest.fixture
def missing_gateway_content():
    """PAC content missing GATEWAY_CHECKS block."""
    return """
---
artifact_type: PAC
artifact_id: PAC-TEST-002

AGENT_ACTIVATION_ACK:
  agent_name: SONNY
  gid: GID-01
  activated_by: GID-00
---
"""


@pytest.fixture
def missing_activation_content():
    """PAC content missing AGENT_ACTIVATION_ACK block."""
    return """
---
artifact_type: PAC
artifact_id: PAC-TEST-003

GATEWAY_CHECKS:
  governance:
    - FAIL_CLOSED
---
"""


@pytest.fixture
def identity_drift_content():
    """PAC content with identity mismatch (name doesn't match GID-01 registry)."""
    return """
---
artifact_type: PAC
artifact_id: PAC-TEST-004

AGENT_ACTIVATION_ACK:
  agent_name: MAGGIE
  gid: GID-01
  activated_by: GID-00
  execution_lane: ORCHESTRATION

GATEWAY_CHECKS:
  governance:
    - FAIL_CLOSED
---
"""


@pytest.fixture
def unsolicited_execution_content():
    """PAC content with unsolicited execution."""
    return """
---
artifact_type: PAC
artifact_id: PAC-TEST-005
artifact_status: EXECUTED
mode: ADVISORY

AGENT_ACTIVATION_ACK:
  agent_name: SONNY
  gid: GID-01
  activated_by: GID-00

GATEWAY_CHECKS:
  governance:
    - FAIL_CLOSED
---
"""


# ============================================================================
# TEST CLASS: GATEWAY VALIDATION
# ============================================================================

class TestGatewayValidation:
    """Test Benson Gateway enforcement (GS_116)."""
    
    def test_gateway_valid(self, guard, valid_pac_content):
        """Valid PAC passes gateway check."""
        result = guard.check_gateway(valid_pac_content, "GID-01")
        assert result.passed is True
        assert result.error_code is None
    
    def test_gateway_missing_block(self, guard, missing_gateway_content):
        """Missing GATEWAY_CHECKS block triggers GS_116."""
        result = guard.check_gateway(missing_gateway_content, "GID-01")
        assert result.passed is False
        assert result.error_code == "GS_116"
        assert "GATEWAY_BYPASS" in result.message
    
    def test_gateway_unknown_agent(self, guard, valid_pac_content):
        """Unknown agent GID triggers GS_116."""
        result = guard.check_gateway(valid_pac_content, "GID-99")
        assert result.passed is False
        assert result.error_code == "GS_116"
        assert "Unknown agent GID" in result.message
    
    def test_gateway_validates_governance_field(self, guard):
        """GATEWAY_CHECKS must contain governance field."""
        content = """
GATEWAY_CHECKS:
  assumptions:
    - Some assumption
"""
        result = guard.validate_gateway_block(content)
        assert result.passed is False
        assert result.error_code == "GS_116"
        assert "governance" in result.message.lower()
    
    def test_gateway_standalone_function(self, valid_pac_content):
        """Standalone validate_gateway function works correctly."""
        errors = validate_gateway(valid_pac_content)
        assert errors == []
    
    def test_gateway_standalone_failure(self, missing_gateway_content):
        """Standalone validate_gateway reports errors."""
        errors = validate_gateway(missing_gateway_content)
        assert len(errors) == 1
        assert errors[0]["code"] == "GS_116"


# ============================================================================
# TEST CLASS: AGENT ACTIVATION
# ============================================================================

class TestAgentActivation:
    """Test agent activation validation (GS_117)."""
    
    def test_activation_valid(self, guard, valid_pac_content):
        """Valid activation block passes check."""
        result = guard.check_activation(valid_pac_content)
        assert result.valid is True
        assert result.agent_gid == "GID-01"
        assert result.agent_name == "SONNY"
    
    def test_activation_missing_block(self, guard):
        """Missing AGENT_ACTIVATION_ACK triggers GS_117."""
        content = "Some content without activation block"
        result = guard.check_activation(content)
        assert result.valid is False
        assert result.error_code == "GS_117"
        assert "AGENT_SELF_ACTIVATION" in result.message
    
    def test_activation_invalid_gid(self, guard):
        """Invalid GID triggers GS_117."""
        content = """
AGENT_ACTIVATION_ACK:
  agent_name: UNKNOWN
  gid: GID-99
  activated_by: GID-00
"""
        result = guard.check_activation(content)
        assert result.valid is False
        assert result.error_code == "GS_117"
        assert "not in registry" in result.message
    
    def test_activation_name_mismatch_triggers_identity_drift(self, guard):
        """Agent name mismatch triggers GS_118 (identity drift)."""
        content = """
AGENT_ACTIVATION_ACK:
  agent_name: WRONG_NAME
  gid: GID-01
  activated_by: GID-00
"""
        result = guard.check_activation(content)
        assert result.valid is False
        assert result.error_code == "GS_118"
        assert "IDENTITY_DRIFT" in result.message
    
    def test_activation_standalone_function(self, valid_pac_content):
        """Standalone validate_activation function works correctly."""
        errors = validate_activation(valid_pac_content)
        assert errors == []
    
    def test_activation_standalone_failure(self, missing_activation_content):
        """Standalone validate_activation reports errors."""
        errors = validate_activation(missing_activation_content)
        assert len(errors) == 1
        assert errors[0]["code"] == "GS_117"


# ============================================================================
# TEST CLASS: IDENTITY CONSISTENCY
# ============================================================================

class TestIdentityConsistency:
    """Test identity consistency validation (GS_118)."""
    
    def test_identity_valid(self, guard, valid_pac_content):
        """Valid identity passes consistency check."""
        result = guard.check_identity_consistency(valid_pac_content)
        assert result.valid is True
        assert result.declared_gid == "GID-01"
        assert result.declared_name == "SONNY"
    
    def test_identity_missing_activation_block(self, guard):
        """Missing activation block fails identity check."""
        content = "Some content without identity"
        result = guard.check_identity_consistency(content)
        assert result.valid is False
        assert result.error_code == "GS_118"
        assert "Cannot determine primary identity" in result.message
    
    def test_identity_unauthorized_lane(self, guard):
        """Agent in unauthorized lane triggers GS_118."""
        content = """
AGENT_ACTIVATION_ACK:
  agent_name: SONNY
  gid: GID-01
  activated_by: GID-00
  execution_lane: ORCHESTRATION
"""
        result = guard.check_identity_consistency(content)
        assert result.valid is False
        assert result.error_code == "GS_118"
        assert "not authorized for lane" in result.message
    
    def test_identity_allows_benson_in_authority(self, guard):
        """GID-00 allowed in authority fields without drift error."""
        content = """
AGENT_ACTIVATION_ACK:
  agent_name: SONNY
  gid: GID-01
  activated_by: GID-00

authority: GID-00
orchestrator: GID-00
"""
        result = guard.check_identity_consistency(content)
        assert result.valid is True
    
    def test_identity_standalone_function(self, valid_pac_content):
        """Standalone validate_identity function works correctly."""
        errors = validate_identity(valid_pac_content)
        assert errors == []
    
    def test_identity_standalone_failure(self, identity_drift_content):
        """Standalone validate_identity reports errors."""
        errors = validate_identity(identity_drift_content)
        assert len(errors) == 1
        assert errors[0]["code"] == "GS_118"


# ============================================================================
# TEST CLASS: EXECUTION REQUEST
# ============================================================================

class TestExecutionRequest:
    """Test execution request validation (GS_119)."""
    
    def test_execution_advisory_mode_valid(self, guard, valid_pac_content):
        """Advisory mode with ISSUED status is valid."""
        result = guard.check_execution_request(valid_pac_content)
        assert result["valid"] is True
    
    def test_execution_without_executable_mode(self, guard, unsolicited_execution_content):
        """EXECUTED status without EXECUTABLE mode triggers GS_119."""
        result = guard.check_execution_request(unsolicited_execution_content)
        assert result["valid"] is False
        assert result["error_code"] == "GS_119"
        assert "UNSOLICITED_EXECUTION" in result["message"]
    
    def test_execution_with_executable_mode_valid(self, guard):
        """EXECUTED status with EXECUTABLE mode is valid."""
        content = """
artifact_status: EXECUTED
mode: EXECUTABLE
"""
        result = guard.check_execution_request(content)
        assert result["valid"] is True
    
    def test_execution_closed_status_without_mode(self, guard):
        """CLOSED status without EXECUTABLE mode triggers GS_119."""
        content = """
artifact_status: CLOSED
mode: ADVISORY
"""
        result = guard.check_execution_request(content)
        assert result["valid"] is False
        assert result["error_code"] == "GS_119"
    
    def test_execution_no_status_is_advisory(self, guard):
        """No artifact_status is treated as advisory only."""
        content = "Some content without status"
        result = guard.check_execution_request(content)
        assert result["valid"] is True
        assert "advisory only" in result["message"].lower()
    
    def test_execution_standalone_function(self, valid_pac_content):
        """Standalone validate_execution_request function works correctly."""
        errors = validate_execution_request(valid_pac_content)
        assert errors == []
    
    def test_execution_standalone_failure(self, unsolicited_execution_content):
        """Standalone validate_execution_request reports errors."""
        errors = validate_execution_request(unsolicited_execution_content)
        assert len(errors) == 1
        assert errors[0]["code"] == "GS_119"


# ============================================================================
# TEST CLASS: FULL DISCIPLINE VALIDATION
# ============================================================================

class TestFullDisciplineValidation:
    """Test full orchestrator discipline validation."""
    
    def test_full_validation_valid(self, guard, valid_pac_content):
        """Valid content passes all checks."""
        result = guard.validate_orchestrator_discipline(valid_pac_content)
        assert result["valid"] is True
        assert result["errors"] == []
        assert "gateway" in result["checks"]
        assert "activation" in result["checks"]
        assert "identity" in result["checks"]
        assert "execution" in result["checks"]
    
    def test_full_validation_multiple_errors(self, guard):
        """Invalid content accumulates multiple errors."""
        content = """
artifact_status: EXECUTED
mode: ADVISORY
"""
        result = guard.validate_orchestrator_discipline(content)
        assert result["valid"] is False
        assert len(result["errors"]) >= 2  # At least gateway and activation errors
    
    def test_full_validation_infers_gid(self, guard, valid_pac_content):
        """Validation infers GID from content if not provided."""
        result = guard.validate_orchestrator_discipline(valid_pac_content)
        assert result["valid"] is True
    
    def test_full_validation_with_explicit_gid(self, guard, valid_pac_content):
        """Validation uses explicit GID when provided."""
        result = guard.validate_orchestrator_discipline(valid_pac_content, "GID-01")
        assert result["valid"] is True


# ============================================================================
# TEST CLASS: AGENT REGISTRY
# ============================================================================

class TestAgentRegistry:
    """Test agent registry constants."""
    
    def test_benson_is_orchestrator(self):
        """BENSON is registered as GID-00."""
        assert "GID-00" in VALID_AGENT_GIDS
        assert VALID_AGENT_GIDS["GID-00"] == "BENSON"
    
    def test_orchestrator_gid_constant(self):
        """ORCHESTRATOR_GID is GID-00."""
        assert ORCHESTRATOR_GID == "GID-00"
    
    def test_only_benson_in_orchestration_lane(self):
        """Only BENSON (GID-00) is authorized for ORCHESTRATION lane."""
        assert EXECUTION_LANES["ORCHESTRATION"] == ["GID-00"]
    
    def test_execution_lane_has_multiple_agents(self):
        """EXECUTION lane has multiple authorized agents."""
        assert len(EXECUTION_LANES["EXECUTION"]) > 1
        assert "GID-01" in EXECUTION_LANES["EXECUTION"]


# ============================================================================
# TEST CLASS: DATA STRUCTURES
# ============================================================================

class TestDataStructures:
    """Test data structure correctness."""
    
    def test_gateway_check_timestamp(self):
        """GatewayCheck auto-generates timestamp."""
        check = GatewayCheck(passed=True, gateway_state="OPEN")
        assert check.timestamp != ""
        assert "T" in check.timestamp  # ISO format
    
    def test_gateway_state_enum(self):
        """GatewayState enum has expected values."""
        assert GatewayState.CLOSED.value == "CLOSED"
        assert GatewayState.OPEN.value == "OPEN"
        assert GatewayState.BLOCKED.value == "BLOCKED"
    
    def test_activation_state_enum(self):
        """ActivationState enum has expected values."""
        assert ActivationState.INACTIVE.value == "INACTIVE"
        assert ActivationState.PENDING.value == "PENDING"
        assert ActivationState.ACTIVE.value == "ACTIVE"
        assert ActivationState.SUSPENDED.value == "SUSPENDED"


# ============================================================================
# TEST CLASS: INTEGRATION
# ============================================================================

class TestIntegration:
    """Integration tests for orchestrator discipline."""
    
    def test_guard_initial_state(self):
        """Fresh guard starts with CLOSED gateway."""
        guard = OrchestratorGuard()
        assert guard.gateway_state == GatewayState.CLOSED
        assert guard.active_agents == {}
    
    def test_complete_pac_workflow(self, guard, valid_pac_content):
        """Complete PAC passes all discipline checks."""
        # Gateway check
        gateway_result = guard.check_gateway(valid_pac_content, "GID-01")
        assert gateway_result.passed is True
        
        # Activation check
        activation_result = guard.check_activation(valid_pac_content)
        assert activation_result.valid is True
        
        # Identity check
        identity_result = guard.check_identity_consistency(valid_pac_content)
        assert identity_result.valid is True
        
        # Execution check
        execution_result = guard.check_execution_request(valid_pac_content)
        assert execution_result["valid"] is True
        
        # Full validation
        full_result = guard.validate_orchestrator_discipline(valid_pac_content)
        assert full_result["valid"] is True


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
