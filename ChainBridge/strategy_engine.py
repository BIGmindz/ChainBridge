import os
import sys
import yaml
import subprocess
import logging
import joblib
import argparse

# --- Add project root to system path for local imports ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)


def detect_market_regime():
    """
    Loads and runs the market regime detection model.
    """
    logging.info("Analyzing current market conditions to detect regime...")
    try:
        # Load the regime detection model
        model_dict = joblib.load("ml_models/regime_detection_model.pkl")
        model = model_dict["model"]
        label_encoder = model_dict.get("label_encoder")

        # Get current market features (simplified for now)
        # In production, this would collect real-time market data
        current_features = {
            "rsi_14": 55,  # Example values
            "macd": 0,
            "macd_signal": 0,
            "macd_hist": 0,
            "bb_upper": 50000,
            "bb_middle": 45000,
            "bb_lower": 40000,
            "bb_width": 0.05,
            "bb_position": 0.2,
            "volume_ratio": 1.0,
            "price_change_1h": 0.01,
            "price_change_24h": 0.02,
            "volatility_24h": 0.03,
            "trend_strength": 0.6,
        }

        # Convert to DataFrame for prediction
        import pandas as pd

        features_df = pd.DataFrame([current_features])

        # Make prediction
        regime_numeric = model.predict(features_df)[0]

        # Decode to string label
        if label_encoder is not None:
            detected_regime = label_encoder.inverse_transform([regime_numeric])[0]
        else:
            regime_map = {0: "bear", 1: "bull", 2: "sideways"}
            detected_regime = regime_map.get(int(regime_numeric), "sideways")

        logging.info(f"✅ Market Regime Detected: '{detected_regime.upper()}'")
        return detected_regime
    except Exception as e:
        logging.error(f"Failed to detect market regime: {e}")
        return "sideways"  # Default to a conservative regime on error


def get_strategy_for_regime_and_symbol(regime: str, symbol: str) -> dict:
    """
    Selects the appropriate model and configuration for the detected regime and symbol.
    Now supports ensemble strategies that combine multiple models.
    """
    logging.info(
        f"Selecting strategy for '{regime.upper()}' regime and '{symbol}' symbol..."
    )

    # Check if ensemble_voting strategy exists and is configured
    ensemble_config_path = "strategies/ensemble_voting/config.yaml"
    if os.path.exists(ensemble_config_path):
        try:
            with open(ensemble_config_path, "r") as f:
                ensemble_config = yaml.safe_load(f)

            if ensemble_config.get("ensemble"):
                logging.info(
                    "🎯 Ensemble strategy detected! Loading multiple models for voting..."
                )
                return prepare_ensemble_strategy(ensemble_config, regime, symbol)
        except Exception as e:
            logging.warning(f"Failed to load ensemble config: {e}")

    # Standard strategy selection (existing logic)
    return get_standard_strategy(regime, symbol)


def prepare_ensemble_strategy(ensemble_config: dict, regime: str, symbol: str) -> dict:
    """
    Prepares an ensemble strategy by loading multiple models for voting.
    """
    ensemble_info = ensemble_config["ensemble"]
    models_to_include = ensemble_info["models_to_include"]
    voting_mechanism = ensemble_info["voting_mechanism"]

    logging.info("📊 Ensemble Configuration:")
    logging.info(f"   Models to include: {models_to_include}")
    logging.info(f"   Voting mechanism: {voting_mechanism}")

    # Collect model paths for each strategy in the ensemble
    model_paths = []
    scaler_paths = []

    for strategy_name in models_to_include:
        strategy_dir = f"strategies/{strategy_name}"

        # Check if strategy has trained models
        model_path = os.path.join(strategy_dir, "model.pkl")
        scaler_path = os.path.join(strategy_dir, "scaler.pkl")

        if os.path.exists(model_path):
            model_paths.append(model_path)  # type: ignore
            scaler_paths.append(scaler_path)  # type: ignore
            logging.info(f"   ✅ Found model: {strategy_name}")
        else:
            logging.warning(f"   ⚠️  Model not found for: {strategy_name}")

    if not model_paths:
        logging.error(
            "❌ No models found for ensemble! Falling back to standard strategy."
        )
        return get_standard_strategy(regime, symbol)

    # Return ensemble configuration
    return {
        "config_path": "strategies/ensemble_voting/config.yaml",
        "model_paths": model_paths,  # List of model paths for ensemble
        "scaler_paths": scaler_paths,  # List of scaler paths for ensemble
        "voting_mechanism": voting_mechanism,
        "is_ensemble": True,
        "description": f"Ensemble voting strategy with {len(model_paths)} models ({voting_mechanism}).",
    }


