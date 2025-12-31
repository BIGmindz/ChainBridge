"""
Tests for Operator Console Live GIE Session View.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-SCALE-031
Agent: GID-02 (Sonny)
Target: Frontend visualization tests

Test Coverage:
- Enums
- Data classes  
- Timeline manager
- Session view
- Agent tracking
- Closure tracking
- Metrics
- Rendering
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from core.console.session_view import (
    # Constants
    MODULE_VERSION,
    MAX_TIMELINE_EVENTS,
    REFRESH_INTERVAL_MS,
    # Enums
    SessionState,
    EventType,
    AgentVisualState,
    ClosureStatus,
    ViewMode,
    # Data Classes
    TimelineEvent,
    AgentView,
    ClosureView,
    MetricPoint,
    SessionMetrics,
    SessionSnapshot,
    # Classes
    TimelineManager,
    SessionView,
    SessionViewRenderer,
    # Factory Functions
    create_session_view,
    create_renderer,
)


# =============================================================================
# TEST: MODULE
# =============================================================================

class TestModule:
    """Test module-level attributes."""
    
    def test_module_version(self):
        """Test module version."""
        assert MODULE_VERSION == "1.0.0"
    
    def test_constants(self):
        """Test constants."""
        assert MAX_TIMELINE_EVENTS == 10000
        assert REFRESH_INTERVAL_MS == 250


# =============================================================================
# TEST: ENUMS
# =============================================================================

class TestEnums:
    """Test enumeration types."""
    
    def test_session_state_values(self):
        """Test session state enum."""
        assert SessionState.INITIALIZING.value == "INITIALIZING"
        assert SessionState.ACTIVE.value == "ACTIVE"
        assert SessionState.COMPLETED.value == "COMPLETED"
    
    def test_event_type_values(self):
        """Test event type enum."""
        assert EventType.SESSION_START.value == "SESSION_START"
        assert EventType.AGENT_STARTED.value == "AGENT_STARTED"
        assert EventType.BER_EMITTED.value == "BER_EMITTED"
        assert EventType.PDO_CREATED.value == "PDO_CREATED"
    
    def test_agent_visual_state_values(self):
        """Test agent visual state enum."""
        assert AgentVisualState.IDLE.value == "IDLE"
        assert AgentVisualState.RUNNING.value == "RUNNING"
        assert AgentVisualState.SUCCESS.value == "SUCCESS"
        assert AgentVisualState.FAILURE.value == "FAILURE"
    
    def test_closure_status_values(self):
        """Test closure status enum."""
        assert ClosureStatus.PENDING.value == "PENDING"
        assert ClosureStatus.COMPLETE.value == "COMPLETE"
    
    def test_view_mode_values(self):
        """Test view mode enum."""
        assert ViewMode.TIMELINE.value == "TIMELINE"
        assert ViewMode.COMBINED.value == "COMBINED"


# =============================================================================
# TEST: DATA CLASSES
# =============================================================================

class TestTimelineEvent:
    """Test TimelineEvent data class."""
    
    def test_event_creation(self):
        """Test creating event."""
        event = TimelineEvent(
            event_id="EVT-001",
            event_type=EventType.SESSION_START,
            timestamp=datetime.now(timezone.utc).isoformat(),
            title="Test Event",
        )
        assert event.event_id == "EVT-001"
        assert event.event_type == EventType.SESSION_START
    
    def test_event_to_dict(self):
        """Test event serialization."""
        event = TimelineEvent(
            event_id="EVT-001",
            event_type=EventType.SESSION_START,
            timestamp=datetime.now(timezone.utc).isoformat(),
            title="Test Event",
        )
        data = event.to_dict()
        assert "event_id" in data
        assert "event_type" in data


class TestAgentView:
    """Test AgentView data class."""
    
    def test_view_creation(self):
        """Test creating agent view."""
        view = AgentView(agent_id="A", name="Agent A")
        assert view.agent_id == "A"
        assert view.state == AgentVisualState.IDLE
    
    def test_is_active(self):
        """Test is_active property."""
        view = AgentView(agent_id="A", name="Agent A")
        assert view.is_active is False
        view.state = AgentVisualState.RUNNING
        assert view.is_active is True
    
    def test_is_complete(self):
        """Test is_complete property."""
        view = AgentView(agent_id="A", name="Agent A")
        assert view.is_complete is False
        view.state = AgentVisualState.SUCCESS
        assert view.is_complete is True
    
    def test_view_to_dict(self):
        """Test view serialization."""
        view = AgentView(agent_id="A", name="Agent A")
        data = view.to_dict()
        assert data["agent_id"] == "A"


class TestClosureView:
    """Test ClosureView data class."""
    
    def test_closure_creation(self):
        """Test creating closure view."""
        closure = ClosureView(session_id="SES-001")
        assert closure.ber_status == ClosureStatus.PENDING
        assert closure.positive_closure is False
    
    def test_is_complete(self):
        """Test closure completion check."""
        closure = ClosureView(session_id="SES-001")
        assert closure.is_complete is False
        
        closure.ber_status = ClosureStatus.COMPLETE
        closure.pdo_status = ClosureStatus.COMPLETE
        closure.positive_closure = True
        assert closure.is_complete is True
    
    def test_completion_percentage(self):
        """Test completion percentage calculation."""
        closure = ClosureView(session_id="SES-001")
        assert closure.completion_percentage == 0.0
        
        closure.ber_status = ClosureStatus.COMPLETE
        closure.pdo_status = ClosureStatus.COMPLETE
        assert closure.completion_percentage == 0.5


class TestSessionMetrics:
    """Test SessionMetrics data class."""
    
    def test_metrics_creation(self):
        """Test creating metrics."""
        metrics = SessionMetrics(total_agents=5, completed_agents=3)
        assert metrics.total_agents == 5
        assert metrics.completed_agents == 3
    
    def test_metrics_to_dict(self):
        """Test metrics serialization."""
        metrics = SessionMetrics(total_agents=5)
        data = metrics.to_dict()
        assert "total_agents" in data


# =============================================================================
# TEST: TIMELINE MANAGER
# =============================================================================

class TestTimelineManager:
    """Test TimelineManager class."""
    
    def test_add_event(self):
        """Test adding event."""
        tm = TimelineManager()
        event = tm.add_event(EventType.SESSION_START, "Test")
        assert event.event_type == EventType.SESSION_START
        assert tm.event_count == 1
    
    def test_get_events(self):
        """Test getting events."""
        tm = TimelineManager()
        tm.add_event(EventType.SESSION_START, "Start")
        tm.add_event(EventType.AGENT_STARTED, "Agent", agent_id="A")
        
        events = tm.get_events()
        assert len(events) == 2
    
    def test_filter_by_type(self):
        """Test filtering events by type."""
        tm = TimelineManager()
        tm.add_event(EventType.SESSION_START, "Start")
        tm.add_event(EventType.AGENT_STARTED, "Agent")
        
        events = tm.get_events(event_type=EventType.SESSION_START)
        assert len(events) == 1
    
    def test_filter_by_agent(self):
        """Test filtering events by agent."""
        tm = TimelineManager()
        tm.add_event(EventType.AGENT_STARTED, "Agent A", agent_id="A")
        tm.add_event(EventType.AGENT_STARTED, "Agent B", agent_id="B")
        
        events = tm.get_events(agent_id="A")
        assert len(events) == 1
    
    def test_max_events_limit(self):
        """Test max events trimming."""
        tm = TimelineManager(max_events=5)
        for i in range(10):
            tm.add_event(EventType.METRIC_RECORDED, f"Metric {i}")
        
        assert tm.event_count == 5
    
    def test_clear(self):
        """Test clearing events."""
        tm = TimelineManager()
        tm.add_event(EventType.SESSION_START, "Start")
        tm.clear()
        assert tm.event_count == 0


# =============================================================================
# TEST: SESSION VIEW
# =============================================================================

class TestSessionView:
    """Test SessionView class."""
    
    def test_create_session(self):
        """Test creating session view."""
        view = create_session_view("SES-001")
        assert view.session_id == "SES-001"
        assert view.state == SessionState.INITIALIZING
    
    def test_session_start(self):
        """Test starting session."""
        view = create_session_view()
        view.start()
        assert view.state == SessionState.ACTIVE
    
    def test_session_complete(self):
        """Test completing session."""
        view = create_session_view()
        view.start()
        view.complete()
        assert view.state == SessionState.COMPLETED
    
    def test_session_fail(self):
        """Test failing session."""
        view = create_session_view()
        view.start()
        view.fail("Error occurred")
        assert view.state == SessionState.FAILED
    
    def test_pause_resume(self):
        """Test pause and resume."""
        view = create_session_view()
        view.start()
        view.pause()
        assert view.state == SessionState.PAUSED
        view.resume()
        assert view.state == SessionState.ACTIVE


class TestAgentTracking:
    """Test agent tracking in session view."""
    
    def test_register_agent(self):
        """Test registering agent."""
        view = create_session_view()
        agent = view.register_agent("A", "Agent A")
        assert agent.agent_id == "A"
        assert view.get_agent("A") is not None
    
    def test_start_agent(self):
        """Test starting agent."""
        view = create_session_view()
        view.register_agent("A", "Agent A")
        view.start_agent("A")
        
        agent = view.get_agent("A")
        assert agent.state == AgentVisualState.RUNNING
    
    def test_update_progress(self):
        """Test updating agent progress."""
        view = create_session_view()
        view.register_agent("A", "Agent A")
        view.update_agent_progress("A", 0.5)
        
        agent = view.get_agent("A")
        assert agent.progress == 0.5
    
    def test_complete_agent_success(self):
        """Test completing agent successfully."""
        view = create_session_view()
        view.register_agent("A", "Agent A")
        view.start_agent("A")
        view.complete_agent("A", outputs=3, success=True)
        
        agent = view.get_agent("A")
        assert agent.state == AgentVisualState.SUCCESS
        assert agent.output_count == 3
    
    def test_complete_agent_failure(self):
        """Test completing agent with failure."""
        view = create_session_view()
        view.register_agent("A", "Agent A")
        view.start_agent("A")
        view.complete_agent("A", success=False)
        
        agent = view.get_agent("A")
        assert agent.state == AgentVisualState.FAILURE
    
    def test_block_agent(self):
        """Test blocking agent."""
        view = create_session_view()
        view.register_agent("A", "Agent A")
        view.block_agent("A", "Dependency not met")
        
        agent = view.get_agent("A")
        assert agent.state == AgentVisualState.BLOCKED


class TestClosureTracking:
    """Test governance closure tracking."""
    
    def test_record_ber(self):
        """Test recording BER."""
        view = create_session_view()
        view.record_ber("BER-001")
        
        snapshot = view.get_snapshot()
        assert snapshot.closure_view.ber_count == 1
        assert snapshot.closure_view.ber_status == ClosureStatus.PARTIAL
    
    def test_complete_ber(self):
        """Test completing BER closure."""
        view = create_session_view()
        view.record_ber("BER-001")
        view.complete_ber()
        
        snapshot = view.get_snapshot()
        assert snapshot.closure_view.ber_status == ClosureStatus.COMPLETE
    
    def test_record_pdo(self):
        """Test recording PDO."""
        view = create_session_view()
        view.record_pdo("PDO-001")
        
        snapshot = view.get_snapshot()
        assert snapshot.closure_view.pdo_count == 1
    
    def test_record_wrap(self):
        """Test recording WRAP."""
        view = create_session_view()
        view.record_wrap("WRAP-001")
        
        snapshot = view.get_snapshot()
        assert snapshot.closure_view.wrap_count == 1
    
    def test_positive_closure(self):
        """Test setting positive closure."""
        view = create_session_view()
        view.set_positive_closure(True)
        
        snapshot = view.get_snapshot()
        assert snapshot.closure_view.positive_closure is True


class TestMetrics:
    """Test metrics recording."""
    
    def test_record_metric(self):
        """Test recording metric."""
        view = create_session_view()
        point = view.record_metric("latency", 150.5, "ms")
        
        assert point.name == "latency"
        assert point.value == 150.5
        assert point.unit == "ms"
    
    def test_metrics_aggregation(self):
        """Test metrics aggregation."""
        view = create_session_view()
        view.start()
        
        view.register_agent("A", "Agent A")
        view.start_agent("A")
        view.complete_agent("A", outputs=5)
        
        metrics = view.metrics
        assert metrics.total_agents == 1
        assert metrics.completed_agents == 1


class TestSnapshot:
    """Test session snapshot."""
    
    def test_get_snapshot(self):
        """Test getting snapshot."""
        view = create_session_view("SES-001")
        snapshot = view.get_snapshot()
        
        assert snapshot.session_id == "SES-001"
        assert snapshot.state == SessionState.INITIALIZING
    
    def test_snapshot_to_dict(self):
        """Test snapshot serialization."""
        view = create_session_view()
        snapshot = view.get_snapshot()
        data = snapshot.to_dict()
        
        assert "session_id" in data
        assert "state" in data
        assert "metrics" in data
    
    def test_to_json(self):
        """Test JSON export."""
        view = create_session_view()
        json_str = view.to_json()
        
        data = json.loads(json_str)
        assert "session_id" in data


class TestListeners:
    """Test snapshot listeners."""
    
    def test_add_listener(self):
        """Test adding listener."""
        view = create_session_view()
        snapshots = []
        
        view.add_listener(lambda s: snapshots.append(s))
        view.start()
        
        assert len(snapshots) >= 1
    
    def test_remove_listener(self):
        """Test removing listener."""
        view = create_session_view()
        snapshots = []
        
        callback = lambda s: snapshots.append(s)
        view.add_listener(callback)
        view.remove_listener(callback)
        view.start()
        
        assert len(snapshots) == 0


# =============================================================================
# TEST: RENDERER
# =============================================================================

class TestRenderer:
    """Test SessionViewRenderer."""
    
    def test_create_renderer(self):
        """Test creating renderer."""
        view = create_session_view()
        renderer = create_renderer(view)
        assert isinstance(renderer, SessionViewRenderer)
    
    def test_render_timeline(self):
        """Test rendering timeline."""
        view = create_session_view()
        view.start()
        
        renderer = create_renderer(view)
        output = renderer.render_timeline_text()
        
        assert "TIMELINE" in output
    
    def test_render_agents(self):
        """Test rendering agents."""
        view = create_session_view()
        view.register_agent("A", "Agent A")
        
        renderer = create_renderer(view)
        output = renderer.render_agents_text()
        
        assert "AGENTS" in output
        assert "Agent A" in output
    
    def test_render_closure(self):
        """Test rendering closure status."""
        view = create_session_view()
        
        renderer = create_renderer(view)
        output = renderer.render_closure_text()
        
        assert "GOVERNANCE CLOSURE" in output
        assert "BER" in output
        assert "PDO" in output
    
    def test_render_metrics(self):
        """Test rendering metrics."""
        view = create_session_view()
        
        renderer = create_renderer(view)
        output = renderer.render_metrics_text()
        
        assert "METRICS" in output
    
    def test_render_full_dashboard(self):
        """Test rendering full dashboard."""
        view = create_session_view()
        view.start()
        view.register_agent("A", "Agent A")
        
        renderer = create_renderer(view)
        output = renderer.render_full_dashboard()
        
        assert "TIMELINE" in output
        assert "AGENTS" in output
        assert "GOVERNANCE CLOSURE" in output
        assert "METRICS" in output


# =============================================================================
# TEST: FACTORY FUNCTIONS
# =============================================================================

class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_session_view_auto_id(self):
        """Test auto-generated session ID."""
        view = create_session_view()
        assert view.session_id.startswith("SES-")
    
    def test_create_session_view_custom_id(self):
        """Test custom session ID."""
        view = create_session_view("MY-SESSION")
        assert view.session_id == "MY-SESSION"
