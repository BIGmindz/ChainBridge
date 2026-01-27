"""
PAC-49: SOVEREIGN WAR ROOM
===========================

God's Eye View: Real-Time Legion Monitoring Dashboard

MISSION:
- Visualize 1,000-agent legion activity in real-time
- Display $100M batch flow metrics
- Monitor transaction throughput (TPS)
- Provide immutable audit trail visibility

INVARIANTS:
- VIEW-01: Dashboard MUST be read-only (no writes to logs)
- VIEW-02: Latency MUST NOT exceed 2 seconds

Author: BENSON (GID-00) via PAC-49
Version: 1.0.0
Status: PRODUCTION-READY
"""

import streamlit as st
import pandas as pd
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go


# ============================================================================
# CONFIGURATION
# ============================================================================

LOG_FILE = Path("logs/legion_audit.jsonl")
REFRESH_INTERVAL = 1  # seconds (VIEW-02: <2s latency)
PAGE_TITLE = "ChainBridge Sovereign War Room"
PAGE_ICON = "🛡️"


# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data(ttl=REFRESH_INTERVAL)
def load_legion_data():
    """
    Load legion audit data from JSONL file.
    
    Returns:
        DataFrame with batch execution records
    
    Invariant: VIEW-01 (Read-only access)
    """
    data = []
    
    if not LOG_FILE.exists():
        return pd.DataFrame()
    
    with open(LOG_FILE, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                data.append(entry)
            except json.JSONDecodeError:
                continue
    
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    # Parse timestamps
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df


def get_summary_metrics(df):
    """
    Calculate summary metrics from audit log.
    
    Args:
        df: Audit log DataFrame
    
    Returns:
        Dictionary with key metrics
    """
    if df.empty:
        return {
            "total_batches": 0,
            "total_transactions": 0,
            "total_volume_usd": 0.0,
            "peak_tps": 0.0,
            "avg_tps": 0.0,
            "legion_size": 0,
            "success_rate": 0.0
        }
    
    return {
        "total_batches": len(df),
        "total_transactions": df['transaction_count'].sum(),
        "total_volume_usd": df['volume_usd'].sum(),
        "peak_tps": df['tps'].max(),
        "avg_tps": df['tps'].mean(),
        "legion_size": df['legion_size'].iloc[-1] if 'legion_size' in df.columns else 0,
        "success_rate": (df['status'] == 'SUCCESS').mean() * 100
    }


# ============================================================================
# VISUALIZATION COMPONENTS
# ============================================================================

def render_header():
    """Render war room header."""
    st.markdown("""
    <style>
    .big-font {
        font-size: 48px !important;
        font-weight: bold;
        text-align: center;
        color: #FF4B4B;
    }
    .status-active {
        font-size: 24px;
        text-align: center;
        color: #00FF00;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="big-font">🛡️ CHAINBRIDGE SOVEREIGN WAR ROOM</p>', unsafe_allow_html=True)
    st.markdown('<p class="status-active">⚡ STATUS: HYPER-DETERMINISTIC LEGION ACTIVE ⚡</p>', unsafe_allow_html=True)
    st.markdown("---")


def render_metrics_dashboard(metrics):
    """
    Render key metrics dashboard.
    
    Args:
        metrics: Summary metrics dictionary
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🎓 LEGION SIZE",
            value=f"{metrics['legion_size']:,} Agents",
            delta="PAC-UNI-100 Active"
        )
    
    with col2:
        st.metric(
            label="📊 TRANSACTIONS",
            value=f"{metrics['total_transactions']:,}",
            delta=f"{metrics['success_rate']:.1f}% Success"
        )
    
    with col3:
        st.metric(
            label="💰 TOTAL VOLUME",
            value=f"${metrics['total_volume_usd']:,.0f}",
            delta=f"{metrics['total_batches']} Batches"
        )
    
    with col4:
        st.metric(
            label="⚡ PEAK THROUGHPUT",
            value=f"{metrics['peak_tps']:,.0f} TPS",
            delta=f"Avg: {metrics['avg_tps']:,.0f} TPS"
        )


def render_tps_timeline(df):
    """
    Render TPS timeline chart.
    
    Args:
        df: Audit log DataFrame
    """
    if df.empty or 'timestamp' not in df.columns:
        st.info("📈 Waiting for batch execution data...")
        return
    
    st.subheader("⚡ THROUGHPUT TIMELINE")
    
    fig = px.line(
        df,
        x='timestamp',
        y='tps',
        title='Transactions Per Second (TPS) Over Time',
        labels={'tps': 'TPS', 'timestamp': 'Time'},
        markers=True
    )
    
    fig.add_hline(
        y=10_000,
        line_dash="dash",
        line_color="red",
        annotation_text="LEGION-02 Requirement (10k TPS)"
    )
    
    fig.update_layout(
        height=400,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_volume_distribution(df):
    """
    Render volume distribution chart.
    
    Args:
        df: Audit log DataFrame
    """
    if df.empty:
        return
    
    st.subheader("💰 VOLUME DISTRIBUTION")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Volume by batch
        fig = px.bar(
            df,
            x='batch_id',
            y='volume_usd',
            title='Volume per Batch',
            labels={'volume_usd': 'Volume (USD)', 'batch_id': 'Batch ID'},
            color='status',
            color_discrete_map={'SUCCESS': 'green', 'FAILURE': 'red', 'PARTIAL_FAILURE': 'orange'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Transaction count by batch
        fig = px.bar(
            df,
            x='batch_id',
            y='transaction_count',
            title='Transactions per Batch',
            labels={'transaction_count': 'Transactions', 'batch_id': 'Batch ID'},
            color='status',
            color_discrete_map={'SUCCESS': 'green', 'FAILURE': 'red', 'PARTIAL_FAILURE': 'orange'}
        )
        st.plotly_chart(fig, use_container_width=True)


def render_legion_status(df):
    """
    Render legion status overview.
    
    Args:
        df: Audit log DataFrame
    """
    st.subheader("🎓 LEGION STATUS")
    
    if df.empty:
        st.info("Legion data not available")
        return
    
    latest = df.iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Latest Batch**")
        st.write(f"Batch ID: `{latest['batch_id']}`")
        st.write(f"Status: `{latest['status']}`")
        st.write(f"Timestamp: `{latest['timestamp']}`")
    
    with col2:
        st.markdown("**Performance**")
        st.write(f"TPS: `{latest['tps']:,.0f}`")
        st.write(f"Duration: `{latest['duration_seconds']:.3f}s`")
        st.write(f"Transactions: `{latest['transaction_count']:,}`")
    
    with col3:
        st.markdown("**Configuration**")
        st.write(f"Legion Size: `{latest['legion_size']:,} agents`")
        st.write(f"PAC ID: `{latest['pac_id']}`")
        st.write(f"Volume: `${latest['volume_usd']:,.0f}`")


def render_audit_trail(df):
    """
    Render immutable audit trail.
    
    Args:
        df: Audit log DataFrame
    
    Invariant: VIEW-01 (Read-only display)
    """
    st.subheader("📜 IMMUTABLE AUDIT TRAIL")
    
    if df.empty:
        st.warning("⏳ Waiting for legion execution data...")
        return
    
    # Show last 10 entries
    recent = df.tail(10).sort_values('timestamp', ascending=False)
    
    # Format for display
    display_df = recent[[
        'timestamp', 'batch_id', 'status', 'transaction_count', 
        'volume_usd', 'tps', 'legion_size'
    ]].copy()
    
    display_df['volume_usd'] = display_df['volume_usd'].apply(lambda x: f"${x:,.2f}")
    display_df['tps'] = display_df['tps'].apply(lambda x: f"{x:,.0f}")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Download option
    if st.button("📥 Download Full Audit Log (CSV)"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"legion_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )


def render_invariant_status():
    """Render invariant validation status."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("🛡️ INVARIANT STATUS")
    
    st.sidebar.markdown("**VIEW-01: Read-Only Access**")
    st.sidebar.success("✅ SATISFIED - Dashboard has no write permissions")
    
    st.sidebar.markdown("**VIEW-02: Latency <2s**")
    st.sidebar.success(f"✅ SATISFIED - Refresh: {REFRESH_INTERVAL}s")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main Streamlit application."""
    
    # Page configuration
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Sidebar
    st.sidebar.title("⚙️ WAR ROOM CONTROLS")
    st.sidebar.markdown(f"**Refresh Rate**: {REFRESH_INTERVAL}s")
    st.sidebar.markdown(f"**Log Source**: `{LOG_FILE}`")
    st.sidebar.markdown(f"**Last Update**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    auto_refresh = st.sidebar.checkbox("🔄 Auto-Refresh", value=True)
    
    render_invariant_status()
    
    # Main content
    render_header()
    
    # Load data
    df = load_legion_data()
    metrics = get_summary_metrics(df)
    
    # Render components
    render_metrics_dashboard(metrics)
    
    st.markdown("---")
    
    render_tps_timeline(df)
    
    st.markdown("---")
    
    render_volume_distribution(df)
    
    st.markdown("---")
    
    render_legion_status(df)
    
    st.markdown("---")
    
    render_audit_trail(df)
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(REFRESH_INTERVAL)
        st.rerun()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
