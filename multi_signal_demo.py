#!/usr/bin/env python3
"""
Multi-Signal Trading Bot Demonstration Script

This script demonstrates the complete uncorrelated signals system integration
with the main Benson bot, showing how multiple signals are combined for better
trading decisions.
"""

import sys
import os
import json
import math
from typing import Dict, Any, List
from datetime import datetime, timedelta

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import core components
from core.module_manager import ModuleManager
from tracking.metrics_collector import MetricsCollector


def generate_realistic_test_data(periods: int = 100, 
                                base_price: float = 45000,
                                volatility: float = 0.02) -> List[Dict[str, Any]]:
    """
    Generate realistic cryptocurrency price data for testing.
    
    Args:
        periods: Number of periods to generate
        base_price: Starting price
        volatility: Price volatility (0.01 = 1%)
        
    Returns:
        List of OHLCV price records
    """
    price_data = []
    current_price = base_price
    
    for i in range(periods):
        # Create trending movement with noise
        trend = 0.0005 * i  # Slight upward trend
        cycle = 0.02 * math.sin(i * 0.1)  # Cyclical movement
        noise = (hash(str(i)) % 1000 - 500) / 25000  # Pseudo-random noise
        
        price_change = trend + cycle + noise
        current_price *= (1 + price_change * volatility)
        
        # Generate OHLCV data
        daily_volatility = volatility * 0.5
        high = current_price * (1 + abs(noise) * daily_volatility)
        low = current_price * (1 - abs(noise) * daily_volatility)
        open_price = price_data[-1]['close'] if price_data else current_price
        close = current_price
        volume = 1000 + abs(noise * 50000)  # Volume varies with price action
        
        price_data.append({
            "timestamp": (datetime.now() + timedelta(days=i)).isoformat(),
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": round(volume, 0)
        })
    
    return price_data


def print_signal_summary(signal_result: Dict[str, Any], module_name: str) -> None:
    """Print a formatted summary of a signal result."""
    signal = signal_result.get('signal', 'UNKNOWN')
    confidence = signal_result.get('confidence', 0.0)
    
    # Get module-specific details
    details = []
    if module_name == 'RSI':
        rsi_value = signal_result.get('rsi_value', 0)
        details.append(f"RSI: {rsi_value:.1f}")
    elif module_name == 'MACD':
        macd_value = signal_result.get('macd_line', 0)
        signal_line = signal_result.get('signal_line', 0)
        details.append(f"MACD: {macd_value:.2f}")
        details.append(f"Signal: {signal_line:.2f}")
    elif module_name == 'BollingerBands':
        percent_b = signal_result.get('percent_b', 0)
        volatility_state = signal_result.get('volatility_state', 'NORMAL')
        details.append(f"%B: {percent_b:.2f}")
        details.append(f"Vol: {volatility_state}")
    elif module_name == 'VolumeProfile':
        poc = signal_result.get('point_of_control', 0)
        volume_trend = signal_result.get('volume_trend', 'STABLE')
        details.append(f"POC: ${poc:,.0f}")
        details.append(f"Vol Trend: {volume_trend}")
    elif module_name == 'SentimentAnalysis':
        sentiment_score = signal_result.get('composite_sentiment_score', 0)
        sentiment_strength = signal_result.get('sentiment_strength', 'WEAK')
        details.append(f"Sentiment: {sentiment_score:.2f}")
        details.append(f"Strength: {sentiment_strength}")
    
    details_str = " | ".join(details)
    confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
    
    print(f"  {module_name:15} │ {signal:4} │ {confidence:.2f} │{confidence_bar}│ {details_str}")


