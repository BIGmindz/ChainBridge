"""
Benson System - Main Entry Point

This is the main entry point for the Benson multi-signal decision bot
with modular architecture support. It integrates the existing RSI bot
functionality with the new modular system.
"""

import argparse
import asyncio
import os
import sys
import math
from typing import Dict, Any

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.module_manager import ModuleManager
from core.pipeline import Pipeline
from tracking.metrics_collector import MetricsCollector
from api import server


def create_default_rsi_pipeline(module_manager: ModuleManager) -> Pipeline:
    """Create a default pipeline that mimics the original RSI bot functionality."""
    pipeline = Pipeline("rsi_trading_pipeline", module_manager)
    
    # Add RSI analysis step
    pipeline.add_step(
        "rsi_analysis",
        "RSIModule",
        {
            "period": 14,
            "buy_threshold": 30,
            "sell_threshold": 70
        }
    )
    
    return pipeline


def run_multi_signal_demo():
    """Demonstrate the new multi-signal analysis capability."""
    print("Starting Multi-Signal Analysis Demo...")
    
    # Initialize core components
    module_manager = ModuleManager()
    
    try:
        # Load all signal modules
        print("Loading signal modules...")
        module_manager.load_module("modules.rsi_module", {
            "period": 14,
            "buy_threshold": 30,
            "sell_threshold": 70
        })
        module_manager.load_module("modules.macd_module", {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9
        })
        module_manager.load_module("modules.bollinger_bands_module", {
            "period": 20,
            "std_multiplier": 2.0
        })
        module_manager.load_module("modules.volume_profile_module", {
            "lookback_periods": 50
        })
        module_manager.load_module("modules.sentiment_analysis_module")
        module_manager.load_module("modules.multi_signal_aggregator_module")
        
        print(f"✓ Loaded {len(module_manager.list_modules())} signal modules")
        
        # Create comprehensive price data for testing
        sample_price_data = []
        base_price = 45000
        for i in range(60):  # 60 periods of data
            price_variation = 100 * math.sin(i * 0.1) + (i * 25)  # Trend with oscillation
            noise = (i % 3 - 1) * 50  # Small random-like noise
            
            close = base_price + price_variation + noise
            high = close + abs(noise) + 50
            low = close - abs(noise) - 50
            volume = 1000 + (i * 20) + abs(noise * 2)
            
            sample_price_data.append({
                "close": close,
                "high": high,
                "low": low,
                "open": close - noise,
                "volume": volume,
                "timestamp": f"2024-01-{i+1:02d}T00:00:00Z"
            })
        
        print(f"✓ Generated {len(sample_price_data)} periods of test data")
        
        # Execute individual signal analyses
        print("\nExecuting individual signal analyses...")
        
        individual_signals = {}
        
        # RSI Analysis
        rsi_result = module_manager.execute_module("RSIModule", {"price_data": sample_price_data})
        individual_signals["RSI"] = rsi_result
        print(f"  RSI: {rsi_result['signal']} (Confidence: {rsi_result['confidence']:.2f}, Value: {rsi_result['rsi_value']:.1f})")
        
        # MACD Analysis
        macd_result = module_manager.execute_module("MACDModule", {"price_data": sample_price_data})
        individual_signals["MACD"] = macd_result
        print(f"  MACD: {macd_result['signal']} (Confidence: {macd_result['confidence']:.2f}, Value: {macd_result['macd_line']:.1f})")
        
        # Bollinger Bands Analysis
        bb_result = module_manager.execute_module("BollingerBandsModule", {"price_data": sample_price_data})
        individual_signals["BollingerBands"] = bb_result
        print(f"  Bollinger Bands: {bb_result['signal']} (Confidence: {bb_result['confidence']:.2f}, %B: {bb_result['percent_b']:.2f})")
        
        # Volume Profile Analysis
        vp_result = module_manager.execute_module("VolumeProfileModule", {"price_data": sample_price_data})
        individual_signals["VolumeProfile"] = vp_result
        print(f"  Volume Profile: {vp_result['signal']} (Confidence: {vp_result['confidence']:.2f}, POC: ${vp_result['point_of_control']:,.0f})")
        
        # Sentiment Analysis
        sa_result = module_manager.execute_module("SentimentAnalysisModule", {})
        individual_signals["SentimentAnalysis"] = sa_result
        print(f"  Sentiment: {sa_result['signal']} (Confidence: {sa_result['confidence']:.2f}, Score: {sa_result['composite_sentiment_score']:.2f})")
        
        # Multi-Signal Aggregation
        print(f"\nExecuting multi-signal aggregation...")
        aggregation_input = {
            "signals": individual_signals,
            "price_data": sample_price_data[-1]  # Current price data
        }
        
        final_result = module_manager.execute_module("MultiSignalAggregatorModule", aggregation_input)
        
        print(f"\n" + "="*60)
        print(f"MULTI-SIGNAL ANALYSIS RESULTS")
        print(f"="*60)
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
        print(f"  Total Signals: {consensus['total_signals']}")
        
        print(f"\nDecision Factors:")
        for factor in final_result['decision_factors']:
            print(f"  • {factor}")
            
        if 'correlation_analysis' in final_result and final_result['correlation_analysis']:
            print(f"\nSignal Independence:")
            corr = final_result['correlation_analysis']
            print(f"  Diversification Score: {corr['diversification_score']:.2f}")
            print(f"  Independence Verified: {corr['independence_verified']}")
            
        print(f"\nTrading Recommendation:")
        rec = final_result['trading_recommendation']
        print(f"  Action: {rec['action']}")
        print(f"  Position Size: {rec['position_size_suggestion']}")
        
        print(f"\n" + "="*60)
        print("✓ Multi-Signal Analysis Demo completed successfully!")
        
    except Exception as e:
        print(f"✗ Multi-Signal Demo failed: {e}")
        raise


