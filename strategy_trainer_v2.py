#!/usr/bin/env python3
"""
Strategy Trainer v2 - Optimized for Tree-Based Models

This trainer uses robust clipping instead of StandardScaler for preprocessing,
which is more appropriate for tree-based models like LightGBM that don't require
feature standardization but benefit from outlier handling.
"""

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import logging
import yaml
import os
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

# Import our robust preprocessing utilities
from utils.feature_hygiene import robust_clip, remove_constant_features, handle_missing_values

logger = logging.getLogger(__name__)

class StrategyTrainerV2:
    """
    Enhanced strategy trainer optimized for tree-based models.

    Key improvements:
    - Uses robust clipping instead of StandardScaler
    - Better handling of financial time series data
    - Improved feature preprocessing pipeline
    - Enhanced model validation and metrics
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize the strategy trainer.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.models = {}
        self.feature_importance = {}
        self.model_metrics = {}

        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.get('logging_level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found, using defaults")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'model_params': {
                'objective': 'binary',
                'metric': 'binary_logloss',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.9,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbose': -1
            },
            'training_params': {
                'test_size': 0.2,
                'random_state': 42,
                'early_stopping_rounds': 50,
                'num_boost_round': 1000
            },
            'preprocessing': {
                'clip_percentiles': (1.0, 99.0),
                'remove_constants': True,
                'handle_missing': 'median'
            },
            'logging_level': 'INFO'
        }

    def preprocess_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess features using robust methods instead of standardization.

        Args:
            X: Raw feature DataFrame

        Returns:
            Preprocessed feature DataFrame
        """
        logger.info("Starting feature preprocessing...")

        # Handle missing values
        X = handle_missing_values(X, strategy=self.config['preprocessing']['handle_missing'])
        logger.info(f"Handled missing values, shape: {X.shape}")

        # Remove constant features
        if self.config['preprocessing']['remove_constants']:
            X = remove_constant_features(X)
            logger.info(f"Removed constant features, shape: {X.shape}")

        # Apply robust clipping instead of StandardScaler
        lower_pct, upper_pct = self.config['preprocessing']['clip_percentiles']
        X = robust_clip(X, lower_percentile=lower_pct, upper_percentile=upper_pct)
        logger.info(f"Applied robust clipping ({lower_pct}%, {upper_pct}%), shape: {X.shape}")

        return X

    def train_model(self, X: pd.DataFrame, y: pd.Series,
                   model_name: str = "default_model",
                   custom_params: Optional[Dict] = None) -> lgb.Booster:
        """
        Train a LightGBM model with robust preprocessing.

        Args:
            X: Feature DataFrame
            y: Target series
            model_name: Name for the trained model
            custom_params: Custom model parameters

        Returns:
            Trained LightGBM model
        """
        logger.info(f"Training model: {model_name}")

        # Preprocess features
        X_processed = self.preprocess_features(X)

        # Split data with time series awareness
        X_train, X_valid, y_train, y_valid = self._time_series_split(X_processed, y)

        # Prepare LightGBM datasets
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_valid, label=y_valid, reference=train_data)

        # Get model parameters
        params = self.config['model_params'].copy()
        if custom_params:
            params.update(custom_params)

        # Train model
        callbacks = [
            lgb.early_stopping(self.config['training_params']['early_stopping_rounds']),
            lgb.log_evaluation(period=100)
        ]

        model = lgb.train(
            params,
            train_data,
            num_boost_round=self.config['training_params']['num_boost_round'],
            valid_sets=[train_data, valid_data],
            valid_names=['train', 'valid'],
            callbacks=callbacks
        )

        # Store model and evaluate
        self.models[model_name] = model
        self._evaluate_model(model, X_valid, y_valid, model_name)

        # Store feature importance
        self.feature_importance[model_name] = dict(zip(
            X_train.columns,
            model.feature_importance(importance_type='gain')
        ))

        logger.info(f"Model {model_name} trained successfully")
        return model

    def _time_series_split(self, X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Split data maintaining time series order.

        Args:
            X: Feature DataFrame
            y: Target series

        Returns:
            Train/validation splits
        """
        test_size = self.config['training_params']['test_size']

        # For time series, we want to use the most recent data for validation
        split_idx = int(len(X) * (1 - test_size))

        X_train = X.iloc[:split_idx]
        X_valid = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_valid = y.iloc[split_idx:]

        logger.info(f"Time series split: train={len(X_train)}, valid={len(X_valid)}")
        return X_train, X_valid, y_train, y_valid

    def _evaluate_model(self, model: lgb.Booster, X_valid: pd.DataFrame,
                       y_valid: pd.Series, model_name: str) -> Dict[str, float]:
        """
        Evaluate model performance and store metrics.

        Args:
            model: Trained LightGBM model
            X_valid: Validation features
            y_valid: Validation targets
            model_name: Name of the model

        Returns:
            Dictionary of evaluation metrics
        """
        # Get predictions
        y_pred_proba = model.predict(X_valid)
        y_pred = (y_pred_proba > 0.5).astype(int)

        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(y_valid, y_pred),
            'precision': precision_score(y_valid, y_pred, zero_division=0),
            'recall': recall_score(y_valid, y_pred, zero_division=0),
            'f1_score': f1_score(y_valid, y_pred, zero_division=0)
        }

        self.model_metrics[model_name] = metrics

        logger.info(f"Model {model_name} metrics: {metrics}")
        return metrics

    def predict(self, X: pd.DataFrame, model_name: str = "default_model") -> np.ndarray:
        """
        Make predictions using trained model.

        Args:
            X: Feature DataFrame
            model_name: Name of model to use

        Returns:
            Prediction probabilities
        """
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found. Available models: {list(self.models.keys())}")

        # Preprocess features using same pipeline as training
        X_processed = self.preprocess_features(X)

        return self.models[model_name].predict(X_processed)

    def get_feature_importance(self, model_name: str = "default_model",
                              top_n: Optional[int] = None) -> Dict[str, float]:
        """
        Get feature importance for trained model.

        Args:
            model_name: Name of model
            top_n: Number of top features to return

        Returns:
            Dictionary of feature importance scores
        """
        if model_name not in self.feature_importance:
            raise ValueError(f"No feature importance found for model {model_name}")

        importance = self.feature_importance[model_name]

        if top_n:
            sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)
            importance = dict(sorted_features[:top_n])

        return importance

    def save_model(self, model_name: str, filepath: str) -> None:
        """
        Save trained model to file.

        Args:
            model_name: Name of model to save
            filepath: Path to save model
        """
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")

        # Create directory if it doesn't exist
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        self.models[model_name].save_model(filepath)
        logger.info(f"Model {model_name} saved to {filepath}")

    def load_model(self, model_name: str, filepath: str) -> lgb.Booster:
        """
        Load model from file.

        Args:
            model_name: Name to assign to loaded model
            filepath: Path to model file

        Returns:
            Loaded LightGBM model
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file {filepath} not found")

        model = lgb.Booster(model_file=filepath)
        self.models[model_name] = model
        logger.info(f"Model loaded from {filepath} as {model_name}")

        return model

    def get_model_summary(self, model_name: str = "default_model") -> Dict[str, Any]:
        """
        Get comprehensive summary of trained model.

        Args:
            model_name: Name of model

        Returns:
            Dictionary with model summary information
        """
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")

        summary = {
            'model_name': model_name,
            'metrics': self.model_metrics.get(model_name, {}),
            'feature_importance': self.get_feature_importance(model_name, top_n=20),
            'config': self.config
        }

        return summary

def main():
    """Example usage of StrategyTrainerV2."""
    # Create sample data for demonstration
    np.random.seed(42)
    n_samples = 1000
    n_features = 20

    # Generate synthetic financial features
    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )

    # Add some outliers to demonstrate robust clipping
    X.iloc[0, 0] = 100  # Extreme positive outlier
    X.iloc[1, 1] = -50  # Extreme negative outlier

    # Generate target (simple classification based on feature sum)
    y = (X.sum(axis=1) > 0).astype(int)

    # Initialize trainer
    trainer = StrategyTrainerV2()

    # Train model
    model = trainer.train_model(X, y, model_name="demo_model")

    # Get predictions on training data (for demonstration)
    predictions = trainer.predict(X[:100], model_name="demo_model")

    # Get model summary
    summary = trainer.get_model_summary("demo_model")

    print("Training completed successfully!")
    print(f"Model metrics: {summary['metrics']}")
    print(f"Top 5 features: {list(summary['feature_importance'].keys())[:5]}")

if __name__ == "__main__":
    main()