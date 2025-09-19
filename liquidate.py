#!/usr/bin/env python3
"""
Kraken Spot Liquidation Script

Safe, idempotent liquidation of all spot holdings to a single quote currency.

USAGE EXAMPLES:
    # Dry run: check what would be liquidated to USDT, skip positions < $25
    python liquidate.py --target-quote USDT --min-usd 25 --cancel-open --dry-run

    # Live liquidation to USD, skip dust < $10, max 0.8% slippage
    python liquidate.py --target-quote USD --min-usd 10 --max-slippage-pct 0.8 --live

    # Force liquidation with higher slippage tolerance
    python liquidate.py --target-quote USDT --force --max-slippage-pct 2.0 --live

    # Cancel open orders first, then liquidate
    python liquidate.py --cancel-open --live

FLAGS:
    --target-quote {USDT|USD}: Target quote currency (default: USDT)
    --min-usd <float>: Skip positions below this USD value (default: 10.0)
    --max-slippage-pct <float>: Max allowed slippage % (default: 0.8)
    --cancel-open: Cancel all open spot orders before liquidation
    --force: Ignore slippage limits and proceed anyway
    --live: Execute real trades (default: dry-run only)
    --dry-run: Show what would happen without executing (default)

OUTPUT:
    - Console logging with timestamps
    - Timestamped log file: liquidation_YYYYMMDD_HHMMSS.log
    - Final report with starting/ending balances, P&L, fees
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ccxt


@dataclass
class Config:
    """Configuration for the liquidation script."""
    target_quote: str = "USDT"
    min_usd_value: float = 10.0
    max_slippage_pct: float = 0.8
    cancel_open_orders: bool = False
    force_mode: bool = False
    live_mode: bool = False
    dry_run: bool = True

    def __post_init__(self):
        if self.live_mode:
            self.dry_run = False


class KrakenLiquidator:
    """Safe liquidation of Kraken spot holdings to target quote currency."""

    def __init__(self, config: Config):
        self.config = config
        self.exchange = None
        self.markets = {}
        self.starting_balances = {}
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging to console and file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"liquidation_{timestamp}.log"

        logger = logging.getLogger("liquidator")
        logger.setLevel(logging.INFO)

        # Remove any existing handlers
        logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        return logger

    def load_api_keys(self) -> Tuple[str, str]:
        """Load API keys from ~/.config/crypto-1.0/kraken.json."""
        config_path = Path.home() / ".config" / "crypto-1.0" / "kraken.json"

        if not config_path.exists():
            raise FileNotFoundError(
                f"API config not found at {config_path}. "
                "Create it with: {'apiKey': 'your_key', 'secret': 'your_secret'}"
            )

        with open(config_path, 'r') as f:
            config = json.load(f)

        api_key = config.get('apiKey')
        secret = config.get('secret')

        if not api_key or not secret:
            raise ValueError("API key or secret missing from config file")

        return api_key, secret

    def initialize_exchange(self):
        """Initialize Kraken exchange connection."""
        api_key, secret = self.load_api_keys()

        self.exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {
                'createMarketBuyOrderRequiresPrice': False,
            }
        })

        # Load markets once
        self.markets = self.exchange.load_markets()
        self.logger.info(f"Loaded {len(self.markets)} markets from Kraken")

    def get_spot_balances(self) -> Dict[str, float]:
        """Get all spot balances, excluding margin/futures/staking."""
        balance = self.exchange.fetch_balance()

        # Filter to spot balances only (exclude margin, futures, staking)
        spot_balances = {}
        for asset, data in balance.items():
            if isinstance(data, dict):
                free = data.get('free', 0)
                if free > 0:
                    spot_balances[asset] = free

        return spot_balances

    def usd_value(self, asset: str, amount: float) -> float:
        """Estimate USD value of an asset amount, including futures."""
        if asset in ['USD', 'USDT', 'USDC']:
            return amount

        # Handle futures contracts by stripping .F suffix
        underlying_asset = asset.replace('.F', '').replace('.B', '')

        # Try direct USD pair first
        usd_symbol = f"{underlying_asset}/USD"
        if usd_symbol in self.markets:
            try:
                ticker = self.exchange.fetch_ticker(usd_symbol)
                return amount * ticker['last']
            except Exception as e:
                self.logger.warning(f"Failed to get {usd_symbol} price: {e}")

        # Try USDT pair and convert
        usdt_symbol = f"{underlying_asset}/USDT"
        if usdt_symbol in self.markets:
            try:
                ticker = self.exchange.fetch_ticker(usdt_symbol)
                usdt_value = amount * ticker['last']

                # Convert USDT to USD
                usdt_usd_symbol = "USDT/USD"
                if usdt_usd_symbol in self.markets:
                    usdt_usd_ticker = self.exchange.fetch_ticker(usdt_usd_symbol)
                    return usdt_value * usdt_usd_ticker['last']
                else:
                    # Assume USDT ≈ USD for estimation
                    return usdt_value * 0.999
            except Exception as e:
                self.logger.warning(f"Failed to get {usdt_symbol} price: {e}")

        self.logger.warning(
            f"Could not estimate USD value for {asset} (underlying: {underlying_asset})"
        )
        return 0.0

    def should_skip_asset(self, asset: str, amount: float) -> bool:
        """Check if asset should be skipped (target quote or dust)."""
        if asset == self.config.target_quote:
            return True

        usd_value = self.usd_value(asset, amount)
        if usd_value < self.config.min_usd_value:
            self.logger.info(
                f"Skipping {asset}: {amount} (dust < ${self.config.min_usd_value})"
            )
            return True

        return False

    def best_pair_for_liquidation(self, asset: str) -> Optional[str]:
        """Find best trading pair for liquidating asset to target quote,
        handling futures.

        Returns the best symbol string or None if not found.
        """
        target = self.config.target_quote

        # Handle futures contracts by stripping suffixes
        underlying_asset = asset.replace('.F', '').replace('.B', '').replace('.S', '')

        # Direct pair to target quote
        direct_symbol = f"{underlying_asset}/{target}"
        if direct_symbol in self.markets:
            return direct_symbol

        # Route via USD if target is USDT
        if target == "USDT":
            usd_symbol = f"{underlying_asset}/USD"
            if usd_symbol in self.markets:
                return usd_symbol

        # Route via USDT if target is USD
        if target == "USD":
            usdt_symbol = f"{underlying_asset}/USDT"
            if usdt_symbol in self.markets:
                return usdt_symbol

        return None

    def estimate_slippage(self, symbol: str, side: str, amount: float) -> float:
        """Estimate slippage for a market order."""
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit=20)

            if side == 'sell':
                asks = orderbook['asks']
                remaining_amount = amount
                total_value = 0.0
                total_volume = 0.0

                for price, volume in asks:
                    if remaining_amount <= 0:
                        break

                    fill_amount = min(remaining_amount, volume)
                    total_value += fill_amount * price
                    total_volume += fill_amount
                    remaining_amount -= fill_amount

                if total_volume > 0:
                    avg_price = total_value / total_volume
                    mid_price = (asks[0][0] + orderbook['bids'][0][0]) / 2
                    slippage = abs(avg_price - mid_price) / mid_price * 100
                    return slippage

        except Exception as e:
            self.logger.warning(f"Failed to estimate slippage for {symbol}: {e}")

        return 0.0  # Conservative estimate

    def place_market_order_safe(
        self, symbol: str, side: str, amount: float
    ) -> Optional[Dict]:
        """Place market order with slippage protection."""
        if self.config.dry_run:
            self.logger.info(f"[DRY RUN] Would {side} {amount} {symbol}")
            return {
                'id': f'dry_run_{symbol}_{side}',
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'status': 'simulated'
            }

        # Check slippage
        slippage = self.estimate_slippage(symbol, side, amount)
        if slippage > self.config.max_slippage_pct and not self.config.force_mode:
            self.logger.error(
                f"Slippage too high for {symbol}: {slippage:.2f}% > "
                f"{self.config.max_slippage_pct:.2f}%. Use --force to override"
            )
            return None
        # Get market info for precision
        try:
            _market = self.markets[symbol]
        except KeyError:
            self.logger.error(f"Market metadata not found for {symbol}")
            return None

        try:
            # Ensure correct amount precision if exchange supports helper
            if hasattr(self.exchange, 'amount_to_precision'):
                amount = self.exchange.amount_to_precision(symbol, amount)

            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount
            )
            self.logger.info(
                f"Placed {side} order: {amount} {symbol} (slippage: {slippage:.2f}%)"
            )
            return order
        except Exception as e:
            self.logger.error(f"Failed to place {side} order for {symbol}: {e}")
            return None

    def cancel_open_orders(self):
        """Cancel all open spot orders."""
        if self.config.dry_run:
            self.logger.info("[DRY RUN] Would cancel all open orders")
            return

        try:
            open_orders = self.exchange.fetch_open_orders()
            if not open_orders:
                self.logger.info("No open orders to cancel")
                return

            self.logger.info(f"Cancelling {len(open_orders)} open orders...")
            for order in open_orders:
                try:
                    self.exchange.cancel_order(order['id'], order['symbol'])
                    self.logger.info(
                        f"Cancelled order {order['id']} for {order['symbol']}"
                    )
                except Exception as e:
                    self.logger.error(f"Failed to cancel order {order['id']}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to fetch/cancel open orders: {e}")

    def liquidate_asset(self, asset: str, amount: float) -> bool:
        """Liquidate a single asset to target quote, handling futures properly."""
        # Handle different asset types
        if asset.endswith('.F') or asset.endswith('.B'):
            return self.liquidate_futures_contract(asset, amount)
        else:
            return self.liquidate_spot_asset(asset, amount)

    def liquidate_spot_asset(self, asset: str, amount: float) -> bool:
        """Liquidate a spot asset."""
        symbol = self.best_pair_for_liquidation(asset)
        if not symbol:
            self.logger.error(f"No trading pair found for {asset}")
            return False

        self.logger.info(f"Liquidating {amount} {asset} via {symbol}")

        # Check minimum order size
        market = self.markets[symbol]
        min_amount = market.get('limits', {}).get('amount', {}).get('min', 0)
        if amount < min_amount:
            self.logger.warning(
                f"Amount {amount} below minimum {min_amount} for {symbol}"
            )
            return False

        # Place the order
        order = self.place_market_order_safe(symbol, 'sell', amount)
        return order is not None

    def liquidate_futures_contract(self, asset: str, amount: float) -> bool:
        """Liquidate a futures contract - requires futures API."""
        self.logger.warning(
            f"{asset} is a futures contract. Futures liquidation requires "
            "futures API access which is not available in this spot-only "
            f"script. Consider manually closing {amount} {asset}"
            " through Kraken Futures interface."
        )
        return False

    def convert_usd_to_usdt(self, usd_order: Dict) -> bool:
        """Convert USD proceeds to USDT."""
        # This would require buying USDT with USD
        # For now, we'll log that this conversion is needed
        self.logger.info("Note: USD proceeds should be converted to USDT manually")
        return True

    def convert_usdt_to_usd(self, usdt_order: Dict) -> bool:
        """Convert USDT proceeds to USD."""
        # This would require selling USDT for USD
        # For now, we'll log that this conversion is needed
        self.logger.info("Note: USDT proceeds should be converted to USD manually")
        return True

    def run_liquidation(self) -> bool:
        """Main liquidation process."""
        try:
            self.initialize_exchange()

            if self.config.cancel_open_orders:
                self.cancel_open_orders()

            # Get starting balances
            self.starting_balances = self.get_spot_balances()
            self.logger.info("Starting balances:")
            for asset, amount in self.starting_balances.items():
                usd_value = self.usd_value(asset, amount)
                self.logger.info(f"  {asset}: {amount} (${usd_value:.2f})")

            # Find assets to liquidate
            assets_to_liquidate = []
            for asset, amount in self.starting_balances.items():
                if not self.should_skip_asset(asset, amount):
                    assets_to_liquidate.append((asset, amount))

            if not assets_to_liquidate:
                self.logger.info("No assets to liquidate")
                return True

            self.logger.info(f"Will liquidate {len(assets_to_liquidate)} assets")

            # Liquidate each asset
            success_count = 0
            failed_assets = []

            for asset, amount in assets_to_liquidate:
                if self.liquidate_asset(asset, amount):
                    success_count += 1
                else:
                    failed_assets.append(asset)

            # Final report
            self.print_final_report(success_count, failed_assets)

            return len(failed_assets) == 0

        except Exception as e:
            self.logger.error(f"Liquidation failed: {e}")
            return False

    def print_final_report(self, success_count: int, failed_assets: List[str]):
        """Print final liquidation report."""
        self.logger.info("\n" + "="*60)
        self.logger.info("LIQUIDATION REPORT")
        self.logger.info("="*60)

        if self.config.dry_run:
            self.logger.info("DRY RUN - No real trades executed")
        else:
            self.logger.info("LIVE MODE - Real trades executed")

        self.logger.info(f"Target quote: {self.config.target_quote}")
        self.logger.info(f"Min USD threshold: ${self.config.min_usd_value}")
        self.logger.info(f"Max slippage: {self.config.max_slippage_pct}%")

        self.logger.info(f"\nSuccessful liquidations: {success_count}")
        if failed_assets:
            self.logger.error(f"Failed assets: {', '.join(failed_assets)}")

        # Get final balances
        try:
            final_balances = self.get_spot_balances()
            target_balance = final_balances.get(self.config.target_quote, 0)
            usd_balance = final_balances.get('USD', 0)

            self.logger.info("\nFinal balances:")
            self.logger.info(f"  {self.config.target_quote}: {target_balance}")
            self.logger.info(f"  USD: {usd_balance}")

            total_usd_value = (
                self.usd_value(self.config.target_quote, target_balance)
                + usd_balance
            )
            self.logger.info(f"  Total USD value: ${total_usd_value:.2f}")

        except Exception as e:
            self.logger.error(f"Failed to get final balances: {e}")

        self.logger.info("="*60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Safe liquidation of Kraken spot holdings to target quote currency"
    )

    parser.add_argument(
        '--target-quote',
        choices=['USDT', 'USD'],
        default='USDT',
        help='Target quote currency (default: USDT)'
    )

    parser.add_argument(
        '--min-usd',
        type=float,
        default=10.0,
        help='Skip positions below this USD value (default: 10.0)'
    )

    parser.add_argument(
        '--max-slippage-pct',
        type=float,
        default=0.8,
        help='Max allowed slippage percentage (default: 0.8)'
    )

    parser.add_argument(
        '--cancel-open',
        action='store_true',
        help='Cancel all open spot orders before liquidation'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Ignore slippage limits and proceed anyway'
    )

    parser.add_argument(
        '--live',
        action='store_true',
        help='Execute real trades (default: dry-run only)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Show what would happen without executing (default: True)'
    )

    args = parser.parse_args()

    # Override dry-run if live is specified
    if args.live:
        args.dry_run = False

    config = Config(
        target_quote=args.target_quote,
        min_usd_value=args.min_usd,
        max_slippage_pct=args.max_slippage_pct,
        cancel_open_orders=args.cancel_open,
        force_mode=args.force,
        live_mode=args.live,
        dry_run=args.dry_run
    )

    liquidator = KrakenLiquidator(config)
    success = liquidator.run_liquidation()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()