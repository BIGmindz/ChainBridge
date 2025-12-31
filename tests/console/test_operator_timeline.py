"""
Tests for Operator Console Timeline.

PAC Reference: PAC-BENSON-EXEC-GOVERNANCE-GIE-REAL-WORK-032
Agent: GID-02 (Sonny) — OPERATOR CONSOLE / SESSION & TIMELINE UX
"""

import pytest
import threading
import time
from datetime import datetime, timedelta, timezone

from core.console.operator_timeline import (
    TimelineRenderer,
    SessionStateDisplay,
    EventStream,
    AlertPanel,
    QuickActions,
    ExportManager,
    TimelineEventType,
    AgentStatus,
    AlertSeverity,
    AlertState,
    TimelineEvent,
    TimelineMarker,
    AgentStatusInfo,
    Alert,
    QuickAction,
    compute_wrap_hash,
)


# =============================================================================
# TIMELINE RENDERER TESTS
# =============================================================================

class TestTimelineRenderer:
    """Tests for TimelineRenderer."""
    
    def test_add_event(self) -> None:
        """Add event to timeline."""
        renderer = TimelineRenderer()
        
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.AGENT_ACTIVATED,
            timestamp=datetime.now(timezone.utc),
            agent_id="GID-01",
            pac_id="PAC-032",
            data={"test": True},
        )
        
        renderer.add_event(event)
        stats = renderer.get_timeline_stats()
        
        assert stats["total_events"] == 1
        assert stats["lanes"] == 1
    
    def test_add_marker(self) -> None:
        """Add marker to timeline."""
        renderer = TimelineRenderer()
        
        marker = TimelineMarker(
            marker_id="mark-1",
            marker_type="WRAP",
            timestamp=datetime.now(timezone.utc),
            label="GID-01 WRAP",
            agent_id="GID-01",
            hash_value="abc123",
        )
        
        renderer.add_marker(marker)
        stats = renderer.get_timeline_stats()
        
        assert stats["total_markers"] == 1
        assert stats["marker_counts"]["WRAP"] == 1
    
    def test_events_in_range(self) -> None:
        """Get events within time range."""
        renderer = TimelineRenderer()
        now = datetime.now(timezone.utc)
        
        for i in range(5):
            event = TimelineEvent(
                event_id=f"evt-{i}",
                event_type=TimelineEventType.AGENT_ACTIVATED,
                timestamp=now + timedelta(minutes=i),
                agent_id=f"GID-{i:02d}",
                pac_id="PAC-032",
                data={},
            )
            renderer.add_event(event)
        
        # Query middle range
        start = now + timedelta(minutes=1)
        end = now + timedelta(minutes=3)
        events = renderer.get_events_in_range(start, end)
        
        assert len(events) == 3
    
    def test_lane_events(self) -> None:
        """Get events for specific lane."""
        renderer = TimelineRenderer()
        now = datetime.now(timezone.utc)
        
        # Add events for different agents
        for agent_id in ["GID-01", "GID-01", "GID-02"]:
            event = TimelineEvent(
                event_id=f"evt-{agent_id}-{time.time()}",
                event_type=TimelineEventType.AGENT_ACTIVATED,
                timestamp=now,
                agent_id=agent_id,
                pac_id="PAC-032",
                data={},
            )
            renderer.add_event(event)
        
        gid01_events = renderer.get_lane_events("GID-01")
        assert len(gid01_events) == 2
        
        gid02_events = renderer.get_lane_events("GID-02")
        assert len(gid02_events) == 1
    
    def test_render_to_json(self) -> None:
        """Render timeline to JSON."""
        renderer = TimelineRenderer()
        now = datetime.now(timezone.utc)
        
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.WRAP_SUBMITTED,
            timestamp=now,
            agent_id="GID-01",
            pac_id="PAC-032",
            data={"hash": "abc123"},
        )
        renderer.add_event(event)
        
        json_output = renderer.render_to_json()
        assert "evt-1" in json_output
        assert "WRAP_SUBMITTED" in json_output
    
    def test_render_to_svg(self) -> None:
        """Render timeline to SVG."""
        renderer = TimelineRenderer()
        now = datetime.now(timezone.utc)
        
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.AGENT_ACTIVATED,
            timestamp=now,
            agent_id="GID-01",
            pac_id="PAC-032",
            data={},
        )
        renderer.add_event(event)
        
        svg = renderer.render_to_svg(800, 400)
        assert "<svg" in svg
        assert "GID-01" in svg
    
    def test_empty_svg(self) -> None:
        """Empty timeline renders placeholder SVG."""
        renderer = TimelineRenderer()
        svg = renderer.render_to_svg()
        
        assert "<svg" in svg
        assert "No events" in svg


