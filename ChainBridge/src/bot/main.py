#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   ENTERPRISE TRADING BOT - CANONICAL ENTRY POINT                     ║
║   Multiple-Signal Decision Bot - Production Grade v2.0               ║
║                                                                       ║
║   This is the ONLY entry point for the trading system.              ║
║   All other bot files are DEPRECATED.                               ║
║                                                                       ║
║   Features:                                                          ║
║   - Secrets management (Vault/AWS/Env)                              ║
║   - Circuit breaker & resilient data fetching                       ║
║   - Structured logging & Prometheus metrics                         ║
║   - Graceful degradation for all external APIs                      ║
║   - Enterprise-grade error handling                                 ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝

Usage:
    python src/bot/main.py --mode live --confirm         # Live trading
    python src/bot/main.py --mode paper --once           # Single paper cycle
    python src/bot/main.py --preflight                   # Validate setup

Environment Variables:
    VAULT_ADDR              HashiCorp Vault address
    VAULT_TOKEN             Vault authentication token
    AWS_REGION              AWS region for Secrets Manager
    METRICS_PORT            Prometheus metrics port (default: 9090)
"""

from __future__ import annotations

import argparse
import sys
import signal
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# Ensure imports resolve
ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

# Load environment first
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Enterprise imports
from src.bot.core.secrets_manager import get_secrets_manager
from src.bot.core.observability import init_observability
from src.bot.core.resilient_data_fetcher import get_resilient_fetcher

# Legacy bot import (will be refactored)
try:
    from live_trading_bot import LiveTradingBot
except ImportError:
    # Fallback to relative import
    import os

    os.chdir(ROOT_DIR)
    from live_trading_bot import LiveTradingBot


class EnterpriseBot:
    """
    Enterprise-grade bot orchestrator

    Responsibilities:
    - Lifecycle management
    - Secrets rotation monitoring
    - Health checks
    - Metrics publication
    - Graceful shutdown
    """

    def __init__(self, mode: str, confirm_live: bool = False, once: bool = False, min_confidence: float = 0.25, metrics_port: int = 9090):
        self.mode = mode
        self.confirm_live = confirm_live
        self.once = once
        self.min_confidence = min_confidence
        self.should_stop = False

        # Initialize enterprise components
        self.secrets = get_secrets_manager()
        self.observability = init_observability(service_name="trading-bot", metrics_port=metrics_port, enable_metrics=True)
        self.data_fetcher = get_resilient_fetcher()

        # Trading bot instance
        self.bot: Optional[LiveTradingBot] = None

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._print_banner()

    def _print_banner(self):
        """Print enterprise banner"""
        mode_indicator = "📝 PAPER TRADING" if self.mode == "paper" else "⚠️  LIVE TRADING"
        print(
            f"""
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   Enterprise Trading Bot v2.0                                        ║
║   Mode: {mode_indicator:60s} ║
║   Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'):58s} ║
║                                                                       ║
║   🔒 Secrets: {self.secrets.provider.__class__.__name__:52s} ║
║   📊 Metrics: http://localhost:{self.observability.metrics.enabled and '9090' or 'disabled':46s} ║
║   🛡️  Circuit Breakers: Active                                       ║
║   📈 Observability: Enabled                                          ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
"""
        )

        if self.mode == "live":
            print("⚠️  WARNING: LIVE TRADING MODE - REAL MONEY AT RISK")
            print("⚠️  Ensure you have reviewed configuration and tested in paper mode")
            print("⚠️  Press Ctrl+C to stop at any time\n")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.observability.logger.warning(f"Received signal {signum}, initiating graceful shutdown")
        print(f"\n🛑 Received signal {signum}. Shutting down gracefully...")
        self.should_stop = True

    def validate_environment(self) -> bool:
        """Validate environment and dependencies"""
        print("🔍 Validating environment...")

        with self.observability.measure_operation("environment_validation"):
            # Check Python version
            if sys.version_info < (3, 9):
                self.observability.logger.error(f"Python 3.9+ required, got {sys.version}")
                return False
            print(f"✅ Python version: {sys.version.split()[0]}")

            # Check dependencies
            required_modules = ["yaml", "ccxt", "pandas", "numpy", "requests"]
            for module in required_modules:
                try:
                    __import__(module)
                    print(f"✅ {module}")
                except ImportError:
                    print(f"❌ {module} not installed")
                    return False

            # Check secrets availability
            try:
                self.secrets.get_exchange_credentials("kraken")
                print("✅ Exchange credentials: Available")
            except Exception as e:
                print(f"❌ Exchange credentials: {e}")
                return False

            # Health check data sources
            print("\n🔍 Checking data source health...")
            self._check_data_sources()

            return True

    def _check_data_sources(self):
        """Check health of external data sources"""
        sources = [
            ("Fear & Greed Index", "https://api.alternative.me/fng/"),
            ("Reddit Sentiment", "https://www.reddit.com/r/cryptocurrency/hot.json"),
        ]

        for source_name, url in sources:
            try:
                _, status = self.data_fetcher.fetch_with_resilience(url=url, fallback_value={"status": "fallback"}, cache_ttl=60, timeout=5)

                status_emoji = {"live": "🟢", "cache": "🟡", "stale_cache": "🟠", "fallback": "🔴"}.get(status, "⚪")

                print(f"  {status_emoji} {source_name}: {status}")
                self.observability.metrics.update_data_source_status(source_name, status)

            except Exception as e:
                print(f"  🔴 {source_name}: ERROR - {e}")
                self.observability.metrics.update_data_source_status(source_name, "down")

    def check_secrets_rotation(self):
        """Check if any secrets need rotation"""
        print("\n🔑 Checking secrets rotation status...")

        secrets_to_check = ["API_KEY", "API_SECRET", "KRAKEN_API_KEY", "KRAKEN_SECRET"]

        for secret_key in secrets_to_check:
            if self.secrets.check_rotation_needed(secret_key, max_age_days=30):
                self.observability.logger.warning(f"Secret rotation needed: {secret_key}", secret=secret_key)
                print(f"  ⚠️  {secret_key}: Rotation recommended (>30 days)")
            else:
                metadata = self.secrets.get_secret_metadata(secret_key)
                if metadata:
                    print(f"  ✅ {secret_key}: OK (accessed {metadata.access_count} times)")

    def initialize_bot(self) -> bool:
        """Initialize trading bot with enterprise configuration"""
        print("\n🚀 Initializing trading bot...")

        try:
            with self.observability.measure_operation("bot_initialization"):
                # Verify exchange credentials are available via secrets manager
                try:
                    self.secrets.get_exchange_credentials("kraken")
                    print("✅ Exchange credentials validated")
                except Exception as e:
                    print(f"⚠️  Credential validation: {e}")

                # Initialize bot (uses environment variables internally)
                # LiveTradingBot loads config from yaml and env automatically
                import os

                os.environ["PAPER"] = "false" if self.mode == "live" else "true"

                self.bot = LiveTradingBot(config=None)

                print("✅ Bot initialized successfully")
                return True

        except Exception as e:
            self.observability.logger.error(f"Bot initialization failed: {e}")
            print(f"❌ Bot initialization failed: {e}")
            return False

    def run_trading_cycle(self) -> bool:
        """Execute single trading cycle"""
        if not self.bot:
            return False

        try:
            with self.observability.measure_operation("trading_cycle"):
                # Run bot cycle (use run_trading_cycle method)
                self.bot.run_trading_cycle()

                # Publish portfolio metrics
                status = self.bot.budget_manager.get_portfolio_status()
                self.observability.log_portfolio_snapshot(
                    total_value=status.get("total_value_usd", 0),
                    realized_pnl=status.get("realized_pnl", 0),
                    unrealized_pnl=status.get("unrealized_pnl", 0),
                    active_positions=status.get("open_positions", 0),
                    capital_utilization=status.get("capital_deployed_pct", 0),
                )

                return True

        except Exception as e:
            self.observability.logger.error(f"Trading cycle failed: {e}")
            print(f"❌ Trading cycle error: {e}")
            return False

    def run(self) -> int:
        """Main execution loop"""
        # Validate environment
        if not self.validate_environment():
            return 1

        # Check secrets rotation
        self.check_secrets_rotation()

        # Require confirmation for live mode
        if self.mode == "live" and not self.confirm_live:
            print("\n❌ Live mode requires --confirm flag")
            return 2

        # Initialize bot
        if not self.initialize_bot():
            return 3

        # Run once or continuous
        if self.once:
            print("\n▶️  Running single trading cycle...")
            success = self.run_trading_cycle()
            return 0 if success else 4
        else:
            print("\n▶️  Starting continuous trading loop...")
            print("   Press Ctrl+C to stop\n")

            cycle_count = 0
            while not self.should_stop:
                try:
                    cycle_count += 1
                    print(f"\n{'='*70}")
                    print(f"Trading Cycle #{cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"{'='*70}")

                    self.run_trading_cycle()

                    if not self.should_stop:
                        print("\n⏳ Waiting 60 seconds before next cycle...")
                        time.sleep(60)

                except KeyboardInterrupt:
                    print("\n\n🛑 Keyboard interrupt detected")
                    break
                except Exception as e:
                    self.observability.logger.error(f"Unexpected error in main loop: {e}")
                    print(f"\n❌ Unexpected error: {e}")
                    print("⏳ Waiting 60 seconds before retry...")
                    time.sleep(60)

            print("\n✅ Bot stopped gracefully")
            return 0


def main() -> int:
    """Entry point"""
    parser = argparse.ArgumentParser(description="Enterprise Trading Bot v2.0", formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument("--mode", choices=["live", "paper"], default="paper", help="Trading mode (default: paper)")

    parser.add_argument(
        "--confirm", "--confirm-live", action="store_true", dest="confirm_live", help="Confirm live trading mode (required for --mode live)"
    )

    parser.add_argument("--once", action="store_true", help="Run single cycle then exit")

    parser.add_argument("--min-confidence", type=float, default=0.25, help="Minimum signal confidence to execute trades (default: 0.25)")

    parser.add_argument("--metrics-port", type=int, default=9090, help="Prometheus metrics port (default: 9090)")

    parser.add_argument("--preflight", action="store_true", help="Run preflight checks only (no trading)")

    args = parser.parse_args()

    # Create enterprise bot
    bot = EnterpriseBot(
        mode=args.mode, confirm_live=args.confirm_live, once=args.once, min_confidence=args.min_confidence, metrics_port=args.metrics_port
    )

    # Run preflight checks only
    if args.preflight:
        print("\n🔍 Running preflight checks...\n")
        success = bot.validate_environment()
        bot.check_secrets_rotation()
        return 0 if success else 1

    # Run bot
    return bot.run()


if __name__ == "__main__":
    sys.exit(main())
