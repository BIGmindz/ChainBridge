#!/usr/bin/env python3
"""
Adaptive Weight Model Trainer

This module handles the training and evaluation of the TensorFlow model
that dynamically optimizes signal weights based on market conditions.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Tuple

import numpy as np

# TensorFlow imports - wrapped in try-except for optional dependency
try:
    import tensorflow as tf  # noqa: F401
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, TensorBoard

    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow not available. Adaptive weight trainer will be disabled.")

# Import related modules
from modules.adaptive_weight_module.adaptive_weight_model import AdaptiveWeightModule


class AdaptiveWeightTrainer:
    """
    Trainer for the adaptive weight TensorFlow model
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the trainer"""
        self.config = config or {}

        # Initialize the model
        self.model = AdaptiveWeightModule(self.config)

        # Configure data paths
        self.data_dir = os.path.join(self.config.get("data_dir", "data"), "adaptive_weight_data")
        os.makedirs(self.data_dir, exist_ok=True)

        # Training configuration
        self.batch_size = self.config.get("batch_size", 32)
        self.epochs = self.config.get("epochs", 100)
        self.validation_split = self.config.get("validation_split", 0.2)
        self.early_stopping_patience = self.config.get("early_stopping_patience", 10)

        # Model checkpoint directory
        self.checkpoint_dir = os.path.join(self.config.get("model_dir", "models"), "adaptive_weight_checkpoints")
        os.makedirs(self.checkpoint_dir, exist_ok=True)

        # TensorBoard logs directory
        self.logs_dir = os.path.join(self.config.get("logs_dir", "logs"), "adaptive_weight_logs")
        os.makedirs(self.logs_dir, exist_ok=True)

    def collect_training_data(self, lookback_days: int = 30) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
        """
        Collect and preprocess training data from stored results

        Args:
            lookback_days: Number of days of data to include

        Returns:
            Tuple of (training inputs, training targets)
        """
        # Calculate the start date
        start_date = datetime.now() - timedelta(days=lookback_days)

        # Initialize data storage
        signal_data_list = []
        market_data_list = []
        regime_data_list = []
        performance_data_list = []

        # Iterate through data files
        data_files = [f for f in os.listdir(self.data_dir) if f.endswith(".json")]
        for filename in data_files:
            # Parse the timestamp from the filename
            try:
                file_date_str = filename.split("_")[0]
                file_date = datetime.strptime(file_date_str, "%Y%m%d")

                # Skip files older than the lookback period
                if file_date < start_date:
                    continue

                # Load the data file
                file_path = os.path.join(self.data_dir, filename)
                with open(file_path, "r") as f:
                    data = json.load(f)

                # Extract data components
                signal_data = data.get("signal_data", {})
                market_data = data.get("market_data", {})
                regime_data = data.get("regime_data", {})
                performance_data = data.get("performance_data", {})

                # Skip incomplete data
                if not signal_data or not market_data or not regime_data:
                    continue

                # Process and append data
                signal_data_list.append(self._process_signal_data(signal_data))  # type: ignore
                market_data_list.append(self._process_market_data(market_data))  # type: ignore
                regime_data_list.append(self._process_regime_data(regime_data))  # type: ignore
                performance_data_list.append(self._process_performance_data(performance_data))  # type: ignore

            except Exception as e:
                print(f"Error processing data file {filename}: {str(e)}")
                continue

        # Check if we have enough data
        min_samples = self.config.get("min_samples_required", 50)
        if len(signal_data_list) < min_samples:
            print(f"Insufficient data for training: {len(signal_data_list)} samples < {min_samples}")
            return {}, {}

        # Convert lists to numpy arrays
        signal_array = np.array(signal_data_list)
        market_array = np.array(market_data_list)
        regime_array = np.array(regime_data_list)
        performance_array = np.array(performance_data_list)

        # Create inputs and targets
        inputs = {
            "signal_input": signal_array,
            "market_input": market_array,
            "regime_input": regime_array,
        }

        targets = {"weight_output": performance_array}

        return inputs, targets

    def _process_signal_data(self, signal_data: Dict[str, Any]) -> np.ndarray:
        """Process signal data into a numpy array"""
        # Extract signal values from all layers
        signals = []

        # Process each layer's signals
        for layer_name, layer_signals in signal_data.items():
            if not isinstance(layer_signals, dict):
                continue

            for signal_name, signal_value in layer_signals.items():
                # Extract numeric signal strength
                if isinstance(signal_value, dict) and "strength" in signal_value:
                    signals.append(float(signal_value["strength"]))  # type: ignore
                elif isinstance(signal_value, (int, float)):
                    signals.append(float(signal_value))  # type: ignore
                else:
                    signals.append(0.0)  # Default value for missing signals  # type: ignore

        return np.array(signals)

    def _process_market_data(self, market_data: Dict[str, Any]) -> np.ndarray:
        """Process market data into a numpy array"""
        # Extract market features
        features = []

        for feature_name in self.model.regime_features:
            feature_value = market_data.get(feature_name, 0.0)
            features.append(float(feature_value))  # type: ignore

        return np.array(features)

    def _process_regime_data(self, regime_data: Dict[str, Any]) -> np.ndarray:
        """Process regime data into a one-hot encoded numpy array"""
        # Get the current regime
        regime = regime_data.get("regime", "UNKNOWN")

        # Create one-hot encoding for regime
        regimes = ["BULL", "BEAR", "SIDEWAYS", "VOLATILE", "LOW_VOLATILITY", "UNKNOWN"]
        one_hot = [1.0 if r == regime else 0.0 for r in regimes[: self.model.n_regimes]]

        return np.array(one_hot)

    def _process_performance_data(self, performance_data: Dict[str, Any]) -> np.ndarray:
        """
        Process performance data into target weights

        This uses performance metrics to estimate optimal signal weights
        """
        # Get layer weights (default to 1.0)
        layer_weights = performance_data.get("layer_weights", {})

        # Default weights if performance data is missing
        if not layer_weights:
            return np.ones(self.model.n_signals) / self.model.n_signals

        # Extract weights for all signals
        signal_weights = []

        # Map layer weights to individual signal weights
        for layer, signals in self.model.signal_layers.items():
            layer_weight = layer_weights.get(layer, 1.0)

            # Each signal in the layer gets the layer weight
            for _ in signals:
                signal_weights.append(float(layer_weight))  # type: ignore

        # Normalize weights to sum to 1.0
        signal_weights = np.array(signal_weights)
        if np.sum(signal_weights) > 0:  # type: ignore
            signal_weights = signal_weights / np.sum(signal_weights)  # type: ignore

        return signal_weights

    def train_model(self, lookback_days: int = 30) -> Dict[str, Any]:
        """
        Train the adaptive weight model

        Args:
            lookback_days: Number of days of data to include in training

        Returns:
            Dictionary with training results and metrics
        """
        # Start timing
        start_time = datetime.now()

        # Collect training data
        inputs, targets = self.collect_training_data(lookback_days)

        if not inputs or not targets:
            return {
                "status": "error",
                "message": "Insufficient data for training",
                "timestamp": datetime.now().isoformat(),
            }

        # Ensure the model is built
        if self.model.weight_model is None:
            self.model._build_weight_model()

        # Configure callbacks
        callbacks = [
            EarlyStopping(
                monitor="val_loss",
                patience=self.early_stopping_patience,
                restore_best_weights=True,
            ),
            ModelCheckpoint(
                filepath=os.path.join(self.checkpoint_dir, "model_{epoch:02d}_{val_loss:.4f}.h5"),
                save_best_only=True,
                monitor="val_loss",
                mode="min",
            ),
            TensorBoard(
                log_dir=os.path.join(self.logs_dir, datetime.now().strftime("%Y%m%d-%H%M%S")),
                histogram_freq=1,
            ),
        ]

        # Train the model
        history = self.model.weight_model.fit(
            inputs,
            targets["weight_output"],
            batch_size=self.batch_size,
            epochs=self.epochs,
            validation_split=self.validation_split,
            callbacks=callbacks,
            verbose=1,
        )

        # Calculate training time
        end_time = datetime.now()
        training_time = (end_time - start_time).total_seconds()

        # Save the model
        self.model._save_weight_model()

        # Update last trained timestamp
        self.model.last_trained = end_time.isoformat()

        # Return training results
        return {
            "status": "success",
            "epochs_completed": len(history.history["loss"]),
            "final_loss": float(history.history["loss"][-1]),  # type: ignore
            "final_val_loss": float(history.history["val_loss"][-1]),  # type: ignore
            "training_time_seconds": training_time,
            "samples_used": inputs["signal_input"].shape[0],
            "timestamp": end_time.isoformat(),
        }

    def evaluate_model(self, test_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Evaluate the adaptive weight model

        Args:
            test_data: Optional test data dictionary

        Returns:
            Dictionary with evaluation metrics
        """
        # If no test data is provided, use the most recent data
        if test_data is None:
            # Get the most recent data file
            data_files = sorted(
                [f for f in os.listdir(self.data_dir) if f.endswith(".json")],
                reverse=True,
            )

            if not data_files:
                return {
                    "status": "error",
                    "message": "No data available for evaluation",
                    "timestamp": datetime.now().isoformat(),
                }

            # Load the most recent data file
            file_path = os.path.join(self.data_dir, data_files[0])
            with open(file_path, "r") as f:
                test_data = json.load(f)

        # Extract components for evaluation
        signal_data = test_data.get("signal_data", {})
        market_data = test_data.get("market_data", {})
        regime_data = test_data.get("regime_data", {})

        if not signal_data or not market_data:
            return {
                "status": "error",
                "message": "Incomplete test data for evaluation",
                "timestamp": datetime.now().isoformat(),
            }

        # Process the data
        processed_signal = self._process_signal_data(signal_data)
        processed_market = self._process_market_data(market_data)
        processed_regime = self._process_regime_data(regime_data)

        # Reshape for prediction
        signal_input = np.expand_dims(processed_signal, axis=0)
        market_input = np.expand_dims(processed_market, axis=0)
        regime_input = np.expand_dims(processed_regime, axis=0)

        # Make a prediction
        try:
            prediction = self.model.weight_model.predict(
                {
                    "signal_input": signal_input,
                    "market_input": market_input,
                    "regime_input": regime_input,
                }
            )

            # Extract the predicted weights
            predicted_weights = prediction[0]

            # Map predicted weights to signal names
            signal_names = []
            for layer, signals in self.model.signal_layers.items():
                signal_names.extend(signals)

            # Create a dictionary mapping signal names to weights
            weight_dict = {signal: weight for signal, weight in zip(signal_names, predicted_weights)}

            # Group weights by layer
            layer_weights = {}
            for layer, signals in self.model.signal_layers.items():
                layer_weights[layer] = {signal: weight_dict.get(signal, 0.0) for signal in signals}

            # Calculate average weight per layer
            layer_avg_weights = {layer: np.mean([w for w in weights.values()]) for layer, weights in layer_weights.items()}

            return {
                "status": "success",
                "predicted_weights": weight_dict,
                "layer_weights": layer_weights,
                "layer_avg_weights": layer_avg_weights,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Error during model evaluation: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            }

    def save_training_results(self, results: Dict[str, Any]) -> None:
        """
        Save training results to a file

        Args:
            results: Training results dictionary
        """
        # Create a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_training_results.json"

        # Save to file
        file_path = os.path.join(self.logs_dir, filename)
        with open(file_path, "w") as f:
            json.dump(results, f, indent=2)


if __name__ == "__main__":
    # Example usage
    config = {
        "data_dir": "data",
        "model_dir": "models",
        "logs_dir": "logs",
        "batch_size": 32,
        "epochs": 100,
        "validation_split": 0.2,
        "early_stopping_patience": 10,
        "min_samples_required": 50,
    }

    trainer = AdaptiveWeightTrainer(config)

    # Train the model
    training_results = trainer.train_model(lookback_days=30)
    print(f"Training results: {training_results}")

    # Evaluate the model
    evaluation_results = trainer.evaluate_model()
    print(f"Evaluation results: {evaluation_results}")
