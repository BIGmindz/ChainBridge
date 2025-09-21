#!/bin/bash
"""
Run Script for BensonBot Strategy Comparison Dashboard

Usage:
    ./run_dashboard.sh        # Launch the dashboard
    ./run_dashboard.sh -h     # Show help
"""

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Change to project root directory
cd "$PROJECT_ROOT"

# Parse command line arguments
SHOW_HELP=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

if [ "$SHOW_HELP" = true ]; then
    echo "BensonBot Strategy Comparison Dashboard"
    echo "======================================="
    echo ""
    echo "This script launches the Streamlit dashboard for comparing"
    echo "backtest performance across all strategies."
    echo ""
    echo "Usage:"
    echo "  $0              # Launch the dashboard"
    echo "  $0 -h|--help    # Show this help message"
    echo ""
    echo "Prerequisites:"
    echo "  - Run the backtester first to generate reports"
    echo "  - Ensure streamlit is installed"
    echo ""
    echo "The dashboard will be available at: http://localhost:8501"
    exit 0
fi

# Check if streamlit is available
if ! command -v streamlit &> /dev/null; then
    echo "❌ Error: streamlit is not installed or not in PATH"
    echo "   Install with: pip install streamlit"
    exit 1
fi

# Check if backtest reports exist
if [ ! -d "strategies" ]; then
    echo "⚠️  Warning: strategies directory not found"
    echo "   The dashboard will show a warning about missing reports"
fi

# Check for any backtest reports
REPORT_COUNT=$(find strategies -name "backtest_report.md" 2>/dev/null | wc -l)
if [ "$REPORT_COUNT" -eq 0 ]; then
    echo "⚠️  Warning: No backtest reports found"
    echo "   Run the backtester first: python apps/backtester/backtester.py"
fi

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Launch the dashboard
echo "🚀 Launching BensonBot Strategy Comparison Dashboard"
echo "📊 Project Root: $PROJECT_ROOT"
echo "📈 Dashboard: http://localhost:8501"
echo "📋 Found $REPORT_COUNT backtest report(s)"
echo ""
echo "Press Ctrl+C to stop the dashboard"
echo "=========================================="

streamlit run apps/dashboard/comparison_dashboard.py