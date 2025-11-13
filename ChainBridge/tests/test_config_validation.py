"""Test configuration validation."""

import os
import yaml
from typing import Dict, Any


def load_config(path: str) -> Dict[str, Any]:
    """Load and validate configuration file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")

    if not isinstance(config, dict):
        raise TypeError("Config must be a dictionary")

    return config


def validate_config(config: Dict[str, Any]) -> None:
    """Validate configuration structure and values."""
    # Required top-level keys
    required_keys = ["exchange", "symbols", "poll_seconds", "initial_capital"]

    for key in required_keys:
        if key not in config:
            raise KeyError(f"Missing required config key: {key}")

    # Validate exchange
    if not isinstance(config["exchange"], str):
        raise TypeError("Exchange must be a string")
    if config["exchange"].lower() not in ["kraken", "coinbase", "binance", "bybit"]:
        raise ValueError("Unsupported exchange")

    # Validate symbols
    if not isinstance(config["symbols"], list):
        raise TypeError("Symbols must be a list")
    for symbol in config["symbols"]:
        if not isinstance(symbol, str):
            raise TypeError("Symbol must be a string")
        if "/" not in symbol:
            raise ValueError(f"Invalid symbol format: {symbol}")

    # Validate numeric values
    if not isinstance(config["poll_seconds"], (int, float)):
        raise TypeError("poll_seconds must be numeric")
    if config["poll_seconds"] < 1:
        raise ValueError("poll_seconds must be positive")

    if not isinstance(config["initial_capital"], (int, float)):
        raise TypeError("initial_capital must be numeric")
    if config["initial_capital"] <= 0:
        raise ValueError("initial_capital must be positive")


def test_config_loading() -> None:
    """Test configuration file loading."""
    config_paths = ["config.yaml", "config/config.yaml"]
    loaded = False

    for path in config_paths:
        if os.path.exists(path):
            config = load_config(path)
            validate_config(config)
            loaded = True
            break

    assert loaded, "No valid config file found"


def test_env_substitution() -> None:
    """Test environment variable substitution."""
    # Set test environment variables
    os.environ["TEST_API_KEY"] = "test_key"
    os.environ["TEST_API_SECRET"] = "test_secret"

    test_config = """
    api:
      key: ${TEST_API_KEY}
      secret: ${TEST_API_SECRET}
    """

    test_path = os.path.join(os.path.dirname(__file__), "test_config.yaml")

    try:
        # Write test config
        with open(test_path, "w") as f:
            f.write(test_config)

        config = load_config(test_path)
        assert config["api"]["key"] == "test_key"
        assert config["api"]["secret"] == "test_secret"
    finally:
        # Cleanup
        if os.path.exists(test_path):
            os.remove(test_path)


def test_market_validation() -> None:
    """Test market configuration validation."""
    config = load_config("config.yaml")

    # Validate trading pairs
    for symbol in config["symbols"]:
        base, quote = symbol.split("/")
        assert base.isalpha(), f"Invalid base currency: {base}"
        assert quote.isalpha(), f"Invalid quote currency: {quote}"

    # Validate risk parameters
    if "risk" in config:
        risk = config["risk"]
        if "max_risk_per_trade" in risk:
            assert 0 < risk["max_risk_per_trade"] <= 1, "Invalid risk per trade"
        if "stop_loss_pct" in risk:
            assert 0 < risk["stop_loss_pct"] <= 100, "Invalid stop loss"
        if "take_profit_pct" in risk:
            assert 0 < risk["take_profit_pct"] <= 1000, "Invalid take profit"
