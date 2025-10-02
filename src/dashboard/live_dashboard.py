"""
LIVE DASHBOARD
Real-time monitoring and visualization for the trading system
"""

import json
import os
from datetime import datetime
from typing import Dict


class LiveDashboard:
    """
    Real-time dashboard for monitoring trading signals, performance, and market regimes
    """

    def __init__(self, config: Dict = None):
        """Initialize the dashboard"""
        self.config = config or {}
        self.signals = {}
        self.performance = {
            "total_pnl": 0,
            "win_rate": 0,
            "active_positions": 0,
            "realized_pnl": 0,
            "unrealized_pnl": 0,
        }
        self.trades = []
        self.market_data = {"regime": "unknown", "volatility": 0, "trend_strength": 0}
        self.alerts = []
        self.last_update = datetime.now()

        # Create log directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        self.log_file = "logs/dashboard.log"

        print("✅ Live Dashboard initialized")

    def update_signals(self, signals: Dict):
        """Update the trading signals"""
        self.signals = signals
        self.last_update = datetime.now()
        self._log_update("signals", signals)

    def update_performance(self, performance: Dict):
        """Update performance metrics"""
        self.performance.update(performance)
        self.last_update = datetime.now()
        self._log_update("performance", performance)

    def add_trade(self, trade: Dict):
        """Add a new trade to the history"""
        self.trades.append(trade)  # type: ignore

        # Update performance stats
        if trade.get("closed", False):
            # This is a closed trade
            pnl = trade.get("pnl", 0)
            self.performance["realized_pnl"] += pnl

            # Update win/loss count
            if pnl > 0:
                self.performance["wins"] = self.performance.get("wins", 0) + 1
            else:
                self.performance["losses"] = self.performance.get("losses", 0) + 1

            # Calculate win rate
            total_trades = self.performance.get("wins", 0) + self.performance.get("losses", 0)
            if total_trades > 0:
                self.performance["win_rate"] = self.performance.get("wins", 0) / total_trades
        else:
            # This is an open trade
            self.performance["active_positions"] += 1

        self._log_update("trade", trade)

    def update_market_data(self, data: Dict):
        """Update market regime and condition data"""
        self.market_data.update(data)
        self.last_update = datetime.now()
        self._log_update("market_data", data)

    def add_alert(self, alert: Dict):
        """Add a new alert"""
        alert["timestamp"] = datetime.now().isoformat()
        self.alerts.append(alert)  # type: ignore
        self._log_update("alert", alert)

    def display(self):
        """Display the dashboard in the console"""
        print("\n" + "=" * 80)
        print(f"📊 LIVE TRADING DASHBOARD | {self.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # Market regime info
        print(f"\n🌎 MARKET REGIME: {self._get_regime_emoji()} {self.market_data.get('regime', 'unknown').upper()}")
        print(f"  Volatility: {self.market_data.get('volatility', 0):.2%}")
        print(f"  Trend Strength: {self.market_data.get('trend_strength', 0):.2f}")

        # Active signals
        print("\n📡 TRADING SIGNALS:")
        for name, value in self.signals.items():
            indicator = "🟢" if value > 0.3 else "🔴" if value < -0.3 else "🟡"
            print(f"  {indicator} {name}: {value:.2f}")

        # Performance metrics
        print("\n💰 PERFORMANCE:")
        print(f"  Total P&L: ${self.performance.get('total_pnl', 0):+,.2f}")
        print(f"  Realized P&L: ${self.performance.get('realized_pnl', 0):+,.2f}")
        print(f"  Unrealized P&L: ${self.performance.get('unrealized_pnl', 0):+,.2f}")
        print(f"  Win Rate: {self.performance.get('win_rate', 0) * 100:.1f}%")
        print(f"  Active Positions: {self.performance.get('active_positions', 0)}")

        # Recent trades
        if self.trades:
            print("\n🔄 RECENT TRADES:")
            for trade in self.trades[-5:]:
                side = trade.get("side", "UNKNOWN")
                emoji = "🟢" if side == "BUY" else "🔴" if side == "SELL" else "⚪"
                print(
                    f"  {emoji} {trade.get('timestamp', 'N/A')}: {side} {trade.get('symbol', '')} - "
                    + f"Size: {trade.get('size', 0):.4f} @ ${trade.get('price', 0):,.2f}"
                )

        # Alerts
        if self.alerts:
            print("\n⚠️ ALERTS:")
            for alert in self.alerts[-3:]:
                print(f"  {alert.get('severity', '❗')} {alert.get('message', 'Unknown alert')}")

        print("=" * 80)

    def _get_regime_emoji(self) -> str:
        """Get appropriate emoji for market regime"""
        regime = self.market_data.get("regime", "").lower()
        if regime == "bull":
            return "🐂"
        elif regime == "bear":
            return "🐻"
        elif regime == "sideways":
            return "↔️"
        else:
            return "❓"

    def _log_update(self, update_type: str, data: Dict):
        """Log dashboard updates to file"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": update_type,
            "data": data,
        }

        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Warning: Could not write to dashboard log: {e}")

    def get_snapshot(self) -> Dict:
        """Get a complete snapshot of dashboard state"""
        return {
            "timestamp": datetime.now().isoformat(),
            "signals": self.signals,
            "performance": self.performance,
            "market_data": self.market_data,
            "recent_trades": self.trades[-10:] if self.trades else [],
            "alerts": self.alerts[-5:] if self.alerts else [],
        }

    def save_snapshot(self, filename: str = None):
        """Save dashboard snapshot to file"""
        if filename is None:
            filename = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(filename, "w") as f:
            json.dump(self.get_snapshot(), f, indent=2, default=str)

        print(f"✅ Dashboard snapshot saved to {filename}")

    def generate_report(self) -> str:
        """Generate a formatted report of current trading status"""
        report = f"""
        📊 TRADING STATUS REPORT
        ========================
        Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        MARKET CONDITIONS
        ----------------
        Regime: {self._get_regime_emoji()} {self.market_data.get("regime", "unknown").upper()}
        Volatility: {self.market_data.get("volatility", 0):.2%}
        Trend Strength: {self.market_data.get("trend_strength", 0):.2f}

        PERFORMANCE METRICS
        -----------------
        Total P&L: ${self.performance.get("total_pnl", 0):+,.2f}
        Realized P&L: ${self.performance.get("realized_pnl", 0):+,.2f}
        Win Rate: {self.performance.get("win_rate", 0) * 100:.1f}%
        Total Trades: {self.performance.get("wins", 0) + self.performance.get("losses", 0)}

        ACTIVE POSITIONS
        --------------
        Count: {self.performance.get("active_positions", 0)}
        Unrealized P&L: ${self.performance.get("unrealized_pnl", 0):+,.2f}
        """

        return report
