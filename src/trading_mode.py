import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TradingMode:
    """Centralized trading mode controller"""

    @staticmethod
    def is_paper_trading():
        """Check if system is in paper trading mode"""
        paper_mode = os.getenv("PAPER", "true").lower()
        return paper_mode in ("true", "1", "yes")

    @staticmethod
    def is_live_trading():
        """Check if system is in live trading mode"""
        return not TradingMode.is_paper_trading()

    @staticmethod
    def get_trading_mode():
        """Get current trading mode as string"""
        return "PAPER" if TradingMode.is_paper_trading() else "LIVE"

    @staticmethod
    def validate_trading_mode():
        """Validate trading mode configuration"""
        if TradingMode.is_live_trading():
            # Check for required API credentials
            api_key = os.getenv("API_KEY")
            api_secret = os.getenv("API_SECRET")

            if not api_key or not api_secret:
                raise ValueError("Live trading mode requires API_KEY and API_SECRET environment variables")

        return True
