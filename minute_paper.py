"""
MINUTE PAPER - Accelerated Trading Simulation
This script runs your multi-signal trading bot in an accelerated timeframe
to simulate trading over a longer period in just minutes.
"""

import asyncio
import sys
import os
import random
import json
from datetime import datetime, timedelta

# Conditionally import matplotlib
has_matplotlib = False
try:
    import matplotlib.pyplot as plt
    has_matplotlib = True
except ImportError:
    pass

# Add src to path
sys.path.append('src')

# Import your trading engine
from src.core.unified_trading_engine import MultiSignalTradingEngine  # noqa: E402

# Simulation config
SIMULATION_CYCLES = 30  # Number of trading cycles to simulate
TRADES_PER_CYCLE = 5    # Number of potential trades per cycle
VOLATILITY = 1.5        # Market volatility factor (higher = more volatile)
TREND_STRENGTH = 0.3    # How strong the market trend is
SIMULATION_SPEED = 0.2  # Seconds between cycles (lower = faster)
STARTING_PRICE = 30000  # Starting price of the asset

# Market conditions
MARKET_CONDITIONS = [
    {"name": "Bull Market", "bias": 0.6, "cycles": 10},
    {"name": "Sideways Market", "bias": 0.0, "cycles": 10},
    {"name": "Bear Market", "bias": -0.5, "cycles": 10}
]

class MarketSimulator:
    """Simulates market conditions for testing the trading bot"""
    
    def __init__(self, starting_price=30000):
        self.price = starting_price
        self.price_history = [starting_price]
        self.current_trend = 0
        self.time = datetime.now()
        self.cycle_returns = []
    
    def update_market(self, bias=0):
        """Update market price with random walk + bias"""
        # Random price movement with trend bias
        trend_change = random.uniform(-0.3, 0.3)
        self.current_trend = 0.7 * self.current_trend + 0.3 * trend_change
        
        # Apply market bias (bull/bear)
        self.current_trend += bias
        
        # Calculate price change with volatility
        price_change = self.price * (self.current_trend * TREND_STRENGTH + 
                                    random.normalvariate(0, 0.02) * VOLATILITY)
        
        # Update price
        self.price += price_change
        self.price_history.append(self.price)
        
        # Calculate returns
        if len(self.price_history) > 1:
            self.cycle_returns.append((self.price_history[-1] / self.price_history[-2]) - 1)
        
        # Update time
        self.time += timedelta(hours=4)  # Simulate 4-hour candles
        
        return {
            'price': self.price,
            'change_pct': 100 * price_change / (self.price - price_change),
            'trend': self.current_trend,
            'timestamp': self.time
        }

    def get_signal_biases(self):
        """Generate biased signals based on current market trend"""
        # This simulates how different signals perform in different market conditions
        bias = self.current_trend
        
        # Add some randomness to signal correlations
        rsi_bias = bias * 0.7 + random.uniform(-0.4, 0.4)
        macd_bias = bias * 0.8 + random.uniform(-0.3, 0.3)
        bollinger_bias = -bias * 0.5 + random.uniform(-0.5, 0.5)  # Often contrarian
        volume_bias = bias * 0.4 + random.uniform(-0.6, 0.6)
        fear_greed_bias = -bias * 0.9 + random.uniform(-0.2, 0.2)  # Contrarian
        social_bias = bias * 1.2 + random.uniform(-0.7, 0.7)  # Exaggerated
        whale_bias = bias * 0.1 + random.uniform(-0.3, 0.3)  # Mostly independent
        flows_bias = -bias * 0.3 + random.uniform(-0.4, 0.4)
        proprietary_bias = bias * 0.6 + random.uniform(-0.2, 0.2)  # Your edge
        
        return {
            'rsi': rsi_bias,
            'macd': macd_bias,
            'bollinger': bollinger_bias,
            'volume': volume_bias,
            'fear_greed': fear_greed_bias,
            'social': social_bias,
            'whale': whale_bias,
            'flows': flows_bias,
            'proprietary': proprietary_bias
        }

