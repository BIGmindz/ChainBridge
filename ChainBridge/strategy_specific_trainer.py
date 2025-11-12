#!/usr/bin/env python3
"""
Strategy-Specific Model Trainer for Pattern-as-a-Service Architecture

This trainer creates specialized ML models for each trading strategy,
trained only on the symbols that strategy is configured to trade.
This ensures each model is a specialist for its specific market pattern.
"""

import os
import sys
import yaml
import pandas as pd
import joblib
import logging
from lightgbm import LGBMClassifier
from sklearn.preprocessing import StandardScaler

# --- Add project root to system path for local imports ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)


def consolidate_data(data_directory: str) -> pd.DataFrame:
    """Finds all relevant CSVs and consolidates them into a single DataFrame."""
    all_files = [
        os.path.join(data_directory, f)
        for f in os.listdir(data_directory)
        if f.endswith(".csv")
    ]
    if not all_files:
        return pd.DataFrame()

    required_columns = [
        "timestamp",
        "symbol",
        "price",
        "rsi_value",
        "ob_imbalance",
        "vol_imbalance",
    ]
    df_list = []
    for file in all_files:
        try:
            if os.path.getsize(file) > 0:
                header_df = pd.read_csv(file, nrows=0)  # type: ignore
                if all(col in header_df.columns for col in required_columns):
                    df_list.append(pd.read_csv(file))  # type: ignore
        except Exception:
            continue  # Skip corrupted files

    if not df_list:
        return pd.DataFrame()

    df = pd.concat(df_list, ignore_index=True)  # type: ignore
    df.drop_duplicates(subset=["timestamp", "symbol"], inplace=True)
    return df


