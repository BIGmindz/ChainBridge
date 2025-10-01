import os
import sys
import pandas as pd
import joblib
import logging
from lightgbm import LGBMClassifier
from utils.feature_hygiene import robust_clip

# --- Add project root to system path for local imports ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def get_trading_symbols():
    """Get the list of symbols currently configured for trading."""
    try:
        import yaml

        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        symbols = config.get("symbols", [])
        logging.info(f"Loaded trading symbols from config: {symbols}")
        return symbols
    except Exception as e:
        logging.warning(f"Could not load trading symbols from config: {e}")
        # Fallback to some default symbols
        return ["BTC/USD", "ETH/USD", "SOL/USD", "DOGE/USD", "AVAX/USD"]


def consolidate_data(data_directory: str, trading_symbols: list) -> pd.DataFrame:
    """Finds and consolidates all valid trade logs into a single DataFrame."""
    all_files = [os.path.join(data_directory, f) for f in os.listdir(data_directory) if f.endswith(".csv")]
    if not all_files:
        logging.error(f"No historical data files found in '{data_directory}'.")
        return pd.DataFrame()

    logging.info(f"Consolidating {len(all_files)} data files for trading symbols: {trading_symbols}...")
    # More flexible column requirements - we'll handle missing columns
    df_list = []

    for file in all_files:
        try:
            df = pd.read_csv(file)  # type: ignore
            # Standardize column names
            column_mapping = {"rsi": "rsi_value", "timestamp": "timestamp", "ts_utc": "timestamp", "time": "timestamp"}
            df = df.rename(columns=column_mapping)

            # Ensure we have the basic required columns
            if "timestamp" in df.columns and "symbol" in df.columns and "price" in df.columns:
                # Filter to only include trading symbols
                df_filtered = df[df["symbol"].isin(trading_symbols)]
                if not df_filtered.empty:
                    df_list.append(df_filtered)  # type: ignore
                    logging.info(f"Loaded {len(df_filtered)} rows from {os.path.basename(file)} for trading symbols")
        except Exception as e:
            logging.warning(f"Could not load {file}: {e}")

    if not df_list:
        logging.error("No valid trade logs could be loaded for the configured trading symbols.")
        return pd.DataFrame()

    df = pd.concat(df_list, ignore_index=True)  # type: ignore
    df.drop_duplicates(subset=["timestamp", "symbol"], inplace=True)

    # Log symbol distribution
    symbol_counts = df["symbol"].value_counts()
    logging.info(f"Consolidated data for trading symbols: {symbol_counts.to_dict()}")  # type: ignore

    return df


def train_and_save_model(data: pd.DataFrame, regime_name: str, symbol_name: str, model_dir: str):
    """Trains a trading model for a specific symbol-regime combination and saves it."""
    model_name = f"{symbol_name}_{regime_name}"
    logging.info(f"--- Training model for '{model_name.upper()}' ---")

    if len(data) < 30:  # Reduced minimum samples for symbol-specific models
        logging.warning(f"Skipping '{model_name}' model: only {len(data)} samples available.")
        return

    # Feature Engineering
    df = data.copy()
    df["price_change_pct"] = (df["price"].diff() / df["price"].shift(1)) * 100
    df = df.dropna()

    # Use only available features
    available_features = ["rsi_value", "ob_imbalance", "vol_imbalance", "price_change_pct"]
    features = [f for f in available_features if f in df.columns]

    if not features:
        logging.error(f"No valid features found for {model_name}")
        return

    X = df[features].values

    # Create target labels
    df["label"] = 0
    df.loc[df["price"].shift(-1) > df["price"], "label"] = 1  # Buy
    df.loc[df["price"].shift(-1) < df["price"], "label"] = -1  # Sell
    y = df["label"].values

    # Scale features using robust clipping instead of StandardScaler
    X_scaled = robust_clip(pd.DataFrame(X)).values

    model = LGBMClassifier(random_state=42, n_estimators=50)  # Smaller model for symbol-specific
    model.fit(X_scaled, y)

    accuracy = model.score(X_scaled, y)
    logging.info(f"'{model_name.upper()}' model trained on {len(df)} samples. Accuracy: {accuracy:.2%}")

    # Save the trained model (no scaler needed with robust_clip)
    model_path = os.path.join(model_dir, f"model_{model_name}.pkl")
    joblib.dump(model, model_path)
    logging.info(f"✅ Saved '{model_name}' model to {model_path}")