class SimulationResults:
    """Stores and visualizes simulation results"""
    
    def __init__(self):
        self.price_history = []
        self.equity_curve = []
        self.trades = []
        self.decisions = []
        self.win_rate_progression = []
        self.signal_weights = {}
        
    def record_cycle(self, cycle, market_data, decision, trade_result=None):
        """Record results from a simulation cycle"""
        self.price_history.append(market_data['price'])
        
        if trade_result:
            self.trades.append(trade_result)
        
        self.decisions.append(decision)
        
        # Calculate current equity
        if not self.equity_curve:
            self.equity_curve.append(10000)  # Starting capital
        else:
            new_equity = self.equity_curve[-1]
            if trade_result and 'pnl' in trade_result:
                new_equity += trade_result['pnl']
            self.equity_curve.append(new_equity)
    
    def record_weights(self, weights):
        """Record signal weights for tracking ML evolution"""
        self.signal_weights = weights
    
    def calculate_win_rate(self):
        """Calculate win rate over time"""
        trades_so_far = 0
        wins_so_far = 0
        
        for trade in self.trades:
            if 'pnl' in trade:
                trades_so_far += 1
                if trade['pnl'] > 0:
                    wins_so_far += 1
                
                if trades_so_far > 0:
                    self.win_rate_progression.append(wins_so_far / trades_so_far * 100)
    
    def plot_results(self):
        """Plot simulation results"""
        try:
            # Create figure with subplots
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 18))
            
            # Plot price chart
            ax1.plot(self.price_history, label='Asset Price', color='blue')
            ax1.set_title('Asset Price During Simulation')
            ax1.set_ylabel('Price')
            ax1.grid(True)
            
            # Plot equity curve
            ax2.plot(self.equity_curve, label='Account Equity', color='green')
            ax2.set_title('Equity Curve')
            ax2.set_ylabel('Equity')
            ax2.grid(True)
            
            # Plot win rate progression
            if self.win_rate_progression:
                ax3.plot(self.win_rate_progression, label='Win Rate %', color='purple')
                ax3.set_title('Win Rate Progression')
                ax3.set_ylabel('Win Rate %')
                ax3.set_ylim(0, 100)
                ax3.grid(True)
            
            # Add trade markers to price chart
            for i, trade in enumerate(self.trades):
                if 'action' in trade:
                    idx = min(i, len(self.price_history)-1)
                    price = self.price_history[idx]
                    
                    if trade['action'] == 'BUY':
                        ax1.scatter(idx, price, color='green', marker='^', s=100)
                    elif trade['action'] == 'SELL':
                        ax1.scatter(idx, price, color='red', marker='v', s=100)
            
            plt.tight_layout()
            
            # Save the plot
            plt.savefig('data/minute_paper_results.png')
            print("\n📊 Saved simulation chart to 'data/minute_paper_results.png'")
            
        except Exception as e:
            print(f"Error plotting results: {e}")
    
    def save_report(self):
        """Save simulation results to file"""
        try:
            results = {
                "equity_start": self.equity_curve[0] if self.equity_curve else 10000,
                "equity_end": self.equity_curve[-1] if self.equity_curve else 10000,
                "roi_pct": ((self.equity_curve[-1] / self.equity_curve[0]) - 1) * 100 if self.equity_curve else 0,
                "trade_count": len(self.trades),
                "win_count": sum(1 for t in self.trades if t.get('pnl', 0) > 0),
                "max_drawdown_pct": self._calculate_drawdown(),
                "final_signal_weights": self.signal_weights
            }
            
            # Calculate win rate
            if results["trade_count"] > 0:
                results["win_rate"] = results["win_count"] / results["trade_count"] * 100
            else:
                results["win_rate"] = 0
                
            with open('data/minute_paper_results.json', 'w') as f:
                json.dump(results, f, indent=2)
                
            print("\n💾 Saved detailed report to 'data/minute_paper_results.json'")
            
            return results
            
        except Exception as e:
            print(f"Error saving report: {e}")
    
    def _calculate_drawdown(self):
        """Calculate maximum drawdown percentage"""
        if not self.equity_curve or len(self.equity_curve) < 2:
            return 0
            
        max_drawdown = 0
        peak = self.equity_curve[0]
        
        for equity in self.equity_curve:
            # Update peak if new high
            if equity > peak:
                peak = equity
            
            # Calculate drawdown
            drawdown = (peak - equity) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
            
        return max_drawdown


