# Kraken Paper Trading Module

## Professional Paper Trading Engine with ML Integration

A comprehensive paper trading implementation specifically designed for the Kraken exchange with real-time price feeds, advanced risk management, and machine learning integration.

### 🌟 Key Features

- **Real-time Price Feeds**: Live price data simulation via CCXT integration
- **Advanced Risk Management**: Position sizing, correlation adjustments, drawdown protection
- **ML Signal Integration**: Seamless connection with existing signal modules
- **Position Tracking**: Detailed P&L calculation and performance metrics
- **Trade Journal**: Complete trade logging and export capabilities
- **Performance Analytics**: Sharpe ratio, win rate, profit factor, and more
- **WebSocket Simulation**: Real-time data feed simulation
- **Emergency Risk Controls**: Automatic position closure on risk limit breaches



### 📁 Module Structure

```text
src/
├── kraken_paper_live_bot.py      # Core paper trading engine
├── ml_trading_integration.py     # ML signal integration layer
└── exchange_adapter.py           # Existing exchange adapter

config/
└── kraken_paper_trading.yaml     # Configuration file

examples/
└── kraken_paper_trading_demo.py  # Comprehensive demo

test_kraken_paper_trading.py      # Validation tests
```

### 🚀 Quick Start

#### 1. Basic Setup

```python
from src.kraken_paper_live_bot import create_kraken_paper_bot

# Create bot with default configuration
bot = create_kraken_paper_bot(config_path="config/kraken_paper_trading.yaml")

# Or with direct configuration
config = {
    'initial_capital': 10000.0,
    'symbols': ['BTC/USD', 'ETH/USD'],
    'risk_management': {
        'max_position_size': 0.1,
        'max_drawdown_limit': 0.15
    }
}
bot = create_kraken_paper_bot(config_dict=config)
```

#### 2. Open Trading Position

```python
# Open a position with ML confidence
result = bot.open_position(
    symbol='BTC/USD',
    side='BUY',
    signal_confidence=0.75,  # ML model confidence
    volatility=0.04,         # Historical volatility
    stop_loss_pct=0.03,      # 3% stop loss
    take_profit_pct=0.06,    # 6% take profit
    tags=['ml_signal', 'momentum']
)

if result['success']:
    position = result['position']
    print(f"Position opened: {position.symbol} {position.side}")
    print(f"Entry: ${position.entry_price:.2f}")
    print(f"Stop Loss: ${position.stop_loss:.2f}")
    print(f"Take Profit: ${position.take_profit:.2f}")
```

#### 3. Monitor Performance

```python
# Get comprehensive performance dashboard
dashboard = bot.get_performance_dashboard()

print(f"Portfolio Value: ${dashboard['account']['portfolio_value']:,.2f}")
print(f"Total Return: {dashboard['account']['total_return_pct']:+.2f}%")
print(f"Win Rate: {dashboard['performance']['win_rate']:.1f}%")
print(f"Sharpe Ratio: {dashboard['performance']['sharpe_ratio']:.2f}")
```

#### 4. ML Integration

```python
from src.ml_trading_integration import MLTradingIntegration

# Create ML integration
ml_integration = MLTradingIntegration(bot, module_manager, config)

# Process signals for all symbols
symbols = ['BTC/USD', 'ETH/USD', 'ADA/USD']
results = await ml_integration.process_trading_signals(symbols)

for symbol, result in results.items():
    if result['decision']['action'] != 'HOLD':
        print(f"{symbol}: {result['decision']['action']} "
              f"(confidence: {result['decision']['confidence']:.2f})")
```

### 🎛️ Configuration

The `config/kraken_paper_trading.yaml` file provides comprehensive configuration options:

#### Core Settings

```yaml
initial_capital: 10000.0
symbols: ["BTC/USD", "ETH/USD", "ADA/USD"]
exchange: "kraken"
```

#### Risk Management

```yaml
risk_management:
  max_position_size: 0.1          # 10% max per position
  max_risk_per_trade: 0.02        # 2% risk per trade
  correlation_threshold: 0.7       # Correlation limit
  max_drawdown_limit: 0.15        # 15% max drawdown
  stop_loss_pct: 0.03             # Default 3% stop loss
  take_profit_pct: 0.06           # Default 6% take profit
```

#### ML Integration

