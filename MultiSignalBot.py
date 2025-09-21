#!/usr/bin/env python3
"""
MultiSignalBot - Clean Live Trading Version
"""

import os
import sys
import time
from datetime import datetime

# Set PAPER mode before imports
os.environ["PAPER"] = "false"

# Add path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.trading_mode import TradingMode
from budget_manager import BudgetManager
from src.data_provider import setup_exchange, validate_symbols
from src.exchange_adapter import ExchangeAdapter

class MultiSignalBot:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.trading_mode = TradingMode()
        
        # Load config
        self.cfg = self._load_config()
        
        # Setup exchange
        self.exchange = setup_exchange("kraken", {})
        
        # Load symbols
        self.symbols = self.cfg.get("symbols", ["WIF/USD", "DOGE/USD", "NEAR/USD", "SOL/USD", "PEPE/USD"])
        validate_symbols(self.exchange, self.symbols)
        
        # Initialize budget manager
        self.initial_capital = float(self.cfg.get("initial_capital", 10000.0))
        self.budget_manager = BudgetManager(
            initial_capital=self.initial_capital,
            exchange=self.exchange,
            live_mode=not self.trading_mode.is_paper_trading
        )
        
        # Initialize exchange adapter
        self.exchange_adapter = ExchangeAdapter(
            exchange=self.exchange,
            paper_mode=self.trading_mode.is_paper_trading,
            budget_manager=self.budget_manager
        )
        
        print("🚀 MultiSignalBot initialized!")
        print(f"💰 Initial Capital: ${self.initial_capital}")
        print(f"🎯 Trading Mode: {'LIVE' if not self.trading_mode.is_paper_trading else 'PAPER'}")
        print(f"📊 Symbols: {', '.join(self.symbols)}")
    
    def _load_config(self):
        import yaml
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def run_once(self):
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Running trading cycle...")
        
        for symbol in self.symbols:
            try:
                # Get market data
                ticker = self.exchange.fetch_ticker(symbol)
                print(f"📊 {symbol}: ${ticker['last']:.4f}")
                
                # Simple signal logic (for demo)
                if ticker['last'] > ticker['open'] * 1.001:  # Simple uptrend
                    signal = "BUY"
                elif ticker['last'] < ticker['open'] * 0.999:  # Simple downtrend
                    signal = "SELL"
                else:
                    signal = "HOLD"
                
                print(f"🎯 {symbol}: {signal}")
                
                # Execute trade if signal is strong
                if signal != "HOLD":
                    self._execute_trade(symbol, signal, ticker['last'])
                    
            except Exception as e:
                print(f"❌ Error with {symbol}: {e}")
        
        print("✅ Cycle completed")
    
    def _execute_trade(self, symbol, signal, price):
        try:
            # Simple position sizing
            position_size = self.initial_capital * 0.02 / price  # 2% of capital
            
            if position_size > 0:
                order = self.exchange_adapter.place_order(
                    symbol=symbol,
                    side=signal.lower(),
                    amount=position_size,
                    price=price
                )
                
                if order:
                    print(f"📈 {signal} {symbol} at ${price} (Size: {position_size:.4f})")
                    
        except Exception as e:
            print(f"❌ Trade error: {e}")

def main():
    print("🔥 LIVE TRADING BOT STARTING...")
    print("⚠️  PAPER=false - REAL ORDERS WILL BE PLACED!")
    
    bot = MultiSignalBot()
    
    while True:
        try:
            bot.run_once()
            time.sleep(60)  # 1 minute cycles
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    main()