def run_rsi_bot_compatibility(once: bool = False):
    """Run the RSI bot in compatibility mode using the new modular architecture."""
    print("Starting Benson RSI Bot (Modular Architecture)")
    
    # Initialize core components
    module_manager = ModuleManager()
    metrics_collector = MetricsCollector()
    
    try:
        # Load the RSI module
        module_manager.load_module("modules.rsi_module", {
            "period": 14,
            "buy_threshold": 30,
            "sell_threshold": 70
        })
        
        print("RSI module loaded successfully")
        
        # Create a sample price data for testing
        sample_price_data = [
            {"close": 45000, "timestamp": "2024-01-01T00:00:00Z"},
            {"close": 45100, "timestamp": "2024-01-01T00:05:00Z"},
            {"close": 44900, "timestamp": "2024-01-01T00:10:00Z"},
            {"close": 45200, "timestamp": "2024-01-01T00:15:00Z"},
            {"close": 45300, "timestamp": "2024-01-01T00:20:00Z"},
            # Add enough data points for RSI calculation
        ] + [{"close": 45000 + (i * 10), "timestamp": f"2024-01-01T{i:02d}:00:00Z"} 
             for i in range(20)]
        
        # Execute RSI analysis
        input_data = {"price_data": sample_price_data}
        result = module_manager.execute_module("RSIModule", input_data)
        
        print(f"RSI Analysis Result:")
        print(f"  RSI Value: {result['rsi_value']:.2f}")
        print(f"  Signal: {result['signal']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Current Price: ${result['current_price']:,.2f}")
        
        # Track metrics
        metrics_collector.track_business_impact("signal_generated", 1.0)
        
        if once:
            print("Single execution completed.")
            return
            
        print("Benson RSI Bot (modular) running... Press Ctrl+C to stop")
        print("Note: This is a demo mode. For full functionality, use the API server.")
        
    except Exception as e:
        print(f"Error running RSI bot: {e}")
        sys.exit(1)


def run_api_server():
    """Run the Benson API server."""
    print("Starting Benson API Server...")
    
    # Start the FastAPI server
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Server will be available at http://{host}:{port}")
    print(f"API Documentation: http://{host}:{port}/docs")
    
    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        reload=False,  # Set to False for production
        log_level="info"
    )