# =============================================================================
# SESSION STATE DISPLAY TESTS
# =============================================================================

class TestSessionStateDisplay:
    """Tests for SessionStateDisplay."""
    
    def test_update_agent(self) -> None:
        """Update agent status."""
        display = SessionStateDisplay()
        
        info = AgentStatusInfo(
            agent_id="GID-01",
            status=AgentStatus.EXECUTING,
            progress=0.5,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            dependencies_satisfied=2,
            dependencies_total=3,
            blocking_issues=[],
            resource_usage={"compute": 50.0},
        )
        
        display.update_agent(info)
        active = display.get_active_agents()
        
        assert len(active) == 1
        assert active[0].agent_id == "GID-01"
    
    def test_resource_gauges(self) -> None:
        """Update and get resource gauges."""
        display = SessionStateDisplay()
        
        display.update_resource("compute", 60.0, 100.0)
        display.update_resource("memory", 800.0, 1000.0)
        
        gauges = display.get_resource_gauges()
        
        assert gauges["compute"]["utilization"] == 0.6
        assert gauges["memory"]["utilization"] == 0.8
    
    def test_blocking_tracking(self) -> None:
        """Track blocking relationships."""
        display = SessionStateDisplay()
        
        display.set_blocking("GID-02", "GID-01")
        display.set_blocking("GID-03", "GID-01")
        
        blocked = display.get_blocked_agents()
        
        assert len(blocked) == 2
        assert ("GID-02", {"GID-01"}) in blocked
    
    def test_dependency_status(self) -> None:
        """Get dependency satisfaction status."""
        display = SessionStateDisplay()
        
        info = AgentStatusInfo(
            agent_id="GID-01",
            status=AgentStatus.READY,
            progress=0.0,
            started_at=None,
            completed_at=None,
            dependencies_satisfied=2,
            dependencies_total=4,
            blocking_issues=[],
            resource_usage={},
        )
        display.update_agent(info)
        
        status = display.get_dependency_status("GID-01")
        
        assert status["satisfied"] == 2
        assert status["total"] == 4
        assert status["ratio"] == 0.5
    
    def test_render_summary(self) -> None:
        """Render session state summary."""
        display = SessionStateDisplay()
        
        for i in range(3):
            info = AgentStatusInfo(
                agent_id=f"GID-{i:02d}",
                status=AgentStatus.EXECUTING if i < 2 else AgentStatus.COMPLETED,
                progress=0.5 if i < 2 else 1.0,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc) if i == 2 else None,
                dependencies_satisfied=1,
                dependencies_total=1,
                blocking_issues=[],
                resource_usage={},
            )
            display.update_agent(info)
        
        summary = display.render_summary()
        
        assert summary["agent_count"] == 3
        assert summary["status_counts"]["EXECUTING"] == 2
        assert summary["status_counts"]["COMPLETED"] == 1


# =============================================================================
# EVENT STREAM TESTS
# =============================================================================

