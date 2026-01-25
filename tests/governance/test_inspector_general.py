"""
Test Suite for Inspector General (IG) Node - PAC-P824
=====================================================

Tests verify IG constitutional invariants:
    IG-01: IG MUST trigger SCRAM upon detecting REJECTED verdict
    IG-02: IG MUST NOT modify audit log (read-only operation)

Test Coverage:
    - SCRAM trigger on REJECTED verdicts
    - Read-only audit log access
    - Incremental log scanning
    - Duplicate entry handling
    - Error handling and fail-closed behavior
    - Status reporting
"""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from core.governance.inspector_general import (
    InspectorGeneral,
    get_inspector_general,
    start_inspector_general_monitoring
)


@pytest.fixture
def temp_audit_log():
    """Create a temporary audit log file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
        log_path = Path(f.name)
    
    yield log_path
    
    # Cleanup
    if log_path.exists():
        log_path.unlink()


@pytest.fixture
def mock_scram_controller():
    """Create a mock SCRAM controller."""
    scram = MagicMock()
    scram.status = "OPERATIONAL"
    scram.emergency_halt = AsyncMock()
    return scram


@pytest.fixture
def ig_node(temp_audit_log, mock_scram_controller):
    """Create an IG node instance with mocked dependencies."""
    return InspectorGeneral(
        log_path=str(temp_audit_log),
        scram_controller=mock_scram_controller
    )


# ============================================================================
# IG-01: SCRAM TRIGGER ON REJECTED VERDICTS
# ============================================================================

class TestIGInvariant01_SCRAMTrigger:
    """Verify IG-01: IG MUST trigger SCRAM upon detecting REJECTED verdict."""
    
    @pytest.mark.asyncio
    async def test_rejected_verdict_triggers_scram(
        self,
        ig_node,
        temp_audit_log,
        mock_scram_controller
    ):
        """
        IG-01.1: REJECTED verdict in audit log triggers SCRAM emergency halt.
        
        Test Flow:
            1. Write REJECTED judgment to audit log
            2. IG scans log
            3. IG detects REJECTED verdict
            4. SCRAM emergency_halt() is called with violation details
        """
        # Create REJECTED audit entry
        rejected_entry = {
            "manifest_id": "MANIFEST-TEST001",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_gid": "GID-04",
            "git_commit_hash": "abc123" * 6 + "abcd",  # 40 chars
            "judgment": "Rejected",
            "reason": "REJECTED: Invalid Ed25519 signature",
            "audit_log": {}
        }
        
        # Write to audit log
        with open(temp_audit_log, 'w') as f:
            f.write(json.dumps(rejected_entry) + '\n')
        
        # Scan log (single scan, not continuous monitoring)
        await ig_node._scan_log()
        
        # Verify SCRAM was triggered
        assert mock_scram_controller.emergency_halt.called
        
        # Verify SCRAM reason contains violation details
        call_args = mock_scram_controller.emergency_halt.call_args
        reason = call_args.kwargs['reason']
        
        assert "IG_VIOLATION_DETECTED" in reason
        assert "MANIFEST-TEST001" in reason
        assert "GID-04" in reason
        assert "REJECTED" in reason
    
    @pytest.mark.asyncio
    async def test_multiple_rejected_verdicts_trigger_scram_once_each(
        self,
        ig_node,
        temp_audit_log,
        mock_scram_controller
    ):
        """
        IG-01.2: Multiple REJECTED verdicts trigger SCRAM for each unique manifest.
        
        Test Flow:
            1. Write 3 REJECTED judgments to audit log
            2. IG scans log
            3. SCRAM should be triggered 3 times (once per manifest)
        """
        # Create 3 different REJECTED entries
        for i in range(3):
            entry = {
                "manifest_id": f"MANIFEST-TEST{i:03d}",
                "timestamp": datetime.utcnow().isoformat(),
                "agent_gid": "GID-04",
                "git_commit_hash": f"{i}" * 40,
                "judgment": "Rejected",
                "reason": f"Test rejection {i}",
                "audit_log": {}
            }
            
            with open(temp_audit_log, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        
        # Scan log
        await ig_node._scan_log()
        
        # Verify SCRAM was triggered 3 times
        assert mock_scram_controller.emergency_halt.call_count == 3
    
    @pytest.mark.asyncio
    async def test_duplicate_rejected_entries_trigger_scram_once(
        self,
        ig_node,
        temp_audit_log,
        mock_scram_controller
    ):
        """
        IG-01.3: Duplicate REJECTED entries (same manifest_id) trigger SCRAM only once.
        
        Test Flow:
            1. Write same REJECTED entry twice
            2. IG scans log
            3. SCRAM should be triggered only once (de-duplication)
        """
        rejected_entry = {
            "manifest_id": "MANIFEST-DUPLICATE",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_gid": "GID-04",
            "git_commit_hash": "abc" * 13 + "a",
            "judgment": "Rejected",
            "reason": "Duplicate test",
            "audit_log": {}
        }
        
        # Write same entry twice
        with open(temp_audit_log, 'w') as f:
            f.write(json.dumps(rejected_entry) + '\n')
            f.write(json.dumps(rejected_entry) + '\n')
        
        # Scan log
        await ig_node._scan_log()
        
        # Verify SCRAM was triggered only once
        assert mock_scram_controller.emergency_halt.call_count == 1


# ============================================================================
# IG-02: READ-ONLY AUDIT LOG ACCESS
# ============================================================================

class TestIGInvariant02_ReadOnly:
    """Verify IG-02: IG MUST NOT modify audit log (read-only operation)."""
    
    @pytest.mark.asyncio
    async def test_ig_never_writes_to_audit_log(
        self,
        ig_node,
        temp_audit_log,
        mock_scram_controller
    ):
        """
        IG-02.1: IG does not modify audit log file (read-only access).
        
        Test Flow:
            1. Write initial audit entry
            2. Record file modification time
            3. IG scans log multiple times
            4. Verify file modification time unchanged (no writes)
        """
        # Write initial entry
        entry = {
            "manifest_id": "MANIFEST-READONLY",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_gid": "GID-04",
            "git_commit_hash": "a" * 40,
            "judgment": "Approved",
            "reason": "All invariants satisfied",
            "audit_log": {}
        }
        
        with open(temp_audit_log, 'w') as f:
            f.write(json.dumps(entry) + '\n')
        
        # Record initial file stats
        initial_mtime = temp_audit_log.stat().st_mtime
        initial_size = temp_audit_log.stat().st_size
        initial_content = temp_audit_log.read_text()
        
        # IG scans log multiple times
        await ig_node._scan_log()
        await ig_node._scan_log()
        await ig_node._scan_log()
        
        # Verify file unchanged
        final_mtime = temp_audit_log.stat().st_mtime
        final_size = temp_audit_log.stat().st_size
        final_content = temp_audit_log.read_text()
        
        assert final_mtime == initial_mtime, "File modification time changed (IG wrote to log)"
        assert final_size == initial_size, "File size changed (IG wrote to log)"
        assert final_content == initial_content, "File content changed (IG wrote to log)"
    
    @pytest.mark.asyncio
    async def test_ig_handles_missing_log_gracefully(self, ig_node):
        """
        IG-02.2: IG handles missing audit log without creating it (read-only).
        
        Test Flow:
            1. Ensure audit log doesn't exist
            2. IG attempts to scan log
            3. No error raised
            4. Log file still doesn't exist (IG didn't create it)
        """
        # Ensure log doesn't exist
        if ig_node.log_path.exists():
            ig_node.log_path.unlink()
        
        # Scan non-existent log
        await ig_node._scan_log()
        
        # Verify log was not created
        assert not ig_node.log_path.exists(), "IG created log file (should be read-only)"


# ============================================================================
# APPROVED VERDICTS (NO SCRAM)
# ============================================================================

class TestApprovedVerdicts:
    """Verify IG does NOT trigger SCRAM for APPROVED verdicts."""
    
    @pytest.mark.asyncio
    async def test_approved_verdict_no_scram(
        self,
        ig_node,
        temp_audit_log,
        mock_scram_controller
    ):
        """
        Approved verdicts should NOT trigger SCRAM.
        
        Test Flow:
            1. Write APPROVED judgment to audit log
            2. IG scans log
            3. SCRAM should NOT be triggered
        """
        approved_entry = {
            "manifest_id": "MANIFEST-GOOD",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_gid": "GID-04",
            "git_commit_hash": "good" * 10,
            "judgment": "Approved",
            "reason": "All invariants satisfied",
            "audit_log": {}
        }
        
        with open(temp_audit_log, 'w') as f:
            f.write(json.dumps(approved_entry) + '\n')
        
        # Scan log
        await ig_node._scan_log()
        
        # Verify SCRAM was NOT triggered
        assert not mock_scram_controller.emergency_halt.called


# ============================================================================
# INCREMENTAL SCANNING
# ============================================================================

class TestIncrementalScanning:
    """Verify IG efficiently scans only new log entries."""
    
    @pytest.mark.asyncio
    async def test_incremental_scan_only_processes_new_entries(
        self,
        ig_node,
        temp_audit_log,
        mock_scram_controller
    ):
        """
        IG should only process new entries on subsequent scans.
        
        Test Flow:
            1. Write entry 1, scan (SCRAM count = 0)
            2. Write entry 2 (REJECTED), scan (SCRAM count = 1)
            3. Write entry 3 (REJECTED), scan (SCRAM count = 2)
            4. Scan again with no new entries (SCRAM count = 2, unchanged)
        """
        # Initial approved entry
        entry1 = {
            "manifest_id": "MANIFEST-001",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_gid": "GID-04",
            "git_commit_hash": "a" * 40,
            "judgment": "Approved",
            "reason": "OK",
            "audit_log": {}
        }
        
        with open(temp_audit_log, 'w') as f:
            f.write(json.dumps(entry1) + '\n')
        
        await ig_node._scan_log()
        assert mock_scram_controller.emergency_halt.call_count == 0
        
        # Add REJECTED entry
        entry2 = {
            "manifest_id": "MANIFEST-002",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_gid": "GID-04",
            "git_commit_hash": "b" * 40,
            "judgment": "Rejected",
            "reason": "Test rejection",
            "audit_log": {}
        }
        
        with open(temp_audit_log, 'a') as f:
            f.write(json.dumps(entry2) + '\n')
        
        await ig_node._scan_log()
        assert mock_scram_controller.emergency_halt.call_count == 1
        
        # Add another REJECTED entry
        entry3 = {
            "manifest_id": "MANIFEST-003",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_gid": "GID-04",
            "git_commit_hash": "c" * 40,
            "judgment": "Rejected",
            "reason": "Another rejection",
            "audit_log": {}
        }
        
        with open(temp_audit_log, 'a') as f:
            f.write(json.dumps(entry3) + '\n')
        
        await ig_node._scan_log()
        assert mock_scram_controller.emergency_halt.call_count == 2
        
        # Scan again with no new entries
        await ig_node._scan_log()
        assert mock_scram_controller.emergency_halt.call_count == 2  # Unchanged


# ============================================================================
# ERROR HANDLING & FAIL-CLOSED
# ============================================================================

class TestErrorHandling:
    """Verify IG fail-closed behavior on errors."""
    
    @pytest.mark.asyncio
    async def test_malformed_json_skipped_gracefully(
        self,
        ig_node,
        temp_audit_log,
        mock_scram_controller
    ):
        """
        Malformed JSON entries should be skipped without crashing IG.
        
        Test Flow:
            1. Write malformed JSON line
            2. Write valid REJECTED entry
            3. IG scans log
            4. SCRAM triggered for valid entry, malformed line ignored
        """
        # Write malformed JSON
        with open(temp_audit_log, 'w') as f:
            f.write("{this is not valid json}\n")
            f.write(json.dumps({
                "manifest_id": "MANIFEST-VALID",
                "timestamp": datetime.utcnow().isoformat(),
                "agent_gid": "GID-04",
                "git_commit_hash": "v" * 40,
                "judgment": "Rejected",
                "reason": "Test",
                "audit_log": {}
            }) + '\n')
        
        # Should not crash
        await ig_node._scan_log()
        
        # SCRAM should still be triggered for valid entry
        assert mock_scram_controller.emergency_halt.call_count == 1
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(5)
    async def test_monitoring_stops_when_scram_triggered(
        self,
        ig_node,
        temp_audit_log,
        mock_scram_controller
    ):
        """
        IG monitoring should stop when SCRAM status is not OPERATIONAL.
        
        Test Flow:
            1. Start monitoring in background
            2. Change SCRAM status to HALTED
            3. Monitoring loop should exit within timeout
        """
        # Start monitoring in background
        monitor_task = asyncio.create_task(ig_node.start_monitoring())
        
        # Wait for monitoring to start
        await asyncio.sleep(0.1)
        
        # Trigger SCRAM status change
        mock_scram_controller.status = "HALTED"
        
        # Monitoring should exit (will raise TimeoutError if it doesn't)
        await asyncio.wait_for(monitor_task, timeout=3.0)


# ============================================================================
# STATUS REPORTING
# ============================================================================

class TestStatusReporting:
    """Verify IG status reporting for health checks."""
    
    def test_get_status_returns_correct_info(
        self,
        ig_node,
        temp_audit_log,
        mock_scram_controller
    ):
        """
        get_status() should return accurate IG state information.
        """
        status = ig_node.get_status()
        
        assert "monitoring" in status
        assert "log_path" in status
        assert "processed_count" in status
        assert "scram_status" in status
        assert "last_scan_position" in status
        
        assert status["monitoring"] is False  # Not started yet
        assert status["log_path"] == str(temp_audit_log)
        assert status["scram_status"] == "OPERATIONAL"
        assert status["processed_count"] == 0
        assert status["last_scan_position"] == 0


# ============================================================================
# SINGLETON PATTERN
# ============================================================================

class TestSingletonPattern:
    """Verify InspectorGeneral singleton behavior."""
    
    def test_get_inspector_general_returns_singleton(self):
        """
        get_inspector_general() should return the same instance each time.
        """
        # Clear singleton for test
        import core.governance.inspector_general as ig_module
        ig_module._inspector_general_instance = None
        
        ig1 = get_inspector_general()
        ig2 = get_inspector_general()
        
        assert ig1 is ig2, "get_inspector_general() should return singleton"
    
    @pytest.mark.asyncio
    async def test_start_inspector_general_monitoring_convenience(self):
        """
        start_inspector_general_monitoring() should create IG and start monitoring.
        """
        # Clear singleton
        import core.governance.inspector_general as ig_module
        ig_module._inspector_general_instance = None
        
        with patch('core.governance.inspector_general.get_scram_controller') as mock_get_scram:
            mock_scram = MagicMock()
            mock_scram.status = "HALTED"  # Prevent infinite loop
            mock_get_scram.return_value = mock_scram
            
            ig = await start_inspector_general_monitoring()
            
            assert ig is not None
            assert isinstance(ig, InspectorGeneral)
            
            # Stop monitoring
            await ig.stop()
