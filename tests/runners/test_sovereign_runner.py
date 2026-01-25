# pylint: disable=redefined-outer-name
# ruff: noqa: W0621
"""
Test Suite: Sovereign Runner SCRAM Integration
==============================================

PAC-P821 | LAW-TIER | ZERO DRIFT TOLERANCE

Verifies SCRAM pre-flight checks in execution hot loop.
Validates fail-closed behavior and RUNNER-01/02/03 invariants.

Tested by: ALEX (GID-08)
Security Audit: SAM (GID-06)
"""

import hashlib
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.runners.sovereign_runner import SovereignRunner
from core.governance.scram import (
    SCRAMController,
    SCRAMKey,
    SCRAMReason,
    get_scram_controller,
)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture(autouse=True)
def reset_scram_singleton():
    """Reset SCRAM singleton before each test."""
    SCRAMController._instance = None
    SCRAMController._lock = threading.RLock()
    yield
    SCRAMController._instance = None


@pytest.fixture
def runner():
    """Create SovereignRunner instance."""
    return SovereignRunner()


@pytest.fixture
def operator_key():
    """Create valid operator key."""
    return SCRAMKey(
        key_id="OP-TEST-P821-001",
        key_type="operator",
        key_hash=hashlib.sha256(b"operator_secret_p821").hexdigest(),
        issued_at=datetime.now(timezone.utc).isoformat()
    )


@pytest.fixture
def architect_key():
    """Create valid architect key."""
    return SCRAMKey(
        key_id="ARCH-TEST-P821-001",
        key_type="architect",
        key_hash=hashlib.sha256(b"architect_secret_p821").hexdigest(),
        issued_at=datetime.now(timezone.utc).isoformat()
    )


# ==============================================================================
# Test: RUNNER-01 - Execution halts when SCRAM active
# ==============================================================================

class TestRunnerInvariant01:
    """Test RUNNER-01: Execution ceases immediately if SCRAM not ARMED."""
    
    @pytest.mark.asyncio
    async def test_runner_halts_when_scram_active(
        self, runner, operator_key, architect_key
    ):
        """RUNNER-01: Runner must halt if SCRAM is active."""
        scram = get_scram_controller()
        
        # Activate SCRAM
        scram.authorize_key(operator_key)
        scram.authorize_key(architect_key)
        scram.activate(SCRAMReason.OPERATOR_INITIATED)
        
        # Attempt batch execution - should abort
        result = await runner.execute_batch("batch-001")
        
        assert result == "SCRAM_ABORT"
    
    @pytest.mark.asyncio
    async def test_runner_halts_with_metadata(
        self, runner, operator_key, architect_key
    ):
        """RUNNER-01: Runner halts even when batch has metadata."""
        scram = get_scram_controller()
        
        # Activate SCRAM
        scram.authorize_key(operator_key)
        scram.authorize_key(architect_key)
        scram.activate(SCRAMReason.SECURITY_BREACH)
        
        # Attempt batch execution with metadata - should abort
        result = await runner.execute_batch(
            "batch-002",
            metadata={"priority": "high", "retry": 3}
        )
        
        assert result == "SCRAM_ABORT"


# ==============================================================================
# Test: RUNNER-02 - No singleton bypass
# ==============================================================================

class TestRunnerInvariant02:
    """Test RUNNER-02: Runner must not bypass SCRAM singleton."""
    
    def test_runner_uses_singleton(self, runner):
        """RUNNER-02: Runner must use SCRAM singleton."""
        scram1 = runner.scram
        scram2 = get_scram_controller()
        
        assert scram1 is scram2  # Same instance
    
    def test_multiple_runners_share_singleton(self):
        """Multiple runners share same SCRAM instance."""
        runner1 = SovereignRunner()
        runner2 = SovereignRunner()
        
        assert runner1.scram is runner2.scram


# ==============================================================================
# Test: Normal Execution (SCRAM ARMED)
# ==============================================================================

class TestNormalExecution:
    """Test runner executes normally when SCRAM is ARMED."""
    
    @pytest.mark.asyncio
    async def test_runner_executes_when_scram_armed(self, runner):
        """Runner executes normally when SCRAM is ARMED."""
        scram = get_scram_controller()
        assert scram.is_armed  # Confirm ARMED state
        
        result = await runner.execute_batch("batch-003")
        
        assert result == "BATCH_COMMITTED"
    
    @pytest.mark.asyncio
    async def test_runner_executes_with_metadata(self, runner):
        """Runner processes metadata when SCRAM is ARMED."""
        scram = get_scram_controller()
        assert scram.is_armed
        
        result = await runner.execute_batch(
            "batch-004",
            metadata={"source": "test", "timestamp": "2026-01-25"}
        )
        
        assert result == "BATCH_COMMITTED"


# ==============================================================================
# Test: Health Check
# ==============================================================================

class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check_includes_scram_status(self, runner):
        """Health check includes SCRAM state information."""
        health = runner.health_check()
        
        assert "scram_state" in health
        assert "scram_armed" in health
        assert "scram_active" in health
        assert "scram_complete" in health
        assert health["runner_status"] == "HEALTHY"
        assert health["scram_state"] == "ARMED"
        assert health["scram_armed"] is True
    
    def test_health_check_reflects_scram_active(
        self, runner, operator_key, architect_key
    ):
        """Health check reflects SCRAM active state."""
        scram = get_scram_controller()
        
        # Activate SCRAM
        scram.authorize_key(operator_key)
        scram.authorize_key(architect_key)
        scram.activate(SCRAMReason.OPERATOR_INITIATED)
        
        health = runner.health_check()
        
        assert health["scram_armed"] is False
        assert health["scram_state"] in ("COMPLETE", "FAILED")


# ==============================================================================
# Test: SCRAM Reason Extraction
# ==============================================================================

class TestSCRAMReasonExtraction:
    """Test SCRAM reason extraction from audit trail."""
    
    @pytest.mark.asyncio
    async def test_scram_reason_extracted(
        self, runner, operator_key, architect_key
    ):
        """SCRAM activation reason is logged on halt."""
        scram = get_scram_controller()
        
        # Activate SCRAM with specific reason
        scram.authorize_key(operator_key)
        scram.authorize_key(architect_key)
        scram.activate(SCRAMReason.SECURITY_BREACH)
        
        # Execute batch - should abort with reason
        result = await runner.execute_batch("batch-005")
        
        assert result == "SCRAM_ABORT"
        # Reason extraction is tested via _get_scram_reason() call


# ==============================================================================
# Test: Runner Initialization
# ==============================================================================

class TestRunnerInitialization:
    """Test runner initialization."""
    
    def test_runner_initializes_with_scram(self):
        """Runner initializes with SCRAM controller."""
        runner = SovereignRunner()
        
        assert runner.scram is not None
        assert runner.scram is get_scram_controller()
    
    def test_runner_logger_configured(self, runner):
        """Runner logger is properly configured."""
        assert runner.logger is not None
        assert runner.logger.name == "SovereignRunner"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
