#!/usr/bin/env python3
"""
ENHANCED BOT PERFORMANCE MONITOR
Track your trading performance and budget metrics
"""

import os
import json
import time
from datetime import datetime

def monitor_performance():
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║   ENHANCED BOT PERFORMANCE MONITOR                    ║
    ║   Track trading metrics and budget performance        ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    budget_file = "budget_state.json"
    trades_file = "multi_signal_trades.json"
    
    while True:
        print(f"\n📊 Performance Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*60)
        
        # Check budget performance
        if os.path.exists(budget_file):
            try:
                with open(budget_file, "r") as f:
                    budget_data = json.load(f)
                
                performance = budget_data.get("performance", {})
                print("\n💰 BUDGET PERFORMANCE:")
                print(f"  Current Capital: ${performance.get('current_capital', 0):,.2f}")
                print(f"  Total P&L: ${performance.get('total_pnl', 0):+,.2f} ({performance.get('total_pnl_pct', 0):+.1f}%)")
                print(f"  Win Rate: {performance.get('win_rate', 0):.1f}%")
                print(f"  Current Drawdown: {performance.get('current_drawdown', 0):.1f}%")
            except Exception as e:
                print(f"⚠️ Error reading budget data: {e}")
        else:
            print("⚠️ No budget data available yet")
        
        # Check recent trades
        if os.path.exists(trades_file):
            try:
                with open(trades_file, "r") as f:
                    trades = json.load(f)
                
                if trades:
                    print("\n📈 RECENT TRADES:")
                    for trade in trades[-5:]:  # Show last 5 trades
                        print(f"  {trade.get('timestamp', '')}: {trade.get('symbol', '')} {trade.get('action', '')} @ ${trade.get('price', 0):,.2f}")
                else:
                    print("\n📈 No trades executed yet")
            except Exception as e:
                print(f"⚠️ Error reading trades data: {e}")
        else:
            print("\n📈 No trades data available yet")
        
        print("\n🔄 Refreshing in 60 seconds... (Ctrl+C to exit)")
        time.sleep(60)

if __name__ == "__main__":
    try:
        monitor_performance()
    except KeyboardInterrupt:
        print("\n✅ Monitoring stopped")
    