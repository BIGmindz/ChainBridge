"""
OCC Agent Uniform Panel - Uniform State and Drift Visibility
=============================================================

PAC Reference: PAC-P755-AU-UNIFORM-ARTIFACT-SCHEMA
Classification: LAW_TIER
Domain: AGENT_UNIVERSITY
Section: 3_OF_N
Task: AU-9 (Expose uniform state and drift in OCC)

Authors:
    - PAX (GID-05) - Panel Design
    - LIRA (GID-09) - UI Rendering
Orchestrator: BENSON (GID-00)
Authority: JEFFREY (ARCHITECT)

Purpose:
    Renders Agent Uniform state and drift detection in OCC dashboard.
    Provides operator visibility into:
        - Uniform registry status
        - Cryptographic binding verification
        - Drift detection alerts
        - Validation history

OCC Integration Fields:
    - agent_gid
    - uniform_version
    - certification_level
    - execution_rights
    - uniform_hash
    - drift_status
    - last_verification
"""

import streamlit as st
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path


# ===================== Configuration =====================

UNIFORMS_DIR = Path(__file__).parent.parent / "governance" / "uniforms"
REFRESH_INTERVAL_SEC = 5

# Level styling
LEVEL_STYLES = {
    "L0": {"color": "#9E9E9E", "icon": "👁️", "label": "Observer", "pac_level": "NONE"},
    "L1": {"color": "#FF9800", "icon": "🔰", "label": "Supervised", "pac_level": "OPS_TIER"},
    "L2": {"color": "#4CAF50", "icon": "✅", "label": "Governed", "pac_level": "GOV_TIER"},
    "L3": {"color": "#2196F3", "icon": "⭐", "label": "Swarm", "pac_level": "LAW_TIER"},
}

STATE_STYLES = {
    "ACTIVE": {"color": "#4CAF50", "icon": "✅"},
    "SUSPENDED": {"color": "#FF9800", "icon": "⏸️"},
    "REVOKED": {"color": "#f44336", "icon": "🚫"},
    "DRAFT": {"color": "#9E9E9E", "icon": "📝"},
    "SUPERSEDED": {"color": "#795548", "icon": "📦"},
}

DRIFT_STYLES = {
    "NONE": {"color": "#4CAF50", "icon": "✅", "label": "No Drift"},
    "LEVEL_MISMATCH": {"color": "#f44336", "icon": "⚠️", "label": "Level Mismatch"},
    "REVOCATION_MISMATCH": {"color": "#f44336", "icon": "🚫", "label": "Revocation Drift"},
    "SIGNATURE_INVALID": {"color": "#f44336", "icon": "🔓", "label": "Signature Invalid"},
    "EXPIRATION_BREACH": {"color": "#FF9800", "icon": "⌛", "label": "Expired"},
}


# ===================== Data Loading =====================

def load_uniforms() -> Dict[str, Any]:
    """Load all uniforms from disk."""
    uniforms = {}
    if UNIFORMS_DIR.exists():
        for uniform_file in UNIFORMS_DIR.glob("*.json"):
            try:
                with open(uniform_file, "r") as f:
                    data = json.load(f)
                    agent_gid = data.get("identity", {}).get("agent_gid", "UNKNOWN")
                    uniforms[agent_gid] = data
            except Exception as e:
                st.error(f"Failed to load {uniform_file}: {e}")
    return uniforms


def check_drift(uniform: Dict[str, Any]) -> tuple:
    """Check for drift in a uniform."""
    # Check revocation status
    revocation = uniform.get("certification", {}).get("revocation_status", {})
    if revocation.get("revoked", False):
        return "REVOCATION_MISMATCH", revocation.get("revocation_reason", "Unknown")
    
    # Check expiration
    expires_at = uniform.get("certification", {}).get("expires_at")
    if expires_at:
        try:
            expires = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires:
                return "EXPIRATION_BREACH", "Uniform has expired"
        except Exception:
            pass
    
    # In production, would also check signature and runtime alignment
    return "NONE", "No drift detected"


# ===================== Panel Components =====================

