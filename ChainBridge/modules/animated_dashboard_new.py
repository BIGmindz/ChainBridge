import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import glob

# ==============================================================================
# --- GENERIC ENGINE CONFIGURATION (EDIT FOR ANY INDUSTRY) ---
# ==============================================================================
# This dictionary now drives the entire dashboard using generic terms.
# To adapt this for a different industry (e.g., Energy Sector), you would
# only need to change the values and labels here.

CONFIG = {
    "dashboard_title": "Benson Bot | Decision Engine Dashboard",
    "data_source": {
        "directory": "data/",
        "timestamp_col": "timestamp",
        # An "Entity" is the thing being tracked (a crypto coin, a power plant, a drug trial)
        "entity_col": "symbol",
        # The primary value of the entity (price, megawatts, success rate)
        "value_col": "price",
        "activity_volume_col": "trade_amount",
        # An "Event" is a discrete action taken by the bot (a trade, a power re-route)
        "event_col": "action",
        "positive_event_str": "SIM_BUY",
        "negative_event_str": "SIM_SELL",
    },
    "state_tracking": {
        # The primary metric of the system's state (portfolio value, grid efficiency)
        "primary_metric_col": "portfolio_value",
        "primary_metric_label": "Portfolio Value",
        # The performance metric (P&L, efficiency gain)
        "performance_metric_col": "pnl",
        "initial_state_value": 10000,
        # A "State Item" is a component of the overall state (asset holding, generator status)
        "state_item_prefix": "holding_",
    },
    "visualization": {
        "chart_type": "candlestick",  # Can be 'candlestick' for finance or 'line' for generic data
        "fast_ma_period": 10,
        "slow_ma_period": 50,
    },
    "ui_tables": {
        "recent_events_cols": [
            "timestamp",
            "symbol",
            "action",
            "price",
            "combined_score",
        ],
        "recent_events_label": "Recent Trades",
    },
}


