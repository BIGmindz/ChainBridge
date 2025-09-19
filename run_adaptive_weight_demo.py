#!/usr/bin/env python3
"""
Run Adaptive Weight Model Demo

This script demonstrates the adaptive weight model functionality,
showing how it detects market regimes and optimizes signal weights.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any

# Set up paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules
from modules.adaptive_weight_module.market_condition_classifier import MarketConditionClassifier
from modules.adaptive_weight_module.market_regime_integrator import MarketRegimeIntegrator
from modules.adaptive_weight_module.adaptive_weight_model import AdaptiveWeightModule
from modules.adaptive_weight_module.weight_visualizer import AdaptiveWeightVisualizer
from modules.adaptive_weight_module.test_adaptive_weights import AdaptiveWeightTester


def load_demo_data(data_file: str = None) -> Dict[str, Any]:
    """
    Load or generate demo data for testing
    
    Args:
        data_file: Optional path to data file
        
    Returns:
        Dictionary with demo data
    """
    # If data file specified and exists, load it
    if data_file and os.path.exists(data_file):
        try:
            with open(data_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading data file: {str(e)}")
    
    # Generate demo data using tester
    print("Generating demo data...")
    tester = AdaptiveWeightTester()
    
    # Use the sample data already generated in tester
    return tester.sample_data


def run_demo(data: Dict[str, Any], output_dir: str, scenario: str = "bull_market") -> Dict[str, Any]:
    """
    Run the adaptive weight model demo
    
    Args:
        data: Dictionary with demo data
        output_dir: Directory for output files
        scenario: Market scenario to demonstrate
        
    Returns:
        Dictionary with demo results
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nRunning adaptive weight model demo for {scenario} scenario...")
    
    # Initialize components
    regime_classifier = MarketConditionClassifier()
    _regime_integrator = MarketRegimeIntegrator()
    weight_model = AdaptiveWeightModule()
    visualizer = AdaptiveWeightVisualizer({"output_dir": output_dir})
    
    # Get data for the specified scenario
    scenario_data = data.get(scenario, {})
    if not scenario_data:
        print(f"Error: No data available for {scenario} scenario")
        return {}
    
    # Extract data
    price_history = scenario_data.get("price_history", [])
    volume_history = scenario_data.get("volume_history", [])
    signal_data = scenario_data.get("signal_data", {})
    
    if not price_history:
        print("Error: No price history available")
        return {}
    
    # Create market data
    market_data = {
        "price_history": price_history,
        "volume_history": volume_history
    }
    
    # Step 1: Detect market regime
    print("\nStep 1: Detecting market regime...")
    regime_results = regime_classifier.detect_regime(price_history, volume_history)
    detected_regime = regime_results.get("regime")
    confidence = regime_results.get("confidence", 0.0)
    
    print(f"Detected market regime: {detected_regime} (confidence: {confidence:.2f})")
    print(f"Expected regime: {scenario_data.get('expected_regime', 'Unknown')}")
    
    # Print regime features
    features = regime_results.get("features", {})
    print("\nKey market features:")
    for feature, value in features.items():
        print(f"  {feature}: {value:.4f}")
    
    # Step 2: Get regime-specific weights
    print("\nStep 2: Getting regime-specific weights...")
    regime_weights = regime_classifier.get_regime_weights(detected_regime)
    
    print("\nRegime-specific signal layer weights:")
    for layer, weight in regime_weights.items():
        print(f"  {layer}: {weight:.2f}")
    
    # Step 3: Apply regime-specific weights to signals
    print("\nStep 3: Applying weights to signal layers...")
    
    # Format input for weight model
    model_input = {
        "signals": signal_data,
        "market_data": market_data,
        "timestamp": datetime.now().isoformat()
    }
    
    # Process with weight model
    weight_results = weight_model.process(model_input)
    
    # Extract optimized weights
    optimized_weights = weight_results.get("optimized_weights", {})
    
    print("\nOptimized weights after adaptive model processing:")
    for layer, weight in optimized_weights.items():
        print(f"  {layer}: {weight:.2f}")
    
    # Step 4: Create visualizations
    print("\nStep 4: Creating visualizations...")
    
    # Create regime visualization
    regime_viz = visualizer.plot_regime_history({
        "regime_history": {
            "regimes": [detected_regime] * 10,
            "timestamps": [(datetime.now() - timedelta(hours=i)).isoformat() for i in range(10)],
            "confidences": [confidence] * 10
        }
    })
    
    # Create weights visualization
    weight_viz = visualizer.plot_signal_importance(optimized_weights)
    
    print(f"\nVisualizations saved to {output_dir}")
    
    # Return all results
    return {
        "scenario": scenario,
        "regime_detection": regime_results,
        "regime_weights": regime_weights,
        "optimized_weights": optimized_weights,
        "visualizations": {
            "regime_history": regime_viz,
            "signal_importance": weight_viz
        },
        "timestamp": datetime.now().isoformat()
    }


def save_results(results: Dict[str, Any], output_dir: str) -> str:
    """
    Save demo results to file
    
    Args:
        results: Dictionary with demo results
        output_dir: Directory for output files
        
    Returns:
        Path to the saved results file
    """
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_demo_results.json"
    
    # Save results
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    return output_path


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run adaptive weight model demo")
    parser.add_argument("--scenario", "-s", choices=["bull_market", "bear_market", "sideways_market", "volatile_market"],
                        default="bull_market", help="Market scenario to demonstrate")
    parser.add_argument("--data-file", "-d", help="Path to data file")
    parser.add_argument("--output-dir", "-o", default="demo_results", help="Directory for output files")
    args = parser.parse_args()
    
    # Load or generate demo data
    data = load_demo_data(args.data_file)
    
    # Run demo
    results = run_demo(data, args.output_dir, args.scenario)
    
    # Save results
    if results:
        results_path = save_results(results, args.output_dir)
        print(f"\nDemo results saved to {results_path}")
    

if __name__ == "__main__":
    try:
        _demo_bot = AdaptiveWeightDemo()
        _demo_bot.run()
    except NameError:
        # AdaptiveWeightDemo is optional in this environment; run CLI main instead
        main()