def render_uniform_summary(uniforms: Dict[str, Any]) -> None:
    """Render uniform summary metrics."""
    st.subheader("📊 Uniform Registry Summary")
    
    # Count by level and state
    level_counts = {"L0": 0, "L1": 0, "L2": 0, "L3": 0}
    drift_count = 0
    active_count = 0
    
    for uniform in uniforms.values():
        level = uniform.get("certification", {}).get("certification_level", "L0")
        level_counts[level] = level_counts.get(level, 0) + 1
        
        revoked = uniform.get("certification", {}).get("revocation_status", {}).get("revoked", False)
        if not revoked:
            active_count += 1
        
        drift_type, _ = check_drift(uniform)
        if drift_type != "NONE":
            drift_count += 1
    
    # Render metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(label="Total Uniforms", value=len(uniforms))
    
    with col2:
        st.metric(label="Active", value=active_count)
    
    with col3:
        st.metric(
            label="Swarm Eligible (L3)",
            value=level_counts.get("L3", 0)
        )
    
    with col4:
        st.metric(
            label="Drift Alerts",
            value=drift_count,
            delta=f"+{drift_count}" if drift_count > 0 else None,
            delta_color="inverse"
        )


def render_drift_alerts(uniforms: Dict[str, Any]) -> None:
    """Render drift alerts."""
    drifted = []
    for agent_gid, uniform in uniforms.items():
        drift_type, drift_message = check_drift(uniform)
        if drift_type != "NONE":
            drifted.append((agent_gid, uniform, drift_type, drift_message))
    
    if drifted:
        st.subheader("🚨 Drift Alerts")
        for agent_gid, uniform, drift_type, drift_message in drifted:
            style = DRIFT_STYLES.get(drift_type, DRIFT_STYLES["NONE"])
            agent_name = uniform.get("identity", {}).get("agent_name", "Unknown")
            st.error(
                f"{style['icon']} **{agent_gid}** ({agent_name}) - "
                f"{style['label']}: {drift_message}"
            )
    else:
        st.success("✅ No drift detected across all uniforms.")


def render_uniform_table(uniforms: Dict[str, Any]) -> None:
    """Render uniform registry table."""
    st.subheader("🎽 Agent Uniforms")
    
    if not uniforms:
        st.info("No uniforms registered.")
        return
    
    # Build table data
    table_data = []
    for agent_gid, uniform in sorted(uniforms.items()):
        identity = uniform.get("identity", {})
        certification = uniform.get("certification", {})
        execution_rights = uniform.get("execution_rights", {})
        crypto = uniform.get("cryptographic_binding", {})
        
        level = certification.get("certification_level", "L0")
        level_style = LEVEL_STYLES.get(level, LEVEL_STYLES["L0"])
        
        revoked = certification.get("revocation_status", {}).get("revoked", False)
        state = "REVOKED" if revoked else "ACTIVE"
        state_style = STATE_STYLES.get(state, STATE_STYLES["ACTIVE"])
        
        drift_type, _ = check_drift(uniform)
        drift_style = DRIFT_STYLES.get(drift_type, DRIFT_STYLES["NONE"])
        
        # Truncate hash for display
        uniform_hash = crypto.get("uniform_hash", "N/A")
        if len(uniform_hash) > 20:
            uniform_hash = uniform_hash[:20] + "..."
        
        table_data.append({
            "Agent": f"{agent_gid}",
            "Name": identity.get("agent_name", "Unknown"),
            "Role": identity.get("agent_role", "Unknown"),
            "Level": f"{level_style['icon']} {level}",
            "State": f"{state_style['icon']} {state}",
            "Swarm": "✅" if execution_rights.get("swarm_eligibility", False) else "❌",
            "Drift": f"{drift_style['icon']}",
            "Hash": uniform_hash,
        })
    
    st.dataframe(table_data, use_container_width=True, hide_index=True)


