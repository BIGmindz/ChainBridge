# TensorFlow Adaptive Weight Model

## Overview

The TensorFlow Adaptive Weight Model is a machine learning system that dynamically optimizes signal weights for the multi-signal trading bot based on current market conditions. This model automatically identifies different market regimes (bull, bear, sideways, volatile) and adjusts the weights of 15 trading signals across 4 layers to maximize performance in each regime.

## Key Features

- **Automatic Market Regime Detection**: Identifies bull, bear, sideways, and volatile markets using machine learning

- **Dynamic Signal Weight Optimization**: Adjusts weights of 15 signals across 4 layers based on detected market conditions

- **Daily Automated Retraining**: Retrains every 24 hours using the last 7 days of performance data

- **Performance Visualization**: Provides comprehensive dashboards and visualizations of model performance

- **Seamless Integration**: Works with the existing multi-signal trading bot framework

## Architecture

The adaptive weight model consists of several key components:

1. **Market Condition Classifier**: Detects market regimes using K-means clustering and rule-based methods

1. **Signal Data Collector**: Gathers and preprocesses all 15 signal outputs for model input

1. **TensorFlow Neural Network**: Learns optimal weights for different market conditions

1. **Market Regime Integrator**: Connects regime detection with weight optimization

1. **Retraining Scheduler**: Automates the daily model retraining process

1. **Weight Visualizer**: Provides insights into weight adjustments and model performance

## Signal Portfolio Integration

The model optimizes weights across the four signal layers:

- **LAYER_1_TECHNICAL**: Short-term price signals (RSI, MACD, Bollinger, Volume, Sentiment)

- **LAYER_2_LOGISTICS**: 30-45 day signals (Port_Congestion, Diesel, Supply_Chain, Container)

- **LAYER_3_GLOBAL_MACRO**: 45-90 day signals (Inflation, Regulatory, Remittance, CBDC, FATF)

- **LAYER_4_ADOPTION**: 3-6 month signals (Chainalysis_Global)

## Usage

### Running the Demo

```bash

python run_adaptive_weight_demo.py --scenario bull_market

```text

Available scenarios: `bull_market`, `bear_market`, `sideways_market`, `volatile_market`

### Enabling in Multi-Signal Bot

To enable the adaptive weight model in the multi-signal bot, set `use_adaptive_weights: true` in your configuration file.

### Testing the Model

```bash

python modules/adaptive_weight_module/test_adaptive_weights.py

```text

## Technical Details

### Market Regime Detection

The model uses the following features to detect market regimes:

- Short-term and long-term volatility

- Price trend indicators

- Volume changes

- RSI values

- Bollinger Band width

### Weight Optimization

The TensorFlow neural network takes three inputs:

1. Signal data from all 15 signals

1. Market regime one-hot encoding

1. Market features (volatility, trend, etc.)

It outputs optimized weights for each signal, which are then applied to the decision-making process.

### Retraining Process

The model automatically retrains every 24 hours, using:

- The last 7 days of trading data

- Performance metrics by regime

- Signal performance correlation with market conditions

## Dependencies

- TensorFlow 2.16.1

- scikit-learn 1.4.1

- pandas 2.3.1

- numpy 2.0.2

- matplotlib 3.9.0

- seaborn 0.13.1

- schedule 1.2.1

## Implementation Details

All model files are located in the `modules/adaptive_weight_module/` directory:

- `adaptive_weight_model.py`: Core TensorFlow implementation

- `market_condition_classifier.py`: Market regime detection

- `market_regime_integrator.py`: Integration between regime detection and weight optimization

- `signal_data_collector.py`: Signal data preprocessing

- `retraining_scheduler.py`: Automated retraining system

- `weight_visualizer.py`: Visualization tools

- `weight_trainer.py`: Model training functionality

- `test_adaptive_weights.py`: Testing framework

- `integrate_adaptive_weights.py`: Bot integration module
