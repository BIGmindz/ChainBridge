"""
BACKTEST ENGINE
Comprehensive backtesting engine for evaluating trading strategies
"""

import json
import os
from datetime import datetime
from typing import Callable, Dict

import numpy as np
import pandas as pd

# pathlib.Path not used in this module


class BacktestEngine:
    """
    Full-featured backtesting engine for trading strategy evaluation
    """

    def __init__(self, config: Dict = None):
        """Initialize backtest engine with configuration"""
        self.config = config or {}
        self.initial_capital = self.config.get("initial_capital", 10000)
        self.current_capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.signals_history = []
        self.custom_metrics = {}

        # Configure risk parameters
        self.position_size_pct = self.config.get(
            "position_size_pct", 0.02
        )  # 2% risk per trade
        self.max_positions = self.config.get("max_positions", 5)
        self.stop_loss_pct = self.config.get("stop_loss_pct", 0.05)
        self.take_profit_pct = self.config.get("take_profit_pct", 0.1)

        print(f"✅ Backtest Engine initialized with ${self.initial_capital:,.2f}")

    def run(self, price_data: pd.DataFrame, signal_generator: Callable) -> Dict:
        """
        Run backtest using provided price data and signal generator function

        Args:
            price_data: DataFrame with OHLCV data
            signal_generator: Function that takes price data and returns signals dict

        Returns:
            Dict with backtest results
        """
        if len(price_data) < 2:
            raise ValueError("Insufficient price data for backtest")

        print(f"\n🔄 Running backtest on {len(price_data)} data points...")

        # Track progress for long runs
        total_bars = len(price_data)
        progress_step = max(1, total_bars // 20)  # Show ~20 progress updates

        # Run the backtest bar by bar
        for i in range(len(price_data)):
            # Get current bar data
            current_data = price_data.iloc[: i + 1]
            if len(current_data) < 2:  # Need at least 2 bars for most indicators
                continue

            # Get signals for this bar
            current_bar = price_data.iloc[i]
            signals = signal_generator(current_data)
            self.signals_history.append(signals)

            # Process existing positions (check stops, take profits)
            self._process_positions(current_bar)

            # Process new signals
            self._process_signals(signals, current_bar)

            # Update equity curve
            self._update_equity(current_bar)

            # Show progress for long backtests
            if i % progress_step == 0 or i == total_bars - 1:
                pct_complete = (i + 1) / total_bars * 100
                print(
                    f"  {pct_complete:.1f}% complete... Current equity: ${self.current_capital:,.2f}"
                )

        # Calculate final metrics
        results = self._calculate_results()

        # Print a safer version of the results summary
        win_rate_str = (
            f"{results.get('win_rate', 0):.1%}" if "win_rate" in results else "N/A"
        )
        print(
            f"\n✅ Backtest complete: {results.get('total_trades', 0)} trades, "
            + f"{results.get('total_return', 0):.2%} return, {win_rate_str} win rate"
        )

        return results

    def _process_positions(self, current_bar: pd.Series):
        """Process existing positions - check stops and targets"""
        positions_to_close = []
        for symbol, position in self.positions.items():
            # Check if we need to close this position
            close_position = False
            close_reason = None
            pnl = 0

            current_price = current_bar["close"]

            if position["side"] == "BUY":
                # For long positions
                pnl = (current_price / position["entry_price"] - 1) * position["size"]

                # Check stop loss
                if current_price <= position["stop_price"]:
                    close_position = True
                    close_reason = "stop_loss"

                # Check take profit
                elif current_price >= position["target_price"]:
                    close_position = True
                    close_reason = "take_profit"

            elif position["side"] == "SELL":
                # For short positions
                pnl = (1 - current_price / position["entry_price"]) * position["size"]

                # Check stop loss
                if current_price >= position["stop_price"]:
                    close_position = True
                    close_reason = "stop_loss"

                # Check take profit
                elif current_price <= position["target_price"]:
                    close_position = True
                    close_reason = "take_profit"

            # Close position if needed
            if close_position:
                positions_to_close.append((symbol, pnl, close_reason))

        # Close positions (in separate loop to avoid modifying while iterating)
        for symbol, pnl, reason in positions_to_close:
            self._close_position(symbol, current_bar["close"], pnl, reason)

    def _process_signals(self, signals: Dict, current_bar: pd.Series):
        """Process trading signals"""
        # Get combined signal strength
        signal_strength = self._calculate_signal_strength(signals)

        # Check if we should enter a new position
        if signal_strength > 0.3 and len(self.positions) < self.max_positions:
            # BUY signal
            self._open_position("BUY", current_bar, signal_strength)

        elif signal_strength < -0.3 and len(self.positions) < self.max_positions:
            # SELL signal
            self._open_position("SELL", current_bar, abs(signal_strength))

    def _calculate_signal_strength(self, signals: Dict) -> float:
        """Calculate combined signal strength from multiple indicators"""
        if not signals:
            return 0.0

        # Simple weighted average of signals
        total_weight = sum(abs(v) for v in signals.values())
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(v for v in signals.values())
        return weighted_sum / len(signals)  # Normalized to [-1, 1] range

    def _open_position(self, side: str, bar: pd.Series, strength: float):
        """Open a new position"""
        current_price = bar["close"]
        position_size = self.current_capital * self.position_size_pct * strength

        # Calculate stop loss and take profit levels
        if side == "BUY":
            stop_price = current_price * (1 - self.stop_loss_pct)
            target_price = current_price * (1 + self.take_profit_pct)
        else:  # SELL
            stop_price = current_price * (1 + self.stop_loss_pct)
            target_price = current_price * (1 - self.take_profit_pct)

        # Create position
        symbol = bar.name if hasattr(bar, "name") else "UNKNOWN"
        position = {
            "side": side,
            "entry_price": current_price,
            "size": position_size,
            "stop_price": stop_price,
            "target_price": target_price,
            "entry_time": bar.get("timestamp", datetime.now()),
            "strength": strength,
        }

        # Add to positions
        self.positions[symbol] = position

        # Record the trade
        trade = {
            "symbol": symbol,
            "side": side,
            "entry_price": current_price,
            "size": position_size,
            "entry_time": bar.get("timestamp", datetime.now()),
            "exit_price": None,
            "exit_time": None,
            "pnl": 0,
            "status": "open",
        }
        self.trades.append(trade)

    def _close_position(
        self, symbol: str, current_price: float, pnl: float, reason: str
    ):
        """Close an existing position"""
        if symbol not in self.positions:
            return
        _position = self.positions[symbol]

        # Update account balance
        self.current_capital += pnl

        # Find the corresponding open trade and update it
        for trade in reversed(self.trades):
            if trade["symbol"] == symbol and trade["status"] == "open":
                trade["exit_price"] = current_price
                trade["exit_time"] = datetime.now()
                trade["pnl"] = pnl
                trade["status"] = "closed"
                trade["close_reason"] = reason
                break

        # Remove from active positions
        del self.positions[symbol]

    def _update_equity(self, current_bar: pd.Series):
        """Update equity curve with current positions value"""
        # Calculate unrealized P&L from open positions
        unrealized_pnl = 0
        current_price = current_bar["close"]

        for symbol, position in self.positions.items():
            if position["side"] == "BUY":
                pos_pnl = (current_price / position["entry_price"] - 1) * position[
                    "size"
                ]
            else:  # SELL
                pos_pnl = (1 - current_price / position["entry_price"]) * position[
                    "size"
                ]
            unrealized_pnl += pos_pnl

        # Update equity curve with current value (cash + positions)
        current_equity = self.current_capital + unrealized_pnl
        self.equity_curve.append(current_equity)

    def _calculate_results(self) -> Dict:
        """Calculate backtest performance metrics"""
        results = {
            "initial_capital": self.initial_capital,
            "final_capital": self.current_capital,
            "total_trades": len([t for t in self.trades if t["status"] == "closed"]),
            "open_trades": len([t for t in self.trades if t["status"] == "open"]),
        }

        # Calculate returns
        results["total_return"] = (
            self.current_capital - self.initial_capital
        ) / self.initial_capital

        # Calculate win/loss metrics
        closed_trades = [t for t in self.trades if t["status"] == "closed"]
        if closed_trades:
            winning_trades = [t for t in closed_trades if t["pnl"] > 0]
            results["winning_trades"] = len(winning_trades)
            results["losing_trades"] = len(closed_trades) - len(winning_trades)
            results["win_rate"] = (
                len(winning_trades) / len(closed_trades) if closed_trades else 0
            )

            # Calculate average win/loss
            if winning_trades:
                results["avg_win"] = sum(t["pnl"] for t in winning_trades) / len(
                    winning_trades
                )
            if results["losing_trades"] > 0:
                losing_trades = [t for t in closed_trades if t["pnl"] <= 0]
                results["avg_loss"] = sum(t["pnl"] for t in losing_trades) / len(
                    losing_trades
                )

            # Calculate profit factor
            total_wins = sum(t["pnl"] for t in winning_trades)
            total_losses = sum(abs(t["pnl"]) for t in closed_trades if t["pnl"] <= 0)
            results["profit_factor"] = (
                total_wins / total_losses if total_losses else float("inf")
            )

        # Calculate equity curve metrics
        equity_series = pd.Series(self.equity_curve)

        # Calculate returns
        returns = equity_series.pct_change().dropna()
        if len(returns) > 0:
            # Sharpe ratio (assuming 252 trading days per year)
            results["sharpe_ratio"] = (
                (returns.mean() / returns.std()) * np.sqrt(252)
                if returns.std() > 0
                else 0
            )

            # Sortino ratio (downside deviation only)
            negative_returns = returns[returns < 0]
            downside_deviation = negative_returns.std()
            results["sortino_ratio"] = (
                (returns.mean() / downside_deviation) * np.sqrt(252)
                if downside_deviation > 0
                else 0
            )

        # Maximum drawdown
        peak = equity_series.expanding().max()
        drawdown = (equity_series - peak) / peak
        results["max_drawdown"] = drawdown.min()

        # Calculate other metrics
        results.update(self.custom_metrics)

        return results

    def add_custom_metric(self, name: str, value):
        """Add a custom metric to track in results"""
        self.custom_metrics[name] = value

    def plot_equity_curve(self, filename: str = None):
        """Plot equity curve (requires matplotlib)"""
        try:
            import matplotlib.pyplot as plt

            plt.figure(figsize=(12, 6))
            plt.plot(self.equity_curve)
            plt.title("Backtest Equity Curve")
            plt.xlabel("Bar Number")
            plt.ylabel("Equity ($)")
            plt.grid(True)

            if filename:
                plt.savefig(filename)
                print(f"✅ Equity curve saved to {filename}")
            else:
                plt.show()

        except ImportError:
            print("⚠️ Matplotlib not available. Cannot plot equity curve.")

    def save_results(self, filename: str = None):
        """Save backtest results to JSON file"""
        if filename is None:
            filename = (
                f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        # Calculate final results
        results = self._calculate_results()

        # Add trade summary
        results["trades"] = [
            {k: str(v) if isinstance(v, datetime) else v for k, v in t.items()}
            for t in self.trades
        ]

        # Add equity curve (sampled to reduce file size if very large)
        max_equity_points = 1000
        equity_curve = self.equity_curve
        if len(equity_curve) > max_equity_points:
            step = len(equity_curve) // max_equity_points
            equity_curve = equity_curve[::step]
        results["equity_curve"] = equity_curve

        # Save to file
        os.makedirs(
            os.path.dirname(filename) if os.path.dirname(filename) else ".",
            exist_ok=True,
        )
        with open(filename, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"✅ Backtest results saved to {filename}")

    def generate_report(self) -> str:
        """Generate a formatted backtest report"""
        results = self._calculate_results()

        report = f"""
        📊 BACKTEST REPORT
        =================
        Initial Capital: ${self.initial_capital:,.2f}
        Final Capital: ${self.current_capital:,.2f}
        Total Return: {results["total_return"]:.2%}
        
        TRADE STATISTICS
        ---------------
        Total Trades: {results["total_trades"]}
        Winning Trades: {results.get("winning_trades", 0)}
        Losing Trades: {results.get("losing_trades", 0)}
        Win Rate: {results.get("win_rate", 0):.1%}
        
        RISK METRICS
        -----------
        Max Drawdown: {results.get("max_drawdown", 0):.2%}
        Sharpe Ratio: {results.get("sharpe_ratio", 0):.2f}
        Sortino Ratio: {results.get("sortino_ratio", 0):.2f}
        Profit Factor: {results.get("profit_factor", 0):.2f}
        
        TRADE PERFORMANCE
        ----------------
        Average Win: ${results.get("avg_win", 0):,.2f}
        Average Loss: ${results.get("avg_loss", 0):,.2f}
        Largest Win: ${max([t["pnl"] for t in self.trades if t["status"] == "closed" and t["pnl"] > 0], default=0):,.2f}
        Largest Loss: ${min([t["pnl"] for t in self.trades if t["status"] == "closed"], default=0):,.2f}
        """

        return report
