import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# --- Professional Color Palette ---
# Inspired by financial terminals
COLORS = {
    "background": "#111111",
    "text": "#EAEAEA",
    "grid": "#222222",
    "primary": "#00A8CC",  # A vibrant blue for primary plots
    "green": "#2EBE7B",  # A clear green for profit/up
    "red": "#D14E55",  # A clear red for loss/down
    "gold": "#FFC107",  # For highlights and key metrics
    "secondary": "#8884d8",  # For secondary metrics or charts
}


def load_and_prepare_data(data_dir="data/"):
    """Finds all trade logs, consolidates them, and prepares for plotting."""
    if not os.path.exists(data_dir):
        return None

    all_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    if not all_files:
        return None

    df_list = []
    # Only include CSVs that parse cleanly and contain expected core columns
    required_cols = {"timestamp", "symbol", "price"}
    for fname in all_files:
        path = os.path.join(data_dir, fname)
        if os.path.getsize(path) == 0:
            continue
        try:
            tmp = pd.read_csv(path)
        except Exception:
            # skip files that fail to parse (HTML pages, malformed CSVs, etc.)
            continue
        if not required_cols.issubset(set(tmp.columns)):
            # skip CSVs that don't contain the expected trading columns
            continue
        df_list.append(tmp)
    if not df_list:
        return None

    df = pd.concat(df_list, ignore_index=True)

    # Expecting a `timestamp` column in the aggregated logs
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    elif "ts_utc" in df.columns:
        df["timestamp"] = pd.to_datetime(df["ts_utc"], errors="coerce")
    else:
        # No timestamp column — the data isn't in expected shape
        return None

    df.drop_duplicates(subset=["timestamp", "symbol"], inplace=True)
    df.sort_values("timestamp", inplace=True)
    return df


def create_candlestick_chart(df, symbol):
    """Creates a professional candlestick chart with volume and moving averages."""
    df_symbol = df[df["symbol"] == symbol].copy()
    if df_symbol.empty:
        return go.Figure()

    # Resample to create OHLC candles (e.g., 5 minutes)
    resampled = df_symbol.set_index("timestamp")["price"].resample("5T").ohlc()
    resampled.dropna(inplace=True)

    # Calculate Moving Averages
    resampled["ma_10"] = resampled["close"].rolling(window=10).mean()
    resampled["ma_50"] = resampled["close"].rolling(window=50).mean()

    # Create figure with secondary y-axis for volume
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(f"{symbol} Price", "Volume"),
        row_heights=[0.7, 0.3],
    )

    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=resampled.index,
            open=resampled["open"],
            high=resampled["high"],
            low=resampled["low"],
            close=resampled["close"],
            increasing_line_color=COLORS["green"],
            decreasing_line_color=COLORS["red"],
            name="Price",
        ),
        row=1,
        col=1,
    )

    # Moving Averages
    fig.add_trace(
        go.Scatter(
            x=resampled.index,
            y=resampled["ma_10"],
            mode="lines",
            line=dict(color=COLORS["primary"], width=1),
            name="10-period MA",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=resampled.index,
            y=resampled["ma_50"],
            mode="lines",
            line=dict(color=COLORS["gold"], width=1),
            name="50-period MA",
        ),
        row=1,
        col=1,
    )

    # Volume Bar Chart
    # Use df_symbol aggregated volume per resample interval
    vol_series = df_symbol.set_index("timestamp")["trade_amount"].resample("5T").sum()
    volume_colors = [COLORS["green"] if row.close >= row.open else COLORS["red"] for _, row in resampled.iterrows()]

    fig.add_trace(
        go.Bar(x=resampled.index, y=vol_series, marker_color=volume_colors, name="Volume"),
        row=2,
        col=1,
    )

    fig.update_layout(
        title_text=f"{symbol} Price Action and Volume",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        paper_bgcolor=COLORS["background"],
        plot_bgcolor=COLORS["background"],
        font_color=COLORS["text"],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    fig.update_yaxes(gridcolor=COLORS["grid"])
    fig.update_xaxes(gridcolor=COLORS["grid"])

    return fig


def create_dashboard():
    st.set_page_config(page_title="Benson Bot Dashboard", layout="wide")
    st.title("🤖 Benson Bot: Live Performance Dashboard")
    st.markdown("---")

    df = load_and_prepare_data()

    if df is None:
        st.error("No trading data found in the 'data/' directory. Please run the trading bot first.")
        return

    # --- Sidebar Filters ---
    st.sidebar.title("Filters")
    selected_symbol = st.sidebar.selectbox("Select Symbol", df["symbol"].unique())

    # --- Main Content ---
    # Key Metrics (KPIs)
    st.subheader("Key Performance Indicators")
    latest_row = df.iloc[-1]
    initial_capital = 10000  # As per config

    pnl = latest_row.get("pnl", 0)
    try:
        pnl_pct = (pnl / initial_capital) * 100
    except Exception:
        pnl_pct = 0

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Portfolio Value",
        f"${latest_row.get('portfolio_value', 0):,.2f}",
        f"{pnl:,.2f} ({pnl_pct:.2f}%)",
    )

    trade_df = df[df["action"].str.contains("SIM_", na=False)] if "action" in df.columns else df
    col2.metric("Total Trades", len(trade_df))

    # Simple Win Rate (can be improved with trade pairing)
    wins = trade_df[trade_df["pnl"] > df["pnl"].shift(1)].shape[0] if "pnl" in trade_df.columns and "pnl" in df.columns else 0

    win_rate = (wins / len(trade_df)) * 100 if not trade_df.empty else 0
    col3.metric("Win Rate", f"{win_rate:.1f}%")

    st.markdown("---")

    # Candlestick Chart
    st.plotly_chart(create_candlestick_chart(df, selected_symbol), use_container_width=True)

    # --- Deeper Analysis in Columns ---
    st.markdown("---")
    st.subheader("Signal & Portfolio Analysis")
    col1, col2 = st.columns(2)

    with col1:
        # Donut chart for holdings
        holdings = {col.replace("holding_", "").upper(): latest_row[col] for col in df.columns if "holding_" in col}

        holdings_df = pd.DataFrame(list(holdings.items()), columns=["Asset", "Amount"]).set_index("Asset")

        st.write("**Current Holdings**")
        st.dataframe(holdings_df)

    with col2:
        # Signal Correlation Heatmap
        st.write("**Signal Correlation**")
        signal_cols = [
            "price",
            "rsi_value",
            "ob_imbalance",
            "vol_imbalance",
            "ml_signal",
            "combined_score",
        ]

        present_cols = [c for c in signal_cols if c in df.columns]
        if present_cols:
            corr_df = df[present_cols].corr()
            fig = go.Figure(
                data=go.Heatmap(
                    z=corr_df.values,
                    x=corr_df.columns,
                    y=corr_df.columns,
                    colorscale="RdBu",
                    zmin=-1,
                    zmax=1,
                )
            )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor=COLORS["background"],
                plot_bgcolor=COLORS["background"],
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough signal columns present to compute correlation.")

    # Recent Trades Log
    with st.expander("View Recent Trades"):
        st.dataframe(trade_df.tail(20))


if __name__ == "__main__":
    create_dashboard()
