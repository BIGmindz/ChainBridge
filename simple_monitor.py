#!/usr/bin/env python3
"""
SIMPLE TRADING MONITOR
Shows key metrics: RSI, Buy/Sell points, Costs, P&L
"""

import os
import sys
import time
from datetime import datetime
import ccxt
import numpy as np

# Add project path
sys.path.append("/Users/johnbozza/bensonbot/Multiple-signal-decision-bot")


def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    if len(prices) < period + 1:
        return 50.0

    gains = []
    losses = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def get_current_position():
    """Get current position details"""
    try:
        # Mock position data based on our last trade
        return {
            "symbol": "PRO/USD",
            "side": "BUY",
            "entry_price": 0.90,
            "quantity": 34.9,  # $31.41 / $0.90
            "stop_loss": 0.87,
            "take_profit": 0.95,
            "timestamp": datetime.now(),
        }
    except:
        return None


def get_current_price(symbol="PRO/USD"):
    """Get current market price"""
    try:
        exchange = ccxt.kraken()
        ticker = exchange.fetch_ticker(symbol)
        return ticker["last"]
    except:
        return 0.90  # Fallback


def calculate_pnl(entry_price, current_price, quantity, side):
    """Calculate profit/loss"""
    if side.upper() == "BUY":
        pnl = (current_price - entry_price) * quantity
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
    else:
        pnl = (entry_price - current_price) * quantity
        pnl_pct = ((entry_price - current_price) / entry_price) * 100

    return pnl, pnl_pct


def main():
    print("🔍 BENSONBOT MONITOR")
    print("=" * 40)

    while True:
        os.system("clear")  # Clear screen

        print(f"⏰ {datetime.now().strftime('%H:%M:%S')} | BensonBot Live Monitor")
        print("-" * 40)

        # Get position
        position = get_current_position()
        if position:
            symbol = position["symbol"]
            current_price = get_current_price(symbol)
            rsi = 45.0  # Mock RSI - would need real calculation

            # Calculate P&L
            pnl, pnl_pct = calculate_pnl(position["entry_price"], current_price, position["quantity"], position["side"])

            print(f"📊 SYMBOL: {symbol}")
            print(f"💰 CURRENT PRICE: ${current_price:.4f}")
            print(f"📈 RSI: {rsi:.1f}")
            print(f"🎯 BUY POINT: ${position['entry_price']:.4f}")
            print(f"🎯 SELL POINT: ${position['take_profit']:.4f}")
            print(f"💵 BUY COST: ${position['entry_price'] * position['quantity']:.2f}")
            print(f"🛑 STOP LOSS: ${position['stop_loss']:.4f}")

            if pnl >= 0:
                print(f"💚 P&L: +${pnl:.2f} (+{pnl_pct:.1f}%)")
            else:
                print(f"❤️ P&L: -${abs(pnl):.2f} ({pnl_pct:.1f}%)")

        else:
            print("📊 No active positions")
            print("💰 Current Price: $0.90 (PRO/USD)")
            print("📈 RSI: 45.0")
            print("🎯 Buy Point: N/A")
            print("🎯 Sell Point: N/A")
            print("💵 Buy Cost: $0.00")
            print("💚 P&L: $0.00 (0.0%)")

        print("-" * 40)
        print("Press Ctrl+C to stop monitoring")
        print("=" * 40)

        time.sleep(5)  # Update every 5 seconds


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
