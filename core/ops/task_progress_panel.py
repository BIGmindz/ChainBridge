"""
Task Progress Panel - OCC Dashboard Component
=============================================

PAC Reference: PAC-P746-GOV-TASK-PROGRESSION-VISIBILITY
Classification: LAW_TIER
Authors:
    - PAX (GID-05) - Progress UX
    - LIRA (GID-09) - UI Rendering
Orchestrator: BENSON (GID-00)

Renders real-time task progression in OCC UI (Streamlit).
"""

import streamlit as st
import json
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


# ==================== Task State Styling ====================

TASK_STATE_STYLES = {
    "DECLARED": {"icon": "📋", "color": "#9E9E9E", "label": "Declared"},
    "IN_PROGRESS": {"icon": "⚡", "color": "#FF9800", "label": "In Progress"},
    "BLOCKED": {"icon": "🚫", "color": "#F44336", "label": "Blocked"},
    "COMPLETE": {"icon": "✅", "color": "#4CAF50", "label": "Complete"},
    "FAILED": {"icon": "❌", "color": "#f44336", "label": "Failed"},
}


# ==================== Mock Data ====================

MOCK_MANIFEST = {
    "manifest_id": "MANIFEST-PAC-P746-GOV-TASK-PROGRESSION-VISIBILITY",
    "pac_id": "PAC-P746-GOV-TASK-PROGRESSION-VISIBILITY",
    "declared_at": "2026-01-13T19:35:00Z",
    "execution_order": "SEQUENTIAL",
    "total_tasks": 4,
    "completed_tasks": 2,
    "failed_tasks": 0,
    "in_progress_tasks": 1,
    "progress_percent": 50.0,
    "is_complete": False,
    "tasks": [
        {
            "task_id": "TASK-01",
            "title": "Define canonical task manifest schema",
            "status": "COMPLETE",
            "assigned_agent": "GID-03",
            "artifact": "schemas/task_manifest.json",
            "duration_ms": 45000
        },
        {
            "task_id": "TASK-02",
            "title": "Bind task states to heartbeat emitter",
            "status": "COMPLETE",
            "assigned_agent": "GID-01",
            "artifact": "ChainBridge/core/orchestration/task_tracker.py",
            "duration_ms": 60000
        },
        {
            "task_id": "TASK-03",
            "title": "Expose task progress in OCC UI",
            "status": "IN_PROGRESS",
            "assigned_agent": "GID-05",
            "artifact": "core/ops/task_progress_panel.py"
        },
        {
            "task_id": "TASK-04",
            "title": "Require task manifest in all future PACs",
            "status": "DECLARED",
            "assigned_agent": "GID-06",
            "artifact": "core/governance/TASK_MANIFEST_POLICY.json"
        }
    ]
}


# ==================== Task Progress Panel ====================

