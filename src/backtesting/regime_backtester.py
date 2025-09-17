"""
Regime-Specific Backtesting Module

This module provides backtesting functionality specifically designed
to evaluate trading performance across different market regimes.
"""

import numpy as np
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import matplotlib.pyplot as plt
from enum import Enum
import os
import sys

# Add the project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Import the trading engine and market regime components
from src.core.unified_trading_engine import MultiSignalTradingEngine, MarketRegime

class RegimeBacktester:
    """
    Specialized backtesting class for analyzing trading performance
    across different market regimes (bull, bear, sideways)
    """
    
    def __init__(self, price_data: List[float], volume_data: Optional[List[float]] = None, 
                 dates: Optional[List[str]] = None, lookback_period: int = 14):
        """
        Initialize the regime backtester
        
        Args:
            price_data: List of historical prices
            volume_data: Optional list of volume data matching price_data length
            dates: Optional list of date strings matching price_data length
            lookback_period: Number of periods to use for regime detection
        """
        self.price_data = price_data
        self.volume_data = volume_data if volume_data else [1.0] * len(price_data)
        self.dates = dates
        
        # Ensure we have enough data
        if len(self.price_data) < 2:
            raise ValueError("Insufficient price data for backtesting")
            
        # Ensure volume data matches price data length
        if len(self.volume_data) != len(self.price_data):
            self.volume_data = [1.0] * len(self.price_data)
        
        # Create trading engine with regime awareness
        self.engine = MultiSignalTradingEngine(enhanced_ml=True, regime_aware=True)
        
        # Track regime classifications
        self.detected_regimes = []
        self.regime_confidences = []
        self.trade_results = []
        self.lookback_period = lookback_period
        
        # Performance metrics by regime
        self.regime_performance = {
            'bull': {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0},
            'bear': {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0},
            'sideways': {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0},
            'unknown': {'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0}
        }
        
    async def run_full_backtest(self) -> Dict:
        """
        Run a complete backtest across all data and separate performance by regime
        
        Returns:
            Dict of performance metrics
        """
        print(f"Running full backtest on {len(self.price_data)} price points...")
        
        # Process each data point
        for i in range(self.lookback_period, len(self.price_data) - 1):
            # Get current price and volume
            current_price = self.price_data[i]
            current_volume = self.volume_data[i]
            
            # Collect signals with price data for regime detection
            signals = await self.engine.collect_all_signals(current_price, current_volume)
            
            # Extract regime info from signals metadata
            current_regime = signals.get('_metadata', {}).get('regime', 'unknown')
            current_confidence = signals.get('_metadata', {}).get('regime_confidence', 0.0)
            
            # Store regime data
            self.detected_regimes.append(current_regime)
            self.regime_confidences.append(current_confidence)
            
            # Make trading decision
            decision = self.engine.make_ml_decision(signals)
            
            # Simulate trade result based on price movement
            next_price = self.price_data[i + 1]
            price_change = (next_price / current_price) - 1
            
            # Calculate PnL based on decision and price change
            if decision['action'] == 'BUY':
                pnl = price_change * 100  # Simplified PnL calculation
            elif decision['action'] == 'SELL':
                pnl = -price_change * 100  # Profit from price drop
            else:  # HOLD
                pnl = 0
                
            # Apply position sizing
            pnl *= decision['position_size'] * 10  # Scale for better visualization
            
            # Create trade result
            date_str = self.dates[i] if self.dates and i < len(self.dates) else datetime.now().isoformat()
            
            trade_result = {
                'action': decision['action'],
                'pnl': pnl,
                'confidence': decision['confidence'],
                'timestamp': date_str,
                'price': current_price,
                'signals': list(signals.keys()),
                'signal_values': signals,
                'regime': current_regime
            }
            
            # Update ML weights based on trade result
            self.engine.update_ml_weights(trade_result)
            
            # Store trade result
            self.trade_results.append(trade_result)
            
            # Update regime-specific performance metrics
            self._update_regime_metrics(trade_result)
            
            # Show progress periodically
            if i % 100 == 0:
                print(f"Processed {i}/{len(self.price_data)} data points...")
                
        # Calculate win rates and return overall performance
        return self._calculate_performance_metrics()
        
    async def backtest_specific_regime(self, target_regime: str) -> Dict:
        """
        Run backtest only on periods matching a specific market regime
        
        Args:
            target_regime: Market regime to target ('bull', 'bear', 'sideways')
            
        Returns:
            Dict of performance metrics for the specific regime
        """
        print(f"Running backtest specifically on {target_regime} market periods...")
        
        # First, we need to run a quick pass to identify regime periods
        regime_periods = await self._identify_regime_periods()
        
        # Get periods matching our target regime
        target_periods = regime_periods.get(target_regime, [])
        
        if not target_periods:
            print(f"No {target_regime} market periods identified in the data")
            return {}
            
        print(f"Found {len(target_periods)} {target_regime} market periods")
        
        # Create a fresh engine for this specific backtest
        specific_engine = MultiSignalTradingEngine(enhanced_ml=True, regime_aware=True)
        
        # Track performance for this specific regime
        trade_results = []
        
        # Process each period that matches our target regime
        for start_idx, end_idx in target_periods:
            print(f"Processing {target_regime} period from index {start_idx} to {end_idx}")
            
            for i in range(start_idx, end_idx):
                if i >= len(self.price_data) - 1:
                    continue
                    
                # Get current price and volume
                current_price = self.price_data[i]
                current_volume = self.volume_data[i]
                
                # Collect signals
                signals = await specific_engine.collect_all_signals(current_price, current_volume)
                
                # Make trading decision
                decision = specific_engine.make_ml_decision(signals)
                
                # Calculate result based on next price
                next_price = self.price_data[i + 1]
                price_change = (next_price / current_price) - 1
                
                # Calculate PnL
                if decision['action'] == 'BUY':
                    pnl = price_change * 100
                elif decision['action'] == 'SELL':
                    pnl = -price_change * 100
                else:  # HOLD
                    pnl = 0
                    
                pnl *= decision['position_size'] * 10
                
                # Create trade result
                date_str = self.dates[i] if self.dates and i < len(self.dates) else datetime.now().isoformat()
                
                trade_result = {
                    'action': decision['action'],
                    'pnl': pnl,
                    'confidence': decision['confidence'],
                    'timestamp': date_str,
                    'price': current_price,
                    'regime': target_regime
                }
                
                # Update ML weights
                specific_engine.update_ml_weights(trade_result)
                
                # Store result
                trade_results.append(trade_result)
        
        # Calculate performance metrics
        wins = sum(1 for t in trade_results if t['pnl'] > 0)
        losses = sum(1 for t in trade_results if t['pnl'] <= 0)
        total_pnl = sum(t['pnl'] for t in trade_results)
        win_rate = (wins / max(len(trade_results), 1)) * 100
        
        return {
            'regime': target_regime,
            'trades': len(trade_results),
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / max(len(trade_results), 1),
            'trade_results': trade_results
        }
    
    async def compare_all_regimes(self) -> Dict:
        """
        Run separate backtests for each regime type and compare results
        
        Returns:
            Dict with performance metrics for each regime
        """
        results = {}
        
        for regime in ['bull', 'bear', 'sideways']:
            print(f"\nBacktesting {regime} market periods...")
            regime_results = await self.backtest_specific_regime(regime)
            results[regime] = regime_results
            
        return results
    
    async def _identify_regime_periods(self) -> Dict[str, List[Tuple[int, int]]]:
        """
        Identify continuous periods of each market regime
        
        Returns:
            Dict mapping regime types to list of (start_idx, end_idx) tuples
        """
        # First, run a pass to identify regimes at each point
        if not self.detected_regimes:
            # We need to run a pass to detect regimes
            for i in range(self.lookback_period, len(self.price_data)):
                current_price = self.price_data[i]
                current_volume = self.volume_data[i]
                
                signals = await self.engine.collect_all_signals(current_price, current_volume)
                current_regime = signals.get('_metadata', {}).get('regime', 'unknown')
                self.detected_regimes.append(current_regime)
        
        # Find continuous periods of each regime type
        regime_periods = {
            'bull': [],
            'bear': [],
            'sideways': [],
            'unknown': []
        }
        
        # Minimum period length to consider (to filter noise)
        min_period_length = 5
        
        current_regime = None
        start_idx = 0
        
        for i, regime in enumerate(self.detected_regimes):
            # Add lookback_period to index since we start detection after lookback
            actual_idx = i + self.lookback_period
            
            if regime != current_regime:
                # Regime has changed
                if current_regime and (actual_idx - start_idx) >= min_period_length:
                    # Save the previous period if it's long enough
                    regime_periods[current_regime].append((start_idx, actual_idx))
                
                # Start a new period
                current_regime = regime
                start_idx = actual_idx
        
        # Don't forget the last period
        if current_regime and (len(self.price_data) - start_idx) >= min_period_length:
            regime_periods[current_regime].append((start_idx, len(self.price_data)))
            
        return regime_periods
    
    def _update_regime_metrics(self, trade_result: Dict) -> None:
        """
        Update performance metrics for the specific regime of this trade
        
        Args:
            trade_result: Dict containing trade result information
        """
        regime = trade_result.get('regime', 'unknown')
        pnl = trade_result.get('pnl', 0)
        
        if regime in self.regime_performance:
            self.regime_performance[regime]['trades'] += 1
            
            if pnl > 0:
                self.regime_performance[regime]['wins'] += 1
            else:
                self.regime_performance[regime]['losses'] += 1
                
            self.regime_performance[regime]['pnl'] += pnl
    
    def _calculate_performance_metrics(self) -> Dict:
        """
        Calculate final performance metrics for each regime
        
        Returns:
            Dict with performance metrics
        """
        for regime, data in self.regime_performance.items():
            trades = data['trades']
            if trades > 0:
                data['win_rate'] = (data['wins'] / trades) * 100
                data['avg_pnl'] = data['pnl'] / trades
            else:
                data['win_rate'] = 0
                data['avg_pnl'] = 0
        
        # Overall metrics
        total_trades = sum(data['trades'] for data in self.regime_performance.values())
        total_wins = sum(data['wins'] for data in self.regime_performance.values())
        total_pnl = sum(data['pnl'] for data in self.regime_performance.values())
        
        # Calculate win rate for all trades
        overall_win_rate = 0
        if total_trades > 0:
            overall_win_rate = (total_wins / total_trades) * 100
        
        return {
            'overall': {
                'trades': total_trades,
                'wins': total_wins,
                'losses': total_trades - total_wins,
                'win_rate': overall_win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': total_pnl / max(total_trades, 1)
            },
            'by_regime': self.regime_performance,
            'ml_adaptation': self.engine.get_weight_changes(),
            'regime_distribution': self._get_regime_distribution()
        }
    
    def _get_regime_distribution(self) -> Dict:
        """
        Get distribution of detected regimes
        
        Returns:
            Dict with regime distribution statistics
        """
        if not self.detected_regimes:
            return {}
            
        total = len(self.detected_regimes)
        distribution = {}
        
        for regime in set(self.detected_regimes):
            count = self.detected_regimes.count(regime)
            distribution[regime] = {
                'count': count,
                'percentage': (count / total) * 100
            }
            
        return distribution
    
    def visualize_regime_performance(self, results: Dict) -> None:
        """
        Visualize performance by market regime
        
        Args:
            results: Dict with performance metrics
        """
        try:
            import matplotlib.pyplot as plt
            
            # Prepare data
            regimes = []
            win_rates = []
            avg_pnls = []
            trade_counts = []
            
            # Get regime-specific metrics
            by_regime = results.get('by_regime', {})
            
            for regime, data in by_regime.items():
                if data['trades'] > 0:
                    regimes.append(regime)
                    win_rates.append(data['win_rate'])
                    avg_pnls.append(data['avg_pnl'])
                    trade_counts.append(data['trades'])
            
            if not regimes:
                print("No regime data to visualize")
                return
                
            # Create figure
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            # Plot win rates
            bars = ax1.bar(regimes, win_rates)
            ax1.set_title('Win Rate by Market Regime')
            ax1.set_ylabel('Win Rate %')
            ax1.grid(True, alpha=0.3)
            
            # Add value labels
            for bar, val in zip(bars, win_rates):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                        f'{val:.1f}%', ha='center', va='bottom')
            
            # Plot average PnL
            bars = ax2.bar(regimes, avg_pnls)
            ax2.set_title('Average PnL by Market Regime')
            ax2.set_ylabel('Average PnL')
            ax2.grid(True, alpha=0.3)
            
            # Add value labels
            for bar, val in zip(bars, avg_pnls):
                height = bar.get_height()
                y_pos = height + 0.5 if height >= 0 else height - 2
                ax2.text(bar.get_x() + bar.get_width()/2., y_pos,
                        f'{val:.2f}', ha='center', va='bottom')
            
            plt.tight_layout()
            plt.savefig('regime_performance_comparison.png')
            plt.close()
            
            # Create a second figure for regime distribution
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot trade count by regime
            bars = ax.bar(regimes, trade_counts)
            ax.set_title('Trade Count by Market Regime')
            ax.set_ylabel('Number of Trades')
            ax.grid(True, alpha=0.3)
            
            # Add value labels
            for bar, val in zip(bars, trade_counts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                      f'{val}', ha='center', va='bottom')
            
            plt.tight_layout()
            plt.savefig('regime_distribution.png')
            plt.close()
            
            print("✅ Performance visualizations saved")
            
        except ImportError:
            print("Matplotlib not available. Skipping visualization.")
            
    def save_results(self, results: Dict, filename: str = 'regime_backtest_results.json') -> None:
        """
        Save backtest results to file
        
        Args:
            results: Dict with performance metrics
            filename: Output filename
        """
        # Convert any non-serializable objects to strings
        def clean_for_json(obj):
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif isinstance(obj, tuple):
                return list(obj)
            elif isinstance(obj, (int, float, str, bool, type(None))):
                return obj
            else:
                return str(obj)
        
        clean_results = clean_for_json(results)
        
        with open(filename, 'w') as f:
            json.dump(clean_results, f, indent=2)
            
        print(f"✅ Results saved to {filename}")
    
    def generate_regime_report(self, results: Dict) -> str:
        """
        Generate a text report of regime performance
        
        Args:
            results: Dict with performance metrics
            
        Returns:
            String with formatted report
        """
        report = []
        
        # Add report header
        report.append("=" * 70)
        report.append("MARKET REGIME BACKTEST REPORT")
        report.append("=" * 70)
        
        # Add overall performance
        overall = results.get('overall', {})
        report.append("\nOVERALL PERFORMANCE:")
        report.append(f"Total Trades: {overall.get('trades', 0)}")
        report.append(f"Win Rate: {overall.get('win_rate', 0):.2f}%")
        report.append(f"Total PnL: {overall.get('total_pnl', 0):.2f}")
        report.append(f"Avg PnL per Trade: {overall.get('avg_pnl', 0):.2f}")
        
        # Add regime distribution
        distribution = results.get('regime_distribution', {})
        report.append("\nREGIME DISTRIBUTION:")
        for regime, data in distribution.items():
            report.append(f"{regime.upper()}: {data.get('count', 0)} data points "
                         f"({data.get('percentage', 0):.1f}%)")
        
        # Add regime-specific performance
        by_regime = results.get('by_regime', {})
        report.append("\nPERFORMANCE BY REGIME:")
        
        for regime, data in by_regime.items():
            if data['trades'] > 0:
                report.append(f"\n{regime.upper()} MARKET:")
                report.append(f"  Trades: {data.get('trades', 0)}")
                report.append(f"  Win Rate: {data.get('win_rate', 0):.2f}%")
                report.append(f"  Total PnL: {data.get('pnl', 0):.2f}")
                report.append(f"  Avg PnL per Trade: {data.get('avg_pnl', 0):.2f}")
        
        # Add ML adaptation info
        ml_adaptation = results.get('ml_adaptation', {})
        report.append("\nML WEIGHT ADAPTATION:")
        
        for signal, data in ml_adaptation.items():
            pct_change = data.get('pct_change', 0)
            direction = "+" if pct_change >= 0 else ""
            report.append(f"{signal}: {direction}{pct_change:.2f}% change "
                         f"({data.get('initial', 0):.4f} → {data.get('current', 0):.4f})")
        
        report.append("\n" + "=" * 70)
        
        return "\n".join(report)


