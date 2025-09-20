#!/usr/bin/env python3
"""
Adaptive Signal Weight Module

This module implements a TensorFlow-based model that dynamically adjusts
signal weights based on recent performance and market conditions.

Key features:
- Automatically retrains every 24 hours using the last 7 days of data
- Recognizes different market regimes and adapts weights accordingly
- Incorporates all 15 signals from the multi-layered portfolio
- Provides optimal signal weights to maximize performance
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import numpy as np

# Try to import joblib - used for model persistence
try:
    import joblib

    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    print("joblib not available. Model saving and loading will be disabled.")

# TensorFlow and related imports - wrapped in try-except for optional dependency
try:
    import tensorflow as tf
    from tensorflow import keras  # noqa: F401
    from tensorflow.keras import layers  # noqa: F401
    from tensorflow.keras.callbacks import (
        EarlyStopping,  # noqa: F401
        ModelCheckpoint,
        TensorBoard,
    )
    from tensorflow.keras.layers import (
        BatchNormalization,  # noqa: F401
        Dense,
        Dropout,
        Input,
    )
    from tensorflow.keras.models import Model, Sequential  # noqa: F401
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.regularizers import l1_l2

    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow not available. Adaptive weight model will be disabled.")

# scikit-learn for preprocessing and evaluation - wrapped in try-except for optional dependency
try:
    # For market regime detection
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.metrics import (
        mean_absolute_error,  # noqa: F401
        mean_squared_error,
        r2_score,
    )
    from sklearn.model_selection import train_test_split  # noqa: F401
    from sklearn.preprocessing import MinMaxScaler, StandardScaler  # noqa: F401

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("scikit-learn not available. Adaptive weight model will be disabled.")

# Import the base Module class
from core.module_manager import Module


class AdaptiveWeightModule(Module):
    """
    TensorFlow-based module that dynamically adjusts signal weights
    based on market conditions and recent performance
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the adaptive weight module"""
        super().__init__(config)
        self.name = "adaptive_weight_module"
        self.version = "1.0.0"
        self.description = "Adaptive signal weight optimization using TensorFlow"

        # Configure from provided config or use defaults
        self.config = config or {}

        # Signal configuration
        self.n_signals = self.config.get("n_signals", 15)  # Total number of signals
        self.signal_layers = {
            "LAYER_1_TECHNICAL": ["RSI", "MACD", "Bollinger", "Volume", "Sentiment"],
            "LAYER_2_LOGISTICS": [
                "Port_Congestion",
                "Diesel",
                "Supply_Chain",
                "Container",
            ],
            "LAYER_3_GLOBAL_MACRO": [
                "Inflation",
                "Regulatory",
                "Remittance",
                "CBDC",
                "FATF",
            ],
            "LAYER_4_ADOPTION": ["Chainalysis_Global"],
        }

        # Training configuration
        self.lookback_days = self.config.get("lookback_days", 7)
        self.retrain_frequency_hours = self.config.get("retrain_frequency_hours", 24)
        self.min_samples_required = self.config.get("min_samples_required", 50)

        # Model hyperparameters
        self.learning_rate = self.config.get("learning_rate", 0.001)
        self.batch_size = self.config.get("batch_size", 32)
        self.epochs = self.config.get("epochs", 100)
        self.early_stopping_patience = self.config.get("early_stopping_patience", 10)
        self.dropout_rate = self.config.get("dropout_rate", 0.2)
        self.l1_reg = self.config.get("l1_reg", 0.0001)
        self.l2_reg = self.config.get("l2_reg", 0.0001)

        # Market regime detection
        self.n_regimes = self.config.get(
            "n_regimes", 4
        )  # Number of market regimes to detect
        self.regime_features = self.config.get(
            "regime_features",
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

        # Model directory for saving/loading
        self.model_dir = os.path.join(
            self.config.get("model_dir", "models"), "adaptive_weight_module"
        )
        os.makedirs(self.model_dir, exist_ok=True)

        # Data storage for training
        self.data_store = os.path.join(
            self.config.get("data_dir", "data"), "adaptive_weight_data"
        )
        os.makedirs(self.data_store, exist_ok=True)

        # Initialize models
        self.weight_model = None  # The main weight optimization model
        self.regime_model = None  # Market regime classification model
        self.scalers = {}  # Data scalers for preprocessing

        # Signal weight constraints
        self.min_weight = self.config.get("min_weight", 0.01)
        self.max_weight = self.config.get("max_weight", 0.5)

        # Last training time
        self.last_trained = None

        # Load existing models if available
        self._load_models()

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data and generate optimized signal weights

        Args:
            data: Dictionary containing all signal outputs and market data

        Returns:
            Dictionary containing optimized weights and metadata
        """
        try:
            # Extract required data
            signal_data = data.get("signals", {})
            market_data = data.get("market_data", {})
            timestamp = data.get("timestamp", datetime.now().isoformat())

            # Check if models need to be trained/retrained
            self._check_and_retrain(signal_data, market_data)

            # Identify current market regime
            regime_features = self._extract_regime_features(market_data)
            current_regime = self._identify_market_regime(regime_features)

            # Prepare input for weight model
            model_inputs = self._prepare_model_inputs(
                signal_data, regime_features, current_regime
            )

            # Generate optimized weights
            optimized_weights = self._generate_optimal_weights(
                model_inputs, current_regime
            )

            # Organize the results
            result = {
                "optimized_weights": optimized_weights,
                "market_regime": current_regime,
                "regime_confidence": self._get_regime_confidence(regime_features),
                "model_version": self.version,
                "last_trained": self.last_trained,
                "timestamp": timestamp,
            }

            # Store this result for future training
            self._store_result_for_training(
                signal_data, market_data, optimized_weights, current_regime, timestamp
            )

            return result

        except Exception as e:
            print(f"Error in AdaptiveWeightModule.process: {str(e)}")
            return self._default_weights()

    def get_schema(self) -> Dict[str, Any]:
        """Return the input/output schema for this module"""
        return {
            "input": {
                "type": "object",
                "properties": {
                    "signals": {
                        "type": "object",
                        "description": "All signal outputs from different modules",
                    },
                    "market_data": {
                        "type": "object",
                        "description": "Market data including price, volume, volatility",
                    },
                    "timestamp": {
                        "type": "string",
                        "description": "ISO format timestamp for the current data",
                    },
                },
                "required": ["signals", "market_data"],
            },
            "output": {
                "type": "object",
                "properties": {
                    "optimized_weights": {
                        "type": "object",
                        "description": "Optimized weights for all signals",
                    },
                    "market_regime": {
                        "type": "string",
                        "description": "Identified market regime/condition",
                    },
                    "regime_confidence": {
                        "type": "number",
                        "description": "Confidence in the regime classification",
                    },
                    "model_version": {
                        "type": "string",
                        "description": "Version of the model used",
                    },
                    "last_trained": {
                        "type": "string",
                        "description": "ISO format timestamp of last model training",
                    },
                },
                "required": ["optimized_weights", "market_regime"],
            },
        }

    def _build_weight_model(self) -> keras.Model:
        """
        Build the TensorFlow model for signal weight optimization

        Returns:
            Compiled Keras model
        """
        # Define input shapes
        signal_input = Input(shape=(self.n_signals,), name="signal_input")
        regime_input = Input(shape=(self.n_regimes,), name="regime_input")
        market_input = Input(shape=(len(self.regime_features),), name="market_input")

        # Process signal inputs
        x_signal = Dense(
            32, activation="relu", kernel_regularizer=l1_l2(self.l1_reg, self.l2_reg)
        )(signal_input)
        x_signal = BatchNormalization()(x_signal)
        x_signal = Dropout(self.dropout_rate)(x_signal)

        # Process market inputs
        x_market = Dense(
            16, activation="relu", kernel_regularizer=l1_l2(self.l1_reg, self.l2_reg)
        )(market_input)
        x_market = BatchNormalization()(x_market)
        x_market = Dropout(self.dropout_rate)(x_market)

        # Combine all inputs
        combined = tf.keras.layers.concatenate([x_signal, x_market, regime_input])

        # Hidden layers
        x = Dense(
            64, activation="relu", kernel_regularizer=l1_l2(self.l1_reg, self.l2_reg)
        )(combined)
        x = BatchNormalization()(x)
        x = Dropout(self.dropout_rate)(x)

        x = Dense(
            32, activation="relu", kernel_regularizer=l1_l2(self.l1_reg, self.l2_reg)
        )(x)
        x = BatchNormalization()(x)
        x = Dropout(self.dropout_rate)(x)

        # Output layer - weights for each signal
        # Using sigmoid to ensure weights are between 0 and 1
        outputs = Dense(self.n_signals, activation="sigmoid", name="weight_output")(x)

        # Create model
        model = Model(
            inputs=[signal_input, regime_input, market_input], outputs=outputs
        )

        # Compile model
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss="mean_squared_error",  # MSE loss for regression task
            metrics=["mean_absolute_error", "mean_squared_error"],
        )

        return model

    def _build_regime_model(self) -> None:
        """
        Build the market regime detection model using K-means clustering

        This uses unsupervised learning to identify market regimes
        """
        self.regime_model = KMeans(
            n_clusters=self.n_regimes, random_state=42, n_init=10
        )

    def _check_and_retrain(
        self, signal_data: Dict[str, Any], market_data: Dict[str, Any]
    ) -> None:
        """
        Check if models need retraining and retrain if necessary

        Args:
            signal_data: Current signal outputs
            market_data: Current market data
        """
        current_time = datetime.now()

        # Initialize models if they don't exist
        if self.weight_model is None:
            self._build_models()

        # Check if it's time to retrain (24 hour intervals)
        if self.last_trained is None or (current_time - self.last_trained) > timedelta(
            hours=self.retrain_frequency_hours
        ):
            # Load historical data for training
            train_data = self._load_training_data()

            if len(train_data) >= self.min_samples_required:
                print(
                    f"Retraining adaptive weight models with {len(train_data)} samples..."
                )
                self._train_models(train_data)
                self.last_trained = current_time
                self._save_models()
                print("Model retraining complete.")
            else:
                print(
                    f"Not enough data for retraining. Have {len(train_data)} samples, need {self.min_samples_required}."
                )

    def _build_models(self) -> None:
        """Build all required models"""
        print("Building adaptive weight models...")
        self._build_regime_model()
        self.weight_model = self._build_weight_model()
        print("Models built successfully.")

    def _load_training_data(self) -> List[Dict[str, Any]]:
        """
        Load historical data for model training

        Returns:
            List of dictionaries containing training samples
        """
        training_data = []

        # Calculate the cutoff date (last 7 days)
        cutoff_date = datetime.now() - timedelta(days=self.lookback_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        # List all data files
        data_files = [f for f in os.listdir(self.data_store) if f.endswith(".json")]

        # Filter by date
        recent_files = [f for f in data_files if f.split("_")[0] >= cutoff_str]

        # Load data from each file
        for filename in recent_files:
            try:
                with open(os.path.join(self.data_store, filename), "r") as f:
                    data = json.load(f)
                    training_data.append(data)
            except Exception as e:
                print(f"Error loading training data from {filename}: {str(e)}")

        return training_data

    def _prepare_training_data(
        self, raw_data: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
        """
        Prepare training data for model training

        Args:
            raw_data: List of raw data samples

        Returns:
            Tuple of (X, y) where X contains input features and y contains target values
        """
        # Extract features and targets
        signal_features = []
        market_features = []
        _regimes = []
        performance_targets = []
        weight_targets = []

        for sample in raw_data:
            # Extract signal features
            if "signal_data" in sample:
                signal_vector = self._extract_signal_vector(sample["signal_data"])
                signal_features.append(signal_vector)

            # Extract market features
            if "market_data" in sample:
                market_vector = self._extract_regime_features(sample["market_data"])
                market_features.append(market_vector)

            # Extract weights and performance (targets)
            if "optimized_weights" in sample and "performance" in sample:
                weight_targets.append(list(sample["optimized_weights"].values()))
                performance_targets.append(sample["performance"])

        # Convert to numpy arrays
        X_signal = np.array(signal_features)
        X_market = np.array(market_features)
        y_weights = np.array(weight_targets)
        _y_performance = np.array(performance_targets)

        # Normalize features
        self.scalers["signal"] = StandardScaler().fit(X_signal)
        self.scalers["market"] = StandardScaler().fit(X_market)

        X_signal_scaled = self.scalers["signal"].transform(X_signal)
        X_market_scaled = self.scalers["market"].transform(X_market)

        # Train regime model and transform data
        regimes_onehot = self._train_regime_model(X_market_scaled)

        # Prepare final input and output dictionaries
        X = {
            "signal_input": X_signal_scaled,
            "market_input": X_market_scaled,
            "regime_input": regimes_onehot,
        }

        y = {"weight_output": y_weights}

        return X, y

    def _train_regime_model(self, X_market_scaled: np.ndarray) -> np.ndarray:
        """
        Train the regime model and get one-hot encoded regimes

        Args:
            X_market_scaled: Scaled market features

        Returns:
            One-hot encoded regimes
        """
        # Reduce dimensionality for better clustering
        if X_market_scaled.shape[1] > 3 and X_market_scaled.shape[0] > 3:
            pca = PCA(n_components=3)
            X_reduced = pca.fit_transform(X_market_scaled)
        else:
            X_reduced = X_market_scaled

        # Fit the regime model
        self.regime_model.fit(X_reduced)

        # Get regime labels
        labels = self.regime_model.predict(X_reduced)

        # Convert to one-hot encoding
        regimes_onehot = np.zeros((len(labels), self.n_regimes))
        for i, label in enumerate(labels):
            regimes_onehot[i, label] = 1

        return regimes_onehot

    def _train_models(self, training_data: List[Dict[str, Any]]) -> None:
        """
        Train all models using the provided data

        Args:
            training_data: List of training data samples
        """
        # Prepare training data
        X, y = self._prepare_training_data(training_data)

        # Split into training and validation sets
        X_train = {}
        X_val = {}

        for key in X:
            X_train[key], X_val[key], y_train, y_val = train_test_split(
                X[key], y["weight_output"], test_size=0.2, random_state=42
            )

        # Callbacks for training
        callbacks = [
            EarlyStopping(
                monitor="val_loss",
                patience=self.early_stopping_patience,
                restore_best_weights=True,
            ),
            ModelCheckpoint(
                filepath=os.path.join(self.model_dir, "best_weight_model.h5"),
                monitor="val_loss",
                save_best_only=True,
            ),
            TensorBoard(log_dir=os.path.join(self.model_dir, "logs")),
        ]

        # Train the weight model
        history = self.weight_model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=self.epochs,
            batch_size=self.batch_size,
            callbacks=callbacks,
            verbose=1,
        )

        # Print training results
        val_loss = min(history.history["val_loss"])
        print(f"Training completed. Validation loss: {val_loss:.4f}")

    def _save_models(self) -> None:
        """Save all models and scalers"""
        # Create model directory if it doesn't exist
        os.makedirs(self.model_dir, exist_ok=True)

        # Save the weight model
        if self.weight_model is not None:
            self.weight_model.save(os.path.join(self.model_dir, "weight_model.h5"))

        # Save the regime model
        if self.regime_model is not None and JOBLIB_AVAILABLE:
            joblib.dump(
                self.regime_model, os.path.join(self.model_dir, "regime_model.joblib")
            )

        # Save scalers
        if self.scalers:
            joblib.dump(self.scalers, os.path.join(self.model_dir, "scalers.joblib"))

        # Save metadata
        metadata = {
            "last_trained": datetime.now().isoformat(),
            "version": self.version,
            "n_signals": self.n_signals,
            "n_regimes": self.n_regimes,
        }

        with open(os.path.join(self.model_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f)

    def _load_models(self) -> None:
        """Load models and scalers if they exist"""
        # Check if models exist
        weight_model_path = os.path.join(self.model_dir, "weight_model.h5")
        regime_model_path = os.path.join(self.model_dir, "regime_model.joblib")
        scalers_path = os.path.join(self.model_dir, "scalers.joblib")
        metadata_path = os.path.join(self.model_dir, "metadata.json")

        # Load metadata if exists
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    self.last_trained = datetime.fromisoformat(
                        metadata.get("last_trained", "")
                    )
                    print(f"Found existing model last trained at: {self.last_trained}")
            except Exception as e:
                print(f"Error loading metadata: {str(e)}")

        # Load weight model if exists
        if os.path.exists(weight_model_path):
            try:
                self.weight_model = keras.models.load_model(weight_model_path)
                print(f"Loaded weight model from {weight_model_path}")
            except Exception as e:
                print(f"Error loading weight model: {str(e)}")
                self.weight_model = None

        # Load regime model if exists
        if os.path.exists(regime_model_path) and JOBLIB_AVAILABLE:
            try:
                self.regime_model = joblib.load(regime_model_path)
                print(f"Loaded regime model from {regime_model_path}")
            except Exception as e:
                print(f"Error loading regime model: {str(e)}")
                self._build_regime_model()

        # Load scalers if they exist
        if os.path.exists(scalers_path) and JOBLIB_AVAILABLE:
            try:
                self.scalers = joblib.load(scalers_path)
                print(f"Loaded data scalers from {scalers_path}")
            except Exception as e:
                print(f"Error loading scalers: {str(e)}")
                self.scalers = {}

    def _extract_signal_vector(self, signal_data: Dict[str, Any]) -> List[float]:
        """
        Extract signal values and confidences as a feature vector

        Args:
            signal_data: Dictionary of signal data

        Returns:
            List of signal features
        """
        features = []

        # Process each signal layer
        for layer_name, signals in self.signal_layers.items():
            for signal in signals:
                if signal in signal_data:
                    # Extract signal strength (normalized to -1 to 1)
                    signal_value = signal_data[signal].get("strength", 0)

                    # Extract confidence (0 to 1)
                    confidence = signal_data[signal].get("confidence", 0.5)

                    # Add to features
                    features.append(signal_value)
                    features.append(confidence)
                else:
                    # Missing signals get zeros
                    features.append(0.0)
                    features.append(0.0)

        return features

    def _extract_regime_features(self, market_data: Dict[str, Any]) -> List[float]:
        """
        Extract market features for regime classification

        Args:
            market_data: Dictionary of market data

        Returns:
            List of market features
        """
        features = []

        # Check if we have price history
        price_history = market_data.get("price_history", [])

        if price_history:
            # Calculate volatility features
            volatility_1d = self._calculate_volatility(price_history, 1)
            volatility_7d = self._calculate_volatility(price_history, 7)
            volatility_30d = self._calculate_volatility(price_history, 30)

            # Calculate trend features
            trend_1d = self._calculate_trend(price_history, 1)
            trend_7d = self._calculate_trend(price_history, 7)
            trend_30d = self._calculate_trend(price_history, 30)

            # Volume changes
            volume_change_1d = self._calculate_volume_change(market_data, 1)
            volume_change_7d = self._calculate_volume_change(market_data, 7)

            # Technical indicators
            rsi_value = market_data.get("rsi", 50)
            bb_width = market_data.get("bb_width", 0)

            features = [
                volatility_1d,
                volatility_7d,
                volatility_30d,
                trend_1d,
                trend_7d,
                trend_30d,
                volume_change_1d,
                volume_change_7d,
                rsi_value,
                bb_width,
            ]
        else:
            # Default features if no price history
            features = [0.0] * len(self.regime_features)

        return features

    def _calculate_volatility(
        self, price_history: List[Dict[str, Any]], days: int
    ) -> float:
        """Calculate price volatility over specified days"""
        if not price_history or len(price_history) < days:
            return 0.0

        # Extract recent prices
        recent_prices = [p["close"] for p in price_history[-days:]]

        # Calculate returns
        returns = np.diff(recent_prices) / recent_prices[:-1]

        # Calculate volatility (standard deviation of returns)
        volatility = np.std(returns) if len(returns) > 0 else 0.0

        return volatility

    def _calculate_trend(self, price_history: List[Dict[str, Any]], days: int) -> float:
        """Calculate price trend over specified days"""
        if not price_history or len(price_history) < days:
            return 0.0

        # Extract recent prices
        recent_prices = [p["close"] for p in price_history[-days:]]

        # Calculate simple trend (ending price / starting price - 1)
        trend = (
            (recent_prices[-1] / recent_prices[0] - 1) if recent_prices[0] > 0 else 0.0
        )

        return trend

    def _calculate_volume_change(self, market_data: Dict[str, Any], days: int) -> float:
        """Calculate volume change over specified days"""
        volume_history = market_data.get("volume_history", [])

        if not volume_history or len(volume_history) < days:
            return 0.0

        # Extract recent volumes
        recent_volumes = volume_history[-days:]

        # Calculate volume change
        volume_change = (
            (recent_volumes[-1] / recent_volumes[0] - 1)
            if recent_volumes[0] > 0
            else 0.0
        )

        return volume_change

    def _identify_market_regime(self, regime_features: List[float]) -> str:
        """
        Identify the current market regime based on features

        Args:
            regime_features: List of market regime features

        Returns:
            String representing the market regime
        """
        if self.regime_model is None:
            self._build_regime_model()
            return "UNKNOWN"

        # Convert to numpy array and reshape for single sample
        features = np.array(regime_features).reshape(1, -1)

        # Apply dimensionality reduction if needed
        if len(regime_features) > 3:
            pca = PCA(n_components=3)
            features_reduced = pca.fit_transform(features)
        else:
            features_reduced = features

        # Predict regime
        regime_id = self.regime_model.predict(features_reduced)[0]

        # Map regime ID to name
        regime_names = ["BULL", "BEAR", "SIDEWAYS", "VOLATILE"]

        if regime_id < len(regime_names):
            return regime_names[regime_id]
        else:
            return f"REGIME_{regime_id}"

    def _get_regime_confidence(self, regime_features: List[float]) -> float:
        """
        Get confidence in the regime classification

        Args:
            regime_features: List of market regime features

        Returns:
            Confidence score (0 to 1)
        """
        if self.regime_model is None:
            return 0.5

        # Convert to numpy array and reshape for single sample
        features = np.array(regime_features).reshape(1, -1)

        # Apply dimensionality reduction
        if len(regime_features) > 3:
            pca = PCA(n_components=3)
            features_reduced = pca.fit_transform(features)
        else:
            features_reduced = features

        # Get distance to cluster center as a proxy for confidence
        cluster_id = self.regime_model.predict(features_reduced)[0]
        distance = np.linalg.norm(
            features_reduced - self.regime_model.cluster_centers_[cluster_id]
        )

        # Convert distance to confidence (closer = higher confidence)
        max_distance = 5.0  # Tunable parameter
        confidence = max(0, 1 - (distance / max_distance))

        return confidence

    def _prepare_model_inputs(
        self,
        signal_data: Dict[str, Any],
        regime_features: List[float],
        current_regime: str,
    ) -> Dict[str, np.ndarray]:
        """
        Prepare inputs for the weight model

        Args:
            signal_data: Current signal data
            regime_features: Market regime features
            current_regime: Identified market regime

        Returns:
            Dictionary of model inputs
        """
        # Extract signal vector
        signal_vector = self._extract_signal_vector(signal_data)
        signal_vector = np.array(signal_vector).reshape(1, -1)

        # Process market features
        market_vector = np.array(regime_features).reshape(1, -1)

        # One-hot encode regime
        regime_names = ["BULL", "BEAR", "SIDEWAYS", "VOLATILE"]
        regime_onehot = np.zeros((1, self.n_regimes))

        if current_regime in regime_names:
            regime_id = regime_names.index(current_regime)
            regime_onehot[0, regime_id] = 1

        # Scale features if scalers exist
        if "signal" in self.scalers:
            signal_vector = self.scalers["signal"].transform(signal_vector)

        if "market" in self.scalers:
            market_vector = self.scalers["market"].transform(market_vector)

        # Prepare model inputs
        model_inputs = {
            "signal_input": signal_vector,
            "market_input": market_vector,
            "regime_input": regime_onehot,
        }

        return model_inputs

    def _generate_optimal_weights(
        self, model_inputs: Dict[str, np.ndarray], current_regime: str
    ) -> Dict[str, float]:
        """
        Generate optimal signal weights

        Args:
            model_inputs: Prepared model inputs
            current_regime: Current market regime

        Returns:
            Dictionary mapping signal names to optimized weights
        """
        if self.weight_model is None:
            return self._default_weights()

        # Make prediction with the model
        raw_weights = self.weight_model.predict(model_inputs)[0]

        # Apply constraints
        constrained_weights = np.clip(raw_weights, self.min_weight, self.max_weight)

        # Normalize weights to sum to 1.0
        normalized_weights = constrained_weights / constrained_weights.sum()

        # Map weights back to signal names
        optimized_weights = {}
        weight_idx = 0

        for layer_name, signals in self.signal_layers.items():
            for signal in signals:
                optimized_weights[signal] = float(normalized_weights[weight_idx])
                weight_idx += 1
                if weight_idx >= len(normalized_weights):
                    break

        return optimized_weights

    def _store_result_for_training(
        self,
        signal_data: Dict[str, Any],
        market_data: Dict[str, Any],
        optimized_weights: Dict[str, float],
        current_regime: str,
        timestamp: str,
    ) -> None:
        """
        Store current results for future training

        Args:
            signal_data: Current signal data
            market_data: Current market data
            optimized_weights: Generated weights
            current_regime: Identified market regime
            timestamp: Current timestamp
        """
        # Create data store if it doesn't exist
        os.makedirs(self.data_store, exist_ok=True)

        # Create data record
        data_record = {
            "timestamp": timestamp,
            "signal_data": signal_data,
            "market_data": market_data,
            "optimized_weights": optimized_weights,
            "market_regime": current_regime,
            "performance": None,  # Will be updated later with actual performance
        }

        # Generate filename with timestamp
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        filename = f"{ts.strftime('%Y-%m-%d_%H-%M-%S')}_weights.json"

        # Save to file
        with open(os.path.join(self.data_store, filename), "w") as f:
            json.dump(data_record, f, indent=2)

    def _default_weights(self) -> Dict[str, Any]:
        """Return default weights when model is unavailable"""
        # Create balanced weights across all signals
        all_signals = []
        for signals in self.signal_layers.values():
            all_signals.extend(signals)

        # Default to equal weights
        weight = 1.0 / len(all_signals) if all_signals else 0.0

        default_weights = {signal: weight for signal in all_signals}

        return {
            "optimized_weights": default_weights,
            "market_regime": "UNKNOWN",
            "regime_confidence": 0.5,
            "model_version": self.version,
            "last_trained": None,
        }


if __name__ == "__main__":
    # Create sample data for testing
    sample_data = {
        "signals": {
            "RSI": {"signal": "BUY", "strength": 0.8, "confidence": 0.7},
            "MACD": {"signal": "SELL", "strength": -0.6, "confidence": 0.8},
            "Bollinger": {"signal": "HOLD", "strength": 0.1, "confidence": 0.5},
            # ... other signals
        },
        "market_data": {
            "price_history": [
                {
                    "time": "2025-09-10T00:00:00",
                    "open": 45000,
                    "high": 46000,
                    "low": 44800,
                    "close": 45900,
                },
                {
                    "time": "2025-09-11T00:00:00",
                    "open": 45900,
                    "high": 47000,
                    "low": 45500,
                    "close": 46800,
                },
                {
                    "time": "2025-09-12T00:00:00",
                    "open": 46800,
                    "high": 48000,
                    "low": 46500,
                    "close": 47500,
                },
                # ... more price data
            ],
            "rsi": 65,
            "bb_width": 0.15,
        },
    }

    # Initialize and test the module
    adaptive_weight_module = AdaptiveWeightModule()
    result = adaptive_weight_module.process(sample_data)

    print("\nAdaptive Weight Module Test:")
    print(f"Market Regime: {result['market_regime']}")
    print(f"Regime Confidence: {result['regime_confidence']:.2f}")
    print("\nOptimized Weights:")

    weights = result["optimized_weights"]
    for signal, weight in weights.items():
        print(f"  {signal}: {weight:.4f}")
