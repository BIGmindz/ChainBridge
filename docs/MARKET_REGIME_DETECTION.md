# Market Regime Detection for Multi-Signal Trading Bot

## Overview

The market regime detection feature enhances the multi-signal trading engine by automatically identifying different market conditions (bull, bear, sideways) and optimizing signal weights accordingly. This allows the trading algorithm to adapt to changing market conditions without manual intervention.

## Key Features

- **Automatic Market Regime Detection**: Identifies bull, bear, and sideways markets using price action analysis
- **Regime-Specific Signal Optimization**: Adjusts signal weights based on the detected market regime
- **Confidence-Based Adaptation**: Higher confidence in regime detection leads to stronger weight adjustments
- **Performance Tracking by Regime**: Analyzes trading performance in different market conditions
- **Visualization Tools**: Provides visual analysis of regime detection and signal performance

## How It Works

### Market Regime Classification

The `MarketRegimeDetector` class analyzes price data to detect the current market regime:

- **Bull Market**: Strong uptrend with consistent higher highs and higher lows
- **Bear Market**: Strong downtrend with consistent lower highs and lower lows
- **Sideways Market**: Range-bound price action without a clear trend
- **Unknown**: Not enough data to determine the market regime

### Signal Optimization by Regime

Each signal category is weighted differently depending on the market regime:

#### Bull Markets

- **Technical Indicators**: 1.2x weight (trends are more reliable)
- **Sentiment**: 0.8x weight (to avoid FOMO-driven decisions)
- **On-chain**: 1.3x weight (confirms strength of bull runs)
- **Proprietary**: 1.1x weight (boosted for unique insights)

#### Bear Markets

- **Technical Indicators**: 1.0x weight (neutral)
- **Sentiment**: 1.3x weight (crucial in bear markets)
- **On-chain**: 1.2x weight (shows capital flows in bear markets)
- **Proprietary**: 1.1x weight (boosted for unique insights)

#### Sideways Markets

- **Technical Indicators**: 1.3x weight (most useful in ranging markets)
- **Sentiment**: 0.7x weight (less useful in sideways markets)
- **On-chain**: 0.9x weight (less useful in sideways markets)
- **Proprietary**: 1.2x weight (boosted for unique insights)

### Position Sizing Adjustments

Position sizes are automatically adjusted based on the market regime:

- **Bull Markets**: Larger position sizes for BUY signals (1.2x)
- **Bear Markets**: Larger position sizes for SELL signals (1.2x)
- **Sideways Markets**: Reduced position sizes (0.8x) to account for higher uncertainty

## Usage

### Basic Implementation

```python
# Initialize trading engine with regime detection
from src.core.unified_trading_engine import MultiSignalTradingEngine

# Create engine with regime detection enabled
engine = MultiSignalTradingEngine(enhanced_ml=True, regime_aware=True)

# Collect signals with price data for regime detection
signals = await engine.collect_all_signals(current_price=19500.0, current_volume=1250.0)

# Make trading decision with regime awareness
decision = engine.make_ml_decision(signals)

# Get current regime information
current_regime = decision.get('regime')
regime_confidence = decision.get('regime_confidence')
print(f"Current market regime: {current_regime} (confidence: {regime_confidence:.2f})")
```

### Accessing Regime Performance

```python
# Get performance statistics with regime breakdowns
stats = engine.get_performance_stats()

# Access regime-specific performance
regime_performance = stats.get('regime_performance', {})

# Print performance by regime
for regime, perf in regime_performance.items():
    print(f"{regime.upper()}: {perf['trades']} trades, Win rate: {perf['win_rate']:.2f}%")

# Get visualization data
viz_data = engine.get_regime_visualization_data()
```

## Example

Run the included example script to see the market regime detection in action:

```bash
python examples/market_regime_demo.py
```

This will:

1. Simulate 30 days of price data across different market regimes
2. Run the trading engine with regime detection
3. Generate visualizations of regime detection and trading performance
4. Save performance statistics to `market_regime_stats.json`

## Visualization Outputs

The example script generates two visualization files:

- `market_regime_simulation.png`: Shows price action with detected regimes and PnL
- `signal_regime_performance.png`: Shows signal performance by market regime

## Configuration

You can customize the regime detection parameters in the `MarketRegimeDetector` class:

```python
# Custom regime detection thresholds
detector = MarketRegimeDetector(lookback_period=14)
detector.trend_threshold = 0.20  # 20% price change to indicate bull/bear
detector.volatility_threshold = 0.08  # 8% average daily change for high volatility
```

## Requirements

- NumPy for mathematical operations
- Matplotlib for visualizations (optional, for examples only)

## Integration with Existing Systems

This feature integrates seamlessly with the existing ML-based weight adaptation system, providing an additional layer of optimization based on market conditions.
