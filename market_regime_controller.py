#!/usr/bin/env python3
"""
Market Regime Controller - Real-time regime detection and adaptive strategy selection
"""

import os
import logging
import numpy as np
from datetime import datetime
import joblib

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


class MarketRegimeController:
    """
    Real-time market regime detection using trained ML models
    """

    def __init__(self, model_dir="ml_models"):
        self.model_dir = model_dir
        self.model = None
        self.label_encoder = None
        self.feature_cols = None
        self.last_prediction = None

        # Load the trained model
        self._load_model()

    def _load_model(self):
        """Load the trained ML model"""
        try:
            model_path = os.path.join(self.model_dir, "regime_detection_model.pkl")

            if os.path.exists(model_path):
                model_data = joblib.load(model_path)
                self.model = model_data["model"]
                self.label_encoder = model_data["label_encoder"]
                self.feature_cols = model_data["feature_cols"]
                logger.info("✅ ML model loaded successfully")
            else:
                logger.warning("No trained model found, using fallback detection")
                self.model = None

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None

    def get_current_features(self):
        """Get current market features for regime detection"""
        try:
            # For demo purposes, return mock features
            # In production, this would fetch real market data
            features = {
                "rsi_14": np.random.uniform(20, 80),
                "macd": np.random.uniform(-500, 500),
                "macd_signal": np.random.uniform(-500, 500),
                "macd_hist": np.random.uniform(-200, 200),
                "bb_upper": np.random.uniform(40000, 60000),
                "bb_middle": np.random.uniform(35000, 55000),
                "bb_lower": np.random.uniform(30000, 50000),
                "bb_width": np.random.uniform(0.02, 0.08),
                "bb_position": np.random.uniform(-0.5, 0.5),
                "volume_ratio": np.random.uniform(0.5, 2.0),
                "price_change_1h": np.random.uniform(-0.05, 0.05),
                "price_change_24h": np.random.uniform(-0.1, 0.1),
                "volatility_24h": np.random.uniform(0.01, 0.08),
                "trend_strength": np.random.uniform(0.1, 0.9),
            }

            logger.info(f"📊 Generated current market features: RSI={features['rsi_14']:.1f}")
            return features

        except Exception as e:
            logger.error(f"Error getting current features: {e}")
            return None

    def detect_regime(self, features=None):
        """Detect current market regime using ML model"""
        try:
            if features is None:
                features = self.get_current_features()

            if features is None:
                return self._fallback_detection()

            if self.model is None:
                return self._fallback_detection()

            # Prepare features for prediction
            feature_values = [features[col] for col in self.feature_cols]
            X = np.array(feature_values).reshape(1, -1)

            # Make prediction
            prediction_encoded = self.model.predict(X)[0]
            prediction_proba = self.model.predict_proba(X)[0]

            # Decode prediction
            regime = self.label_encoder.inverse_transform([prediction_encoded])[0]
            confidence = prediction_proba[prediction_encoded]

            self.last_prediction = {"regime": regime, "confidence": confidence, "timestamp": datetime.now(), "features": features}

            logger.info(f"🎯 ML Regime Detection: {regime} (confidence: {confidence:.3f})")
            return regime

        except Exception as e:
            logger.error(f"Error in regime detection: {e}")
            return self._fallback_detection()

    def _fallback_detection(self):
        """Fallback regime detection using simple rules"""
        try:
            # Simple fallback based on RSI
            features = self.get_current_features()
            if features and "rsi_14" in features:
                rsi = features["rsi_14"]
                if rsi < 30:
                    regime = "bull"  # Oversold, potential for upward movement
                elif rsi > 70:
                    regime = "bear"  # Overbought, potential for downward movement
                else:
                    regime = "sideways"  # Neutral zone
            else:
                regime = "sideways"  # Default fallback

            logger.info(f"🔄 Fallback regime detection: {regime}")
            return regime

        except Exception:
            logger.error("Fallback detection failed")
            return "sideways"

    def get_regime_status(self):
        """Get current regime detection status"""
        return {
            "current_regime": self.last_prediction["regime"] if self.last_prediction else None,
            "confidence": self.last_prediction["confidence"] if self.last_prediction else None,
            "last_update": self.last_prediction["timestamp"] if self.last_prediction else None,
            "model_loaded": self.model is not None,
        }


def detect_market_regime(features=None):
    """
    Convenience function for regime detection
    """
    controller = MarketRegimeController()
    return controller.detect_regime(features)


if __name__ == "__main__":
    # Demo the regime controller
    print("🔬 Market Regime Controller Demo")
    print("=" * 40)

    controller = MarketRegimeController()

    # Detect regime
    regime = controller.detect_regime()
    print(f"📊 Detected Regime: {regime}")

    # Show status
    status = controller.get_regime_status()
    print(f"🎯 Confidence: {status['confidence']:.3f}")
    print(f"📅 Last Update: {status['last_update']}")
    print(f"🤖 Model Loaded: {status['model_loaded']}")

    print("\n✅ Demo Complete")
