#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   CANONICAL TRADING BOT ENTRY POINT                                  ║
║   Multiple-Signal Decision Bot - Enterprise Edition                  ║
║                                                                       ║
║   This is the ONLY entry point for the trading system.              ║
║   All other bot files are DEPRECATED and will be removed.           ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝

Usage:
    python main.py --mode paper --once          # Single cycle, paper trading
    python main.py --mode live                  # Continuous live trading
    python main.py --mode paper --symbols BTC/USD,ETH/USD
    python main.py --preflight                  # Validate setup without trading

Environment Variables:
    API_KEY / KRAKEN_API_KEY        Exchange API key
    API_SECRET / KRAKEN_SECRET      Exchange API secret
    CONFIG_PATH                     Path to config.yaml (default: config/config.yaml)

Documentation:
    - Architecture: docs/ARCHITECTURE.md
    - Operations: docs/RUNBOOK.md
    - Configuration: docs/CONFIGURATION.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import signal
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure imports resolve correctly
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import the complete multi-signal bot implementation
# This is the canonical implementation with all features
from live_trading_bot import LiveTradingBot as TradingEngine, load_bot_config, preflight_check

CANONICAL_RSI_BUY = 35
CANONICAL_RSI_SELL = 64

METRICS_PATH = Path("runtime_metrics.json")


