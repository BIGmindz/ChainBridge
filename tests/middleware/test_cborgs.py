"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                   C-BORGS ADAPTER — TEST SUITE                                ║
║                   PAC-OCC-P33 — Verification                                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Tests for the C-Borgs Middleware Adapter.

Run with: pytest tests/middleware/test_cborgs.py -v
"""

import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.middleware.cborgs_adapter import (
    CBorgsAdapter,
    CBorgsPayload,
    DispatchResult,
    DispatchStatus,
    OutcomeType,
    ALEXGovernance,
    SENSITIVE_PATTERNS,
)


class TestCBorgsPayload(unittest.TestCase):
    """Test CBorgsPayload data class."""
    
    def test_payload_creation(self):
        """Test basic payload creation."""
        payload = CBorgsPayload(
            event_id="CB-TEST-001",
            event_type="pac_completed",
            timestamp="2026-01-06T12:00:00Z",
        )
        
        self.assertEqual(payload.event_id, "CB-TEST-001")
        self.assertEqual(payload.event_type, "pac_completed")
        self.assertEqual(payload.source, "chainbridge")
        self.assertEqual(payload.version, "1.0.0")
    
    def test_payload_to_dict(self):
        """Test payload serialization to dict."""
        payload = CBorgsPayload(
            event_id="CB-TEST-002",
            event_type="agent_spawned",
            timestamp="2026-01-06T12:00:00Z",
            pac_id="PAC-TEST",
            agent_gid="GID-11",
        )
        
        data = payload.to_dict()
        
        self.assertEqual(data["event_id"], "CB-TEST-002")
        self.assertEqual(data["pac_id"], "PAC-TEST")
        self.assertNotIn("error", data)  # None values excluded
    
    def test_payload_to_json(self):
        """Test payload serialization to JSON."""
        payload = CBorgsPayload(
            event_id="CB-TEST-003",
            event_type="alert",
            timestamp="2026-01-06T12:00:00Z",
        )
        
        json_str = payload.to_json()
        
        self.assertIn('"event_id"', json_str)
        self.assertIn("CB-TEST-003", json_str)


class TestALEXGovernance(unittest.TestCase):
    """Test ALEX governance review."""
    
    def setUp(self):
        """Create governance instance."""
        self.alex = ALEXGovernance()
    
    def test_alex_identity(self):
        """Test ALEX identity."""
        self.assertEqual(self.alex.gid, "GID-08")
        self.assertEqual(self.alex.name, "ALEX")
        self.assertEqual(self.alex.role, "Governance Enforcer")
    
    def test_approve_clean_payload(self):
        """Test approval of clean payload."""
        payload = CBorgsPayload(
            event_id="CB-CLEAN-001",
            event_type="pac_completed",
            timestamp="2026-01-06T12:00:00Z",
            pac_id="PAC-TEST",
            status="SUCCESS",
        )
        
        approved, reason = self.alex.review_payload(payload)
        
        self.assertTrue(approved)
        self.assertIsNone(reason)
    
    def test_block_missing_event_id(self):
        """Test blocking payload without event_id."""
        payload = CBorgsPayload(
            event_id="",  # Empty
            event_type="alert",
            timestamp="2026-01-06T12:00:00Z",
        )
        
        approved, reason = self.alex.review_payload(payload)
        
        self.assertFalse(approved)
        self.assertIn("event_id", reason)
    
    def test_block_missing_event_type(self):
        """Test blocking payload without event_type."""
        payload = CBorgsPayload(
            event_id="CB-TEST",
            event_type="",  # Empty
            timestamp="2026-01-06T12:00:00Z",
        )
        
        approved, reason = self.alex.review_payload(payload)
        
        self.assertFalse(approved)
        self.assertIn("event_type", reason)
    
    @patch.dict(os.environ, {"CBORGS_GOVERNANCE_STRICT": "true"})
    def test_block_sensitive_password(self):
        """Test blocking payload with password."""
        # Re-import to pick up env var
        payload = CBorgsPayload(
            event_id="CB-SENSITIVE-001",
            event_type="alert",
            timestamp="2026-01-06T12:00:00Z",
            details={"user_password": "secret123"},
        )
        
        alex = ALEXGovernance()
        approved, reason = alex.review_payload(payload)
        
        self.assertFalse(approved)
        self.assertIn("ALEX BLOCKED", reason)
        self.assertIn("password", reason.lower())
    
    def test_governance_stats(self):
        """Test governance statistics."""
        payload = CBorgsPayload(
            event_id="CB-STATS-001",
            event_type="test",
            timestamp="2026-01-06T12:00:00Z",
        )
        
        self.alex.review_payload(payload)
        self.alex.review_payload(payload)
        
        stats = self.alex.get_stats()
        
        self.assertEqual(stats["total_reviews"], 2)


class TestCBorgsAdapter(unittest.TestCase):
    """Test CBorgsAdapter class."""
    
    def setUp(self):
        """Create adapter instance (disabled by default)."""
        self.adapter = CBorgsAdapter(
            webhook_url="https://test.seaburgers.biz/webhook",
            api_key="test-key-123",
            enabled=False,  # Disabled for testing
        )
    
    def test_adapter_creation(self):
        """Test adapter initialization."""
        self.assertFalse(self.adapter.is_enabled)
        self.assertEqual(self.adapter.webhook_url, "https://test.seaburgers.biz/webhook")
        self.assertEqual(self.adapter.api_key, "test-key-123")
    
    def test_event_id_generation(self):
        """Test unique event ID generation."""
        id1 = self.adapter._generate_event_id()
        id2 = self.adapter._generate_event_id()
        
        self.assertTrue(id1.startswith("CB-"))
        self.assertTrue(id2.startswith("CB-"))
        self.assertNotEqual(id1, id2)
    
    def test_hash_computation(self):
        """Test integrity hash computation."""
        hash1 = self.adapter._compute_hash("test data")
        hash2 = self.adapter._compute_hash("test data")
        hash3 = self.adapter._compute_hash("different data")
        
        self.assertEqual(len(hash1), 64)  # SHA256 hex
        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
    
    def test_dispatch_disabled(self):
        """Test dispatch when adapter is disabled."""
        result = self.adapter.dispatch_outcome(
            event_type=OutcomeType.PAC_COMPLETED,
            pac_id="PAC-TEST",
            status="SUCCESS",
        )
        
        self.assertEqual(result.status, DispatchStatus.PENDING)
        self.assertIn("disabled", result.error.lower())
    
    def test_dispatch_governance_block(self):
        """Test dispatch blocked by governance."""
        result = self.adapter.dispatch_outcome(
            event_type=OutcomeType.ALERT,
            details={"api_key": "should-be-blocked"},
        )
        
        self.assertEqual(result.status, DispatchStatus.BLOCKED_GOVERNANCE)
    
    def test_dispatch_pac_completed_convenience(self):
        """Test PAC completed convenience method."""
        result = self.adapter.dispatch_pac_completed(
            pac_id="PAC-OCC-P33",
            executor_gid="GID-00",
            verdict="ACCEPTED",
            notes="Test notes",
        )
        
        # Should be PENDING (adapter disabled)
        self.assertEqual(result.status, DispatchStatus.PENDING)
    
    def test_dispatch_agent_spawned_convenience(self):
        """Test agent spawned convenience method."""
        result = self.adapter.dispatch_agent_spawned(
            requester_gid="GID-00",
            target_gid="GID-11",
            task_summary="Test task",
        )
        
        self.assertEqual(result.status, DispatchStatus.PENDING)
    
    def test_dispatch_alert_convenience(self):
        """Test alert convenience method."""
        result = self.adapter.dispatch_alert(
            alert_type="test",
            message="Test alert message",
            severity="INFO",
        )
        
        self.assertEqual(result.status, DispatchStatus.PENDING)
    
    def test_adapter_stats(self):
        """Test adapter statistics."""
        # Make some dispatches
        self.adapter.dispatch_outcome(
            event_type=OutcomeType.AUDIT_EVENT,
            status="SUCCESS",
        )
        self.adapter.dispatch_outcome(
            event_type=OutcomeType.ALERT,
            details={"password": "blocked"},
        )
        
        stats = self.adapter.get_stats()
        
        self.assertIn("dispatches", stats)
        self.assertIn("governance", stats)
        self.assertEqual(stats["dispatches"]["total"], 2)
        self.assertEqual(stats["dispatches"]["blocked"], 1)


class TestCBorgsAdapterEnabled(unittest.TestCase):
    """Test CBorgsAdapter with mocked HTTP calls."""
    
    def setUp(self):
        """Create enabled adapter with mock."""
        self.adapter = CBorgsAdapter(
            webhook_url="https://test.seaburgers.biz/webhook",
            api_key="test-key",
            enabled=True,
            timeout=1,
        )
    
    @patch('src.core.middleware.cborgs_adapter.urlopen')
    def test_dispatch_success(self, mock_urlopen):
        """Test successful HTTP dispatch."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        result = self.adapter.dispatch_outcome(
            event_type=OutcomeType.PAC_COMPLETED,
            pac_id="PAC-TEST",
            status="SUCCESS",
            blocking=True,  # Wait for result
        )
        
        self.assertEqual(result.status, DispatchStatus.DELIVERED)
        self.assertEqual(result.response_code, 200)
    
    @patch('src.core.middleware.cborgs_adapter.urlopen')
    def test_dispatch_http_error(self, mock_urlopen):
        """Test HTTP error handling."""
        from urllib.error import HTTPError
        
        mock_urlopen.side_effect = HTTPError(
            url="https://test.seaburgers.biz/webhook",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )
        
        result = self.adapter.dispatch_outcome(
            event_type=OutcomeType.ALERT,
            status="ERROR",
            blocking=True,
        )
        
        self.assertEqual(result.status, DispatchStatus.FAILED)
        self.assertEqual(result.response_code, 500)
    
    @patch('src.core.middleware.cborgs_adapter.urlopen')
    def test_dispatch_non_blocking(self, mock_urlopen):
        """Test non-blocking dispatch (daemon thread)."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        result = self.adapter.dispatch_outcome(
            event_type=OutcomeType.PAC_COMPLETED,
            pac_id="PAC-ASYNC",
            blocking=False,  # Non-blocking
        )
        
        # Should return DISPATCHED immediately
        self.assertEqual(result.status, DispatchStatus.DISPATCHED)
        
        # Wait for daemon thread
        time.sleep(0.2)
        
        # HTTP call should have been made
        mock_urlopen.assert_called_once()


class TestOutcomeTypes(unittest.TestCase):
    """Test outcome type enum."""
    
    def test_outcome_types_exist(self):
        """Test all outcome types are defined."""
        self.assertEqual(OutcomeType.PAC_COMPLETED.value, "pac_completed")
        self.assertEqual(OutcomeType.AGENT_SPAWNED.value, "agent_spawned")
        self.assertEqual(OutcomeType.GOVERNANCE_DECISION.value, "governance_decision")
        self.assertEqual(OutcomeType.SETTLEMENT_REQUEST.value, "settlement_request")
        self.assertEqual(OutcomeType.ALERT.value, "alert")
        self.assertEqual(OutcomeType.AUDIT_EVENT.value, "audit_event")


class TestDispatchStatus(unittest.TestCase):
    """Test dispatch status enum."""
    
    def test_dispatch_statuses_exist(self):
        """Test all dispatch statuses are defined."""
        self.assertEqual(DispatchStatus.PENDING.value, "pending")
        self.assertEqual(DispatchStatus.DISPATCHED.value, "dispatched")
        self.assertEqual(DispatchStatus.DELIVERED.value, "delivered")
        self.assertEqual(DispatchStatus.FAILED.value, "failed")
        self.assertEqual(DispatchStatus.BLOCKED_GOVERNANCE.value, "blocked_governance")


if __name__ == "__main__":
    unittest.main()
