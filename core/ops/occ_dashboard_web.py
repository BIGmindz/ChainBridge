#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           CHAINBRIDGE OPERATIONS COMMAND CENTER (OCC) - WEB UI               ║
║                   PAC-OPS-P160-OCC-WEB                                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  TYPE: COMMAND_CENTER_WEB_INTERFACE                                          ║
║  GOVERNANCE_TIER: TIER-1_MONITORING                                          ║
║  MODE: TOTAL_AWARENESS                                                       ║
║  WATCH OFFICER: Morgan (GID-12)                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Streamlit Web Interface for the Operations Command Center.
Provides real-time monitoring of:
  • Treasury Balance & Flow
  • Lattice Node Health (14/14)
  • Agent Swarm Status (17 Agents)
  • Transaction Velocity
  • Security Perimeter
  • Module Health (Core, Pay, Sense, Freight)
"""

import streamlit as st
import time
import random
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

# Import from the main OCC dashboard
from occ_dashboard import (
    TREASURY_BALANCE,
    AGENTS,
    NODES,
    MODULES,
    MetricsCollector,
)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="ChainBridge OCC",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for dark theme styling
st.markdown("""
<style>
    .stApp {
        background-color: #0a0a0a;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .status-green { color: #00ff88; }
    .status-yellow { color: #ffcc00; }
    .status-red { color: #ff4444; }
    .header-title {
        font-family: 'Courier New', monospace;
        color: #00ff88;
        text-align: center;
        font-size: 2em;
        border: 2px solid #00ff88;
        padding: 10px;
        margin-bottom: 20px;
    }
    .agent-card {
        background: #1a1a2e;
        border-left: 3px solid #00ff88;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
    }
    .node-badge {
        display: inline-block;
        padding: 5px 10px;
        margin: 3px;
        border-radius: 5px;
        font-size: 0.8em;
    }
    .node-synced { background: #00ff8822; border: 1px solid #00ff88; color: #00ff88; }
    .node-pending { background: #ffcc0022; border: 1px solid #ffcc00; color: #ffcc00; }
    .node-offline { background: #ff444422; border: 1px solid #ff4444; color: #ff4444; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# METRICS COLLECTOR INSTANCE
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_collector():
    return MetricsCollector()

collector = get_collector()

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="header-title">
    ╔═══════════════════════════════════════════════════════════════╗<br>
    ║  🔗 CHAINBRIDGE OPERATIONS COMMAND CENTER (OCC)  🔗           ║<br>
    ║            THE BRIDGE - TOTAL AWARENESS MODE                  ║<br>
    ╚═══════════════════════════════════════════════════════════════╝
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR - STATUS & CONTROLS
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 🎯 System Status")
    
    # System time
    current_time = datetime.now(timezone.utc)
    st.markdown(f"**UTC Time:** `{current_time.strftime('%Y-%m-%d %H:%M:%S')}`")
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("🔄 Auto-Refresh (5s)", value=True)
    
    st.divider()
    
    # Quick stats
    st.markdown("### 📊 Quick Stats")
    st.metric("Treasury Balance", f"${TREASURY_BALANCE:,.2f}")
    st.metric("Agents Online", f"{len(AGENTS)}/17")
    st.metric("Nodes Synced", f"{len([n for n in NODES.values() if n['status'] == 'SYNCED'])}/14")
    
    st.divider()
    
    # Watch Officer
    st.markdown("### 👁️ Watch Officer")
    st.info("**Morgan (GID-12)**\nMonitoring Operations")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

# Collect fresh metrics
metrics = collector.collect_all()

# Top row - Key metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 💰 Treasury")
    treasury = metrics['treasury']
    st.metric(
        "Available Balance",
        f"${Decimal(treasury['available_usd']):,.2f}",
        delta=f"+${Decimal(treasury['daily_inflow_usd']):,.2f}/day"
    )
    st.caption(f"Reserved: ${Decimal(treasury['reserved_usd']):,.2f}")

with col2:
    st.markdown("### 🌐 Lattice Network")
    lattice = metrics['lattice']
    st.metric(
        "Nodes Online",
        f"{lattice['nodes_online']}/{lattice['total_nodes']}",
        delta=f"{lattice['sync_rate_pct']}% synced"
    )
    st.caption(f"Block Height: {lattice['last_block_height']}")

with col3:
    st.markdown("### 🤖 Agent Swarm")
    agents = metrics['agents']
    st.metric(
        "Agents Active",
        f"{agents['agents_active']}/{agents['total_agents']}",
        delta=f"{agents['swarm_health_pct']}% health"
    )
    st.caption(f"Orchestrator: {agents['orchestrator']}")

with col4:
    st.markdown("### 🛡️ Security")
    security = metrics['security']
    threat_color = "🟢" if security['threat_level'] == "GREEN" else "🟡" if security['threat_level'] == "YELLOW" else "🔴"
    st.metric(
        "Threat Level",
        f"{threat_color} {security['threat_level']}",
        delta=f"{security['attacks_blocked_24h']} blocked today"
    )
    st.caption(f"Invariants: {security['invariants_enforced']} enforced")

st.divider()

# Second row - Detailed panels
tab1, tab2, tab3, tab4 = st.tabs(["📡 Nodes", "🤖 Agents", "📦 Modules", "⚡ Transactions"])

with tab1:
    st.markdown("### Consensus Lattice Nodes")
    
    # Node grid
    cols = st.columns(4)
    for idx, (node_id, node_data) in enumerate(NODES.items()):
        col = cols[idx % 4]
        with col:
            status_emoji = "🟢" if node_data['status'] == "SYNCED" else "🟡" if node_data['status'] == "PENDING" else "🔴"
            st.markdown(f"""
            <div class="agent-card">
                <strong>{status_emoji} {node_id}</strong><br>
                📍 {node_data['location']}<br>
                🌍 {node_data['region']}<br>
                Status: {node_data['status']}
            </div>
            """, unsafe_allow_html=True)

with tab2:
    st.markdown("### Agent Swarm Status")
    
    # Agent grid
    cols = st.columns(3)
    for idx, (gid, agent_data) in enumerate(AGENTS.items()):
        col = cols[idx % 3]
        with col:
            status_emoji = "🟢" if agent_data['status'] == "ACTIVE" else "🟡" if agent_data['status'] == "IDLE" else "🔴"
            st.markdown(f"""
            <div class="agent-card">
                <strong>{status_emoji} {agent_data['name']}</strong> ({gid})<br>
                🎭 Role: {agent_data['role']}<br>
                Status: {agent_data['status']}
            </div>
            """, unsafe_allow_html=True)

with tab3:
    st.markdown("### Module Health")
    
    cols = st.columns(4)
    for idx, (mod_id, mod_data) in enumerate(MODULES.items()):
        col = cols[idx % 4]
        with col:
            status_emoji = "🟢" if mod_data['status'] == "OPERATIONAL" else "🟡" if mod_data['status'] == "DEGRADED" else "🔴"
            st.markdown(f"""
            <div class="agent-card">
                <strong>{status_emoji} {mod_data['name']}</strong><br>
                📌 Version: {mod_data['version']}<br>
                Status: {mod_data['status']}
            </div>
            """, unsafe_allow_html=True)

with tab4:
    st.markdown("### Transaction Metrics")
    
    tx = metrics['transactions']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Transactions", tx['total_transactions'])
        st.metric("24h Transactions", tx['transactions_24h'])
    
    with col2:
        st.metric("Current TPS", tx['current_tps'])
        st.metric("Peak TPS", f"{tx['peak_tps']:,}")
    
    with col3:
        st.metric("Avg Settlement", f"{tx['avg_settlement_ms']:.2f} ms")
        st.metric("Pending Escrows", tx['pending_escrows'])
        st.caption(f"Escrow Value: ${Decimal(tx['escrow_value_usd']):,.2f}")

st.divider()

# Bottom row - Alerts and recent activity
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🚨 Recent Alerts")
    
    alerts = metrics.get('alerts', [])
    if alerts:
        for alert in alerts[-5:]:
            severity_color = "🔴" if alert['severity'] == "CRITICAL" else "🟡" if alert['severity'] == "WARNING" else "🔵"
            st.markdown(f"""
            <div class="agent-card">
                {severity_color} <strong>[{alert['severity']}]</strong> {alert['message']}<br>
                <small>Source: {alert['source']} | {alert['timestamp']}</small>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ No active alerts - System nominal")

with col2:
    st.markdown("### 📜 Invariants")
    invariants = [
        ("INV-OPS-001", "Real-Time Integrity", "✅"),
        ("INV-OPS-002", "Truth Visibility", "✅"),
        ("INV-OPS-003", "Read-Only Safety", "✅"),
    ]
    for inv_id, inv_name, status in invariants:
        st.markdown(f"**{inv_id}**: {inv_name} {status}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    ChainBridge Operations Command Center v1.0 | Watch Officer: Morgan (GID-12) | Mode: TOTAL_AWARENESS
</div>
""", unsafe_allow_html=True)

# Auto-refresh logic
if auto_refresh:
    time.sleep(5)
    st.rerun()
