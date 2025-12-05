"""
Streaming aggregator for rolling ML features.
Maintains last event time, rolling averages, EMAs, anomaly accumulators.
"""

import numpy as np
from collections import defaultdict
import logging

logger = logging.getLogger("maggie.streaming.aggregator")

class RollingFeatureAggregator:
    def __init__(self):
        self.last_event_time = defaultdict(lambda: None)
        self.rolling_delay = defaultdict(list)
        self.ema_delay = defaultdict(lambda: None)
        self.anomaly_count = defaultdict(int)
        self.alpha = 0.2  # EMA smoothing factor

    def update(self, entity_id, delay, is_anomaly, event_time):
        self.last_event_time[entity_id] = event_time
        self.rolling_delay[entity_id].append(delay)
        if self.ema_delay[entity_id] is None:
            self.ema_delay[entity_id] = delay
        else:
            self.ema_delay[entity_id] = self.alpha * delay + (1 - self.alpha) * self.ema_delay[entity_id]
        if is_anomaly:
            self.anomaly_count[entity_id] += 1
        logger.info(f"Updated rolling features for {entity_id}")

    def get_features(self, entity_id):
        delays = self.rolling_delay[entity_id]
        return {
            "last_event_time": self.last_event_time[entity_id],
            "rolling_avg_delay": np.mean(delays) if delays else None,
            "ema_delay": self.ema_delay[entity_id],
            "anomaly_count": self.anomaly_count[entity_id],
        }
