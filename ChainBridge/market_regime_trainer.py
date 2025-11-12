#!/usr/bin/env python3
"""
Market Regime Trainer - Trains ML models for regime detection
"""

import os
import logging
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from lightgbm import LGBMClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix
import joblib

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class MarketRegimeTrainer:
    """
    Trains and compares ML models for market regime detection
    """

    def __init__(self, data_dir="data/regime_training", model_dir="ml_models"):
        self.data_dir = data_dir
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

    def load_training_data(self):
        """Load training data from file"""
        try:
            data_path = os.path.join(self.data_dir, "regime_training_data.csv")

            # If the default file doesn't exist, look for the most recent timestamped file
            if not os.path.exists(data_path):
                import glob

                pattern = os.path.join(self.data_dir, "regime_training_data_*.csv")
                matching_files = glob.glob(pattern)

                if matching_files:
                    # Get the most recent file by timestamp
                    latest_file = max(matching_files, key=os.path.getctime)
                    data_path = latest_file
                    logger.info(
                        f"Using latest training data file: {os.path.basename(data_path)}"
                    )
                else:
                    logger.warning("No training data found, generating sample data")
                    self._generate_sample_data()
                    return (
                        self.load_training_data()
                    )  # Recursive call to load the generated data

            df = pd.read_csv(data_path)  # type: ignore

            # Prepare features and labels
            feature_cols = [
                "rsi_14",
                "macd",
                "macd_signal",
                "macd_hist",
                "bb_upper",
                "bb_middle",
                "bb_lower",
                "bb_width",
                "bb_position",
                "volume_ratio",
                "price_change_1h",
                "price_change_24h",
                "volatility_24h",
                "trend_strength",
            ]

            # Encode labels
            label_encoder = LabelEncoder()
            df["regime_encoded"] = label_encoder.fit_transform(df["regime"])

            logger.info(f"📊 Loaded {len(df)} training samples")
            logger.info(f"🏷️  Regimes: {label_encoder.classes_}")

            return df, feature_cols, label_encoder

        except Exception as e:
            logger.error(f"Error loading training data: {e}")
            return None, None, None

    def _generate_sample_data(self):
        """Generate sample training data"""
        logger.info("🎲 Generating sample training data...")

        from market_regime_data_collector import MarketRegimeDataCollector

        collector = MarketRegimeDataCollector()
        df = collector.collect_multi_asset_features()

        if df is not None:
            df = collector.calculate_technical_features(df)
            df = collector.label_market_regime(df)
            collector.save_training_data(df, "regime_training_data.csv")

    def compare_models(self, X_train, X_test, y_train, y_test):
        """Compare different ML models"""
        logger.info("🔬 Comparing ML models...")

        models = {
            "LightGBM": LGBMClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                num_leaves=31,
                objective="multiclass",
                random_state=42,
                verbose=-1,  # Suppress output
            ),
            "RandomForest": RandomForestClassifier(
                n_estimators=100, max_depth=10, random_state=42, class_weight="balanced"
            ),
            "SVM": SVC(
                kernel="rbf",
                C=1.0,
                gamma="scale",
                probability=True,
                random_state=42,
                class_weight="balanced",
            ),
        }

        results = {}

        for name, model in models.items():
            try:
                logger.info(f"Training {name}...")

                # Train model
                model.fit(X_train, y_train)

                # Cross-validation
                cv_scores = cross_val_score(model, X_train, y_train, cv=5)
                cv_mean = cv_scores.mean()
                cv_std = cv_scores.std()

                # Test predictions
                y_pred = model.predict(X_test)

                # Store results
                results[name] = {
                    "model": model,
                    "cv_mean": cv_mean,
                    "cv_std": cv_std,
                    "predictions": y_pred,
                    "test_data": (X_test, y_test),
                }

                logger.info(f"✅ {name} trained - CV: {cv_mean:.3f} (+/- {cv_std:.3f})")
            except Exception as e:
                logger.error(f"Error training {name}: {e}")
                continue

        # Select best model
        if results:
            best_model_name = max(results.keys(), key=lambda x: results[x]["cv_mean"])
            logger.info(
                f"🏆 Best model: {best_model_name} (CV: {results[best_model_name]['cv_mean']:.3f})"
            )

            return results, best_model_name
        else:
            logger.error("No models trained successfully")
            return None, None

    def save_model(self, model_results, model_name, label_encoder, feature_cols):
        """Save trained model to file"""
        try:
            model_data = {
                "model": model_results["model"],
                "label_encoder": label_encoder,
                "feature_cols": feature_cols,
                "cv_score": model_results["cv_mean"],
                "training_date": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "model_name": model_name,
            }

            model_path = os.path.join(self.model_dir, "regime_detection_model.pkl")
            joblib.dump(model_data, model_path)

            logger.info(f"💾 Model saved: {model_path}")
            return model_path

        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return None

    def evaluate_model(self, model_results, label_encoder):
        """Evaluate model performance"""
        try:
            X_test, y_test = model_results["test_data"]
            y_pred = model_results["predictions"]

            # Classification report
            target_names = label_encoder.classes_
            report = classification_report(y_test, y_pred, target_names=target_names)

            # Confusion matrix
            cm = confusion_matrix(y_test, y_pred)

            logger.info("📊 Model Evaluation:")
            logger.info(f"\n{report}")

            logger.info("🔢 Confusion Matrix:")
            logger.info(f"{cm}")

            return report, cm

        except Exception as e:
            logger.error(f"Error evaluating model: {e}")
            return None, None

    def train_model(self):
        """Complete model training pipeline"""
        logger.info("🚀 Starting model training pipeline...")

        # Load data
        df, feature_cols, label_encoder = self.load_training_data()

        if df is None or len(df) < 100:
            logger.error("Insufficient training data")
            return None

        # Prepare data
        X = df[feature_cols]
        y = df["regime_encoded"]

        # Handle missing values
        X = X.fillna(X.mean())

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        logger.info(f"📊 Training set: {len(X_train)} samples")
        logger.info(f"🧪 Test set: {len(X_test)} samples")

        # Compare models
        results, best_model_name = self.compare_models(X_train, X_test, y_train, y_test)

        if results and best_model_name:
            # Save best model
            best_results = results[best_model_name]
            model_path = self.save_model(
                best_results, best_model_name, label_encoder, feature_cols
            )

            # Evaluate model
            self.evaluate_model(best_results, label_encoder)

            logger.info("✅ Model training completed successfully")
            return model_path
        else:
            logger.error("Model training failed")
            return None


if __name__ == "__main__":
    # Demo the trainer
    print("🔬 Market Regime Trainer Demo")
    print("=" * 35)

    trainer = MarketRegimeTrainer()

    # Train model
    model_path = trainer.train_model()

    if model_path:
        print(f"✅ Model trained and saved: {model_path}")
    else:
        print("❌ Model training failed")

    print("\n✅ Demo Complete")