def render_task_progress_panel(
    api_base_url: str = "http://localhost:5001/api/v1/tasks",
    use_mock: bool = True,
    pac_id: Optional[str] = None
):
    """
    Render the task progress panel for OCC dashboard.
    
    Args:
        api_base_url: Base URL for task API
        use_mock: Use mock data
        pac_id: Filter to specific PAC
    """
    st.markdown("""
    <style>
    .task-card {
        padding: 12px 15px;
        margin: 8px 0;
        border-radius: 8px;
        border-left: 5px solid;
    }
    .task-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .task-meta {
        font-size: 0.85em;
        color: #666;
        margin-top: 5px;
    }
    .progress-bar-container {
        background: #e0e0e0;
        border-radius: 10px;
        height: 20px;
        overflow: hidden;
    }
    .progress-bar {
        height: 100%;
        border-radius: 10px;
        transition: width 0.3s ease;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("## 📊 Task Progression")
    
    # Fetch data
    if use_mock:
        manifest = MOCK_MANIFEST
    else:
        manifest = fetch_manifest(api_base_url, pac_id)
    
    if not manifest:
        st.warning("No task manifest found")
        return
    
    # Progress overview
    render_progress_overview(manifest)
    
    st.divider()
    
    # Task list
    st.markdown("### 📋 Task Manifest")
    render_task_list(manifest.get("tasks", []))
    
    # State machine diagram
    st.divider()
    st.markdown("### 🔄 State Machine")
    render_state_machine()


def fetch_manifest(api_base_url: str, pac_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Fetch manifest from API."""
    try:
        url = f"{api_base_url}/manifest"
        if pac_id:
            url += f"?pac_id={pac_id}"
        resp = requests.get(url, timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


def render_progress_overview(manifest: Dict[str, Any]):
    """Render progress overview section."""
    col1, col2, col3, col4 = st.columns(4)
    
    total = manifest.get("total_tasks", 0)
    completed = manifest.get("completed_tasks", 0)
    failed = manifest.get("failed_tasks", 0)
    progress = manifest.get("progress_percent", 0)
    
    with col1:
        st.metric("Total Tasks", total)
    with col2:
        st.metric("Completed", completed, delta=None)
    with col3:
        st.metric("Failed", failed, delta=None if failed == 0 else f"-{failed}")
    with col4:
        st.metric("Progress", f"{progress:.0f}%")
    
    # Progress bar
    progress_color = "#4CAF50" if progress >= 100 else "#FF9800" if progress >= 50 else "#2196F3"
    st.markdown(f"""
    <div class="progress-bar-container">
        <div class="progress-bar" style="width: {progress}%; background: {progress_color};"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # PAC info
    st.caption(f"**PAC:** `{manifest.get('pac_id', 'Unknown')}` | **Execution:** {manifest.get('execution_order', 'SEQUENTIAL')}")


def render_task_list(tasks: List[Dict[str, Any]]):
    """Render list of tasks."""
    if not tasks:
        st.info("No tasks declared")
        return
    
    for task in tasks:
        render_task_card(task)


def render_task_card(task: Dict[str, Any]):
    """Render single task card."""
    status = task.get("status", "DECLARED")
    style = TASK_STATE_STYLES.get(status, TASK_STATE_STYLES["DECLARED"])
    
    task_id = task.get("task_id", "TASK-?")
    title = task.get("title", "Untitled")
    agent = task.get("assigned_agent", "—")
    artifact = task.get("artifact", "—")
    duration = task.get("duration_ms")
    
    # Format duration
    duration_str = ""
    if duration:
        if duration >= 60000:
            duration_str = f" | ⏱️ {duration // 60000}m {(duration % 60000) // 1000}s"
        else:
            duration_str = f" | ⏱️ {duration // 1000}s"
    
    st.markdown(f"""
    <div class="task-card" style="border-left-color: {style['color']}; background: {style['color']}10;">
        <div class="task-header">
            <span><strong>{task_id}</strong>: {title}</span>
            <span>{style['icon']} {style['label']}</span>
        </div>
        <div class="task-meta">
            🤖 {agent} | 📁 <code>{artifact}</code>{duration_str}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_state_machine():
    """Render state machine diagram."""
    st.markdown("""
    ```
    ┌──────────┐
    │ DECLARED │
    └────┬─────┘
         │
         ▼
    ┌─────────────┐     ┌─────────┐
    │ IN_PROGRESS │◄────│ BLOCKED │
    └──────┬──────┘     └────┬────┘
           │                 │
           ▼                 │
    ┌──────────┐            │
    │ COMPLETE │            │
    └──────────┘            │
           ▲                │
           │                ▼
    ┌──────────┐      ┌────────┐
    │  FAILED  │◄─────│ FAILED │
    └──────────┘      └────────┘
    ```
    
    **Valid Transitions:**
    - `DECLARED` → `IN_PROGRESS`, `BLOCKED`
    - `IN_PROGRESS` → `COMPLETE`, `FAILED`, `BLOCKED`
    - `BLOCKED` → `IN_PROGRESS`, `FAILED`
    - `COMPLETE` → *(terminal)*
    - `FAILED` → *(terminal)*
    """)


# ==================== Agent Task Assignment View ====================

def render_agent_task_view(manifest: Dict[str, Any]):
    """Render tasks grouped by assigned agent."""
    tasks = manifest.get("tasks", [])
    
    # Group by agent
    by_agent: Dict[str, List[Dict]] = {}
    for task in tasks:
        agent = task.get("assigned_agent", "Unassigned")
        if agent not in by_agent:
            by_agent[agent] = []
        by_agent[agent].append(task)
    
    st.markdown("### 🤖 Tasks by Agent")
    
    cols = st.columns(min(4, len(by_agent)))
    for i, (agent, agent_tasks) in enumerate(sorted(by_agent.items())):
        col = cols[i % len(cols)]
        with col:
            completed = sum(1 for t in agent_tasks if t.get("status") == "COMPLETE")
            st.markdown(f"**{agent}** ({completed}/{len(agent_tasks)})")
            for task in agent_tasks:
                status = task.get("status", "DECLARED")
                style = TASK_STATE_STYLES.get(status, {})
                icon = style.get("icon", "❓")
                st.caption(f"{icon} {task.get('task_id')}")


# ==================== Standalone Entrypoint ====================

def main():
    """Run task progress panel as standalone Streamlit app."""
    st.set_page_config(
        page_title="OCC Task Progress",
        page_icon="📊",
        layout="wide"
    )
    
    st.sidebar.title("⚙️ Settings")
    
    mode = st.sidebar.radio("Mode", ["Mock Data", "Live API"])
    use_mock = mode == "Mock Data"
    
    api_url = st.sidebar.text_input(
        "API Base URL",
        value="http://localhost:5001/api/v1/tasks"
    )
    
    render_task_progress_panel(
        api_base_url=api_url,
        use_mock=use_mock
    )
    
    # Agent view
    if use_mock:
        st.divider()
        render_agent_task_view(MOCK_MANIFEST)


if __name__ == "__main__":
    main()
