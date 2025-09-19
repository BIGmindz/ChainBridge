"""
TRADING DASHBOARD
Simple visual dashboard for your multi-signal bot
"""

import json
from datetime import datetime
from typing import Dict, List

class TradingDashboard:
    """
    Simple dashboard that shows what's happening
    Perfect for monitoring your bot
    """
    
    def __init__(self):
        """Initialize dashboard"""
        self.signals = {}
        self.trades = []
        self.performance = {
            'total_pnl': 0,
            'win_rate': 0,
            'active_positions': 0
        }
        print("✅ Dashboard initialized")
    
    def update_signals(self, signals: Dict):
        """Update current signals"""
        self.signals = signals
        
    def add_trade(self, trade: Dict):
        """Add new trade to history"""
        self.trades.append(trade)
        self._update_performance()
    
    def _update_performance(self):
        """Update performance metrics"""
        if self.trades:
            wins = sum(1 for t in self.trades if t.get('pnl', 0) > 0)
            self.performance['win_rate'] = wins / len(self.trades)
            self.performance['total_pnl'] = sum(t.get('pnl', 0) for t in self.trades)
    
    def display(self):
        """Display dashboard in console"""
        print("\n" + "="*60)
        print("📊 TRADING DASHBOARD")
        print("="*60)
        
        # Show signals
        print("\n📡 CURRENT SIGNALS:")
        for name, value in self.signals.items():
            indicator = "🟢" if value > 0.3 else "🔴" if value < -0.3 else "🟡"
            print(f"  {indicator} {name}: {value:.2f}")
        
        # Show performance
        print("\n📈 PERFORMANCE:")
        print(f"  Total P&L: ${self.performance['total_pnl']:+,.2f}")
        print(f"  Win Rate: {self.performance['win_rate']*100:.1f}%")
        print(f"  Active Positions: {self.performance['active_positions']}")
        
        # Recent trades
        if self.trades:
            print("\n💰 RECENT TRADES:")
            for trade in self.trades[-5:]:
                print(f"  {trade.get('timestamp', 'N/A')}: {trade.get('side', 'N/A')} - P&L: ${trade.get('pnl', 0):+.2f}")
        
        print("="*60)
    
    def get_json(self) -> str:
        """Get dashboard data as JSON"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'signals': self.signals,
            'performance': self.performance,
            'recent_trades': self.trades[-10:] if self.trades else []
        }
        return json.dumps(data, indent=2, default=str)
    
    def save_snapshot(self, filename: str = None):
        """Save dashboard snapshot"""
        if filename is None:
            filename = f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            f.write(self.get_json())
        
        print(f"✅ Dashboard saved to {filename}")

class LiveMonitor:
    """
    Live monitoring for real-time trading
    """
    
    def __init__(self):
        self.alerts = []
        self.metrics = {}
        
    def check_alerts(self, data: Dict) -> List[str]:
        """Check for important alerts"""
        alerts = []
        
        # Check for high volatility
        if data.get('volatility', 0) > 0.03:
            alerts.append("⚠️ HIGH VOLATILITY DETECTED")
        
        # Check for large drawdown
        if data.get('drawdown', 0) < -0.05:
            alerts.append("🚨 SIGNIFICANT DRAWDOWN")
        
        # Check for unusual volume
        if data.get('volume_ratio', 1) > 3:
            alerts.append("📊 UNUSUAL VOLUME SPIKE")
        
        self.alerts.extend(alerts)
        return alerts
    
    def display_alerts(self):
        """Display recent alerts"""
        if self.alerts:
            print("\n🚨 ALERTS:")
            for alert in self.alerts[-5:]:
                print(f"  {alert}")