```yaml
ml_integration:
  confidence_threshold: 0.6        # Minimum confidence to trade
  cooldown_minutes: 30            # Cooldown between signals
  signal_weights:
    rsi: 0.25
    macd: 0.30
    bollinger_bands: 0.20
    sentiment: 0.25
```

### 🔧 Advanced Features

#### 1. Real-time Price Feeds

```python
# Initialize exchange connection
await bot.initialize_exchange(exchange)

# Start WebSocket simulation
await bot.run_live_trading()
```

#### 2. Correlation-based Position Sizing

The bot automatically adjusts position sizes based on correlation:

- Similar assets (BTC/ETH) get reduced allocation
- Different asset classes maintain full allocation
- Real-time correlation monitoring



#### 3. Dynamic Risk Management

```python
# Check risk limits
bot._check_risk_limits()

# Emergency stop if drawdown exceeds limit
if current_drawdown > max_drawdown_limit:
    bot._emergency_close_all_positions()
```

#### 4. Trade Journal Export

```python
# Export complete trade history
journal_path = bot.export_trade_journal()
print(f"Trade journal exported to: {journal_path}")
```

### 📊 Performance Tracking

#### Key Metrics

- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / Gross loss
- **Sharpe Ratio**: Risk-adjusted return metric
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Average Win/Loss**: Mean profit and loss per trade



#### Real-time Monitoring

```python
# Get performance metrics
metrics = bot.performance

print(f"Total Trades: {metrics.total_trades}")
print(f"Win Rate: {metrics.win_rate:.1%}")
print(f"Profit Factor: {metrics.profit_factor:.2f}")
print(f"Sharpe Ratio: {bot._calculate_sharpe_ratio(daily_returns):.2f}")
```

### 🤖 ML Signal Integration

#### Supported Signal Types

- **RSI**: Relative Strength Index signals
- **MACD**: Moving Average Convergence Divergence
- **Bollinger Bands**: Volatility-based signals
- **Volume Profile**: Volume-based momentum
- **Sentiment Analysis**: Market sentiment indicators



#### Signal Processing

```python
# Aggregate signals with confidence weighting
aggregated_signal = ml_integration._aggregate_signals(signal_data, symbol)

print(f"Final Signal: {aggregated_signal['signal']}")
print(f"Confidence: {aggregated_signal['confidence']:.2f}")
print(f"Signal Count: {aggregated_signal['signal_count']}")
```

#### Performance Feedback Loop

```python
# Update signal performance based on trade outcomes
ml_integration.update_signal_performance(position_id, 'WIN', pnl=150.0)

# Get signal performance report
report = ml_integration.get_signal_performance_report()
print(f"Best performing module: {report['summary']['best_performing_module']}")
```

### 🧪 Testing and Validation

#### Run Basic Tests

```bash
python test_kraken_paper_trading.py
```

#### Run Demo

```bash
python examples/kraken_paper_trading_demo.py --demo all --duration 5
```

#### Demo Options

- `--demo basic`: Basic paper trading features
- `--demo ml`: ML signal integration
- `--demo risk`: Risk management features
- `--demo all`: Complete feature demonstration



### 🔌 Integration with Existing Bot

#### 1. Update Multi-Signal Bot

```python
from src.kraken_paper_live_bot import KrakenPaperLiveBot

class EnhancedMultiSignalBot:
    def __init__(self):
        # Existing initialization...

        # Add Kraken paper trading
        self.kraken_bot = KrakenPaperLiveBot(self.config)

    async def execute_trade_decision(self, symbol, decision):
        # Use Kraken bot for execution
        if decision['action'] in ['BUY', 'SELL']:
            result = self.kraken_bot.open_position(
                symbol=symbol,
                side=decision['action'],
                signal_confidence=decision['confidence'],
                volatility=decision.get('volatility', 0.03)
            )
            return result
        return {'action': 'HOLD'}
```

#### 2. Replace Budget Manager Calls

```python
# Old way
position_calc = budget_manager.calculate_position_size(symbol, confidence, volatility)

# New way with enhanced features
position_calc = kraken_bot.calculate_position_size(
    symbol, confidence, volatility, correlation_adj=0.8
)
```

#### 3. Enhanced Performance Tracking

```python
# Get comprehensive performance dashboard
dashboard = kraken_bot.get_performance_dashboard()

# Replace simple metrics with detailed analytics
performance_metrics = dashboard['performance']
risk_metrics = dashboard['risk_metrics']
```

