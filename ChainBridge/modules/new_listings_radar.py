#!/usr/bin/env python3
"""
NEW LISTINGS RADAR
Standalone module for monitoring exchanges for new coin listings
Detects new listings across major exchanges and generates signals
"""

import json
import logging
import sys
import time
from datetime import datetime

from modules.new_listings_radar_module import NewListingsRadar

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("new_listings_radar.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


class ListingsMonitor:
    """Main class for running the new listings radar"""

    def __init__(self):
        self.radar = NewListingsRadar()
        self.listings = []
        self.last_scan = None
        self.scan_interval = 600  # 10 minutes between scans

    def scan_exchanges(self):
        """Scan all exchanges for new listings"""
        logging.info("📡 Scanning exchanges for new listings...")
        print(
            "\n        ╔════════════════════════════════════════════════════════════╗"
        )
        print("        ║   EXECUTING NEW LISTINGS STRATEGY                        ║")
        print("        ╚════════════════════════════════════════════════════════════╝")

        # Call radar module to scan exchanges
        self.listings = self.radar.scan_all_exchanges()
        self.last_scan = datetime.now()

        # Log discoveries
        if self.listings:
            logging.info(f"🎯 NEW LISTING OPPORTUNITIES FOUND: {len(self.listings)}")
            logging.info("=" * 60)

            for listing in self.listings:
                logging.info(f"\n💎 {listing['symbol']} on {listing['exchange']}")
                logging.info(f"   Confidence: {listing['confidence']}%")
                logging.info(f"   Expected Return: {listing['expected_return']}%")
                logging.info(f"   Position Size: {listing['position_size']}%")
                logging.info(f"   Entry: {listing['entry']}")
                logging.info(f"   Stop Loss: {listing['stop_loss']}%")
                logging.info(f"   Take Profit: {listing['take_profit']}%")
                logging.info(f"   Risk Level: {listing['risk_level']}")

            # Save listings to file for other components
            self._save_listings()
        else:
            logging.info("No new listings discovered in this scan")

    def _save_listings(self):
        """Save listings to file"""
        try:
            with open("new_listings.json", "w") as f:
                json.dump(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "listings": self.listings,
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logging.error(f"Error saving listings: {e}")

    def continuous_monitoring(self):
        """Run continuous monitoring loop"""
        logging.info("Starting continuous monitoring for new listings...")

        try:
            while True:
                self.scan_exchanges()
                logging.info(f"Waiting {self.scan_interval} seconds until next scan...")
                time.sleep(self.scan_interval)
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Error in monitoring loop: {e}")
            sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="New Listings Radar Monitor")
    parser.add_argument("--scan", action="store_true", help="Scan exchanges once")
    parser.add_argument(
        "--monitor", action="store_true", help="Continuously monitor for new listings"
    )
    parser.add_argument(
        "--interval", type=int, default=600, help="Scan interval in seconds"
    )
    args = parser.parse_args()

    monitor = ListingsMonitor()
    if args.monitor:
        monitor.scan_interval = args.interval
        monitor.continuous_monitoring()
    else:
        # Default to single scan if no args provided
        monitor.scan_exchanges()


if __name__ == "__main__":
    import argparse

    main()