class BotOrchestrator:
    """Enterprise orchestrator: lifecycle, safety, metrics, overrides."""

    TRADE_LOG_PATH = Path("logs/trades.jsonl")

    def __init__(
        self,
        mode: str,
        config_path: Optional[str] = None,
        confirm_live: bool = False,
        force_execution: bool = False,
        min_confidence: float = 0.0,
        min_trade_usd: float = 0.0,
    ):
        self.mode = mode
        self.config_path = config_path
        self.confirm_live = confirm_live
        self.should_stop = False
        self.engine: Optional[TradingEngine] = None
        self.force_execution = force_execution
        self.min_confidence = float(min_confidence or 0.0)
        self.min_trade_usd = float(min_trade_usd or 0.0)

        # Configure paper mode environment variable
        os.environ["PAPER"] = "true" if mode == "paper" else "false"
        try:
            from src.trading_mode import MODE  # type: ignore
            MODE.refresh_mode()
        except Exception:
            pass

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self._print_banner()
    
    def _print_banner(self):
        mode_indicator = "📝 PAPER" if self.mode == "paper" else "⚠️  LIVE"
        print(f"""
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   Multiple-Signal Decision Bot - Enterprise Edition                  ║
║   Canonical Entry Point v2.0                                         ║
║                                                                       ║
║   Mode: {mode_indicator:60s} ║
║   Config: {str(self.config_path or 'config/config.yaml'):57s} ║
║   Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'):58s} ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
        """)
        if self.mode == "live":
            print("⚠️  WARNING: LIVE TRADING MODE - REAL MONEY AT RISK")
            if not self._live_confirmation_granted():
                print("❌ Live mode launch blocked: confirmation guard not satisfied.")
                print("   Re-run with --confirm-live OR set CONFIRM_LIVE=YES to proceed.")
                sys.exit(2)
            print("✅ Live mode confirmation acknowledged (explicit flag or env var).")
            print("⚠️  Ensure you have reviewed configuration and tested in paper mode")
            print("⚠️  Press Ctrl+C to stop at any time\n")
        print(f"📏 Canonical RSI thresholds: BUY={CANONICAL_RSI_BUY} SELL={CANONICAL_RSI_SELL}")

    def _live_confirmation_granted(self) -> bool:
        return self.confirm_live or os.getenv("CONFIRM_LIVE", "").upper() in {"YES", "Y", "TRUE", "1"}
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print(f"\n🛑 Received signal {signum}. Initiating graceful shutdown...")
        self.should_stop = True
    
    def validate_environment(self) -> bool:
        """
        Validate that the environment is properly configured.
        
        Returns:
            True if validation passes, False otherwise
        """
        print("🔍 Validating environment...")
        
        # Check Python version
        if sys.version_info < (3, 9):
            print(f"❌ Python 3.9+ required. Current: {sys.version}")
            return False
        print(f"✅ Python version: {sys.version.split()[0]}")
        
        # Check required dependencies
        required_modules = ['yaml', 'ccxt', 'pandas', 'numpy']
        missing = []
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing.append(module)
        
        if missing:
            print(f"❌ Missing required modules: {', '.join(missing)}")
            print("   Install with: pip install -r requirements.txt")
            return False
        print("✅ All required modules available")
        
        # Check API credentials for live mode
        if self.mode == "live":
            key = os.getenv("API_KEY") or os.getenv("KRAKEN_API_KEY")
            secret = os.getenv("API_SECRET") or os.getenv("KRAKEN_SECRET")
            
            if not key or not secret:
                print("❌ Live mode requires API credentials")
                print("   Set API_KEY and API_SECRET environment variables")
                return False
            print("✅ API credentials detected")
        
        # Check config file exists
        config_paths = [
            self.config_path,
            "config/config.yaml",
            "config.yaml"
        ]
        config_found = False
        for path in config_paths:
            if path and Path(path).exists():
                print(f"✅ Configuration file: {path}")
                config_found = True
                break
        
        if not config_found:
            print("⚠️  No configuration file found, will use defaults")

        print("✅ Environment validation complete\n")
        return True
    
    def run_preflight(self) -> bool:
        """
        Run preflight checks without starting the bot.
        
        Returns:
            True if all checks pass, False otherwise
        """
        print("🚀 Running preflight checks...\n")
        
        if not self.validate_environment():
            return False
        
        try:
            # Run the canonical preflight check
            preflight_check()
            print("✅ Preflight checks passed\n")
            return True
        except Exception as e:
            print(f"❌ Preflight failed: {e}\n")
            return False
    
    def _emit_metrics(self, cycle: int, mode: str, status: str) -> None:
        snapshot = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "cycle": cycle,
            "symbols": getattr(self.engine, "symbols", []),
            "poll_seconds": getattr(self.engine, "poll_seconds", None),
            "capital_available": getattr(getattr(self.engine, "budget_manager", {}), "available_capital", None),
            "capital_total": getattr(getattr(self.engine, "budget_manager", {}), "current_capital", None),
            "status": status,
            "rsi_buy": CANONICAL_RSI_BUY,
            "rsi_sell": CANONICAL_RSI_SELL,
        }
        try:
            existing: List[Dict[str, Any]] = []
            if METRICS_PATH.exists():
                with METRICS_PATH.open("r", encoding="utf-8") as fh:
                    try:
                        existing = json.load(fh) or []
                    except json.JSONDecodeError:
                        existing = []
            existing.append(snapshot)
            with METRICS_PATH.open("w", encoding="utf-8") as fh:
                json.dump(existing[-500:], fh, indent=2)
        except Exception as exc:
            print(f"⚠️  Failed to write metrics stub: {exc}")

    def run_once(self) -> bool:
        """
        Run a single trading cycle.
        
        Returns:
            True if cycle completes successfully, False otherwise
        """
        print("🔄 Running single trading cycle...\n")
        
        try:
            # Initialize engine if not already done
            if not self.engine:
                config = load_bot_config()
                if self.config_path:
                    import yaml
                    with open(self.config_path, 'r') as f:
                        config = yaml.safe_load(f) or {}
                runtime_overrides = config.get("runtime_overrides", {})
                runtime_overrides["force_execution"] = self.force_execution
                if self.min_confidence > 0:
                    runtime_overrides["min_confidence"] = self.min_confidence
                if self.min_trade_usd > 0:
                    runtime_overrides["min_trade_usd"] = self.min_trade_usd
                config["runtime_overrides"] = runtime_overrides
                self.engine = TradingEngine(config=config)
            
            # Run one cycle
            self.engine.run_trading_cycle()
            self._emit_metrics(cycle=1, mode=self.mode, status="cycle_complete")
            print("\n✅ Trading cycle complete")
            return True
            
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Error during trading cycle: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_continuous(self) -> int:
        """
        Run the bot continuously until stopped.
        
        Returns:
            Exit code (0 for success, 1 for error)
        """
        print("🔄 Starting continuous trading mode...")
        print("   Press Ctrl+C to stop gracefully\n")
        
        try:
            # Initialize engine
            config = load_bot_config()
            if self.config_path:
                import yaml
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
            runtime_overrides = config.get("runtime_overrides", {})
            runtime_overrides["force_execution"] = self.force_execution
            if self.min_confidence > 0:
                runtime_overrides["min_confidence"] = self.min_confidence
            if self.min_trade_usd > 0:
                runtime_overrides["min_trade_usd"] = self.min_trade_usd
            config["runtime_overrides"] = runtime_overrides
            self.engine = TradingEngine(config=config)
            
            cycle_count = 0
            error_count = 0
            max_consecutive_errors = 5
            
            while not self.should_stop:
                cycle_count += 1
                print(f"\n{'='*80}")
                print(f"Cycle #{cycle_count} - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"{'='*80}\n")
                
                try:
                    self.engine.run_trading_cycle()
                    self._emit_metrics(cycle=cycle_count, mode=self.mode, status="cycle_complete")
                    error_count = 0
                    if not self.should_stop:
                        sleep_time = getattr(self.engine, "poll_seconds", 30)
                        print(f"\n💤 Sleeping for {sleep_time} seconds...")
                        time.sleep(sleep_time)
                
                except KeyboardInterrupt:
                    print("\n🛑 Interrupted by user")
                    break
                
                except Exception as e:
                    error_count += 1
                    print(f"\n❌ Error in cycle #{cycle_count}: {e}")
                    
                    if error_count >= max_consecutive_errors:
                        print(f"\n🚨 Too many consecutive errors ({error_count}). Stopping for safety.")
                        return 1
                    
                    # Exponential backoff
                    backoff_time = min(300, 10 * (2 ** error_count))
                    print(f"⏳ Backing off for {backoff_time} seconds...")
                    time.sleep(backoff_time)
            
            print("\n✅ Bot stopped gracefully")
            self._emit_metrics(cycle=cycle_count, mode=self.mode, status="stopped")
            return 0
        
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            self._emit_metrics(cycle=cycle_count if 'cycle_count' in locals() else -1, mode=self.mode, status="fatal_error")
            return 1


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Multiple-Signal Decision Bot - Canonical Entry Point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run preflight checks
  python main.py --preflight
  
  # Single cycle in paper mode
  python main.py --mode paper --once
  
  # Continuous paper trading
  python main.py --mode paper
  
  # Continuous live trading (REAL MONEY)
  python main.py --mode live
  
  # Use custom config file
  python main.py --mode paper --config my-config.yaml

For more information, see docs/OPERATIONS.md
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["paper", "live"],
        default="paper",
        help="Trading mode: 'paper' for simulation, 'live' for real trading (default: paper)"
    )
    
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single trading cycle and exit"
    )
    
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run preflight checks and exit (no trading)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (default: config/config.yaml)"
    )
    
    parser.add_argument(
        "--symbols",
        type=str,
        help="Comma-separated list of trading symbols (overrides config)"
    )
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help="Explicitly confirm launching in --mode live (OR set CONFIRM_LIVE=YES)"
    )
    parser.add_argument(
        "--force-execution",
        action="store_true",
        help="Force execution even if confidence below config threshold"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Override minimum confidence required to execute a trade"
    )
    parser.add_argument(
        "--min-trade-usd",
        type=float,
        default=0.0,
        help="Override minimum trade USD size threshold"
    )
    return parser.parse_args()


def main() -> int:
    """
    Main entry point for the trading bot.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    args = parse_arguments()
    
    # Create orchestrator
    orchestrator = BotOrchestrator(
        mode=args.mode,
        config_path=args.config,
        confirm_live=args.confirm_live,
        force_execution=args.force_execution,
        min_confidence=args.min_confidence,
        min_trade_usd=args.min_trade_usd,
    )
    
    # Preflight-only mode
    if args.preflight:
        return 0 if orchestrator.run_preflight() else 1
    
    # Validate environment
    if not orchestrator.validate_environment():
        return 1
    
    # Run once or continuous
    if args.once:
        return 0 if orchestrator.run_once() else 1
    else:
        return orchestrator.run_continuous()


if __name__ == "__main__":
    sys.exit(main())
