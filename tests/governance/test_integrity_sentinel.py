"""
PAC-P825: IntegritySentinel Test Suite

Tests SEAL-01 and SEAL-02 invariants for constitutional immutability.

SEAL-01: Critical files MUST match governance.lock baseline
SEAL-02: Modification requires SCRAM reset + re-baselining

Test Coverage:
- Baseline creation (TOFU)
- Integrity verification (pass/fail)
- File modification detection
- SCRAM trigger on breach
- Baseline reset workflow
- Missing file handling
"""

import pytest
import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from core.governance.integrity_sentinel import (
    IntegritySentinel,
    get_integrity_sentinel,
    initialize_integrity_sentinel,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_workspace(tmp_path):
    """
    Create temporary workspace with mock governance files.
    """
    # Create directory structure
    gov_dir = tmp_path / "core" / "governance"
    swarm_dir = tmp_path / "core" / "swarm"
    runner_dir = tmp_path / "core" / "runners"
    logs_dir = tmp_path / "logs" / "governance"
    
    gov_dir.mkdir(parents=True)
    swarm_dir.mkdir(parents=True)
    runner_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)
    
    # Create mock critical files
    (gov_dir / "scram.py").write_text("# SCRAM v1.0\ndef emergency_halt(): pass\n")
    (gov_dir / "test_governance_layer.py").write_text("# TGL v1.0\nclass SemanticJudge: pass\n")
    (gov_dir / "inspector_general.py").write_text("# IG v1.0\nclass InspectorGeneral: pass\n")
    (swarm_dir / "byzantine_voter.py").write_text("# Byzantine v1.0\nclass Voter: pass\n")
    (runner_dir / "sovereign_runner.py").write_text("# Runner v1.0\nclass Runner: pass\n")
    
    # Return workspace root and change working directory
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    yield tmp_path
    
    # Restore original directory
    os.chdir(old_cwd)


@pytest.fixture
def mock_scram():
    """
    Mock SCRAM controller for testing.
    """
    scram = MagicMock()
    scram.status = "OPERATIONAL"
    scram.emergency_halt = AsyncMock()
    return scram


@pytest.fixture
def sentinel(temp_workspace, mock_scram):
    """
    IntegritySentinel instance with temp workspace and mock SCRAM.
    """
    return IntegritySentinel(scram=mock_scram)


# ============================================================================
# TEST SEAL-01: BASELINE INTEGRITY VERIFICATION
# ============================================================================

class TestSEAL01_IntegrityVerification:
    """
    SEAL-01: Critical files MUST match governance.lock baseline.
    """
    
    @pytest.mark.asyncio
    async def test_intact_files_pass_verification(self, sentinel, temp_workspace):
        """
        SEAL-01: Unmodified files should pass integrity check.
        """
        # Create baseline
        sentinel.baseline_hashes = sentinel._load_or_create_baseline()
        
        # Verify integrity
        result = await sentinel.verify_integrity()
        
        assert result == "INTEGRITY_VERIFIED"
        assert sentinel.scram.emergency_halt.call_count == 0
    
    @pytest.mark.asyncio
    async def test_modified_file_triggers_scram(self, sentinel, temp_workspace):
        """
        SEAL-01: Modified file should trigger SCRAM.
        """
        # Create baseline
        sentinel.baseline_hashes = sentinel._load_or_create_baseline()
        
        # Modify critical file
        scram_file = temp_workspace / "core" / "governance" / "scram.py"
        scram_file.write_text("# SCRAM v1.0 - MODIFIED\ndef emergency_halt(): pass\n")
        
        # Verify integrity (should detect modification)
        result = await sentinel.verify_integrity()
        
        assert result == "BREACH_DETECTED"
        assert sentinel.scram.emergency_halt.call_count == 1
        
        # Check SCRAM reason
        call_args = sentinel.scram.emergency_halt.call_args
        reason = call_args.kwargs["reason"]
        assert "INTEGRITY_BREACH" in reason
        assert "scram.py" in reason
    
    @pytest.mark.asyncio
    async def test_multiple_modified_files_trigger_scram_once(self, sentinel, temp_workspace):
        """
        SEAL-01: Multiple violations should trigger SCRAM once with all files listed.
        """
        # Create baseline
        sentinel.baseline_hashes = sentinel._load_or_create_baseline()
        
        # Modify multiple critical files
        (temp_workspace / "core" / "governance" / "scram.py").write_text("# MODIFIED\n")
        (temp_workspace / "core" / "governance" / "inspector_general.py").write_text("# MODIFIED\n")
        
        # Verify integrity
        result = await sentinel.verify_integrity()
        
        assert result == "BREACH_DETECTED"
        assert sentinel.scram.emergency_halt.call_count == 1
        
        # Check reason includes both files
        reason = sentinel.scram.emergency_halt.call_args.kwargs["reason"]
        assert "scram.py" in reason
        assert "inspector_general.py" in reason
    
    @pytest.mark.asyncio
    async def test_missing_file_triggers_scram(self, sentinel, temp_workspace):
        """
        SEAL-01: Missing critical file should trigger SCRAM.
        """
        # Create baseline
        sentinel.baseline_hashes = sentinel._load_or_create_baseline()
        
        # Delete critical file
        scram_file = temp_workspace / "core" / "governance" / "scram.py"
        scram_file.unlink()
        
        # Verify integrity
        result = await sentinel.verify_integrity()
        
        assert result == "BREACH_DETECTED"
        assert sentinel.scram.emergency_halt.call_count == 1


