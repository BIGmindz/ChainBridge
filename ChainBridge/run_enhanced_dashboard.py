"""
Enhanced Multi-Signal Trading Dashboard Runner
"""

import argparse
import ccxt
import pandas as pd
from dash import Input, Output
from modules.animated_dashboard import AnimatedTradingDashboard
import os
import yaml
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def fetch_market_data(
    exchange_id: str, symbol: str = "BTC/USD", timeframe: str = "1m", limit: int = 100
):
    """Fetch real-time market data from exchange."""
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class(
            {
                "apiKey": os.getenv("API_KEY", "1234"),
                "secret": os.getenv("API_SECRET", "dummy"),
                "enableRateLimit": True,
            }
        )

        # Fetch OHLCV data
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv:
            logger.error("No data received from exchange")
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(
            ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")  # type: ignore
        df.set_index("timestamp", inplace=True)

        # Convert string values to float
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)  # type: ignore

        logger.info(f"Fetched {len(df)} candles from {exchange_id}")
        return df

    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        return pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(description="Enhanced Trading Dashboard")
    parser.add_argument("config", help="Path to config file")
    parser.add_argument("--port", type=int, default=8050, help="Dashboard port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Initialize dashboard
    dashboard = AnimatedTradingDashboard()

    # Set up data callbacks
    @dashboard.app.callback(
        Output("main-chart", "figure"), Input("chart-interval", "n_intervals")
    )
    def update_main_chart(n):
        df = fetch_market_data(
            os.getenv("EXCHANGE", "kraken"),
            config["trading"]["symbol"],
            config["trading"]["timeframe"],
        )
        if df is not None:
            return dashboard.update_main_chart(df)
        return {}

    @dashboard.app.callback(
        Output("indicator-grid", "figure"), Input("indicator-interval", "n_intervals")
    )
    def update_indicators(n):
        df = fetch_market_data(
            os.getenv("EXCHANGE", "kraken"),
            config["trading"]["symbol"],
            config["trading"]["timeframe"],
        )
        if df is not None:
            return dashboard.update_indicator_grid(df)
        return {}

    @dashboard.app.callback(
        Output("live-clock", "children"), Input("interval-component", "n_intervals")
    )
    def update_clock(n):
        return f"🕒 {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Run dashboard
    dashboard.run(port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