def get_standard_strategy(regime: str, symbol: str) -> dict:
    """
    Original strategy selection logic (extracted for clarity).
    """
    # Standardize paths
    model_dir = "ml_models/"

    # Try symbol-specific model first
    symbol_clean = symbol.replace("/", "_")  # Convert BTC/USD to BTC_USD for filename
    symbol_model_path = os.path.join(model_dir, f"model_{symbol_clean}_{regime}.pkl")
    symbol_scaler_path = os.path.join(model_dir, f"scaler_{symbol_clean}_{regime}.pkl")

    if os.path.exists(symbol_model_path):
        config_file = f"config/regime_{regime}.yaml"
        return {
            "config_path": config_file,
            "model_path": symbol_model_path,
            "scaler_path": symbol_scaler_path,
            "is_ensemble": False,
            "description": f"Symbol-specific {regime} strategy for {symbol}.",
        }

    # Fallback to general regime model
    general_model_path = os.path.join(model_dir, f"model_{regime}.pkl")
    general_scaler_path = os.path.join(model_dir, f"scaler_{regime}.pkl")

    if os.path.exists(general_model_path):
        config_file = f"config/regime_{regime}.yaml"
        return {
            "config_path": config_file,
            "model_path": general_model_path,
            "scaler_path": general_scaler_path,
            "is_ensemble": False,
            "description": f"General {regime} strategy (fallback for {symbol}).",
        }

    # Final fallback to sideways
    return {
        "config_path": "config/regime_sideways.yaml",
        "model_path": os.path.join(model_dir, "model_sideways.pkl"),
        "scaler_path": os.path.join(model_dir, "scaler_sideways.pkl"),
        "is_ensemble": False,
        "description": f"Conservative sideways strategy (fallback for {symbol}).",
    }


def main():
    """
    The master controller for the trading bot.
    """
    parser = argparse.ArgumentParser(description="Trading Strategy Engine")
    parser.add_argument(
        "--symbol",
        type=str,
        default="BTC/USD",
        help="Trading symbol to use for strategy selection (default: BTC/USD)",
    )
    args = parser.parse_args()

    regime = detect_market_regime()
    strategy = get_strategy_for_regime_and_symbol(regime, args.symbol)

    logging.info(f"Strategy Selected: {strategy['description']}")

    # Check if the specialized model exists, otherwise use the general model
    if not os.path.exists(strategy["model_path"]):
        logging.warning(f"Specialized model not found: {strategy['model_path']}")
        logging.info("Falling back to general regime detection model")
        strategy["model_path"] = os.path.join("ml_models", "regime_detection_model.pkl")
        strategy["scaler_path"] = None  # General model doesn't have a scaler

    # Set environment variables to pass the selected strategy to the main bot
    env = os.environ.copy()
    env["BENSON_CONFIG"] = strategy["config_path"]
    env["BENSON_SYMBOL"] = args.symbol

    if strategy.get("is_ensemble"):
        # For ensemble strategies, pass multiple model paths
        env["BENSON_ENSEMBLE_MODELS"] = ",".join(strategy["model_paths"])
        env["BENSON_ENSEMBLE_SCALERS"] = ",".join(strategy["scaler_paths"])
        env["BENSON_VOTING_MECHANISM"] = strategy["voting_mechanism"]
        env["BENSON_IS_ENSEMBLE"] = "true"
        logging.info("🎯 Ensemble strategy configured with multiple models")
    else:
        # For single model strategies (existing logic)
        env["BENSON_MODEL"] = strategy["model_path"]
        if strategy.get("scaler_path"):
            env["BENSON_SCALER"] = strategy["scaler_path"]
        env["BENSON_IS_ENSEMBLE"] = "false"

    # Try different possible main bot scripts
    possible_scripts = [
        "apps/hypertrader/kraken_hypertrade_test.py",
        "multi_signal_bot.py",
        "benson_rsi_bot.py",
    ]

    main_bot_script = None
    for script in possible_scripts:
        if os.path.exists(script):
            main_bot_script = script
            break

    if main_bot_script:
        logging.info("🚀 Launching main trading bot with selected strategy...")
        logging.info(f"   Symbol: {args.symbol}")
        logging.info(f"   Regime: {regime.upper()}")
        logging.info(f"   Config: {strategy['config_path']}")
        logging.info(f"   Model: {strategy['model_path']}")

        try:
            subprocess.run([sys.executable, main_bot_script], check=True, env=env)
        except FileNotFoundError:
            logging.error(
                f"FATAL: The main trading script was not found at '{main_bot_script}'."
            )
        except subprocess.CalledProcessError as e:
            logging.error(
                f"The trading bot exited with an error (code {e.returncode})."
            )
    else:
        logging.error("No suitable trading bot script found!")
        logging.info("Available scripts to check:")
        for script in possible_scripts:
            exists = "✅" if os.path.exists(script) else "❌"
            logging.info(f"   {exists} {script}")


if __name__ == "__main__":
    main()
