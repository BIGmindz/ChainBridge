# ═══════════════════════════════════════════════════════════════════════════════
# ChainBridge Agent Execution Tests
# PAC-008: Agent Execution Visibility
# ═══════════════════════════════════════════════════════════════════════════════

"""
Tests for agent execution visibility module.

GOVERNANCE INVARIANTS TESTED:
- INV-AGENT-001: Agent activation must be explicit and visible
- INV-AGENT-002: Each execution step maps to exactly one agent
- INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
- INV-AGENT-004: OC is read-only; no agent control actions
- INV-AGENT-005: Missing state must be explicit (no inference)
"""

import pytest
from datetime import datetime, timezone

from core.execution.agent_events import (
    AgentState,
    AgentExecutionMode,
    AgentActivationEvent,
    AgentExecutionStateEvent,
    UNAVAILABLE_MARKER,
    emit_agent_activation,
    emit_agent_state_change,
    get_activation_events,
    get_state_events,
    get_current_agent_state,
    clear_events,
)
from core.execution.execution_ledger import (
    ExecutionEntryType,
    ExecutionLedger,
    ExecutionLedgerEntry,
    get_execution_ledger,
    reset_execution_ledger,
    GENESIS_HASH,
)
from core.execution.agent_aggregator import (
    OCAgentExecutionView,
    OCAgentTimelineEvent,
    OCPACExecutionView,
    AgentExecutionAggregator,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def clean_events():
    """Clear events before and after each test."""
    clear_events()
    reset_execution_ledger()
    yield
    clear_events()
    reset_execution_ledger()


# ═══════════════════════════════════════════════════════════════════════════════
# INV-AGENT-001: Agent activation must be explicit and visible
# ═══════════════════════════════════════════════════════════════════════════════

class TestINVAGENT001_AgentActivationExplicit:
    """
    INV-AGENT-001: Agent activation must be explicit and visible.
    """
    
    def test_activation_event_has_required_fields(self):
        """Activation events must have all required fields."""
        event = emit_agent_activation(
            agent_gid="GID-01",
            agent_name="Cody",
            pac_id="PAC-TEST-001",
            execution_mode=AgentExecutionMode.EXECUTION,
            agent_role="Backend",
            agent_color="BLUE",
            execution_order=1,
            order_description="Test order",
        )
        
        assert event.agent_gid == "GID-01"
        assert event.agent_name == "Cody"
        assert event.pac_id == "PAC-TEST-001"
        assert event.execution_mode == "EXECUTION"
        assert event.permissions_accepted is True
        assert event.runtime_bound is True
        assert event.event_type == "AGENT_ACTIVATION"
    
    def test_activation_event_validation_fails_without_gid(self):
        """Activation without agent_gid must fail validation."""
        event = AgentActivationEvent(
            agent_gid=UNAVAILABLE_MARKER,
            agent_name="Test",
            pac_id="PAC-001",
        )
        
        assert event.validate() is False
    
    def test_activation_event_validation_fails_without_pac_id(self):
        """Activation without pac_id must fail validation."""
        event = AgentActivationEvent(
            agent_gid="GID-01",
            agent_name="Test",
            pac_id=UNAVAILABLE_MARKER,
        )
        
        assert event.validate() is False
    
    def test_activation_events_are_stored(self):
        """Activation events must be stored and retrievable."""
        emit_agent_activation(
            agent_gid="GID-01",
            agent_name="Cody",
            pac_id="PAC-TEST-001",
        )
        
        events = get_activation_events(pac_id="PAC-TEST-001")
        assert len(events) == 1
        assert events[0].agent_gid == "GID-01"


# ═══════════════════════════════════════════════════════════════════════════════
# INV-AGENT-002: Each execution step maps to exactly one agent
# ═══════════════════════════════════════════════════════════════════════════════

class TestINVAGENT002_OneAgentPerStep:
    """
    INV-AGENT-002: Each execution step maps to exactly one agent.
    """
    
    def test_state_event_requires_agent_gid(self):
        """State events must have agent_gid."""
        event = AgentExecutionStateEvent(
            agent_gid=UNAVAILABLE_MARKER,
            agent_name="Test",
            pac_id="PAC-001",
            new_state=AgentState.ACTIVE.value,
        )
        
        assert event.validate() is False
    
    def test_execution_order_is_captured(self):
        """Execution order must be captured in events."""
        event = emit_agent_activation(
            agent_gid="GID-01",
            agent_name="Cody",
            pac_id="PAC-001",
            execution_order=1,
            order_description="First step",
        )
        
        assert event.execution_order == 1
        assert event.order_description == "First step"


# ═══════════════════════════════════════════════════════════════════════════════
# INV-AGENT-003: Agent state ∈ {QUEUED, ACTIVE, COMPLETE, FAILED}
# ═══════════════════════════════════════════════════════════════════════════════

class TestINVAGENT003_ValidStates:
    """
    INV-AGENT-003: Agent state must be one of QUEUED, ACTIVE, COMPLETE, FAILED.
    """
    
    def test_all_valid_states(self):
        """All valid states must be accepted."""
        valid_states = [AgentState.QUEUED, AgentState.ACTIVE, AgentState.COMPLETE, AgentState.FAILED]
        
        for state in valid_states:
            event = emit_agent_state_change(
                agent_gid="GID-01",
                agent_name="Cody",
                pac_id="PAC-001",
                new_state=state,
            )
            assert event.validate() is True
    
    def test_invalid_state_fails_validation(self):
        """Invalid states must fail validation."""
        event = AgentExecutionStateEvent(
            agent_gid="GID-01",
            agent_name="Test",
            pac_id="PAC-001",
            new_state="INVALID_STATE",
        )
        
        assert event.validate() is False
    
    def test_state_enum_values(self):
        """State enum must have exactly the allowed values."""
        assert AgentState.QUEUED.value == "QUEUED"
        assert AgentState.ACTIVE.value == "ACTIVE"
        assert AgentState.COMPLETE.value == "COMPLETE"
        assert AgentState.FAILED.value == "FAILED"
        
        # Only 4 states allowed
        assert len(AgentState) == 4


# ═══════════════════════════════════════════════════════════════════════════════
# INV-AGENT-005: Missing state must be explicit (no inference)
# ═══════════════════════════════════════════════════════════════════════════════

class TestINVAGENT005_MissingStateExplicit:
    """
    INV-AGENT-005: Missing state must be explicit (no inference).
    """
    
    def test_unavailable_marker_used(self):
        """UNAVAILABLE marker must be used for missing data."""
        assert UNAVAILABLE_MARKER == "UNAVAILABLE"
    
    def test_default_values_use_unavailable_marker(self):
        """Default values must use UNAVAILABLE marker."""
        event = AgentActivationEvent(
            agent_gid="GID-01",
            agent_name="Test",
            pac_id="PAC-001",
        )
        
        assert event.agent_role == UNAVAILABLE_MARKER
        assert event.agent_color == UNAVAILABLE_MARKER
        assert event.order_description == UNAVAILABLE_MARKER
    
    def test_aggregator_view_uses_unavailable_marker(self):
        """Aggregator views must use UNAVAILABLE marker for missing data."""
        view = OCAgentExecutionView(
            agent_gid="GID-01",
            agent_name="Cody",
            agent_role=UNAVAILABLE_MARKER,
            agent_color=UNAVAILABLE_MARKER,
            current_state="QUEUED",
            pac_id="PAC-001",
            execution_mode="EXECUTION",
        )
        
        assert view.order_description == UNAVAILABLE_MARKER
        assert view.ledger_entry_hash == UNAVAILABLE_MARKER


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTION LEDGER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionLedger:
    """
    Tests for the execution ledger.
    """
    
    def test_ledger_append_only(self):
        """Ledger must be append-only."""
        ledger = ExecutionLedger()
        
        entry = ledger.append(
            entry_type=ExecutionEntryType.AGENT_ACTIVATION,
            payload={"agent_gid": "GID-01"},
            pac_id="PAC-001",
            agent_gid="GID-01",
        )
        
        assert len(ledger) == 1
        assert entry.sequence_number == 0
    
    def test_ledger_update_forbidden(self):
        """Ledger update must be forbidden."""
        ledger = ExecutionLedger()
        
        entry = ledger.append(
            entry_type=ExecutionEntryType.AGENT_ACTIVATION,
            payload={"agent_gid": "GID-01"},
            pac_id="PAC-001",
        )
        
        with pytest.raises(RuntimeError, match="UPDATE FORBIDDEN"):
            ledger.update(entry.entry_id, payload={})
    
    def test_ledger_delete_forbidden(self):
        """Ledger delete must be forbidden."""
        ledger = ExecutionLedger()
        
        entry = ledger.append(
            entry_type=ExecutionEntryType.AGENT_ACTIVATION,
            payload={"agent_gid": "GID-01"},
            pac_id="PAC-001",
        )
        
        with pytest.raises(RuntimeError, match="DELETE FORBIDDEN"):
            ledger.delete(entry.entry_id)
    
    def test_ledger_hash_chain_integrity(self):
        """Ledger must maintain hash chain integrity."""
        ledger = ExecutionLedger()
        
        # Append multiple entries
        for i in range(3):
            ledger.append(
                entry_type=ExecutionEntryType.AGENT_STATE_CHANGE,
                payload={"sequence": i},
                pac_id="PAC-001",
            )
        
        # Verify chain
        is_valid, error = ledger.verify_chain()
        assert is_valid is True
        assert error is None
    
    def test_ledger_genesis_hash(self):
        """First entry must have genesis hash as previous."""
        ledger = ExecutionLedger()
        
        entry = ledger.append(
            entry_type=ExecutionEntryType.AGENT_ACTIVATION,
            payload={},
            pac_id="PAC-001",
        )
        
        assert entry.previous_hash == GENESIS_HASH


# ═══════════════════════════════════════════════════════════════════════════════
# AGGREGATOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentExecutionAggregator:
    """
    Tests for agent execution aggregator.
    """
    
    def test_get_pac_execution_view(self):
        """Aggregator must return PAC execution view."""
        # Emit activation
        emit_agent_activation(
            agent_gid="GID-01",
            agent_name="Cody",
            pac_id="PAC-TEST",
            execution_order=1,
        )
        
        aggregator = AgentExecutionAggregator()
        view = aggregator.get_pac_execution_view("PAC-TEST")
        
        assert view.pac_id == "PAC-TEST"
        assert view.total_agents == 1
    
    def test_get_active_agents_empty(self):
        """Active agents list must be empty when no agents active."""
        aggregator = AgentExecutionAggregator()
        active = aggregator.get_active_agents()
        
        assert len(active) == 0
    
    def test_aggregator_timeline(self):
        """Aggregator must provide timeline view."""
        ledger = get_execution_ledger()
        
        # Add ledger entry
        event = emit_agent_activation(
            agent_gid="GID-01",
            agent_name="Cody",
            pac_id="PAC-TIMELINE",
            execution_order=1,
        )
        ledger.append_activation(event)
        
        aggregator = AgentExecutionAggregator(ledger)
        timeline = aggregator.get_agent_timeline("PAC-TIMELINE")
        
        assert len(timeline) == 1
        assert timeline[0].event_type == "ACTIVATION"


# ═══════════════════════════════════════════════════════════════════════════════
# API TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentOCAPI:
    """
    Tests for the Agent OC API.
    INV-AGENT-004: OC is read-only; no agent control actions.
    """
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from api.server import app
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Health endpoint must return read_only=true."""
        response = client.get("/oc/agents/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["read_only"] is True
    
    def test_post_blocked(self, client):
        """POST must be blocked (INV-AGENT-004)."""
        response = client.post("/oc/agents/test", json={})
        assert response.status_code == 405
        # Either from agent_oc or operator_console router
        assert response.status_code == 405
    
    def test_put_blocked(self, client):
        """PUT must be blocked (INV-AGENT-004)."""
        response = client.put("/oc/agents/test", json={})
        assert response.status_code == 405
    
    def test_patch_blocked(self, client):
        """PATCH must be blocked (INV-AGENT-004)."""
        response = client.patch("/oc/agents/test", json={})
        assert response.status_code == 405
    
    def test_delete_blocked(self, client):
        """DELETE must be blocked (INV-AGENT-004)."""
        response = client.delete("/oc/agents/test")
        assert response.status_code == 405
    
    def test_get_active_agents(self, client):
        """GET /oc/agents/active must return 200."""
        response = client.get("/oc/agents/active")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "count" in data
    
    def test_get_pac_list(self, client):
        """GET /oc/agents/pacs must return 200."""
        response = client.get("/oc/agents/pacs")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    "TestINVAGENT001_AgentActivationExplicit",
    "TestINVAGENT002_OneAgentPerStep",
    "TestINVAGENT003_ValidStates",
    "TestINVAGENT005_MissingStateExplicit",
    "TestExecutionLedger",
    "TestAgentExecutionAggregator",
    "TestAgentOCAPI",
]
