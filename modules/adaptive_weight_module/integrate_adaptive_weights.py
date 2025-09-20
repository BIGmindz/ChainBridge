#!/usr/bin/env python3
"""
Adaptive Weight Integration

This script integrates the adaptive weight model with the multi-signal trading bot,
enabling automatic weight optimization based on market conditions and recent performance.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/adaptive_weight_integration.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("adaptive_weight_integration")

# Import required modules
from modules.adaptive_weight_module.adaptive_weight_model import (
    AdaptiveWeightModule,
)  # noqa: E402
from modules.adaptive_weight_module.market_regime_integrator import (
    MarketRegimeIntegrator,
)  # noqa: E402
from modules.adaptive_weight_module.signal_data_collector import (
    SignalDataCollector,
)  # noqa: E402


class AdaptiveWeightIntegrator:
    """
    Integrates the adaptive weight model with the multi-signal trading bot
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the integrator"""
        self.config = config or {}

        # Initialize components
        self.weight_model = AdaptiveWeightModule(self.config)
        self.regime_integrator = MarketRegimeIntegrator(self.config)
        self.data_collector = SignalDataCollector(self.config)

        # Data storage path
        self.data_dir = os.path.join(
            self.config.get("data_dir", "data"), "adaptive_weight_data"
        )
        os.makedirs(self.data_dir, exist_ok=True)

    def optimize_signal_weights(
        self, signal_data: Dict[str, Any], market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Optimize signal weights based on current market conditions

        Args:
            signal_data: Raw signal data from all modules
            market_data: Market data including price, volume, etc.

        Returns:
            Dictionary with optimized weights and metadata
        """
        try:
            # Process input data
            timestamp = datetime.now().isoformat()

            # Standardize signal data
            std_signals = self.data_collector.collect_signals(signal_data, timestamp)

            # Standardize market data
            std_market = self.data_collector.collect_market_data(market_data, timestamp)

            # Detect market regime
            regime_results = self.regime_integrator.detect_regime(market_data)

            # Get optimized weights from the model
            model_input = {
                "signals": std_signals,
                "market_data": std_market,
                "timestamp": timestamp,
            }

            optimized_weights = self.weight_model.process(model_input)

            # Save the results for future training
            self._save_optimization_results(
                std_signals, std_market, regime_results, optimized_weights
            )

            return optimized_weights

        except Exception as e:
            logger.error(f"Error in weight optimization: {str(e)}")
            # Return default weights on error
            return self._get_default_weights()

    def _save_optimization_results(
        self,
        signals: Dict[str, Any],
        market_data: Dict[str, Any],
        regime_data: Dict[str, Any],
        weights: Dict[str, Any],
    ) -> None:
        """Save optimization results for future training"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_weights.json"
        file_path = os.path.join(self.data_dir, filename)

        data = {
            "signal_data": signals,
            "market_data": market_data,
            "regime_data": regime_data,
            "optimized_weights": weights,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving optimization results: {str(e)}")

    def _get_default_weights(self) -> Dict[str, Any]:
        """Get default signal weights"""
        # Default equal weights for all layers
        layer_weights = {
            "LAYER_1_TECHNICAL": 1.0,
            "LAYER_2_LOGISTICS": 1.0,
            "LAYER_3_GLOBAL_MACRO": 1.0,
            "LAYER_4_ADOPTION": 1.0,
        }

        return {
            "optimized_weights": layer_weights,
            "market_regime": "UNKNOWN",
            "regime_confidence": 0.0,
            "timestamp": datetime.now().isoformat(),
            "status": "default_weights",
        }

    def update_performance_metrics(
        self, regime: str, metrics: Dict[str, float]
    ) -> None:
        """
        Update performance metrics for a specific market regime

        Args:
            regime: Market regime name
            metrics: Dictionary with performance metrics
        """
        self.regime_integrator.update_performance_metrics(regime, metrics)

    def get_current_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the current market regime

        Args:
            market_data: Market data dictionary

        Returns:
            Dictionary with regime information
        """
        return self.regime_integrator.detect_regime(market_data)


