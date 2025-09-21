#!/bin/bash
"""
Run Script for High-Fidelity Backtesting Engine

Usage:
    ./run_backtester.sh        # Run all strategies
    ./run_backtester.sh -s strategy_name  # Run specific strategy
"""

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root directory
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Check if required files exist
if [ ! -f "data/consolidated_market_data.csv" ]; then
    echo "❌ Error: data/consolidated_market_data.csv not found"
    echo "   Please run data collection first"
    exit 1
fi

if [ ! -d "strategies" ]; then
    echo "❌ Error: strategies directory not found"
    exit 1
fi

# Parse command line arguments
STRATEGY=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--strategy)
            STRATEGY="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [-s strategy_name]"
            echo "  -s, --strategy: Run specific strategy (optional)"
            echo "  -h, --help: Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Run the backtester
echo "🚀 Starting High-Fidelity Backtesting Engine"
echo "📊 Project Root: $PROJECT_ROOT"
echo "📁 Data File: data/consolidated_market_data.csv"

if [ -n "$STRATEGY" ]; then
    echo "🎯 Running strategy: $STRATEGY"
    python apps/backtester/backtester.py --strategy "$STRATEGY"
else
    echo "🔄 Running all strategies"
    python apps/backtester/backtester.py
fi

echo "✅ Backtesting complete!"
echo "📋 Check strategy directories for reports and charts"