#!/usr/bin/env python3
"""
Simple Kraken Paper Trading Demo (No External Dependencies)
==========================================================

Simplified demonstration of the Kraken paper trading capabilities
without requiring websockets or other external dependencies.

This shows the core functionality in a basic environment.

Author: BIGmindz
Version: 1.0.0
"""

import json
from datetime import datetime, timezone


# Simple mock classes for demo
class MockBudgetManager:
    def __init__(self, initial_capital=10000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.available_capital = initial_capital
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        print(f"💰 BudgetManager initialized with ${initial_capital:,.2f}")

    def calculate_position_size(self, symbol, confidence, volatility):
        # Simple position sizing: 5% of available capital
        size = self.available_capital * 0.05 * confidence
        return {"size": size, "size_pct": size / self.initial_capital}

    def open_position(self, **kwargs):
        position_id = f"pos_{int(datetime.now().timestamp())}"
        return {
            "success": True,
            "position": {
                "id": position_id,
                "symbol": kwargs["symbol"],
                "side": kwargs["side"],
                "entry_price": kwargs["entry_price"],
                "stop_loss": kwargs.get("stop_loss"),
                "take_profit": kwargs.get("take_profit"),
            },
        }

    def close_position(self, position_id, price, reason):
        return {"success": True, "reason": reason}


class MockPriceData:
    def __init__(self, symbol, price):
        self.symbol = symbol
        self.price = price
        self.bid = price * 0.999
        self.ask = price * 1.001
        self.volume_24h = 1000000
        self.timestamp = datetime.now(timezone.utc)
        self.spread = self.ask - self.bid


class MockPosition:
    def __init__(
        self,
        position_id,
        symbol,
        side,
        entry_price,
        quantity,
        stop_loss=None,
        take_profit=None,
    ):
        self.id = position_id
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.current_price = entry_price
        self.quantity = quantity
        self.entry_time = datetime.now(timezone.utc)
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.pnl = 0.0
        self.pnl_pct = 0.0
        self.max_pnl = 0.0
        self.max_drawdown = 0.0
        self.tags = []

    def update_price(self, new_price):
        self.current_price = new_price
        if self.side == "BUY":
            self.pnl = (new_price - self.entry_price) * self.quantity
            self.pnl_pct = (new_price - self.entry_price) / self.entry_price
        else:
            self.pnl = (self.entry_price - new_price) * self.quantity
            self.pnl_pct = (self.entry_price - new_price) / self.entry_price

        if self.pnl > self.max_pnl:
            self.max_pnl = self.pnl


class SimplePaperTradingBot:
    """
    Simplified version of the Kraken paper trading bot for demo purposes
    """

    def __init__(self, config):
        self.config = config
        self.budget_manager = MockBudgetManager(config.get("initial_capital", 10000.0))
        self.positions = {}
        self.price_data = {}
        self.trade_journal = []
        self.performance_stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
        }

        print("🤖 SimplePaperTradingBot initialized")
        print(f"   Capital: ${self.budget_manager.initial_capital:,.2f}")
        print(f"   Symbols: {config.get('symbols', [])}")

    def update_price(self, symbol, price):
        """Update price for a symbol"""
        self.price_data[symbol] = MockPriceData(symbol, price)

        # Update positions
        for pos in self.positions.values():
            if pos.symbol == symbol:
                pos.update_price(price)

    def open_position(
        self,
        symbol,
        side,
        signal_confidence,
        volatility=0.03,
        stop_loss_pct=0.03,
        take_profit_pct=0.06,
        tags=None,
    ):
        """Open a trading position"""
        if symbol not in self.price_data:
            return {"success": False, "error": f"No price data for {symbol}"}

        current_price = self.price_data[symbol].price

        # Calculate position size
        pos_calc = self.budget_manager.calculate_position_size(
            symbol, signal_confidence, volatility
        )

        if pos_calc["size"] <= 0:
            return {"success": False, "error": "Invalid position size"}

        # Calculate stops
        if side == "BUY":
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + take_profit_pct)
        else:
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - take_profit_pct)

        # Create position
        position_id = f"pos_{int(datetime.now().timestamp())}"
        quantity = pos_calc["size"] / current_price

        position = MockPosition(
            position_id=position_id,
            symbol=symbol,
            side=side,
            entry_price=current_price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        position.tags = tags or []
        self.positions[position_id] = position

        # Log trade
        trade_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "OPEN",
            "position_id": position_id,
            "symbol": symbol,
            "side": side,
            "entry_price": current_price,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "signal_confidence": signal_confidence,
            "tags": tags,
        }

        self.trade_journal.append(trade_log)  # type: ignore

        print(f"✅ Position opened: {side} {symbol} @ ${current_price:.2f}")
        print(
            f"   Size: ${pos_calc['size']:.2f} ({quantity:.6f} {symbol.split('/')[0]})"
        )
        print(f"   Stop Loss: ${stop_loss:.2f}")
        print(f"   Take Profit: ${take_profit:.2f}")

        return {"success": True, "position_id": position_id, "position": position}

    def close_position(self, position_id, reason="MANUAL"):
        """Close a position"""
        if position_id not in self.positions:
            return {"success": False, "error": "Position not found"}

        position = self.positions[position_id]
        current_price = self.price_data[position.symbol].price

        # Final P&L calculation
        position.update_price(current_price)

        # Update performance stats
        self.performance_stats["total_trades"] += 1
        self.performance_stats["total_pnl"] += position.pnl

        if position.pnl > 0:
            self.performance_stats["winning_trades"] += 1
            if position.pnl > self.performance_stats["largest_win"]:
                self.performance_stats["largest_win"] = position.pnl
        else:
            self.performance_stats["losing_trades"] += 1
            if abs(position.pnl) > self.performance_stats["largest_loss"]:
                self.performance_stats["largest_loss"] = abs(position.pnl)

        # Log trade closure
        trade_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "CLOSE",
            "position_id": position_id,
            "symbol": position.symbol,
            "side": position.side,
            "entry_price": position.entry_price,
            "exit_price": current_price,
            "quantity": position.quantity,
            "pnl": position.pnl,
            "pnl_pct": position.pnl_pct * 100,
            "reason": reason,
        }

        self.trade_journal.append(trade_log)  # type: ignore

        print(f"🔄 Position closed: {position.symbol} {position.side}")
        print(f"   Entry: ${position.entry_price:.2f} → Exit: ${current_price:.2f}")
        print(
            f"   P&L: ${position.pnl:+.2f} ({position.pnl_pct * 100:+.2f}%) - {reason}"
        )

        # Remove from active positions
        del self.positions[position_id]

        return {"success": True, "position": position, "pnl": position.pnl}

    def get_portfolio_summary(self):
        """Get portfolio summary"""
        portfolio_value = self.budget_manager.current_capital
        for pos in self.positions.values():
            portfolio_value += pos.pnl

        total_return = portfolio_value - self.budget_manager.initial_capital
        total_return_pct = (total_return / self.budget_manager.initial_capital) * 100

        win_rate = 0
        if self.performance_stats["total_trades"] > 0:
            win_rate = (
                self.performance_stats["winning_trades"]
                / self.performance_stats["total_trades"]
            ) * 100

        return {
            "initial_capital": self.budget_manager.initial_capital,
            "portfolio_value": portfolio_value,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "active_positions": len(self.positions),
            "total_trades": self.performance_stats["total_trades"],
            "win_rate": win_rate,
            "largest_win": self.performance_stats["largest_win"],
            "largest_loss": self.performance_stats["largest_loss"],
        }

    def export_trade_journal(self, filename=None):
        """Export trade journal to JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"simple_paper_trade_journal_{timestamp}.json"

        export_data = {
            "metadata": {
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "bot_version": "Simple 1.0",
                "initial_capital": self.budget_manager.initial_capital,
            },
            "performance_summary": self.get_portfolio_summary(),
            "trade_history": self.trade_journal,
            "active_positions": [
                {
                    "id": pos.id,
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "entry_price": pos.entry_price,
                    "current_price": pos.current_price,
                    "pnl": pos.pnl,
                    "pnl_pct": pos.pnl_pct * 100,
                }
                for pos in self.positions.values()
            ],
        }

        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        return filename


def demo_simple_paper_trading():
    """Demonstrate simple paper trading functionality"""
    print("🎯 SIMPLE KRAKEN PAPER TRADING DEMO")
    print("=" * 50)

    # Configuration
    config = {
        "initial_capital": 10000.0,
        "symbols": ["BTC/USD", "ETH/USD", "ADA/USD"],
        "risk_management": {"max_position_size": 0.1},
    }

    # Create bot
    bot = SimplePaperTradingBot(config)

    # Set initial prices
    prices = {"BTC/USD": 45000.0, "ETH/USD": 3200.0, "ADA/USD": 0.45}
    print("\n📊 Initial Prices:")
    for symbol, price in prices.items():
        bot.update_price(symbol, price)
        print(f"   {symbol}: ${price:,.4f}")

    # Demo trading sequence
    print("\n🎯 Opening positions...")

    # Open BTC position
    _btc_result = bot.open_position(
        symbol="BTC/USD",
        side="BUY",
        signal_confidence=0.8,
        tags=["demo", "high_confidence"],
    )

    # Open ETH position
    _eth_result = bot.open_position(
        symbol="ETH/USD",
        side="BUY",
        signal_confidence=0.65,
        tags=["demo", "medium_confidence"],
    )

    # Try to open ADA position with low confidence
    _ada_result = bot.open_position(
        symbol="ADA/USD",
        side="SELL",
        signal_confidence=0.7,
        tags=["demo", "short_position"],
    )

    # Show initial portfolio
    print("\n📈 Initial Portfolio:")
    summary = bot.get_portfolio_summary()
    print(f"   Portfolio Value: ${summary['portfolio_value']:,.2f}")
    print(f"   Active Positions: {summary['active_positions']}")

    # Simulate price movements
    print("\n📈 Simulating price movements...")

    # BTC up 5%
    new_btc = prices["BTC/USD"] * 1.05
    bot.update_price("BTC/USD", new_btc)
    print(f"   BTC: ${prices['BTC/USD']:,.2f} → ${new_btc:,.2f} (+5%)")

    # ETH down 3%
    new_eth = prices["ETH/USD"] * 0.97
    bot.update_price("ETH/USD", new_eth)
    print(f"   ETH: ${prices['ETH/USD']:,.2f} → ${new_eth:,.2f} (-3%)")

    # ADA up 8% (good for our short)
    new_ada = prices["ADA/USD"] * 1.08
    bot.update_price("ADA/USD", new_ada)
    print(f"   ADA: ${prices['ADA/USD']:,.4f} → ${new_ada:.4f} (+8%)")

    # Show updated portfolio
    print("\n📊 Updated Portfolio:")
    summary = bot.get_portfolio_summary()
    print(f"   Portfolio Value: ${summary['portfolio_value']:,.2f}")
    print(
        f"   Total Return: ${summary['total_return']:+,.2f} ({summary['total_return_pct']:+.2f}%)"
    )

    # Show position details
    print("\n💼 Position Details:")
    for pos in bot.positions.values():
        print(
            f"   {pos.symbol} {pos.side}: ${pos.pnl:+,.2f} ({pos.pnl_pct * 100:+.2f}%)"
        )

    # Close positions
    print("\n🔄 Closing all positions...")
    position_ids = list(bot.positions.keys())  # type: ignore
    for pos_id in position_ids:
        bot.close_position(pos_id, "DEMO_END")

    # Final summary
    print("\n📋 FINAL SUMMARY")
    print("-" * 30)
    summary = bot.get_portfolio_summary()
    print(f"Initial Capital: ${summary['initial_capital']:,.2f}")
    print(f"Final Portfolio: ${summary['portfolio_value']:,.2f}")
    print(
        f"Total Return: ${summary['total_return']:+,.2f} ({summary['total_return_pct']:+.2f}%)"
    )
    print(f"Total Trades: {summary['total_trades']}")
    print(f"Win Rate: {summary['win_rate']:.1f}%")
    print(f"Largest Win: ${summary['largest_win']:,.2f}")
    print(f"Largest Loss: ${summary['largest_loss']:,.2f}")

    # Export journal
    journal_path = bot.export_trade_journal()
    print(f"\n📄 Trade journal exported to: {journal_path}")

    return bot


def main():
    """Main demo function"""
    try:
        print("🚀 SIMPLIFIED KRAKEN PAPER TRADING DEMONSTRATION")
        print("=" * 60)
        print("This demo shows core paper trading functionality without")
        print("external dependencies like websockets or ccxt.")
        print("=" * 60)

        # Run demo
        _bot = demo_simple_paper_trading()

        print("\n✅ Demo completed successfully!")
        print("\nKey features demonstrated:")
        print("  ✅ Position opening with confidence-based sizing")
        print("  ✅ Real-time P&L calculation")
        print("  ✅ Stop loss and take profit setting")
        print("  ✅ Performance tracking")
        print("  ✅ Trade journal export")
        print("  ✅ Portfolio summary reporting")

        print("\n🎯 This simplified version demonstrates the core concepts")
        print("   that are fully implemented in the complete Kraken module!")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    main()