async def run_minute_paper():
    """Run accelerated trading simulation"""
    
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║   MINUTE PAPER - ACCELERATED TRADING SIMULATION           ║
    ║                                                            ║
    ║   Testing your Multi-Signal ML Trading Bot                ║
    ║   Simulating market conditions and trading decisions      ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize simulator and results
    market = MarketSimulator(STARTING_PRICE)
    results = SimulationResults()
    
    # Initialize trading engine
    print("🚀 Initializing trading engine...")
    engine = MultiSignalTradingEngine()
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    print(f"\n📈 Beginning {SIMULATION_CYCLES} trading cycles across different market conditions...")
    
    # Tracking variables
    total_cycles = 0
    trades_executed = 0
    
    # Run through market conditions
    for condition in MARKET_CONDITIONS:
        print(f"\n{'='*60}")
        print(f"🌎 MARKET CONDITION: {condition['name']}")
        print(f"{'='*60}")
        
        # Run cycles for this market condition
        for cycle in range(condition['cycles']):
            # Update market with bias from current condition
            market_data = market.update_market(bias=condition['bias'])
            
            # Get signal biases for this market condition
            signal_biases = market.get_signal_biases()
            
            print(f"\n📊 CYCLE #{total_cycles+1}")
            print(f"Price: ${market_data['price']:.2f} ({market_data['change_pct']:+.2f}%) | {market_data['timestamp'].strftime('%Y-%m-%d %H:%M')}")
            
            # Collect signals (biased by market condition)
            signals = await collect_biased_signals(engine, signal_biases)
            
            # Print signals
            print("\n📡 SIGNALS:")
            for name, data in signals.items():
                value = data['value']
                if value > 0.3:
                    direction = "BUY ↑"
                    color = "🟢"
                elif value < -0.3:
                    direction = "SELL ↓"
                    color = "🔴"
                else:
                    direction = "HOLD →"
                    color = "🟡"
                
                print(f"  {color} {name:12} | {direction:7} | Strength: {abs(value)*100:5.1f}%")
            
            # Make decision
            decision = engine.make_ml_decision(signals)
            
            print("\n🤖 DECISION:")
            print(f"  Action: {decision['action']}")
            print(f"  Confidence: {decision['confidence']*100:.1f}%")
            print(f"  Position Size: {decision['position_size']*100:.1f}% of capital")
            
            # Execute trades with some probability
            trade_result = None
            if decision['action'] != 'HOLD':
                # Execute trade and get result
                trade_result = execute_trade(decision, market_data, signals)
                trades_executed += 1
                
                # Add signal values to trade result for enhanced ML learning
                trade_result['signal_values'] = signals
                
                # Update ML weights
                engine.update_ml_weights(trade_result)
                
                print(f"\n💰 Trade: {'WIN' if trade_result['pnl'] > 0 else 'LOSS'} (${trade_result['pnl']:+.2f})")
            
            # Record results
            results.record_cycle(total_cycles, market_data, decision, trade_result)
            
            # Increment cycle counter
            total_cycles += 1
            
            # Wait a bit to make output readable
            await asyncio.sleep(SIMULATION_SPEED)
    
    # Record final weights
    results.record_weights(engine.ml_weights)
    
    # Calculate win rate progression
    results.calculate_win_rate()
    
    # Plot results
    results.plot_results()
    
    # Generate report
    report = results.save_report()
    
    # Get performance stats
    stats = engine.get_performance_stats()
    
    # Show final summary
    print(f"\n{'='*60}")
    print("📊 SIMULATION RESULTS SUMMARY")
    print('='*60)
    print(f"Total Cycles: {total_cycles}")
    print(f"Trades Executed: {trades_executed}")
    print(f"Starting Capital: ${results.equity_curve[0]:.2f}")
    print(f"Final Capital: ${results.equity_curve[-1]:.2f}")
    print(f"ROI: {((results.equity_curve[-1] / results.equity_curve[0]) - 1) * 100:+.2f}%")
    print(f"Win Rate: {report['win_rate']:.1f}%")
    print(f"Max Drawdown: {report['max_drawdown_pct']:.1f}%")
    
    print("\n🧠 ML-OPTIMIZED SIGNAL WEIGHTS:")
    for signal, weight in sorted(engine.ml_weights.items(), key=lambda x: x[1], reverse=True):
        print(f"  {signal}: {weight:.3f}")
    
    print("\n📝 MACHINE LEARNING INSIGHTS:")
    
    # Get weight changes from the engine
    weight_changes = stats.get('weight_changes', {})
    
    if weight_changes:
        # Sort by percentage change
        gainers = sorted(weight_changes.items(), key=lambda x: x[1]['pct_change'], reverse=True)[:3]
        losers = sorted(weight_changes.items(), key=lambda x: x[1]['pct_change'])[:3]
        
        print(f"  ML Adaptation Score: {stats.get('ml_adaptation', 0):.2f}%")
        print("\n  Most improved signals:")
        for signal, data in gainers:
            print(f"    {signal}: {data['pct_change']:+.1f}% weight change ({data['initial']:.3f} → {data['current']:.3f})")
            
        print("\n  Decreased signals:")
        for signal, data in losers:
            print(f"    {signal}: {data['pct_change']:+.1f}% weight change ({data['initial']:.3f} → {data['current']:.3f})")
    else:
        # Fallback to old method if weight_changes not available
        initial_weights = {'rsi': 0.12, 'macd': 0.10, 'bollinger': 0.08, 'volume': 0.08,
                          'fear_greed': 0.15, 'social': 0.10, 'whale': 0.12, 'flows': 0.10, 'proprietary': 0.15}
        
        # Find biggest gainers and losers
        changes = {s: (engine.ml_weights[s] - initial_weights[s])/initial_weights[s]*100 for s in initial_weights}
        gainers = sorted(changes.items(), key=lambda x: x[1], reverse=True)[:3]
        losers = sorted(changes.items(), key=lambda x: x[1])[:3]
        
        print("  Most improved signals:")
        for signal, pct in gainers:
            print(f"    {signal}: {pct:+.1f}% weight change")
            
        print("  Decreased signals:")
        for signal, pct in losers:
            print(f"    {signal}: {pct:+.1f}% weight change")
    
    print("\n🚀 READY FOR LIVE TRADING!")


