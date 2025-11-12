#!/usr/bin/env python3
"""
Regime Model Utilities - Easy model loading and inference utilities
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Union
import warnings

try:
    import joblib
    from lightgbm import LGBMClassifier
    from sklearn.preprocessing import LabelEncoder, StandardScaler
except ImportError as e:
    print(f"Required dependency missing: {e}")
    print("Please install: pip install lightgbm scikit-learn joblib")
    sys.exit(1)

# Suppress warnings
warnings.filterwarnings("ignore")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RegimeModelLoader:
    """
    Utility class for loading and using regime detection models
    """

    def __init__(self, model_dir: str = "ml_models"):
        self.model_dir = model_dir
        self.models = {}
        self.available_models = self._discover_models()

    def _discover_models(self) -> Dict[str, str]:
        """
        Discover available regime detection models in the model directory

        Returns:
            Dictionary mapping model names to file paths
        """
        available = {}

        if not os.path.exists(self.model_dir):
            logger.warning(f"Model directory not found: {self.model_dir}")
            return available

        # Look for regime detection models
        model_files = [
            ("enhanced_regime_model.pkl", "enhanced"),
            ("regime_detection_model.pkl", "original"),
        ]

        for filename, model_name in model_files:
            filepath = os.path.join(self.model_dir, filename)
            if os.path.exists(filepath):
                available[model_name] = filepath
                logger.info(f"🔍 Found model: {model_name} -> {filepath}")

        return available

    def load_model(self, model_name: str = "enhanced") -> bool:
        """
        Load a specific regime detection model

        Args:
            model_name: Name of the model to load ('enhanced' or 'original')

        Returns:
            True if model loaded successfully
        """
        if model_name not in self.available_models:
            logger.error(f"Model '{model_name}' not found. Available: {list(self.available_models.keys())}")  # type: ignore
            return False

        try:
            filepath = self.available_models[model_name]
            model_data = joblib.load(filepath)

            self.models[model_name] = {
                "model": model_data["model"],
                "label_encoder": model_data["label_encoder"],
                "feature_scaler": model_data.get("feature_scaler"),
                "feature_columns": model_data.get(
                    "feature_columns", model_data.get("feature_cols")
                ),
                "metadata": model_data.get("metadata", {}),
                "loaded_from": filepath,
            }

            logger.info(f"✅ Model '{model_name}' loaded successfully")
            logger.info(f"🎯 Classes: {model_data['label_encoder'].classes_}")

            return True

        except Exception as e:
            logger.error(f"Error loading model '{model_name}': {e}")
            return False

    def predict_regime(
        self, features: Union[Dict, pd.DataFrame], model_name: str = "enhanced"
    ) -> Dict:
        """
        Predict market regime using specified model

        Args:
            features: Feature dictionary or DataFrame
            model_name: Name of model to use

        Returns:
            Prediction results dictionary
        """
        if model_name not in self.models:
            if not self.load_model(model_name):
                raise ValueError(f"Could not load model: {model_name}")

        model_info = self.models[model_name]
        model = model_info["model"]
        label_encoder = model_info["label_encoder"]
        feature_scaler = model_info["feature_scaler"]
        feature_columns = model_info["feature_columns"]

        # Convert features to DataFrame if needed
        if isinstance(features, dict):
            df = pd.DataFrame([features])
        else:
            df = features.copy()

        # Ensure we have all required features
        missing_features = set(feature_columns) - set(df.columns)
        if missing_features:
            raise ValueError(f"Missing required features: {missing_features}")

        # Select and order features
        X = df[feature_columns]

        # Handle missing values
        X = X.fillna(X.median())

        # Scale features if scaler is available
        if feature_scaler is not None:
            X_scaled = feature_scaler.transform(X)
        else:
            X_scaled = X.values

        # Make predictions
        pred_encoded = model.predict(X_scaled)
        pred_proba = model.predict_proba(X_scaled)

        # If single prediction, extract scalar values
        if len(pred_encoded) == 1:
            pred_encoded = pred_encoded[0]
            pred_proba = pred_proba[0]

            # Decode prediction
            regime = label_encoder.inverse_transform([pred_encoded])[0]
            confidence = pred_proba.max()

            # Get all probabilities
            regime_probs = dict(zip(label_encoder.classes_, pred_proba))

            return {
                "regime": regime,
                "confidence": confidence,
                "probabilities": regime_probs,
                "model_used": model_name,
            }
        else:
            # Multiple predictions
            regimes = label_encoder.inverse_transform(pred_encoded)
            confidences = pred_proba.max(axis=1)

            return {
                "regimes": regimes.tolist(),  # type: ignore
                "confidences": confidences.tolist(),  # type: ignore
                "probabilities": pred_proba.tolist(),  # type: ignore
                "model_used": model_name,
            }

    def get_model_info(self, model_name: str = "enhanced") -> Dict:
        """
        Get information about a loaded model

        Args:
            model_name: Name of the model

        Returns:
            Model information dictionary
        """
        if model_name not in self.models:
            if not self.load_model(model_name):
                return {}

        model_info = self.models[model_name]

        info = {
            "model_name": model_name,
            "model_type": type(model_info["model"]).__name__,
            "regime_classes": model_info["label_encoder"].classes_.tolist(),  # type: ignore
            "feature_columns": model_info["feature_columns"],
            "n_features": len(model_info["feature_columns"]),
            "loaded_from": model_info["loaded_from"],
            "has_scaler": model_info["feature_scaler"] is not None,
            "metadata": model_info["metadata"],
        }

        return info

    def list_available_models(self) -> List[str]:
        """
        List all available models

        Returns:
            List of available model names
        """
        return list(self.available_models.keys())  # type: ignore


def create_sample_features(regime_type: str = "bull") -> Dict:
    """
    Create sample feature dictionary for testing

    Args:
        regime_type: Type of regime to simulate ('bull', 'bear', 'sideways')

    Returns:
        Dictionary with sample features
    """
    np.random.seed(42)

    if regime_type == "bull":
        # Bullish market characteristics
        features = {
            "rsi_14": np.random.uniform(60, 85),
            "macd": np.random.uniform(0.01, 0.05),
            "macd_signal": np.random.uniform(0.008, 0.04),
            "macd_hist": np.random.uniform(0.002, 0.01),
            "bb_upper": 52000,
            "bb_middle": 50000,
            "bb_lower": 48000,
            "bb_width": 4000,
            "bb_position": np.random.uniform(0.6, 0.9),
            "volume_ratio": np.random.uniform(1.2, 2.0),
            "price_change_1h": np.random.uniform(0.005, 0.02),
            "price_change_24h": np.random.uniform(0.02, 0.08),
            "volatility_24h": np.random.uniform(0.15, 0.25),
            "trend_strength": np.random.uniform(0.6, 1.0),
        }

        # Enhanced features if available
        features.update(
            {
                "momentum_rsi": features["rsi_14"] + np.random.normal(0, 3),
                "price_momentum": features["price_change_24h"]
                / features["volatility_24h"],
                "volume_price_trend": features["volume_ratio"]
                * features["price_change_24h"],
                "bb_squeeze": 0,  # No squeeze in trending market
            }
        )

    elif regime_type == "bear":
        # Bearish market characteristics
        features = {
            "rsi_14": np.random.uniform(15, 40),
            "macd": np.random.uniform(-0.05, -0.01),
            "macd_signal": np.random.uniform(-0.04, -0.008),
            "macd_hist": np.random.uniform(-0.01, -0.002),
            "bb_upper": 52000,
            "bb_middle": 50000,
            "bb_lower": 48000,
            "bb_width": 4000,
            "bb_position": np.random.uniform(0.1, 0.4),
            "volume_ratio": np.random.uniform(1.5, 2.5),
            "price_change_1h": np.random.uniform(-0.02, -0.005),
            "price_change_24h": np.random.uniform(-0.08, -0.02),
            "volatility_24h": np.random.uniform(0.20, 0.35),
            "trend_strength": np.random.uniform(-1.0, -0.6),
        }

        # Enhanced features if available
        features.update(
            {
                "momentum_rsi": features["rsi_14"] + np.random.normal(0, 3),
                "price_momentum": features["price_change_24h"]
                / features["volatility_24h"],
                "volume_price_trend": features["volume_ratio"]
                * features["price_change_24h"],
                "bb_squeeze": 0,  # No squeeze in trending market
            }
        )

    else:  # sideways
        # Sideways/consolidation market characteristics
        features = {
            "rsi_14": np.random.uniform(40, 60),
            "macd": np.random.uniform(-0.005, 0.005),
            "macd_signal": np.random.uniform(-0.004, 0.004),
            "macd_hist": np.random.uniform(-0.002, 0.002),
            "bb_upper": 51000,
            "bb_middle": 50000,
            "bb_lower": 49000,
            "bb_width": 2000,
            "bb_position": np.random.uniform(0.3, 0.7),
            "volume_ratio": np.random.uniform(0.8, 1.2),
            "price_change_1h": np.random.uniform(-0.005, 0.005),
            "price_change_24h": np.random.uniform(-0.01, 0.01),
            "volatility_24h": np.random.uniform(0.10, 0.20),
            "trend_strength": np.random.uniform(-0.3, 0.3),
        }

        # Enhanced features if available
        features.update(
            {
                "momentum_rsi": features["rsi_14"] + np.random.normal(0, 3),
                "price_momentum": (
                    features["price_change_24h"] / features["volatility_24h"]
                    if features["volatility_24h"] > 0
                    else 0
                ),
                "volume_price_trend": features["volume_ratio"]
                * features["price_change_24h"],
                "bb_squeeze": 1,  # Squeeze in sideways market
            }
        )

    # Ensure RSI bounds
    features["momentum_rsi"] = max(0, min(100, features["momentum_rsi"]))

    return features


def quick_predict(
    features: Union[Dict, pd.DataFrame], model_name: str = "enhanced"
) -> str:
    """
    Quick prediction function for convenience

    Args:
        features: Feature dictionary or DataFrame
        model_name: Model to use ('enhanced' or 'original')

    Returns:
        Predicted regime as string
    """
    loader = RegimeModelLoader()
    result = loader.predict_regime(features, model_name)
    return result["regime"]


def main():
    """
    Demonstration of regime model utilities
    """
    print("🔧 Regime Model Utilities Demo")
    print("=" * 35)

    # Initialize model loader
    loader = RegimeModelLoader()

    # List available models
    available = loader.list_available_models()
    print(f"📋 Available models: {available}")

    if not available:
        print("❌ No models found. Please train a model first.")
        return

    # Load a model (try enhanced first, fallback to original)
    model_to_use = "enhanced" if "enhanced" in available else available[0]
    success = loader.load_model(model_to_use)

    if not success:
        print(f"❌ Failed to load model: {model_to_use}")
        return

    # Get model info
    info = loader.get_model_info(model_to_use)
    print("\n📊 Model Information:")
    print(f"  Name: {info['model_name']}")
    print(f"  Type: {info['model_type']}")
    print(f"  Classes: {info['regime_classes']}")
    print(f"  Features: {info['n_features']}")
    print(f"  Has Scaler: {info['has_scaler']}")

    # Test predictions for different market regimes
    print("\n🔮 TESTING PREDICTIONS:")
    print("-" * 35)

    for regime_type in ["bull", "bear", "sideways"]:
        print(f"\n{regime_type.upper()} Market Sample:")

        # Create sample features
        sample_features = create_sample_features(regime_type)

        # Make prediction
        result = loader.predict_regime(sample_features, model_to_use)

        print(
            f"  Predicted: {result['regime']} (confidence: {result['confidence']:.3f})"
        )
        print("  Probabilities:")
        for regime, prob in result["probabilities"].items():
            print(f"    {regime}: {prob:.3f}")

    # Test quick predict function
    print("\n⚡ Quick Predict Function:")
    bull_features = create_sample_features("bull")
    quick_result = quick_predict(bull_features, model_to_use)
    print(f"  Quick prediction: {quick_result}")

    print("\n✅ Demo completed successfully!")


if __name__ == "__main__":
    main()
