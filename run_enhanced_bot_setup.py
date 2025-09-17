#!/usr/bin/env python3
"""
INTEGRATE VOLATILE CRYPTOS + BUDGET MANAGER
Complete setup for your enhanced multi-signal bot
"""

import json
import os
import sys
from src.crypto_selector import VolatileCryptoSelector
from src.budget_manager import BudgetManager

def setup_enhanced_trading():
    """
    Set up your bot with volatile cryptos and budget management
    """
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║   ENHANCED MULTI-SIGNAL BOT SETUP                     ║
    ║   Adding: Volatile Cryptos + Budget Management        ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    # Step 1: Get top volatile cryptos
    print("\n📊 STEP 1: Finding Most Volatile Cryptos")
    print("-"*50)
    
    selector = VolatileCryptoSelector()
    top_cryptos = selector.get_top_volatile_cryptos(top_n=5)
    
    # Step 2: Initialize budget manager
    print("\n💰 STEP 2: Setting Up Budget Manager")
    print("-"*50)
    
    initial_capital = 10000  # $10,000 paper trading capital
    budget = BudgetManager(initial_capital=initial_capital)
    
    # Step 3: Create integrated configuration
    print("\n🔧 STEP 3: Creating Integrated Configuration")
    print("-"*50)
    
    config = {
        'trading_pairs': top_cryptos,
        'budget': {
            'initial_capital': initial_capital,
            'risk_parameters': budget.risk_parameters
        },
        'signals': [
            'RSI', 'MACD', 'Bollinger', 'Volume', 'Sentiment',
            'Whale_Tracking', 'Exchange_Flows', 'Order_Flow', 'Fear_Greed'
        ],
        'position_sizing': {
            'method': 'kelly',
            'base_risk': 0.02,
            'max_positions': 5
        },
        'trading_rules': {
            'min_confidence': 0.6,
            'stop_loss': 0.03,
            'take_profit': 0.06,
            'compound_profits': True
        }
    }
    
    # Save configuration
    with open('enhanced_bot_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    # Also update the main config.yaml file with new settings
    update_main_config(top_cryptos, initial_capital)
    
    print("\n✅ SETUP COMPLETE!")
    print(f"\n📋 SUMMARY:")
    print(f"  Trading Pairs: {', '.join(top_cryptos)}")
    print(f"  Initial Capital: ${initial_capital:,}")
    print(f"  Risk Per Trade: {config['position_sizing']['base_risk']*100}%")
    print(f"  Max Positions: {config['position_sizing']['max_positions']}")
    print(f"  Total Signals: {len(config['signals'])}")
    
    print("\n🚀 YOUR BOT IS NOW ENHANCED WITH:")
    print("  ✅ Top 5 most volatile cryptos for maximum opportunity")
    print("  ✅ Professional budget management system")
    print("  ✅ Real dollar tracking (paper money)")
    print("  ✅ Position sizing with Kelly Criterion")
    print("  ✅ Profit compounding for growth")
    
    return config, budget

def update_main_config(crypto_symbols, initial_capital):
    """Update the main config.yaml with new settings"""
    try:
        import yaml
        
        config_path = "config.yaml"
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            
            # Update with new settings
            config["symbols"] = crypto_symbols
            config["initial_capital"] = initial_capital
            config["budget_management"] = {
                "max_risk_per_trade": 0.02,
                "max_positions": 5,
                "position_size_method": "kelly",
                "compound_profits": True,
                "reduce_on_drawdown": True
            }
            
            # Save updated config
            with open(config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False)
                
            print(f"✅ Updated main config.yaml with new settings")
        else:
            print(f"⚠️ Couldn't find {config_path} to update")
    except Exception as e:
        print(f"⚠️ Error updating config.yaml: {e}")

def create_monitor_script():
    """Create a simple performance monitoring script"""
    monitor_code = """#!/usr/bin/env python3
\"\"\"
ENHANCED BOT PERFORMANCE MONITOR
Track your trading performance and budget metrics
\"\"\"

import os
import json
import time
from datetime import datetime

def monitor_performance():
    print(\"\"\"
    ╔════════════════════════════════════════════════════════╗
    ║   ENHANCED BOT PERFORMANCE MONITOR                    ║
    ║   Track trading metrics and budget performance        ║
    ╚════════════════════════════════════════════════════════╝
    \"\"\")
    
    budget_file = "budget_state.json"
    trades_file = "multi_signal_trades.json"
    
    while True:
        print(f"\\n📊 Performance Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*60)
        
        # Check budget performance
        if os.path.exists(budget_file):
            try:
                with open(budget_file, "r") as f:
                    budget_data = json.load(f)
                
                performance = budget_data.get("performance", {})
                print("\\n💰 BUDGET PERFORMANCE:")
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
                    print("\\n📈 RECENT TRADES:")
                    for trade in trades[-5:]:  # Show last 5 trades
                        print(f"  {trade.get('timestamp', '')}: {trade.get('symbol', '')} {trade.get('action', '')} @ ${trade.get('price', 0):,.2f}")
                else:
                    print("\\n📈 No trades executed yet")
            except Exception as e:
                print(f"⚠️ Error reading trades data: {e}")
        else:
            print("\\n📈 No trades data available yet")
        
        print("\\n🔄 Refreshing in 60 seconds... (Ctrl+C to exit)")
        time.sleep(60)

if __name__ == "__main__":
    try:
        monitor_performance()
    except KeyboardInterrupt:
        print("\\n✅ Monitoring stopped")
    """
    
    with open("monitor_performance.py", "w") as f:
        f.write(monitor_code)
    
    # Make it executable
    os.chmod("monitor_performance.py", 0o755)
    print("✅ Created monitor_performance.py")

if __name__ == "__main__":
    config, budget = setup_enhanced_trading()
    
    # Create the monitoring script
    create_monitor_script()
    
    print("\n💡 NEXT STEPS:")
    print("1. Restart your paper trading bot with new config:")
    print("   $ python multi_signal_bot.py")
    print("2. Monitor using: python monitor_performance.py")
    print("3. Track budget using: python budget_manager.py")
    print("4. Optimize after 24 hours of data")