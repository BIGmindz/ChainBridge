#!/usr/bin/env python3
"""
Market Condition Classifier

This module identifies different market regimes (bull, bear, sideways, volatile)
based on price action, volatility, and trend indicators to help the adaptive
weight model optimize signal weights for current conditions.

The classifier uses both unsupervised clustering and rule-based approaches
to provide robust market regime detection.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

# scikit-learn imports for clustering - wrapped in try-except for optional dependency
try:
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print(
        "scikit-learn not available. Market condition classifier will use fallback methods."
    )


class MarketConditionClassifier:
    """
    Detects and classifies market conditions using price data analysis
    and machine learning techniques
    """

    # Market regime constants
    BULL_MARKET = "BULL"
    BEAR_MARKET = "BEAR"
    SIDEWAYS_MARKET = "SIDEWAYS"
    VOLATILE_MARKET = "VOLATILE"
    LOW_VOL_MARKET = "LOW_VOLATILITY"
    UNKNOWN_MARKET = "UNKNOWN"

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the market condition classifier"""
        self.config = config or {}

        # Clustering configuration
        self.n_regimes = self.config.get("n_regimes", 4)
        self.min_samples = self.config.get("min_samples", 30)
        self.lookback_days = self.config.get("lookback_days", 30)

        # Feature configuration
        self.features = self.config.get(
            "features",
            [
                "volatility_1d",
                "volatility_7d",
                "volatility_30d",
                "trend_1d",
                "trend_7d",
                "trend_30d",
                "volume_change_1d",
                "volume_change_7d",
                "rsi_value",
                "bb_width",
            ],
        )

        # Regime labeling thresholds (from configuration or defaults)
        self.volatility_thresh = self.config.get("volatility_threshold", 0.02)
        self.trend_thresh = self.config.get("trend_threshold", 0.005)

        # Model storage
        self.model_dir = os.path.join(
            self.config.get("model_dir", "models"), "market_regime_classifier"
        )
        os.makedirs(self.model_dir, exist_ok=True)

        # Initialize models
        self.kmeans_model = None
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=2)  # For visualization
        self.regime_mapping = {}  # Maps cluster numbers to regime names

        # Historical data storage
        self._historical_regimes = []

        # Initialize models
        self._initialize_models()

    def _initialize_models(self) -> None:
        """Initialize or load existing clustering models"""
        # Try to load existing model
        model_path = os.path.join(self.model_dir, "kmeans_regime_model.json")
        if os.path.exists(model_path):
            try:
                self._load_model(model_path)
            except Exception as e:
                print(f"Error loading market regime model: {str(e)}")
                self._build_new_model()
        else:
            self._build_new_model()

    def _build_new_model(self) -> None:
        """Build a new K-means clustering model for market regimes"""
        self.kmeans_model = KMeans(
            n_clusters=self.n_regimes, random_state=42, n_init=10
        )

        # Default cluster-to-regime mapping
        # Will be refined during training/calibration
        self.regime_mapping = {
            0: self.BULL_MARKET,
            1: self.BEAR_MARKET,
            2: self.SIDEWAYS_MARKET,
            3: self.VOLATILE_MARKET,
        }

        if self.n_regimes > 4:
            self.regime_mapping[4] = self.LOW_VOL_MARKET

    def _load_model(self, model_path: str) -> None:
        """Load a previously saved model"""
        with open(model_path, "r") as f:
            model_data = json.load(f)

        # Recreate K-means model
        self.kmeans_model = KMeans(
            n_clusters=model_data.get("n_clusters", self.n_regimes),
            random_state=42,
            n_init=10,
        )

        # Set cluster centers directly
        self.kmeans_model.cluster_centers_ = np.array(
            model_data.get("cluster_centers", [])
        )
        self.kmeans_model._n_threads = None

        # Load regime mapping
        self.regime_mapping = model_data.get("regime_mapping", {})

        # Convert keys from strings to integers
        self.regime_mapping = {int(k): v for k, v in self.regime_mapping.items()}

    def save_model(self) -> None:
        """Save the current model to disk"""
        if self.kmeans_model is None or not hasattr(
            self.kmeans_model, "cluster_centers_"
        ):
            print("Cannot save market regime model: Model not trained")
            return

        model_data = {
            "n_clusters": self.n_regimes,
            "cluster_centers": self.kmeans_model.cluster_centers_.tolist(),
            "regime_mapping": self.regime_mapping,
            "features": self.features,
            "last_updated": datetime.now().isoformat(),
        }

        model_path = os.path.join(self.model_dir, "kmeans_regime_model.json")
        with open(model_path, "w") as f:
            json.dump(model_data, f, indent=2)

    def extract_features(
        self, price_data: List[float], volume_data: List[float] = None
    ) -> Dict[str, float]:
        """
        Extract features for regime detection from price and volume data

        Args:
            price_data: List of historical prices (most recent last)
            volume_data: Optional list of historical volumes

        Returns:
            Dictionary of features
        """
        # Ensure we have enough data
        if len(price_data) < 30:
            return {}

        # Convert to numpy arrays for efficient calculations
        prices = np.array(price_data)
        volumes = np.array(volume_data) if volume_data else None

        # Calculate returns
        returns = np.diff(prices) / prices[:-1]

        # Extract features
        features = {}

        # Volatility features (annualized)
        features["volatility_1d"] = np.std(returns[-1:]) * np.sqrt(365)
        features["volatility_7d"] = np.std(returns[-7:]) * np.sqrt(365)
        features["volatility_30d"] = np.std(returns[-30:]) * np.sqrt(365)

        # Trend features (annualized)
        features["trend_1d"] = np.mean(returns[-1:]) * 365
        features["trend_7d"] = np.mean(returns[-7:]) * 365
        features["trend_30d"] = np.mean(returns[-30:]) * 365

        # RSI calculation
        delta = np.diff(prices)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = np.mean(gain[-14:])
        avg_loss = np.mean(loss[-14:])
        rs = avg_gain / (avg_loss + 1e-10)  # Avoid division by zero
        features["rsi_value"] = 100 - (100 / (1 + rs))

        # Bollinger Band width
        ma20 = np.mean(prices[-20:])
        std20 = np.std(prices[-20:])
        _bb_width = (ma20 + 2 * std20 - (ma20 - 2 * std20)) / ma20
        features["bb_width"] = _bb_width

        # Volume features (if available)
        if volumes is not None and len(volumes) > 7:
            features["volume_change_1d"] = volumes[-1] / np.mean(volumes[-7:-1])
            features["volume_change_7d"] = np.mean(volumes[-7:]) / np.mean(
                volumes[-30:-7]
            )
        else:
            features["volume_change_1d"] = 1.0
            features["volume_change_7d"] = 1.0

        return features

    def detect_regime_rule_based(self, features: Dict[str, float]) -> Tuple[str, float]:
        """
        Detect market regime using rule-based approach

        Args:
            features: Dictionary of extracted features

        Returns:
            Tuple of (regime name, confidence level)
        """
        # Extract key indicators
        volatility = features.get("volatility_30d", 0.0)
        trend = features.get("trend_30d", 0.0)
        _bb_width = features.get("bb_width", 0.0)
        rsi = features.get("rsi_value", 50.0)

        # Rule-based classification
        if abs(trend) < self.trend_thresh:  # Low trend
            if volatility < self.volatility_thresh:
                return self.SIDEWAYS_MARKET, 0.8
            else:
                return self.VOLATILE_MARKET, 0.7
        elif trend > 0:  # Positive trend
            if rsi > 70:
                return self.BULL_MARKET, 0.9  # Strong bull
            else:
                return self.BULL_MARKET, 0.7  # Moderate bull
        else:  # Negative trend
            if rsi < 30:
                return self.BEAR_MARKET, 0.9  # Strong bear
            else:
                return self.BEAR_MARKET, 0.7  # Moderate bear

    def detect_regime_ml(self, features: Dict[str, float]) -> Tuple[str, float]:
        """
        Detect market regime using the K-means clustering model

        Args:
            features: Dictionary of extracted features

        Returns:
            Tuple of (regime name, confidence level)
        """
        if self.kmeans_model is None:
            return self.UNKNOWN_MARKET, 0.0

        # Extract feature vector in the correct order
        feature_vector = []
        for feature_name in self.features:
            feature_value = features.get(feature_name, 0.0)
            feature_vector.append(feature_value)

        feature_vector = np.array(feature_vector).reshape(1, -1)

        # Scale features
        scaled_features = self.scaler.transform(feature_vector)

        # Predict cluster
        cluster = self.kmeans_model.predict(scaled_features)[0]

        # Calculate distance to cluster center for confidence
        distances = self.kmeans_model.transform(scaled_features)
        min_distance = distances[0, cluster]
        max_distance = np.max(distances)

        # Convert distance to confidence score (inverse relationship)
        # Closer to center = higher confidence
        confidence = 1.0 - (min_distance / max_distance)

        # Get regime name from mapping
        regime = self.regime_mapping.get(cluster, self.UNKNOWN_MARKET)

        return regime, confidence

    def detect_regime(
        self, price_data: List[float], volume_data: List[float] = None
    ) -> Dict[str, Any]:
        """
        Detect market regime using both rule-based and ML approaches

        Args:
            price_data: List of historical prices (most recent last)
            volume_data: Optional list of historical volumes

        Returns:
            Dictionary with regime information
        """
        # Extract features
        features = self.extract_features(price_data, volume_data)
        if not features:
            return {
                "regime": self.UNKNOWN_MARKET,
                "confidence": 0.0,
                "features": {},
                "timestamp": datetime.now().isoformat(),
            }

        # Get rule-based regime
        rule_regime, rule_confidence = self.detect_regime_rule_based(features)

        # Get ML-based regime if model is trained
        if self.kmeans_model and hasattr(self.kmeans_model, "cluster_centers_"):
            ml_regime, ml_confidence = self.detect_regime_ml(features)
        else:
            ml_regime, ml_confidence = self.UNKNOWN_MARKET, 0.0

        # Combine results (prefer ML if confident, otherwise use rule-based)
        if ml_confidence > 0.6:
            final_regime = ml_regime
            final_confidence = ml_confidence
        else:
            final_regime = rule_regime
            final_confidence = rule_confidence

        # Store this regime detection for history
        self._historical_regimes.append(
            {
                "regime": final_regime,
                "confidence": final_confidence,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Keep only the last 100 regime detections
        if len(self._historical_regimes) > 100:
            self._historical_regimes = self._historical_regimes[-100:]

        return {
            "regime": final_regime,
            "confidence": final_confidence,
            "rule_based": {"regime": rule_regime, "confidence": rule_confidence},
            "ml_based": {"regime": ml_regime, "confidence": ml_confidence},
            "features": features,
            "timestamp": datetime.now().isoformat(),
        }

    def train_model(self, historical_data: Dict[str, Any]) -> None:
        """
        Train the K-means clustering model with historical data

        Args:
            historical_data: Dictionary with price_history, volume_history, etc.
        """
        # Extract price and volume history
        price_history = historical_data.get("price_history", [])
        volume_history = historical_data.get("volume_history", [])

        if len(price_history) < self.min_samples:
            print(
                f"Not enough data to train market regime model: {len(price_history)} samples < {self.min_samples}"
            )
            return False

        # Prepare feature vectors
        feature_vectors = []

        # Create sliding windows to extract features
        for i in range(30, len(price_history)):
            window_prices = price_history[i - 30 : i + 1]
            window_volumes = volume_history[i - 30 : i + 1] if volume_history else None

            features = self.extract_features(window_prices, window_volumes)
            if not features:
                continue

            # Extract feature vector in the correct order
            feature_vector = []
            for feature_name in self.features:
                feature_value = features.get(feature_name, 0.0)
                feature_vector.append(feature_value)

            feature_vectors.append(feature_vector)

        if len(feature_vectors) < self.min_samples:
            print(
                f"Not enough feature vectors extracted: {len(feature_vectors)} < {self.min_samples}"
            )
            return False

        # Convert to numpy array
        feature_matrix = np.array(feature_vectors)

        # Fit scaler
        self.scaler.fit(feature_matrix)

        # Scale features
        scaled_features = self.scaler.transform(feature_matrix)

        # Fit PCA for visualization (optional)
        self.pca.fit(scaled_features)

        # Fit K-means model
        self.kmeans_model.fit(scaled_features)

        # Analyze clusters to map them to regimes
        self._map_clusters_to_regimes(feature_matrix, self.kmeans_model.labels_)

        # Save the trained model
        self.save_model()

        return True

    def _map_clusters_to_regimes(
        self, feature_matrix: np.ndarray, labels: np.ndarray
    ) -> None:
        """
        Map cluster numbers to meaningful market regimes
        by analyzing the characteristics of each cluster

        Args:
            feature_matrix: Matrix of feature vectors
            labels: Cluster labels for each feature vector
        """
        # Extract the indices of each feature in the matrix
        trend_idx = (
            self.features.index("trend_30d") if "trend_30d" in self.features else -1
        )
        vol_idx = (
            self.features.index("volatility_30d")
            if "volatility_30d" in self.features
            else -1
        )

        if trend_idx == -1 or vol_idx == -1:
            # Default mapping if we can't find the indices
            return

        # Analyze each cluster
        cluster_stats = {}
        for cluster in range(self.n_regimes):
            # Get data points in this cluster
            cluster_data = feature_matrix[labels == cluster]

            if len(cluster_data) == 0:
                continue

            # Calculate statistics
            avg_trend = np.mean(cluster_data[:, trend_idx])
            avg_vol = np.mean(cluster_data[:, vol_idx])

            cluster_stats[cluster] = {
                "avg_trend": avg_trend,
                "avg_vol": avg_vol,
                "count": len(cluster_data),
            }

        # Map clusters to regimes based on their characteristics
        sorted_by_trend = sorted(cluster_stats.items(), key=lambda x: x[1]["avg_trend"])
        sorted_by_vol = sorted(cluster_stats.items(), key=lambda x: x[1]["avg_vol"])

        # Most negative trend = BEAR
        if sorted_by_trend:
            self.regime_mapping[sorted_by_trend[0][0]] = self.BEAR_MARKET

        # Most positive trend = BULL
        if len(sorted_by_trend) > 1:
            self.regime_mapping[sorted_by_trend[-1][0]] = self.BULL_MARKET

        # Highest volatility = VOLATILE
        if sorted_by_vol:
            self.regime_mapping[sorted_by_vol[-1][0]] = self.VOLATILE_MARKET

        # Lowest volatility and trend near zero = SIDEWAYS
        for cluster, stats in cluster_stats.items():
            if (
                abs(stats["avg_trend"]) < self.trend_thresh
                and stats["avg_vol"] < self.volatility_thresh
            ):
                self.regime_mapping[cluster] = self.SIDEWAYS_MARKET
                break

    def get_regime_transition_matrix(self) -> pd.DataFrame:
        """
        Calculate the transition probability matrix between regimes

        Returns:
            Pandas DataFrame with transition probabilities
        """
        if len(self._historical_regimes) < 10:
            return pd.DataFrame()

        # Extract regime sequence
        regime_sequence = [item["regime"] for item in self._historical_regimes]

        # Find unique regimes
        unique_regimes = set(regime_sequence)

        # Initialize transition matrix
        transition_matrix = pd.DataFrame(
            0, index=unique_regimes, columns=unique_regimes
        )

        # Count transitions
        for i in range(1, len(regime_sequence)):
            prev_regime = regime_sequence[i - 1]
            curr_regime = regime_sequence[i]
            transition_matrix.loc[prev_regime, curr_regime] += 1

        # Convert to probabilities
        for row in unique_regimes:
            row_sum = transition_matrix.loc[row].sum()
            if row_sum > 0:
                transition_matrix.loc[row] = transition_matrix.loc[row] / row_sum

        return transition_matrix

    def get_regime_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get the history of regime detections

        Args:
            days: Number of days of history to return

        Returns:
            List of regime detection results
        """
        return self._historical_regimes[-days:]

    def get_regime_weights(self, regime: str) -> Dict[str, float]:
        """
        Get recommended signal weights for a specific market regime

        Args:
            regime: The detected market regime

        Returns:
            Dictionary of weight multipliers for each signal layer
        """
        # Default weights (no adjustment)
        default_weights = {
            "LAYER_1_TECHNICAL": 1.0,
            "LAYER_2_LOGISTICS": 1.0,
            "LAYER_3_GLOBAL_MACRO": 1.0,
            "LAYER_4_ADOPTION": 1.0,
        }

        # Regime-specific weights based on documentation
        weights_map = {
            self.BULL_MARKET: {
                "LAYER_1_TECHNICAL": 1.2,
                "LAYER_2_LOGISTICS": 0.9,
                "LAYER_3_GLOBAL_MACRO": 0.8,
                "LAYER_4_ADOPTION": 1.3,
            },
            self.BEAR_MARKET: {
                "LAYER_1_TECHNICAL": 1.0,
                "LAYER_2_LOGISTICS": 1.2,
                "LAYER_3_GLOBAL_MACRO": 1.3,
                "LAYER_4_ADOPTION": 1.2,
            },
            self.SIDEWAYS_MARKET: {
                "LAYER_1_TECHNICAL": 1.3,
                "LAYER_2_LOGISTICS": 0.8,
                "LAYER_3_GLOBAL_MACRO": 0.9,
                "LAYER_4_ADOPTION": 0.7,
            },
            self.VOLATILE_MARKET: {
                "LAYER_1_TECHNICAL": 0.7,
                "LAYER_2_LOGISTICS": 1.1,
                "LAYER_3_GLOBAL_MACRO": 1.2,
                "LAYER_4_ADOPTION": 1.0,
            },
            self.LOW_VOL_MARKET: {
                "LAYER_1_TECHNICAL": 1.2,
                "LAYER_2_LOGISTICS": 0.9,
                "LAYER_3_GLOBAL_MACRO": 0.8,
                "LAYER_4_ADOPTION": 0.8,
            },
        }

        return weights_map.get(regime, default_weights)
