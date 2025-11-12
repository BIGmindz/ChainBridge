#!/bin/bash
# Streamlit Dashboard Runner for Benson Bot

cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Run the Streamlit dashboard
echo "Starting Benson Bot Streamlit Dashboard..."
echo "Dashboard will be available at: http://localhost:8501"
echo "Press Ctrl+C to stop the dashboard"
echo ""

streamlit run modules/animated_dashboard_new.py --server.port 8501 --server.address 0.0.0.0
