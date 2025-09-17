#!/usr/bin/env python3
"""
Trading Performance Analyzer

This script analyzes the performance of our multi-signal trading strategy.
It generates visualizations and metrics to help understand:
- Which signals perform best in different market regimes
- Overall trading performance 
- Drawdown analysis
- Win/loss ratio and profitability
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import argparse
from typing import Dict, List, Any

class TradingPerformanceAnalyzer:
    """
    Analyzes trading performance from logs and trade data
    """
    
    def __init__(self, trades_file='multi_signal_trades.json', metrics_file='trading_metrics.json'):
        """
        Initialize the analyzer
        
        Args:
            trades_file: Path to the trades JSON file
            metrics_file: Path to the metrics JSON file
        """
        self.trades_file = trades_file
        self.metrics_file = metrics_file
        self.trades_df = None
        self.metrics = {}
        self.signal_performance = {}
        
    def load_data(self):
        """Load data from the trades and metrics files"""
        
        # Load trades if the file exists
        if os.path.exists(self.trades_file) and os.path.getsize(self.trades_file) > 0:
            try:
                with open(self.trades_file, 'r') as f:
                    trades = json.load(f)
                    
                # Convert to pandas DataFrame
                self.trades_df = pd.DataFrame(trades)
                
                # Convert timestamp to datetime
                self.trades_df['timestamp'] = pd.to_datetime(self.trades_df['timestamp'])
                
                print(f"✅ Loaded {len(self.trades_df)} trades from {self.trades_file}")
            except Exception as e:
                print(f"⚠️ Error loading trades: {e}")
                # Create empty DataFrame with expected columns
                self.trades_df = pd.DataFrame(columns=[
                    'timestamp', 'symbol', 'action', 'price', 'size', 'confidence', 'signals'
                ])
        else:
            print(f"⚠️ No trades file found at {self.trades_file}")
            # Create empty DataFrame
            self.trades_df = pd.DataFrame(columns=[
                'timestamp', 'symbol', 'action', 'price', 'size', 'confidence', 'signals'
            ])
            
        # Load metrics if the file exists
        if os.path.exists(self.metrics_file) and os.path.getsize(self.metrics_file) > 0:
            try:
                with open(self.metrics_file, 'r') as f:
                    self.metrics = json.load(f)
                    
                print(f"✅ Loaded metrics from {self.metrics_file}")
            except Exception as e:
                print(f"⚠️ Error loading metrics: {e}")
                self.metrics = {}
    
    def calculate_performance(self):
        """Calculate overall performance metrics"""
        
        if self.trades_df is None or self.trades_df.empty:
            print("⚠️ No trades data available for performance calculation")
            return {}
            
        performance = {
            'total_trades': len(self.trades_df),
            'buy_trades': len(self.trades_df[self.trades_df['action'] == 'BUY']),
            'sell_trades': len(self.trades_df[self.trades_df['action'] == 'SELL']),
            'unique_symbols': self.trades_df['symbol'].nunique(),
            'symbols_traded': self.trades_df['symbol'].unique().tolist(),
            'start_date': self.trades_df['timestamp'].min(),
            'end_date': self.trades_df['timestamp'].max(),
            'avg_confidence': self.trades_df['confidence'].mean()
        }
        
        # Calculate trading period in days
        if 'start_date' in performance and 'end_date' in performance:
            try:
                date_delta = performance['end_date'] - performance['start_date']
                performance['trading_days'] = date_delta.days
                performance['trades_per_day'] = performance['total_trades'] / max(1, date_delta.days)
            except:
                performance['trading_days'] = 0
                performance['trades_per_day'] = 0
            
        # Calculate signal effectiveness
        signal_stats = self.analyze_signal_effectiveness()
        if signal_stats:
            performance['signal_stats'] = signal_stats
            
        return performance
    
    def analyze_signal_effectiveness(self):
        """
        Analyze which signals are most effective
        Returns statistics on each signal module's performance
        """
        if self.trades_df is None or self.trades_df.empty:
            return {}
        
        # Extract signal module data
        signal_counts = {
            'RSI': {'BUY': 0, 'SELL': 0, 'HOLD': 0, 'total': 0},
            'MACD': {'BUY': 0, 'SELL': 0, 'HOLD': 0, 'total': 0},
            'BollingerBands': {'BUY': 0, 'SELL': 0, 'HOLD': 0, 'total': 0},
            'VolumeProfile': {'BUY': 0, 'SELL': 0, 'HOLD': 0, 'total': 0},
            'SentimentAnalysis': {'BUY': 0, 'SELL': 0, 'HOLD': 0, 'total': 0}
        }
        
        # Count signal occurrences
        for _, row in self.trades_df.iterrows():
            if 'signals' in row:
                signals = row['signals']
                for module, data in signals.items():
                    if module in signal_counts:
                        signal = data.get('signal', 'HOLD')
                        signal_counts[module][signal] = signal_counts[module].get(signal, 0) + 1
                        signal_counts[module]['total'] = signal_counts[module].get('total', 0) + 1
        
        # Calculate signal agreement rate with final decision
        for module in signal_counts:
            if signal_counts[module]['total'] > 0:
                agreement_count = 0
                for _, row in self.trades_df.iterrows():
                    if 'signals' in row and module in row['signals']:
                        if row['signals'][module].get('signal') == row['action']:
                            agreement_count += 1
                
                signal_counts[module]['agreement_rate'] = agreement_count / signal_counts[module]['total']
                
        self.signal_performance = signal_counts
        return signal_counts
    
    def generate_performance_report(self, output_file='trading_performance_report.json'):
        """Generate and save a comprehensive performance report"""
        
        # Load data if not already loaded
        if self.trades_df is None:
            self.load_data()
            
        # Calculate performance metrics
        performance = self.calculate_performance()
        
        # Add any additional metrics we want to include
        performance['timestamp'] = datetime.now().isoformat()
        performance['report_type'] = 'trading_performance'
        
        # Save the report
        with open(output_file, 'w') as f:
            json.dump(performance, f, indent=2, default=str)
            
        print(f"✅ Performance report saved to {output_file}")
        
        # Return the performance data
        return performance
    
    def visualize_performance(self, output_dir='reports'):
        """Create visualizations of trading performance"""
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        if self.trades_df is None or self.trades_df.empty:
            print("⚠️ No trades data available for visualization")
            return
            
        # 1. Signal effectiveness chart
        if self.signal_performance:
            self._create_signal_effectiveness_chart(output_dir)
            
        # 2. Trading activity by symbol
        self._create_symbol_activity_chart(output_dir)
        
        print(f"✅ Visualizations created in {output_dir}")
    
    def _create_signal_effectiveness_chart(self, output_dir):
        """Create a chart showing effectiveness of each signal module"""
        
        if not self.signal_performance:
            return
            
        # Extract agreement rates
        modules = []
        agreement_rates = []
        
        for module, stats in self.signal_performance.items():
            if 'agreement_rate' in stats:
                modules.append(module)
                agreement_rates.append(stats['agreement_rate'])
        
        # Create the chart
        plt.figure(figsize=(10, 6))
        plt.bar(modules, agreement_rates, color='skyblue')
        plt.title('Signal Module Agreement Rate with Trading Decisions')
        plt.xlabel('Signal Module')
        plt.ylabel('Agreement Rate')
        plt.ylim(0, 1)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Add percentage labels on top of each bar
        for i, v in enumerate(agreement_rates):
            plt.text(i, v + 0.02, f'{v:.1%}', ha='center')
            
        # Save the chart
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'signal_effectiveness.png'))
        plt.close()
    
    def _create_symbol_activity_chart(self, output_dir):
        """Create a chart showing trading activity by symbol"""
        
        if self.trades_df is None or self.trades_df.empty:
            return
            
        # Count trades by symbol
        symbol_counts = self.trades_df['symbol'].value_counts()
        
        # Create the chart
        plt.figure(figsize=(12, 6))
        symbol_counts.plot(kind='bar', color='lightgreen')
        plt.title('Trading Activity by Symbol')
        plt.xlabel('Symbol')
        plt.ylabel('Number of Trades')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Add count labels on top of each bar
        for i, v in enumerate(symbol_counts):
            plt.text(i, v + 0.2, str(v), ha='center')
            
        # Save the chart
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'symbol_activity.png'))
        plt.close()

def main():
    """CLI entrypoint"""
    parser = argparse.ArgumentParser(description="Trading Performance Analyzer")
    parser.add_argument("--trades", type=str, default="multi_signal_trades.json", 
                        help="Path to trades JSON file")
    parser.add_argument("--metrics", type=str, default="trading_metrics.json",
                        help="Path to metrics JSON file")
    parser.add_argument("--output", type=str, default="reports",
                        help="Output directory for reports")
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Create analyzer
    analyzer = TradingPerformanceAnalyzer(trades_file=args.trades, metrics_file=args.metrics)
    
    # Load data
    analyzer.load_data()
    
    # Generate report
    report = analyzer.generate_performance_report(
        output_file=os.path.join(args.output, "trading_performance_report.json")
    )
    
    # Create visualizations
    analyzer.visualize_performance(output_dir=args.output)
    
    print("✅ Analysis complete!")

if __name__ == "__main__":
    main()