def main():
    """
    Main orchestrator for training regime-specific models.
    """
    data_dir = "data/"
    model_dir = "ml_models/"
    os.makedirs(model_dir, exist_ok=True)

    # 1. Load the master regime detection model
    try:
        regime_model_dict = joblib.load(os.path.join(model_dir, "regime_detection_model.pkl"))
        regime_model = regime_model_dict["model"]  # Extract the actual model
        label_encoder = regime_model_dict.get("label_encoder")  # Get label encoder if available
        logging.info("✅ Loaded regime detection model")
    except FileNotFoundError:
        logging.error("FATAL: Regime detection model not found. Please train it first.")
        return
    except KeyError:
        logging.error("FATAL: Invalid model format. Expected 'model' key not found.")
        return

    # 2. Get trading symbols and consolidate historical data
    trading_symbols = get_trading_symbols()
    historical_df = consolidate_data(data_dir, trading_symbols)
    if historical_df.empty:
        return

    # 3. Tag data with regimes using the trained model
    # Use features that match our regime detection model
    regime_features = [
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

    # Map our data columns to regime model features
    column_mapping = {
        "rsi_value": "rsi_14",
        "ob_imbalance": "bb_position",  # Use as proxy
        "vol_imbalance": "volume_ratio",  # Use as proxy
    }

    # Create regime features DataFrame with same index as historical_df
    regime_df = pd.DataFrame(index=historical_df.index)

    # Add available features
    for feature in regime_features:
        if feature in historical_df.columns:
            regime_df[feature] = historical_df[feature]
        elif feature in column_mapping and column_mapping[feature] in historical_df.columns:
            regime_df[feature] = historical_df[column_mapping[feature]]
        else:
            # Fill missing features with reasonable defaults
            if "rsi" in feature.lower():
                regime_df[feature] = 50  # Neutral RSI
            elif "volatility" in feature.lower():
                regime_df[feature] = 0.03  # Moderate volatility
            elif "trend" in feature.lower():
                regime_df[feature] = 0.5  # Neutral trend
            else:
                regime_df[feature] = 0  # Default to 0

    logging.info(f"Created regime_df with shape: {regime_df.shape}")
    logging.info(f"Regime features: {regime_df.columns.tolist()}")  # type: ignore

    # Ensure we only predict on rows with the necessary data
    # Don't drop all rows if some features are missing - fill with defaults
    regime_df = regime_df.fillna(0)  # Fill any remaining NaN with 0

    logging.info(f"After fillna, regime_df shape: {regime_df.shape}")

    if len(regime_df) == 0:
        logging.error("No valid data for regime prediction")
        return

    logging.info(f"Predicting regimes for {len(regime_df)} data points...")

    # Predict regimes
    try:
        predicted_regimes_numeric = regime_model.predict(regime_df[regime_features])

        # Decode numeric predictions back to string labels if encoder is available
        if label_encoder is not None:
            predicted_regimes = label_encoder.inverse_transform(predicted_regimes_numeric)
        else:
            # Fallback: map numeric predictions to string labels
            regime_map = {0: "bear", 1: "bull", 2: "sideways"}
            predicted_regimes = [regime_map.get(int(p), "sideways") for p in predicted_regimes_numeric]

        historical_df["regime"] = predicted_regimes
        logging.info("✅ Successfully predicted market regimes")
    except Exception as e:
        logging.error(f"Failed to predict regimes: {e}")
        # Fallback: assign all data to sideways regime
        historical_df["regime"] = "sideways"
        logging.warning("Using fallback regime assignment (all sideways)")

    logging.info("Historical data tagged with market regimes.")
    logging.info(f"\n{historical_df['regime'].value_counts().to_string()}")

    # 4. Split data by symbol and regime, then train models
    logging.info("Training symbol-specific models for each regime...")
    trained_models = 0

    for symbol in historical_df["symbol"].unique():  # type: ignore
        symbol_data = historical_df[historical_df["symbol"] == symbol]
        logging.info(f"Processing {len(symbol_data)} samples for {symbol}")

        for regime_name in symbol_data["regime"].unique():  # type: ignore
            regime_symbol_data = symbol_data[symbol_data["regime"] == regime_name]
            if len(regime_symbol_data) >= 30:  # Minimum samples for training
                train_and_save_model(regime_symbol_data, regime_name, symbol, model_dir)
                trained_models += 1

    logging.info(f"✅ Training complete! Created {trained_models} symbol-specific models")

    # Create a summary of available models
    model_files = [f for f in os.listdir(model_dir) if f.startswith("model_") and f.endswith(".pkl")]
    logging.info(f"Available models: {len(model_files)}")
    for model_file in sorted(model_files):
        model_name = model_file.replace("model_", "").replace(".pkl", "")
        logging.info(f"  📊 {model_name}")


if __name__ == "__main__":
    main()
