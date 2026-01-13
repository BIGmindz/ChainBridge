"""
OCC Agent Certification Panel - Agent University Visibility
============================================================

PAC Reference: PAC-P754-AU-ENFORCEMENT-RUNTIME
Classification: LAW_TIER
Domain: AGENT_UNIVERSITY
Task: AU-6 (Expose certification state in OCC)

Authors:
    - PAX (GID-05) - Panel Design
    - LIRA (GID-09) - UI Rendering
Orchestrator: BENSON (GID-00)
Authority: JEFFREY (ARCHITECT)

Purpose:
    Renders Agent University certification state in OCC dashboard.
    Provides operator visibility into:
        - Agent certification levels
        - Certification status
        - Revocation events
        - Enforcement decisions

OCC Integration Fields:
    - agent_id
    - certification_level
    - certification_status
    - revocation_reason
    - last_audit_timestamp
"""

import streamlit as st
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


# ===================== Configuration =====================

RUNTIME_STATE_FILE = Path(__file__).parent / "agent_certification_runtime_state.json"
REFRESH_INTERVAL_SEC = 5

# Level styling
LEVEL_STYLES = {
    "L0": {"color": "#9E9E9E", "icon": "👁️", "label": "Observer"},
    "L1": {"color": "#FF9800", "icon": "🔰", "label": "Supervised"},
    "L2": {"color": "#4CAF50", "icon": "✅", "label": "Governed"},
    "L3": {"color": "#2196F3", "icon": "⭐", "label": "Swarm"},
}

STATUS_STYLES = {
    "ACTIVE": {"color": "#4CAF50", "icon": "✅"},
    "SUSPENDED": {"color": "#FF9800", "icon": "⏸️"},
    "REVOKED": {"color": "#f44336", "icon": "🚫"},
    "PENDING": {"color": "#9E9E9E", "icon": "⏳"},
    "EXPIRED": {"color": "#795548", "icon": "⌛"},
}


# ===================== Data Loading =====================

