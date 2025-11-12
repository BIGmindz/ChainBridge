#!/usr/bin/env python3
"""
Example Script: LightGBM Regime Detection Model Usage
Demonstrates how to use the enhanced regime detection model for predictions
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings

# Add the current directory to Python path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from enhanced_regime_model import EnhancedRegimeModel
    from regime_model_utils import RegimeModelLoader, create_sample_features
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the repository root directory")
    sys.exit(1)

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")


def demonstrate_model_training():
    """
    Demonstrate training the enhanced regime detection model
    """
    print("🚀 TRAINING ENHANCED REGIME DETECTION MODEL")
    print("=" * 50)

    # Initialize the model
    model = EnhancedRegimeModel()

    # Generate sample training data
    print("📊 Generating sample training data...")
    sample_data = model.generate_sample_data(n_samples=1500)

    # Display data info
    print(f"   📈 Generated {len(sample_data)} samples")
    print(f"   🎯 Features: {len(sample_data.columns) - 1}")  # -1 for regime column
    print("   📊 Regime distribution:")
    for regime, count in sample_data["regime"].value_counts().items():
        print(f"      {regime}: {count} ({count / len(sample_data) * 100:.1f}%)")

    # Train the model
    print("\n🔥 Training model...")
    results = model.train_model(sample_data)

    # Save the model
    model_path = model.save_model()
    print(f"💾 Model saved to: {model_path}")

    # Print model summary
    model.print_model_summary()

    return model


def demonstrate_model_loading_and_prediction():
    """
    Demonstrate loading a trained model and making predictions
    """
    print("\n🔧 LOADING MODEL AND MAKING PREDICTIONS")
    print("=" * 45)

    # Initialize model loader
    loader = RegimeModelLoader()

    # Check available models
    available_models = loader.list_available_models()
    print(f"📋 Available models: {available_models}")

    # Try to load enhanced model first, then original
    model_name = "enhanced" if "enhanced" in available_models else ("original" if "original" in available_models else None)

    if model_name is None:
        print("❌ No models found. Please train a model first.")
        return None

    print(f"🔄 Loading model: {model_name}")
    success = loader.load_model(model_name)

    if not success:
        print(f"❌ Failed to load model: {model_name}")
        return None

    # Get model information
    model_info = loader.get_model_info(model_name)
    print("\n📊 Model Information:")
    print(f"   Model Type: {model_info['model_type']}")
    print(f"   Regime Classes: {model_info['regime_classes']}")
    print(f"   Number of Features: {model_info['n_features']}")
    print(f"   Has Feature Scaler: {model_info['has_scaler']}")

    return loader, model_name


def demonstrate_predictions(loader, model_name):
    """
    Demonstrate various types of predictions
    """
    print(f"\n🔮 MAKING PREDICTIONS WITH {model_name.upper()} MODEL")
    print("=" * 50)

    # Test individual regime predictions
    regime_types = ["bull", "bear", "sideways"]

    print("🎯 Single Prediction Examples:")
    print("-" * 35)

    for regime_type in regime_types:
        print(f"\n{regime_type.upper()} Market Simulation:")

        # Create sample features for the regime
        features = create_sample_features(regime_type)

        # Make prediction
        result = loader.predict_regime(features, model_name)

        # Display results
        print(f"   Predicted Regime: {result['regime']}")
        print(f"   Confidence: {result['confidence']:.3f}")
        print("   Probabilities:")
        for regime, prob in result["probabilities"].items():
            indicator = "👑" if regime == result["regime"] else "  "
            print(f"     {indicator} {regime}: {prob:.3f}")

        # Show some key features for context
        print("   Key Features:")
        print(f"     RSI(14): {features['rsi_14']:.1f}")
        print(f"     MACD: {features['macd']:.4f}")
        print(f"     BB Position: {features['bb_position']:.2f}")
        print(f"     Price Change 24h: {features['price_change_24h']:.3f}")
        print(f"     Trend Strength: {features['trend_strength']:.2f}")


def demonstrate_batch_predictions(loader, model_name):
    """
    Demonstrate batch predictions on multiple samples
    """
    print("\n📊 BATCH PREDICTION EXAMPLE")
    print("=" * 35)

    # Create multiple samples
    samples = []
    true_regimes = []

    # Generate 10 samples of each regime type
    for regime_type in ["bull", "bear", "sideways"]:
        for i in range(5):
            np.random.seed(42 + i)  # Different seed for variety
            sample = create_sample_features(regime_type)
            samples.append(sample)  # type: ignore
            true_regimes.append(regime_type)  # type: ignore

    # Convert to DataFrame
    batch_df = pd.DataFrame(samples)

    print(f"📈 Predicting on {len(batch_df)} samples...")

    # Make batch predictions
    results = loader.predict_regime(batch_df, model_name)

    # Analyze results
    predicted_regimes = results["regimes"]
    confidences = results["confidences"]

    print("\n📊 Batch Prediction Results:")
    print("-" * 40)

    # Calculate accuracy
    correct = sum(1 for true, pred in zip(true_regimes, predicted_regimes) if true == pred)  # type: ignore
    accuracy = correct / len(true_regimes)

    print(f"Overall Accuracy: {accuracy:.2%} ({correct}/{len(true_regimes)})")
    print(f"Average Confidence: {np.mean(confidences):.3f}")

    # Show regime-wise accuracy
    regime_accuracy = {}
    for regime in ["bull", "bear", "sideways"]:
        true_indices = [i for i, r in enumerate(true_regimes) if r == regime]
        regime_correct = sum(1 for i in true_indices if predicted_regimes[i] == regime)  # type: ignore
        regime_accuracy[regime] = regime_correct / len(true_indices) if true_indices else 0

    print("\nRegime-wise Accuracy:")
    for regime, acc in regime_accuracy.items():
        print(f"  {regime.capitalize()}: {acc:.2%}")

    # Show a few detailed examples
    print("\n🔍 Detailed Examples:")
    print("-" * 25)

    for i in range(min(6, len(samples))):
        true_regime = true_regimes[i]
        pred_regime = predicted_regimes[i]
        confidence = confidences[i]
        status = "✅" if true_regime == pred_regime else "❌"

        print(f"{status} Sample {i + 1}: True={true_regime}, Pred={pred_regime} (conf: {confidence:.3f})")


def demonstrate_feature_importance(loader, model_name):
    """
    Demonstrate feature importance analysis
    """
    print("\n📈 FEATURE IMPORTANCE ANALYSIS")
    print("=" * 35)

    try:
        # Try to get feature importance from the loaded model
        model_info = loader.models[model_name]
        model = model_info["model"]
        feature_columns = model_info["feature_columns"]

        if hasattr(model, "feature_importances_"):
            importance_scores = model.feature_importances_
            feature_importance = dict(zip(feature_columns, importance_scores))

            # Sort by importance
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

            print("🏆 TOP 10 MOST IMPORTANT FEATURES:")
            print("-" * 40)

            for i, (feature, importance) in enumerate(sorted_features[:10]):
                bar_length = int(importance * 50)  # Scale for visualization
                bar = "█" * bar_length + "░" * (20 - bar_length)
                print(f"{i + 1:2d}. {feature:<20} │{bar}│ {importance:.4f}")

            # Group features by category
            print("\n📊 FEATURE CATEGORIES:")
            print("-" * 25)

            categories = {
                "RSI": ["rsi_14", "momentum_rsi"],
                "MACD": ["macd", "macd_signal", "macd_hist"],
                "Bollinger Bands": ["bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_position", "bb_squeeze"],
                "Volume": ["volume_ratio", "volume_price_trend"],
                "Price Change": ["price_change_1h", "price_change_24h", "price_momentum"],
                "Volatility": ["volatility_24h"],
                "Trend": ["trend_strength"],
            }

            for category, features in categories.items():
                category_importance = sum(feature_importance.get(f, 0) for f in features)  # type: ignore
                print(f"  {category:<15}: {category_importance:.4f}")

        else:
            print("⚠️  Feature importance not available for this model type")

    except Exception as e:
        print(f"❌ Error analyzing feature importance: {e}")


def create_live_market_simulation():
    """
    Simulate live market data prediction
    """
    print("\n🎯 LIVE MARKET SIMULATION")
    print("=" * 30)

    # Simulate market data for the last 7 days
    dates = [datetime.now() - timedelta(days=i) for i in range(6, -1, -1)]

    print("Simulating market regime detection for the past week...")
    print("-" * 55)

    loader = RegimeModelLoader()
    model_name = "enhanced" if "enhanced" in loader.list_available_models() else "original"

    if not loader.load_model(model_name):
        print("❌ Could not load model for simulation")
        return

    print("Date         │ Regime   │ Conf │ RSI │ MACD  │ Trend │ Vol")
    print("-" * 60)

    for date in dates:
        # Simulate realistic market conditions
        np.random.seed(int(date.timestamp()))

        # Randomly choose market condition
        market_condition = np.random.choice(["bull", "bear", "sideways"], p=[0.4, 0.3, 0.3])
        features = create_sample_features(market_condition)

        # Make prediction
        result = loader.predict_regime(features, model_name)

        # Format output
        date_str = date.strftime("%Y-%m-%d")
        regime = result["regime"]
        confidence = result["confidence"]

        # Color coding for regime
        regime_emoji = {"bull": "🟢", "bear": "🔴", "sideways": "🟡"}[regime]

        print(
            f"{date_str} │ {regime_emoji}{regime:<7} │{confidence:.2f} │{features['rsi_14']:4.0f}│"
            f"{features['macd']:6.3f}│{features['trend_strength']:6.2f}│{features['volatility_24h']:5.2f}"
        )


def main():
    """
    Main demonstration function
    """
    print("🤖 LIGHTGBM REGIME DETECTION MODEL - COMPLETE EXAMPLE")
    print("=" * 60)
    print("This script demonstrates:")
    print("1. Training the enhanced regime detection model")
    print("2. Loading trained models and making predictions")
    print("3. Single and batch predictions")
    print("4. Feature importance analysis")
    print("5. Live market simulation")
    print("=" * 60)

    try:
        # Step 1: Train model if needed
        model = demonstrate_model_training()

        # Step 2: Load model and make predictions
        loader, model_name = demonstrate_model_loading_and_prediction()

        if loader and model_name:
            # Step 3: Demonstrate various prediction types
            demonstrate_predictions(loader, model_name)

            # Step 4: Batch predictions
            demonstrate_batch_predictions(loader, model_name)

            # Step 5: Feature importance analysis
            demonstrate_feature_importance(loader, model_name)

            # Step 6: Live market simulation
            create_live_market_simulation()

        print("\n🎉 ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
        print("=" * 50)
        print("📚 What you learned:")
        print("• How to train the enhanced LightGBM regime detection model")
        print("• How to load and use trained models for predictions")
        print("• How to interpret prediction results and confidence scores")
        print("• How to analyze feature importance for model insights")
        print("• How to integrate the model into live trading systems")
        print("\n💡 Next Steps:")
        print("• Integrate this model into your trading bot")
        print("• Use real market data for training")
        print("• Implement model retraining pipeline")
        print("• Add model monitoring and performance tracking")

    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
