"""
Heartbeat Panel - OCC Dashboard Component
==========================================

PAC Reference: PAC-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM
Classification: LAW_TIER
Authors: 
    - PAX (GID-05) - Timeline UX
    - LIRA (GID-09) - UI Rendering
Orchestrator: BENSON (GID-00)

Renders real-time heartbeat timeline in OCC UI (Streamlit).
Provides visual feedback for all PAC execution events.
"""

import streamlit as st
import json
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


# ==================== Event Type Styling ====================

EVENT_STYLES = {
    "PAC_START": {"icon": "🚀", "color": "#4CAF50", "label": "PAC Start"},
    "PAC_COMPLETE": {"icon": "✅", "color": "#2196F3", "label": "PAC Complete"},
    "PAC_FAILED": {"icon": "❌", "color": "#f44336", "label": "PAC Failed"},
    "LANE_TRANSITION": {"icon": "🔀", "color": "#9C27B0", "label": "Lane Change"},
    "LANE_ACTIVE": {"icon": "🛤️", "color": "#9C27B0", "label": "Lane Active"},
    "TASK_START": {"icon": "⚡", "color": "#FF9800", "label": "Task Start"},
    "TASK_COMPLETE": {"icon": "✔️", "color": "#8BC34A", "label": "Task Done"},
    "TASK_FAILED": {"icon": "⚠️", "color": "#FF5722", "label": "Task Failed"},
    "AGENT_ACTIVE": {"icon": "🤖", "color": "#00BCD4", "label": "Agent Active"},
    "AGENT_ATTESTED": {"icon": "📝", "color": "#009688", "label": "Attested"},
    "AGENT_IDLE": {"icon": "💤", "color": "#607D8B", "label": "Agent Idle"},
    "WRAP_GENERATED": {"icon": "📦", "color": "#673AB7", "label": "WRAP"},
    "BER_GENERATED": {"icon": "📊", "color": "#3F51B5", "label": "BER"},
    "LEDGER_COMMIT": {"icon": "📒", "color": "#795548", "label": "Ledger"},
    "HEARTBEAT_PING": {"icon": "💓", "color": "#E91E63", "label": "Ping"},
    "VISIBILITY_CHECK": {"icon": "👁️", "color": "#CDDC39", "label": "Visibility"},
}


# ==================== Mock Data for Standalone Testing ====================

MOCK_EVENTS = [
    {
        "event_type": "PAC_START",
        "timestamp": "2026-01-13T18:30:00Z",
        "pac_id": "PAC-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM",
        "pac_title": "OCC Execution Heartbeat System",
        "lane": "OCC/GOVERNANCE_VISIBILITY",
        "sequence_number": 1
    },
    {
        "event_type": "AGENT_ACTIVE",
        "timestamp": "2026-01-13T18:30:01Z",
        "agent_gid": "GID-00",
        "agent_name": "BENSON",
        "agent_role": "Orchestrator",
        "sequence_number": 2
    },
    {
        "event_type": "TASK_START",
        "timestamp": "2026-01-13T18:30:05Z",
        "task_id": "TASK-01",
        "task_title": "Implement heartbeat emitter",
        "agent_name": "CODY",
        "sequence_number": 3
    },
    {
        "event_type": "TASK_COMPLETE",
        "timestamp": "2026-01-13T18:31:00Z",
        "task_id": "TASK-01",
        "task_title": "Implement heartbeat emitter",
        "sequence_number": 4
    },
    {
        "event_type": "WRAP_GENERATED",
        "timestamp": "2026-01-13T18:32:00Z",
        "wrap_id": "WRAP-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM",
        "pac_id": "PAC-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM",
        "sequence_number": 5
    },
    {
        "event_type": "BER_GENERATED",
        "timestamp": "2026-01-13T18:32:30Z",
        "ber_id": "BER-P744-OCC-EXECUTION-HEARTBEAT-SYSTEM",
        "ber_score": 100,
        "sequence_number": 6
    }
]


# ==================== Heartbeat Panel Component ====================

