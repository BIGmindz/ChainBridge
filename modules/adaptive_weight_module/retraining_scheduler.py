#!/usr/bin/env python3
"""
Automated Retraining Scheduler

This script implements a scheduler that automatically retrains
the adaptive weight model every 24 hours using the most recent 7 days of data.
It can be run as a standalone script or integrated into the main trading system.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict

# Try to import schedule library - wrapped in try-except for optional dependency
try:
    import schedule

    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    print("schedule library not available. Automated retraining scheduling will be disabled.")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/adaptive_weight_scheduler.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("adaptive_weight_scheduler")

from modules.adaptive_weight_module.market_regime_integrator import (  # noqa: E402
    MarketRegimeIntegrator,
)

# Import the trainer
from modules.adaptive_weight_module.weight_trainer import (  # noqa: E402
    AdaptiveWeightTrainer,
)
from modules.adaptive_weight_module.weight_visualizer import (  # noqa: E402
    AdaptiveWeightVisualizer,
)


class AdaptiveWeightScheduler:
    """
    Scheduler for automated retraining of the adaptive weight model
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the scheduler"""
        self.config = config or {}

        # Configure retraining frequency
        self.retrain_hour = self.config.get("retrain_hour", 2)  # 2 AM by default
        self.lookback_days = self.config.get("lookback_days", 7)
        self.retrain_frequency = self.config.get("retrain_frequency", "daily")

        # Configure paths
        self.logs_dir = os.path.join(self.config.get("logs_dir", "logs"), "adaptive_weight_scheduler")
        os.makedirs(self.logs_dir, exist_ok=True)

        # Last training time tracking
        self.last_trained = None
        self.last_trained_file = os.path.join(self.logs_dir, "last_trained.json")
        self._load_last_trained()

        # Initialize components
        self.trainer = AdaptiveWeightTrainer(self.config)
        self.regime_integrator = MarketRegimeIntegrator(self.config)
        self.visualizer = AdaptiveWeightVisualizer(self.config)

        # Schedule for retraining
        self._setup_schedule()

    def _load_last_trained(self) -> None:
        """Load the timestamp of the last training"""
        if os.path.exists(self.last_trained_file):
            try:
                with open(self.last_trained_file, "r") as f:
                    data = json.load(f)
                    self.last_trained = data.get("last_trained")
            except Exception as e:
                logger.error(f"Error loading last trained timestamp: {str(e)}")

    def _save_last_trained(self) -> None:
        """Save the timestamp of the last training"""
        with open(self.last_trained_file, "w") as f:
            json.dump(
                {
                    "last_trained": self.last_trained,
                    "timestamp": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def _setup_schedule(self) -> None:
        """Set up the training schedule"""
        if self.retrain_frequency == "daily":
            schedule.every().day.at(f"{self.retrain_hour:02d}:00").do(self.retrain_model)
        elif self.retrain_frequency == "hourly":
            schedule.every().hour.do(self.retrain_model)
        else:
            # Default to daily
            schedule.every().day.at(f"{self.retrain_hour:02d}:00").do(self.retrain_model)

        logger.info(f"Scheduled retraining with frequency: {self.retrain_frequency}")

    def retrain_model(self) -> Dict[str, Any]:
        """
        Retrain the adaptive weight model and generate visualizations

        Returns:
            Dictionary with retraining results
        """
        logger.info("Starting scheduled model retraining")

        try:
            # Start timing
            start_time = datetime.now()

            # Train the model
            training_results = self.trainer.train_model(lookback_days=self.lookback_days)

            if training_results.get("status") != "success":
                logger.error(f"Training failed: {training_results.get('message', 'Unknown error')}")
                return training_results

            # Update last trained timestamp
            self.last_trained = datetime.now().isoformat()
            self._save_last_trained()

            # Evaluate the model
            evaluation_results = self.trainer.evaluate_model()

            # Generate visualizations
            viz_data = self._gather_visualization_data()
            dashboard_path = self.visualizer.create_dashboard(viz_data)

            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Save results
            results = {
                "status": "success",
                "training_results": training_results,
                "evaluation_results": evaluation_results,
                "dashboard_path": dashboard_path,
                "duration_seconds": duration,
                "timestamp": end_time.isoformat(),
            }

            # Log success
            logger.info(f"Model retraining completed successfully in {duration:.2f} seconds")

            return results

        except Exception as e:
            logger.exception(f"Error during scheduled retraining: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _gather_visualization_data(self) -> Dict[str, Any]:
        """Gather data for visualizations"""
        # Get regime data
        regime_data = {"regime_history": self.regime_integrator.market_classifier.get_regime_history(days=30)}

        # Get transition matrix
        transition_matrix = self.regime_integrator.get_regime_transition_matrix().to_dict()  # type: ignore

        # Get performance data
        performance_data = self.regime_integrator.get_regime_performance()

        # Get current weights
        current_weights = self.trainer.evaluate_model().get("layer_avg_weights", {})

        # Gather historical weight data
        weight_history = self._load_weight_history()

        return {
            "regime_data": regime_data,
            "transition_matrix": transition_matrix,
            "performance_data": performance_data,
            "weight_history": weight_history,
            "current_weights": current_weights,
        }

    def _load_weight_history(self) -> list[dict[str, any]]:
        """Load historical weight data"""
        history = []

        # Look for weight history files
        history_dir = os.path.join(self.config.get("data_dir", "data"), "adaptive_weight_data")
        if not os.path.exists(history_dir):
            return history

        # Find and load history files
        history_files = sorted([f for f in os.listdir(history_dir) if f.endswith("_weights.json")])
        for filename in history_files[-30:]:  # Get the 30 most recent files
            try:
                with open(os.path.join(history_dir, filename), "r") as f:
                    data = json.load(f)
                    history.append(data)  # type: ignore
            except Exception as e:
                logger.error(f"Error loading weight history file {filename}: {str(e)}")

        return history

    def run(self) -> None:
        """Run the scheduler loop"""
        logger.info("Starting adaptive weight scheduler")

        # Immediately train if never trained before
        if self.last_trained is None:
            logger.info("No previous training detected, training now")
            self.retrain_model()
        else:
            # Check if it's been more than 24 hours since last training
            last_train_time = datetime.fromisoformat(self.last_trained)
            time_since_last = datetime.now() - last_train_time

            if time_since_last.total_seconds() > 24 * 3600:
                logger.info(f"Last training was {time_since_last.total_seconds() / 3600:.1f} hours ago, training now")
                self.retrain_model()

        # Run the scheduler loop
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.exception(f"Error in scheduler loop: {str(e)}")
                time.sleep(300)  # Wait 5 minutes before retrying after an error


def main():
    """Main entry point"""
    # Load configuration
    config_path = os.path.join("config", "adaptive_weight_config.json")
    config = {}

    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")

    # Create and run the scheduler
    scheduler = AdaptiveWeightScheduler(config)
    scheduler.run()


if __name__ == "__main__":
    main()
