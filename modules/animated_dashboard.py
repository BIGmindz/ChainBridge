"""
Professional Trading Dashboard combining TradingView and Robinhood styles
"""

import dash
from dash import html, dcc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict
import talib
from modules.enhanced_indicators import EnhancedTechnicalIndicators

# TradingView Color Scheme
TV_COLORS = {
    "blue": "rgba(0, 150, 255, 0.8)",
    "red": "rgba(255, 82, 82, 0.8)",
    "green": "rgba(76, 175, 80, 0.8)",
    "orange": "rgba(255, 152, 0, 0.8)",
    "purple": "rgba(156, 39, 176, 0.8)",
    "cloud_fill": "rgba(0, 150, 255, 0.1)",
}

# Robinhood Color Scheme
RH_COLORS = {"green": "#00C805", "red": "#FF5000", "black": "#1E2124", "dark_gray": "#18191A", "light_gray": "#8C8C8E"}


class AnimatedTradingDashboard:
    def __init__(self):
        self.app = dash.Dash(__name__)
        self.indicators = EnhancedTechnicalIndicators()
        self.setup_layout()

    def setup_layout(self):
        """Create a Robinhood-style modern layout."""
        self.app.layout = html.Div(
            [
                # Top Navigation Bar
                html.Div(
                    [
                        html.Div(
                            [
                                html.H2("BTC-USD", style={"color": "#ffffff", "margin": 0}),
                                html.Div(id="price-change", className="price-change"),
                            ],
                            style={"display": "flex", "alignItems": "center", "gap": "15px"},
                        ),
                        html.Div(id="live-clock", className="live-clock"),
                        dcc.Interval(id="interval-component", interval=1000, n_intervals=0),
                    ],
                    className="nav-bar",
                ),
                # Main Trading View
                html.Div(
                    [
                        # Left Column - Main Chart
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H1(id="current-price", className="current-price"),
                                        html.Div(id="price-metrics", className="price-metrics"),
                                    ],
                                    className="price-header",
                                ),
                                dcc.Graph(id="main-chart", config={"displayModeBar": False}, className="main-chart"),
                                dcc.Interval(id="chart-interval", interval=5000, n_intervals=0),
                            ],
                            className="chart-container",
                        ),
                        # Right Column - Stats & Indicators
                        html.Div(
                            [
                                html.Div(
                                    [html.H3("Key Stats", className="section-title"), html.Div(id="key-stats", className="stats-grid")],
                                    className="stats-container",
                                ),
                                html.Div(
                                    [
                                        html.H3("Trading Signals", className="section-title"),
                                        html.Div(id="signal-panel", className="signal-container"),
                                    ],
                                    className="signals-container",
                                ),
                                html.Div(
                                    [
                                        html.H3("Technical Analysis", className="section-title"),
                                        dcc.Graph(id="indicator-grid", config={"displayModeBar": False}, className="indicator-chart"),
                                        dcc.Interval(id="indicator-interval", interval=2000, n_intervals=0),
                                    ],
                                    className="indicators-container",
                                ),
                            ],
                            className="sidebar",
                        ),
                    ],
                    className="main-content",
                ),
            ],
            className="app-container",
        )

    def update_main_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create a TradingView-style professional chart with Robinhood aesthetics."""
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3], subplot_titles=("", "Volume"))

        if df.empty:
            return fig

        # TradingView-style Candlestick Chart
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="Price Action",
                increasing_line_color="#00C805",  # Robinhood green
                decreasing_line_color="#FF5000",  # Robinhood red
                increasing_fillcolor="rgba(0, 200, 5, 0.2)",
                decreasing_fillcolor="rgba(255, 80, 0, 0.2)",
            ),
            row=1,
            col=1,
        )

        # Add Bollinger Bands with gradient fill
        bb_data = self.indicators._calculate_price_action(df)["bollinger_bands"]
        fig.add_trace(
            go.Scatter(x=df.index, y=bb_data["upper"], name="BB Upper", line=dict(color="rgba(0,255,0,0.5)"), fill=None), row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df.index, y=bb_data["lower"], name="BB Lower", line=dict(color="rgba(255,0,0,0.5)"), fill="tonexty"), row=1, col=1
        )

        # Add TradingView-style MA Cloud
        ema_fast = talib.EMA(df["close"].astype(float), timeperiod=21)
        ema_slow = talib.EMA(df["close"].astype(float), timeperiod=55)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=ema_fast,
                name="EMA 21",
                line=dict(
                    width=1.5,
                    color="rgba(0, 150, 255, 0.8)",  # TradingView blue
                ),
                fill=None,
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=ema_slow,
                name="EMA 55",
                line=dict(
                    width=1.5,
                    color="rgba(255, 82, 82, 0.8)",  # TradingView red
                ),
                fill="tonexty",
                fillcolor="rgba(0, 150, 255, 0.1)",  # Light blue cloud
            ),
            row=1,
            col=1,
        )

        # Add short-term EMA for momentum
        ema_short = talib.EMA(df["close"].astype(float), timeperiod=8)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=ema_short,
                name="EMA 8",
                line=dict(
                    width=1.5,
                    color="rgba(255, 152, 0, 0.8)",  # TradingView orange
                ),
            ),
            row=1,
            col=1,
        )

        # Volume Bars with Color Intensity
        colors = ["#00ff00" if row["close"] >= row["open"] else "#ff0000" for idx, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df["volume"], name="Volume", marker_color=colors, opacity=0.6), row=2, col=1)

        # Add Moving Averages with Glow Effect
        for period in [8, 21, 55]:
            ema = talib.EMA(df["close"], timeperiod=period)
            fig.add_trace(
                go.Scatter(
                    x=df.index, y=ema, name=f"EMA {period}", line=dict(width=2, color=f"rgba({255 - period * 2},255,{period * 3},0.8)")
                ),
                row=1,
                col=1,
            )

        # TradingView-style layout
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1E2124",  # Robinhood dark theme
            plot_bgcolor="#1E2124",
            showlegend=True,
            legend=dict(bgcolor="rgba(30, 33, 36, 0.8)", bordercolor="rgba(255, 255, 255, 0.1)", borderwidth=1, font=dict(size=10)),
            xaxis_rangeslider_visible=False,
            margin=dict(l=40, r=40, t=40, b=40),
            # TradingView-style grid
            xaxis=dict(
                gridcolor="rgba(58, 58, 58, 0.15)",
                gridwidth=1,
                showgrid=True,
                zeroline=False,
                showline=True,
                linecolor="rgba(58, 58, 58, 0.3)",
                tickfont=dict(size=10),
            ),
            yaxis=dict(
                gridcolor="rgba(58, 58, 58, 0.15)",
                gridwidth=1,
                showgrid=True,
                zeroline=False,
                showline=True,
                linecolor="rgba(58, 58, 58, 0.3)",
                tickfont=dict(size=10),
                tickformat="$,.2f",
            ),
            # Volume subplot styling
            xaxis2=dict(
                gridcolor="rgba(58, 58, 58, 0.15)", showgrid=True, showline=True, linecolor="rgba(58, 58, 58, 0.3)", tickfont=dict(size=8)
            ),
            yaxis2=dict(
                gridcolor="rgba(58, 58, 58, 0.15)", showgrid=True, showline=True, linecolor="rgba(58, 58, 58, 0.3)", tickfont=dict(size=8)
            ),
        )

        # Add dynamic annotations for signals
        last_close = df["close"].iloc[-1]
        rsi = talib.RSI(df["close"])[-1]

        fig.add_annotation(
            x=df.index[-1],
            y=last_close,
            text=f"RSI: {rsi:.1f}",
            showarrow=True,
            arrowhead=1,
            arrowcolor="#00ff00" if rsi < 30 else "#ff0000" if rsi > 70 else "#ffffff",
        )

        return fig

    def create_signal_panel(self, signals: Dict) -> html.Div:
        """Create an animated signal panel with visual alerts."""
        return html.Div(
            [
                html.Div(
                    [
                        html.H3(signal["name"], style={"color": signal["color"]}),
                        html.H4(signal["value"], style={"animation": "pulse 2s infinite"}),
                        html.P(signal["description"], style={"opacity": "0.8"}),
                    ],
                    className="signal-card",
                )
                for signal in signals
            ]
        )

    def run(self, port: int = 8050, debug: bool = True):
        """Run the dashboard server."""
        self.app.run(port=port, debug=debug)


if __name__ == "__main__":
    # Add CSS for animations
    app_css = """
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .signal-card {
        background: linear-gradient(45deg, #1a1a1a, #2a2a2a);
        border-radius: 10px;
        padding: 15px;
        margin: 10px;
        box-shadow: 0 4px 6px rgba(0,255,0,0.1);
        transition: all 0.3s ease;
    }
    
    .signal-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 8px rgba(0,255,0,0.2);
    }
    
    .alert-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 20px;
        padding: 20px;
    }
    """

    dashboard = AnimatedTradingDashboard()
    dashboard.run()
