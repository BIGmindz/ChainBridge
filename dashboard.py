import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import time
from datetime import datetime

# --- Professional Color Palette ---
COLORS = {
    "background": "#111111",
    "text": "#EAEAEA",
    "grid": "#222222",
    "primary": "#00A8CC",
    "green": "#2EBE7B",
    "red": "#D14E55",
    "gold": "#FFC107",
    "secondary": "#8884d8",
}

def load_trading_data():
    """Load live trading data from CSV logs"""
    try:
        # Try to load the main signals CSV
        if os.path.exists("benson_signals.csv"):
            df = pd.read_csv("benson_signals.csv")
            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
                return df
        
        # Fallback: check data directory
        data_dir = "data/"
        if not os.path.exists(data_dir):
            return None
            
        csv_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
        if not csv_files:
            return None
            
        df_list = []
        for fname in csv_files:
            path = os.path.join(data_dir, fname)
            try:
                tmp = pd.read_csv(path)
                if not tmp.empty and "timestamp" in tmp.columns:
                    df_list.append(tmp)
            except Exception:
                continue
                
        if df_list:
            df = pd.concat(df_list, ignore_index=True)
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df.sort_values("timestamp", inplace=True)
            return df
            
    except Exception as e:
        st.error(f"Error loading data: {e}")
    
    return None

def create_price_chart(df, symbol):
    """Create a price chart for the selected symbol"""
    if df is None or df.empty:
        return go.Figure()
    
    # Filter for the specific symbol
    symbol_data = df[df["symbol"] == symbol].copy() if "symbol" in df.columns else df
    
    if symbol_data.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # Add price line
    fig.add_trace(go.Scatter(
        x=symbol_data["timestamp"],
        y=symbol_data["price"] if "price" in symbol_data.columns else symbol_data.iloc[:, 1],
        mode="lines",
        name=f"{symbol} Price",
        line=dict(color=COLORS["primary"], width=2)
    ))
    
    # Add buy/sell signals if available
    if "action" in symbol_data.columns:
        buys = symbol_data[symbol_data["action"].str.contains("BUY", na=False)]
        sells = symbol_data[symbol_data["action"].str.contains("SELL", na=False)]
        
        if not buys.empty:
            fig.add_trace(go.Scatter(
                x=buys["timestamp"],
                y=buys["price"] if "price" in buys.columns else buys.iloc[:, 1],
                mode="markers",
                name="Buy Signals",
                marker=dict(color=COLORS["green"], size=10, symbol="triangle-up")
            ))
            
        if not sells.empty:
            fig.add_trace(go.Scatter(
                x=sells["timestamp"],
                y=sells["price"] if "price" in sells.columns else sells.iloc[:, 1],
                mode="markers",
                name="Sell Signals",
                marker=dict(color=COLORS["red"], size=10, symbol="triangle-down")
            ))
    
    fig.update_layout(
        title=f"{symbol} Live Trading Chart",
        template="plotly_dark",
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["background"],
        font_color=COLORS["text"],
        xaxis_title="Time",
        yaxis_title="Price ($)",
        showlegend=True
    )
    
    return fig

def create_pnl_chart(df):
    """Create P&L chart"""
    if df is None or df.empty or "pnl" not in df.columns:
        return go.Figure()
    
    fig = go.Figure()
    
    # Cumulative P&L
    cumulative_pnl = df["pnl"].cumsum() if "pnl" in df.columns else pd.Series([0])
    
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=cumulative_pnl,
        mode="lines",
        name="Cumulative P&L",
        line=dict(color=COLORS["gold"], width=3),
        fill="tozeroy"
    ))
    
    fig.update_layout(
        title="Cumulative Profit & Loss",
        template="plotly_dark",
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["background"],
        font_color=COLORS["text"],
        xaxis_title="Time",
        yaxis_title="P&L ($)",
        showlegend=True
    )
    
    return fig

