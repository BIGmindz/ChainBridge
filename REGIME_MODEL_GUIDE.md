# LightGBM Regime Detection Model - Integration Guide

This guide explains how to use the enhanced LightGBM multiclass classification model for market regime detection in the Multiple Signal Decision Bot system.

## Overview

The regime detection model is a comprehensive machine learning solution that classifies market conditions into three regimes:

- **Bull Market**: Strong upward trending conditions
- **Bear Market**: Strong downward trending conditions
- **Sideways Market**: Consolidation or range-bound conditions



## Features

The model uses **18 financial and technical features**:

### Core Technical Indicators

- `rsi_14`: 14-period Relative Strength Index
- `macd`: MACD line value
- `macd_signal`: MACD signal line
- `macd_hist`: MACD histogram (MACD - Signal)



### Bollinger Bands

- `bb_upper`: Upper Bollinger Band
- `bb_middle`: Middle Bollinger Band (SMA)
- `bb_lower`: Lower Bollinger Band
- `bb_width`: Band width (upper - lower)
- `bb_position`: Price position within bands (0-1)
- `bb_squeeze`: Bollinger squeeze indicator (0 or 1)



### Volume and Price Metrics

- `volume_ratio`: Volume relative to average
- `price_change_1h`: 1-hour price change percentage
- `price_change_24h`: 24-hour price change percentage



### Volatility and Trend

- `volatility_24h`: 24-hour price volatility
- `trend_strength`: Trend strength indicator (-1 to 1)



### Enhanced Features

- `momentum_rsi`: RSI with momentum adjustment
- `price_momentum`: Price change normalized by volatility
- `volume_price_trend`: Volume-weighted price trend



## Installation and Setup

### 1. Install Dependencies

```bash
pip install lightgbm scikit-learn joblib pandas numpy
```

### 2. Model Files

The system includes several model files:

```text
ml_models/
├── enhanced_regime_model.pkl    # Enhanced model (18 features)
└── regime_detection_model.pkl   # Original model (14 features)
```

## Quick Start

### Basic Usage

```python
from regime_model_utils import RegimeModelLoader, create_sample_features

# Initialize model loader
loader = RegimeModelLoader()

# Load the enhanced model
loader.load_model('enhanced')

# Create sample features for a bull market
features = create_sample_features('bull')

# Make prediction
result = loader.predict_regime(features, 'enhanced')

print(f"Predicted Regime: {result['regime']}")
print(f"Confidence: {result['confidence']:.3f}")
print(f"Probabilities: {result['probabilities']}")
```

### Using Real Market Data

```python
import pandas as pd
from regime_model_utils import RegimeModelLoader

# Your market data
market_data = {
    'rsi_14': 65.0,
    'macd': 0.02,
    'macd_signal': 0.015,
    'macd_hist': 0.005,
    'bb_upper': 52000,
    'bb_middle': 50000,
    'bb_lower': 48000,
    'bb_width': 4000,
    'bb_position': 0.75,
    'volume_ratio': 1.5,
    'price_change_1h': 0.01,
    'price_change_24h': 0.03,
    'volatility_24h': 0.20,
    'trend_strength': 0.7,
    'momentum_rsi': 68.0,
    'price_momentum': 0.15,
    'volume_price_trend': 0.045,
    'bb_squeeze': 0
}

# Load model and predict
loader = RegimeModelLoader()
loader.load_model('enhanced')
result = loader.predict_regime(market_data, 'enhanced')

print(f"Market Regime: {result['regime']} (confidence: {result['confidence']:.2%})")
```

## Training Your Own Model

### Train with Sample Data

```python
from enhanced_regime_model import EnhancedRegimeModel

# Initialize model
model = EnhancedRegimeModel()

# Generate sample training data
sample_data = model.generate_sample_data(n_samples=2000)

# Train the model
results = model.train_model(sample_data)

# Save the trained model
model_path = model.save_model()
print(f"Model saved to: {model_path}")
```

### Train with Your Data

```python
import pandas as pd
from enhanced_regime_model import EnhancedRegimeModel

# Load your historical data
# Make sure it has all required features plus 'regime' column
your_data = pd.read_csv('your_market_data.csv')

# Initialize and train model
model = EnhancedRegimeModel()
results = model.train_model(your_data)

# Save model
model.save_model('your_custom_model.pkl')
```

## Integration with Trading Bot

### 1. Add to Your Trading Strategy

```python
from regime_model_utils import RegimeModelLoader

class TradingStrategy:
    def __init__(self):
        self.regime_model = RegimeModelLoader()
        self.regime_model.load_model('enhanced')

    def get_current_regime(self, market_features):
        """Get current market regime"""
        result = self.regime_model.predict_regime(market_features, 'enhanced')
        return result['regime'], result['confidence']

    def adjust_strategy_for_regime(self, regime, confidence):
        """Adjust trading parameters based on regime"""
        if regime == 'bull' and confidence > 0.7:
            return {
                'position_size': 1.2,  # Increase position size
                'stop_loss': 0.02,     # Tighter stops
                'take_profit': 0.06    # Higher targets
            }
        elif regime == 'bear' and confidence > 0.7:
            return {
                'position_size': 0.5,  # Reduce position size
                'stop_loss': 0.03,     # Wider stops
                'take_profit': 0.04    # Lower targets
            }
        else:  # sideways or low confidence
            return {
                'position_size': 0.8,  # Moderate size
                'stop_loss': 0.025,    # Medium stops
                'take_profit': 0.05    # Medium targets
            }
```

### 2. Real-time Regime Detection

