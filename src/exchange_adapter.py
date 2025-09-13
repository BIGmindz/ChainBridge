"""
Exchange Adapter Module

Manages all communication with the exchange for placing orders.
Currently operates in paper-trade mode for safety.
"""

from typing import Dict, Any, List
import time
from datetime import datetime, timezone


class ExchangeAdapter:
    """
    Adapter for exchange operations.
    Currently in paper-trade mode - no actual orders are placed.
    """
    
    def __init__(self, exchange, config: Dict[str, Any]):
        self.exchange = exchange
        self.config = config
        self.paper_trade = True  # Always paper trade for now
        self.paper_trades: List[Dict[str, Any]] = []
    
    def place_order(self, symbol: str, side: str, amount: float, price: float) -> Dict[str, Any]:
        """
        Place an order (currently paper trading only).
        
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
                "type": "paper_trade"
            }
            self.paper_trades.append(order)
            print(f"[PAPER TRADE] {side.upper()} {amount} {symbol} @ ${price:,.2f}")
            return order
        else:
            # Real trading would go here in the future
            raise NotImplementedError("Real trading not implemented yet")
    
    def get_paper_trades(self) -> List[Dict[str, Any]]:
        """Get all paper trades executed."""
        return self.paper_trades.copy()
    
    def get_balance(self, currency: str) -> float:
        """Get balance for a currency (paper trading returns mock balance)."""
        if self.paper_trade:
            # Mock balance for paper trading
            return 10000.0 if currency == "USD" else 1.0
        else:
            # Real balance would be fetched here
            return self.exchange.fetch_balance()[currency]["free"]