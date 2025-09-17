#!/usr/bin/env python3
"""
Market Regime Integration Module

This module integrates market regime detection with signal weight optimization,
providing a bridge between the market condition classifier and the adaptive weight model.
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional, Union

# Import related modules
from modules.adaptive_weight_module.market_condition_classifier import MarketConditionClassifier


class MarketRegimeIntegrator:
    """
    Integrates market regime detection with signal weight optimization
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the market regime integrator"""
        self.config = config or {}
        
        # Initialize market condition classifier
        self.market_classifier = MarketConditionClassifier(self.config)
        
        # Directory to store regime history and statistics
        self.data_dir = os.path.join(
            self.config.get("data_dir", "data"), 
            "market_regime_data"
        )
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Regime statistics and history
        self.regime_stats = {
            "transitions": {},
            "durations": {},
            "performance": {}
        }
        
        # Load existing stats if available
        self._load_regime_stats()
    
    def _load_regime_stats(self) -> None:
        """Load existing regime statistics if available"""
        stats_path = os.path.join(self.data_dir, "regime_stats.json")
        if os.path.exists(stats_path):
            try:
                with open(stats_path, "r") as f:
                    self.regime_stats = json.load(f)
            except Exception as e:
                print(f"Error loading regime stats: {str(e)}")
    
    def save_regime_stats(self) -> None:
        """Save regime statistics to disk"""
        stats_path = os.path.join(self.data_dir, "regime_stats.json")
        try:
            with open(stats_path, "w") as f:
                json.dump(self.regime_stats, f, indent=2)
        except Exception as e:
            print(f"Error saving regime stats: {str(e)}")
    
    def detect_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect current market regime using the classifier
        
        Args:
            market_data: Dictionary with price and volume history
            
        Returns:
            Dictionary with regime detection results
        """
        price_history = market_data.get("price_history", [])
        volume_history = market_data.get("volume_history", [])
        
        # Detect regime
        regime_results = self.market_classifier.detect_regime(price_history, volume_history)
        
        # Update regime history and statistics
        self._update_regime_stats(regime_results)
        
        return regime_results
    
    def _update_regime_stats(self, regime_results: Dict[str, Any]) -> None:
        """
        Update regime statistics based on new detection
        
        Args:
            regime_results: Results from regime detection
        """
        current_regime = regime_results.get("regime")
        current_time = datetime.now()
        
        # Get regime history
        regime_history = self.market_classifier.get_regime_history()
        
        if not regime_history:
            return
        
        # Check for regime transitions
        if len(regime_history) >= 2:
            prev_regime = regime_history[-2]["regime"]
            
            if prev_regime != current_regime:
                # Update transition counts
                transitions = self.regime_stats["transitions"]
                
                if prev_regime not in transitions:
                    transitions[prev_regime] = {}
                
                if current_regime not in transitions[prev_regime]:
                    transitions[prev_regime][current_regime] = 0
                
                transitions[prev_regime][current_regime] += 1
    
    def get_regime_performance(self) -> Dict[str, Any]:
        """
        Get performance statistics for each market regime
        
        Returns:
            Dictionary with performance metrics by regime
        """
        return self.regime_stats.get("performance", {})
    
    def get_regime_weights(self, regime_results: Dict[str, Any]) -> Dict[str, float]:
        """
        Get optimized signal weights based on detected regime
        
        Args:
            regime_results: Results from regime detection
            
        Returns:
            Dictionary with weight multipliers for each signal layer
        """
        regime = regime_results.get("regime")
        confidence = regime_results.get("confidence", 0.0)
        
        # Get base weights from classifier
        base_weights = self.market_classifier.get_regime_weights(regime)
        
        # Adjust weights based on confidence
        # Lower confidence = closer to neutral weights
        adjusted_weights = {}
        for layer, weight in base_weights.items():
            # Weight adjustment formula: 
            # final_weight = 1.0 + (base_weight - 1.0) * confidence
            adjusted_weights[layer] = 1.0 + (weight - 1.0) * confidence
        
        return adjusted_weights
    
    def update_performance_metrics(self, regime: str, metrics: Dict[str, float]) -> None:
        """
        Update performance metrics for a specific regime
        
        Args:
            regime: Market regime name
            metrics: Dictionary with performance metrics
        """
        if "performance" not in self.regime_stats:
            self.regime_stats["performance"] = {}
        
        if regime not in self.regime_stats["performance"]:
            self.regime_stats["performance"][regime] = {
                "total_trades": 0,
                "winning_trades": 0,
                "pnl": 0.0,
                "sharpe": 0.0,
                "max_drawdown": 0.0,
                "avg_trade_duration": 0.0
            }
        
        # Update metrics
        regime_perf = self.regime_stats["performance"][regime]
        
        regime_perf["total_trades"] += metrics.get("trades", 0)
        regime_perf["winning_trades"] += metrics.get("winning_trades", 0)
        regime_perf["pnl"] += metrics.get("pnl", 0.0)
        
        # Update averages for other metrics
        if regime_perf["total_trades"] > 0:
            n_trades = regime_perf["total_trades"]
            
            # Update Sharpe ratio (weighted average)
            old_weight = (n_trades - 1) / n_trades
            new_weight = 1 / n_trades
            regime_perf["sharpe"] = (regime_perf["sharpe"] * old_weight + 
                                     metrics.get("sharpe", 0.0) * new_weight)
            
            # Keep track of worst drawdown
            regime_perf["max_drawdown"] = max(
                regime_perf["max_drawdown"],
                metrics.get("max_drawdown", 0.0)
            )
            
            # Update average trade duration
            regime_perf["avg_trade_duration"] = (
                regime_perf["avg_trade_duration"] * old_weight +
                metrics.get("avg_trade_duration", 0.0) * new_weight
            )
        
        # Calculate win rate
        if regime_perf["total_trades"] > 0:
            regime_perf["win_rate"] = (
                regime_perf["winning_trades"] / regime_perf["total_trades"]
            ) * 100.0
        
        # Save updated statistics
        self.save_regime_stats()
    
    def train_regime_model(self, historical_data: Dict[str, Any]) -> bool:
        """
        Train the market regime model with historical data
        
        Args:
            historical_data: Dictionary with price and volume history
            
        Returns:
            True if training was successful, False otherwise
        """
        return self.market_classifier.train_model(historical_data)
    
    def get_regime_transition_matrix(self) -> pd.DataFrame:
        """
        Get the transition probability matrix between regimes
        
        Returns:
            Pandas DataFrame with transition probabilities
        """
        return self.market_classifier.get_regime_transition_matrix()
    
    def get_regime_visualization_data(self) -> Dict[str, Any]:
        """
        Get data for visualizing market regimes
        
        Returns:
            Dictionary with visualization data
        """
        # Get regime history
        regime_history = self.market_classifier.get_regime_history(days=30)
        
        # Extract regimes and timestamps
        regimes = [item["regime"] for item in regime_history]
        timestamps = [item["timestamp"] for item in regime_history]
        confidences = [item["confidence"] for item in regime_history]
        
        # Get transition matrix
        transition_matrix = self.get_regime_transition_matrix()
        
        # Get performance by regime
        performance = self.get_regime_performance()
        
        return {
            "regime_history": {
                "regimes": regimes,
                "timestamps": timestamps,
                "confidences": confidences
            },
            "transition_matrix": transition_matrix.to_dict() if not transition_matrix.empty else {},
            "performance": performance
        }