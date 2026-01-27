#!/bin/bash
# PAC-49: Sovereign War Room Launcher

echo "=" 
echo "🛡️  CHAINBRIDGE SOVEREIGN WAR ROOM"
echo "   PAC-49: God's Eye View Activation"
echo "="
echo ""
echo "Starting Streamlit dashboard..."
echo "URL: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo "="

streamlit run core/dashboard/war_room.py --server.port 8501 --server.address localhost
