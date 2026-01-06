"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                      CHAINAUDIT — TEST SUITE                                  ║
║                      PAC-OCC-P30 — Verification                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Tests for the ChainAudit persistence layer.

Run with: pytest tests/audit/test_audit.py -v
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.audit.models import AuditLog, PACAudit, AgentSpawnAudit, Base
from src.core.audit.recorder import AuditRecorder, compute_integrity_hash


class TestIntegrityHash(unittest.TestCase):
    """Test integrity hashing functionality."""
    
    def test_hash_string(self):
        """Test hashing a simple string."""
        hash1 = compute_integrity_hash("test payload")
        hash2 = compute_integrity_hash("test payload")
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA256 hex length
    
    def test_hash_dict(self):
        """Test hashing a dictionary."""
        payload = {"action": "test", "value": 123}
        hash1 = compute_integrity_hash(payload)
        hash2 = compute_integrity_hash(payload)
        self.assertEqual(hash1, hash2)
    
    def test_hash_none(self):
        """Test hashing None."""
        hash_none = compute_integrity_hash(None)
        self.assertEqual(len(hash_none), 64)


class TestAuditRecorder(unittest.TestCase):
    """Test the AuditRecorder class."""
    
    def setUp(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_audit.db")
        self.recorder = AuditRecorder(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up temporary database."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_log_action_basic(self):
        """Test basic action logging."""
        record = self.recorder.log_action(
            agent_gid="GID-00",
            action="TEST_ACTION",
            status="SUCCESS"
        )
        
        self.assertIsNotNone(record)
        self.assertEqual(record.agent_gid, "GID-00")
        self.assertEqual(record.action, "TEST_ACTION")
        self.assertEqual(record.status, "SUCCESS")
    
    def test_log_action_with_payload(self):
        """Test action logging with payload."""
        payload = {"detail": "test", "count": 42}
        record = self.recorder.log_action(
            agent_gid="GID-01",
            action="TEST_PAYLOAD",
            payload=payload
        )
        
        self.assertIsNotNone(record.payload)
        self.assertIsNotNone(record.integrity_hash)
    
    def test_log_action_with_target(self):
        """Test action logging with target."""
        record = self.recorder.log_action(
            agent_gid="GID-11",
            action="FIX_FILE",
            target="src/core/tools.py",
            status="SUCCESS"
        )
        
        self.assertEqual(record.target, "src/core/tools.py")
    
    def test_verify_integrity(self):
        """Test integrity verification."""
        record = self.recorder.log_action(
            agent_gid="GID-06",
            action="SECURITY_CHECK",
            payload={"verified": True}
        )
        
        # Integrity should pass
        self.assertTrue(self.recorder.verify_integrity(record.id))
    
    def test_log_pac_lifecycle(self):
        """Test PAC start and completion logging."""
        # Start PAC
        pac_record = self.recorder.log_pac_start(
            pac_id="PAC-TEST-001",
            issuer_gid="GID-JEFFREY",
            executor_gid="GID-00",
            title="Test PAC",
            scope="tests/"
        )
        
        self.assertEqual(pac_record.status, "IN_PROGRESS")
        
        # Complete PAC
        completed = self.recorder.log_pac_complete(
            pac_id="PAC-TEST-001",
            verdict="ACCEPTED",
            notes="Test passed"
        )
        
        self.assertEqual(completed.status, "COMPLETED")
        self.assertEqual(completed.ber_verdict, "ACCEPTED")
    
    def test_log_agent_spawn(self):
        """Test agent spawn logging."""
        record = self.recorder.log_agent_spawn(
            requester_gid="GID-00",
            target_gid="GID-11",
            status="SUCCESS",
            task_summary="Fix lint errors",
            execution_time_ms=1500
        )
        
        self.assertEqual(record.target_gid, "GID-11")
        self.assertEqual(record.status, "SUCCESS")
    
    def test_log_agent_spawn_blocked(self):
        """Test blocked agent spawn logging."""
        record = self.recorder.log_agent_spawn(
            requester_gid="GID-00",
            target_gid="GID-11",
            status="BLOCKED",
            task_summary="Attempted spawn",
            block_reason="KILL_SWITCH_ACTIVE"
        )
        
        self.assertEqual(record.status, "BLOCKED")
        self.assertEqual(record.block_reason, "KILL_SWITCH_ACTIVE")
    
    def test_get_recent_logs(self):
        """Test retrieving recent logs."""
        # Create some logs
        for i in range(5):
            self.recorder.log_action(
                agent_gid=f"GID-{i:02d}",
                action=f"ACTION_{i}"
            )
        
        logs = self.recorder.get_recent_logs(limit=3)
        self.assertEqual(len(logs), 3)
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        # Create some records
        self.recorder.log_action(agent_gid="GID-00", action="TEST")
        self.recorder.log_pac_start(
            pac_id="PAC-TEST",
            issuer_gid="GID-JEFFREY",
            executor_gid="GID-00"
        )
        self.recorder.log_agent_spawn(
            requester_gid="GID-00",
            target_gid="GID-11",
            status="SUCCESS"
        )
        
        stats = self.recorder.get_stats()
        self.assertEqual(stats["total_audit_logs"], 1)
        self.assertEqual(stats["total_pac_executions"], 1)
        self.assertEqual(stats["total_agent_spawns"], 1)


class TestAuditModels(unittest.TestCase):
    """Test audit model methods."""
    
    def test_audit_log_to_dict(self):
        """Test AuditLog.to_dict() serialization."""
        from datetime import datetime, timezone
        
        log = AuditLog(
            id=1,
            timestamp=datetime.now(timezone.utc),
            agent_gid="GID-00",
            action="TEST",
            status="SUCCESS"
        )
        
        d = log.to_dict()
        self.assertEqual(d["agent_gid"], "GID-00")
        self.assertEqual(d["action"], "TEST")
    
    def test_audit_log_repr(self):
        """Test AuditLog string representation."""
        log = AuditLog(
            id=1,
            agent_gid="GID-00",
            action="TEST",
            status="SUCCESS"
        )
        
        repr_str = repr(log)
        self.assertIn("GID-00", repr_str)
        self.assertIn("TEST", repr_str)


if __name__ == "__main__":
    print("📼 [ChainAudit] Running Test Suite...")
    print()
    unittest.main(verbosity=2)