class TestEventStream:
    """Tests for EventStream."""
    
    def test_push_and_query(self) -> None:
        """Push events and query."""
        stream = EventStream()
        now = datetime.now(timezone.utc)
        
        for i in range(5):
            event = TimelineEvent(
                event_id=f"evt-{i}",
                event_type=TimelineEventType.AGENT_ACTIVATED,
                timestamp=now + timedelta(seconds=i),
                agent_id=f"GID-{i:02d}",
                pac_id="PAC-032",
                data={},
            )
            stream.push(event)
        
        events = stream.query(limit=3)
        assert len(events) == 3
    
    def test_filter_by_agent(self) -> None:
        """Filter events by agent."""
        stream = EventStream()
        now = datetime.now(timezone.utc)
        
        for agent_id in ["GID-01", "GID-01", "GID-02"]:
            event = TimelineEvent(
                event_id=f"evt-{time.time()}",
                event_type=TimelineEventType.AGENT_ACTIVATED,
                timestamp=now,
                agent_id=agent_id,
                pac_id="PAC-032",
                data={},
            )
            stream.push(event)
        
        events = stream.query(agent_ids={"GID-01"})
        assert len(events) == 2
    
    def test_filter_by_type(self) -> None:
        """Filter events by type."""
        stream = EventStream()
        now = datetime.now(timezone.utc)
        
        for event_type in [
            TimelineEventType.AGENT_ACTIVATED,
            TimelineEventType.WRAP_SUBMITTED,
            TimelineEventType.AGENT_COMPLETED,
        ]:
            event = TimelineEvent(
                event_id=f"evt-{event_type.value}",
                event_type=event_type,
                timestamp=now,
                agent_id="GID-01",
                pac_id="PAC-032",
                data={},
            )
            stream.push(event)
        
        events = stream.query(event_types={TimelineEventType.WRAP_SUBMITTED})
        assert len(events) == 1
        assert events[0].event_type == TimelineEventType.WRAP_SUBMITTED
    
    def test_subscribe_listener(self) -> None:
        """Subscribe to event stream."""
        stream = EventStream()
        received = []
        
        def callback(event: TimelineEvent) -> None:
            received.append(event)
        
        stream.subscribe(callback)
        
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.BER_ISSUED,
            timestamp=datetime.now(timezone.utc),
            agent_id=None,
            pac_id="PAC-032",
            data={},
        )
        stream.push(event)
        
        assert len(received) == 1
        
        stream.unsubscribe(callback)
        stream.push(event)
        
        assert len(received) == 1  # No new events
    
    def test_export_csv(self) -> None:
        """Export to CSV."""
        stream = EventStream()
        now = datetime.now(timezone.utc)
        
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.PDO_SEALED,
            timestamp=now,
            agent_id=None,
            pac_id="PAC-032",
            data={},
        )
        stream.push(event)
        
        csv = stream.export_to_csv()
        
        assert "evt-1" in csv
        assert "PDO_SEALED" in csv
        assert "PAC-032" in csv
    
    def test_severity_color(self) -> None:
        """Get severity color for events."""
        stream = EventStream()
        
        failed_event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.AGENT_FAILED,
            timestamp=datetime.now(timezone.utc),
            agent_id="GID-01",
            pac_id="PAC-032",
            data={},
        )
        
        completed_event = TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.PAC_COMPLETED,
            timestamp=datetime.now(timezone.utc),
            agent_id=None,
            pac_id="PAC-032",
            data={},
        )
        
        assert stream.get_severity_color(failed_event) == "#F44336"  # Red
        assert stream.get_severity_color(completed_event) == "#4CAF50"  # Green


# =============================================================================
# ALERT PANEL TESTS
# =============================================================================

