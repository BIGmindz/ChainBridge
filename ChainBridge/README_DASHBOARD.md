# BensonBot Enhanced Dashboard

A powerful, real-time dashboard for monitoring and analyzing trading bot performance.

## Features

- Real-time Market Metrics

  - Market Regime Indicator

  - Dynamic RSI Period Display

  - Trend Strength Measurement

  - Volatility Analysis

- Advanced Technical Analysis

  - Interactive Candlestick Charts

  - Volume Profile Analysis

  - Multiple Technical Indicators

  - Trading Signal Visualization

- Performance Analytics

  - Win Rate & Profit Factor

  - Sharpe Ratio

  - Maximum Drawdown

  - Trade Statistics

- User-Configurable Interface

  - Adjustable Update Intervals

  - Multiple Timeframe Selection

  - Customizable Indicators

  - Dark Theme Optimized

## Quick Start

1. Setup the environment:

```bash

make venv
make install

```text

1. Run the dashboard:

```bash

./run_dashboard.sh

```text

1. Access the dashboard at: `http://localhost:8050`

## Data Sources

The dashboard automatically reads:

- Trade data from CSV files in `data/` directory

- Real-time market data from configured exchanges

- Technical indicators and signals from the trading bot

## Configuration

- Update intervals can be adjusted in the dashboard UI

- Default port (8050) can be modified in `run_dashboard.sh`

- Indicator settings are configurable through the UI

- Color schemes and layouts follow system dark/light mode

## Requirements

- Python 3.11+

- Required packages:

  - dash

  - dash-bootstrap-components

  - plotly

  - pandas

  - numpy

All dependencies are automatically installed by the setup script.