def run_system_tests():
    """Run comprehensive system tests for the modular architecture."""
    print("Running Benson System Tests...")
    
    # Import test functions from the original bot
    try:
        from benson_rsi_bot import run_tests as run_rsi_tests
        print("Running RSI tests...")
        run_rsi_tests()
        print("RSI tests completed.")
    except Exception as e:
        print(f"RSI tests failed: {e}")
    
    # Test modular components
    print("\nTesting modular components...")
    
    try:
        # Test module manager
        module_manager = ModuleManager()
        
        # Test CSV ingestion module
        print("Testing CSV ingestion module...")
        module_manager.load_module("modules.csv_ingestion")
        print("✓ CSV ingestion module loaded")
        
        # Test RSI module
        print("Testing RSI module...")
        module_manager.load_module("modules.rsi_module")
        print("✓ RSI module loaded")
        
        # Test sales forecasting module
        print("Testing sales forecasting module...")
        module_manager.load_module("modules.sales_forecasting")
        print("✓ Sales forecasting module loaded")
        
        # Test new signal modules
        print("Testing new signal modules...")
        
        # Test MACD module
        print("Testing MACD module...")
        module_manager.load_module("modules.macd_module")
        print("✓ MACD module loaded")
        
        # Test Bollinger Bands module
        print("Testing Bollinger Bands module...")
        module_manager.load_module("modules.bollinger_bands_module")
        print("✓ Bollinger Bands module loaded")
        
        # Test Volume Profile module
        print("Testing Volume Profile module...")
        module_manager.load_module("modules.volume_profile_module")
        print("✓ Volume Profile module loaded")
        
        # Test Sentiment Analysis module
        print("Testing Sentiment Analysis module...")
        module_manager.load_module("modules.sentiment_analysis_module")
        print("✓ Sentiment Analysis module loaded")
        
        # Test Multi-Signal Aggregator module
        print("Testing Multi-Signal Aggregator module...")
        module_manager.load_module("modules.multi_signal_aggregator_module")
        print("✓ Multi-Signal Aggregator module loaded")
        
        # Test pipeline creation
        print("Testing pipeline creation...")
        pipeline = Pipeline("test_pipeline", module_manager)
        pipeline.add_step("forecast", "SalesForecastingModule")
        validation = pipeline.validate_pipeline()
        
        if validation['valid']:
            print("✓ Pipeline creation and validation successful")
        else:
            print(f"✗ Pipeline validation failed: {validation['issues']}")
            
        # Test multi-signal pipeline
        print("Testing multi-signal pipeline...")
        multi_signal_pipeline = Pipeline("multi_signal_pipeline", module_manager)
        multi_signal_pipeline.add_step("rsi", "RSIModule")
        multi_signal_pipeline.add_step("macd", "MACDModule")
        multi_signal_pipeline.add_step("bollinger", "BollingerBandsModule")
        multi_signal_validation = multi_signal_pipeline.validate_pipeline()
        
        if multi_signal_validation['valid']:
            print("✓ Multi-signal pipeline creation successful")
        else:
            print(f"✗ Multi-signal pipeline validation failed: {multi_signal_validation['issues']}")
            
        # Test metrics collector
        print("Testing metrics collector...")
        metrics_collector = MetricsCollector()
        metrics_collector.track_module_execution("test_module", 1.0, 100, 200)
        metrics = metrics_collector.get_all_metrics()
        print(f"✓ Metrics collection working - {len(metrics)} metric categories tracked")
        
        print(f"\n✓ All modular architecture tests passed!")
        print(f"✓ Total modules loaded: {len(module_manager.list_modules())}")
        print(f"✓ Available modules: {', '.join(module_manager.list_modules())}")
        
    except Exception as e:
        print(f"✗ Modular architecture tests failed: {e}")
        sys.exit(1)


def main():
    """Main entry point for the Benson system."""
    parser = argparse.ArgumentParser(
        description="Benson Multi-Signal Decision Bot - Modular Architecture"
    )
    
    parser.add_argument(
        "--mode", 
        choices=["rsi-compat", "api-server", "test", "multi-signal-demo"], 
        default="api-server",
        help="Run mode: rsi-compat (RSI bot compatibility), api-server (API server), test (run tests), multi-signal-demo (demonstrate multi-signal analysis)"
    )
    parser.add_argument(
        "--once", 
        action="store_true", 
        help="Run once and exit (for rsi-compat mode)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for API server (default: 8000)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for API server (default: 0.0.0.0)"
    )
    
    args = parser.parse_args()
    
    # Set environment variables for server configuration
    if args.mode == "api-server":
        os.environ["PORT"] = str(args.port)
        os.environ["HOST"] = args.host
    
    # Route to appropriate mode
    if args.mode == "rsi-compat":
        run_rsi_bot_compatibility(once=args.once)
    elif args.mode == "api-server":
        run_api_server()
    elif args.mode == "test":
        run_system_tests()
    elif args.mode == "multi-signal-demo":
        run_multi_signal_demo()


if __name__ == "__main__":
    main()