class TestAlertPanel:
    """Tests for AlertPanel."""
    
    def test_raise_alert(self) -> None:
        """Raise new alert."""
        panel = AlertPanel()
        
        alert = panel.raise_alert(
            severity=AlertSeverity.CRITICAL,
            title="Agent Failed",
            message="GID-01 failed to complete",
            pac_id="PAC-032",
            agent_id="GID-01",
        )
        
        assert alert.alert_id is not None
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.state == AlertState.ACTIVE
    
    def test_acknowledge_alert(self) -> None:
        """Acknowledge alert."""
        panel = AlertPanel()
        
        alert = panel.raise_alert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            pac_id="PAC-032",
        )
        
        result = panel.acknowledge(alert.alert_id, "operator-1")
        
        assert result is True
        assert alert.state == AlertState.ACKNOWLEDGED
        assert alert.acknowledged_at is not None
    
    def test_resolve_alert(self) -> None:
        """Resolve alert."""
        panel = AlertPanel()
        
        alert = panel.raise_alert(
            severity=AlertSeverity.INFO,
            title="Test Alert",
            message="Test message",
            pac_id="PAC-032",
        )
        
        result = panel.resolve(alert.alert_id, "Issue fixed")
        
        assert result is True
        assert alert.state == AlertState.RESOLVED
        assert "Issue fixed" in alert.actions_taken[-1]
    
    def test_escalate_alert(self) -> None:
        """Escalate alert."""
        panel = AlertPanel()
        
        alert = panel.raise_alert(
            severity=AlertSeverity.CRITICAL,
            title="Urgent Issue",
            message="Needs escalation",
            pac_id="PAC-032",
        )
        
        result = panel.escalate(alert.alert_id, "No response")
        
        assert result is True
        assert alert.state == AlertState.ESCALATED
    
    def test_get_active_alerts(self) -> None:
        """Get active alerts."""
        panel = AlertPanel()
        
        alert1 = panel.raise_alert(
            severity=AlertSeverity.CRITICAL,
            title="Alert 1",
            message="Message 1",
            pac_id="PAC-032",
        )
        
        alert2 = panel.raise_alert(
            severity=AlertSeverity.WARNING,
            title="Alert 2",
            message="Message 2",
            pac_id="PAC-032",
        )
        
        panel.resolve(alert2.alert_id)
        
        active = panel.get_active_alerts()
        
        assert len(active) == 1
        assert active[0].alert_id == alert1.alert_id
    
    def test_root_cause_grouping(self) -> None:
        """Group alerts by root cause."""
        panel = AlertPanel()
        
        panel.raise_alert(
            severity=AlertSeverity.WARNING,
            title="Alert 1",
            message="Message 1",
            pac_id="PAC-032",
            root_cause_group="database-issue",
        )
        
        panel.raise_alert(
            severity=AlertSeverity.WARNING,
            title="Alert 2",
            message="Message 2",
            pac_id="PAC-032",
            root_cause_group="database-issue",
        )
        
        grouped = panel.get_alerts_by_root_cause("database-issue")
        
        assert len(grouped) == 2
    
    def test_auto_escalation(self) -> None:
        """Check auto-escalation."""
        panel = AlertPanel()
        
        alert = panel.raise_alert(
            severity=AlertSeverity.CRITICAL,
            title="Urgent",
            message="Test",
            pac_id="PAC-032",
        )
        
        # Set deadline in past
        alert.escalation_deadline = datetime.now(timezone.utc) - timedelta(minutes=1)
        
        escalated = panel.check_escalations()
        
        assert len(escalated) == 1
        assert alert.state == AlertState.ESCALATED


# =============================================================================
# QUICK ACTIONS TESTS
# =============================================================================

class TestQuickActions:
    """Tests for QuickActions."""
    
    def test_create_restart_action(self) -> None:
        """Create restart action."""
        actions = QuickActions()
        
        action = actions.create_restart_action("GID-01")
        
        assert action.action_type == "RESTART_AGENT"
        assert action.target_agent == "GID-01"
        assert action.requires_confirmation is True
    
    def test_create_priority_override(self) -> None:
        """Create priority override action."""
        actions = QuickActions()
        
        action = actions.create_priority_override("GID-01", "CRITICAL")
        
        assert action.action_type == "PRIORITY_OVERRIDE"
        assert action.parameters["new_priority"] == "CRITICAL"
    
    def test_queue_and_execute(self) -> None:
        """Queue and execute action."""
        actions = QuickActions()
        executed = []
        
        def handler(action: QuickAction) -> bool:
            executed.append(action)
            return True
        
        actions.register_handler("MANUAL_CHECKPOINT", handler)
        
        action = actions.create_checkpoint_action()
        action_id = actions.queue_action(action)
        
        success, msg = actions.execute_action(action_id)
        
        assert success is True
        assert len(executed) == 1
    
    def test_confirmation_required(self) -> None:
        """Action requiring confirmation fails without it."""
        actions = QuickActions()
        
        def handler(action: QuickAction) -> bool:
            return True
        
        actions.register_handler("EMERGENCY_TERMINATE", handler)
        
        action = actions.create_terminate_action("test")
        action_id = actions.queue_action(action)
        
        # Without confirmation
        success, msg = actions.execute_action(action_id, confirmed=False)
        assert success is False
        
        # Re-queue and confirm
        action_id = actions.queue_action(action)
        success, msg = actions.execute_action(action_id, confirmed=True)
        assert success is True
    
    def test_available_actions(self) -> None:
        """Get available actions."""
        actions = QuickActions()
        
        # Without agent context
        available = actions.get_available_actions()
        assert len(available) == 2  # checkpoint and terminate
        
        # With agent context
        available = actions.get_available_actions("GID-01")
        assert len(available) == 4  # + restart and priority


