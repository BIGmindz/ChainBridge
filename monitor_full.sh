#!/bin/bash
# Enhanced Live Trading Bot Monitor - Shows All Symbols and Continuous Output
# Usage: ./monitor_full.sh

echo "================================================================================"
echo "🤖 BENSON BOT LIVE TRADING MONITOR - FULL OUTPUT"
echo "================================================================================"
echo "⏰ Started: $(date)"
echo "📊 Monitoring ALL 20 trading pairs with continuous output"
echo "🔄 Press Ctrl+C to stop monitoring"
echo "================================================================================"

# Change to bot directory
cd "$(dirname "$0")"

# Check if bot file exists
if [ ! -f "live_trading_bot.py" ]; then
    echo "❌ Error: live_trading_bot.py not found in current directory"
    echo "🔧 Please run this script from the bot directory"
    exit 1
fi

echo ""
echo "📡 LIVE BOT OUTPUT - ALL SYMBOLS:"
echo "--------------------------------------------------------------------------------"
echo "Tracking: BTC, ETH, SOL, XRP, ADA, DOGE, LTC, DOT, LINK, AVAX"
echo "          ATOM, ARB, TRX, XLM, FIL, NEAR, AAVE, ETC, BCH, UNI"
echo "--------------------------------------------------------------------------------"

# Run the bot and show continuous output
python3 live_trading_bot.py 2>&1 | while IFS= read -r line; do
    timestamp=$(date "+%H:%M:%S")
    
    # Show all trading-related output
    if echo "$line" | grep -E "(📊|🎯|💼|💰|📈|🚀|⚡|🟢|🔴|⚪)" > /dev/null; then
        echo "[$timestamp] $line"
    elif echo "$line" | grep -E "(BTC/USD|ETH/USD|SOL/USD|XRP/USD|ADA/USD|DOGE/USD|LTC/USD|DOT/USD|LINK/USD|AVAX/USD)" > /dev/null; then
        echo "[$timestamp] 💎 $line"
    elif echo "$line" | grep -E "(ATOM/USD|ARB/USD|TRX/USD|XLM/USD|FIL/USD|NEAR/USD|AAVE/USD|ETC/USD|BCH/USD|UNI/USD)" > /dev/null; then
        echo "[$timestamp] 💎 $line"
    elif echo "$line" | grep -E "(Aggregated Signal:|Signal:|PORTFOLIO|BUY|SELL|HOLD)" > /dev/null; then
        echo "[$timestamp] 🎯 $line"
    elif echo "$line" | grep -E "(Capital:|Balance:|Positions:|P&L:|Available|Open|Total|Win Rate)" > /dev/null; then
        echo "[$timestamp] 💰 $line"
    elif echo "$line" | grep -E "(RSI|MACD|Bollinger|Volume|Sentiment|Logistics|Macro|Adoption|Region|Listings)" > /dev/null; then
        echo "[$timestamp] 📊 $line"
    elif echo "$line" | grep -E "(Confidence:|Signals:)" > /dev/null; then
        echo "[$timestamp] 🔍 $line"
    elif echo "$line" | grep -E "(===|TRADING CYCLE|Cycle completed)" > /dev/null; then
        echo ""
        echo "[$timestamp] 🔄 $line"
        echo "=================================================================================="
    elif echo "$line" | grep -E "(ERROR|Exception|Failed|Error)" > /dev/null; then
        echo "[$timestamp] ❌ $line"
    elif echo "$line" | grep -E "(Using|Fetching|Downloading|Reading)" > /dev/null; then
        echo "[$timestamp] 📡 $line"
    else
        # Show everything else with minimal formatting
        if [[ -n "$line" ]]; then
            echo "[$timestamp] $line"
        fi
    fi
done

echo ""
echo "👋 Full monitoring stopped. Check if bot is still running with: ps aux | grep live_trading_bot"