# Regime-Based Trading Strategies Documentation

This document provides comprehensive guidance on implementing and optimizing trading strategies across different market regimes.

## Table of Contents

1. [Introduction to Market Regimes](#introduction-to-market-regimes)
2. [Identifying Market Regimes](#identifying-market-regimes)
3. [Regime-Specific Strategy Optimization](#regime-specific-strategy-optimization)
4. [Backtesting Across Different Regimes](#backtesting-across-different-regimes)
5. [Performance Visualization and Analysis](#performance-visualization-and-analysis)
6. [Implementation Guide](#implementation-guide)
7. [Best Practices](#best-practices)
8. [Advanced Topics](#advanced-topics)

## Introduction to Market Regimes

Market regimes represent distinct periods in financial markets characterized by specific patterns of price action, volatility, and correlation between assets. Trading strategies that adapt to these different regimes typically outperform static approaches.

### Key Market Regimes

1. **Bullish (Uptrend)**
   - Characterized by rising prices, lower volatility
   - Often accompanied by positive economic indicators
   - Technical indicators: Higher highs and higher lows, prices above major moving averages

2. **Bearish (Downtrend)**
   - Characterized by falling prices, often with higher volatility
   - May be triggered by negative economic news or market sentiment
   - Technical indicators: Lower highs and lower lows, prices below major moving averages

3. **Sideways (Range-bound)**
   - Characterized by horizontal price movement within a range
   - Often represents market indecision or consolidation
   - Technical indicators: Price oscillating between clear support and resistance levels

4. **Volatile (Choppy)**
   - Characterized by large price swings with no clear direction
   - Often occurs during major market events or economic uncertainty
   - Technical indicators: High ATR (Average True Range), wide Bollinger Bands

5. **Low-Volatility**
   - Characterized by small price movements and low trading volume
   - Often occurs during holiday periods or before major announcements
   - Technical indicators: Low ATR, narrow Bollinger Bands

## Identifying Market Regimes

Several methods can be used to identify market regimes:

### Statistical Methods

```python
def detect_regime_statistical(prices, window=50):
    """
    Detect market regime using statistical measures.

    Args:
        prices: Array of historical prices
        window: Lookback period for calculations

    Returns:
        Identified regime and confidence level
    """
    returns = np.diff(prices) / prices[:-1]

    # Calculate key metrics
    volatility = np.std(returns[-window:]) * np.sqrt(252)  # Annualized
    trend = np.mean(returns[-window:]) * 252  # Annualized

    # Simple regime classification
    if abs(trend) < 0.05:  # Low trend
        if volatility < 0.10:
            return "SIDEWAYS_LOW_VOL", 0.8
        else:
            return "CHOPPY", 0.7
    elif trend > 0:  # Positive trend
        if volatility < 0.15:
            return "BULLISH", 0.85
        else:
            return "BULLISH_VOLATILE", 0.75
    else:  # Negative trend
        if volatility < 0.20:
            return "BEARISH", 0.8
        else:
            return "BEARISH_VOLATILE", 0.9
```

### Technical Indicators

- **Moving Averages**: Price above/below major moving averages, MA slope
- **Bollinger Bands Width**: Measure of volatility
- **ADX (Average Directional Index)**: Strength of trends
- **RSI (Relative Strength Index)**: Overbought/oversold conditions

### Market Breadth Indicators

- Advance/Decline Line
- Number of stocks above 50/200-day moving average
- New highs vs. new lows

### Example Implementation

```python
def detect_regime_technical(prices, volumes=None):
    """
    Detect market regime using technical indicators.

    Args:
        prices: Array of historical prices
        volumes: Optional array of trading volumes

    Returns:
        Identified regime and confidence level
    """
    # Calculate indicators
    sma50 = calculate_sma(prices, 50)
    sma200 = calculate_sma(prices, 200)

    bollinger_width = calculate_bollinger_width(prices, 20)
    adx = calculate_adx(prices, 14)

    # Logic for regime detection
    trend_strength = adx[-1]
    vol_level = bollinger_width[-1] / np.mean(bollinger_width[-50:])

    price_above_ma = prices[-1] > sma50[-1] > sma200[-1]
    price_below_ma = prices[-1] < sma50[-1] < sma200[-1]

    # Classify regime
    if trend_strength > 25:
        if price_above_ma:
            return "BULLISH", min(0.5 + trend_strength/100, 0.95)
        elif price_below_ma:
            return "BEARISH", min(0.5 + trend_strength/100, 0.95)

    if vol_level > 1.5:
        return "VOLATILE", min(0.5 + (vol_level-1)/2, 0.9)

    return "SIDEWAYS", 0.7
```

## Regime-Specific Strategy Optimization

Different strategies perform better in different market regimes. Here's how to optimize strategies for each regime:

### Bullish Regime Strategies

- **Trend Following**: Works well in strong bullish trends
- **Breakout Trading**: Effective for capturing continuation moves
- **Parameter Adjustments**:
  - Longer holding periods
  - Trailing stops rather than fixed stops
  - Higher overbought thresholds for oscillators

### Bearish Regime Strategies

- **Short Selling**: More effective in established downtrends
- **Mean Reversion**: Can work for counter-trend rallies
- **Parameter Adjustments**:
  - Tighter stop losses
  - Lower oversold thresholds for oscillators
  - Faster moving averages for trend identification

### Sideways Regime Strategies

- **Range Trading**: Buy at support, sell at resistance
- **Option Strategies**: Iron condors, short strangles
- **Parameter Adjustments**:
  - Narrower entry/exit thresholds
  - Shorter holding periods
  - More emphasis on support/resistance levels

### Volatile Regime Strategies

- **Volatility-based Position Sizing**: Reduce position size
- **Option Strategies**: Long straddles/strangles
- **Parameter Adjustments**:
  - Wider stop losses
  - Shorter holding periods
  - Less frequent trading

### Parameter Optimization Example

```python
# RSI strategy parameters by regime
regime_specific_params = {
    "BULLISH": {
        "rsi_period": 14,
        "overbought": 80,  # Higher threshold in bull markets
        "oversold": 40,    # Higher oversold threshold too
        "stop_loss": 7,    # Wider stop loss
        "take_profit": 15  # Larger profit targets
    },
    "BEARISH": {
        "rsi_period": 10,  # Faster RSI response
        "overbought": 60,  # Lower threshold in bear markets
        "oversold": 30,    # Standard oversold threshold
        "stop_loss": 5,    # Tighter stop loss
        "take_profit": 10  # Smaller profit targets
    },
    "SIDEWAYS": {
        "rsi_period": 14,
        "overbought": 70,  # Standard thresholds
        "oversold": 30,
        "stop_loss": 3,    # Very tight stop loss
        "take_profit": 5   # Smaller profit targets
    },
    "VOLATILE": {
        "rsi_period": 21,  # Slower RSI to filter noise
        "overbought": 75,
        "oversold": 25,    # More extreme thresholds
        "stop_loss": 15,   # Much wider stop loss
        "take_profit": 20  # Larger profit targets
    }
}
```

## Backtesting Across Different Regimes

Proper regime-specific backtesting involves:

1. **Regime Segmentation**: Divide historical data into different regime periods
2. **Separate Evaluation**: Test strategy performance within each regime separately
3. **Parameter Optimization**: Find optimal parameters for each regime
4. **Transition Management**: Test smooth transitions between regimes

### Using the RegimeBacktester

Our `RegimeBacktester` class facilitates this process:

```python
from src.backtesting.regime_backtester import RegimeBacktester
from src.backtesting.dashboard import create_dashboard

# Initialize backtester with price data and regime information
backtester = RegimeBacktester(price_data, regime_data, regime_labels)

# Define default strategy parameters
default_params = {
    "window": 14,
    "overbought": 70,
    "oversold": 30
}

# Define regime-specific parameters
regime_specific_params = {
    "Bullish": {"overbought": 75, "oversold": 40},
    "Bearish": {"overbought": 60, "oversold": 20},
    "Sideways": {"overbought": 65, "oversold": 35}
}

# Run backtest with regime-specific parameters
results = backtester.run_backtest(
    strategy_function,
    default_params,
    regime_specific_params
)

# Find best parameters for each regime
param_grid = {
    "window": [7, 14, 21],
    "overbought": [65, 70, 75, 80],
    "oversold": [20, 25, 30, 35]
}

best_params = backtester.get_best_parameters_by_regime(
    strategy_function,
    param_grid,
    "sharpe_ratio"  # Optimization metric
)

# Visualize results
create_dashboard(
    results,
    title="Strategy Performance by Market Regime"
)
```

## Performance Visualization and Analysis

The regime performance dashboard provides:

1. **Cumulative Returns by Regime**: Comparing performance across regimes
2. **Metrics Table**: Key metrics (Sharpe ratio, max drawdown, etc.) for each regime
3. **Regime Distribution**: Percentage of time spent in each regime
4. **Trade Analysis**: Distribution of buy/sell/hold signals by regime
5. **Risk Metrics**: Volatility and drawdown visualization

### Performance Metrics to Consider

For each regime, analyze:

- **Return Metrics**: Total return, annualized return, risk-adjusted return
- **Risk Metrics**: Volatility, max drawdown, Sortino ratio
- **Trade Metrics**: Win rate, profit factor, average win/loss
- **Exposure Metrics**: Time in market, number of trades

### Sample Performance Analysis

```python
# Print performance summary by regime
for regime, result in results.items():
    metrics = result['metrics']
    print(f"\n{regime} Regime:")
    print(f"  Total Return: {metrics['total_return']:.2%}")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
    print(f"  Win Rate: {metrics['win_rate']:.2%}")

    # Calculate additional metrics
    if 'returns' in result and len(result['returns']) > 0:
        returns = np.array(result['returns'])
        print(f"  Volatility: {np.std(returns) * np.sqrt(252):.2%}")
        print(f"  Sortino Ratio: {calculate_sortino(returns):.2f}")

    if 'signals' in result:
        signals = np.array(result['signals'])
        buys = np.sum(signals == 1)
        sells = np.sum(signals == -1)
        holds = np.sum(signals == 0)
        print(f"  Signal Distribution: Buy: {buys}, Sell: {sells}, Hold: {holds}")
```

## Implementation Guide

### Step 1: Integrate Regime Detection

```python
class MarketRegimeAwareTrader:
    def __init__(self):
        self.current_regime = "UNKNOWN"
        self.regime_confidence = 0.0
        self.regime_history = []

    def update_regime(self, prices, volumes=None):
        """Update current market regime based on recent data."""
        regime, confidence = detect_regime_technical(prices, volumes)

        # Apply smoothing to avoid frequent regime changes
        if confidence > 0.8 or len(self.regime_history) == 0:
            # High confidence or initial detection
            self.current_regime = regime
            self.regime_confidence = confidence
        elif regime != self.current_regime and confidence > self.regime_confidence:
            # New regime with higher confidence
            self.current_regime = regime
            self.regime_confidence = confidence

        # Store regime history
        self.regime_history.append((regime, confidence))
        if len(self.regime_history) > 20:
            self.regime_history.pop(0)
```

### Step 2: Select Regime-Specific Parameters

```python
def get_strategy_parameters(self):
    """Get the appropriate strategy parameters for the current regime."""
    base_params = {
        "rsi_period": 14,
        "overbought": 70,
        "oversold": 30,
        "stop_loss": 5,
        "take_profit": 10
    }

    # Apply regime-specific adjustments
    if self.current_regime == "BULLISH":
        base_params.update({
            "overbought": 80,
            "oversold": 40,
            "stop_loss": 7,
            "take_profit": 15
        })
    elif self.current_regime == "BEARISH":
        base_params.update({
            "rsi_period": 10,
            "overbought": 60,
            "stop_loss": 5
        })
    # Add other regimes...

    return base_params
```

### Step 3: Adjust Signal Generation

```python
def generate_trading_signals(self, prices, indicators):
    """Generate trading signals with regime-specific adjustments."""
    # Get appropriate parameters for current regime
    params = self.get_strategy_parameters()

    # Calculate indicators with regime-specific parameters
    rsi = calculate_rsi(prices, params["rsi_period"])

    # Generate signals with regime-specific thresholds
    signals = np.zeros_like(prices)
    for i in range(len(prices) - 1):
        if rsi[i] < params["oversold"]:
            signals[i] = 1  # Buy signal
        elif rsi[i] > params["overbought"]:
            signals[i] = -1  # Sell signal

    # Adjust signals based on regime confidence
    if self.regime_confidence < 0.6:
        # Lower confidence - reduce signal strength
        signals = signals * self.regime_confidence

    return signals
```

### Step 4: Implement Position Sizing

```python
def calculate_position_size(self, signal, price):
    """Calculate position size based on regime and signal strength."""
    base_size = 1.0  # Base position size (e.g., 1 unit or 1% of portfolio)

    # Adjust for regime
    regime_multiplier = 1.0
    if self.current_regime == "VOLATILE":
        regime_multiplier = 0.5  # Reduce size in volatile regimes
    elif self.current_regime == "BULLISH" and signal > 0:
        regime_multiplier = 1.2  # Increase size for buys in bullish regime
    elif self.current_regime == "BEARISH" and signal < 0:
        regime_multiplier = 1.2  # Increase size for sells in bearish regime

    # Adjust for signal strength
    signal_strength = min(abs(signal), 1.0)

    # Final position size
    position_size = base_size * regime_multiplier * signal_strength

    return position_size
```

## Best Practices

### 1. Regime Transitions

Handle transitions between regimes carefully to avoid excessive trading:

- Use time-weighted averaging of regime classifications
- Implement confidence thresholds before changing regimes
- Consider overlapping regime periods for gradual transitions

### 2. Avoiding Overfitting

Be cautious about overfitting regime-specific parameters:

- Use cross-validation across multiple regime cycles
- Keep parameter differences between regimes meaningful but not extreme
- Test on out-of-sample data that includes various regime types

### 3. Monitoring and Adaptation

Continuously monitor regime detection and performance:

- Log regime changes and their impact on performance
- Periodically re-optimize regime-specific parameters
- Consider ensemble methods that combine multiple regime detection approaches

### 4. Risk Management

Adjust risk management based on regime characteristics:

- Reduce position sizes in volatile regimes
- Set wider stops in trending regimes
- Consider correlation shifts between assets in different regimes

## Advanced Topics

### 1. Machine Learning for Regime Classification

Use supervised or unsupervised learning for regime detection:

```python
from sklearn.cluster import KMeans

def ml_regime_detection(market_features):
    """
    Detect market regimes using K-means clustering.

    Args:
        market_features: Feature array with columns for volatility, trend, etc.

    Returns:
        Array of regime labels
    """
    # Normalize features
    scaler = StandardScaler()
    normalized_features = scaler.fit_transform(market_features)

    # Cluster into regimes
    kmeans = KMeans(n_clusters=4, random_state=42)
    regimes = kmeans.fit_predict(normalized_features)

    return regimes
```

### 2. Hybrid Strategies

Implement hybrid strategies that combine elements from multiple approaches:

```python
def hybrid_strategy(prices, regime):
    """
    Hybrid strategy that adapts based on market regime.

    Args:
        prices: Price data
        regime: Current market regime

    Returns:
        Trading signal
    """
    if regime == "BULLISH":
        # Use trend following for bullish regimes
        return trend_following_strategy(prices)
    elif regime == "BEARISH":
        # Use combined trend and reversal for bearish regimes
        trend_signal = trend_following_strategy(prices)
        reversal_signal = mean_reversion_strategy(prices)
        return 0.7 * trend_signal + 0.3 * reversal_signal
    else:
        # Use mean reversion for sideways regimes
        return mean_reversion_strategy(prices)
```

### 3. Multi-timeframe Regime Analysis

Analyze regimes across multiple timeframes for more robust detection:

```python
def multi_timeframe_regime(daily_prices, hourly_prices, weekly_prices):
    """
    Detect market regime using multiple timeframes.

    Args:
        daily_prices: Daily price data
        hourly_prices: Hourly price data
        weekly_prices: Weekly price data

    Returns:
        Regime classification and confidence
    """
    daily_regime, daily_conf = detect_regime(daily_prices)
    hourly_regime, hourly_conf = detect_regime(hourly_prices)
    weekly_regime, weekly_conf = detect_regime(weekly_prices)

    # Weight by timeframe importance
    regimes = {
        daily_regime: daily_conf * 0.5,
        hourly_regime: hourly_conf * 0.3,
        weekly_regime: weekly_conf * 0.2
    }

    # Find dominant regime
    dominant_regime = max(regimes, key=regimes.get)
    confidence = regimes[dominant_regime]

    return dominant_regime, confidence
```

### 4. Portfolio Optimization by Regime

Adjust portfolio allocation based on current regime:

```python
def optimize_portfolio(assets, regime):
    """
    Optimize portfolio allocations based on current market regime.

    Args:
        assets: List of available assets
        regime: Current market regime

    Returns:
        Dictionary of asset allocations
    """
    allocations = {}

    if regime == "BULLISH":
        # Higher equity allocation in bullish regimes
        allocations = {
            "equity": 0.70,
            "bonds": 0.20,
            "gold": 0.05,
            "cash": 0.05
        }
    elif regime == "BEARISH":
        # More defensive allocation in bearish regimes
        allocations = {
            "equity": 0.30,
            "bonds": 0.40,
            "gold": 0.20,
            "cash": 0.10
        }
    elif regime == "VOLATILE":
        # More cash and hedges in volatile regimes
        allocations = {
            "equity": 0.40,
            "bonds": 0.25,
            "gold": 0.15,
            "cash": 0.20
        }
    else:  # SIDEWAYS
        # Balanced allocation in sideways markets
        allocations = {
            "equity": 0.50,
            "bonds": 0.30,
            "gold": 0.10,
            "cash": 0.10
        }

    return allocations
```

---

This documentation provides a comprehensive foundation for implementing and optimizing regime-based trading strategies. By adapting to different market conditions, these strategies can potentially achieve more consistent performance across varying market environments.