# ==============================================================================
# --- STYLING (Unchanged) ---
# ==============================================================================
def apply_styling():
    """Injects custom CSS for a professional dark theme."""
    st.markdown(
        """
    <style>
        .stApp { background-color: #0E1117; }
        .st-emotion-cache-16txtl3 { color: #FAFAFA; }
        .st-emotion-cache-1g82d3j, .st-emotion-cache-1rtd21g { color: #A0A0A0; }
        .st-emotion-cache-1cypcdb { background-color: #1A1C22; }
        footer, header { visibility: hidden; }
    </style>
    """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# --- DATA PROVIDER (Now fully generic) ---
# ==============================================================================
class DataProvider:
    """Handles loading and preparing all time-series event data."""

    def __init__(self, config):
        self.config = config["data_source"]
        self.state_config = config["state_tracking"]

    @st.cache_data(ttl=60)
    def load_data(_self):
        """Finds all logs, consolidates them, and prepares a master DataFrame."""
        try:
            all_files = glob.glob(os.path.join(_self.config["directory"], "*.csv"))
            if not all_files:
                return pd.DataFrame()

            # Load only files that contain the primary state metric
            df_list = [pd.read_csv(f) for f in all_files if _self.state_config["primary_metric_col"] in pd.read_csv(f, nrows=0).columns]  # type: ignore
            if not df_list:
                return pd.DataFrame()

            df = pd.concat(df_list, ignore_index=True)  # type: ignore
            df[_self.config["timestamp_col"]] = pd.to_datetime(df[_self.config["timestamp_col"]])  # type: ignore
            df.drop_duplicates(
                subset=[_self.config["timestamp_col"], _self.config["entity_col"]],
                inplace=True,
            )
            df.sort_values(_self.config["timestamp_col"], inplace=True)  # type: ignore
            return df
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame()


# ==============================================================================
# --- DASHBOARD RENDERER (Now fully generic) ---
# ==============================================================================
class DashboardRenderer:
    """Contains all the logic to render different UI modules based on the config."""

    def __init__(self, config, data):
        self.config = config
        self.data = data

    def render_sidebar(self):
        """Renders the sidebar with controls and state summary."""
        st.sidebar.header("Engine Controls")
        all_entities = self.data[self.config["data_source"]["entity_col"]].unique()  # type: ignore
        selected_entity = st.sidebar.selectbox(
            "Select Entity to Analyze", all_entities, index=0
        )

        st.sidebar.header("System State Overview")
        latest_row = self.data.iloc[-1]
        state_cfg = self.config["state_tracking"]
        performance_metric = latest_row[state_cfg["performance_metric_col"]]
        perf_pct = (performance_metric / state_cfg["initial_state_value"]) * 100

        st.sidebar.metric(
            state_cfg["primary_metric_label"],
            f"${latest_row[state_cfg['primary_metric_col']]:,.2f}",
            f"{performance_metric:,.2f} ({perf_pct:.2f}%)",
        )

        state_items = {
            col.replace(state_cfg["state_item_prefix"], ""): latest_row[col]
            for col in self.data.columns
            if col.startswith(state_cfg["state_item_prefix"])
        }
        for item, value in state_items.items():
            if isinstance(value, float) and value > 1e-6 or isinstance(value, str):
                st.sidebar.text(
                    f"- {item.upper()}: {value:,.4f}"
                    if isinstance(value, float)
                    else f"- {item.upper()}: {value}"
                )
        return selected_entity

    def render_entity_activity_chart(self, entity):
        """Renders the main activity chart for a selected entity."""
        cfg = self.config
        df_entity = self.data[
            self.data[cfg["data_source"]["entity_col"]] == entity
        ].copy()
        if df_entity.empty:
            st.warning("No data for selected entity.")
            return

        df_resampled = (
            df_entity.set_index(cfg["data_source"]["timestamp_col"])[
                cfg["data_source"]["value_col"]
            ]
            .resample("1T")
            .ohlc()
            .dropna()
        )
        df_resampled["ma_fast"] = (
            df_resampled["close"]
            .rolling(window=cfg["visualization"]["fast_ma_period"])
            .mean()
        )
        df_resampled["ma_slow"] = (
            df_resampled["close"]
            .rolling(window=cfg["visualization"]["slow_ma_period"])
            .mean()
        )

        events = df_entity[
            df_entity[cfg["data_source"]["event_col"]].str.contains("SIM_", na=False)
        ]
        positive_events = events[
            events[cfg["data_source"]["event_col"]]
            == cfg["data_source"]["positive_event_str"]
        ]
        negative_events = events[
            events[cfg["data_source"]["event_col"]]
            == cfg["data_source"]["negative_event_str"]
        ]

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=[0.8, 0.2],
        )

        # Add primary value trace (Candlestick or Line)
        if cfg["visualization"]["chart_type"] == "candlestick":
            fig.add_trace(
                go.Candlestick(
                    x=df_resampled.index,
                    open=df_resampled["open"],
                    high=df_resampled["high"],
                    low=df_resampled["low"],
                    close=df_resampled["close"],
                    name="Value",
                    increasing_line_color="#2EBE7B",
                    decreasing_line_color="#D14E55",
                ),
                row=1,
                col=1,
            )
        else:  # Default to line chart
            fig.add_trace(
                go.Scatter(
                    x=df_resampled.index,
                    y=df_resampled["close"],
                    name="Value",
                    line=dict(color="#00A8CC"),
                ),
                row=1,
                col=1,
            )

        fig.add_trace(
            go.Scatter(
                x=df_resampled.index,
                y=df_resampled["ma_fast"],
                name=f"MA({cfg['visualization']['fast_ma_period']})",
                line=dict(color="#00A8CC", width=1),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df_resampled.index,
                y=df_resampled["ma_slow"],
                name=f"MA({cfg['visualization']['slow_ma_period']})",
                line=dict(color="#FFC107", width=1),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=positive_events[cfg["data_source"]["timestamp_col"]],
                y=positive_events[cfg["data_source"]["value_col"]],
                name="Positive Events",
                mode="markers",
                marker=dict(
                    color="#2EBE7B",
                    size=10,
                    symbol="triangle-up",
                    line=dict(width=1, color="White"),
                ),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=negative_events[cfg["data_source"]["timestamp_col"]],
                y=negative_events[cfg["data_source"]["value_col"]],
                name="Negative Events",
                mode="markers",
                marker=dict(
                    color="#D14E55",
                    size=10,
                    symbol="triangle-down",
                    line=dict(width=1, color="White"),
                ),
            ),
            row=1,
            col=1,
        )

        df_volume = df_entity.set_index(cfg["data_source"]["timestamp_col"])[cfg["data_source"]["activity_volume_col"]].resample("1T").sum()  # type: ignore
        fig.add_trace(
            go.Bar(
                x=df_volume.index,
                y=df_volume,
                name="Activity Volume",
                marker_color="#8884d8",
            ),
            row=2,
            col=1,
        )

        fig.update_layout(
            title=f"{entity} Activity Analysis",
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#1A1C22",
            xaxis_rangeslider_visible=False,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )
        st.plotly_chart(fig, use_container_width=True)

    def render_kpis_and_events(self):
        """Renders the KPI cards and recent events table."""
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(self.config["ui_tables"]["recent_events_label"])
            events_df = self.data[
                self.data[self.config["data_source"]["event_col"]].str.contains(
                    "SIM_", na=False
                )
            ].tail(10)
            st.dataframe(
                events_df[self.config["ui_tables"]["recent_events_cols"]],
                use_container_width=True,
            )
        with col2:
            st.subheader("Performance Metrics")
            event_count = len(
                self.data[
                    self.data[self.config["data_source"]["event_col"]].str.contains(
                        "SIM_", na=False
                    )
                ]
            )
            st.metric("Total Events", event_count)
            wins = len(
                self.data[self.config["state_tracking"]["performance_metric_col"]]
                > self.data[self.config["state_tracking"]["performance_metric_col"]]
                .shift(1)
                .fillna(0)
            )
            success_rate = (wins / event_count) * 100 if event_count > 0 else 0
            st.metric("Success Rate", f"{success_rate:.1f}%")


# ==============================================================================
# --- MAIN APPLICATION (The "Engine") ---
# ==============================================================================
def run_app():
    """The main function to orchestrate the dashboard creation."""
    st.set_page_config(
        page_title=CONFIG["dashboard_title"], page_icon="🤖", layout="wide"
    )
    apply_styling()

    data_provider = DataProvider(CONFIG)
    df = data_provider.load_data()

    if df.empty:
        st.warning(
            "No valid decision engine data found. Please run the bot to generate logs."
        )
        st.stop()

    renderer = DashboardRenderer(CONFIG, df)

    st.title(CONFIG["dashboard_title"])
    selected_entity = renderer.render_sidebar()
    st.header(f"Analysis for {selected_entity}")

    # Main content area
    renderer.render_entity_activity_chart(selected_entity)
    renderer.render_kpis_and_events()


if __name__ == "__main__":
    run_app()