def load_runtime_state() -> Dict[str, Any]:
    """Load certification runtime state."""
    if RUNTIME_STATE_FILE.exists():
        try:
            with open(RUNTIME_STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Failed to load runtime state: {e}")
    return {"certifications": {}, "enforcement_gates": {}}


def load_enforcement_log() -> List[Dict[str, Any]]:
    """Load recent enforcement decisions from enforcer (mock for standalone)."""
    # In production, this would query the enforcer's log
    return [
        {
            "agent_id": "GID-01",
            "result": "PASSED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_allowed": True
        }
    ]


# ===================== Panel Components =====================

def render_certification_summary(state: Dict[str, Any]) -> None:
    """Render certification summary metrics."""
    certs = state.get("certifications", {})
    
    # Count by level
    level_counts = {"L0": 0, "L1": 0, "L2": 0, "L3": 0}
    status_counts = {"ACTIVE": 0, "SUSPENDED": 0, "REVOKED": 0, "PENDING": 0}
    
    for cert in certs.values():
        level = cert.get("certification_level", "L0")
        status = cert.get("certification_status", "PENDING")
        level_counts[level] = level_counts.get(level, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Render metrics
    st.subheader("📊 Certification Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Agents",
            value=len(certs),
            delta=None
        )
    
    with col2:
        st.metric(
            label="Active",
            value=status_counts.get("ACTIVE", 0),
            delta=None
        )
    
    with col3:
        st.metric(
            label="Swarm Eligible (L3)",
            value=level_counts.get("L3", 0),
            delta=None
        )
    
    with col4:
        revoked = status_counts.get("REVOKED", 0)
        st.metric(
            label="Revoked",
            value=revoked,
            delta=f"+{revoked}" if revoked > 0 else None,
            delta_color="inverse"
        )


def render_certification_table(state: Dict[str, Any]) -> None:
    """Render certification table."""
    st.subheader("🎓 Agent Certifications")
    
    certs = state.get("certifications", {})
    
    if not certs:
        st.info("No certifications registered.")
        return
    
    # Build table data
    table_data = []
    for agent_id, cert in sorted(certs.items()):
        level = cert.get("certification_level", "L0")
        status = cert.get("certification_status", "PENDING")
        
        level_style = LEVEL_STYLES.get(level, LEVEL_STYLES["L0"])
        status_style = STATUS_STYLES.get(status, STATUS_STYLES["PENDING"])
        
        table_data.append({
            "Agent ID": agent_id,
            "Name": cert.get("agent_name", "Unknown"),
            "Role": cert.get("agent_role", "Unknown"),
            "Level": f"{level_style['icon']} {level} ({level_style['label']})",
            "Status": f"{status_style['icon']} {status}",
            "Revoked": "🚫 YES" if cert.get("revocation_flag", False) else "✅ NO",
            "Last Audit": cert.get("last_audit_timestamp", "Never")[:19],
        })
    
    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True
    )


def render_enforcement_gates(state: Dict[str, Any]) -> None:
    """Render enforcement gate status."""
    st.subheader("🚧 Enforcement Gates")
    
    gates = state.get("enforcement_gates", {})
    
    if not gates:
        st.warning("No enforcement gates configured.")
        return
    
    for gate_id, gate in gates.items():
        with st.expander(f"**{gate_id}**: {gate.get('description', 'No description')}", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Check:** `{gate.get('check', 'N/A')}`")
                st.write(f"**Required:** `{gate.get('required', 'N/A')}`")
            with col2:
                failure_mode = gate.get('failure_mode', 'UNKNOWN')
                if failure_mode == "HARD_BLOCK":
                    st.error(f"**Failure Mode:** {failure_mode}")
                elif failure_mode == "IMMEDIATE_TERMINATION":
                    st.error(f"**Failure Mode:** {failure_mode}")
                elif failure_mode == "SCRAM_AND_AUDIT":
                    st.error(f"**Failure Mode:** {failure_mode}")
                else:
                    st.warning(f"**Failure Mode:** {failure_mode}")


def render_revocation_alerts(state: Dict[str, Any]) -> None:
    """Render revocation alerts."""
    certs = state.get("certifications", {})
    revoked = [
        (agent_id, cert) 
        for agent_id, cert in certs.items() 
        if cert.get("revocation_flag", False)
    ]
    
    if revoked:
        st.subheader("🚨 Revocation Alerts")
        for agent_id, cert in revoked:
            st.error(
                f"**{agent_id}** ({cert.get('agent_name', 'Unknown')}) - "
                f"REVOKED: {cert.get('revocation_reason', 'No reason provided')}"
            )
    else:
        st.success("No active revocations.")


def render_active_executions(state: Dict[str, Any]) -> None:
    """Render active execution tracking."""
    st.subheader("⚡ Active Executions")
    
    executions = state.get("active_executions", {})
    
    if not executions:
        st.info("No active executions.")
        return
    
    for agent_id, execution_id in executions.items():
        cert = state.get("certifications", {}).get(agent_id, {})
        st.write(
            f"**{agent_id}** ({cert.get('agent_name', 'Unknown')}): "
            f"`{execution_id}`"
        )


def render_enforcement_log() -> None:
    """Render recent enforcement decisions."""
    st.subheader("📜 Recent Enforcement Decisions")
    
    log = load_enforcement_log()
    
    if not log:
        st.info("No enforcement decisions logged.")
        return
    
    for entry in log[-10:]:  # Last 10 entries
        result = entry.get("result", "UNKNOWN")
        icon = "✅" if result == "PASSED" else "🚫"
        st.write(
            f"{icon} **{entry.get('agent_id', 'N/A')}** - "
            f"{result} at {entry.get('timestamp', 'N/A')[:19]}"
        )


def render_governance_config(state: Dict[str, Any]) -> None:
    """Render governance configuration."""
    st.subheader("⚙️ Governance Configuration")
    
    governance = state.get("governance", {})
    
    col1, col2 = st.columns(2)
    
    with col1:
        fail_mode = governance.get("fail_mode", "UNKNOWN")
        if fail_mode == "CLOSED":
            st.success(f"**Fail Mode:** {fail_mode}")
        else:
            st.warning(f"**Fail Mode:** {fail_mode}")
        
        st.write(f"**Default Decision:** {governance.get('default_decision', 'UNKNOWN')}")
    
    with col2:
        st.write(f"**Human Override Requires:** {governance.get('human_override_requires', 'N/A')}")
        
        audit = governance.get("audit_all_decisions", False)
        if audit:
            st.success("**Audit All Decisions:** Enabled")
        else:
            st.warning("**Audit All Decisions:** Disabled")


# ===================== Main Panel =====================

def render_agent_certification_panel() -> None:
    """
    Main entry point for OCC Agent Certification Panel.
    
    Call this from occ_dashboard.py to integrate.
    """
    st.header("🎓 Agent University - Certification Panel")
    st.caption("PAC-P754-AU-ENFORCEMENT-RUNTIME | LAW_TIER")
    
    # Load state
    state = load_runtime_state()
    
    # Last update time
    last_updated = state.get("last_updated", "Unknown")
    st.caption(f"Last updated: {last_updated}")
    
    # Render components
    render_certification_summary(state)
    st.divider()
    
    render_revocation_alerts(state)
    st.divider()
    
    render_certification_table(state)
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        render_enforcement_gates(state)
    with col2:
        render_active_executions(state)
    
    st.divider()
    render_enforcement_log()
    
    st.divider()
    render_governance_config(state)


# ===================== Standalone Mode =====================

def main():
    """Standalone panel for testing."""
    st.set_page_config(
        page_title="AU Certification Panel",
        page_icon="🎓",
        layout="wide"
    )
    
    render_agent_certification_panel()
    
    # Auto-refresh
    if st.checkbox("Auto-refresh", value=False):
        time.sleep(REFRESH_INTERVAL_SEC)
        st.rerun()


if __name__ == "__main__":
    main()