async def demo_regime_backtester():
    """Demo function to show how to use the regime backtester"""
    # Generate sample price data with different regimes
    print("Generating sample price data...")
    
    # Create sample data with clear bull, bear, and sideways regimes
    price_data = []
    volume_data = []
    dates = []
    
    # Starting price
    price = 10000.0
    
    # Create a 100-day period (bull, sideways, bear, sideways)
    days = 100
    
    # Bull market for 30 days
    for i in range(30):
        # Bull market with upward trend
        price *= (1 + np.random.normal(0.004, 0.01))  # ~0.4% daily gain plus noise
        price_data.append(price)
        volume_data.append(price * np.random.uniform(0.8, 1.2) / 1000)
        dates.append((datetime.now() + timedelta(days=i)).isoformat())
    
    # Sideways market for 20 days
    start_price = price
    for i in range(30, 50):
        # Sideways market with mean reversion
        deviation = (price / start_price) - 1
        price *= (1 + np.random.normal(-deviation * 0.3, 0.007))  # Mean reversion
        price_data.append(price)
        volume_data.append(price * np.random.uniform(0.5, 0.9) / 1000)  # Lower volume
        dates.append((datetime.now() + timedelta(days=i)).isoformat())
    
    # Bear market for 30 days
    for i in range(50, 80):
        # Bear market with downward trend
        price *= (1 + np.random.normal(-0.003, 0.012))  # ~0.3% daily loss plus noise
        price_data.append(price)
        volume_data.append(price * np.random.uniform(1.0, 1.5) / 1000)  # Higher volume
        dates.append((datetime.now() + timedelta(days=i)).isoformat())
    
    # Sideways market for 20 days
    start_price = price
    for i in range(80, 100):
        # Sideways market with mean reversion
        deviation = (price / start_price) - 1
        price *= (1 + np.random.normal(-deviation * 0.3, 0.006))  # Mean reversion
        price_data.append(price)
        volume_data.append(price * np.random.uniform(0.5, 0.9) / 1000)  # Lower volume
        dates.append((datetime.now() + timedelta(days=i)).isoformat())
    
    print(f"Generated {len(price_data)} days of price data")
    print(f"Starting price: ${price_data[0]:,.2f}")
    print(f"Ending price: ${price_data[-1]:,.2f}")
    print(f"Price change: {((price_data[-1]/price_data[0])-1)*100:.2f}%")
    
    # Create backtester
    backtester = RegimeBacktester(price_data, volume_data, dates)
    
    # Run full backtest
    print("\nRunning full backtest...")
    full_results = await backtester.run_full_backtest()
    
    # Save and visualize results
    backtester.save_results(full_results, 'full_regime_backtest.json')
    backtester.visualize_regime_performance(full_results)
    
    # Generate and print report
    report = backtester.generate_regime_report(full_results)
    print("\n" + report)
    
    # Run regime-specific backtests
    print("\nRunning regime comparison backtests...")
    regime_results = await backtester.compare_all_regimes()
    
    # Save regime-specific results
    backtester.save_results(regime_results, 'regime_comparison_results.json')
    
    return {
        'full_results': full_results,
        'regime_results': regime_results
    }

if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║   REGIME-SPECIFIC BACKTESTER                          ║
    ║   Testing Trading Performance Across Market Regimes    ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(demo_regime_backtester())