def main():
    """
    Main script to train a specialized trading model for each defined strategy.
    """
    logging.info("🚀 Starting Strategy-Specific Model Trainer...")
    logging.info("=" * 60)

    # --- Load Consolidated Historical Data ---
    logging.info("📊 Loading consolidated historical data...")
    consolidated_df = consolidate_data("data/")

    if consolidated_df.empty:
        logging.error(
            "❌ No valid historical data found. Please ensure CSV files exist in the data/ directory."
        )
        logging.info(
            "💡 Required CSV columns: timestamp, symbol, price, rsi_value, ob_imbalance, vol_imbalance"
        )
        return

    logging.info(f"📈 Final dataset: {len(consolidated_df)} rows, {len(consolidated_df['symbol'].unique())} unique symbols")  # type: ignore

    # --- Discover Strategies to Train ---
    strategy_dir = "strategies/"
    if not os.path.exists(strategy_dir):
        logging.error(f"❌ Strategy directory '{strategy_dir}' not found.")
        return

    strategy_folders = [
        f
        for f in os.listdir(strategy_dir)
        if os.path.isdir(os.path.join(strategy_dir, f))
    ]
    if not strategy_folders:
        logging.error(f"❌ No strategy folders found in '{strategy_dir}'")
        return

    logging.info(
        f"🎯 Found {len(strategy_folders)} strategies to process: {strategy_folders}"
    )

    trained_strategies = 0

    for strategy_name in strategy_folders:
        strategy_path = os.path.join(strategy_dir, strategy_name)
        logging.info("=" * 60)
        logging.info(f"🎯 Processing Strategy: '{strategy_name.upper()}'")
        logging.info(f"📁 Strategy path: {strategy_path}")

        try:
            # --- Load the strategy's own config to see which symbols it trades ---
            config_path = os.path.join(strategy_path, "config.yaml")
            if not os.path.exists(config_path):
                logging.warning(
                    f"⚠️  No config.yaml found for strategy '{strategy_name}'. Skipping."
                )
                continue

            with open(config_path, "r") as f:
                strategy_config = yaml.safe_load(f)

            target_symbols = strategy_config.get("exchange", {}).get("symbols", [])
            if not target_symbols:
                logging.warning(
                    f"⚠️  No symbols defined in config for '{strategy_name}'. Skipping."
                )
                continue

            logging.info(f"   📊 Strategy targets symbols: {target_symbols}")

            # --- Filter the master dataset for this strategy's symbols ---
            strategy_df = consolidated_df[
                consolidated_df["symbol"].isin(target_symbols)
            ].copy()

            if strategy_df.empty:
                logging.warning(
                    f"⚠️  No data found for symbols {target_symbols} in strategy '{strategy_name}'. Skipping."
                )
                continue

            min_samples = (
                strategy_config.get("signals", {})
                .get("machine_learning", {})
                .get("min_training_samples", 30)
            )
            if len(strategy_df) < min_samples:
                logging.warning(
                    f"⚠️  Insufficient data for '{strategy_name}' (have {len(strategy_df)}, need {min_samples}). Skipping."
                )
                continue

            logging.info(
                f"   📈 Training model on {len(strategy_df)} relevant data points..."
            )

            # --- Feature Engineering and Labeling ---
            logging.info("   🔧 Performing feature engineering...")

            # Calculate price change percentage using diff/shift
            strategy_df["price_change_pct"] = (
                strategy_df["price"].diff() / strategy_df["price"].shift(1)
            ) * 100

            # Create labels based on future price movement
            strategy_df["future_price"] = strategy_df["price"].shift(-1)
            strategy_df["label"] = 0  # Default to HOLD

            # Define thresholds for buy/sell signals
            buy_threshold = 1.0005  # 0.05% increase
            sell_threshold = 0.9995  # 0.05% decrease

            # Apply labels where we have future price data
            mask_buy = (
                strategy_df["future_price"] > strategy_df["price"] * buy_threshold
            )
            mask_sell = (
                strategy_df["future_price"] < strategy_df["price"] * sell_threshold
            )

            strategy_df.loc[mask_buy, "label"] = 1  # BUY
            strategy_df.loc[mask_sell, "label"] = -1  # SELL

            # Drop rows with NaN values created by diff() and shift() AFTER all calculations
            logging.info(f"   📊 Before dropna: {len(strategy_df)} rows")
            strategy_df = strategy_df.dropna(
                subset=["price_change_pct", "future_price"]
            )
            logging.info(f"   📊 After dropna: {len(strategy_df)} rows")

            if len(strategy_df) < min_samples:
                logging.warning(
                    f"⚠️  After feature engineering, insufficient data (have {len(strategy_df)}, need {min_samples}). Skipping."
                )
                continue

            # Define feature columns
            feature_cols = [
                "rsi_value",
                "ob_imbalance",
                "vol_imbalance",
                "price_change_pct",
            ]

            # Add additional features if available
            if "africa_factor" in strategy_df.columns:
                feature_cols.append("africa_factor")  # type: ignore
            if "sc_factor" in strategy_df.columns:
                feature_cols.append("sc_factor")  # type: ignore

            # Ensure all feature columns exist, filling missing ones with 0
            for col in feature_cols:
                if col not in strategy_df.columns:
                    strategy_df[col] = 0

            logging.info(f"   📊 Using features: {feature_cols}")
            logging.info(f"   📊 Final dataset: {len(strategy_df)} samples")

            # Create features and labels
            X = strategy_df[feature_cols].values
            y = strategy_df["label"].values

            # Count label distribution
            buy_count = sum(y == 1)  # type: ignore
            hold_count = sum(y == 0)  # type: ignore
            sell_count = sum(y == -1)  # type: ignore
            logging.info(
                f"   📊 Label distribution: BUY={buy_count}, HOLD={hold_count}, SELL={sell_count}"
            )

            # --- Train and Save Model & Scaler ---
            logging.info("   🤖 Training LightGBM model...")

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            model = LGBMClassifier(
                objective="multiclass",
                num_class=3,
                random_state=42,
                n_estimators=100,
                learning_rate=0.1,
            )

            model.fit(X_scaled, y)

            # Calculate training accuracy
            train_accuracy = model.score(X_scaled, y)

            # Save model and scaler
            model_path = os.path.join(strategy_path, "model.pkl")
            scaler_path = os.path.join(strategy_path, "scaler.pkl")

            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)

            logging.info(f"   ✅ Model for '{strategy_name}' trained and saved!")
            logging.info(f"   📊 Training accuracy: {train_accuracy:.2%}")
            logging.info(f"   💾 Model saved to: {model_path}")
            logging.info(f"   💾 Scaler saved to: {scaler_path}")

            trained_strategies += 1

        except Exception as e:
            logging.error(f"   ❌ Failed to process strategy '{strategy_name}': {e}")

    logging.info("=" * 60)
    logging.info(
        f"🎉 Training complete! Successfully trained {trained_strategies} strategies."
    )

    if trained_strategies == 0:
        logging.warning("⚠️  No strategies were successfully trained.")
        logging.info("💡 Make sure you have:")
        logging.info("   1. CSV data files in the data/ directory")
        logging.info("   2. Strategy folders in the strategies/ directory")
        logging.info("   3. config.yaml files in each strategy folder")
        logging.info("   4. Sufficient data for the symbols each strategy targets")


if __name__ == "__main__":
    main()