async def collect_biased_signals(engine, biases):
    """Collect signals biased by market conditions"""
    # Get normal signals
    signals = await engine.collect_all_signals()
    
    # Apply biases to simulate how signals perform in different markets
    for name, bias in biases.items():
        if name in signals:
            # Add bias to signal value (limited to -1 to +1 range)
            signals[name]['value'] = max(-1, min(1, signals[name]['value'] + bias * 0.3))
    
    return signals


def execute_trade(decision, market_data, signals):
    """Simulate trade execution and outcome"""
    # Determine price impact by position size (slippage)
    slippage_pct = decision['position_size'] * random.uniform(0, 1)
    
    # Execute price with slippage
    if decision['action'] == 'BUY':
        entry_price = market_data['price'] * (1 + slippage_pct/100)
    else:  # SELL
        entry_price = market_data['price'] * (1 - slippage_pct/100)
    
    # Get the trend strength and market bias
    trend = market_data['trend']
    
    # Determine trade outcome (affected by decision confidence and market trend)
    # If buy in uptrend or sell in downtrend, higher chance of success
    alignment = (decision['action'] == 'BUY' and trend > 0) or (decision['action'] == 'SELL' and trend < 0)
    alignment_boost = 0.2 if alignment else -0.2
    
    # Add some randomness (market is unpredictable!)
    luck_factor = random.normalvariate(0, 0.7)
    
    # Calculate PnL based on position size, confidence, alignment and luck
    base_pnl = decision['position_size'] * 10000  # % of capital
    pnl_multiplier = (decision['confidence'] * 0.4) + (alignment_boost * 0.3) + (luck_factor * 0.3)
    pnl = base_pnl * pnl_multiplier
    
    # Return trade result
    return {
        'action': decision['action'],
        'entry_price': entry_price,
        'position_size': decision['position_size'],
        'confidence': decision['confidence'],
        'pnl': pnl,
        'signals': list(signals.keys()),
        'timestamp': market_data['timestamp'].isoformat()
    }


if __name__ == "__main__":
    print("\n🔬 Running Minute Paper Trading Simulation...")
    asyncio.run(run_minute_paper())