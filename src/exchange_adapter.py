"""
Exchange Adapter Module

Manages all communication with the exchange for placing orders.
Supports both paper trading and live trading modes.
"""

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system env vars


class ExchangeAdapter:
    """
    Adapter for exchange operations.
    Supports both paper trading and live trading modes.
    """

    def __init__(self, exchange, config: Dict[str, Any]):
        self.exchange = exchange
        self.config = config

        # Read paper trading mode from environment variable
        self.paper_trade = os.getenv("PAPER", "true").lower() == "true"

        # Read API credentials from environment
        self.api_key = os.getenv("API_KEY", "")
        self.api_secret = os.getenv("API_SECRET", "")

        self.paper_trades: List[Dict[str, Any]] = []

        # Validate live trading setup
        if not self.paper_trade:
            if not self.api_key or not self.api_secret:
                raise ValueError("Live trading requires API_KEY and API_SECRET environment variables")
            print("⚠️  LIVE TRADING MODE ENABLED - Real orders will be placed!")
            print("⚠️  Make sure you have sufficient funds and understand the risks!")
        else:
            print("📝 PAPER TRADING MODE - No real orders will be placed")

    def place_order(self, symbol: str, side: str, amount: float, price: float) -> Dict[str, Any]:
        """
        Place an order (supports both paper and live trading).

        Args:
            symbol: Trading symbol (e.g., "BTC/USD")
            side: "buy" or "sell"
            amount: Order amount
            price: Order price

        Returns:
            Order result dictionary
        """
        if self.paper_trade:
            order = {
                "id": f"paper_{int(time.time())}",
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "filled",
                "type": "paper_trade",
            }
            self.paper_trades.append(order)
            print(f"[PAPER TRADE] {side.upper()} {amount} {symbol} @ ${price:,.2f}")
            return order
        else:
            # Live trading implementation
            try:
                # Set API credentials on exchange object
                if hasattr(self.exchange, "apiKey"):
                    self.exchange.apiKey = self.api_key
                    self.exchange.secret = self.api_secret

                # Place live order
                order = self.exchange.create_order(symbol=symbol, type="limit", side=side, amount=amount, price=price)

                print(f"[LIVE ORDER] {side.upper()} {amount} {symbol} @ ${price:,.2f}")
                print(f"[LIVE ORDER] Order ID: {order.get('id', 'N/A')}")

                return {
                    "id": order.get("id", f"live_{int(time.time())}"),
                    "symbol": symbol,
                    "side": side,
                    "amount": amount,
                    "price": price,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": order.get("status", "unknown"),
                    "type": "live_trade",
                }

            except Exception as e:
                error_msg = f"Failed to place live order: {str(e)}"
                print(f"[ERROR] {error_msg}")
                raise Exception(error_msg)

    def get_paper_trades(self) -> List[Dict[str, Any]]:
        """Get all paper trades executed."""
        return self.paper_trades.copy()

    def get_balance(self, currency: str) -> float:
        """Get balance for a currency (supports both paper and live trading)."""
        if self.paper_trade:
            # Mock balance for paper trading
            return 10000.0 if currency == "USD" else 1.0
        else:
            # Live balance from exchange
            try:
                # Set API credentials on exchange object
                if hasattr(self.exchange, "apiKey"):
                    self.exchange.apiKey = self.api_key
                    self.exchange.secret = self.api_secret

                balance = self.exchange.fetch_balance()
                return balance.get(currency, {}).get("free", 0.0)
            except Exception as e:
                print(f"[ERROR] Failed to fetch live balance: {str(e)}")
                return 0.0
