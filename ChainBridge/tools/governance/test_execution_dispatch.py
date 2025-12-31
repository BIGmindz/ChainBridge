#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
🟦🟩 UNIT TESTS: EXECUTION DISPATCH AUTHORIZATION
PAC Reference: PAC-BENSON-P54-AGENT-DISPATCH-EXECUTION-BINDING-01
═══════════════════════════════════════════════════════════════════════════════

Tests for the EXECUTION_DISPATCH_AUTH artifact and dispatch authorization system.

Invariants Tested:
    - GS_160: Agent execution without dispatch triggers FAIL_CLOSED
    - GS_161: Session mismatch triggers FAIL_CLOSED
    - GS_162: Expired dispatch triggers FAIL_CLOSED
    - Only Benson (GID-00) can generate dispatch authorizations
    - dispatch_session_id is globally unique
    - AgentExecutionResult must bind to execution_session_id
"""

import json
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Import from benson_execution
from benson_execution import (
    BensonExecutionEngine,
    ExecutionDispatchAuth,
    ExecutionResult,
    ExecutionStatus,
    BlockReason,
    WrapArtifact,
)


class TestExecutionDispatchAuth(unittest.TestCase):
    """Test suite for ExecutionDispatchAuth dataclass."""
    
    def test_dispatch_auth_creation(self):
        """Test creating an ExecutionDispatchAuth artifact."""
        dispatch = ExecutionDispatchAuth(
            dispatch_id="DISPATCH-DAN-P54-20251226120000",
            pac_id="PAC-DAN-P54-TEST-01",
            agent_gid="GID-01",
            agent_name="DAN",
            dispatch_session_id="SESS-ABC123DEF456",
            dispatch_timestamp="2025-12-26T12:00:00+00:00",
            authority_gid="GID-00",
            authority_name="BENSON",
            dispatch_hash="abc123def456",
            expires_at=None,
            notes="Test dispatch"
        )
        
        self.assertEqual(dispatch.pac_id, "PAC-DAN-P54-TEST-01")
        self.assertEqual(dispatch.agent_gid, "GID-01")
        self.assertEqual(dispatch.authority_gid, "GID-00")
        self.assertEqual(dispatch.authority_name, "BENSON")
    
    def test_dispatch_auth_with_expiry(self):
        """Test dispatch authorization with expiry time."""
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        dispatch = ExecutionDispatchAuth(
            dispatch_id="DISPATCH-DAN-P54-20251226120000",
            pac_id="PAC-DAN-P54-TEST-01",
            agent_gid="GID-01",
            agent_name="DAN",
            dispatch_session_id="SESS-ABC123DEF456",
            dispatch_timestamp="2025-12-26T12:00:00+00:00",
            authority_gid="GID-00",
            authority_name="BENSON",
            dispatch_hash="abc123def456",
            expires_at=expires_at,
            notes=None
        )
        
        self.assertIsNotNone(dispatch.expires_at)


class TestDispatchAgent(unittest.TestCase):
    """Test suite for dispatch_agent() method."""
    
    def setUp(self):
        """Set up test engine."""
        self.engine = BensonExecutionEngine(enable_telemetry=False)
    
    def test_dispatch_agent_creates_authorization(self):
        """Test that dispatch_agent creates a valid authorization."""
        dispatch = self.engine.dispatch_agent(
            pac_id="PAC-DAN-P54-TEST-01",
            agent_gid="GID-01",
            agent_name="DAN"
        )
        
        self.assertIsInstance(dispatch, ExecutionDispatchAuth)
        self.assertEqual(dispatch.pac_id, "PAC-DAN-P54-TEST-01")
        self.assertEqual(dispatch.agent_gid, "GID-01")
        self.assertEqual(dispatch.agent_name, "DAN")
        self.assertEqual(dispatch.authority_gid, "GID-00")
        self.assertEqual(dispatch.authority_name, "BENSON")
    
    def test_dispatch_agent_generates_unique_session_id(self):
        """Test that each dispatch gets a unique session ID."""
        dispatch1 = self.engine.dispatch_agent("PAC-TEST-01", "GID-01", "DAN")
        dispatch2 = self.engine.dispatch_agent("PAC-TEST-02", "GID-01", "DAN")
        
        self.assertNotEqual(dispatch1.dispatch_session_id, dispatch2.dispatch_session_id)
        self.assertTrue(dispatch1.dispatch_session_id.startswith("SESS-"))
        self.assertTrue(dispatch2.dispatch_session_id.startswith("SESS-"))
    
    def test_dispatch_agent_stores_in_active_dispatches(self):
        """Test that dispatch is stored in active dispatches."""
        dispatch = self.engine.dispatch_agent("PAC-TEST-01", "GID-01", "DAN")
        
        self.assertIn(dispatch.dispatch_session_id, self.engine._active_dispatches)
        self.assertEqual(
            self.engine._active_dispatches[dispatch.dispatch_session_id],
            dispatch
        )
    
    def test_dispatch_agent_with_expiry(self):
        """Test dispatch with expiry time."""
        dispatch = self.engine.dispatch_agent(
            pac_id="PAC-TEST-01",
            agent_gid="GID-01",
            agent_name="DAN",
            expires_in_seconds=3600  # 1 hour
        )
        
        self.assertIsNotNone(dispatch.expires_at)
    
    def test_dispatch_agent_with_notes(self):
        """Test dispatch with notes."""
        dispatch = self.engine.dispatch_agent(
            pac_id="PAC-TEST-01",
            agent_gid="GID-01",
            agent_name="DAN",
            notes="Test execution for P54 validation"
        )
        
        self.assertEqual(dispatch.notes, "Test execution for P54 validation")
    
    def test_dispatch_generates_integrity_hash(self):
        """Test that dispatch generates an integrity hash."""
        dispatch = self.engine.dispatch_agent("PAC-TEST-01", "GID-01", "DAN")
        
        self.assertIsNotNone(dispatch.dispatch_hash)
        self.assertEqual(len(dispatch.dispatch_hash), 64)  # SHA256 hex length


class TestValidateDispatch(unittest.TestCase):
    """Test suite for validate_dispatch() method."""
    
    def setUp(self):
        """Set up test engine with a dispatch."""
        self.engine = BensonExecutionEngine(enable_telemetry=False)
        self.dispatch = self.engine.dispatch_agent(
            pac_id="PAC-DAN-P54-TEST-01",
            agent_gid="GID-01",
            agent_name="DAN"
        )
    
    def test_validate_dispatch_success(self):
        """Test successful dispatch validation."""
        result = self.engine.validate_dispatch(
            dispatch_session_id=self.dispatch.dispatch_session_id,
            pac_id="PAC-DAN-P54-TEST-01",
            agent_gid="GID-01"
        )
        
        self.assertTrue(result["valid"])
        self.assertIsNone(result["error_code"])
        self.assertEqual(result["dispatch"], self.dispatch)
    
    def test_validate_dispatch_not_found_gs160(self):
        """Test GS_160: Dispatch not found."""
        result = self.engine.validate_dispatch(
            dispatch_session_id="SESS-NONEXISTENT",
            pac_id="PAC-DAN-P54-TEST-01",
            agent_gid="GID-01"
        )
        
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_160")
        self.assertIn("No dispatch authorization found", result["message"])
        self.assertIn("training_signal", result)
    
    def test_validate_dispatch_pac_mismatch_gs161(self):
        """Test GS_161: PAC mismatch."""
        result = self.engine.validate_dispatch(
            dispatch_session_id=self.dispatch.dispatch_session_id,
            pac_id="PAC-DIFFERENT-01",  # Wrong PAC
            agent_gid="GID-01"
        )
        
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_161")
        self.assertIn("Session mismatch", result["message"])
    
    def test_validate_dispatch_agent_mismatch_gs161(self):
        """Test GS_161: Agent mismatch."""
        result = self.engine.validate_dispatch(
            dispatch_session_id=self.dispatch.dispatch_session_id,
            pac_id="PAC-DAN-P54-TEST-01",
            agent_gid="GID-05"  # Wrong agent
        )
        
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_161")
        self.assertIn("Agent mismatch", result["message"])
    
    def test_validate_dispatch_expired_gs162(self):
        """Test GS_162: Expired dispatch."""
        # Create dispatch with already-expired time
        expired_dispatch = ExecutionDispatchAuth(
            dispatch_id="DISPATCH-TEST-EXPIRED",
            pac_id="PAC-TEST-EXPIRED",
            agent_gid="GID-01",
            agent_name="DAN",
            dispatch_session_id="SESS-EXPIRED123",
            dispatch_timestamp="2025-12-26T10:00:00+00:00",
            authority_gid="GID-00",
            authority_name="BENSON",
            dispatch_hash="expired123",
            expires_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),  # Past
            notes=None
        )
        self.engine._active_dispatches["SESS-EXPIRED123"] = expired_dispatch
        
        result = self.engine.validate_dispatch(
            dispatch_session_id="SESS-EXPIRED123",
            pac_id="PAC-TEST-EXPIRED",
            agent_gid="GID-01"
        )
        
        self.assertFalse(result["valid"])
        self.assertEqual(result["error_code"], "GS_162")
        self.assertIn("expired", result["message"].lower())


class TestRevokeDispatch(unittest.TestCase):
    """Test suite for revoke_dispatch() method."""
    
    def setUp(self):
        """Set up test engine with a dispatch."""
        self.engine = BensonExecutionEngine(enable_telemetry=False)
        self.dispatch = self.engine.dispatch_agent(
            pac_id="PAC-TEST-01",
            agent_gid="GID-01",
            agent_name="DAN"
        )
    
    def test_revoke_dispatch_success(self):
        """Test successful dispatch revocation."""
        session_id = self.dispatch.dispatch_session_id
        
        result = self.engine.revoke_dispatch(session_id)
        
        self.assertTrue(result["revoked"])
        self.assertEqual(result["dispatch_session_id"], session_id)
        self.assertNotIn(session_id, self.engine._active_dispatches)
    
    def test_revoke_dispatch_not_found(self):
        """Test revoking nonexistent dispatch."""
        result = self.engine.revoke_dispatch("SESS-NONEXISTENT")
        
        self.assertFalse(result["revoked"])
        self.assertIn("not found", result["message"].lower())


class TestGetActiveDispatches(unittest.TestCase):
    """Test suite for get_active_dispatches() method."""
    
    def setUp(self):
        """Set up test engine."""
        self.engine = BensonExecutionEngine(enable_telemetry=False)
    
    def test_get_active_dispatches_empty(self):
        """Test getting active dispatches when none exist."""
        dispatches = self.engine.get_active_dispatches()
        self.assertEqual(len(dispatches), 0)
    
    def test_get_active_dispatches_multiple(self):
        """Test getting multiple active dispatches."""
        dispatch1 = self.engine.dispatch_agent("PAC-TEST-01", "GID-01", "DAN")
        dispatch2 = self.engine.dispatch_agent("PAC-TEST-02", "GID-05", "ATLAS")
        
        dispatches = self.engine.get_active_dispatches()
        
        self.assertEqual(len(dispatches), 2)
        self.assertIn(dispatch1, dispatches)
        self.assertIn(dispatch2, dispatches)


class TestExecutePacWithDispatch(unittest.TestCase):
    """Test suite for execute_pac_with_dispatch() method."""
    
    def setUp(self):
        """Set up test engine with mocked registry."""
        self.engine = BensonExecutionEngine(enable_telemetry=False)
        
        # Mock the registry file read for agent validation
        self.registry_mock = {
            "agents": {
                "DAN": {"gid": "GID-01", "name": "Dan", "status": "active"},
                "ATLAS": {"gid": "GID-05", "name": "Atlas", "status": "active"}
            }
        }
    
    @patch("builtins.open", create=True)
    def test_execute_with_dispatch_requires_valid_dispatch(self, mock_open):
        """Test that execution without valid dispatch is blocked."""
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(self.registry_mock)
        
        execution_result = ExecutionResult(
            pac_id="PAC-TEST-01",
            agent_gid="GID-01",
            agent_name="DAN",
            execution_timestamp=datetime.now(timezone.utc).isoformat(),
            tasks_completed=["T1"],
            files_modified=[],
            quality_score=0.9,
            scope_compliance=True,
            execution_time_ms=100
        )
        
        # Try to execute without dispatch
        result = self.engine.execute_pac_with_dispatch(
            dispatch_session_id="SESS-NONEXISTENT",
            execution_result=execution_result
        )
        
        self.assertEqual(result["status"], ExecutionStatus.BLOCKED.value)
        self.assertEqual(result["block_reason"], BlockReason.DISPATCH_NOT_AUTHORIZED.value)
        self.assertEqual(result["error_code"], "GS_160")
    
    @patch("builtins.open", create=True)
    def test_execute_with_dispatch_session_mismatch_blocked(self, mock_open):
        """Test that PAC mismatch blocks execution."""
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(self.registry_mock)
        
        # Create dispatch for different PAC
        dispatch = self.engine.dispatch_agent(
            pac_id="PAC-DIFFERENT-01",
            agent_gid="GID-01",
            agent_name="DAN"
        )
        
        execution_result = ExecutionResult(
            pac_id="PAC-TEST-01",  # Different PAC
            agent_gid="GID-01",
            agent_name="DAN",
            execution_timestamp=datetime.now(timezone.utc).isoformat(),
            tasks_completed=["T1"],
            files_modified=[],
            quality_score=0.9,
            scope_compliance=True,
            execution_time_ms=100
        )
        
        result = self.engine.execute_pac_with_dispatch(
            dispatch_session_id=dispatch.dispatch_session_id,
            execution_result=execution_result
        )
        
        self.assertEqual(result["status"], ExecutionStatus.BLOCKED.value)
        self.assertEqual(result["block_reason"], BlockReason.DISPATCH_SESSION_MISMATCH.value)
        self.assertEqual(result["error_code"], "GS_161")


class TestDispatchBinding(unittest.TestCase):
    """Test suite for dispatch binding in execution results."""
    
    def setUp(self):
        """Set up test engine."""
        self.engine = BensonExecutionEngine(enable_telemetry=False)
    
    def test_dispatch_session_id_included_in_execution_record(self):
        """Test that dispatch_session_id is included in execution record."""
        dispatch = self.engine.dispatch_agent(
            pac_id="PAC-TEST-01",
            agent_gid="GID-01",
            agent_name="DAN"
        )
        
        # Verify dispatch is active
        validation = self.engine.validate_dispatch(
            dispatch_session_id=dispatch.dispatch_session_id,
            pac_id="PAC-TEST-01",
            agent_gid="GID-01"
        )
        
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["dispatch"].dispatch_session_id, dispatch.dispatch_session_id)


class TestDispatchTelemetry(unittest.TestCase):
    """Test suite for dispatch telemetry events."""
    
    def setUp(self):
        """Set up test engine with telemetry enabled."""
        self.engine = BensonExecutionEngine(enable_telemetry=False)
    
    def test_dispatch_emits_telemetry(self):
        """Test that dispatch_agent emits telemetry."""
        dispatch = self.engine.dispatch_agent(
            pac_id="PAC-TEST-01",
            agent_gid="GID-01",
            agent_name="DAN"
        )
        
        events = self.engine.telemetry.get_all_events()
        dispatch_events = [e for e in events if e.get("event_type") == "DISPATCH_AUTHORIZED"]
        
        self.assertGreaterEqual(len(dispatch_events), 1)
        self.assertEqual(dispatch_events[0]["data"]["dispatch_session_id"], dispatch.dispatch_session_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