# ============================================================================
# TEST SEAL-02: BASELINE RESET WORKFLOW
# ============================================================================

class TestSEAL02_BaselineReset:
    """
    SEAL-02: Modification requires SCRAM reset + re-baselining.
    """
    
    @pytest.mark.asyncio
    async def test_baseline_reset_requires_confirmation(self, sentinel, temp_workspace):
        """
        SEAL-02: Baseline reset requires explicit confirmation string.
        """
        # Try reset without confirmation
        result = await sentinel.reset_baseline("WRONG_CONFIRMATION")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_baseline_reset_creates_new_lock(self, sentinel, temp_workspace):
        """
        SEAL-02: Baseline reset should create new governance.lock.
        """
        # Create initial baseline
        sentinel.baseline_hashes = sentinel._load_or_create_baseline()
        assert os.path.exists(sentinel.LOCK_FILE)
        
        # Modify file
        scram_file = temp_workspace / "core" / "governance" / "scram.py"
        scram_file.write_text("# SCRAM v2.0 - UPDATED\n")
        
        # Reset baseline (after SCRAM reset)
        result = await sentinel.reset_baseline("RESET_GOVERNANCE_BASELINE")
        
        assert result is True
        assert os.path.exists(sentinel.LOCK_FILE)
        
        # Verify new baseline reflects current state
        with open(sentinel.LOCK_FILE, 'r') as f:
            new_baseline = json.load(f)
        
        assert len(new_baseline) == len(IntegritySentinel.CRITICAL_FILES)


# ============================================================================
# TEST BASELINE CREATION (TOFU)
# ============================================================================

class TestBaselineCreation:
    """
    Trust On First Use (TOFU) baseline creation.
    """
    
    def test_baseline_creation_on_first_use(self, sentinel, temp_workspace):
        """
        First run should create governance.lock with SHA3-512 hashes.
        """
        # Ensure no lock file exists
        assert not os.path.exists(sentinel.LOCK_FILE)
        
        # Load baseline (should create lock file)
        baseline = sentinel._load_or_create_baseline()
        
        assert os.path.exists(sentinel.LOCK_FILE)
        assert len(baseline) == len(IntegritySentinel.CRITICAL_FILES)
        
        # Verify hashes are SHA3-512 (128 hex chars)
        for path, hash_val in baseline.items():
            assert len(hash_val) == 128  # SHA3-512 hex digest length
    
    def test_baseline_persistence_across_instances(self, sentinel, temp_workspace, mock_scram):
        """
        Lock file should persist across IntegritySentinel instances.
        """
        # Create baseline with first instance
        baseline1 = sentinel._load_or_create_baseline()
        
        # Create new instance
        sentinel2 = IntegritySentinel(scram=mock_scram)
        baseline2 = sentinel2._load_or_create_baseline()
        
        # Baselines should match
        assert baseline1 == baseline2


# ============================================================================
# TEST ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """
    Error handling for edge cases.
    """
    
    @pytest.mark.asyncio
    async def test_no_baseline_returns_no_baseline_status(self, sentinel, temp_workspace):
        """
        Missing baseline should return NO_BASELINE (not crash).
        """
        # Remove lock file if exists
        if os.path.exists(sentinel.LOCK_FILE):
            os.remove(sentinel.LOCK_FILE)
        
        # Clear baseline
        sentinel.baseline_hashes = {}
        
        # Mock _load_or_create_baseline to return empty dict
        sentinel._load_or_create_baseline = lambda: {}
        
        # Verify integrity
        result = await sentinel.verify_integrity()
        
        assert result == "NO_BASELINE"
    
    def test_hash_computation_handles_missing_files(self, sentinel, temp_workspace):
        """
        Hash computation should handle missing files gracefully.
        """
        # Try to hash non-existent file
        hash_val = sentinel._compute_hash("nonexistent/file.py")
        
        assert hash_val == "FILE_MISSING"


# ============================================================================
# TEST STATUS REPORTING
# ============================================================================

class TestStatusReporting:
    """
    Status reporting for monitoring.
    """
    
    def test_get_status_returns_correct_info(self, sentinel, temp_workspace):
        """
        get_status() should return baseline and SCRAM info.
        """
        # Create baseline
        sentinel.baseline_hashes = sentinel._load_or_create_baseline()
        
        # Get status
        status = sentinel.get_status()
        
        assert status["baseline_loaded"] is True
        assert status["protected_files"] == len(IntegritySentinel.CRITICAL_FILES)
        assert status["lock_file"] == sentinel.LOCK_FILE
        assert status["lock_file_exists"] is True
        assert status["scram_status"] == "OPERATIONAL"


# ============================================================================
# TEST SINGLETON PATTERN
# ============================================================================

class TestSingletonPattern:
    """
    Singleton factory pattern tests.
    """
    
    def test_get_integrity_sentinel_returns_singleton(self):
        """
        get_integrity_sentinel() should return same instance.
        """
        sentinel1 = get_integrity_sentinel()
        sentinel2 = get_integrity_sentinel()
        
        assert sentinel1 is sentinel2
    
    @pytest.mark.asyncio
    async def test_initialize_integrity_sentinel_helper(self, temp_workspace):
        """
        initialize_integrity_sentinel() should load baseline.
        """
        sentinel = await initialize_integrity_sentinel()
        
        assert sentinel.baseline_hashes is not None
        assert len(sentinel.baseline_hashes) > 0