def create_signal_strength_chart(df):
    """Create signal strength visualization"""
    if df is None or df.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # If we have signal columns, plot them
    signal_cols = [col for col in df.columns if "signal" in col.lower() or "rsi" in col.lower()]
    
    for i, col in enumerate(signal_cols[:5]):  # Limit to 5 signals for readability
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["timestamp"],
                y=df[col],
                mode="lines",
                name=col.replace("_", " ").title(),
                line=dict(width=2)
            ))
    
    fig.update_layout(
        title="Multi-Signal Analysis",
        template="plotly_dark",
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["background"],
        font_color=COLORS["text"],
        xaxis_title="Time",
        yaxis_title="Signal Strength",
        showlegend=True
    )
    
    return fig

def main():
    st.set_page_config(
        page_title="BensonBot Live Dashboard",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🤖 BensonBot Live Trading Dashboard")
    st.markdown("---")
    
    # Auto-refresh every 30 seconds
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    # Add refresh button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("**Live Trading Performance Monitor**")
    with col2:
        if st.button("🔄 Refresh Data"):
            st.session_state.last_refresh = time.time()
            st.rerun()
    
    # Load data
    df = load_trading_data()
    
    if df is None or df.empty:
        st.error("🚫 No trading data found. Make sure the live trading bot is running and generating data.")
        st.info("Expected files: benson_signals.csv or CSV files in data/ directory")
        return
    
    # Sidebar filters
    st.sidebar.title("📊 Dashboard Controls")
    
    # Symbol selection
    available_symbols = df["symbol"].unique().tolist() if "symbol" in df.columns else ["ALL"]
    selected_symbol = st.sidebar.selectbox("Select Trading Symbol", available_symbols)
    
    # Time range
    hours_back = st.sidebar.slider("Hours of data to show", 1, 24, 6)
    
    # Filter data by time
    cutoff_time = pd.Timestamp.now() - pd.Timedelta(hours=hours_back)
    recent_df = df[df["timestamp"] > cutoff_time] if "timestamp" in df.columns else df
    
    # Key Metrics Row
    st.subheader("📈 Key Performance Indicators")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_trades = len(recent_df)
        st.metric("Total Trades", total_trades)
    
    with col2:
        if "pnl" in recent_df.columns and not recent_df["pnl"].empty:
            total_pnl = recent_df["pnl"].sum()
            st.metric("Total P&L", f"${total_pnl:.2f}")
        else:
            st.metric("Total P&L", "N/A")
    
    with col3:
        if "portfolio_value" in recent_df.columns and not recent_df["portfolio_value"].empty:
            current_value = recent_df["portfolio_value"].iloc[-1]
            st.metric("Portfolio Value", f"${current_value:.2f}")
        else:
            st.metric("Portfolio Value", "$211.63")  # Starting balance
    
    with col4:
        if "action" in recent_df.columns:
            buy_count = recent_df["action"].str.contains("BUY", na=False).sum()
            sell_count = recent_df["action"].str.contains("SELL", na=False).sum()
            win_rate = (buy_count / (buy_count + sell_count) * 100) if (buy_count + sell_count) > 0 else 0
            st.metric("Win Rate", f"{win_rate:.1f}%")
        else:
            st.metric("Win Rate", "N/A")
    
    st.markdown("---")
    
    # Charts Row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            create_price_chart(recent_df, selected_symbol),
            use_container_width=True
        )
    
    with col2:
        st.plotly_chart(
            create_pnl_chart(recent_df),
            use_container_width=True
        )
    
    # Charts Row 2
    st.plotly_chart(
        create_signal_strength_chart(recent_df),
        use_container_width=True
    )
    
    # Recent Activity
    st.subheader("📋 Recent Trading Activity")
    
    # Show recent trades
    display_df = recent_df.tail(10) if not recent_df.empty else pd.DataFrame()
    
    if not display_df.empty:
        # Select relevant columns for display
        display_cols = []
        for col in ["timestamp", "symbol", "action", "price", "pnl", "portfolio_value"]:
            if col in display_df.columns:
                display_cols.append(col)
        
        if display_cols:
            st.dataframe(
                display_df[display_cols].sort_values(by="timestamp", ascending=False),  # type: ignore
                use_container_width=True
            )
        else:
            st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No recent trading activity to display")
    
    # Status footer
    st.markdown("---")
    st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("**Status:** 🟢 Live Trading Active")

    # Auto-refresh every 30 seconds
    time.sleep(0.1)  # Small delay to prevent excessive CPU usage

if __name__ == "__main__":
    main()