def render_heartbeat_panel(
    api_base_url: str = "http://localhost:5001/api/v1/heartbeat",
    use_mock: bool = False,
    auto_refresh: bool = True,
    refresh_interval: int = 5
):
    """
    Render the heartbeat timeline panel for OCC dashboard.
    
    Args:
        api_base_url: Base URL for heartbeat API
        use_mock: Use mock data instead of live API
        auto_refresh: Enable auto-refresh
        refresh_interval: Refresh interval in seconds
    """
    st.markdown("""
    <style>
    .heartbeat-event {
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 8px;
        border-left: 4px solid;
    }
    .heartbeat-timeline {
        max-height: 600px;
        overflow-y: auto;
    }
    .event-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .event-time {
        font-size: 0.8em;
        color: #888;
    }
    .ber-score {
        font-size: 1.5em;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown("## 💓 Execution Heartbeat")
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    with col3:
        auto_refresh = st.checkbox("Auto", value=auto_refresh)
    
    # Fetch events
    if use_mock:
        events = MOCK_EVENTS
        status = {"status": "mock", "sequence": len(events)}
    else:
        events, status = fetch_heartbeat_data(api_base_url)
    
    # Status indicator
    if status.get("status") == "healthy":
        st.success(f"🟢 Stream Active | Sequence: {status.get('sequence', 0)}")
    elif status.get("status") == "mock":
        st.info("🟡 Mock Mode | Using sample data")
    else:
        st.error(f"🔴 Stream Unavailable: {status.get('error', 'Unknown error')}")
    
    # Current execution state
    render_current_state(events)
    
    st.divider()
    
    # Timeline
    st.markdown("### 📜 Event Timeline")
    render_timeline(events)
    
    # Agent status grid
    st.divider()
    st.markdown("### 🤖 Agent Status")
    render_agent_grid(events)
    
    # Auto-refresh
    if auto_refresh and not use_mock:
        time.sleep(refresh_interval)
        st.rerun()


def fetch_heartbeat_data(api_base_url: str) -> tuple:
    """Fetch heartbeat data from API."""
    events = []
    status = {"status": "unavailable"}
    
    try:
        # Fetch health
        health_resp = requests.get(f"{api_base_url}/health", timeout=2)
        if health_resp.status_code == 200:
            status = health_resp.json()
        
        # Fetch history
        history_resp = requests.get(f"{api_base_url}/history?limit=100", timeout=2)
        if history_resp.status_code == 200:
            data = history_resp.json()
            events = data.get("events", [])
    except requests.RequestException as e:
        status = {"status": "error", "error": str(e)}
    
    return events, status


def render_current_state(events: List[Dict[str, Any]]):
    """Render current execution state summary."""
    # Extract current PAC from events
    current_pac = None
    current_lane = None
    latest_task = None
    ber_score = None
    
    for event in reversed(events):
        event_type = event.get("event_type", "")
        
        if event_type == "PAC_START" and not current_pac:
            current_pac = event.get("pac_id")
            current_lane = event.get("lane")
        
        if event_type in ("TASK_START", "TASK_COMPLETE") and not latest_task:
            latest_task = event.get("task_title")
        
        if event_type == "BER_GENERATED" and not ber_score:
            ber_score = event.get("ber_score")
    
    # Display current state
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Current PAC", current_pac[:20] + "..." if current_pac and len(current_pac) > 20 else current_pac or "None")
    
    with col2:
        st.metric("Lane", current_lane or "—")
    
    with col3:
        st.metric("Latest Task", latest_task[:15] + "..." if latest_task and len(latest_task) > 15 else latest_task or "—")
    
    with col4:
        if ber_score is not None:
            color = "#4CAF50" if ber_score >= 90 else "#FF9800" if ber_score >= 70 else "#f44336"
            st.markdown(f"**BER Score**")
            st.markdown(f"<span class='ber-score' style='color:{color}'>{ber_score}/100</span>", unsafe_allow_html=True)
        else:
            st.metric("BER Score", "—")


def render_timeline(events: List[Dict[str, Any]]):
    """Render event timeline."""
    if not events:
        st.info("No heartbeat events yet. Waiting for execution...")
        return
    
    # Sort by sequence (most recent first)
    sorted_events = sorted(events, key=lambda e: e.get("sequence_number", 0), reverse=True)
    
    for event in sorted_events[:50]:  # Limit display
        render_event_card(event)


def render_event_card(event: Dict[str, Any]):
    """Render single event card."""
    event_type = event.get("event_type", "UNKNOWN")
    style = EVENT_STYLES.get(event_type, {"icon": "❓", "color": "#999", "label": event_type})
    
    # Format timestamp
    ts = event.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M:%S")
    except:
        time_str = ts[:19] if ts else "—"
    
    # Build content based on event type
    content_parts = []
    
    if event.get("pac_id"):
        content_parts.append(f"**PAC:** `{event['pac_id']}`")
    if event.get("pac_title"):
        content_parts.append(f"*{event['pac_title']}*")
    if event.get("task_id"):
        content_parts.append(f"**Task:** {event.get('task_title', event['task_id'])}")
    if event.get("agent_name"):
        content_parts.append(f"**Agent:** {event['agent_name']} ({event.get('agent_gid', '')})")
    if event.get("wrap_id"):
        content_parts.append(f"**WRAP:** `{event['wrap_id']}`")
    if event.get("ber_id"):
        content_parts.append(f"**BER:** `{event['ber_id']}` → **{event.get('ber_score', '?')}/100**")
    if event.get("lane"):
        content_parts.append(f"**Lane:** {event['lane']}")
    
    content = " | ".join(content_parts) if content_parts else "—"
    
    # Render card
    st.markdown(f"""
    <div class="heartbeat-event" style="border-left-color: {style['color']}; background: {style['color']}15;">
        <div class="event-header">
            <span>{style['icon']} <strong>{style['label']}</strong></span>
            <span class="event-time">#{event.get('sequence_number', '?')} | {time_str}</span>
        </div>
        <div style="margin-top: 5px; font-size: 0.9em;">
            {content}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_agent_grid(events: List[Dict[str, Any]]):
    """Render agent status grid."""
    # Extract agent states from events
    agents = {}
    
    for event in events:
        if event.get("agent_gid"):
            gid = event["agent_gid"]
            if gid not in agents:
                agents[gid] = {
                    "name": event.get("agent_name", gid),
                    "role": event.get("agent_role", "—"),
                    "status": "IDLE",
                    "last_event": event.get("event_type")
                }
            
            # Update status based on event
            if event.get("event_type") == "AGENT_ACTIVE":
                agents[gid]["status"] = "ACTIVE"
            elif event.get("event_type") == "AGENT_ATTESTED":
                agents[gid]["status"] = "ATTESTED"
    
    if not agents:
        # Show default agent roster
        default_agents = [
            ("GID-00", "BENSON", "Orchestrator"),
            ("GID-01", "CODY", "Backend"),
            ("GID-02", "SONNY", "API"),
            ("GID-03", "MIRA-R", "Docs"),
            ("GID-04", "CINDY", "Testing"),
            ("GID-05", "PAX", "Workflow"),
            ("GID-06", "SAM", "Security"),
            ("GID-07", "DAN", "CI/CD"),
            ("GID-08", "ALEX", "Logic"),
            ("GID-09", "LIRA", "UX"),
            ("GID-10", "MAGGIE", "AI Policy"),
            ("GID-11", "ATLAS", "Architecture"),
            ("GID-12", "DIGGI", "Audit"),
        ]
        for gid, name, role in default_agents:
            agents[gid] = {"name": name, "role": role, "status": "IDLE"}
    
    # Render 4-column grid
    cols = st.columns(4)
    for i, (gid, info) in enumerate(sorted(agents.items())):
        col = cols[i % 4]
        status_color = {
            "ACTIVE": "🟢",
            "ATTESTED": "✅",
            "IDLE": "⚪"
        }.get(info["status"], "⚪")
        
        with col:
            st.markdown(f"""
            <div style="padding: 8px; border-radius: 5px; background: #f5f5f5; margin: 3px 0; text-align: center;">
                <div>{status_color} <strong>{info['name']}</strong></div>
                <div style="font-size: 0.75em; color: #666;">{gid} | {info['role']}</div>
            </div>
            """, unsafe_allow_html=True)


# ==================== Standalone Entrypoint ====================

def main():
    """Run heartbeat panel as standalone Streamlit app."""
    st.set_page_config(
        page_title="OCC Heartbeat Monitor",
        page_icon="💓",
        layout="wide"
    )
    
    st.sidebar.title("⚙️ Settings")
    
    mode = st.sidebar.radio("Mode", ["Live API", "Mock Data"])
    use_mock = mode == "Mock Data"
    
    api_url = st.sidebar.text_input(
        "API Base URL",
        value="http://localhost:5001/api/v1/heartbeat"
    )
    
    refresh = st.sidebar.slider("Refresh (seconds)", 1, 30, 5)
    
    render_heartbeat_panel(
        api_base_url=api_url,
        use_mock=use_mock,
        auto_refresh=not use_mock,
        refresh_interval=refresh
    )


if __name__ == "__main__":
    main()
