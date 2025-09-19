#!/usr/bin/env python3
"""
Simple Rapid Fire Training System (No TensorFlow)

This is a simplified version of the Rapid Fire ML Training System
that doesn't require TensorFlow. It still performs signal weight
optimization and collects valuable training data.
"""

import os
import json
import time
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from typing import Dict, List

# Import from the existing bot architecture
from MultiSignalBot import MultiSignalBot
from budget_manager import BudgetManager


class SimpleRapidFireTrainer:
    """
    30-minute simplified paper trading system for signal optimization
    without TensorFlow dependency
    """
    
    def __init__(self, config_path: str = "config/config.yaml", initial_capital: float = 1000.0):
        """
        Initialize the SimpleRapidFireTrainer system
        
        Args:
            config_path: Path to the configuration file
            initial_capital: Initial capital for paper trading (default $1000)
        """
        # Trading setup
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = []
        self.trade_history = []
        
        # Initialize the MultiSignalBot in paper mode
        self.bot = MultiSignalBot(config_path=config_path, paper_mode=True)
        
        # Override the budget manager with our custom budget
        self.bot.budget_manager = BudgetManager(initial_capital=initial_capital)
        
        # Performance tracking
        self.wins = 0
        self.losses = 0
        self.total_trades = 0
        self.decision_history = []
        
        # Dashboard data
        self.dashboard_data = {
            'timestamp': [],
            'capital': [],
            'win_rate': [],
            'best_signal': None,
            'worst_signal': None
        }
        
        # Signal sources (all 15 signals from the existing bot)
        self.signals = [
            'RSI', 'MACD', 'Bollinger', 'Volume', 'Sentiment',
            'Port_Congestion', 'Diesel', 'Supply_Chain', 'Container',
            'Inflation', 'Regulatory', 'Remittance', 'CBDC', 'FATF',
            'Chainalysis_Global'
        ]
        
        # Signal weights (will be dynamically adjusted)
        self.signal_weights = {signal: 1.0/len(self.signals) for signal in self.signals}
        
        # Learning rate for weight adjustments
        self.learning_rate = 0.01
        
        # Training session directory
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join("data", "rapid_fire_sessions", f"session_{self.session_timestamp}")
        os.makedirs(self.session_dir, exist_ok=True)
        os.makedirs(os.path.join(self.session_dir, "visualizations"), exist_ok=True)
        os.makedirs(os.path.join(self.session_dir, "data"), exist_ok=True)
        
        # Dashboard update interval
        self.dashboard_update_seconds = 15 * 60  # 15 minutes
        
        print(f"""
        ╔══════════════════════════════════════════════════════════════
        ║ 🚀 SIMPLE RAPID FIRE TRAINING SYSTEM INITIALIZED
        ║══════════════════════════════════════════════════════════════
        ║ Initial Capital: ${self.initial_capital:.2f}
        ║ Training Session: {self.session_timestamp}
        ║ Signals: {len(self.signals)}
        ║ Dashboard Updates: Every 15 minutes
        ║ Focus: Signal Weight Optimization & Performance Tracking
        ╚══════════════════════════════════════════════════════════════
        """)
    
    def collect_signal_data(self) -> Dict[str, float]:
        """
        Collect signal data from the bot's last signals
        
        Returns:
            Dictionary of signal values
        """
        # Get the latest signals from the bot
        signal_data = {}
        
        for symbol, data in self.bot.last_signals.items():
            # Extract module signals and convert to numerical values
            module_signals = data.get('modules', {})
            
            # Process all signals
            for signal_name in self.signals:
                if signal_name in module_signals:
                    signal = module_signals[signal_name]
                    if signal == 'BUY':
                        signal_data[signal_name] = 1.0
                    elif signal == 'SELL':
                        signal_data[signal_name] = -1.0
                    else:  # HOLD
                        signal_data[signal_name] = 0.0
                else:
                    signal_data[signal_name] = 0.0  # Default to HOLD
            
            # Only use the first symbol for now (simplification)
            break
        
        # If we have no signals yet, return zeros
        if not signal_data:
            signal_data = {signal: 0.0 for signal in self.signals}
        
        return signal_data
    
    def decide_action(self, signal_data: Dict[str, float]) -> str:
        """
        Decide the best action based on weighted signals
        
        Args:
            signal_data: Dictionary of signal values
            
        Returns:
            String representing action ('BUY', 'SELL', or 'HOLD')
        """
        # Calculate weighted sum of signals
        weighted_sum = 0
        for signal, value in signal_data.items():
            if signal in self.signal_weights:
                weighted_sum += value * self.signal_weights[signal]
        
        # Decide action based on weighted sum
        if weighted_sum > 0.3:
            return 'BUY'
        elif weighted_sum < -0.3:
            return 'SELL'
        else:
            return 'HOLD'
    
    def record_decision(self, signals: Dict[str, float], action: str, 
                        price: float, timestamp: datetime, symbol: str) -> None:
        """
        Record a trading decision for later evaluation
        
        Args:
            signals: The signal data that led to the decision
            action: The action taken ('BUY', 'SELL', or 'HOLD')
            price: The price at which the action was taken
            timestamp: The time of the decision
            symbol: The trading symbol
        """
        self.decision_history.append({
            'timestamp': timestamp,
            'signals': signals,
            'action': action,
            'price': price,
            'symbol': symbol,
            'evaluated': False
        })
        
        # If we have more than 1000 decisions, remove the oldest one
        if len(self.decision_history) > 1000:
            self.decision_history.pop(0)
    
    def evaluate_decisions(self, current_prices: Dict[str, float]) -> None:
        """
        Evaluate past decisions and update signal weights
        
        Args:
            current_prices: Dictionary of current prices by symbol
        """
        # Only evaluate decisions that are at least 5 minutes old and not already evaluated
        cutoff_time = datetime.now() - timedelta(minutes=5)
        
        successful_signals = {signal: [] for signal in self.signals}
        unsuccessful_signals = {signal: [] for signal in self.signals}
        
        for decision in self.decision_history:
            if decision['timestamp'] < cutoff_time and not decision.get('evaluated', False):
                symbol = decision.get('symbol', list(current_prices.keys())[0])
                current_price = current_prices.get(symbol, 0)
                
                if current_price > 0:
                    old_price = decision['price']
                    price_change_pct = (current_price - old_price) / old_price * 100
                    action = decision['action']
                    
                    # Determine if the decision was good
                    success = False
                    if action == 'BUY' and price_change_pct > 0:
                        success = True
                    elif action == 'SELL' and price_change_pct < 0:
                        success = True
                    elif action == 'HOLD' and abs(price_change_pct) < 0.5:
                        success = True
                    
                    # Update win/loss counters
                    if success:
                        self.wins += 1
                        # Record which signals contributed to successful decisions
                        for signal, value in decision['signals'].items():
                            if abs(value) > 0.01:  # Only count non-zero signals
                                successful_signals[signal].append(value)
                    else:
                        self.losses += 1
                        # Record which signals contributed to unsuccessful decisions
                        for signal, value in decision['signals'].items():
                            if abs(value) > 0.01:  # Only count non-zero signals
                                unsuccessful_signals[signal].append(value)
                    
                    self.total_trades += 1
                    
                    # Mark the decision as evaluated
                    decision['evaluated'] = True
                    decision['success'] = success
                    decision['current_price'] = current_price
                    decision['price_change_pct'] = price_change_pct
        
        # Update signal weights based on evaluation
        self._update_signal_weights(successful_signals, unsuccessful_signals)
    
    def _update_signal_weights(self, successful_signals: Dict[str, List[float]], 
                              unsuccessful_signals: Dict[str, List[float]]) -> None:
        """
        Update signal weights based on their success rate
        
        Args:
            successful_signals: Dictionary of signal values that led to successful decisions
            unsuccessful_signals: Dictionary of signal values that led to unsuccessful decisions
        """
        for signal in self.signals:
            successful = successful_signals.get(signal, [])
            unsuccessful = unsuccessful_signals.get(signal, [])
            
            if successful or unsuccessful:
                # Calculate average signal value for successful and unsuccessful decisions
                avg_success = sum(successful) / len(successful) if successful else 0
                avg_failure = sum(unsuccessful) / len(unsuccessful) if unsuccessful else 0
                
                # Calculate success rate
                total_occurrences = len(successful) + len(unsuccessful)
                success_rate = len(successful) / total_occurrences if total_occurrences > 0 else 0
                
                # Update weight based on success rate and signal correlation with success
                weight_adjustment = (success_rate - 0.5) * self.learning_rate
                if avg_success != 0 and avg_failure != 0:
                    # Further adjust based on the contrast between successful and unsuccessful signals
                    contrast = avg_success - avg_failure
                    weight_adjustment += contrast * self.learning_rate
                
                self.signal_weights[signal] += weight_adjustment
        
        # Ensure weights are positive
        for signal in self.signals:
            self.signal_weights[signal] = max(0.01, self.signal_weights[signal])
        
        # Normalize weights to sum to 1
        total_weight = sum(self.signal_weights.values())
        if total_weight > 0:
            for signal in self.signals:
                self.signal_weights[signal] /= total_weight
    
    def update_dashboard(self) -> None:
        """
        Update the dashboard with the latest performance metrics
        """
        timestamp = datetime.now()
        portfolio = self.bot.budget_manager.get_portfolio_status()
        
        # Calculate win rate
        win_rate = (self.wins / self.total_trades * 100) if self.total_trades > 0 else 0
        
        # Update dashboard data
        self.dashboard_data['timestamp'].append(timestamp)
        self.dashboard_data['capital'].append(portfolio['current_capital'])
        self.dashboard_data['win_rate'].append(win_rate)
        
        # Identify best and worst signals
        if self.signal_weights:
            best_signal = max(self.signal_weights.items(), key=lambda x: x[1])
            worst_signal = min(self.signal_weights.items(), key=lambda x: x[1])
            
            self.dashboard_data['best_signal'] = best_signal
            self.dashboard_data['worst_signal'] = worst_signal
        
        # Save dashboard data
        dashboard_file = os.path.join(self.session_dir, "data", "dashboard.json")
        with open(dashboard_file, 'w') as f:
            # Convert timestamps to strings for JSON serialization
            dashboard_json = {
                'timestamp': [t.isoformat() for t in self.dashboard_data['timestamp']],
                'capital': self.dashboard_data['capital'],
                'win_rate': self.dashboard_data['win_rate'],
                'best_signal': self.dashboard_data['best_signal'],
                'worst_signal': self.dashboard_data['worst_signal']
            }
            json.dump(dashboard_json, f, indent=2)
        
        # Save current signal weights
        weights_file = os.path.join(self.session_dir, "data", "signal_weights.json")
        with open(weights_file, 'w') as f:
            json.dump(self.signal_weights, f, indent=2)
        
        # Display dashboard
        self._display_dashboard()
    
    def _display_dashboard(self) -> None:
        """Display the current performance dashboard"""
        latest_idx = -1  # Get the most recent data
        
        if not self.dashboard_data['timestamp']:
            print("No dashboard data available yet.")
            return
        
        timestamp = self.dashboard_data['timestamp'][latest_idx]
        capital = self.dashboard_data['capital'][latest_idx]
        win_rate = self.dashboard_data['win_rate'][latest_idx]
        
        print(f"""
        ╔══════════════════════════════════════════════════════════════
        ║ 📊 SIMPLE RAPID FIRE TRAINING DASHBOARD
        ║══════════════════════════════════════════════════════════════
        ║ Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        ║ Current Capital: ${capital:.2f} ({(capital-self.initial_capital)/self.initial_capital*100:+.2f}%)
        ║ Win Rate: {win_rate:.1f}% ({self.wins}/{self.total_trades})
        ║ 
        ║ SIGNAL WEIGHTS:
        ║ {self._format_signal_weights()}
        ║ 
        ║ BEST SIGNAL: {self.dashboard_data['best_signal'][0] if self.dashboard_data['best_signal'] else 'N/A'} ({self.dashboard_data['best_signal'][1]:.4f} if self.dashboard_data['best_signal'] else 'N/A')
        ║ WORST SIGNAL: {self.dashboard_data['worst_signal'][0] if self.dashboard_data['worst_signal'] else 'N/A'} ({self.dashboard_data['worst_signal'][1]:.4f} if self.dashboard_data['worst_signal'] else 'N/A')
        ╚══════════════════════════════════════════════════════════════
        """)
    
    def _format_signal_weights(self) -> str:
        """Format signal weights for display"""
        result = ""
        for i, (signal, weight) in enumerate(sorted(self.signal_weights.items(), key=lambda x: x[1], reverse=True)):
            result += f"║ {signal}: {weight:.4f}"
            if i < len(self.signal_weights) - 1:
                result += "\n"
        return result
    
    def visualize_performance(self) -> None:
        """
        Generate performance visualizations
        """
        if len(self.dashboard_data['timestamp']) < 2:
            print("Not enough data for visualization yet.")
            return
        
        try:
            # Create visualization directory
            viz_dir = os.path.join(self.session_dir, "visualizations")
            os.makedirs(viz_dir, exist_ok=True)
            
            # Set up plots
            plt.figure(figsize=(12, 6))
            
            # Plot capital over time
            plt.subplot(1, 2, 1)
            plt.plot([t.timestamp() for t in self.dashboard_data['timestamp']], 
                    self.dashboard_data['capital'], 'b-')
            plt.title('Capital Over Time')
            plt.xlabel('Time')
            plt.ylabel('Capital ($)')
            plt.grid(True)
            
            # Plot win rate over time
            plt.subplot(1, 2, 2)
            plt.plot([t.timestamp() for t in self.dashboard_data['timestamp']], 
                    self.dashboard_data['win_rate'], 'g-')
            plt.title('Win Rate Over Time')
            plt.xlabel('Time')
            plt.ylabel('Win Rate (%)')
            plt.grid(True)
            
            # Save the figure
            plt.tight_layout()
            plt.savefig(os.path.join(viz_dir, 'performance_metrics.png'))
            
            # Plot signal weights
            plt.figure(figsize=(12, 8))
            signals = list(self.signal_weights.keys())
            weights = list(self.signal_weights.values())
            
            # Sort by weight for better visualization
            sorted_indices = np.argsort(weights)[::-1]
            sorted_signals = [signals[i] for i in sorted_indices]
            sorted_weights = [weights[i] for i in sorted_indices]
            
            bars = plt.bar(sorted_signals, sorted_weights)
            
            # Color best and worst signals
            if self.dashboard_data['best_signal'] and self.dashboard_data['worst_signal']:
                best_signal = self.dashboard_data['best_signal'][0]
                worst_signal = self.dashboard_data['worst_signal'][0]
                
                for i, signal in enumerate(sorted_signals):
                    if signal == best_signal:
                        bars[i].set_color('green')
                    elif signal == worst_signal:
                        bars[i].set_color('red')
            
            plt.title('Signal Weights')
            plt.xlabel('Signal')
            plt.ylabel('Weight')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.savefig(os.path.join(viz_dir, 'signal_weights.png'))
            
            plt.close('all')  # Close all figures to free memory
            
        except Exception as e:
            print(f"Error generating visualizations: {e}")
    
    def save_results(self) -> None:
        """Save the final training results"""
        results_file = os.path.join(self.session_dir, "training_results.json")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'duration_minutes': (datetime.now() - datetime.strptime(self.session_timestamp, "%Y%m%d_%H%M%S")).total_seconds() / 60,
            'initial_capital': self.initial_capital,
            'final_capital': self.dashboard_data['capital'][-1] if self.dashboard_data['capital'] else self.initial_capital,
            'return_pct': ((self.dashboard_data['capital'][-1] / self.initial_capital) - 1) * 100 if self.dashboard_data['capital'] else 0,
            'trades': self.total_trades,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': self.dashboard_data['win_rate'][-1] if self.dashboard_data['win_rate'] else 0,
            'signal_weights': self.signal_weights,
            'best_signal': self.dashboard_data['best_signal'],
            'worst_signal': self.dashboard_data['worst_signal']
        }
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to {results_file}")
    
    def run_training_cycle(self) -> None:
        """Run a single training cycle"""
        timestamp = datetime.now()
        
        # Run the bot for one cycle
        self.bot.run_once(timestamp=timestamp.isoformat())
        
        # Collect signal data
        signal_data = self.collect_signal_data()
        
        # Get current prices from market data
        market_data = self.bot.get_latest_market_data()
        current_prices = {}
        for symbol, data in market_data.items():
            current_prices[symbol] = data.get("last", 0)
        
        # Use the first symbol for simplicity
        symbol = self.bot.symbols[0] if self.bot.symbols else "UNKNOWN"
        current_price = current_prices.get(symbol, 0)
        
        # Decide action
        action = self.decide_action(signal_data)
        
        # Record the decision
        self.record_decision(signal_data, action, current_price, timestamp, symbol)
        
        # Evaluate past decisions
        self.evaluate_decisions(current_prices)
        
        return symbol, current_price, action
    
    def run_training(self, duration_minutes: int = 30, cycle_seconds: int = 30) -> None:
        """
        Run the training session for the specified duration
        
        Args:
            duration_minutes: Duration of the training session in minutes
            cycle_seconds: Seconds between training cycles
        """
        print(f"Starting {duration_minutes}-minute training session...")
        print(f"Training cycles every {cycle_seconds} seconds")
        print(f"Dashboard updates every {self.dashboard_update_seconds // 60} minutes")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        last_dashboard_update = start_time
        
        try:
            while time.time() < end_time:
                cycle_start = time.time()
                
                # Run a training cycle
                symbol, price, action = self.run_training_cycle()
                
                # Update dashboard if needed
                if time.time() - last_dashboard_update >= self.dashboard_update_seconds:
                    self.update_dashboard()
                    self.visualize_performance()
                    last_dashboard_update = time.time()
                
                # Print cycle results
                remaining_time = end_time - time.time()
                minutes = int(remaining_time // 60)
                seconds = int(remaining_time % 60)
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {symbol}: ${price:.2f} | {action} | Remaining: {minutes}m {seconds}s")
                
                # Wait for next cycle
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0.1, cycle_seconds - cycle_duration)
                time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            print("\nTraining session interrupted by user.")
        
        # Final dashboard update and results save
        self.update_dashboard()
        self.visualize_performance()
        self.save_results()
        
        print(f"""
        ╔══════════════════════════════════════════════════════════════
        ║ 🎓 SIMPLE RAPID FIRE TRAINING COMPLETED
        ║══════════════════════════════════════════════════════════════
        ║ Final Capital: ${self.dashboard_data['capital'][-1]:.2f} ({(self.dashboard_data['capital'][-1]-self.initial_capital)/self.initial_capital*100:+.2f}%)
        ║ Win Rate: {self.dashboard_data['win_rate'][-1]:.1f}%
        ║ Total Trades: {self.total_trades}
        ║ Session Results Saved To: {self.session_dir}
        ╚══════════════════════════════════════════════════════════════
        """)


def main():
    """Main function to run the SimpleRapidFireTrainer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Simple Rapid Fire Training (No TensorFlow)")
    parser.add_argument("--duration", type=int, default=30,
                        help="Duration of training in minutes (default: 30)")
    parser.add_argument("--cycle", type=int, default=30,
                        help="Seconds between training cycles (default: 30)")
    parser.add_argument("--capital", type=float, default=1000.0,
                        help="Initial paper trading capital (default: $1000)")
    parser.add_argument("--config", type=str, default="config/config.yaml",
                        help="Path to configuration file (default: config/config.yaml)")
    
    args = parser.parse_args()
    
    # Create and run the trainer
    trainer = SimpleRapidFireTrainer(
        config_path=args.config,
        initial_capital=args.capital
    )
    
    trainer.run_training(
        duration_minutes=args.duration,
        cycle_seconds=args.cycle
    )


if __name__ == "__main__":
    main()