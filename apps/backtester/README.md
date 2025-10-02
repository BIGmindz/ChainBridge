# High-Fidelity Backtesting Engine

A production-grade backtesting engine designed for the "Pattern as a Service" architecture.

## Features

- **Realistic Trading Simulation**: Includes fees, slippage, and position sizing
- **Comprehensive Performance Metrics**: Sharpe ratio, Sortino ratio, max drawdown, total return
- **Professional Reporting**: Markdown reports and interactive equity curve charts
- **Multi-Strategy Support**: Automatically discovers and backtests all strategies
- **ML Model Integration**: Loads trained models and scalers from strategy directories



## Usage

### Basic Usage

```bash
# Run all strategies
python apps/backtester/backtester.py

# Or from project root
python -m apps.backtester.backtester
```

### Prerequisites

1. **Trained Models**: Ensure strategies have trained `model.pkl` and `scaler.pkl` files
2. **Historical Data**: `data/consolidated_market_data.csv` must exist
3. **Strategy Configs**: Each strategy needs a valid `config.yaml`



### Data Format

The backtester expects historical data in CSV format with columns:

- `timestamp`: DateTime index
- `symbol`: Trading symbol (e.g., 'BTC/USD')
- `price`: Asset price
- Additional feature columns as defined in strategy configs



## Output

For each strategy, the backtester generates:

1. **Performance Report** (`strategies/{strategy}/backtest_report.md`)
   - Total return percentage
   - Final portfolio value
   - Sharpe ratio
   - Maximum drawdown

2. **Equity Curve Chart** (`strategies/{strategy}/backtest_equity_curve.html`)
   - Interactive Plotly chart
   - Portfolio value over time



## Configuration

Strategies are configured via their `config.yaml` files:

```yaml
trading:
  initial_capital: 10000
  fees:
    taker_bps: 25  # 0.25% fee

signals:
  machine_learning:
    features: ['rsi_value', 'price_change_pct', 'volume']

exchange:
  symbols: ['BTC/USD', 'ETH/USD']
```

## Architecture

The backtester follows the "Pattern as a Service" architecture:

1. **Strategy Discovery**: Automatically finds all strategy directories
2. **Model Loading**: Loads trained ML models and scalers
3. **Feature Engineering**: Prepares features as defined in config
4. **Signal Generation**: Uses ML models to generate trading signals
5. **Trade Simulation**: Realistic execution with fees and position sizing
6. **Performance Analysis**: Calculates comprehensive metrics
7. **Report Generation**: Creates professional reports and visualizations



## Dependencies

- pandas
- numpy
- scikit-learn
- joblib
- plotly
- pyyaml



## Error Handling

The backtester includes robust error handling for:

- Missing model files
- Invalid configurations
- Data format issues
- Feature mismatches



Failed strategies are logged but don't stop the overall backtesting process.
