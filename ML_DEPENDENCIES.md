# ML Dependencies Installation Guide

This repository includes optional ML dependencies that may be required for certain advanced features. Follow these instructions to install the necessary packages:

## Core Dependencies

The core trading bot functionality can be installed with:

```bash
pip install -r requirements.txt
```

## Machine Learning Dependencies (Optional)

For advanced features like Adaptive Weight Model, Rapid Fire ML Training, and Market Regime Detection:

```bash
pip install -r requirements-dev.txt
```

## Feature Support Matrix

| Feature | Core Requirements | ML Requirements |
|---------|------------------|----------------|
| Basic Trading | ✅ | ❌ |
| Multi-Signal Aggregation | ✅ | ❌ |
| Sentiment Analysis | ✅ | ❌ |
| Adaptive Weight Model | ❌ | ✅ |
| Rapid Fire ML Training | ❌ | ✅ |
| Market Regime Detection | ❌ | ✅ |

## Troubleshooting

If you encounter errors related to missing modules:

1. For TensorFlow errors:

   ```bash
   pip install tensorflow>=2.8.0
   ```

2. For scikit-learn errors:

   ```bash
   pip install scikit-learn>=1.0.0
   ```

3. For joblib errors:

   ```bash
   pip install joblib>=1.1.0
   ```

4. For scheduling errors:

   ```bash
   pip install schedule>=1.1.0
   ```

The code has been designed with graceful degradation, so most features will work even without the ML dependencies installed.
