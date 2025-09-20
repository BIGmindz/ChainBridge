# Trading Strategy System

This directory contains the "Strategy as a Service" architecture for the BensonBot trading system. Each subdirectory represents a distinct trading strategy that can be deployed independently.

## Architecture Overview

```
strategies/
├── bull_trend/          # Aggressive trend-following strategy
│   ├── config.yaml      # Strategy-specific configuration
│   └── model.pkl        # Trained ML model for this strategy
├── bear_defense/        # Conservative bear market strategy
│   ├── config.yaml
│   └── model.pkl
└── sideways_range/      # Mean-reversion range trading strategy
    ├── config.yaml
    └── model.pkl
```

## How It Works

1. **Strategy Discovery**: The `strategy_launcher.py` automatically scans this directory
2. **Interactive Selection**: User selects which strategy to deploy
3. **Strategy Execution**: Selected strategy is passed to the strategy engine
4. **Independent Deployment**: Each strategy runs with its own configuration and model

## Creating New Strategies

To create a new trading strategy:

1. **Create Strategy Directory**:

   ```bash
   mkdir strategies/my_new_strategy
   ```

2. **Add Configuration File**:
   Create `strategies/my_new_strategy/config.yaml` with strategy-specific settings:

   ```yaml
   budget_management:
     max_positions: 5
     max_risk_per_trade: 0.15
   symbols:
   - BTC/USD
   - ETH/USD
   strategy:
     name: "My New Strategy"
     description: "Description of the strategy"
   ```

3. **Add Trained Model**:
   Place your trained model at `strategies/my_new_strategy/model.pkl`

4. **Strategy is Ready**: The launcher will automatically discover and offer your new strategy

## Strategy Types

### Bull Trend Strategy

- **Aggressive position sizing** (up to 8 positions)
- **Higher risk tolerance** (20% per trade)
- **Trend-following approach**
- **Optimized for upward markets**

### Bear Defense Strategy

- **Conservative position sizing** (max 3 positions)
- **Lower risk tolerance** (8% per trade)
- **Short-biased approach**
- **Optimized for downward markets**

### Sideways Range Strategy

- **Moderate position sizing** (5 positions)
- **Balanced risk tolerance** (12% per trade)
- **Mean-reversion approach**
- **Optimized for ranging markets**

## Usage

Run the strategy launcher:

```bash
python strategy_launcher.py
```

This will:

1. Discover all available strategies
2. Present an interactive menu for selection
3. Launch the selected strategy with its configuration

## Integration with Regime Detection

While strategies can be selected manually, they are designed to work with the automatic regime detection system:

- **Bull Trend** ← Deployed when regime detection identifies bull markets
- **Bear Defense** ← Deployed when regime detection identifies bear markets
- **Sideways Range** ← Deployed when regime detection identifies sideways markets

## Future Enhancements

- **Strategy Performance Tracking**: Historical performance metrics for each strategy
- **Dynamic Strategy Switching**: Automatic switching based on real-time performance
- **Strategy Optimization**: Automated parameter tuning for each strategy
- **Backtesting Integration**: Built-in backtesting for strategy validation
