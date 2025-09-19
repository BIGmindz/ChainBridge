#!/usr/bin/env python3
"""
Liquidation Script for Crypto Positions

This script safely liquidates crypto positions to USDG (stablecoin)
for immediate trading liquidity instead of USD (which has withdrawal delays).
"""

import os
import sys
import json
import time
import argparse
from typing import Dict, Any, List
from datetime import datetime, timezone

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import required modules
from src.data_provider import setup_exchange, safe_fetch_ticker
from src.exchange_adapter import ExchangeAdapter
from budget_manager import BudgetManager


class PositionLiquidator:
    """Handles safe liquidation of crypto positions to USDG."""

    def __init__(self, exchange_adapter: ExchangeAdapter, budget_manager: BudgetManager):
        self.exchange_adapter = exchange_adapter
        self.budget_manager = budget_manager
        self.liquidation_log = []

    def get_current_positions(self) -> Dict[str, float]:
        """Get current crypto positions from budget manager."""
        # This would need to be implemented based on your position tracking
        # For now, return empty dict - you'll need to populate this
        return {}

    def calculate_liquidation_amount(self, symbol: str, target_value_usd: float) -> float:
        """Calculate how much crypto to sell to reach target USD value."""
        try:
            # Get current price
            ticker = safe_fetch_ticker(self.exchange_adapter.exchange, symbol)
            current_price = ticker["last"]

            # Calculate amount needed to sell
            amount_to_sell = target_value_usd / current_price

            print(f"💰 To liquidate ${target_value_usd}: Sell {amount_to_sell:.6f} {symbol} @ ${current_price:,.2f}")
            return amount_to_sell

        except Exception as e:
            print(f"❌ Error calculating liquidation amount for {symbol}: {str(e)}")
            return 0.0

    def liquidate_to_usdg(self, symbol: str, amount: float) -> bool:
        """Liquidate crypto position to USDG via two-step process."""
        try:
            print(f"\n🔄 Starting liquidation of {amount} {symbol} to USDG...")

            # Step 1: Sell crypto for USD
            usd_symbol = symbol.replace('/USD', '') + '/USD'
            print(f"📈 Step 1: Selling {amount} {symbol} for USD...")

            # Get current price for limit order
            ticker = safe_fetch_ticker(self.exchange_adapter.exchange, usd_symbol)
            sell_price = ticker["last"] * 0.995  # 0.5% below market for limit order

            # Place sell order
            sell_order = self.exchange_adapter.place_order(
                symbol=usd_symbol,
                side="sell",
                amount=amount,
                price=sell_price
            )

            if sell_order:
                usd_received = amount * sell_price
                print(f"✅ Sold {amount} {symbol} for ${usd_received:.2f} USD")

                # Step 2: Convert USD to USDG
                print(f"🔄 Step 2: Converting ${usd_received:.2f} USD to USDG...")

                # Calculate USDG amount (USDG/USD rate)
                usdg_ticker = safe_fetch_ticker(self.exchange_adapter.exchange, "USDG/USD")
                usdg_price = usdg_ticker["last"]
                usdg_amount = usd_received / usdg_price

                # Buy USDG with USD
                buy_price = usdg_price * 1.005  # 0.5% above market for limit order
                buy_order = self.exchange_adapter.place_order(
                    symbol="USDG/USD",
                    side="buy",
                    amount=usdg_amount,
                    price=buy_price
                )

                if buy_order:
                    print(f"✅ Converted to {usdg_amount:.2f} USDG")
                    print(f"💰 Liquidation complete! Funds available immediately for trading.")

                    # Log the transaction
                    self.liquidation_log.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "symbol": symbol,
                        "amount_sold": amount,
                        "usd_received": usd_received,
                        "usdg_received": usdg_amount,
                        "sell_order_id": sell_order.get("id"),
                        "buy_order_id": buy_order.get("id")
                    })

                    return True
                else:
                    print("❌ Failed to convert USD to USDG")
                    return False
            else:
                print("❌ Failed to sell crypto for USD")
                return False

        except Exception as e:
            print(f"❌ Liquidation failed: {str(e)}")
            return False

    def save_liquidation_log(self, filename: str = "liquidation_log.json"):
        """Save liquidation transaction log."""
        try:
            with open(filename, 'w') as f:
                json.dump(self.liquidation_log, f, indent=2)
            print(f"📝 Liquidation log saved to {filename}")
        except Exception as e:
            print(f"❌ Failed to save liquidation log: {str(e)}")


def main():
    """Main liquidation function."""
    parser = argparse.ArgumentParser(description="Liquidate crypto positions to USDG")
    parser.add_argument("--symbol", required=True, help="Symbol to liquidate (e.g., PRO/USD)")
    parser.add_argument("--value", type=float, required=True, help="USD value to liquidate")
    parser.add_argument("--config", default="config.yaml", help="Config file path")

    args = parser.parse_args()

    try:
        # Load configuration
        import yaml
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)

        # Setup exchange
        exchange_id = config.get("exchange", "kraken")
        api_config = config.get("api", {})
        exchange = setup_exchange(exchange_id, api_config)

        # Initialize components
        exchange_adapter = ExchangeAdapter(exchange, config)
        budget_manager = BudgetManager(initial_capital=config.get("initial_capital", 10000))

        # Create liquidator
        liquidator = PositionLiquidator(exchange_adapter, budget_manager)

        # Calculate and execute liquidation
        amount_to_sell = liquidator.calculate_liquidation_amount(args.symbol, args.value)

        if amount_to_sell > 0:
            success = liquidator.liquidate_to_usdg(args.symbol, amount_to_sell)

            if success:
                liquidator.save_liquidation_log()
                print("✅ Liquidation completed successfully!")
                return 0
            else:
                print("❌ Liquidation failed!")
                return 1
        else:
            print("❌ Could not calculate liquidation amount!")
            return 1

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())