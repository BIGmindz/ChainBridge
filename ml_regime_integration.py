#!/usr/bin/env python3
"""
ML Regime Detection Integration for Benson Bot
Integrates market regime detection with the main trading bot
"""

import os
import sys
import logging
from datetime import datetime
import yaml

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))  # type: ignore

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("logs/ml_integration.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class MLRegimeIntegration:
    """
    Integrates ML regime detection with Benson Bot trading decisions
    """

    def __init__(self, config_path="config/config.yaml"):
        self.config_path = config_path
        self.regime_configs = {
            "bull": "config/regime_bull.yaml",
            "bear": "config/regime_bear.yaml",
            "sideways": "config/regime_sideways.yaml",
        }
        self.current_regime = None
        self.last_regime_check = None

        # Load base configuration
        self.base_config = self._load_config(config_path)

    def _load_config(self, config_path):
        """Load YAML configuration"""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config {config_path}: {e}")
            return {}

    def detect_current_regime(self):
        """Detect current market regime using ML model"""
        try:
            from market_regime_controller import detect_market_regime

            # Get current market features
            features = self._get_current_market_features()

            if features is None:
                logger.warning("Could not get current market features, using fallback")
                return self._fallback_regime_detection()

            # Detect regime
            regime = detect_market_regime(features)

            if regime:
                self.current_regime = regime
                self.last_regime_check = datetime.now()
                logger.info(f"📊 Detected market regime: {regime}")
                return regime
            else:
                logger.warning("ML regime detection failed, using fallback")
                return self._fallback_regime_detection()

        except Exception as e:
            logger.error(f"Error detecting regime: {e}")
            return self._fallback_regime_detection()

    def _get_current_market_features(self):
        """Get current market features for regime detection"""
        try:
            from market_regime_data_collector import MarketRegimeDataCollector

            collector = MarketRegimeDataCollector()
            # Get recent data for feature calculation
            features = collector.get_current_features()

            return features

        except Exception as e:
            logger.error(f"Error getting market features: {e}")
            return None

    def _fallback_regime_detection(self):
        """Fallback regime detection using simple rules"""
        try:
            # Simple fallback: check recent price action
            # This is a basic implementation - could be enhanced
            logger.info("Using fallback regime detection")

            # For now, default to sideways regime as safest option
            regime = "sideways"
            self.current_regime = regime
            return regime

        except Exception as e:
            logger.error(f"Fallback regime detection failed: {e}")
            return "sideways"  # Ultimate fallback

    def get_adaptive_config(self, detected_regime=None):
        """Get configuration adapted for current market regime"""
        if detected_regime is None:
            detected_regime = self.detect_current_regime()

        # Load regime-specific configuration
        regime_config_path = self.regime_configs.get(detected_regime)

        if regime_config_path and os.path.exists(regime_config_path):
            regime_config = self._load_config(regime_config_path)

            # Merge with base config
            adaptive_config = self._merge_configs(self.base_config, regime_config)

            logger.info(f"✅ Loaded adaptive config for {detected_regime} regime")
            return adaptive_config
        else:
            logger.warning(f"No specific config for {detected_regime}, using base config")
            return self.base_config

    def _merge_configs(self, base_config, regime_config):
        """Merge base config with regime-specific overrides"""
        merged = base_config.copy()

        # Deep merge regime config into base config
        def deep_merge(base, update):
            for key, value in update.items():
                if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                    deep_merge(base[key], value)
                else:
                    base[key] = value

        deep_merge(merged, regime_config)
        return merged

    def should_recheck_regime(self):
        """Check if we should re-detect the market regime"""
        if self.last_regime_check is None:
            return True

        # Recheck every 4 hours
        time_since_check = (datetime.now() - self.last_regime_check).total_seconds()
        return time_since_check > 14400  # 4 hours in seconds

    def get_regime_status(self):
        """Get current regime detection status"""
        return {
            "current_regime": self.current_regime,
            "last_check": self.last_regime_check.isoformat() if self.last_regime_check else None,
            "should_recheck": self.should_recheck_regime(),
        }


def integrate_with_benson_bot():
    """Main integration function for Benson Bot"""
    logger.info("🚀 Starting ML Regime Integration with Benson Bot")

    integration = MLRegimeIntegration()

    try:
        # Detect current regime
        regime = integration.detect_current_regime()

        # Get adaptive configuration
        adaptive_config = integration.get_adaptive_config(regime)

        # Log integration status
        status = integration.get_regime_status()
        logger.info(f"📈 Integration Status: {status}")

        return {"regime": regime, "config": adaptive_config, "status": status}

    except Exception as e:
        logger.error(f"Integration failed: {e}")
        return None


def demo_integration():
    """Demo function to show integration working"""
    print("🔬 ML Regime Detection Integration Demo")
    print("=" * 50)

    integration = MLRegimeIntegration()

    # Detect regime
    regime = integration.detect_current_regime()
    print(f"📊 Detected Market Regime: {regime}")

    # Get adaptive config
    config = integration.get_adaptive_config(regime)
    print(f"⚙️  Adaptive Configuration Loaded: {len(config)} settings")

    # Show regime-specific settings
    if "rsi" in config:
        print(f"📈 RSI Buy Threshold: {config['rsi'].get('buy_threshold', 'default')}")
        print(f"📉 RSI Sell Threshold: {config['rsi'].get('sell_threshold', 'default')}")

    # Show status
    status = integration.get_regime_status()
    print(f"🔍 Last Regime Check: {status['last_check']}")
    print(f"🔄 Should Recheck: {status['should_recheck']}")

    print("\n✅ Integration Demo Complete")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo_integration()
    else:
        result = integrate_with_benson_bot()
        if result:
            print("✅ ML Integration Successful")
            print(f"Regime: {result['regime']}")
        else:
            print("❌ ML Integration Failed")
