# Rapid Fire ML Training System

A 30-minute intensive paper trading simulation for the Multiple-signal-decision-bot that performs real-time learning, pattern recognition, and decision tracking with a dashboard that updates every 15 minutes.

## Overview

The Rapid Fire ML Training System is designed to optimize the signal weights and decision-making process of the Multiple-signal-decision-bot through intensive short-duration paper trading. It leverages TensorFlow and machine learning techniques to learn from trading decisions and optimize the weighting of the bot's 15 different signals across technical, logistics, global macro, and adoption categories.

## Key Features

- **30-minute intensive paper trading** with $1,000 starting capital
- **Real-time learning and pattern recognition** using TensorFlow
- **Signal weight optimization** based on trading performance
- **Interactive dashboard** with performance metrics and visualizations
- **Win/loss tracking** with emphasis on learning from mistakes
- **Visualization of signal importance** to identify most valuable signals



## Installation

### Full Version (with TensorFlow)

The full version requires TensorFlow and provides advanced pattern recognition capabilities.

```bash
# Install dependencies
pip install tensorflow pandas numpy matplotlib seaborn

# Run the training
python run_rapid_fire_training.py
```

### Simple Version (No TensorFlow)

A simplified version is provided that doesn't require TensorFlow but still performs signal weight optimization.

```bash
# Install dependencies (minimal)
pip install pandas numpy matplotlib

# Run the simplified version
python run_simple_rapid_training.py
```

## Usage

### Command Line Options

Both training scripts support the following command line options:

```bash
--duration INT    Duration of training in minutes (default: 30)
--cycle INT       Seconds between training cycles (default: 30)
--capital FLOAT   Initial paper trading capital (default: $1000)
--config PATH     Path to configuration file (default: config/config.yaml)
--dashboard INT   Minutes between dashboard updates (default: 15)
```

### Examples

Run a standard 30-minute training session:

```bash
python run_rapid_fire_training.py
```

Run a shorter 10-minute training session with $5000 capital:

```bash
python run_rapid_fire_training.py --duration 10 --capital 5000
```

Run the simplified version with more frequent cycles:

```bash
python run_simple_rapid_training.py --cycle 15
```

## Training Output

After running a training session, you'll find the following outputs in the `data/rapid_fire_sessions/session_YYYYMMDD_HHMMSS/` directory:

- **Signal Weights**: Optimized weights for each signal
- **Performance Metrics**: Capital growth, win rate, and trading statistics
- **Visualizations**: Charts showing performance over time and signal importance
- **Training Data**: Raw data collected during the training session



For the TensorFlow version, a trained model will also be saved for later use in production.

## Technical Details

### Signal Categories

The system works with the bot's 15 signals across 4 categories:

1. **Technical Signals**: RSI, MACD, Bollinger Bands, Volume Profile, Sentiment Analysis
2. **Logistics Signals**: Port Congestion, Diesel Prices, Supply Chain Pressure, Container Rates
3. **Global Macro Signals**: Inflation, Regulatory, Remittance, CBDC, FATF
4. **Adoption Signals**: Chainalysis Global Adoption



### Learning Process

1. The system runs multiple trading cycles during the 30-minute period
2. For each cycle, it collects signal data and makes a trading decision
3. Past decisions are evaluated based on price movements
4. Signal weights are adjusted to prioritize effective signals
5. The dashboard updates every 15 minutes to show progress



### Model Architecture

The TensorFlow model uses a simple dense neural network:

- Input layer: 15 neurons (one for each signal)
- Hidden layers: 64, 32, and 16 neurons with ReLU activation
- Output layer: 3 neurons with softmax activation (BUY, SELL, HOLD)



## Integration

The Rapid Fire ML Training System is designed to work seamlessly with the existing Multiple-signal-decision-bot architecture. It uses the same configuration files and interfaces with the same components, ensuring compatibility with the overall trading system.
