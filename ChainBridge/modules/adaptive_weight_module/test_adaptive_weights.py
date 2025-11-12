#!/usr/bin/env python3
"""
Adaptive Weight Testing and Validation

This script provides tools to test and validate the adaptive weight model,
ensuring it correctly optimizes signal weights based on market conditions.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict

import matplotlib.pyplot as plt
import numpy as np

# Set up paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # type: ignore

# Import the modules to test
from modules.adaptive_weight_module.adaptive_weight_model import AdaptiveWeightModule
from modules.adaptive_weight_module.market_condition_classifier import (
    MarketConditionClassifier,
)
from modules.adaptive_weight_module.market_regime_integrator import (
    MarketRegimeIntegrator,
)
from modules.adaptive_weight_module.weight_visualizer import AdaptiveWeightVisualizer


class AdaptiveWeightTester:
    """
    Testing and validation tools for the adaptive weight model
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the tester"""
        self.config = config or {}

        # Initialize components
        self.weight_model = AdaptiveWeightModule(self.config)
        self.regime_classifier = MarketConditionClassifier(self.config)
        self.regime_integrator = MarketRegimeIntegrator(self.config)
        self.visualizer = AdaptiveWeightVisualizer(self.config)

        # Results directory
        self.results_dir = os.path.join(
            self.config.get("results_dir", "test_results"), "adaptive_weight_tests"
        )
        os.makedirs(self.results_dir, exist_ok=True)

        # Configure test settings
        self.test_scenarios = self.config.get(
            "test_scenarios",
            ["bull_market", "bear_market", "sideways_market", "volatile_market"],
        )

        # Set up sample data
        self._setup_sample_data()

    def _setup_sample_data(self) -> None:
        """Set up sample data for testing"""
        self.sample_data = {}

        # Generate price data for different market scenarios
        self._generate_price_scenarios()

        # Generate signal data for different scenarios
        self._generate_signal_scenarios()

    def _generate_price_scenarios(self) -> None:
        """Generate price data for different market scenarios"""
        # Base parameters
        days = 30
        base_price = 20000.0

        # Generate timestamps
        timestamps = [
            (datetime.now() - timedelta(days=days - i)).isoformat()
            for i in range(days + 1)
        ]

        # Bull market - strong uptrend
        bull_prices = [
            base_price * (1 + 0.02 * i + np.random.normal(0, 0.01))
            for i in range(days + 1)
        ]

        # Bear market - strong downtrend
        bear_prices = [
            base_price * (1 - 0.015 * i + np.random.normal(0, 0.01))
            for i in range(days + 1)
        ]

        # Sideways market - range-bound
        sideways_prices = [
            base_price * (1 + np.sin(i / 5) * 0.03 + np.random.normal(0, 0.005))
            for i in range(days + 1)
        ]

        # Volatile market - large swings
        volatile_prices = [
            base_price * (1 + np.sin(i / 3) * 0.08 + np.random.normal(0, 0.02))
            for i in range(days + 1)
        ]

        # Store scenarios
        self.sample_data["bull_market"] = {
            "price_history": bull_prices,
            "timestamps": timestamps,
            "expected_regime": "BULL",
        }

        self.sample_data["bear_market"] = {
            "price_history": bear_prices,
            "timestamps": timestamps,
            "expected_regime": "BEAR",
        }

        self.sample_data["sideways_market"] = {
            "price_history": sideways_prices,
            "timestamps": timestamps,
            "expected_regime": "SIDEWAYS",
        }

        self.sample_data["volatile_market"] = {
            "price_history": volatile_prices,
            "timestamps": timestamps,
            "expected_regime": "VOLATILE",
        }

        # Generate volume data
        for scenario in self.sample_data.values():
            # Volume somewhat correlated with price changes
            price_changes = np.diff(scenario["price_history"])
            base_volume = 1000.0

            # Generate volumes (higher on bigger price moves)
            volumes = [
                base_volume
                * (1 + 2 * abs(change) / base_price + np.random.normal(0, 0.1))
                for change in price_changes
            ]

            # Add first volume point
            volumes = [base_volume] + volumes

            scenario["volume_history"] = volumes

    def _generate_signal_scenarios(self) -> None:
        """Generate signal data for different scenarios"""
        # Define signal layers and names
        signal_layers = {
            "LAYER_1_TECHNICAL": ["RSI", "MACD", "Bollinger", "Volume", "Sentiment"],
            "LAYER_2_LOGISTICS": [
                "Port_Congestion",
                "Diesel",
                "Supply_Chain",
                "Container",
            ],
            "LAYER_3_GLOBAL_MACRO": [
                "Inflation",
                "Regulatory",
                "Remittance",
                "CBDC",
                "FATF",
            ],
            "LAYER_4_ADOPTION": ["Chainalysis_Global"],
        }

        # Define scenario-specific signal biases
        signal_biases = {
            "bull_market": {
                "LAYER_1_TECHNICAL": 0.7,  # Technical signals strong in bull markets
                "LAYER_2_LOGISTICS": 0.2,
                "LAYER_3_GLOBAL_MACRO": 0.0,
                "LAYER_4_ADOPTION": 0.8,  # Adoption signals strong in bull markets
            },
            "bear_market": {
                "LAYER_1_TECHNICAL": -0.6,  # Technical signals negative in bear markets
                "LAYER_2_LOGISTICS": -0.2,
                "LAYER_3_GLOBAL_MACRO": -0.5,
                "LAYER_4_ADOPTION": -0.1,
            },
            "sideways_market": {
                "LAYER_1_TECHNICAL": 0.1,  # Technical signals mixed in sideways markets
                "LAYER_2_LOGISTICS": 0.0,
                "LAYER_3_GLOBAL_MACRO": 0.2,
                "LAYER_4_ADOPTION": 0.0,
            },
            "volatile_market": {
                "LAYER_1_TECHNICAL": 0.0,  # Technical signals unreliable in volatile markets
                "LAYER_2_LOGISTICS": 0.3,  # Fundamentals more reliable in volatile markets
                "LAYER_3_GLOBAL_MACRO": 0.5,
                "LAYER_4_ADOPTION": 0.2,
            },
        }

        # Generate signal data for each scenario
        for scenario_name, scenario_data in self.sample_data.items():
            signal_data = {}

            # Get the biases for this scenario
            biases = signal_biases.get(scenario_name, {})

            # Generate signals for each layer
            for layer_name, signals in signal_layers.items():
                layer_bias = biases.get(layer_name, 0.0)
                layer_signals = {}

                # Generate each signal
                for signal_name in signals:
                    # Base signal with noise
                    signal_value = layer_bias + np.random.normal(0, 0.2)

                    # Clip to valid range
                    signal_value = max(-1.0, min(1.0, signal_value))

                    # Create signal object
                    layer_signals[signal_name] = {
                        "value": signal_value,
                        "strength": abs(signal_value),
                        "signal": (
                            "BUY"
                            if signal_value > 0.2
                            else ("SELL" if signal_value < -0.2 else "HOLD")
                        ),
                    }

                signal_data[layer_name] = layer_signals

            # Store signal data
            scenario_data["signal_data"] = signal_data

    def test_regime_detection(self) -> Dict[str, Any]:
        """
        Test market regime detection across different scenarios

        Returns:
            Dictionary with test results
        """
        results = {}

        # Test each scenario
        for scenario_name, scenario_data in self.sample_data.items():
            if scenario_name not in self.test_scenarios:
                continue

            price_history = scenario_data["price_history"]
            volume_history = scenario_data.get("volume_history")
            expected_regime = scenario_data.get("expected_regime")

            # Detect regime
            regime_results = self.regime_classifier.detect_regime(
                price_history, volume_history
            )
            detected_regime = regime_results.get("regime")
            confidence = regime_results.get("confidence", 0.0)

            # Store results
            results[scenario_name] = {
                "expected_regime": expected_regime,
                "detected_regime": detected_regime,
                "confidence": confidence,
                "correct": expected_regime == detected_regime,
                "regime_features": regime_results.get("features", {}),
            }

        # Calculate overall accuracy
        correct_count = sum(1 for r in results.values() if r.get("correct", False))  # type: ignore
        accuracy = correct_count / len(results) if results else 0.0

        summary = {
            "accuracy": accuracy,
            "scenarios_tested": len(results),
            "correct_classifications": correct_count,
            "scenario_results": results,
        }

        # Save results
        self._save_results("regime_detection_test", summary)

        return summary

    def test_weight_optimization(self) -> Dict[str, Any]:
        """
        Test signal weight optimization across different market regimes

        Returns:
            Dictionary with test results
        """
        results = {}

        # Test each scenario
        for scenario_name, scenario_data in self.sample_data.items():
            if scenario_name not in self.test_scenarios:
                continue

            price_history = scenario_data["price_history"]
            volume_history = scenario_data.get("volume_history")
            signal_data = scenario_data.get("signal_data", {})

            # Create market data
            market_data = {
                "price_history": price_history,
                "volume_history": volume_history,
            }

            # Add volatility features
            regime_features = self.regime_classifier.extract_features(
                price_history, volume_history
            )
            market_data.update(regime_features)

            # Detect regime first
            regime_results = self.regime_integrator.detect_regime(market_data)

            # Get optimized weights
            try:
                # Format input for weight model
                model_input = {
                    "signals": signal_data,
                    "market_data": market_data,
                    "timestamp": datetime.now().isoformat(),
                }

                # Process with weight model
                optimized_weights = self.weight_model.process(model_input)

                # Store results
                results[scenario_name] = {
                    "detected_regime": regime_results.get("regime"),
                    "regime_confidence": regime_results.get("confidence", 0.0),
                    "optimized_weights": optimized_weights.get("optimized_weights", {}),
                    "weight_insights": self._analyze_weights(
                        optimized_weights.get("optimized_weights", {}),
                        regime_results.get("regime"),
                    ),
                }

            except Exception as e:
                results[scenario_name] = {
                    "error": str(e),
                    "detected_regime": regime_results.get("regime"),
                    "regime_confidence": regime_results.get("confidence", 0.0),
                }

        # Save results
        self._save_results("weight_optimization_test", results)

        return results

    def _analyze_weights(
        self, weights: Dict[str, float], regime: str
    ) -> Dict[str, Any]:
        """Analyze weights for a specific regime"""
        # Define expected weight patterns
        expected_patterns = {
            "BULL": {
                "LAYER_1_TECHNICAL": "high",
                "LAYER_2_LOGISTICS": "low",
                "LAYER_3_GLOBAL_MACRO": "low",
                "LAYER_4_ADOPTION": "high",
            },
            "BEAR": {
                "LAYER_1_TECHNICAL": "medium",
                "LAYER_2_LOGISTICS": "medium",
                "LAYER_3_GLOBAL_MACRO": "high",
                "LAYER_4_ADOPTION": "medium",
            },
            "SIDEWAYS": {
                "LAYER_1_TECHNICAL": "high",
                "LAYER_2_LOGISTICS": "low",
                "LAYER_3_GLOBAL_MACRO": "low",
                "LAYER_4_ADOPTION": "low",
            },
            "VOLATILE": {
                "LAYER_1_TECHNICAL": "low",
                "LAYER_2_LOGISTICS": "medium",
                "LAYER_3_GLOBAL_MACRO": "high",
                "LAYER_4_ADOPTION": "medium",
            },
        }

        # Check if weights match expected patterns
        pattern = expected_patterns.get(regime, {})
        insights = {
            "highest_weight_layer": (
                max(weights.items(), key=lambda x: x[1])[0] if weights else "N/A"
            ),
            "lowest_weight_layer": (
                min(weights.items(), key=lambda x: x[1])[0] if weights else "N/A"
            ),
            "weight_spread": (
                max(weights.values()) - min(weights.values()) if weights else 0.0
            ),
            "matches_expected_pattern": True,
        }

        # Check each layer against expected pattern
        for layer, expected in pattern.items():
            weight = weights.get(layer, 0.0)

            if expected == "high" and weight < 1.1:
                insights["matches_expected_pattern"] = False
            elif expected == "low" and weight > 0.9:
                insights["matches_expected_pattern"] = False

        return insights

    def visualize_test_results(self, results: Dict[str, Any], test_type: str) -> str:
        """
        Create visualizations of test results

        Args:
            results: Test results dictionary
            test_type: Type of test ('regime_detection' or 'weight_optimization')

        Returns:
            Path to the saved visualization
        """
        if test_type == "regime_detection":
            return self._visualize_regime_detection(results)
        elif test_type == "weight_optimization":
            return self._visualize_weight_optimization(results)
        else:
            return ""

    def _visualize_regime_detection(self, results: Dict[str, Any]) -> str:
        """Visualize regime detection results"""
        # Extract data
        scenarios = list(results.get("scenario_results", {}).keys())  # type: ignore
        expected = [
            results["scenario_results"][s]["expected_regime"] for s in scenarios
        ]
        detected = [
            results["scenario_results"][s]["detected_regime"] for s in scenarios
        ]
        confidences = [results["scenario_results"][s]["confidence"] for s in scenarios]

        # Create figure
        plt.figure(figsize=(12, 8))

        # Plot expected vs detected regimes
        x = range(len(scenarios))
        width = 0.35

        # Create a mapping of regime names to numerical values
        regimes = sorted(set(expected + detected))
        regime_map = {r: i for i, r in enumerate(regimes)}

        # Convert regimes to numbers for plotting
        expected_nums = [regime_map[r] for r in expected]
        detected_nums = [regime_map[r] for r in detected]

        # Create bar chart
        plt.bar([i - width / 2 for i in x], expected_nums, width, label="Expected")
        plt.bar([i + width / 2 for i in x], detected_nums, width, label="Detected")

        # Add confidence as text
        for i, conf in enumerate(confidences):
            plt.text(i, detected_nums[i] + 0.1, f"{conf:.2f}", ha="center")

        # Configure plot
        plt.xlabel("Scenario")
        plt.ylabel("Market Regime")
        plt.title("Market Regime Detection Test Results")
        plt.xticks(x, scenarios, rotation=45)
        plt.yticks([regime_map[r] for r in regimes], regimes)
        plt.legend()
        plt.tight_layout()

        # Save figure
        output_path = os.path.join(self.results_dir, "regime_detection_results.png")
        plt.savefig(output_path)
        plt.close()

        return output_path

    def _visualize_weight_optimization(self, results: Dict[str, Any]) -> str:
        """Visualize weight optimization results"""
        # Extract data
        scenarios = list(results.keys())  # type: ignore
        regimes = [results[s].get("detected_regime", "UNKNOWN") for s in scenarios]

        # Extract weights by layer
        layers = [
            "LAYER_1_TECHNICAL",
            "LAYER_2_LOGISTICS",
            "LAYER_3_GLOBAL_MACRO",
            "LAYER_4_ADOPTION",
        ]
        weights_by_layer = {layer: [] for layer in layers}

        for scenario in scenarios:
            optimized_weights = results[scenario].get("optimized_weights", {})
            for layer in layers:
                weights_by_layer[layer].append(optimized_weights.get(layer, 0.0))  # type: ignore

        # Create figure
        plt.figure(figsize=(12, 8))

        # Create grouped bar chart
        x = range(len(scenarios))
        width = 0.2
        offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]

        for i, layer in enumerate(layers):
            plt.bar(
                [j + offsets[i] for j in x], weights_by_layer[layer], width, label=layer
            )

        # Configure plot
        plt.xlabel("Scenario (Market Regime)")
        plt.ylabel("Weight Multiplier")
        plt.title("Signal Weight Optimization by Market Regime")
        plt.xticks(x, [f"{s}\n({r})" for s, r in zip(scenarios, regimes)])
        plt.axhline(y=1.0, color="gray", linestyle="--")
        plt.legend()
        plt.tight_layout()

        # Save figure
        output_path = os.path.join(self.results_dir, "weight_optimization_results.png")
        plt.savefig(output_path)
        plt.close()

        return output_path

    def _save_results(self, test_name: str, results: Dict[str, Any]) -> None:
        """Save test results to file"""
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{test_name}.json"

        # Save results
        file_path = os.path.join(self.results_dir, filename)
        with open(file_path, "w") as f:
            json.dump(results, f, indent=2)

    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all tests and visualize results

        Returns:
            Dictionary with all test results
        """
        print("Testing adaptive weight model...")

        # Run regime detection tests
        print("Testing market regime detection...")
        regime_results = self.test_regime_detection()
        print(f"Regime detection accuracy: {regime_results['accuracy']:.2f}")

        # Run weight optimization tests
        print("Testing signal weight optimization...")
        weight_results = self.test_weight_optimization()

        # Create visualizations
        print("Creating visualizations...")
        regime_viz = self.visualize_test_results(regime_results, "regime_detection")
        weight_viz = self.visualize_test_results(weight_results, "weight_optimization")

        # Return all results
        return {
            "regime_detection": regime_results,
            "weight_optimization": weight_results,
            "visualizations": {
                "regime_detection": regime_viz,
                "weight_optimization": weight_viz,
            },
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """Main entry point"""
    # Load configuration
    config_path = os.path.join("config", "adaptive_weight_config.json")
    config = {}

    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config: {str(e)}")

    # Create tester and run all tests
    tester = AdaptiveWeightTester(config)
    results = tester.run_all_tests()

    # Print summary
    print("\nTest Summary:")
    print(f"Regime Detection Accuracy: {results['regime_detection']['accuracy']:.2f}")
    print(
        f"Correct Classifications: {results['regime_detection']['correct_classifications']}/{results['regime_detection']['scenarios_tested']}"
    )
    print(f"Visualization saved to: {results['visualizations']['weight_optimization']}")

    return results


if __name__ == "__main__":
    main()