def integrate_with_multi_signal_bot():
    """Integrate adaptive weight model with the multi-signal bot"""
    logger.info("Integrating adaptive weight model with multi-signal bot")

    # Load configuration
    config_path = os.path.join("config", "adaptive_weight_config.json")
    config = {}

    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")

    # Create default configuration if not found
    if not config:
        config = {
            "data_dir": "data",
            "model_dir": "models",
            "logs_dir": "logs",
            "n_signals": 15,
            "n_regimes": 4,
            "lookback_days": 7,
            "retrain_frequency_hours": 24,
        }

        # Save default configuration
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

    # Create integrator
    integrator = AdaptiveWeightIntegrator(config)

    # Apply patches to multi_signal_bot.py
    _patch_multi_signal_bot()

    return integrator


def _patch_multi_signal_bot():
    """Apply patches to multi_signal_bot.py to use adaptive weights"""
    # Define the file path
    file_path = "multi_signal_bot.py"

    if not os.path.exists(file_path):
        logger.error(f"Cannot patch {file_path}: file not found")
        return

    try:
        # Read the current file
        with open(file_path, "r") as f:
            content = f.read()

        # Check if already patched
        if "from modules.adaptive_weight_module" in content:
            logger.info(f"{file_path} already patched for adaptive weights")
            return

        # Import statement to add
        import_statement = """
# Import adaptive weight module
from modules.adaptive_weight_module.adaptive_weight_model import AdaptiveWeightModule
from modules.adaptive_weight_module.market_regime_integrator import MarketRegimeIntegrator
"""

        # Find the right spot to insert imports (after existing imports)
        import_spot = content.find("\n\n", content.rfind("import "))
        if import_spot == -1:
            import_spot = content.find("\n\nclass")

        if import_spot != -1:
            new_content = (
                content[:import_spot] + import_statement + content[import_spot:]
            )

            # Add adaptive weight initialization to the __init__ method
            init_pattern = "def __init__(self, config=None):"
            init_code = """
        # Initialize adaptive weight module if enabled
        self.use_adaptive_weights = config.get("use_adaptive_weights", False)
        self.adaptive_weight_module = None
        
        if self.use_adaptive_weights:
            try:
                from modules.adaptive_weight_module.integrate_adaptive_weights import AdaptiveWeightIntegrator
                self.adaptive_weight_module = AdaptiveWeightIntegrator(config)
                self.logger.info("Adaptive weight module initialized successfully")
            except Exception as e:
                self.logger.error(f"Error initializing adaptive weight module: {str(e)}")
                self.use_adaptive_weights = False
"""

            # Find the end of the __init__ method
            init_end = new_content.find("\n    def", new_content.find(init_pattern))
            if init_end != -1:
                # Find the last line of the __init__ method
                last_line = new_content.rfind(
                    "\n        ", new_content.find(init_pattern), init_end
                )
                if last_line != -1:
                    new_content = (
                        new_content[:last_line] + init_code + new_content[last_line:]
                    )

            # Add adaptive weight logic to the decision making process
            decision_pattern = "def make_decision(self, signals):"
            weight_code = """
        # Apply adaptive weights if enabled
        if self.use_adaptive_weights and self.adaptive_weight_module:
            try:
                # Get market data
                market_data = self._get_market_data()
                
                # Get optimized weights
                weight_results = self.adaptive_weight_module.optimize_signal_weights(signals, market_data)
                
                # Apply weights to signal layers
                optimized_weights = weight_results.get("optimized_weights", {})
                market_regime = weight_results.get("market_regime", "UNKNOWN")
                regime_confidence = weight_results.get("regime_confidence", 0.0)
                
                self.logger.info(f"Using adaptive weights for market regime: {market_regime} (confidence: {regime_confidence:.2f})")
                
                for layer, weight in optimized_weights.items():
                    if layer in signal_weights:
                        signal_weights[layer] *= weight
                        self.logger.debug(f"Applied weight {weight:.2f} to {layer}")
                
                # Add regime information to the decision
                decision["market_regime"] = market_regime
                decision["regime_confidence"] = regime_confidence
                decision["adaptive_weights_applied"] = True
                
            except Exception as e:
                self.logger.error(f"Error applying adaptive weights: {str(e)}")
"""

            # Find where to insert the weight code
            signal_weights_line = new_content.find(
                "signal_weights = {", new_content.find(decision_pattern)
            )
            if signal_weights_line != -1:
                # Find the end of the signal_weights block
                weights_end = new_content.find(
                    "\n", new_content.find("}", signal_weights_line)
                )
                if weights_end != -1:
                    new_content = (
                        new_content[: weights_end + 1]
                        + weight_code
                        + new_content[weights_end + 1 :]
                    )

            # Add method to get market data
            market_data_method = """
    def _get_market_data(self):
        \"\"\"Get market data for regime detection and weight optimization\"\"\"
        try:
            # Get price history (last 30 days if available)
            price_history = self.price_history[-30:] if hasattr(self, 'price_history') and len(self.price_history) > 0 else []
            
            # Get volume history if available
            volume_history = self.volume_history[-30:] if hasattr(self, 'volume_history') and len(self.volume_history) > 0 else []
            
            # Calculate volatility features
            volatility_features = self._calculate_volatility_features(price_history)
            
            # Create market data dictionary
            market_data = {
                "price_history": price_history,
                "volume_history": volume_history,
                "current_price": price_history[-1] if price_history else 0,
                "current_volume": volume_history[-1] if volume_history else 0
            }
            
            # Add volatility features
            market_data.update(volatility_features)
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Error getting market data: {str(e)}")
            return {"price_history": [], "volume_history": []}
    
    def _calculate_volatility_features(self, price_history):
        \"\"\"Calculate volatility features from price history\"\"\"
        import numpy as np
        
        if not price_history or len(price_history) < 30:
            return {
                "volatility_1d": 0.0,
                "volatility_7d": 0.0,
                "volatility_30d": 0.0,
                "trend_1d": 0.0,
                "trend_7d": 0.0,
                "trend_30d": 0.0
            }
        
        # Calculate returns
        prices = np.array(price_history)
        returns = np.diff(prices) / prices[:-1]
        
        # Calculate volatility features
        vol_1d = np.std(returns[-1:]) * np.sqrt(365) if len(returns) >= 1 else 0
        vol_7d = np.std(returns[-7:]) * np.sqrt(365) if len(returns) >= 7 else 0
        vol_30d = np.std(returns) * np.sqrt(365)
        
        # Calculate trend features
        trend_1d = np.mean(returns[-1:]) * 365 if len(returns) >= 1 else 0
        trend_7d = np.mean(returns[-7:]) * 365 if len(returns) >= 7 else 0
        trend_30d = np.mean(returns) * 365
        
        return {
            "volatility_1d": float(vol_1d),
            "volatility_7d": float(vol_7d),
            "volatility_30d": float(vol_30d),
            "trend_1d": float(trend_1d),
            "trend_7d": float(trend_7d),
            "trend_30d": float(trend_30d)
        }
"""

            # Add market data method to the class
            last_method_end = new_content.rfind("\n\n    def ")
            last_method_block_end = new_content.find("\n\n", last_method_end + 10)
            if last_method_block_end != -1:
                new_content = (
                    new_content[:last_method_block_end]
                    + market_data_method
                    + new_content[last_method_block_end:]
                )

            # Write the patched file
            with open(file_path, "w") as f:
                f.write(new_content)

            logger.info(f"Successfully patched {file_path} for adaptive weights")

        else:
            logger.error(f"Could not find suitable location to patch {file_path}")

    except Exception as e:
        logger.error(f"Error patching {file_path}: {str(e)}")


if __name__ == "__main__":
    # Run integration
    integrator = integrate_with_multi_signal_bot()

    logger.info("Adaptive weight model integration complete")
    print("Adaptive weight model has been integrated with the multi-signal bot")
    print(
        "To use adaptive weights, set 'use_adaptive_weights': true in your configuration"
    )
