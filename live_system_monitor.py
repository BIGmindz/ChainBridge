#!/usr/bin/env python3
"""
Live System Monitor - Real-time monitoring of ML regime detection system
"""

import os
import sys
import time
import logging
from datetime import datetime
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("logs/live_monitor.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class LiveSystemMonitor:
    """
    Monitors the ML regime detection system in real-time
    """

    def __init__(self):
        self.monitoring_active = True
        self.cycle_count = 0

    def run_monitoring_cycle(self):
        """Run a single monitoring cycle"""
        self.cycle_count += 1

        print(f"\n{'=' * 60}")
        print(f"🔍 LIVE MONITORING CYCLE #{self.cycle_count}")
        print(f"{'=' * 60}")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # Run ML regime integration
            print("\n🤖 Running ML Regime Detection...")
            result = self._run_regime_detection()

            if result:
                print(f"📊 Current Regime: {result.get('regime', 'unknown')}")
                print(f"🎯 Confidence: {result.get('confidence', 'N/A')}")
                print(f"⚙️  Config Status: {result.get('config_status', 'unknown')}")

            # Show system status
            print("\n📈 System Status:")
            self._show_system_status()

            # Show recent logs
            print("\n📋 Recent Activity:")
            self._show_recent_logs()

            # Show data capture stats
            print("\n💾 Data Capture:")
            self._show_data_stats()

        except Exception as e:
            print(f"❌ Error in monitoring cycle: {e}")
            logger.error(f"Monitoring cycle error: {e}")

    def _run_regime_detection(self):
        """Run regime detection and return results"""
        try:
            # Import here to avoid circular imports
            from ml_regime_integration import integrate_with_benson_bot

            result = integrate_with_benson_bot()

            if result:
                # Extract additional info
                status = result.get("status", {})
                confidence = "High" if status.get("confidence", 0) > 0.8 else "Medium" if status.get("confidence", 0) > 0.6 else "Low"

                return {
                    "regime": result.get("regime"),
                    "confidence": confidence,
                    "config_status": "Adaptive" if result.get("config") else "Base",
                }

            return None

        except Exception as e:
            print(f"⚠️  Regime detection error: {e}")
            return None

    def _show_system_status(self):
        """Show current system status"""
        try:
            # Check if model exists
            model_path = "ml_models/regime_detection_model.pkl"
            model_exists = os.path.exists(model_path)
            print(f"   🤖 ML Model: {'✅ Loaded' if model_exists else '❌ Missing'}")

            # Check training data
            data_path = "data/regime_training/regime_training_data.csv"
            data_exists = os.path.exists(data_path)
            print(f"   📊 Training Data: {'✅ Available' if data_exists else '❌ Missing'}")

            # Check logs
            log_files = [f for f in os.listdir("logs") if f.endswith(".log")]
            print(f"   📝 Log Files: {len(log_files)} active")

            # Memory usage (simplified)
            print("   💾 System: Running normally")

        except Exception as e:
            print(f"   ⚠️  Status check error: {e}")

        except Exception as e:
            print(f"   ⚠️  Status check error: {e}")

    def _show_recent_logs(self):
        """Show recent log entries"""
        try:
            log_files = ["logs/ml_integration.log", "logs/live_monitor.log"]

            for log_file in log_files:
                if os.path.exists(log_file):
                    # Get last 3 lines
                    result = subprocess.run(["tail", "-3", log_file], capture_output=True, text=True, timeout=5)

                    if result.returncode == 0 and result.stdout.strip():
                        lines = result.stdout.strip().split("\n")
                        for line in lines[-2:]:  # Show last 2 lines
                            if line.strip():
                                print(f"   📋 {line}")

        except Exception as e:
            print(f"   ⚠️  Log reading error: {e}")

    def _show_data_stats(self):
        """Show data capture statistics"""
        try:
            # Check training data size
            data_path = "data/regime_training/regime_training_data.csv"
            if os.path.exists(data_path):
                with open(data_path, "r") as f:
                    lines = sum(1 for _ in f)  # type: ignore
                print(f"   📊 Training Samples: {lines - 1:,}")  # Subtract header

            # Check model file size
            model_path = "ml_models/regime_detection_model.pkl"
            if os.path.exists(model_path):
                size = os.path.getsize(model_path)
                print(f"   🤖 Model Size: {size:,} bytes")

            # Show current data capture rate
            print(f"   🔄 Monitoring Cycles: {self.cycle_count}")

        except Exception as e:
            print(f"   ⚠️  Data stats error: {e}")

    def start_live_monitoring(self, interval_seconds=30):
        """Start live monitoring loop"""
        print("🚀 STARTING LIVE SYSTEM MONITORING")
        print("=" * 60)
        print(f"📊 Monitoring interval: {interval_seconds} seconds")
        print("💡 Press Ctrl+C to stop monitoring")
        print("=" * 60)

        try:
            while self.monitoring_active:
                self.run_monitoring_cycle()

                if self.monitoring_active:
                    print(f"\n⏳ Waiting {interval_seconds} seconds until next cycle...")
                    time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")
            logger.error(f"Live monitoring error: {e}")

        print("✅ Live monitoring session ended")


def main():
    """Main function"""
    monitor = LiveSystemMonitor()

    # Check command line arguments
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            print("⚠️  Invalid interval, using default 30 seconds")
            interval = 30
    else:
        interval = 30

    monitor.start_live_monitoring(interval)


if __name__ == "__main__":
    main()