```python
import time
from datetime import datetime

class RegimeMonitor:
    def __init__(self):
        self.loader = RegimeModelLoader()
        self.loader.load_model('enhanced')
        self.current_regime = None
        self.last_update = None

    def update_regime(self, market_data):
        """Update current market regime"""
        result = self.loader.predict_regime(market_data, 'enhanced')

        # Only update if confidence is high enough
        if result['confidence'] > 0.6:
            if self.current_regime != result['regime']:
                print(f"🔄 Regime change detected: {self.current_regime} → {result['regime']}")
                self.current_regime = result['regime']
                self.last_update = datetime.now()

        return result

    def get_regime_status(self):
        """Get current regime status"""
        return {
            'regime': self.current_regime,
            'last_update': self.last_update,
            'age_minutes': (datetime.now() - self.last_update).seconds // 60 if self.last_update else None
        }
```

## Model Performance and Metrics

### Understanding Model Output

```python
# Example prediction result
result = {
    'regime': 'bull',           # Predicted regime
    'confidence': 0.847,        # Highest probability (0-1)
    'probabilities': {          # All regime probabilities
        'bull': 0.847,
        'bear': 0.089,
        'sideways': 0.064
    },
    'model_used': 'enhanced'    # Which model was used
}
```

### Confidence Interpretation

- **> 0.8**: Very high confidence - strong signal
- **0.6 - 0.8**: Good confidence - reliable signal
- **0.4 - 0.6**: Moderate confidence - use with caution
- **< 0.4**: Low confidence - consider market uncertainty



### Feature Importance

The model ranks features by importance. Typical rankings:

1. **trend_strength** - Most predictive of regime
2. **rsi_14** - Strong regime indicator
3. **price_change_24h** - Direct price movement signal
4. **bb_position** - Position within volatility bands
5. **macd_hist** - Momentum divergence signal



## Troubleshooting

### Common Issues

1. **Missing Features Error**


   ```python
   # Make sure all required features are present
   required_features = loader.get_model_info('enhanced')['feature_columns']
   missing = set(required_features) - set(your_data.columns)
   if missing:
       print(f"Missing features: {missing}")
   ```

2. **Model Loading Failed**


   ```python
   # Check if model file exists
   import os
   model_path = 'ml_models/enhanced_regime_model.pkl'
   if not os.path.exists(model_path):
       print("Model file not found. Train model first.")
   ```

3. **Poor Predictions**
   - Retrain with more recent data
   - Check feature quality and scaling
   - Increase training data size
   - Consider market regime changes



### Model Retraining

```python
# Schedule regular retraining
def retrain_model_weekly():
    """Retrain model with recent data"""
    from enhanced_regime_model import EnhancedRegimeModel

    # Get recent market data (implement your data collection)
    recent_data = collect_recent_market_data(days=30)

    # Retrain model
    model = EnhancedRegimeModel()
    results = model.train_model(recent_data)

    # Only save if performance is good
    if results['test_accuracy'] > 0.75:
        model.save_model()
        print(f"✅ Model retrained successfully (accuracy: {results['test_accuracy']:.2%})")
    else:
        print(f"⚠️  Model performance degraded (accuracy: {results['test_accuracy']:.2%})")
```

## Advanced Usage

### Ensemble Predictions

```python
def ensemble_regime_prediction(features):
    """Use both models for ensemble prediction"""
    loader = RegimeModelLoader()

    # Load both models
    loader.load_model('enhanced')
    loader.load_model('original')

    # Get predictions from both
    enhanced_result = loader.predict_regime(features, 'enhanced')
    original_result = loader.predict_regime(features, 'original')

    # Simple ensemble - average probabilities
    ensemble_probs = {}
    for regime in enhanced_result['probabilities'].keys():
        ensemble_probs[regime] = (
            enhanced_result['probabilities'][regime] +
            original_result['probabilities'][regime]
        ) / 2

    # Get final prediction
    final_regime = max(ensemble_probs, key=ensemble_probs.get)
    final_confidence = ensemble_probs[final_regime]

    return {
        'regime': final_regime,
        'confidence': final_confidence,
        'probabilities': ensemble_probs,
        'method': 'ensemble'
    }
```

### Custom Feature Engineering

```python
def engineer_additional_features(price_data, volume_data):
    """Add custom features to improve model performance"""

    # Calculate additional technical indicators
    features = {}

    # Custom RSI variants
    features['rsi_7'] = calculate_rsi(price_data, period=7)
    features['rsi_21'] = calculate_rsi(price_data, period=21)

    # Volume-weighted features
    features['vwap'] = calculate_vwap(price_data, volume_data)
    features['volume_momentum'] = calculate_volume_momentum(volume_data)

    # Volatility features
    features['realized_vol'] = calculate_realized_volatility(price_data)
    features['vol_ratio'] = features['realized_vol'] / features['volatility_24h']

    return features
```

## Best Practices

1. **Regular Model Updates**: Retrain monthly or when market conditions change
2. **Feature Quality**: Ensure feature calculations are consistent with training data
3. **Confidence Thresholds**: Set minimum confidence levels for trading decisions
4. **Backtesting**: Test regime-based strategies on historical data
5. **Monitoring**: Track model performance and regime change accuracy
6. **Fallback Strategy**: Have a backup strategy when model confidence is low



## Support and Contributing

- **Issues**: Report bugs or request features via GitHub issues
- **Documentation**: Contribute to documentation improvements
- **Models**: Share improved models or feature engineering techniques



## License

This model integration is part of the Multiple Signal Decision Bot project. Please refer to the project license for usage terms.