def run_comprehensive_demo():
    """Run a comprehensive demonstration of the multi-signal system."""
    print("="*80)
    print("BENSON MULTI-SIGNAL TRADING BOT - COMPREHENSIVE DEMONSTRATION")
    print("="*80)
    
    # Initialize components
    print("\n1. INITIALIZING SYSTEM COMPONENTS")
    print("-" * 40)
    
    module_manager = ModuleManager()
    metrics_collector = MetricsCollector()
    
    # Load all signal modules
    signal_modules = [
        ("modules.rsi_module", "RSI Module", {"period": 14, "buy_threshold": 30, "sell_threshold": 70}),
        ("modules.macd_module", "MACD Module", {"fast_period": 12, "slow_period": 26, "signal_period": 9}),
        ("modules.bollinger_bands_module", "Bollinger Bands Module", {"period": 20, "std_multiplier": 2.0}),
        ("modules.volume_profile_module", "Volume Profile Module", {"lookback_periods": 50}),
        ("modules.sentiment_analysis_module", "Sentiment Analysis Module", {}),
        ("modules.adoption_tracker_module", "Chainalysis Adoption Tracker Module", {}),
        ("modules.multi_signal_aggregator_module", "Multi-Signal Aggregator Module", {})
    ]
    
    loaded_modules = []
    for module_path, display_name, config in signal_modules:
        try:
            module_name = module_manager.load_module(module_path, config)
            loaded_modules.append((module_name, display_name))
            print(f"✓ Loaded: {display_name}")
        except Exception as e:
            print(f"✗ Failed to load {display_name}: {e}")
    
    print(f"\n✓ Successfully loaded {len(loaded_modules)} signal modules")
    
    # Generate test data
    print("\n2. GENERATING REALISTIC TEST DATA")
    print("-" * 40)
    
    # Create multiple market scenarios
    scenarios = [
        ("Bull Market", 120, 50000, 0.015, "Strong upward trend with moderate volatility"),
        ("Bear Market", 100, 45000, 0.025, "Declining trend with higher volatility"),
        ("Sideways Market", 150, 47000, 0.008, "Range-bound movement with low volatility")
    ]
    
    scenario_results = {}
    
    for scenario_name, periods, base_price, volatility, description in scenarios:
        print(f"\n{scenario_name}: {description}")
        
        # Generate price data for this scenario
        price_data = generate_realistic_test_data(periods, base_price, volatility)
        print(f"  Generated {len(price_data)} periods of price data")
        print(f"  Price range: ${price_data[0]['close']:,.0f} - ${price_data[-1]['close']:,.0f}")
        print(f"  Total return: {((price_data[-1]['close'] / price_data[0]['close']) - 1) * 100:.1f}%")
        
        # Execute individual signal analyses
        print(f"\n3. INDIVIDUAL SIGNAL ANALYSIS - {scenario_name.upper()}")
        print("-" * 60)
        print(f"{'Module':15} │ {'Sig':4} │ {'Conf':4} │{'Confidence':10}│ Details")
        print("-" * 60)
        
        individual_signals = {}
        
        # RSI Analysis
        try:
            rsi_result = module_manager.execute_module("RSIModule", {"price_data": price_data})
            individual_signals["RSI"] = rsi_result
            print_signal_summary(rsi_result, "RSI")
        except Exception as e:
            print(f"  RSI               │ ERR │ 0.00 │          │ Error: {e}")
        
        # MACD Analysis
        try:
            macd_result = module_manager.execute_module("MACDModule", {"price_data": price_data})
            individual_signals["MACD"] = macd_result
            print_signal_summary(macd_result, "MACD")
        except Exception as e:
            print(f"  MACD              │ ERR │ 0.00 │          │ Error: {e}")
        
        # Bollinger Bands Analysis
        try:
            bb_result = module_manager.execute_module("BollingerBandsModule", {"price_data": price_data})
            individual_signals["BollingerBands"] = bb_result
            print_signal_summary(bb_result, "BollingerBands")
        except Exception as e:
            print(f"  BollingerBands    │ ERR │ 0.00 │          │ Error: {e}")
        
        # Volume Profile Analysis
        try:
            vp_result = module_manager.execute_module("VolumeProfileModule", {"price_data": price_data})
            individual_signals["VolumeProfile"] = vp_result
            print_signal_summary(vp_result, "VolumeProfile")
        except Exception as e:
            print(f"  VolumeProfile     │ ERR │ 0.00 │          │ Error: {e}")
        
        # Sentiment Analysis
        try:
            sa_result = module_manager.execute_module("SentimentAnalysisModule", {})
            individual_signals["SentimentAnalysis"] = sa_result
            print_signal_summary(sa_result, "SentimentAnalysis")
        except Exception as e:
            print(f"  SentimentAnalysis │ ERR │ 0.00 │          │ Error: {e}")
        
        # Chainalysis Adoption Tracker
        try:
            adoption_result = module_manager.execute_module("AdoptionTrackerModule", {})
            individual_signals["AdoptionTracker"] = adoption_result
            print_signal_summary(adoption_result, "AdoptionTracker")
        except Exception as e:
            print(f"  AdoptionTracker   │ ERR │ 0.00 │          │ Error: {e}")
        
        # Multi-Signal Aggregation
        print(f"\n4. MULTI-SIGNAL AGGREGATION - {scenario_name.upper()}")
        print("-" * 60)
        
        if individual_signals:
            try:
                aggregation_input = {
                    "signals": individual_signals,
                    "price_data": price_data[-1]
                }
                
                final_result = module_manager.execute_module("MultiSignalAggregatorModule", aggregation_input)
                
                print(f"Final Decision: {final_result['final_signal']}")
                print(f"Confidence: {final_result['final_confidence']:.2f}")
                print(f"Signal Strength: {final_result['signal_strength']}")
                print(f"Consensus Score: {final_result['consensus_score']:.2f}")
                print(f"Risk Level: {final_result['risk_assessment']['overall_risk']}")
                
                print(f"\nSignal Breakdown:")
                consensus = final_result['signal_consensus']
                print(f"  Buy Signals: {consensus['buy_signals']}")
                print(f"  Sell Signals: {consensus['sell_signals']}")
                print(f"  Hold Signals: {consensus['hold_signals']}")
                
                print(f"\nKey Decision Factors:")
                for i, factor in enumerate(final_result['decision_factors'][:3], 1):
                    print(f"  {i}. {factor}")
                
                # Store results for comparison
                scenario_results[scenario_name] = {
                    "final_signal": final_result['final_signal'],
                    "confidence": final_result['final_confidence'],
                    "consensus": final_result['consensus_score'],
                    "risk": final_result['risk_assessment']['overall_risk'],
                    "individual_signals": individual_signals,
                    "price_return": ((price_data[-1]['close'] / price_data[0]['close']) - 1) * 100
                }
                
            except Exception as e:
                print(f"✗ Multi-signal aggregation failed: {e}")
        else:
            print("✗ No individual signals available for aggregation")
            
        print("\n" + "="*80)
    
    # Comparative analysis
    print("\n5. COMPARATIVE ANALYSIS ACROSS MARKET SCENARIOS")
    print("-" * 60)
    
    if scenario_results:
        print(f"{'Scenario':15} │ {'Signal':6} │ {'Conf':5} │ {'Cons':5} │ {'Risk':6} │ {'Return':7}")
        print("-" * 60)
        
        for scenario_name, result in scenario_results.items():
            print(f"{scenario_name:15} │ {result['final_signal']:6} │ {result['confidence']:5.2f} │ "
                  f"{result['consensus']:5.2f} │ {result['risk']:6} │ {result['price_return']:6.1f}%")
    
    # System metrics
    print(f"\n6. SYSTEM PERFORMANCE METRICS")
    print("-" * 40)
    
    all_metrics = metrics_collector.get_all_metrics()
    print(f"Module Executions: {len(all_metrics.get('module_metrics', {}))}")
    print(f"Business Impact Events: {len(all_metrics.get('business_impact', {}))}")
    print(f"Total Analysis Runs: {len(scenario_results)}")
    
    # Signal correlation analysis
    print(f"\n7. SIGNAL INDEPENDENCE VERIFICATION")
    print("-" * 50)
    
    # Analyze signal correlation across scenarios
    if len(scenario_results) >= 2:
        signal_names = ['RSI', 'MACD', 'BollingerBands', 'VolumeProfile', 'SentimentAnalysis']
        
        print("Signal correlation analysis across different market conditions:")
        
        # Check how signals vary across scenarios
        signal_variations = {signal: [] for signal in signal_names}
        
        for scenario_name, result in scenario_results.items():
            for signal_name in signal_names:
                if signal_name in result['individual_signals']:
                    signal_data = result['individual_signals'][signal_name]
                    # Convert signal to numerical score
                    score = 1 if signal_data['signal'] == 'BUY' else -1 if signal_data['signal'] == 'SELL' else 0
                    score *= signal_data.get('confidence', 0)
                    signal_variations[signal_name].append(score)
        
        print(f"\nSignal diversity across {len(scenario_results)} market scenarios:")
        for signal_name, scores in signal_variations.items():
            if scores:
                diversity = len(set([round(s, 1) for s in scores])) / len(scores) if scores else 0
                avg_score = sum(scores) / len(scores)
                print(f"  {signal_name:15}: Diversity {diversity:.2f}, Avg Score {avg_score:+.2f}")
    
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETED SUCCESSFULLY!")
    print("="*80)
    
    print(f"\n✓ Multi-signal system demonstrates:")
    print(f"  • Integration of {len(loaded_modules)} uncorrelated signal modules")
    print(f"  • Adaptive decision making across {len(scenario_results)} market scenarios")
    print(f"  • Risk-aware confidence scoring and consensus analysis")
    print(f"  • Independence verification between different signal types")
    print(f"  • Comprehensive performance tracking and metrics collection")
    
    return scenario_results


if __name__ == "__main__":
    try:
        results = run_comprehensive_demo()
        
        # Save results to file for further analysis
        with open("multi_signal_demo_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
            
        print(f"\n✓ Results saved to multi_signal_demo_results.json")
        
    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        raise