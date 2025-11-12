"""
Run the trading dashboard
"""

from modules.animated_dashboard import AnimatedTradingDashboard

if __name__ == "__main__":
    dashboard = AnimatedTradingDashboard()
    print("Starting dashboard on http://localhost:8050")
    dashboard.run(debug=True)