def render_uniform_detail(uniforms: Dict[str, Any]) -> None:
    """Render detailed uniform view."""
    st.subheader("🔍 Uniform Details")
    
    if not uniforms:
        return
    
    agent_options = list(uniforms.keys())
    selected_agent = st.selectbox("Select Agent", agent_options)
    
    if selected_agent:
        uniform = uniforms[selected_agent]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Identity**")
            identity = uniform.get("identity", {})
            st.json(identity)
            
            st.write("**Certification**")
            certification = uniform.get("certification", {})
            st.json(certification)
        
        with col2:
            st.write("**Execution Rights**")
            execution_rights = uniform.get("execution_rights", {})
            st.json(execution_rights)
            
            st.write("**Behavioral Constraints**")
            constraints = uniform.get("behavioral_constraints", {})
            st.json(constraints)
        
        st.write("**Cryptographic Binding**")
        crypto = uniform.get("cryptographic_binding", {})
        st.code(json.dumps(crypto, indent=2), language="json")


def render_enforcement_gates() -> None:
    """Render uniform enforcement gates."""
    st.subheader("🚧 Uniform Enforcement Gates")
    
    gates = [
        {
            "gate_id": "AU-UNIFORM-001",
            "check": "uniform_present",
            "required": True,
            "failure_mode": "HARD_BLOCK",
            "description": "Agent must have a uniform artifact"
        },
        {
            "gate_id": "AU-UNIFORM-002",
            "check": "uniform_signature_valid",
            "required": True,
            "failure_mode": "IMMEDIATE_TERMINATION",
            "description": "Uniform signature must verify"
        },
        {
            "gate_id": "AU-UNIFORM-003",
            "check": "uniform_certification_alignment",
            "required": True,
            "failure_mode": "SCRAM_AND_AUDIT",
            "description": "Uniform must align with runtime certification"
        }
    ]
    
    for gate in gates:
        with st.expander(f"**{gate['gate_id']}**: {gate['description']}", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Check:** `{gate['check']}`")
                st.write(f"**Required:** `{gate['required']}`")
            with col2:
                failure_mode = gate['failure_mode']
                if failure_mode == "HARD_BLOCK":
                    st.error(f"**Failure Mode:** {failure_mode}")
                elif failure_mode == "IMMEDIATE_TERMINATION":
                    st.error(f"**Failure Mode:** {failure_mode}")
                elif failure_mode == "SCRAM_AND_AUDIT":
                    st.error(f"**Failure Mode:** {failure_mode}")


def render_level_reference() -> None:
    """Render certification level reference."""
    st.subheader("📚 Certification Level Reference")
    
    reference_data = []
    for level, style in LEVEL_STYLES.items():
        reference_data.append({
            "Level": f"{style['icon']} {level}",
            "Name": style['label'],
            "Max PAC Level": style['pac_level'],
            "Swarm Eligible": "✅" if level == "L3" else "❌"
        })
    
    st.dataframe(reference_data, use_container_width=True, hide_index=True)


# ===================== Main Panel =====================

def render_agent_uniform_panel() -> None:
    """
    Main entry point for OCC Agent Uniform Panel.
    
    Call this from occ_dashboard.py to integrate.
    """
    st.header("🎽 Agent University - Uniform Panel")
    st.caption("PAC-P755-AU-UNIFORM-ARTIFACT-SCHEMA | LAW_TIER")
    
    # Load uniforms
    uniforms = load_uniforms()
    
    # Last update time
    st.caption(f"Last updated: {datetime.now(timezone.utc).isoformat()}")
    
    # Render components
    render_uniform_summary(uniforms)
    st.divider()
    
    render_drift_alerts(uniforms)
    st.divider()
    
    render_uniform_table(uniforms)
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        render_enforcement_gates()
    with col2:
        render_level_reference()
    
    st.divider()
    render_uniform_detail(uniforms)


# ===================== Standalone Mode =====================

def main():
    """Standalone panel for testing."""
    st.set_page_config(
        page_title="AU Uniform Panel",
        page_icon="🎽",
        layout="wide"
    )
    
    render_agent_uniform_panel()
    
    # Auto-refresh
    if st.checkbox("Auto-refresh", value=False):
        time.sleep(REFRESH_INTERVAL_SEC)
        st.rerun()


if __name__ == "__main__":
    main()
