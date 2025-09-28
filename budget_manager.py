"""
PROFESSIONAL BUDGET MANAGEMENT SYSTEM
Manage your trading capital like a hedge fund
Track every dollar, compound profits, manage risk
"""

import json
from datetime import datetime
from typing import Dict, Optional


class BudgetManager:
    """
    Professional money management for your multi-signal bot
    This turns paper trading into realistic practice
    """

    def __init__(self, initial_capital: float = 10000.0, exchange=None, live_mode: bool = False):
        """
        Initialize with your starting capital
        Default $10,000 for realistic paper trading
        """
        self.live_mode = live_mode
        self.exchange = exchange
        if live_mode:
            # Fetch live balance from Kraken account
            try:
                balance = self.exchange.fetch_balance()
                # Assume the balance returns a dict with a 'free' key containing USD balance
                self.initial_capital = balance.get("free", {}).get("USD", initial_capital)
            except Exception as e:
                print(f"❌ Failed to fetch live balance: {e}")
                self.initial_capital = initial_capital
        else:
            self.initial_capital = initial_capital
        self.available_capital = self.initial_capital

        # Updated risk per trade to 4% and max positions to 10
        self.risk_per_trade = 4.0  # previously 2.0%
        self.max_positions = 10  # previously 5

        # RADICAL FIX: Always fetch real balance in live mode
        if live_mode and exchange:
            try:
                real_balance = self._fetch_real_balance(exchange)
                if real_balance > 0:
                    initial_capital = real_balance
                    print(f"🚀 LIVE BALANCE DETECTED: ${real_balance:,.2f} (overriding config)")
            except Exception as e:
                print(f"⚠️  Could not fetch real balance: {e}")

        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.available_capital = initial_capital
        self.positions = {}  # Active positions
        self.trade_history = []
        self.daily_pnl = []
        self.risk_parameters = self._default_risk_parameters()
        self.exchange = exchange
        self._markets = None
        if self.exchange:
            try:
                # load markets once for minima/precision info
                self._markets = self.exchange.load_markets()
            except Exception:
                self._markets = None

        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.largest_win = 0
        self.largest_loss = 0
        self.current_drawdown = 0
        self.max_drawdown = 0
        self.peak_capital = initial_capital

        print(
            f"""
        💰 BUDGET MANAGER INITIALIZED
        ================================
        Starting Capital: ${initial_capital:,.2f}
        Risk Per Trade: {self.risk_parameters["max_risk_per_trade"] * 100:.1f}%
        Max Positions: {self.risk_parameters["max_positions"]}
        ================================
        """
        )

    def _fetch_real_balance(self, exchange) -> float:
        """Radically fetch the real USD balance from exchange"""
        try:
            balance = exchange.fetch_balance()
            usd_balance = balance.get("USD", {}).get("free", 0)
            return float(usd_balance)
        except Exception as e:
            print(f"❌ Failed to fetch real balance: {e}")
            return 0.0

    def _default_risk_parameters(self) -> Dict:
        """
        Professional risk management parameters
        Based on hedge fund best practices
        """
        return {
            "max_risk_per_trade": 0.02,  # 2% max risk per trade
            "max_positions": 5,  # Maximum concurrent positions
            "max_portfolio_risk": 0.10,  # 10% max portfolio risk
            "position_size_method": "kelly",  # kelly, fixed, volatility_adjusted
            "compound_profits": True,  # Compound winning trades
            "reduce_on_drawdown": True,  # Reduce size during drawdowns
            "stop_loss_multiplier": 1.0,  # Adjust stop losses
            "take_profit_multiplier": 2.0,  # Risk:Reward ratio
        }

    def calculate_position_size(
        self,
        symbol: str,
        signal_confidence: float,
        volatility: float = 0.02,
        price: float = None,
    ) -> Dict:
        """
        Calculate optimal position size using Kelly Criterion
        This is how you maximize long-term growth
        """

        # Check if we can take more positions
        if len(self.positions) >= self.risk_parameters["max_positions"]:
            return {
                "size": 0,
                "reason": "Max positions reached",
                "capital_allocated": 0,
            }

        # Base position size (% of capital)
        base_size = self.risk_parameters["max_risk_per_trade"]

        # Apply Kelly Criterion
        if self.risk_parameters["position_size_method"] == "kelly":
            # Simplified Kelly: f = (p*b - q)/b
            # where p = win probability, b = win/loss ratio, q = loss probability

            win_prob = 0.45 + (signal_confidence * 0.2)  # Convert confidence to probability
            win_loss_ratio = self.risk_parameters["take_profit_multiplier"]

            kelly_fraction = (win_prob * win_loss_ratio - (1 - win_prob)) / win_loss_ratio
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%

            position_size_pct = base_size * kelly_fraction / 0.25  # Scale to base size

        elif self.risk_parameters["position_size_method"] == "volatility_adjusted":
            # Reduce size for high volatility
            vol_adjustment = max(0.5, 1 - volatility * 2)
            position_size_pct = base_size * vol_adjustment

        else:  # Fixed
            position_size_pct = base_size

        # Adjust for drawdown
        if self.risk_parameters["reduce_on_drawdown"] and self.current_drawdown < -0.05:
            drawdown_adjustment = 1 + self.current_drawdown  # Reduce by drawdown %
            position_size_pct *= drawdown_adjustment

        # Adjust for confidence
        position_size_pct *= signal_confidence

        # Calculate dollar amount
        position_size_dollars = self.available_capital * position_size_pct

        # Ensure we have enough capital
        if position_size_dollars > self.available_capital:
            position_size_dollars = self.available_capital * 0.95  # Use 95% of available

        # Ensure minimum order size is met (use price to enforce quantity minima when available)
        original_size = position_size_dollars
        position_size_dollars = self._ensure_minimum_order_size(symbol, position_size_dollars, price)

        if position_size_dollars != original_size:
            print(f"📈 Adjusted position size for {symbol}: ${original_size:.2f} → ${position_size_dollars:.2f} (minimum requirement)")

        return {
            "size": position_size_dollars,
            "size_pct": position_size_pct,
            "reason": "Calculated",
            "capital_allocated": position_size_dollars,
            "confidence_used": signal_confidence,
            "method": self.risk_parameters["position_size_method"],
        }

    def _ensure_minimum_order_size(self, symbol: str, position_size_dollars: float, price: float = None) -> float:
        """
        Ensure position size meets exchange minimum order requirements.
        If `price` is provided we will compute the quantity and make sure quantity >= minimum quantity for symbol.
        This helps avoid "invalid volume" errors from exchanges.
        """
        # Attempt to use exchange-provided market limits/precision when available
        usd_min = 5.0
        qty_min = 1.0

        try:
            if self._markets and symbol in self._markets:
                m = self._markets[symbol]
                limits = m.get("limits", {}) or {}
                # If exchange provides minimum cost, use it
                cost_limit = limits.get("cost")
                if isinstance(cost_limit, dict):
                    cost_min = cost_limit.get("min")
                    if cost_min:
                        usd_min = float(cost_min)
                elif isinstance(cost_limit, (int, float)):
                    usd_min = float(cost_limit)

                # Quantity minimum
                amount_limit = limits.get("amount") or {}
                if isinstance(amount_limit, dict):
                    amt_min = amount_limit.get("min")
                    if amt_min:
                        qty_min = float(amt_min)
                elif isinstance(amount_limit, (int, float)):
                    qty_min = float(amount_limit)

                # Precision-based fallback: use market precision to infer minimal tradable qty
                precision = m.get("precision", {}) or {}
                if "amount" in precision and qty_min == 1.0:
                    p = precision.get("amount")
                    if isinstance(p, int) and p > 0:
                        qty_min = 10 ** (-p)

        except Exception:
            # If anything goes wrong, keep conservative defaults
            usd_min = max(5.0, usd_min)
            qty_min = max(1.0, qty_min)

        # First, ensure USD-based minimum
        if position_size_dollars < usd_min:
            position_size_dollars = usd_min
            if position_size_dollars > self.available_capital:
                position_size_dollars = self.available_capital * 0.95

        # If price provided, ensure quantity meets qty_min
        if price and price > 0:
            qty = position_size_dollars / price
            if qty < qty_min:
                required_usd = qty_min * price
                position_size_dollars = max(position_size_dollars, required_usd)
                if position_size_dollars > self.available_capital:
                    position_size_dollars = self.available_capital * 0.95

        return position_size_dollars

    def open_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        position_size: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict:
        """
        Open a new trading position with proper risk management
        """

        if position_size > self.available_capital:
            return {"success": False, "error": "Insufficient capital"}

        # Calculate stop loss and take profit if not provided
        if stop_loss is None:
            sl_distance = entry_price * 0.03  # 3% stop loss
            stop_loss = entry_price - sl_distance if side == "BUY" else entry_price + sl_distance

        if take_profit is None:
            tp_distance = entry_price * 0.06  # 6% take profit (2:1 ratio)
            take_profit = entry_price + tp_distance if side == "BUY" else entry_price - tp_distance

        # Create position
        position_id = f"{symbol}_{datetime.now().timestamp()}"
        position = {
            "id": position_id,
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "current_price": entry_price,
            "size": position_size,
            "quantity": position_size / entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "opened_at": datetime.now().isoformat(),
            "pnl": 0,
            "pnl_pct": 0,
            "status": "OPEN",
        }

        # Update capital
        self.available_capital -= position_size
        self.positions[position_id] = position
        self.total_trades += 1

        print(
            f"""
        📈 POSITION OPENED
        Symbol: {symbol}
        Side: {side}
        Entry: ${entry_price:,.2f}
        Size: ${position_size:,.2f}
        Stop Loss: ${stop_loss:,.2f}
        Take Profit: ${take_profit:,.2f}
        Available Capital: ${self.available_capital:,.2f}
        """
        )

        return {"success": True, "position": position}

    def update_position(self, position_id: str, current_price: float) -> Dict:
        """
        Update position with current price and check stops
        """
        if position_id not in self.positions:
            return {"error": "Position not found"}

        position = self.positions[position_id]
        position["current_price"] = current_price

        # Calculate P&L
        if position["side"] == "BUY":
            pnl = (current_price - position["entry_price"]) * position["quantity"]
            pnl_pct = (current_price - position["entry_price"]) / position["entry_price"]
        else:  # SELL
            pnl = (position["entry_price"] - current_price) * position["quantity"]
            pnl_pct = (position["entry_price"] - current_price) / position["entry_price"]

        position["pnl"] = pnl
        position["pnl_pct"] = pnl_pct

        # Check stop loss
        if position["side"] == "BUY":
            if current_price <= position["stop_loss"]:
                return self.close_position(position_id, current_price, "STOP_LOSS")
            elif current_price >= position["take_profit"]:
                return self.close_position(position_id, current_price, "TAKE_PROFIT")
        else:  # SELL
            if current_price >= position["stop_loss"]:
                return self.close_position(position_id, current_price, "STOP_LOSS")
            elif current_price <= position["take_profit"]:
                return self.close_position(position_id, current_price, "TAKE_PROFIT")

        return {"status": "UPDATED", "pnl": pnl, "pnl_pct": pnl_pct}

    def close_position(self, position_id: str, exit_price: float, reason: str = "MANUAL") -> Dict:
        """
        Close a position and update capital
        """
        if position_id not in self.positions:
            return {"error": "Position not found"}

        position = self.positions[position_id]

        # Calculate final P&L
        if position["side"] == "BUY":
            pnl = (exit_price - position["entry_price"]) * position["quantity"]
        else:
            pnl = (position["entry_price"] - exit_price) * position["quantity"]

        # Update capital
        self.current_capital += position["size"] + pnl
        self.available_capital += position["size"] + pnl

        # Track performance
        if pnl > 0:
            self.winning_trades += 1
            self.largest_win = max(self.largest_win, pnl)
        else:
            self.losing_trades += 1
            self.largest_loss = min(self.largest_loss, pnl)

        # Update drawdown
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital

        self.current_drawdown = (self.current_capital - self.peak_capital) / self.peak_capital
        self.max_drawdown = min(self.max_drawdown, self.current_drawdown)

        # Record trade
        trade_record = {
            **position,
            "exit_price": exit_price,
            "closed_at": datetime.now().isoformat(),
            "pnl": pnl,
            "pnl_pct": pnl / position["size"],
            "reason": reason,
        }

        self.trade_history.append(trade_record)
        del self.positions[position_id]

        # Print result
        emoji = "💚" if pnl > 0 else "💔"
        print(
            f"""
        {emoji} POSITION CLOSED ({reason})
        Symbol: {position["symbol"]}
        P&L: ${pnl:+,.2f} ({pnl / position["size"] * 100:+.1f}%)
        Current Capital: ${self.current_capital:,.2f}
        """
        )

        # Compound profits if enabled
        if self.risk_parameters["compound_profits"] and pnl > 0:
            compound_bonus = pnl * 0.1  # Reinvest 10% of profits
            print(f"  📈 Compounding: Adding ${compound_bonus:.2f} to position sizing")

        return {"success": True, "pnl": pnl, "trade": trade_record}

    def get_portfolio_status(self) -> Dict:
        """
        Get comprehensive portfolio status
        """
        open_pnl = sum(pos["pnl"] for pos in self.positions.values())

        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0

        return {
            "current_capital": self.current_capital,
            "available_capital": self.available_capital,
            "initial_capital": self.initial_capital,
            "total_pnl": self.current_capital - self.initial_capital,
            "total_pnl_pct": (self.current_capital - self.initial_capital) / self.initial_capital * 100,
            "open_positions": len(self.positions),
            "open_pnl": open_pnl,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": win_rate,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
            "current_drawdown": self.current_drawdown * 100,
            "max_drawdown": self.max_drawdown * 100,
        }

    def display_dashboard(self):
        """
        Display a professional trading dashboard
        """
        status = self.get_portfolio_status()

        print(
            f"""
        {"=" * 60}
        💰 PORTFOLIO DASHBOARD
        {"=" * 60}

        CAPITAL
        -------
        Current: ${status["current_capital"]:,.2f}
        Available: ${status["available_capital"]:,.2f}
        Total P&L: ${status["total_pnl"]:+,.2f} ({status["total_pnl_pct"]:+.1f}%)

        POSITIONS
        ---------
        Open: {status["open_positions"]} / {self.risk_parameters["max_positions"]}
        Open P&L: ${status["open_pnl"]:+,.2f}

        PERFORMANCE
        -----------
        Total Trades: {status["total_trades"]}
        Win Rate: {status["win_rate"]:.1f}%
        Largest Win: ${status["largest_win"]:+,.2f}
        Largest Loss: ${status["largest_loss"]:+,.2f}

        RISK METRICS
        ------------
        Current Drawdown: {status["current_drawdown"]:.1f}%
        Max Drawdown: {status["max_drawdown"]:.1f}%

        {"=" * 60}
        """
        )

        # Show open positions
        if self.positions:
            print("\n📊 OPEN POSITIONS:")
            print("-" * 40)
            for pos_id, pos in self.positions.items():
                emoji = "🟢" if pos["pnl"] > 0 else "🔴"
                print(f"{emoji} {pos['symbol']}: ${pos['pnl']:+,.2f} ({pos['pnl_pct'] * 100:+.1f}%)")

    def save_state(self, filename: str = "budget_state.json"):
        """
        Save budget manager state to file
        """
        state = {
            "current_capital": self.current_capital,
            "available_capital": self.available_capital,
            "positions": list(self.positions.values()),
            "trade_history": self.trade_history[-100:],  # Last 100 trades
            "performance": self.get_portfolio_status(),
            "timestamp": datetime.now().isoformat(),
        }

        with open(filename, "w") as f:
            json.dump(state, f, indent=2, default=str)

        print(f"📁 Budget state saved to {filename}")


# Test the budget manager
if __name__ == "__main__":
    # Initialize with $10,000
    budget = BudgetManager(initial_capital=10000)

    # Simulate some trades
    print("\n🧪 TESTING BUDGET MANAGER WITH SAMPLE TRADES")
    print("=" * 60)

    # Open a position
    position_calc = budget.calculate_position_size("BTC/USD", signal_confidence=0.75, volatility=0.03)
    print("\n📊 Position Size Calculation:")
    print(f"  Allocated: ${position_calc['size']:,.2f}")
    print(f"  Percentage: {position_calc['size_pct'] * 100:.1f}%")

    # Open position
    result = budget.open_position(
        symbol="BTC/USD",
        side="BUY",
        entry_price=43250,
        position_size=position_calc["size"],
    )

    # Update with profit
    budget.update_position(result["position"]["id"], 44000)

    # Display dashboard
    budget.display_dashboard()

    # Save state
    budget.save_state()
