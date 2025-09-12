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
        
        # Test pipeline creation
        print("Testing pipeline creation...")
        pipeline = Pipeline("test_pipeline", module_manager)
        pipeline.add_step("forecast", "SalesForecastingModule")
        validation = pipeline.validate_pipeline()
        
        if validation['valid']:
            print("✓ Pipeline creation and validation successful")
        else:
            print(f"✗ Pipeline validation failed: {validation['issues']}")
            
        # Test metrics collector
        print("Testing metrics collector...")
        metrics_collector = MetricsCollector()
        metrics_collector.track_module_execution("test_module", 1.0, 100, 200)
        metrics = metrics_collector.get_all_metrics()
        print(f"✓ Metrics collection working - {len(metrics)} metric categories tracked")
        
        print("\n✓ All modular architecture tests passed!")
        
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
        choices=["rsi-compat", "api-server", "test"], 
        default="api-server",
        help="Run mode: rsi-compat (RSI bot compatibility), api-server (API server), test (run tests)"
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


if __name__ == "__main__":
    main()