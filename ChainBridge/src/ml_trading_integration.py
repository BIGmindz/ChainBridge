"""
ML Integration Module for Kraken Paper Trading Bot
=================================================

This module integrates the KrakenPaperLiveBot with the existing ML decision engine,
providing seamless connection between signal generation and trade execution.

Features:
- Signal aggregation from multiple modules
- ML confidence weighting
- Risk-adjusted position sizing
- Performance feedback loop
- Real-time decision making

Author: BIGmindz
Version: 1.0.0
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Import existing components
try:
    from core.module_manager import ModuleManager
except ImportError:
    # Mock ModuleManager for testing
    class ModuleManager:
        def __init__(self):
            self.modules = {}


try:
    from .kraken_paper_live_bot import KrakenPaperLiveBot
except ImportError:
    from kraken_paper_live_bot import KrakenPaperLiveBot

try:
    from .exchange_adapter import ExchangeAdapter  # noqa: F401
except ImportError:
    pass


class MLTradingIntegration:
    """
    Integration layer between ML signals and Kraken paper trading execution
    """

    def __init__(
        self,
        paper_bot: KrakenPaperLiveBot,
        module_manager: ModuleManager,
        config: Dict[str, Any],
    ):
        """
        Initialize ML trading integration

        Args:
            paper_bot: KrakenPaperLiveBot instance
            module_manager: ModuleManager with signal modules
            config: Integration configuration
        """
        self.paper_bot = paper_bot
        self.module_manager = module_manager
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Signal processing settings
        self.signal_weights = config.get(
            "signal_weights",
            {
                "rsi": 0.2,
                "macd": 0.25,
                "bollinger_bands": 0.2,
                "volume_profile": 0.15,
                "sentiment_analysis": 0.2,
            },
        )

        self.confidence_threshold = config.get("confidence_threshold", 0.6)
        self.cooldown_minutes = config.get("cooldown_minutes", 30)
        self.last_signal_time = {}

        # Performance tracking for feedback loop
        self.signal_performance = {}
        self.position_outcomes = []

        self.logger.info("ML Trading Integration initialized")

    async def process_trading_signals(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Process signals for all symbols and make trading decisions

        Args:
            symbols: List of trading symbols to analyze

        Returns:
            Trading decisions and execution results
        """
        results = {}

        for symbol in symbols:
            try:
                # Collect signals from all modules
                signal_data = await self._collect_symbol_signals(symbol)

                if not signal_data:
                    continue

                # Aggregate signals using ML-based weighting
                aggregated_signal = self._aggregate_signals(signal_data, symbol)

                # Make trading decision
                decision = self._make_trading_decision(symbol, aggregated_signal)

                if decision["action"] != "HOLD":
                    # Execute trade
                    execution_result = await self._execute_trade(symbol, decision)
                    results[symbol] = {
                        "signals": signal_data,
                        "aggregated_signal": aggregated_signal,
                        "decision": decision,
                        "execution": execution_result,
                    }

            except Exception as e:
                self.logger.error(f"Error processing signals for {symbol}: {e}")
                results[symbol] = {"error": str(e)}

        return results

    async def _collect_symbol_signals(self, symbol: str) -> Dict[str, Any]:
        """
        Collect signals from all registered modules for a specific symbol

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary of signals from all modules
        """
        signals = {}

        # Get current price data (required by some modules)
        current_price = self.paper_bot.price_data.get(symbol)
        if not current_price:
            self.logger.warning(f"No price data available for {symbol}")
            return signals

        # Collect signals from each module
        for module_name, module in self.module_manager.modules.items():
            try:
                # Get signal from module
                signal_result = await self._get_module_signal(
                    module, symbol, current_price
                )

                if signal_result:
                    signals[module_name] = signal_result

            except Exception as e:
                self.logger.error(
                    f"Error getting signal from {module_name} for {symbol}: {e}"
                )

        return signals

    async def _get_module_signal(
        self, module, symbol: str, price_data
    ) -> Optional[Dict[str, Any]]:
        """
        Get signal from a specific module

        Args:
            module: Signal module instance
            symbol: Trading symbol
            price_data: Current price data

        Returns:
            Signal data from the module
        """
        try:
            # Different modules may have different interfaces
            if hasattr(module, "generate_signal"):
                return await module.generate_signal(symbol, price_data)
            elif hasattr(module, "process"):
                return await module.process(symbol, price_data)
            elif hasattr(module, "calculate"):
                return await module.calculate(symbol, price_data)
            else:
                self.logger.warning(
                    f"Module {module.__class__.__name__} has no recognized signal method"
                )
                return None

        except Exception as e:
            self.logger.error(f"Error calling module {module.__class__.__name__}: {e}")
            return None

    def _aggregate_signals(
        self, signal_data: Dict[str, Any], symbol: str
    ) -> Dict[str, Any]:
        """
        Aggregate signals from multiple modules using weighted average

        Args:
            signal_data: Raw signals from all modules
            symbol: Trading symbol

        Returns:
            Aggregated signal with confidence score
        """
        if not signal_data:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "reason": "No signals available",
            }

        buy_weight = 0.0
        sell_weight = 0.0
        total_weight = 0.0
        signal_details = {}

        # Process each signal
        for module_name, signal in signal_data.items():
            module_weight = self.signal_weights.get(module_name, 0.1)

            # Adjust weight based on historical performance
            performance_multiplier = self._get_module_performance_multiplier(
                module_name, symbol
            )
            adjusted_weight = module_weight * performance_multiplier

            # Extract signal strength and direction
            signal_strength = self._extract_signal_strength(signal)
            signal_direction = self._extract_signal_direction(signal)

            # Weight the signal
            if signal_direction == "BUY":
                buy_weight += adjusted_weight * signal_strength
            elif signal_direction == "SELL":
                sell_weight += adjusted_weight * signal_strength

            total_weight += adjusted_weight
            signal_details[module_name] = {
                "direction": signal_direction,
                "strength": signal_strength,
                "weight": adjusted_weight,
                "raw_signal": signal,
            }

        # Determine final signal
        if total_weight == 0:
            return {"signal": "HOLD", "confidence": 0.0, "reason": "No valid signals"}

        # Normalize weights
        buy_score = buy_weight / total_weight
        sell_score = sell_weight / total_weight

        # Determine action and confidence
        if buy_score > sell_score and buy_score > self.confidence_threshold:
            final_signal = "BUY"
            confidence = buy_score
        elif sell_score > buy_score and sell_score > self.confidence_threshold:
            final_signal = "SELL"
            confidence = sell_score
        else:
            final_signal = "HOLD"
            confidence = max(buy_score, sell_score)

        return {
            "signal": final_signal,
            "confidence": confidence,
            "buy_score": buy_score,
            "sell_score": sell_score,
            "signal_count": len(signal_data),
            "details": signal_details,
            "reason": f"Aggregated from {len(signal_data)} signals",
        }

    def _extract_signal_strength(self, signal: Dict[str, Any]) -> float:
        """Extract normalized signal strength (0-1) from module output"""
        # Handle different signal formats
        if isinstance(signal, dict):
            # Look for common strength indicators
            for key in ["strength", "confidence", "score", "probability"]:
                if key in signal:
                    value = signal[key]
                    # Normalize to 0-1 range
                    if isinstance(value, (int, float)):
                        return max(0.0, min(1.0, abs(value)))

            # Look for RSI-style signals
            if "rsi" in signal:
                rsi_value = signal["rsi"]
                if rsi_value <= 30:
                    return (30 - rsi_value) / 30  # Stronger as it gets lower
                elif rsi_value >= 70:
                    return (rsi_value - 70) / 30  # Stronger as it gets higher
                else:
                    return 0.0

            # Look for boolean signals
            if "signal" in signal:
                return 1.0 if signal["signal"] in ["BUY", "SELL"] else 0.0

        # Default strength
        return 0.5

    def _extract_signal_direction(self, signal: Dict[str, Any]) -> str:
        """Extract signal direction from module output"""
        if isinstance(signal, dict):
            # Look for explicit signal
            if "signal" in signal:
                return str(signal["signal"]).upper()

            if "action" in signal:
                return str(signal["action"]).upper()

            # Look for RSI-style signals
            if "rsi" in signal:
                rsi_value = signal["rsi"]
                if rsi_value <= 30:
                    return "BUY"
                elif rsi_value >= 70:
                    return "SELL"

            # Look for MACD signals
            if "macd_signal" in signal:
                return "BUY" if signal["macd_signal"] > 0 else "SELL"

            # Look for boolean indicators
            for buy_key in ["is_oversold", "buy_signal", "bullish"]:
                if signal.get(buy_key, False):
                    return "BUY"

            for sell_key in ["is_overbought", "sell_signal", "bearish"]:
                if signal.get(sell_key, False):
                    return "SELL"

        return "HOLD"

    def _get_module_performance_multiplier(
        self, module_name: str, symbol: str
    ) -> float:
        """
        Get performance-based weight multiplier for a module

        Args:
            module_name: Name of the signal module
            symbol: Trading symbol

        Returns:
            Performance multiplier (0.5 - 2.0)
        """
        key = f"{module_name}_{symbol}"

        if key not in self.signal_performance:
            return 1.0  # Default multiplier

        perf_data = self.signal_performance[key]

        # Calculate success rate
        total_signals = perf_data["total_signals"]
        successful_signals = perf_data["successful_signals"]

        if total_signals < 10:
            return 1.0  # Need more data

        success_rate = successful_signals / total_signals

        # Map success rate to multiplier (0.5x to 2.0x)
        if success_rate > 0.7:
            return 1.5 + (success_rate - 0.7) * 1.67  # 1.5x to 2.0x
        elif success_rate > 0.5:
            return 1.0 + (success_rate - 0.5) * 2.5  # 1.0x to 1.5x
        else:
            return 0.5 + success_rate  # 0.5x to 1.0x

    def _make_trading_decision(
        self, symbol: str, aggregated_signal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make final trading decision based on aggregated signal and risk management

        Args:
            symbol: Trading symbol
            aggregated_signal: Aggregated signal from all modules

        Returns:
            Trading decision with action and parameters
        """
        signal = aggregated_signal["signal"]
        confidence = aggregated_signal["confidence"]

        # Check cooldown period
        now = datetime.now(timezone.utc)
        last_signal_key = f"{symbol}_{signal}"

        if last_signal_key in self.last_signal_time:
            time_since_last = (
                now - self.last_signal_time[last_signal_key]
            ).total_seconds() / 60
            if time_since_last < self.cooldown_minutes:
                return {
                    "action": "HOLD",
                    "reason": f"Cooldown period active ({time_since_last:.1f} min < {self.cooldown_minutes} min)",
                    "confidence": confidence,
                }

        # Check if we already have a position in this symbol
        existing_positions = [
            pos for pos in self.paper_bot.positions.values() if pos.symbol == symbol
        ]

        if signal == "HOLD":
            return {
                "action": "HOLD",
                "reason": "Signal below confidence threshold or conflicting signals",
                "confidence": confidence,
            }

        # Check position limits
        if len(existing_positions) > 0 and signal in ["BUY", "SELL"]:
            # Already have position - could implement position scaling here
            return {
                "action": "HOLD",
                "reason": f"Already have position in {symbol}",
                "confidence": confidence,
            }

        # Calculate volatility for position sizing
        volatility = self._calculate_symbol_volatility(symbol)

        # Update last signal time
        self.last_signal_time[last_signal_key] = now

        return {
            "action": signal,
            "confidence": confidence,
            "volatility": volatility,
            "reason": f"ML decision with {confidence:.2f} confidence",
            "signal_details": aggregated_signal.get("details", {}),
            "stop_loss_pct": self._calculate_dynamic_stop_loss(confidence, volatility),
            "take_profit_pct": self._calculate_dynamic_take_profit(
                confidence, volatility
            ),
        }

    def _calculate_symbol_volatility(self, symbol: str) -> float:
        """
        Calculate recent volatility for the symbol

        Args:
            symbol: Trading symbol

        Returns:
            Estimated volatility (standard deviation of returns)
        """
        # For now, return a default volatility based on symbol type
        # In production, this should calculate from recent price history

        if symbol.startswith("BTC"):
            return 0.04  # 4% daily volatility for BTC
        elif symbol.startswith("ETH"):
            return 0.05  # 5% daily volatility for ETH
        else:
            return 0.06  # 6% for altcoins

    def _calculate_dynamic_stop_loss(
        self, confidence: float, volatility: float
    ) -> float:
        """Calculate dynamic stop loss based on confidence and volatility"""
        base_stop = 0.03  # 3% base stop loss

        # Adjust based on confidence (higher confidence = tighter stop)
        confidence_adjustment = (1.0 - confidence) * 0.02  # Up to 2% adjustment

        # Adjust based on volatility
        volatility_adjustment = volatility * 0.5  # 50% of volatility

        return base_stop + confidence_adjustment + volatility_adjustment

    def _calculate_dynamic_take_profit(
        self, confidence: float, volatility: float
    ) -> float:
        """Calculate dynamic take profit based on confidence and volatility"""
        base_tp = 0.06  # 6% base take profit

        # Adjust based on confidence (higher confidence = wider target)
        confidence_adjustment = confidence * 0.04  # Up to 4% adjustment

        # Adjust based on volatility
        volatility_adjustment = volatility * 1.0  # 100% of volatility

        return base_tp + confidence_adjustment + volatility_adjustment

    async def _execute_trade(
        self, symbol: str, decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute trading decision using the paper bot

        Args:
            symbol: Trading symbol
            decision: Trading decision dictionary

        Returns:
            Execution result
        """
        try:
            action = decision["action"]
            confidence = decision["confidence"]
            volatility = decision.get("volatility", 0.03)
            stop_loss_pct = decision.get("stop_loss_pct", 0.03)
            take_profit_pct = decision.get("take_profit_pct", 0.06)

            # Create tags for position tracking
            tags = [
                f"ml_confidence_{confidence:.2f}",
                f"signal_count_{len(decision.get('signal_details', {}))}",
                "auto_ml_trade",
            ]

            # Execute the trade
            result = self.paper_bot.open_position(
                symbol=symbol,
                side=action,
                signal_confidence=confidence,
                volatility=volatility,
                stop_loss_pct=stop_loss_pct,
                take_profit_pct=take_profit_pct,
                tags=tags,
            )

            if result.get("success", False):
                self.logger.info(
                    f"Trade executed: {action} {symbol} "
                    f"(Confidence: {confidence:.2f}, SL: {stop_loss_pct:.2f}%, TP: {take_profit_pct:.2f}%)"
                )

                # Track the signal for performance feedback
                self._track_signal_usage(
                    decision["signal_details"], symbol, result["position_id"]
                )

            return result

        except Exception as e:
            self.logger.error(f"Error executing trade for {symbol}: {e}")
            return {"success": False, "error": str(e)}

    def _track_signal_usage(
        self, signal_details: Dict[str, Any], symbol: str, position_id: str
    ):
        """
        Track signal usage for performance feedback loop

        Args:
            signal_details: Details of signals used
            symbol: Trading symbol
            position_id: Position identifier for tracking outcome
        """
        for module_name, signal_info in signal_details.items():
            key = f"{module_name}_{symbol}"

            if key not in self.signal_performance:
                self.signal_performance[key] = {
                    "total_signals": 0,
                    "successful_signals": 0,
                    "failed_signals": 0,
                    "avg_confidence": 0.0,
                    "recent_outcomes": [],
                }

            self.signal_performance[key]["total_signals"] += 1

            # Store for later outcome evaluation
            self.position_outcomes.append(  # type: ignore
                {
                    "position_id": position_id,
                    "module_signals": signal_details,
                    "symbol": symbol,
                    "timestamp": datetime.now(timezone.utc),
                }
            )

    def update_signal_performance(self, position_id: str, outcome: str, pnl: float):
        """
        Update signal performance based on position outcome

        Args:
            position_id: Position identifier
            outcome: 'WIN', 'LOSS', or 'BREAKEVEN'
            pnl: Profit/loss amount
        """
        # Find the position outcome record
        for outcome_record in self.position_outcomes:
            if outcome_record["position_id"] == position_id:
                # Update performance for each module that contributed
                for module_name, signal_info in outcome_record[
                    "module_signals"
                ].items():
                    key = f"{module_name}_{outcome_record['symbol']}"

                    if key in self.signal_performance:
                        if outcome == "WIN":
                            self.signal_performance[key]["successful_signals"] += 1
                        else:
                            self.signal_performance[key]["failed_signals"] += 1

                        # Update recent outcomes (keep last 20)
                        recent_outcomes = self.signal_performance[key][
                            "recent_outcomes"
                        ]
                        recent_outcomes.append(  # type: ignore
                            {
                                "outcome": outcome,
                                "pnl": pnl,
                                "timestamp": datetime.now(timezone.utc),
                            }
                        )

                        if len(recent_outcomes) > 20:
                            recent_outcomes.pop(0)

                # Remove processed outcome
                self.position_outcomes.remove(outcome_record)
                break

    def get_signal_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive signal performance report

        Returns:
            Performance report for all modules
        """
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "modules": {},
            "summary": {
                "total_modules": 0,
                "active_modules": 0,
                "avg_success_rate": 0.0,
                "best_performing_module": None,
                "worst_performing_module": None,
            },
        }

        success_rates = []

        for key, perf_data in self.signal_performance.items():
            module_name, symbol = key.rsplit("_", 1)

            if module_name not in report["modules"]:
                report["modules"][module_name] = {}

            total = perf_data["total_signals"]
            successful = perf_data["successful_signals"]
            success_rate = successful / total if total > 0 else 0.0

            report["modules"][module_name][symbol] = {
                "total_signals": total,
                "successful_signals": successful,
                "failed_signals": perf_data["failed_signals"],
                "success_rate": success_rate,
                "performance_multiplier": self._get_module_performance_multiplier(
                    module_name, symbol
                ),
                "recent_outcomes": perf_data["recent_outcomes"][-5:],  # Last 5 outcomes
            }

            success_rates.append(success_rate)  # type: ignore

        # Calculate summary statistics
        report["summary"]["total_modules"] = len(
            set(key.rsplit("_", 1)[0] for key in self.signal_performance.keys())
        )
        report["summary"]["active_modules"] = len(
            [sr for sr in success_rates if sr > 0]
        )
        report["summary"]["avg_success_rate"] = (
            np.mean(success_rates) if success_rates else 0.0
        )

        # Find best and worst performing modules
        if success_rates:
            module_performance = {}
            for key, perf_data in self.signal_performance.items():
                module_name = key.rsplit("_", 1)[0]
                if module_name not in module_performance:
                    module_performance[module_name] = []

                total = perf_data["total_signals"]
                if total > 5:  # Only consider modules with sufficient data
                    success_rate = perf_data["successful_signals"] / total
                    module_performance[module_name].append(success_rate)  # type: ignore

            # Calculate average success rate per module
            avg_module_performance = {
                module: np.mean(rates)
                for module, rates in module_performance.items()
                if rates
            }

            if avg_module_performance:
                best_module = max(
                    avg_module_performance.keys(),
                    key=lambda x: avg_module_performance[x],
                )
                worst_module = min(
                    avg_module_performance.keys(),
                    key=lambda x: avg_module_performance[x],
                )

                report["summary"]["best_performing_module"] = {
                    "name": best_module,
                    "success_rate": avg_module_performance[best_module],
                }
                report["summary"]["worst_performing_module"] = {
                    "name": worst_module,
                    "success_rate": avg_module_performance[worst_module],
                }

        return report


# Integration helper functions
async def create_ml_trading_system(
    config_path: str = None,
) -> Tuple[KrakenPaperLiveBot, MLTradingIntegration]:
    """
    Create complete ML trading system with paper bot and integration

    Args:
        config_path: Path to configuration file

    Returns:
        Tuple of (paper_bot, ml_integration)
    """
    import yaml

    from ..core.module_manager import ModuleManager
    from ..kraken_paper_live_bot import create_kraken_paper_bot

    # Load configuration
    if config_path:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    # Create paper trading bot
    paper_bot = create_kraken_paper_bot(config_dict=config)

    # Create module manager and register modules
    module_manager = ModuleManager()

    # Register signal modules (this would be customized based on available modules)
    # module_manager.register_module("rsi", RSIModule())
    # module_manager.register_module("macd", MACDModule())
    # etc.

    # Create ML integration
    ml_integration = MLTradingIntegration(
        paper_bot, module_manager, config.get("ml_integration", {})
    )

    return paper_bot, ml_integration


async def run_integrated_trading_loop(
    paper_bot: KrakenPaperLiveBot,
    ml_integration: MLTradingIntegration,
    symbols: List[str],
    update_interval: int = 60,
):
    """
    Run integrated trading loop with ML signal processing

    Args:
        paper_bot: KrakenPaperLiveBot instance
        ml_integration: MLTradingIntegration instance
        symbols: List of symbols to trade
        update_interval: Update interval in seconds
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting integrated ML trading loop...")

    try:
        while True:
            # Process trading signals
            results = await ml_integration.process_trading_signals(symbols)

            # Log results
            for symbol, result in results.items():
                if "execution" in result and result["execution"].get("success"):
                    logger.info(
                        f"Trade executed for {symbol}: {result['decision']['action']}"
                    )
                elif "error" in result:
                    logger.error(f"Error processing {symbol}: {result['error']}")

            # Wait for next iteration
            await asyncio.sleep(update_interval)

    except KeyboardInterrupt:
        logger.info("Trading loop interrupted by user")
    except Exception as e:
        logger.error(f"Error in trading loop: {e}")
    finally:
        # Cleanup
        paper_bot.stop_trading()
        logger.info("Integrated trading loop stopped")