### 📈 Production Deployment

#### 1. Environment Setup

```bash
# Install additional dependencies
pip install websockets asyncio

# Create log directory
mkdir -p logs/

# Set up configuration
cp config/kraken_paper_trading.yaml config/production.yaml
```

#### 2. Production Configuration

```yaml
# production.yaml
paper_trading:
  simulate_latency: true
  simulate_slippage: true
  simulate_fees: true
  execution_delay_ms: 100
  slippage_bps: 5
  commission_bps: 10

logging:
  level: "INFO"
  log_to_file: true
  log_file: "logs/kraken_paper_trading.log"
  log_rotation: "daily"
```

#### 3. Monitoring Setup

```python
# Set up periodic performance reporting
async def performance_monitor():
    while True:
        dashboard = kraken_bot.get_performance_dashboard()

        # Log key metrics
        logger.info(f"Portfolio: ${dashboard['account']['portfolio_value']:,.2f}")
        logger.info(f"Return: {dashboard['account']['total_return_pct']:+.2f}%")
        logger.info(f"Drawdown: {dashboard['performance']['max_drawdown']:-.2%}")

        await asyncio.sleep(3600)  # Every hour
```

### 🛡️ Risk Management

#### Position Sizing Rules

1. **Maximum Position Size**: 10% of capital per position
2. **Correlation Adjustment**: Reduce size for correlated positions
3. **Volatility Adjustment**: Smaller positions for higher volatility
4. **Confidence Weighting**: Position size scales with ML confidence



#### Stop Loss Management

1. **Fixed Percentage**: Default 3% stop loss
2. **Volatility-based**: Adjust based on symbol volatility
3. **Trailing Stops**: Dynamic stop loss adjustment
4. **Time-based**: Close positions after maximum duration



#### Emergency Controls

1. **Drawdown Limit**: Close all positions at 15% drawdown
2. **Daily Loss Limit**: Stop trading after 5% daily loss
3. **Consecutive Losses**: Stop after 5 consecutive losses
4. **Correlation Monitoring**: Reduce exposure during high correlation



### 📋 Trade Journal Format

```json
{
  "metadata": {
    "bot_version": "1.0.0",
    "export_timestamp": "2024-01-15T10:30:00Z",
    "initial_capital": 10000.0,
    "final_portfolio_value": 10750.0
  },
  "performance_summary": {
    "total_return": 750.0,
    "total_return_pct": 7.5,
    "win_rate": 65.0,
    "sharpe_ratio": 1.25,
    "max_drawdown": -5.2
  },
  "trade_history": [
    {
      "timestamp": "2024-01-15T09:15:00Z",
      "action": "OPEN",
      "position_id": "pos_20240115_001",
      "symbol": "BTC/USD",
      "side": "BUY",
      "entry_price": 45000.0,
      "quantity": 0.111,
      "stop_loss": 43650.0,
      "take_profit": 47700.0,
      "signal_confidence": 0.75,
      "tags": ["ml_signal", "rsi_oversold"]
    }
  ]
}
```

### 🔍 Troubleshooting

#### Common Issues

1. **Import Errors**


   ```python
   # Add to Python path
   import sys
   sys.path.insert(0, 'src')
   ```

2. **WebSocket Connection Issues**


   ```python
   # Use fallback polling if WebSocket fails
   config['price_feed']['backup_polling_interval'] = 5.0
   ```

3. **Memory Usage**


   ```python
   # Limit trade history size
   if len(self.trade_journal) > 10000:
       self.trade_journal = self.trade_journal[-5000:]
   ```

### 🎯 Next Steps

1. **Integration Testing**: Test with existing multi-signal bot
2. **Performance Optimization**: Optimize for high-frequency updates
3. **Additional Exchanges**: Extend to other exchanges
4. **Real Trading**: Transition from paper to live trading
5. **Advanced Analytics**: Add more sophisticated metrics



### 📞 Support

For issues or questions:

1. Check the test suite: `python test_kraken_paper_trading.py`
2. Run the demo: `python examples/kraken_paper_trading_demo.py`
3. Review the configuration: `config/kraken_paper_trading.yaml`
4. Check logs: `logs/kraken_paper_trading.log`



---

**Version**: 1.0.0
**Author**: BIGmindz
**License**: MIT
**Status**: Ready for Production Integration