# =============================================================================
# EXPORT MANAGER TESTS
# =============================================================================

class TestExportManager:
    """Tests for ExportManager."""
    
    def test_export_timeline_json(self) -> None:
        """Export timeline to JSON."""
        renderer = TimelineRenderer()
        display = SessionStateDisplay()
        stream = EventStream()
        
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.AGENT_ACTIVATED,
            timestamp=datetime.now(timezone.utc),
            agent_id="GID-01",
            pac_id="PAC-032",
            data={},
        )
        renderer.add_event(event)
        
        manager = ExportManager(renderer, display, stream)
        json_output = manager.export_timeline_json()
        
        assert "evt-1" in json_output
    
    def test_export_timeline_svg(self) -> None:
        """Export timeline to SVG."""
        renderer = TimelineRenderer()
        display = SessionStateDisplay()
        stream = EventStream()
        
        manager = ExportManager(renderer, display, stream)
        svg = manager.export_timeline_svg()
        
        assert "<svg" in svg
    
    def test_export_full_report(self) -> None:
        """Export full report."""
        renderer = TimelineRenderer()
        display = SessionStateDisplay()
        stream = EventStream()
        
        manager = ExportManager(renderer, display, stream)
        report = manager.export_full_report()
        
        assert "exported_at" in report
        assert "version" in report
        assert "timeline_stats" in report


# =============================================================================
# WRAP HASH TESTS
# =============================================================================

class TestWrapHash:
    """Tests for WRAP hash computation."""
    
    def test_compute_wrap_hash(self) -> None:
        """Compute WRAP hash."""
        wrap_hash = compute_wrap_hash()
        
        assert wrap_hash is not None
        assert len(wrap_hash) == 16
    
    def test_wrap_hash_deterministic(self) -> None:
        """WRAP hash is deterministic."""
        hash1 = compute_wrap_hash()
        hash2 = compute_wrap_hash()
        
        assert hash1 == hash2


# =============================================================================
# THREAD SAFETY TESTS
# =============================================================================

class TestThreadSafety:
    """Tests for thread safety."""
    
    def test_concurrent_timeline_events(self) -> None:
        """Concurrent timeline event addition."""
        renderer = TimelineRenderer()
        errors = []
        
        def add_events(thread_id: int) -> None:
            try:
                for i in range(50):
                    event = TimelineEvent(
                        event_id=f"evt-{thread_id}-{i}",
                        event_type=TimelineEventType.AGENT_ACTIVATED,
                        timestamp=datetime.now(timezone.utc),
                        agent_id=f"GID-{thread_id:02d}",
                        pac_id="PAC-032",
                        data={},
                    )
                    renderer.add_event(event)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=add_events, args=(i,)) for i in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        stats = renderer.get_timeline_stats()
        assert stats["total_events"] == 250  # 5 threads * 50 events
    
    def test_concurrent_alerts(self) -> None:
        """Concurrent alert operations."""
        panel = AlertPanel()
        errors = []
        
        def alert_operations(thread_id: int) -> None:
            try:
                for i in range(20):
                    alert = panel.raise_alert(
                        severity=AlertSeverity.WARNING,
                        title=f"Alert {thread_id}-{i}",
                        message="Test",
                        pac_id="PAC-032",
                    )
                    panel.acknowledge(alert.alert_id)
            except Exception as e:
                errors.append(e)
        
        threads = [
            threading.Thread(target=alert_operations, args=(i,))
            for i in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
