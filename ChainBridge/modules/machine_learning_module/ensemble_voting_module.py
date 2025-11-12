#!/usr/bin/env python3
"""
Machine Learning Ensemble Module

This module implements ensemble voting for multiple ML models,
providing robust trading signal predictions through consensus.
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import joblib

    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    logging.warning("joblib not available. ML functionality will be disabled.")

from core.module_manager import Module


class EnsembleVotingModule(Module):
    """
    Ensemble voting module that combines predictions from multiple ML models
    for more robust trading decisions.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the ensemble voting module"""
        super().__init__(config)
        self.name = "ensemble_voting_module"
        self.version = "1.0.0"
        self.description = "Ensemble voting for multiple ML models"

        # Ensemble configuration
        self.model_paths = []
        self.scaler_paths = []
        self.models = []
        self.scalers = []
        self.voting_mechanism = "majority_vote"

        # Load ensemble configuration from environment
        self._load_ensemble_config()

    def get_schema(self) -> Dict[str, Any]:
        """Return the input/output schema for this module."""
        return {
            "input": {
                "type": "object",
                "properties": {
                    "price_data": {
                        "type": "object",
                        "description": "Current price and technical data",
                    },
                    "symbol": {"type": "string", "description": "Trading symbol"},
                },
                "required": ["price_data", "symbol"],
            },
            "output": {
                "type": "object",
                "properties": {
                    "signal": {
                        "type": "string",
                        "enum": ["BUY", "SELL", "HOLD"],
                        "description": "Ensemble trading signal",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence in the ensemble signal",
                    },
                    "ensemble_votes": {
                        "type": "object",
                        "description": "Breakdown of votes from individual models",
                    },
                    "individual_predictions": {
                        "type": "array",
                        "description": "Predictions from each individual model",
                    },
                    "model_count": {
                        "type": "integer",
                        "description": "Number of models in the ensemble",
                    },
                },
            },
        }

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data and return ensemble trading signal.
        This is the main entry point that matches the Module interface.
        """
        price_data = data.get("price_data", {})
        symbol = data.get("symbol", "UNKNOWN")

        return self.get_signal(price_data, symbol)

    def _load_ensemble_config(self):
        """Load ensemble configuration from environment variables"""
        if not JOBLIB_AVAILABLE:
            logging.error("joblib not available. Cannot load ML models.")
            return

        # Check if this is an ensemble strategy
        is_ensemble = os.getenv("BENSON_IS_ENSEMBLE", "false").lower() == "true"

        if is_ensemble:
            logging.info("🎯 Loading ensemble voting configuration...")

            # Get model paths from environment
            ensemble_models = os.getenv("BENSON_ENSEMBLE_MODELS", "")
            ensemble_scalers = os.getenv("BENSON_ENSEMBLE_SCALERS", "")
            voting_mechanism = os.getenv("BENSON_VOTING_MECHANISM", "majority_vote")

            if ensemble_models:
                self.model_paths = ensemble_models.split(",")
                logging.info(f"📊 Found {len(self.model_paths)} models for ensemble")

            if ensemble_scalers:
                self.scaler_paths = ensemble_scalers.split(",")

            self.voting_mechanism = voting_mechanism

            # Load the models
            self._load_models()
        else:
            # Single model mode - try to load from BENSON_MODEL
            single_model_path = os.getenv("BENSON_MODEL")
            single_scaler_path = os.getenv("BENSON_SCALER")

            if single_model_path and os.path.exists(single_model_path):
                self.model_paths = [single_model_path]
                self.scaler_paths = [single_scaler_path] if single_scaler_path else []
                self._load_models()
                logging.info("📊 Loaded single model configuration")

    def _load_models(self):
        """Load ML models and scalers from configured paths"""
        self.models = []
        self.scalers = []

        for i, model_path in enumerate(self.model_paths):
            try:
                if os.path.exists(model_path):
                    model = joblib.load(model_path)
                    self.models.append(model)  # type: ignore
                    logging.info(
                        f"✅ Loaded model {i + 1}: {os.path.basename(model_path)}"
                    )

                    # Load corresponding scaler if available
                    if i < len(self.scaler_paths) and self.scaler_paths[i]:
                        scaler_path = self.scaler_paths[i]
                        if os.path.exists(scaler_path):
                            scaler = joblib.load(scaler_path)
                            self.scalers.append(scaler)  # type: ignore
                            logging.info(
                                f"✅ Loaded scaler {i + 1}: {os.path.basename(scaler_path)}"
                            )
                        else:
                            self.scalers.append(None)  # type: ignore
                            logging.warning(f"⚠️  Scaler not found: {scaler_path}")
                    else:
                        self.scalers.append(None)  # type: ignore
                else:
                    logging.warning(f"⚠️  Model not found: {model_path}")
                    self.models.append(None)  # type: ignore
                    self.scalers.append(None)  # type: ignore

            except Exception as e:
                logging.error(f"❌ Failed to load model {model_path}: {e}")
                self.models.append(None)  # type: ignore
                self.scalers.append(None)  # type: ignore

        logging.info(
            f"🎯 Ensemble ready with {len([m for m in self.models if m is not None])} active models"
        )

    def get_signal(self, price_data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        Generate ensemble trading signal by combining predictions from multiple models.

        Args:
            price_data: Current price and technical data
            symbol: Trading symbol

        Returns:
            Dict containing ensemble signal and confidence
        """
        if not self.models or not any(m is not None for m in self.models):
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "ensemble_votes": {},
                "individual_predictions": [],
                "model_count": len([m for m in self.models if m is not None]),
                "error": "No models available",
            }

        # Extract features for ML prediction
        features = self._extract_features(price_data, symbol)

        if features is None:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "ensemble_votes": {},
                "individual_predictions": [],
                "model_count": len([m for m in self.models if m is not None]),
                "error": "Could not extract features",
            }

        # Get predictions from all models
        predictions = []
        confidences = []

        for i, (model, scaler) in enumerate(zip(self.models, self.scalers)):
            if model is None:
                continue

            try:
                # Prepare features for this model
                features_df = pd.DataFrame([features])

                # Scale features if scaler available
                if scaler:
                    try:
                        features_scaled = scaler.transform(features_df)
                    except ValueError as ve:
                        logging.warning(
                            f"Feature mismatch for model {i + 1}, skipping: {ve}"
                        )
                        continue
                else:
                    features_scaled = features_df.values

                # Make prediction
                if hasattr(model, "predict_proba"):
                    # Classification with probabilities
                    probabilities = model.predict_proba(features_scaled)[0]
                    prediction_idx = np.argmax(probabilities)
                    confidence = probabilities[prediction_idx]

                    # Convert prediction index to signal
                    signal = self._index_to_signal(prediction_idx)
                else:
                    # Direct prediction
                    prediction = model.predict(features_scaled)[0]
                    signal = self._prediction_to_signal(prediction)
                    confidence = (
                        0.5  # Default confidence for models without probabilities
                    )

                predictions.append(signal)  # type: ignore
                confidences.append(confidence)  # type: ignore

                logging.debug(
                    f"Model {i + 1} prediction: {signal} (confidence: {confidence:.3f})"
                )

            except Exception as e:
                logging.warning(f"Model {i + 1} prediction failed: {e}")
                continue

        if not predictions:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "ensemble_votes": {},
                "individual_predictions": [],
                "model_count": len([m for m in self.models if m is not None]),
                "error": "All model predictions failed",
            }

        # Perform ensemble voting
        ensemble_signal, ensemble_confidence, vote_breakdown = self._perform_voting(
            predictions, confidences
        )

        return {
            "signal": ensemble_signal,
            "confidence": ensemble_confidence,
            "ensemble_votes": vote_breakdown,
            "individual_predictions": predictions,
            "model_count": len([m for m in self.models if m is not None]),
        }

    def _extract_features(
        self, price_data: Dict[str, Any], symbol: str
    ) -> Optional[Dict[str, float]]:
        """Extract ML features from price data"""
        try:
            # Extract basic price and technical features
            features = {}

            # Price-based features
            if "close" in price_data:
                features["price"] = float(price_data["close"])  # type: ignore
            elif "last" in price_data:
                features["price"] = float(price_data["last"])  # type: ignore
            else:
                return None

            # Technical indicators (if available)
            if "rsi_value" in price_data:
                features["rsi_value"] = float(price_data["rsi_value"])  # type: ignore
            else:
                features["rsi_value"] = 50.0  # Neutral RSI

            if "ob_imbalance" in price_data:
                features["ob_imbalance"] = float(price_data["ob_imbalance"])  # type: ignore
            else:
                features["ob_imbalance"] = 0.0

            if "vol_imbalance" in price_data:
                features["vol_imbalance"] = float(price_data["vol_imbalance"])  # type: ignore
            else:
                features["vol_imbalance"] = 0.0

            # Calculate price change percentage
            if "previous_price" in price_data:
                features["price_change_pct"] = (
                    (features["price"] - float(price_data["previous_price"])) / float(price_data["previous_price"])  # type: ignore
                ) * 100
            else:
                features["price_change_pct"] = 0.0

            # Optional features
            if "africa_factor" in price_data:
                features["africa_factor"] = float(price_data["africa_factor"])  # type: ignore

            if "sc_factor" in price_data:
                features["sc_factor"] = float(price_data["sc_factor"])  # type: ignore

            return features

        except Exception as e:
            logging.error(f"Failed to extract features: {e}")
            return None

    def _index_to_signal(self, prediction_idx: int) -> str:
        """Convert model prediction index to trading signal"""
        # Assuming 3-class classification: 0=SELL, 1=HOLD, 2=BUY
        signal_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
        return signal_map.get(prediction_idx, "HOLD")

    def _prediction_to_signal(self, prediction: Any) -> str:
        """Convert raw prediction to trading signal"""
        if isinstance(prediction, (int, float)):
            if prediction > 0.5:
                return "BUY"
            elif prediction < -0.5:
                return "SELL"
            else:
                return "HOLD"
        elif isinstance(prediction, str):
            return prediction.upper()
        else:
            return "HOLD"

    def _perform_voting(
        self, predictions: List[str], confidences: List[float]
    ) -> Tuple[str, float, Dict]:
        """
        Perform ensemble voting based on configured mechanism.

        Returns:
            Tuple of (ensemble_signal, confidence, vote_breakdown)
        """
        if self.voting_mechanism == "majority_vote":
            return self._majority_vote(predictions, confidences)
        elif self.voting_mechanism == "weighted_vote":
            return self._weighted_vote(predictions, confidences)
        else:
            # Default to majority vote
            return self._majority_vote(predictions, confidences)

    def _majority_vote(
        self, predictions: List[str], confidences: List[float]
    ) -> Tuple[str, float, Dict]:
        """Perform simple majority voting"""
        # Count votes for each signal
        vote_counts = Counter(predictions)

        # Find the signal with most votes
        max_votes = max(vote_counts.values())
        winners = [
            signal for signal, count in vote_counts.items() if count == max_votes
        ]

        # If tie, choose the one with highest average confidence
        if len(winners) > 1:
            winner_confidences = {}
            for winner in winners:
                winner_indices = [
                    i for i, pred in enumerate(predictions) if pred == winner
                ]
                winner_confidences[winner] = np.mean(
                    [confidences[i] for i in winner_indices]
                )

            ensemble_signal = max(winner_confidences, key=winner_confidences.get)
            ensemble_confidence = winner_confidences[ensemble_signal]
        else:
            ensemble_signal = winners[0]
            # Calculate confidence as proportion of total votes
            ensemble_confidence = max_votes / len(predictions)

        # Create vote breakdown
        vote_breakdown = dict(vote_counts)
        vote_breakdown["total_votes"] = len(predictions)
        vote_breakdown["ensemble_signal"] = ensemble_signal

        return ensemble_signal, ensemble_confidence, vote_breakdown

    def _weighted_vote(
        self, predictions: List[str], confidences: List[float]
    ) -> Tuple[str, float, Dict]:
        """Perform weighted voting based on model confidences"""
        # Calculate weighted scores for each signal
        signal_weights = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}

        for prediction, confidence in zip(predictions, confidences):
            if prediction in signal_weights:
                signal_weights[prediction] += confidence

        # Find signal with highest weighted score
        ensemble_signal = max(signal_weights, key=signal_weights.get)
        ensemble_confidence = signal_weights[ensemble_signal] / sum(signal_weights.values())  # type: ignore

        # Create vote breakdown
        vote_breakdown = {
            "weighted_scores": signal_weights,
            "total_weight": sum(signal_weights.values()),  # type: ignore
            "ensemble_signal": ensemble_signal,
        }

        return ensemble_signal, ensemble_confidence, vote_breakdown

    def get_status(self) -> Dict[str, Any]:
        """Get module status and ensemble information"""
        return {
            "name": self.name,
            "version": self.version,
            "active_models": len([m for m in self.models if m is not None]),
            "total_models": len(self.models),
            "voting_mechanism": self.voting_mechanism,
            "is_ensemble": len(self.models) > 1,
            "joblib_available": JOBLIB_AVAILABLE,
        }
