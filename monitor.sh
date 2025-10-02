#!/bin/bash
# Live Trading Bot Monitor - Simple Terminal Script
# Usage: ./monitor.sh

echo "================================================================================"
echo "🤖 BENSON BOT LIVE TRADING MONITOR"
echo "================================================================================"
echo "⏰ Started: $(date)"
echo "📊 Monitoring: Real-time signals, balance, and trade execution"
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
echo "📡 LIVE BOT OUTPUT (filtered for key info):"
echo "--------------------------------------------------------------------------------"

# Run the bot and filter output for important information
python3 live_trading_bot.py 2>&1 | while IFS= read -r line; do
    # Add timestamp to each line
    timestamp=$(date "+%H:%M:%S")
    
    # Filter for all trading symbols and important keywords
    if echo "$line" | grep -E "(📊|🎯|💼|💰|📈|🚀|⚡)" > /dev/null; then
        echo "[$timestamp] $line"
    elif echo "$line" | grep -E "(BTC/USD|ETH/USD|SOL/USD|XRP/USD|ADA/USD|DOGE/USD|LTC/USD|DOT/USD|LINK/USD|AVAX/USD|ATOM/USD|ARB/USD|TRX/USD|XLM/USD|FIL/USD|NEAR/USD|AAVE/USD|ETC/USD|BCH/USD|UNI/USD)" > /dev/null; then
        echo "[$timestamp] $line"
    elif echo "$line" | grep -E "(Signal:|Aggregated Signal:|PORTFOLIO|BUY|SELL|HOLD)" > /dev/null; then
        echo "[$timestamp] $line"
    elif echo "$line" | grep -E "(Capital:|Balance:|Positions:|P&L:|Available|Open|Total|Win Rate|Total Trades)" > /dev/null; then
        echo "[$timestamp] $line"
    elif echo "$line" | grep -E "(RSI|MACD|BollingerBands|VolumeProfile|SentimentAnalysis|LogisticsSignal|GlobalMacro|AdoptionTracker|RegionCryptoMapper|NewListingsRadar)" > /dev/null; then
        echo "[$timestamp] $line"
    elif echo "$line" | grep -E "(ERROR|Exception|Failed|Error)" > /dev/null; then
        echo "[$timestamp] ❌ $line"
    elif echo "$line" | grep -E "(===|TRADING CYCLE|Cycle completed)" > /dev/null; then
        echo ""
        echo "[$timestamp] $line"
        echo "--------------------------------------------------------------------------------"
    fi
done

echo ""
echo "👋 Monitoring stopped. Check if bot is still running with: ps aux | grep live_trading_bot"