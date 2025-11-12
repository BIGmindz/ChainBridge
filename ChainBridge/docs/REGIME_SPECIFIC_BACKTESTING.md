# Regime-Specific Backtesting

The regime-specific backtesting module allows you to evaluate trading performance across different market regimes (bull, bear, and sideways markets). This helps you understand how your trading strategy performs in different market conditions and optimize signal weights for each regime type.

## Overview

The regime-specific backtester:

1. Automatically identifies market regimes in historical price data

1. Runs backtests on the entire dataset and calculates performance metrics by regime

1. Runs separate backtests specifically on bull, bear, and sideways market periods

1. Analyzes how signal weights adapt to different market regimes

1. Generates comprehensive performance reports and visualizations

## Key Features

- **Regime Identification**: Automatically detects bull, bear, and sideways market regimes

- **Regime-Specific Performance**: Calculates win rate, PnL, and other metrics for each regime

- **Isolated Regime Testing**: Runs separate backtests on specific market regimes

- **ML Weight Adaptation**: Tracks how ML weights adapt in different market conditions

- **Visualization Tools**: Generates charts comparing performance across regimes

- **Performance Reports**: Creates detailed text reports with regime-specific metrics

## Usage

### Running the Backtester

```bash

## Run with synthetic data (demo mode)

./run_regime_backtest.py --demo

## Run with your own CSV data

./run_regime_backtest.py --data /path/to/your/price_data.csv --output results.json

## Run BTC example with enhanced dataset

./examples/btc_regime_backtest.py

```text

### CSV Data Format

Your CSV should include at least the following columns:

- `price` or `close`: Price data

- `date` (optional): Date information

- `volume` (optional): Volume data

Example:

```csv

date,close,volume
2024-01-01,45000.00,1000000
2024-01-02,45200.00,1200000
...

```text

### Programmatic Usage

```python

import asyncio
from src.backtesting.regime_backtester import RegimeBacktester

async def run_backtest():

## Initialize with price data

    backtester = RegimeBacktester(
        price_data=[45000, 45200, 45400, ...],
        volume_data=[1000000, 1200000, 900000, ...],
        dates=['2024-01-01', '2024-01-02', ...]
    )

## Run full backtest across all regimes

    full_results = await backtester.run_full_backtest()

## Run separate backtests for each regime

    bull_results = await backtester.backtest_specific_regime('bull')
    bear_results = await backtester.backtest_specific_regime('bear')
    sideways_results = await backtester.backtest_specific_regime('sideways')

## Or run all regime-specific backtests at once

    regime_results = await backtester.compare_all_regimes()

## Generate visualizations

    backtester.visualize_regime_performance(full_results)

## Save results to file

    backtester.save_results(full_results, 'backtest_results.json')

## Generate performance report

    report = backtester.generate_regime_report(full_results)
    print(report)

## Run the async function

asyncio.run(run_backtest())

```text

## Output Files

The backtester generates several output files:

- `regime_backtest_results.json`: Full backtest results with regime-specific metrics

- `regime_comparison_results.json`: Results from regime-specific backtests

- `regime_performance_comparison.png`: Chart showing win rates and PnL by regime

- `regime_distribution.png`: Chart showing trade distribution across regimes

- `enhanced_btc_dataset.png`: (BTC example only) Visualization of the price dataset with regime markers

## Performance Metrics

The backtester calculates and reports the following metrics:

### Overall Metrics

- Total trades executed

- Overall win rate

- Total and average PnL

- ML adaptation score

### Regime-Specific Metrics

- Trades per regime

- Win rate per regime

- PnL per regime

- Average PnL per trade in each regime

### ML Adaptation Metrics

- Weight changes by signal

- Initial vs final weights

- Category adaptation by regime

## Example Report

## ```plaintext

## MARKET REGIME BACKTEST REPORT

OVERALL PERFORMANCE:
Total Trades: 166
Win Rate: 37.95%
Total PnL: 341.75
Avg PnL per Trade: 2.06

REGIME DISTRIBUTION:
BULL: 60 data points (33.3%)
BEAR: 60 data points (33.3%)
SIDEWAYS: 60 data points (33.3%)

PERFORMANCE BY REGIME:
BULL MARKET:
  Trades: 56
  Win Rate: 60.71%
  Total PnL: 387.24
  Avg PnL per Trade: 6.91

BEAR MARKET:
  Trades: 55
  Win Rate: 23.64%
  Total PnL: -112.38
  Avg PnL per Trade: -2.04

SIDEWAYS MARKET:
  Trades: 55
  Win Rate: 29.09%
  Total PnL: 66.89
  Avg PnL per Trade: 1.22

ML WEIGHT ADAPTATION:
rsi: +3.42% change (0.1200 → 0.1241)
macd: +1.75% change (0.1000 → 0.1018)
bollinger: -2.28% change (0.0800 → 0.0782)
volume: -1.03% change (0.0800 → 0.0792)
fear_greed: +0.86% change (0.1500 → 0.1513)
social: -2.90% change (0.1000 → 0.0971)
whale: -0.24% change (0.1200 → 0.1197)
flows: +0.17% change (0.1000 → 0.1002)

## proprietary: +0.52% change (0.1500 → 0.1508)

```text

## Customization

You can customize the regime detection parameters in the `MarketRegimeDetector` class:

```python

## Access regime detector through the trading engine

engine = backtester.engine
regime_detector = engine.regime_detector

## Customize parameters

regime_detector.lookback_period = 21  # Default is 14
regime_detector.trend_threshold = 0.12  # Default is 0.10
regime_detector.volatility_threshold = 0.05  # Default is 0.04

```text

## Integration with ML Optimization

The regime-specific backtester works with the ML weight adaptation system to:

1. Track how weights change in different market regimes

1. Identify which signals perform best in each regime

1. Optimize initial weights based on expected market conditions

## Best Practices

For the most meaningful results:

1. Use sufficient historical data (at least 6 months recommended)

1. Include data covering different market regimes

1. Run backtests with both default and optimized signal weights

1. Compare regime-specific performance to identify strengths and weaknesses

1. Consider adjusting signal weights based on the current market regime

## Requirements

- NumPy for mathematical operations

- Matplotlib for visualizations (optional)

- Pandas for data loading (optional)
