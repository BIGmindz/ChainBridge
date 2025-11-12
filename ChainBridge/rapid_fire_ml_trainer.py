#!/usr/bin/env python3
"""
RAPID FIRE ML TRAINING SYSTEM

A 30-minute intensive paper trading simulation with $1000
Real-time learning, pattern recognition, and decision tracking
Dashboard updates every 15 minutes

This system integrates with the existing MultiSignalBot architecture
to provide accelerated learning and optimization of signal weights.
"""

import os

import numpy as np

# TensorFlow imports - wrapped in try-except for optional dependency
try:
    import tensorflow as tf  # noqa: F401
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.optimizers import Adam

    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow not available. Rapid Fire ML Trainer will be disabled.")
import json
import time
import warnings
from datetime import datetime, timedelta
from typing import Dict

import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

from budget_manager import BudgetManager  # noqa: E402

# Import from the existing bot architecture
from MultiSignalBot import MultiSignalBot  # noqa: E402


class RapidFireMLTrainer:
    """
    30-minute intensive ML training system
    Paper trades with $1000, learns patterns in real-time
    Tracks wins/losses with emphasis on learning from mistakes
    """

    def __init__(
        self, config_path: str = "config/config.yaml", initial_capital: float = 1000.0
    ):
        """
        Initialize the RapidFireMLTrainer system

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

        # ML Brain
        self.model = self._build_ml_model()
        self.pattern_memory = []
        self.decision_history = []

        # Performance tracking
        self.wins = 0
        self.losses = 0
        self.total_trades = 0
        self.loss_patterns = []  # CRITICAL: Learn from losses
        self.win_patterns = []

        # Dashboard data
        self.dashboard_data = {
            "timestamp": [],
            "capital": [],
            "win_rate": [],
            "patterns_learned": [],
            "confidence": [],
            "best_signal": None,
            "worst_signal": None,
        }

        # Signal sources (all 15 signals from the existing bot)
        self.signals = [
            "RSI",
            "MACD",
            "Bollinger",
            "Volume",
            "Sentiment",
            "Port_Congestion",
            "Diesel",
            "Supply_Chain",
            "Container",
            "Inflation",
            "Regulatory",
            "Remittance",
            "CBDC",
            "FATF",
            "Chainalysis_Global",
        ]

        # Signal weights (will be dynamically adjusted)
        self.signal_weights = {
            signal: 1.0 / len(self.signals) for signal in self.signals
        }

        # Learning rate for weight adjustments
        self.learning_rate = 0.01

        # Training session directory
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = os.path.join(
            "data", "rapid_fire_sessions", f"session_{self.session_timestamp}"
        )
        os.makedirs(self.session_dir, exist_ok=True)
        os.makedirs(os.path.join(self.session_dir, "models"), exist_ok=True)
        os.makedirs(os.path.join(self.session_dir, "visualizations"), exist_ok=True)
        os.makedirs(os.path.join(self.session_dir, "data"), exist_ok=True)

        # Dashboard update interval
        self.dashboard_update_seconds = 15 * 60  # 15 minutes

        print(
            f"""
        ╔══════════════════════════════════════════════════════════════
        ║ 🚀 RAPID FIRE ML TRAINING SYSTEM INITIALIZED
        ║══════════════════════════════════════════════════════════════
        ║ Initial Capital: ${self.initial_capital:.2f}
        ║ Training Session: {self.session_timestamp}
        ║ Signals: {len(self.signals)}
        ║ Dashboard Updates: Every 15 minutes
        ║ Learning Focus: Pattern Recognition & Signal Optimization
        ╚══════════════════════════════════════════════════════════════
        """
        )

    def _build_ml_model(self) -> Sequential:
        """
        Build the TensorFlow model for signal pattern recognition

        Returns:
            A compiled TensorFlow Sequential model
        """
        model = Sequential(
            [
                Dense(64, activation="relu", input_shape=(15,)),  # 15 signals
                Dropout(0.2),
                Dense(32, activation="relu"),
                Dropout(0.2),
                Dense(16, activation="relu"),
                Dense(3, activation="softmax"),  # BUY, SELL, HOLD
            ]
        )

        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss="categorical_crossentropy",
            metrics=["accuracy"],
        )

        return model

    def _build_lstm_model(self) -> Sequential:
        """
        Build an LSTM model for time series pattern recognition

        Returns:
            A compiled TensorFlow LSTM model
        """
        model = Sequential(
            [
                LSTM(
                    64, return_sequences=True, input_shape=(10, 15)
                ),  # 10 time steps, 15 features
                Dropout(0.2),
                LSTM(32),
                Dropout(0.2),
                Dense(16, activation="relu"),
                Dense(3, activation="softmax"),  # BUY, SELL, HOLD
            ]
        )

        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss="categorical_crossentropy",
            metrics=["accuracy"],
        )

        return model

    def collect_signal_data(self) -> np.ndarray:
        """
        Collect signal data from the bot's last signals

        Returns:
            Numpy array of normalized signal values
        """
        # Get the latest signals from the bot
        signal_data = []

        for symbol, data in self.bot.last_signals.items():
            # Extract module signals and convert to numerical values
            module_signals = data.get("modules", {})
            signal_values = []

            # Process technical signals
            for signal_name in ["RSI", "MACD", "Bollinger", "Volume", "Sentiment"]:
                if signal_name in module_signals:
                    signal = module_signals[signal_name]
                    if signal == "BUY":
                        signal_values.append(1.0)  # type: ignore
                    elif signal == "SELL":
                        signal_values.append(-1.0)  # type: ignore
                    else:  # HOLD
                        signal_values.append(0.0)  # type: ignore
                else:
                    signal_values.append(0.0)  # Default to HOLD  # type: ignore

            # Process logistics signals
            for signal_name in [
                "Port_Congestion",
                "Diesel",
                "Supply_Chain",
                "Container",
            ]:
                if signal_name in module_signals:
                    signal = module_signals[signal_name]
                    if signal == "BUY":
                        signal_values.append(1.0)  # type: ignore
                    elif signal == "SELL":
                        signal_values.append(-1.0)  # type: ignore
                    else:  # HOLD
                        signal_values.append(0.0)  # type: ignore
                else:
                    signal_values.append(0.0)  # Default to HOLD  # type: ignore

            # Process global macro signals
            for signal_name in [
                "Inflation",
                "Regulatory",
                "Remittance",
                "CBDC",
                "FATF",
            ]:
                if signal_name in module_signals:
                    signal = module_signals[signal_name]
                    if signal == "BUY":
                        signal_values.append(1.0)  # type: ignore
                    elif signal == "SELL":
                        signal_values.append(-1.0)  # type: ignore
                    else:  # HOLD
                        signal_values.append(0.0)  # type: ignore
                else:
                    signal_values.append(0.0)  # Default to HOLD  # type: ignore

            # Process adoption signal
            if "AdoptionTracker" in module_signals:
                signal = module_signals["AdoptionTracker"]
                if signal == "BUY":
                    signal_values.append(1.0)  # type: ignore
                elif signal == "SELL":
                    signal_values.append(-1.0)  # type: ignore
                else:  # HOLD
                    signal_values.append(0.0)  # type: ignore
            else:
                signal_values.append(0.0)  # Default to HOLD  # type: ignore

            # Only use the first symbol for now (simplification)
            # In a full implementation, you'd process all symbols
            signal_data = signal_values
            break

        # If we have no signals yet, return zeros
        if not signal_data:
            signal_data = [0.0] * 15

        return np.array(signal_data).reshape(1, -1)  # Reshape for model input

    def predict_action(self, signal_data: np.ndarray) -> str:
        """
        Use the model to predict the best action

        Args:
            signal_data: Normalized signal data

        Returns:
            String representing action ('BUY', 'SELL', or 'HOLD')
        """
        prediction = self.model.predict(signal_data, verbose=0)[0]
        action_index = np.argmax(prediction)

        if action_index == 0:
            return "BUY"
        elif action_index == 1:
            return "SELL"
        else:
            return "HOLD"

    def record_decision(
        self, signals: np.ndarray, action: str, price: float, timestamp: datetime
    ) -> None:
        """
        Record a trading decision for later learning

        Args:
            signals: The signal data that led to the decision
            action: The action taken ('BUY', 'SELL', or 'HOLD')
            price: The price at which the action was taken
            timestamp: The time of the decision
        """
        self.decision_history.append(  # type: ignore
            {
                "timestamp": timestamp,
                "signals": signals.tolist(),  # type: ignore
                "action": action,
                "price": price,
            }
        )

        # If we have more than 1000 decisions, remove the oldest one
        if len(self.decision_history) > 1000:
            self.decision_history.pop(0)

    def evaluate_decision(self, decision_index: int, current_price: float) -> float:
        """
        Evaluate a past decision and calculate reward

        Args:
            decision_index: Index of the decision in decision_history
            current_price: Current price for evaluation

        Returns:
            Reward value (positive for good decisions, negative for bad ones)
        """
        if decision_index >= len(self.decision_history):
            return 0.0

        decision = self.decision_history[decision_index]
        action = decision["action"]
        old_price = decision["price"]
        price_change_pct = (current_price - old_price) / old_price * 100

        # Calculate reward based on action and price change
        if action == "BUY":
            reward = price_change_pct  # Positive if price went up
        elif action == "SELL":
            reward = -price_change_pct  # Positive if price went down
        else:  # HOLD
            reward = (
                0.1 if abs(price_change_pct) < 0.5 else -0.1
            )  # Small positive reward for HOLD in stable price

        # Record win/loss
        if reward > 0:
            self.wins += 1
            self.win_patterns.append(decision["signals"])  # type: ignore
        elif reward < 0:
            self.losses += 1
            self.loss_patterns.append(decision["signals"])  # type: ignore

        self.total_trades += 1

        return reward

    def learn_from_decisions(self, current_prices: Dict[str, float]) -> None:
        """
        Learn from past decisions by evaluating their outcomes

        Args:
            current_prices: Dictionary of current prices by symbol
        """
        # Only evaluate decisions that are at least 5 minutes old
        cutoff_time = datetime.now() - timedelta(minutes=5)

        training_data = []
        training_labels = []

        for i, decision in enumerate(self.decision_history):
            decision_time = decision["timestamp"]
            if decision_time < cutoff_time:
                symbol = decision.get("symbol", list(current_prices.keys())[0])  # type: ignore
                current_price = current_prices.get(symbol, 0)

                if current_price > 0:
                    # Evaluate the decision
                    reward = self.evaluate_decision(i, current_price)

                    # Convert signals to training data
                    signals = np.array(decision["signals"])
                    action = decision["action"]

                    # Create one-hot encoded label
                    label = [0, 0, 0]  # BUY, SELL, HOLD
                    if reward > 0:  # It was a good decision
                        if action == "BUY":
                            label[0] = 1
                        elif action == "SELL":
                            label[1] = 1
                        else:  # HOLD
                            label[2] = 1
                    else:  # It was a bad decision, learn the opposite
                        if action == "BUY":
                            label[1] = 1  # Should have SOLD
                        elif action == "SELL":
                            label[0] = 1  # Should have BOUGHT
                        else:  # HOLD
                            # Determine if we should have bought or sold
                            price_change = (
                                current_price - decision["price"]
                            ) / decision["price"]
                            if price_change > 0.01:
                                label[0] = 1  # Should have BOUGHT
                            elif price_change < -0.01:
                                label[1] = 1  # Should have SOLD
                            else:
                                label[2] = 1  # HOLD was actually correct

                    training_data.append(signals)  # type: ignore
                    training_labels.append(label)  # type: ignore

        # If we have enough training data, update the model
        if len(training_data) >= 10:
            X = np.array(training_data)
            y = np.array(training_labels)

            # Train the model
            self.model.fit(X, y, epochs=5, batch_size=min(32, len(X)), verbose=0)

            # Update pattern memory
            self.pattern_memory.extend(training_data)
            if len(self.pattern_memory) > 1000:
                self.pattern_memory = self.pattern_memory[
                    -1000:
                ]  # Keep only the most recent 1000

    def update_signal_weights(self) -> None:
        """
        Update signal weights based on their correlation with successful outcomes
        """
        if not self.win_patterns or not self.loss_patterns:
            return

        win_patterns = np.array(self.win_patterns)
        loss_patterns = np.array(self.loss_patterns)

        # Calculate the mean for each signal in win and loss patterns
        win_means = np.mean(win_patterns, axis=0)
        loss_means = np.mean(loss_patterns, axis=0)

        # Calculate new weights based on the difference
        for i, signal in enumerate(self.signals):
            if i < len(win_means) and i < len(loss_means):
                # Higher weight for signals that are more positive in wins and more negative in losses
                weight_adjustment = (win_means[i] - loss_means[i]) * self.learning_rate
                self.signal_weights[signal] += weight_adjustment

        # Normalize weights to sum to 1
        total_weight = sum(self.signal_weights.values())  # type: ignore
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

        # Calculate patterns learned
        patterns_learned = len(self.pattern_memory)

        # Calculate confidence score (based on model accuracy)
        confidence = min(
            100, patterns_learned / 10
        )  # Simple metric: 10 patterns = 1% confidence

        # Update dashboard data
        self.dashboard_data["timestamp"].append(timestamp)  # type: ignore
        self.dashboard_data["capital"].append(portfolio["current_capital"])  # type: ignore
        self.dashboard_data["win_rate"].append(win_rate)  # type: ignore
        self.dashboard_data["patterns_learned"].append(patterns_learned)  # type: ignore
        self.dashboard_data["confidence"].append(confidence)  # type: ignore

        # Identify best and worst signals
        if self.signal_weights:
            best_signal = max(self.signal_weights.items(), key=lambda x: x[1])
            worst_signal = min(self.signal_weights.items(), key=lambda x: x[1])

            self.dashboard_data["best_signal"] = best_signal
            self.dashboard_data["worst_signal"] = worst_signal

        # Save dashboard data
        dashboard_file = os.path.join(self.session_dir, "data", "dashboard.json")
        with open(dashboard_file, "w") as f:
            # Convert timestamps to strings for JSON serialization
            dashboard_json = {
                "timestamp": [t.isoformat() for t in self.dashboard_data["timestamp"]],
                "capital": self.dashboard_data["capital"],
                "win_rate": self.dashboard_data["win_rate"],
                "patterns_learned": self.dashboard_data["patterns_learned"],
                "confidence": self.dashboard_data["confidence"],
                "best_signal": self.dashboard_data["best_signal"],
                "worst_signal": self.dashboard_data["worst_signal"],
            }
            json.dump(dashboard_json, f, indent=2)

        # Display dashboard
        self._display_dashboard()

    def _display_dashboard(self) -> None:
        """Display the current performance dashboard"""
        latest_idx = -1  # Get the most recent data

        if not self.dashboard_data["timestamp"]:
            print("No dashboard data available yet.")
            return

        timestamp = self.dashboard_data["timestamp"][latest_idx]
        capital = self.dashboard_data["capital"][latest_idx]
        win_rate = self.dashboard_data["win_rate"][latest_idx]
        patterns_learned = self.dashboard_data["patterns_learned"][latest_idx]
        confidence = self.dashboard_data["confidence"][latest_idx]

        print(
            f"""
        ╔══════════════════════════════════════════════════════════════
        ║ 📊 RAPID FIRE ML TRAINING DASHBOARD
        ║══════════════════════════════════════════════════════════════
        ║ Timestamp: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}
        ║ Current Capital: ${capital:.2f} ({(capital - self.initial_capital) / self.initial_capital * 100:+.2f}%)
        ║ Win Rate: {win_rate:.1f}% ({self.wins}/{self.total_trades})
        ║ Patterns Learned: {patterns_learned}
        ║ Model Confidence: {confidence:.1f}%
        ║
        ║ SIGNAL WEIGHTS:
        ║ {self._format_signal_weights()}
        ║
        ║ BEST SIGNAL: {self.dashboard_data["best_signal"][0] if self.dashboard_data["best_signal"] else "N/A"} ({self.dashboard_data["best_signal"][1]:.4f} if self.dashboard_data['best_signal'] else 'N/A')
        ║ WORST SIGNAL: {self.dashboard_data["worst_signal"][0] if self.dashboard_data["worst_signal"] else "N/A"} ({self.dashboard_data["worst_signal"][1]:.4f} if self.dashboard_data['worst_signal'] else 'N/A')
        ╚══════════════════════════════════════════════════════════════
        """
        )

    def _format_signal_weights(self) -> str:
        """Format signal weights for display"""
        result = ""
        for i, (signal, weight) in enumerate(
            sorted(self.signal_weights.items(), key=lambda x: x[1], reverse=True)
        ):
            result += f"║ {signal}: {weight:.4f}"
            if i < len(self.signal_weights) - 1:
                result += "\n"
        return result

    def visualize_performance(self) -> None:
        """
        Generate performance visualizations
        """
        if len(self.dashboard_data["timestamp"]) < 2:
            print("Not enough data for visualization yet.")
            return

        # Create visualization directory
        viz_dir = os.path.join(self.session_dir, "visualizations")
        os.makedirs(viz_dir, exist_ok=True)

        # Convert timestamps to matplotlib dates
        dates = self.dashboard_data["timestamp"]

        # Set up plots
        fig, axs = plt.subplots(2, 2, figsize=(16, 12))

        # Plot capital over time
        axs[0, 0].plot(dates, self.dashboard_data["capital"], "b-")
        axs[0, 0].set_title("Capital Over Time")
        axs[0, 0].set_xlabel("Time")
        axs[0, 0].set_ylabel("Capital ($)")
        axs[0, 0].grid(True)

        # Plot win rate over time
        axs[0, 1].plot(dates, self.dashboard_data["win_rate"], "g-")
        axs[0, 1].set_title("Win Rate Over Time")
        axs[0, 1].set_xlabel("Time")
        axs[0, 1].set_ylabel("Win Rate (%)")
        axs[0, 1].grid(True)

        # Plot patterns learned over time
        axs[1, 0].plot(dates, self.dashboard_data["patterns_learned"], "r-")
        axs[1, 0].set_title("Patterns Learned Over Time")
        axs[1, 0].set_xlabel("Time")
        axs[1, 0].set_ylabel("Number of Patterns")
        axs[1, 0].grid(True)

        # Plot confidence over time
        axs[1, 1].plot(dates, self.dashboard_data["confidence"], "m-")
        axs[1, 1].set_title("Model Confidence Over Time")
        axs[1, 1].set_xlabel("Time")
        axs[1, 1].set_ylabel("Confidence (%)")
        axs[1, 1].grid(True)

        # Adjust layout and save
        plt.tight_layout()
        plt.savefig(os.path.join(viz_dir, "performance_metrics.png"))

        # Plot signal weights
        plt.figure(figsize=(12, 8))
        signals = list(self.signal_weights.keys())  # type: ignore
        weights = list(self.signal_weights.values())  # type: ignore

        # Sort by weight for better visualization
        sorted_indices = np.argsort(weights)[::-1]
        sorted_signals = [signals[i] for i in sorted_indices]
        sorted_weights = [weights[i] for i in sorted_indices]

        bars = plt.bar(sorted_signals, sorted_weights)

        # Color best and worst signals
        if self.dashboard_data["best_signal"] and self.dashboard_data["worst_signal"]:
            best_signal = self.dashboard_data["best_signal"][0]
            worst_signal = self.dashboard_data["worst_signal"][0]

            for i, signal in enumerate(sorted_signals):
                if signal == best_signal:
                    bars[i].set_color("green")
                elif signal == worst_signal:
                    bars[i].set_color("red")

        plt.title("Signal Weights")
        plt.xlabel("Signal")
        plt.ylabel("Weight")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(viz_dir, "signal_weights.png"))

        plt.close("all")  # Close all figures to free memory

    def save_model(self) -> None:
        """Save the trained model and weights"""
        model_dir = os.path.join(self.session_dir, "models")

        # Save TensorFlow model
        model_path = os.path.join(model_dir, "rapid_fire_model")
        self.model.save(model_path)

        # Save signal weights
        weights_path = os.path.join(model_dir, "signal_weights.json")
        with open(weights_path, "w") as f:
            json.dump(self.signal_weights, f, indent=2)

        print(f"Model and weights saved to {model_dir}")

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

        # Predict action
        action = self.predict_action(signal_data)

        # Record the decision
        self.record_decision(signal_data, action, current_price, timestamp)

        # Learn from past decisions
        self.learn_from_decisions(current_prices)

        # Update signal weights
        self.update_signal_weights()

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

                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] {symbol}: ${price:.2f} | {action} | Remaining: {minutes}m {seconds}s"
                )

                # Wait for next cycle
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0.1, cycle_seconds - cycle_duration)
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\nTraining session interrupted by user.")

        # Final dashboard update and model save
        self.update_dashboard()
        self.visualize_performance()
        self.save_model()

        print(
            f"""
        ╔══════════════════════════════════════════════════════════════
        ║ 🎓 RAPID FIRE ML TRAINING COMPLETED
        ║══════════════════════════════════════════════════════════════
        ║ Final Capital: ${self.dashboard_data["capital"][-1]:.2f} ({(self.dashboard_data["capital"][-1] - self.initial_capital) / self.initial_capital * 100:+.2f}%)
        ║ Win Rate: {self.dashboard_data["win_rate"][-1]:.1f}%
        ║ Patterns Learned: {self.dashboard_data["patterns_learned"][-1]}
        ║ Model Confidence: {self.dashboard_data["confidence"][-1]:.1f}%
        ║ Session Results Saved To: {self.session_dir}
        ╚══════════════════════════════════════════════════════════════
        """
        )


def main():
    """Main function to run the RapidFireMLTrainer"""
    import argparse

    parser = argparse.ArgumentParser(description="Run a Rapid Fire ML Training Session")
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration of training in minutes (default: 30)",
    )
    parser.add_argument(
        "--cycle",
        type=int,
        default=30,
        help="Seconds between training cycles (default: 30)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1000.0,
        help="Initial paper trading capital (default: $1000)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)",
    )

    args = parser.parse_args()

    # Create and run the trainer
    trainer = RapidFireMLTrainer(config_path=args.config, initial_capital=args.capital)

    trainer.run_training(duration_minutes=args.duration, cycle_seconds=args.cycle)


if __name__ == "__main__":
    main()
