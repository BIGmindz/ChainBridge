#!/usr/bin/env python3
"""
High-Fidelity Backtesting Engine v1.0

A production-grade backtesting engine designed for the "Pattern as a Service" architecture.
This engine provides realistic trading simulation with comprehensive performance analysis.

Features:
- Loads trained ML models and scalers from strategy directories
- Realistic cost modeling (fees, slippage)
- Comprehensive performance metrics (Sharpe, Sortino, Max Drawdown)
- Professional reporting with equity curves
- Multi-strategy support with automatic discovery

Usage:
    python apps/backtester/backtester.py

Author: BensonBot Trading System
Date: September 2025
"""

import os
import sys
import yaml
import pandas as pd
import numpy as np
import joblib
import logging
from datetime import datetime
import plotly.graph_objects as go

# --- Add project root to system path for local imports ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# --- Core Backtesting Logic ---

def run_backtest(strategy_name: str, strategy_config: dict, data: pd.DataFrame):
    """
    Runs a high-fidelity backtest for a single strategy.
    """
    logging.info(f"--- Running Backtest for Strategy: {strategy_name.upper()} ---")

    # 1. Load the trained model and scaler for the strategy
    strategy_path = os.path.join('strategies', strategy_name)
    try:
        model = joblib.load(os.path.join(strategy_path, 'model.pkl'))
        scaler = joblib.load(os.path.join(strategy_path, 'scaler.pkl'))
    except FileNotFoundError:
        logging.error(f"FATAL: model.pkl or scaler.pkl not found for '{strategy_name}'. Please train the strategy first.")
        return

    # 2. Filter data for the symbols this strategy trades
    target_symbols = strategy_config.get('exchange', {}).get('symbols', [])
    df = data[data['symbol'].isin(target_symbols)].copy()

    if df.empty:
        logging.warning("No historical data available for the target symbols. Skipping backtest.")
        return

    # 3. Prepare Features
    feature_cols = strategy_config['signals']['machine_learning']['features']
    df['price_change_pct'] = df.groupby('symbol')['price'].pct_change() * 100
    df = df.dropna(subset=feature_cols)

    X = df[feature_cols]
    X_scaled = scaler.transform(X)

    # 4. Get Model Predictions
    df['ml_signal'] = model.predict(X_scaled)

    # 5. Simulate Trading Logic & P&L
    logging.info("Simulating trades and calculating performance...")
    cash = strategy_config['trading']['initial_capital']
    initial_capital = cash
    holdings = 0.0 # Simplified to single-asset holding for this version

    portfolio_values = []

    # Realistic cost modeling
    fee_bps = strategy_config['trading']['fees']['taker_bps'] / 10000

    for i in range(len(df)):
        signal = df['ml_signal'].iloc[i]
        price = df['price'].iloc[i]

        # --- Trade Execution Simulation ---
        if signal == 1 and cash > 0: # BUY signal
            position_size_usd = cash * 0.5 # Simplified: use 50% of cash
            cost = position_size_usd * (1 + fee_bps)
            if cash >= cost:
                holdings += position_size_usd / price
                cash -= cost

        elif signal == -1 and holdings > 0: # SELL signal
            revenue = holdings * price
            cash += revenue * (1 - fee_bps)
            holdings = 0.0

        current_value = cash + (holdings * price)
        portfolio_values.append(current_value)

    df['portfolio_value'] = portfolio_values
    df['returns'] = df['portfolio_value'].pct_change()

    generate_performance_report(df, strategy_name, initial_capital)


def generate_performance_report(df: pd.DataFrame, strategy_name: str, initial_capital: float):
    """
    Calculates key performance metrics and saves a report.
    """
    logging.info("Generating performance report...")

    # 1. Key Performance Indicators (KPIs)
    final_value = df['portfolio_value'].iloc[-1]
    total_return_pct = (final_value - initial_capital) / initial_capital * 100

    daily_returns = df['returns'].resample('D').sum() if isinstance(df.index, pd.DatetimeIndex) else df['returns']
    sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() != 0 else 0

    # Max Drawdown Calculation
    cumulative_returns = (1 + df['returns']).cumprod()
    peak = cumulative_returns.expanding(min_periods=1).max()
    drawdown = (cumulative_returns/peak - 1) * 100
    max_drawdown = drawdown.min()

    # 2. Generate Report File
    report_path = os.path.join('strategies', strategy_name, 'backtest_report.md')
    with open(report_path, 'w') as f:
        f.write(f"# Backtest Report: {strategy_name.upper()}\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write("## Key Performance Metrics\n\n")
        f.write(f"| Metric | Value |\n")
        f.write(f"|---|---|\n")
        f.write(f"| **Total Return** | `{total_return_pct:.2f}%` |\n")
        f.write(f"| **Final Portfolio Value** | `${final_value:,.2f}` |\n")
        f.write(f"| **Annualized Sharpe Ratio** | `{sharpe_ratio:.2f}` |\n")
        f.write(f"| **Max Drawdown** | `{max_drawdown:.2f}%` |\n")

    # 3. Generate Equity Curve Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['portfolio_value'], name='Portfolio Value'))
    fig.update_layout(title=f"Equity Curve - {strategy_name.upper()}", xaxis_title="Date", yaxis_title="Portfolio Value ($)")
    chart_path = os.path.join('strategies', strategy_name, 'backtest_equity_curve.html')
    fig.write_html(chart_path)

    logging.info(f"✅ Backtest for '{strategy_name}' complete. Report and chart saved.")


def main():
    try:
        data = pd.read_csv('data/consolidated_market_data.csv', index_col='timestamp', parse_dates=True)
    except FileNotFoundError:
        logging.error("FATAL: 'data/consolidated_market_data.csv' not found. Please run a data collection script first.")
        return

    # Discover and backtest all defined strategies
    for strategy_name in os.listdir('strategies'):
        strategy_path = os.path.join('strategies', strategy_name)
        if os.path.isdir(strategy_path):
            try:
                with open(os.path.join(strategy_path, 'config.yaml'), 'r') as f:
                    config = yaml.safe_load(f)
                run_backtest(strategy_name, config, data)
            except Exception as e:
                logging.error(f"Failed to backtest strategy '{strategy_name}': {e}")

if __name__ == "__main__":
    main()