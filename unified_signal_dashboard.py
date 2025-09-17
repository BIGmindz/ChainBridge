#!/usr/bin/env python3
"""
UNIFIED SIGNAL DASHBOARD
Displays all trading signals in a single powerful dashboard
Combines technical, logistics, and global macro signals
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Any, List

# Add the current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import signal modules
try:
    from modules.rsi_module import RSIModule
    from modules.macd_module import MACDModule
    from modules.bollinger_bands_module import BollingerBandsModule
    from modules.volume_profile_module import VolumeProfileModule
    from modules.sentiment_analysis_module import SentimentAnalysisModule
    from modules.logistics_signal_module import LogisticsSignalModule
    from modules.global_macro_module import GlobalMacroModule
except ImportError as e:
    print(f"Error importing signal modules: {e}")
    print("Make sure all signal modules are properly installed.")
    sys.exit(1)

def load_price_data(symbol='BTC/USD', days=100):
    """Load or generate mock price data"""
    
    try:
        # For demo purposes, generate mock data
        print(f"Generating mock price data for {symbol}")
        
        # Create a dataframe with dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        dates = pd.date_range(start=start_date, end=end_date, periods=days)
        
        # Generate price data with a realistic pattern
        base_price = 30000  # Starting price
        volatility = 0.02   # Daily volatility
        
        prices = [base_price]
        for i in range(1, days):
            # Random walk with drift
            daily_return = np.random.normal(0.0005, volatility)  # Small upward drift
            
            # Add some trend patterns
            if i > 30 and i < 50:
                daily_return += 0.005  # Bull run period
            elif i > 70 and i < 80:
                daily_return -= 0.003  # Correction period
            
            new_price = prices[-1] * (1 + daily_return)
            prices.append(new_price)
        
        # Create volume data
        volumes = [np.random.normal(1000000, 300000) * (1 + 0.2 * abs(prices[i]/prices[i-1] - 1)) 
                  if i > 0 else np.random.normal(1000000, 300000) for i in range(len(prices))]
        
        # Create high/low/open data
        highs = [price * (1 + np.random.uniform(0, 0.03)) for price in prices]
        lows = [price * (1 - np.random.uniform(0, 0.03)) for price in prices]
        opens = [prices[i-1] if i > 0 else prices[0] * 0.99 for i in range(len(prices))]
        
        # Create OHLCV data format
        price_data = []
        for i in range(len(dates)):
            timestamp = dates[i].timestamp() * 1000
            candle = [
                timestamp,
                opens[i],
                highs[i],
                lows[i],
                prices[i],  # Close
                volumes[i]
            ]
            price_data.append(candle)
        
        print(f"Generated {len(price_data)} candles of mock data")
        return price_data
        
    except Exception as e:
        print(f"Error loading price data: {e}")
        return []

def generate_signals(symbol='BTC/USD'):
    """Generate signals from all modules"""
    
    print(f"Generating unified signals for {symbol}...")
    
    # Initialize all signal modules
    rsi = RSIModule()
    macd = MACDModule()
    bollinger = BollingerBandsModule()
    volume = VolumeProfileModule()
    sentiment = SentimentAnalysisModule()
    logistics = LogisticsSignalModule()
    macro = GlobalMacroModule()
    
    # Get price data
    price_data = load_price_data(symbol)
    if not price_data:
        print("Failed to get price data. Exiting.")
        return {}
    
    # Process signals
    signals = {}
    
    print("\nPROCESSING TECHNICAL INDICATORS")
    print("=" * 40)
    # Technical indicators
    try:
        signals["RSI"] = process_module(rsi, "RSI", {"price_data": price_data})
        signals["MACD"] = process_module(macd, "MACD", {"price_data": price_data})
        signals["BollingerBands"] = process_module(bollinger, "BollingerBands", {"price_data": price_data})
        signals["VolumeProfile"] = process_module(volume, "VolumeProfile", {"price_data": price_data})
        signals["Sentiment"] = process_module(sentiment, "Sentiment", {"symbol": symbol})
    except Exception as e:
        print(f"Error processing technical indicators: {e}")
    
    print("\nPROCESSING LOGISTICS SIGNALS")
    print("=" * 40)
    # Logistics signals
    try:
        signals["Logistics"] = process_module(logistics, "Logistics", {"price_data": price_data, "symbol": symbol})
    except Exception as e:
        print(f"Error processing logistics signals: {e}")
    
    print("\nPROCESSING GLOBAL MACRO SIGNALS")
    print("=" * 40)
    # Global macro signals
    try:
        signals["GlobalMacro"] = process_module(macro, "GlobalMacro", {"price_data": price_data, "symbol": symbol})
    except Exception as e:
        print(f"Error processing global macro signals: {e}")
    
    # Generate summary
    print("\nGENERATING SIGNAL SUMMARY")
    print("=" * 40)
    summary = generate_signal_summary(signals)
    
    # Combine everything
    result = {
        "symbol": symbol,
        "timestamp": datetime.now().isoformat(),
        "signals": signals,
        "summary": summary
    }
    
    # Save to file
    try:
        with open('unified_signals.json', 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"Unified signals saved to unified_signals.json")
    except Exception as e:
        print(f"Error saving signals: {e}")
    
    return result

def process_module(module, name, params):
    """Process a single module and return its signals"""
    
    print(f"Processing {name} module...")
    
    try:
        # Get raw signals
        signal_data = module.process(params)
        
        if not isinstance(signal_data, dict):
            print(f"Warning: {name} module did not return a dictionary.")
            signal_data = {"signal": "HOLD", "confidence": 0, "error": "Invalid response format"}
        
        # Print signal
        signal = signal_data.get('signal', 'HOLD')
        confidence = signal_data.get('confidence', 0) * 100
        
        emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
        print(f"  {emoji} {name}: {signal} ({confidence:.1f}% confidence)")
        
        return signal_data
    except Exception as e:
        print(f"  ❌ Error in {name} module: {e}")
        return {"signal": "HOLD", "confidence": 0, "error": str(e)}

def generate_signal_summary(signals):
    """Generate a summary of all signals"""
    
    # Count signals
    buy_count = sum(1 for name, data in signals.items() if data.get('signal') == 'BUY')
    sell_count = sum(1 for name, data in signals.items() if data.get('signal') == 'SELL')
    hold_count = sum(1 for name, data in signals.items() if data.get('signal') == 'HOLD')
    
    total_signals = len(signals)
    
    # Calculate weighted consensus
    total_weight = 0
    weighted_score = 0
    
    for name, data in signals.items():
        # Default weight
        weight = 0.1
        
        # Adjust weight based on module type
        if name in ["RSI", "MACD", "BollingerBands", "VolumeProfile", "Sentiment"]:
            # Technical indicators get less weight
            weight = 0.05
        elif name == "Logistics":
            # Logistics gets medium weight
            weight = 0.25
        elif name == "GlobalMacro":
            # Global Macro gets highest weight (most predictive)
            weight = 0.30
            
        # Adjust by confidence
        confidence = data.get('confidence', 0)
        weight = weight * max(0.1, confidence)  # Minimum weight is 10% of base weight
        
        # Calculate signal score (-1 for SELL, 0 for HOLD, +1 for BUY)
        signal_value = 1 if data.get('signal') == 'BUY' else (-1 if data.get('signal') == 'SELL' else 0)
        
        weighted_score += signal_value * weight
        total_weight += weight
    
    # Final consensus
    if total_weight > 0:
        consensus_score = weighted_score / total_weight
    else:
        consensus_score = 0
        
    # Convert to signal
    if consensus_score > 0.3:
        consensus = "BUY"
    elif consensus_score < -0.3:
        consensus = "SELL"
    else:
        consensus = "HOLD"
        
    # Calculate consensus strength (0-100%)
    consensus_strength = min(100, abs(consensus_score) * 100)
    
    return {
        "buy_count": buy_count,
        "sell_count": sell_count,
        "hold_count": hold_count,
        "total_signals": total_signals,
        "consensus": consensus,
        "consensus_score": consensus_score,
        "consensus_strength": consensus_strength
    }

def display_unified_dashboard(result):
    """Display unified dashboard with all signals"""
    
    # Clear terminal for better display
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Get data
    symbol = result['symbol']
    timestamp = datetime.fromisoformat(result['timestamp'])
    signals = result['signals']
    summary = result['summary']
    
    # Calculate signal counts and consensus
    buy_count = summary['buy_count']
    sell_count = summary['sell_count']
    hold_count = summary['hold_count']
    consensus = summary['consensus']
    consensus_strength = summary['consensus_strength']
    
    # Create header banner
    print("\n" + "="*80)
    print(f"  🚀 UNIFIED TRADING SIGNAL DASHBOARD - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Symbol info
    print(f"\n  SYMBOL: {symbol}")
    
    # Display consensus
    consensus_emoji = "🟢" if consensus == "BUY" else "🔴" if consensus == "SELL" else "⚪"
    print(f"\n  CONSENSUS: {consensus_emoji} {consensus} - {consensus_strength:.1f}% Strength")
    print(f"  Signal Count: {buy_count} BUY, {sell_count} SELL, {hold_count} HOLD")
    
    # Technical indicator section
    print("\n  📈 TECHNICAL INDICATORS")
    print("  " + "-"*38)
    for name in ["RSI", "MACD", "BollingerBands", "VolumeProfile", "Sentiment"]:
        if name in signals:
            data = signals[name]
            signal = data.get('signal', 'HOLD')
            confidence = data.get('confidence', 0) * 100
            emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
            print(f"  {emoji} {name}: {signal} ({confidence:.1f}% confidence)")
    
    # Logistics signals section
    if "Logistics" in signals:
        print("\n  🚢 LOGISTICS SIGNALS (Forward-Looking: 30-45 days)")
        print("  " + "-"*38)
        data = signals["Logistics"]
        signal = data.get('signal', 'HOLD')
        confidence = data.get('confidence', 0) * 100
        emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
        
        # Extract components if available
        components = data.get('components', {})
        print(f"  {emoji} Overall: {signal} ({confidence:.1f}% confidence)")
        
        if components:
            for comp_name, comp_data in components.items():
                interp = comp_data.get('interpretation', 'N/A')
                metric = comp_data.get('metric', 'N/A')
                print(f"  • {comp_name}: {metric}")
                print(f"    → {interp}")
    
    # Global macro signals section
    if "GlobalMacro" in signals:
        print("\n  🌍 GLOBAL MACRO SIGNALS (Forward-Looking: 45-90 days)")
        print("  " + "-"*38)
        data = signals["GlobalMacro"]
        signal = data.get('signal', 'HOLD')
        confidence = data.get('confidence', 0) * 100
        emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "⚪"
        
        # Get key insight
        insight = data.get('key_insight', 'No insights available')
        
        print(f"  {emoji} Overall: {signal} ({confidence:.1f}% confidence)")
        print(f"  Key Insight: {insight}")
        
        # Extract components if available
        components = data.get('components', {})
        if components:
            for comp_name, comp_data in components.items():
                if 'data' in comp_data:
                    interp = comp_data['data'].get('interpretation', 'N/A')
                    print(f"  • {comp_name}: {interp}")
    
    # Display footer
    print("\n" + "="*80)
    print("  ⚠️  EDUCATIONAL USE ONLY - NOT FINANCIAL ADVICE")
    print("="*80 + "\n")

def main():
    print("\n" + "="*60)
    print("🚀 UNIFIED SIGNAL DASHBOARD")
    print("="*60)
    
    # Default symbol
    symbol = "BTC/USD"
    
    # Generate all signals
    result = generate_signals(symbol)
    
    if result:
        # Display unified dashboard
        display_unified_dashboard(result)
    else:
        print("❌ Failed to generate signals.")

if __name__ == "__main__":
    main()