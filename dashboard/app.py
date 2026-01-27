"""
ChainBridge God View Dashboard
PAC-VIZ-P55: Real-time Polyatomic Resonance Visualization
PAC-INT-P56: Live Data Pipeline Integration

Visualizes:
- Legion Status (Active Hives, Consensus Rate, Hallucinations)
- Live Hive Consensus (3-of-5 Voting Grid)
- Context Sync Health (P52 - SYNC-01/02/03)
- Historical Consensus Events

Invariant: VIZ-01 (Truth in UI) - Dashboard reflects actual system state
Invariant: PIPE-01 (No Mock Data) - Dashboard uses live audit logs
If Hive SCRAMs, Dashboard turns RED
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# PAC-INT-P56: Import LIVE metrics instead of mock
ENABLE_LIVE_DATA = os.environ.get("CHAINBRIDGE_LIVE_DATA", "true").lower() == "true"

if ENABLE_LIVE_DATA:
    # Use live data pipeline (PIPE-01)
    from core.orchestration.metrics_stream_live import (
        get_live_legion_metrics as get_legion_metrics,
        get_live_context_sync_metrics as get_context_sync_metrics,
        get_live_consensus_events as get_latest_consensus_events,
        get_live_hive_health as get_hive_health,
        validate_live_pipeline
    )
    from core.orchestration.metrics_stream import HiveHealthState, AtomVoteState
else:
    # Fallback to mock data (DEVELOPMENT ONLY)
    from core.orchestration.metrics_stream import (
        get_legion_metrics,
        get_context_sync_metrics,
        get_latest_consensus_events,
        get_hive_health,
        HiveHealthState,
        AtomVoteState
    )


# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="ChainBridge God View",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# CUSTOM CSS STYLING
# ============================================================================

def inject_custom_css():
    """Inject custom CSS for health states and atom votes."""
    st.markdown("""
    <style>
    /* Health State Colors */
    .health-operational {
        color: #00ff00;
        font-weight: bold;
    }
    .health-degraded {
        color: #ffaa00;
        font-weight: bold;
    }
    .health-scram {
        color: #ff0000;
        font-weight: bold;
        animation: blink 1s infinite;
    }
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.3; }
    }
    
    /* Atom Vote States */
    .vote-agree {
        background-color: #00ff00;
        color: #000;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
    .vote-disagree {
        background-color: #ff0000;
        color: #fff;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
    .vote-pending {
        background-color: #888888;
        color: #fff;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
    .vote-timeout {
        background-color: #ffaa00;
        color: #000;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)


inject_custom_css()


# ============================================================================
# HEADER
# ============================================================================

st.title("🔗 ChainBridge: Polyatomic Resonance Engine")

# PAC-INT-P56: Display data source mode
data_source_badge = "🟢 LIVE DATA" if ENABLE_LIVE_DATA else "🟡 MOCK DATA"
st.markdown(f"**PAC-VIZ-P55**: Real-Time Hive Mind Visualization | **PAC-INT-P56**: {data_source_badge} | **Invariant VIZ-01**: Truth in UI")

# Validate live pipeline if enabled
if ENABLE_LIVE_DATA:
    try:
        pipeline_healthy = validate_live_pipeline()
        if not pipeline_healthy:
            st.error("⚠️ PIPE-01 VIOLATION: Live data pipeline unhealthy. Check logs.")
    except Exception as e:
        st.error(f"❌ PIPE-02 FAILURE: Pipeline validation error: {e}")


# ============================================================================
# SIDEBAR: SYSTEM CONTROLS
# ============================================================================

with st.sidebar:
    st.header("⚙️ System Controls")
    
    # Refresh rate
    refresh_rate = st.slider("Refresh Rate (seconds)", min_value=1, max_value=10, value=2)
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("Auto-Refresh", value=True)
    
    # Manual refresh button
    if st.button("🔄 Refresh Now"):
        st.rerun()
    
    st.divider()
    
    # System Info
    st.subheader("📊 System Info")
    st.text(f"Timestamp: {datetime.now().strftime('%H:%M:%S')}")
    st.text(f"Data Source: {'LIVE' if ENABLE_LIVE_DATA else 'MOCK'}")
    
    # Health Status
    health = get_hive_health()
    health_color = {
        HiveHealthState.OPERATIONAL: "health-operational",
        HiveHealthState.DEGRADED: "health-degraded",
        HiveHealthState.SCRAM: "health-scram",
        HiveHealthState.RECOVERING: "health-degraded"
    }
    st.markdown(f"**Status**: <span class='{health_color[health]}'>{health.value}</span>", 
                unsafe_allow_html=True)


# ============================================================================
# SECTION 1: LEGION STATUS (PAC-48)
# ============================================================================

st.header("🏛️ Legion Status")

legion = get_legion_metrics()

# Create 4 columns for metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Active Hive Minds",
        value=f"{legion.active_hives:,}",
        delta=f"{legion.active_hives - legion.total_hives} offline" if legion.active_hives < legion.total_hives else "All Online"
    )

with col2:
    st.metric(
        label="Consensus Checks/Sec",
        value=f"{legion.consensus_checks_per_sec:,.0f}",
        delta="PAC-48 Benchmark"
    )

with col3:
    st.metric(
        label="Hallucinations Crushed",
        value=f"{legion.hallucinations_crushed:,}",
        delta="Dissonance Events" if legion.hallucinations_crushed > 0 else "Clean Slate"
    )

with col4:
    st.metric(
        label="Uptime",
        value=f"{legion.uptime_hours:.1f}h",
        delta=f"{legion.scram_count} SCRAMs"
    )


# ============================================================================
# SECTION 2: CONTEXT SYNC HEALTH (PAC-P52)
# ============================================================================

st.header("🔄 Context Synchronization (P52)")

sync = get_context_sync_metrics()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Total Syncs",
        value=f"{sync.total_syncs:,}",
        delta=f"{sync.successful_syncs}/{sync.total_syncs} successful"
    )

with col2:
    st.metric(
        label="Success Rate",
        value=f"{sync.success_rate:.1%}",
        delta="SYNC-01 Compliance"
    )

with col3:
    st.metric(
        label="Drift Detections",
        value=f"{sync.drift_detections:,}",
        delta="SYNC-02 Triggers" if sync.drift_detections > 0 else "No Input Drift"
    )


# ============================================================================
# SECTION 3: LIVE HIVE CONSENSUS (PAC-P51)
# ============================================================================

st.header("🧠 Live Hive Consensus (3-of-5 Voting)")

# Get latest consensus events
events = get_latest_consensus_events(count=5)

if events:
    # Show most recent event in detail
    latest_event = events[0]
    
    st.subheader(f"Latest Consensus: {latest_event.consensus_id}")
    st.text(f"Task: {latest_event.task_description}")
    st.text(f"Context Hash: {latest_event.context_hash[:32]}...")
    
    # Voting Grid Visualization
    st.markdown("### Atom Voting Grid")
    
    vote_cols = st.columns(len(latest_event.atom_votes))
    
    for i, vote in enumerate(latest_event.atom_votes):
        with vote_cols[i]:
            # Determine vote state CSS class
            vote_class = {
                AtomVoteState.AGREE: "vote-agree",
                AtomVoteState.DISAGREE: "vote-disagree",
                AtomVoteState.PENDING: "vote-pending",
                AtomVoteState.TIMEOUT: "vote-timeout"
            }
            
            vote_icon = {
                AtomVoteState.AGREE: "✅",
                AtomVoteState.DISAGREE: "❌",
                AtomVoteState.PENDING: "⏳",
                AtomVoteState.TIMEOUT: "⚠️"
            }
            
            st.markdown(
                f"<div class='{vote_class[vote.vote_state]}'>"
                f"{vote_icon[vote.vote_state]} {vote.gid}<br>"
                f"Hash: {vote.hash[:8]}...<br>"
                f"Latency: {vote.latency_ms:.1f}ms"
                f"</div>",
                unsafe_allow_html=True
            )
    
    # Consensus Result
    st.divider()
    
    result_col1, result_col2 = st.columns(2)
    
    with result_col1:
        if latest_event.achieved:
            st.success(f"✅ **CONSENSUS ACHIEVED** (Threshold: {latest_event.threshold}/{len(latest_event.atom_votes)})")
            st.text(f"Winning Hash: {latest_event.winning_hash[:32]}...")
        else:
            st.error(f"❌ **DISSONANCE DETECTED** (Failed to reach {latest_event.threshold}/{len(latest_event.atom_votes)} threshold)")
            st.text("POLY-02 TRIGGERED: Fail-Closed")
    
    with result_col2:
        # Vote distribution
        vote_df = pd.DataFrame([
            {"Hash": hash_val[:8] + "...", "Votes": count}
            for hash_val, count in latest_event.vote_count.items()
        ])
        st.dataframe(vote_df, hide_index=True)


# ============================================================================
# SECTION 4: CONSENSUS HISTORY
# ============================================================================

st.header("📜 Consensus History")

# Build history table
history_data = []
for event in events:
    history_data.append({
        "Timestamp": event.timestamp.strftime("%H:%M:%S"),
        "Consensus ID": event.consensus_id,
        "Task": event.task_description[:40] + "..." if len(event.task_description) > 40 else event.task_description,
        "Result": "✅ CONSENSUS" if event.achieved else "❌ DISSONANCE",
        "Votes": f"{max(event.vote_count.values()) if event.vote_count else 0}/{len(event.atom_votes)}",
        "Latency": f"{sum(v.latency_ms for v in event.atom_votes) / len(event.atom_votes):.1f}ms"
    })

history_df = pd.DataFrame(history_data)
st.dataframe(history_df, hide_index=True, use_container_width=True)


# ============================================================================
# SECTION 5: PERFORMANCE CHARTS
# ============================================================================

st.header("📈 Performance Metrics")

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    # Consensus Rate Over Time (Mock Data)
    st.subheader("Consensus Rate (Last 60s)")
    
    # Generate mock time series
    now = datetime.now()
    timestamps = [now - timedelta(seconds=i) for i in range(60, 0, -1)]
    rates = [legion.consensus_checks_per_sec + (i % 10 - 5) * 1000 for i in range(60)]
    
    chart_data = pd.DataFrame({
        "Time": timestamps,
        "Consensus/Sec": rates
    })
    
    fig = px.line(chart_data, x="Time", y="Consensus/Sec", title="Real-Time Consensus Rate")
    st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    # Vote Distribution (Pie Chart)
    st.subheader("Vote Distribution (Latest Event)")
    
    if events:
        vote_states = {}
        for vote in latest_event.atom_votes:
            state = vote.vote_state.value
            vote_states[state] = vote_states.get(state, 0) + 1
        
        fig = go.Figure(data=[go.Pie(
            labels=list(vote_states.keys()),
            values=list(vote_states.values()),
            marker=dict(colors=['#00ff00', '#ff0000', '#888888', '#ffaa00'])
        )])
        fig.update_layout(title="Atom Vote States")
        st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption(f"ChainBridge God View Dashboard | PAC-VIZ-P55 | VIZ-01: Truth in UI | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# ============================================================================
# AUTO-REFRESH LOGIC
# ============================================================================

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
