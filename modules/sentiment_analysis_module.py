"""
Sentiment Analysis Module

This module implements sentiment-based signal generation using alternative data sources
like geopolitical events, social media sentiment, and market fear/greed indicators.
This provides fundamental analysis signals uncorrelated to technical indicators.
"""

import math
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple

from core.module_manager import Module

# Add the parent directory to import data_ingestor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_ingestor import fetch_all_alternative_data


class SentimentAnalysisModule(Module):
    """Sentiment Analysis and alternative data signal generation module."""

    VERSION = "1.0.0"

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.sentiment_weights = (
            config.get(
                "sentiment_weights",
                {
                    "trump_sentiment_score": 0.2,
                    "market_fear_greed_index": 0.3,
                    "brazil_regulatory_score": 0.15,
                    "india_regulatory_score": 0.1,
                    "btc_exchange_netflow": 0.25,
                },
            )
            if config
            else {
                "trump_sentiment_score": 0.2,
                "market_fear_greed_index": 0.3,
                "brazil_regulatory_score": 0.15,
                "india_regulatory_score": 0.1,
                "btc_exchange_netflow": 0.25,
            }
        )
        self.sentiment_threshold_strong = (
            config.get("sentiment_threshold_strong", 0.7) if config else 0.7
        )
        self.sentiment_threshold_moderate = (
            config.get("sentiment_threshold_moderate", 0.4) if config else 0.4
        )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "input": {
                "alternative_data": "dict (optional, will fetch if not provided)",
                "sentiment_weights": "dict (optional, custom weights for each data source)",
                "current_price": "float (optional, for price-sentiment divergence analysis)",
                "price_trend": "string (optional, UPWARD/DOWNWARD/NEUTRAL for divergence analysis)",
            },
            "output": {
                "composite_sentiment_score": "float (-1 to 1)",
                "individual_scores": "dict (breakdown by data source)",
                "signal": "string (BUY/SELL/HOLD)",
                "confidence": "float (0-1)",
                "sentiment_strength": "string (STRONG/MODERATE/WEAK)",
                "dominant_factors": "list (main drivers of sentiment)",
                "sentiment_analysis": {
                    "bullish_factors": "list",
                    "bearish_factors": "list",
                    "neutral_factors": "list",
                },
                "metadata": {
                    "data_sources_used": "integer",
                    "sentiment_weights_used": "dict",
                },
            },
        }

    def normalize_sentiment_score(self, value: float, data_type: str) -> float:
        """
        Normalize different types of sentiment data to a -1 to 1 scale.

        Args:
            value: Raw value from data source
            data_type: Type of data to determine normalization method

        Returns:
            Normalized score between -1 (very bearish) and 1 (very bullish)
        """
        if data_type == "fear_greed_index":
            # Fear & Greed Index: 0-100 scale where 0=extreme fear, 100=extreme greed
            # Convert to -1 to 1 scale
            return (value - 50) / 50

        elif data_type == "regulatory_score":
            # Regulatory scores: already -1 to 1 scale
            return max(-1, min(1, value))

        elif data_type == "exchange_netflow":
            # Exchange netflow: negative = outflow (bullish), positive = inflow (bearish)
            # Normalize based on magnitude (assuming typical values are -10000 to 10000)
            normalized = -value / 5000  # Invert sign and scale
            return max(-1, min(1, normalized))

        elif data_type == "social_sentiment":
            # Social sentiment scores: already -1 to 1 scale
            return max(-1, min(1, value))

        else:
            # Default: assume already normalized
            return max(-1, min(1, value))

    def calculate_composite_sentiment(
        self, alternative_data: Dict[str, float], weights: Dict[str, float]
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate composite sentiment score from multiple data sources.

        Returns:
            Tuple of (composite_score, individual_normalized_scores)
        """
        individual_scores = {}
        weighted_sum = 0.0
        total_weight = 0.0

        # Process each data source
        for source, raw_value in alternative_data.items():
            if source in weights:
                weight = weights[source]

                # Normalize based on data type
                if "fear_greed_index" in source:
                    normalized_score = self.normalize_sentiment_score(
                        raw_value, "fear_greed_index"
                    )
                elif "regulatory" in source:
                    normalized_score = self.normalize_sentiment_score(
                        raw_value, "regulatory_score"
                    )
                elif "netflow" in source:
                    normalized_score = self.normalize_sentiment_score(
                        raw_value, "exchange_netflow"
                    )
                elif "sentiment" in source:
                    normalized_score = self.normalize_sentiment_score(
                        raw_value, "social_sentiment"
                    )
                else:
                    normalized_score = self.normalize_sentiment_score(
                        raw_value, "default"
                    )

                individual_scores[source] = normalized_score
                weighted_sum += normalized_score * weight
                total_weight += weight

        # Calculate composite score
        composite_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        return composite_score, individual_scores

    def categorize_sentiment_factors(
        self, individual_scores: Dict[str, float]
    ) -> Dict[str, List]:
        """
        Categorize sentiment factors into bullish, bearish, and neutral.

        Returns:
            Dict with 'bullish_factors', 'bearish_factors', 'neutral_factors'
        """
        bullish_factors = []
        bearish_factors = []
        neutral_factors = []

        for source, score in individual_scores.items():
            # Clean up source names for display
            display_name = source.replace("_", " ").title()

            if score > 0.3:
                bullish_factors.append(
                    {
                        "factor": display_name,
                        "score": score,
                        "strength": "STRONG" if score > 0.7 else "MODERATE",
                    }
                )
            elif score < -0.3:
                bearish_factors.append(
                    {
                        "factor": display_name,
                        "score": score,
                        "strength": "STRONG" if score < -0.7 else "MODERATE",
                    }
                )
            else:
                neutral_factors.append({"factor": display_name, "score": score})

        return {
            "bullish_factors": bullish_factors,
            "bearish_factors": bearish_factors,
            "neutral_factors": neutral_factors,
        }

    def identify_dominant_factors(
        self, individual_scores: Dict[str, float], top_n: int = 3
    ) -> List[Dict]:
        """
        Identify the most influential sentiment factors.

        Returns:
            List of dominant factors sorted by absolute impact
        """
        # Sort by absolute score value
        sorted_factors = sorted(
            individual_scores.items(), key=lambda x: abs(x[1]), reverse=True
        )

        dominant_factors = []
        for source, score in sorted_factors[:top_n]:
            display_name = source.replace("_", " ").title()
            impact_direction = (
                "BULLISH" if score > 0 else "BEARISH" if score < 0 else "NEUTRAL"
            )

            dominant_factors.append(
                {
                    "factor": display_name,
                    "score": score,
                    "impact": impact_direction,
                    "strength": abs(score),
                }
            )

        return dominant_factors

    def generate_signal(
        self,
        composite_score: float,
        individual_scores: Dict[str, float],
        current_price: float = None,
        price_trend: str = None,
    ) -> Tuple[str, float, str]:
        """
        Generate trading signal based on sentiment analysis.

        Returns:
            Tuple of (signal, confidence, sentiment_strength)
        """
        signal = "HOLD"
        confidence = 0.0

        # Determine sentiment strength
        abs_score = abs(composite_score)
        if abs_score >= self.sentiment_threshold_strong:
            sentiment_strength = "STRONG"
        elif abs_score >= self.sentiment_threshold_moderate:
            sentiment_strength = "MODERATE"
        else:
            sentiment_strength = "WEAK"

        # Basic sentiment-driven signals
        if composite_score > self.sentiment_threshold_moderate:
            signal = "BUY"
            confidence = min(1.0, abs(composite_score))
        elif composite_score < -self.sentiment_threshold_moderate:
            signal = "SELL"
            confidence = min(1.0, abs(composite_score))

        # Enhance confidence based on consensus
        consensus_factors = len(
            [
                score
                for score in individual_scores.values()
                if (score > 0.2 and composite_score > 0)
                or (score < -0.2 and composite_score < 0)
            ]
        )
        total_factors = len(individual_scores)

        if total_factors > 0:
            consensus_ratio = consensus_factors / total_factors
            confidence *= 0.5 + (
                consensus_ratio * 0.5
            )  # Boost confidence with consensus

        # Price-sentiment divergence analysis (if price data provided)
        if current_price is not None and price_trend is not None:
            if price_trend == "UPWARD" and composite_score < -0.3:
                # Price rising but sentiment negative - potential reversal signal
                signal = "SELL"
                confidence = max(confidence, 0.6)
            elif price_trend == "DOWNWARD" and composite_score > 0.3:
                # Price falling but sentiment positive - potential reversal signal
                signal = "BUY"
                confidence = max(confidence, 0.6)

        # Special handling for extreme sentiment readings
        if abs_score > 0.8:
            # Very extreme sentiment - potential contrarian signal
            # In crypto markets, extreme fear can be buying opportunity
            # and extreme greed can be selling opportunity
            if composite_score > 0.8:  # Extreme greed
                signal = "SELL"
                confidence = min(1.0, abs_score)
            elif composite_score < -0.8:  # Extreme fear
                signal = "BUY"
                confidence = min(1.0, abs_score)

        return signal, confidence, sentiment_strength

    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process alternative data and generate sentiment-based signals."""

        try:
            # Get alternative data (either provided or fetch fresh)
            alternative_data = data.get("alternative_data")
            if alternative_data is None:
                alternative_data = fetch_all_alternative_data()

            if not alternative_data:
                return {
                    "composite_sentiment_score": 0.0,
                    "individual_scores": {},
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "sentiment_strength": "WEAK",
                    "dominant_factors": [],
                    "sentiment_analysis": {
                        "bullish_factors": [],
                        "bearish_factors": [],
                        "neutral_factors": [],
                    },
                    "metadata": {
                        "data_sources_used": 0,
                        "sentiment_weights_used": self.sentiment_weights,
                        "error": "No alternative data available",
                    },
                }

            # Get configuration
            sentiment_weights = data.get("sentiment_weights", self.sentiment_weights)
            current_price = data.get("current_price")
            price_trend = data.get("price_trend")

            # Calculate composite sentiment
            composite_score, individual_scores = self.calculate_composite_sentiment(
                alternative_data, sentiment_weights
            )

            # Categorize sentiment factors
            sentiment_factors = self.categorize_sentiment_factors(individual_scores)

            # Identify dominant factors
            dominant_factors = self.identify_dominant_factors(individual_scores)

            # Generate signal
            signal, confidence, sentiment_strength = self.generate_signal(
                composite_score, individual_scores, current_price, price_trend
            )

            result = {
                "composite_sentiment_score": composite_score,
                "individual_scores": individual_scores,
                "signal": signal,
                "confidence": confidence,
                "sentiment_strength": sentiment_strength,
                "dominant_factors": dominant_factors,
                "sentiment_analysis": sentiment_factors,
                "raw_data": alternative_data,
                "sentiment_interpretation": {
                    "overall_sentiment": (
                        "BULLISH"
                        if composite_score > 0.1
                        else "BEARISH" if composite_score < -0.1 else "NEUTRAL"
                    ),
                    "sentiment_magnitude": abs(composite_score),
                    "market_conditions": self._interpret_market_conditions(
                        individual_scores
                    ),
                    "risk_factors": self._identify_risk_factors(individual_scores),
                    "opportunity_factors": self._identify_opportunity_factors(
                        individual_scores
                    ),
                },
                "metadata": {
                    "data_sources_used": len(individual_scores),
                    "sentiment_weights_used": sentiment_weights,
                    "data_freshness": datetime.now().isoformat(),
                    "module_info": {
                        "name": self.name,
                        "version": self.version,
                        "signal_type": "fundamental_sentiment",
                    },
                },
            }

            return result

        except Exception as e:
            raise RuntimeError(f"Failed to process sentiment analysis: {str(e)}")

    def _interpret_market_conditions(self, individual_scores: Dict[str, float]) -> str:
        """Interpret overall market conditions from individual sentiment scores."""
        fear_greed = individual_scores.get("market_fear_greed_index", 0)
        regulatory_avg = (
            individual_scores.get("brazil_regulatory_score", 0)
            + individual_scores.get("india_regulatory_score", 0)
        ) / 2

        if fear_greed > 0.5 and regulatory_avg > 0:
            return "OPTIMISTIC"
        elif fear_greed < -0.5 and regulatory_avg < 0:
            return "PESSIMISTIC"
        elif fear_greed > 0.3:
            return "GREEDY"
        elif fear_greed < -0.3:
            return "FEARFUL"
        else:
            return "NEUTRAL"

    def _identify_risk_factors(self, individual_scores: Dict[str, float]) -> List[str]:
        """Identify current risk factors from sentiment data."""
        risk_factors = []

        if individual_scores.get("market_fear_greed_index", 0) > 0.7:
            risk_factors.append("Extreme Greed - Market overheating risk")

        if individual_scores.get("brazil_regulatory_score", 0) < -0.5:
            risk_factors.append("Negative Brazilian regulatory environment")

        if individual_scores.get("india_regulatory_score", 0) < -0.5:
            risk_factors.append("Negative Indian regulatory environment")

        if individual_scores.get("btc_exchange_netflow", 0) < -0.7:
            risk_factors.append(
                "Heavy BTC outflows from exchanges - potential selling pressure"
            )

        return risk_factors

    def _identify_opportunity_factors(
        self, individual_scores: Dict[str, float]
    ) -> List[str]:
        """Identify current opportunity factors from sentiment data."""
        opportunity_factors = []

        if individual_scores.get("market_fear_greed_index", 0) < -0.5:
            opportunity_factors.append("Market fear - potential buying opportunity")

        if individual_scores.get("trump_sentiment_score", 0) > 0.5:
            opportunity_factors.append("Positive political sentiment")

        if individual_scores.get("btc_exchange_netflow", 0) > 0.5:
            opportunity_factors.append("BTC accumulation - reduced selling pressure")

        regulatory_sentiment = (
            individual_scores.get("brazil_regulatory_score", 0)
            + individual_scores.get("india_regulatory_score", 0)
        ) / 2

        if regulatory_sentiment > 0.3:
            opportunity_factors.append("Positive regulatory environment")

        return opportunity_factors

    def backtest_strategy(
        self,
        historical_data: List[Dict[str, Any]],
        sentiment_data_history: List[Dict[str, float]] = None,
        initial_balance: float = 10000,
    ) -> Dict[str, Any]:
        """
        Simple backtesting functionality for Sentiment Analysis strategy.

        Note: This uses mock sentiment data if historical sentiment data is not provided.
        """
        if not historical_data:
            raise ValueError("Historical data is required for backtesting")

        balance = initial_balance
        position = 0
        trades = []
        signals_history = []

        # Generate mock sentiment data if not provided
        if sentiment_data_history is None:
            sentiment_data_history = self._generate_mock_sentiment_history(
                len(historical_data)
            )

        for i, (price_data, sentiment_data) in enumerate(
            zip(historical_data, sentiment_data_history)
        ):
            if i == 0:
                continue  # Skip first entry

            # Process sentiment for this period
            result = self.process({"alternative_data": sentiment_data})

            signal = result["signal"]
            price = price_data.get("close", price_data.get("price", 0))
            confidence = result["confidence"]

            signals_history.append(
                {
                    "date": i,
                    "price": price,
                    "composite_sentiment": result["composite_sentiment_score"],
                    "signal": signal,
                    "confidence": confidence,
                    "sentiment_strength": result["sentiment_strength"],
                }
            )

            # Trade on moderate to high confidence signals
            if confidence >= 0.5:
                if signal == "BUY" and position == 0:
                    position = balance / price
                    balance = 0
                    trades.append(
                        {
                            "type": "BUY",
                            "price": price,
                            "sentiment_score": result["composite_sentiment_score"],
                            "confidence": confidence,
                            "position": position,
                        }
                    )
                elif signal == "SELL" and position > 0:
                    balance = position * price
                    pnl = balance - initial_balance
                    trades.append(
                        {
                            "type": "SELL",
                            "price": price,
                            "sentiment_score": result["composite_sentiment_score"],
                            "confidence": confidence,
                            "pnl": pnl,
                        }
                    )
                    position = 0

        # Calculate final portfolio value
        final_price = (
            historical_data[-1]["close"]
            if "close" in historical_data[-1]
            else historical_data[-1]["price"]
        )
        final_value = balance + (position * final_price)

        return {
            "initial_balance": initial_balance,
            "final_value": final_value,
            "total_return": final_value - initial_balance,
            "return_percentage": ((final_value - initial_balance) / initial_balance)
            * 100,
            "total_trades": len(trades),
            "total_signals": len(signals_history),
            "sentiment_driven_trades": len(
                [t for t in trades if abs(t.get("sentiment_score", 0)) > 0.3]
            ),
            "high_confidence_trades": len(
                [t for t in trades if t.get("confidence", 0) > 0.7]
            ),
            "signal_accuracy": self._calculate_signal_accuracy(
                signals_history,
                [p["close"] if "close" in p else p["price"] for p in historical_data],
            ),
            "trades": trades,
            "signals_history": signals_history[-10:],  # Last 10 signals for inspection
        }

    def _generate_mock_sentiment_history(self, length: int) -> List[Dict[str, float]]:
        """Generate mock sentiment data for backtesting."""
        import random

        sentiment_history = []
        for i in range(length):
            # Generate somewhat realistic sentiment data with trends
            base_sentiment = 0.1 * math.sin(i * 0.1)  # Slow oscillation
            noise = random.uniform(-0.3, 0.3)  # Random noise

            sentiment_data = {
                "trump_sentiment_score": max(-1, min(1, base_sentiment + noise)),
                "market_fear_greed_index": max(
                    0, min(100, 50 + (base_sentiment + noise) * 30)
                ),
                "brazil_regulatory_score": max(
                    -1, min(1, base_sentiment * 0.5 + random.uniform(-0.2, 0.2))
                ),
                "india_regulatory_score": max(
                    -1, min(1, base_sentiment * 0.3 + random.uniform(-0.2, 0.2))
                ),
                "btc_exchange_netflow": random.uniform(-5000, 5000),
            }
            sentiment_history.append(sentiment_data)

        return sentiment_history

    def _calculate_signal_accuracy(
        self, signals_history: List[Dict], prices: List[float]
    ) -> float:
        """Calculate the accuracy of signals based on price movement after signal."""
        if len(signals_history) < 2:
            return 0.0

        correct_signals = 0
        total_actionable_signals = 0

        for i, signal_data in enumerate(signals_history):
            if i >= len(prices) - 1:  # Can't check future price
                break

            if signal_data["signal"] in ["BUY", "SELL"]:
                total_actionable_signals += 1
                current_price = prices[i]
                future_price = prices[
                    min(i + 5, len(prices) - 1)
                ]  # Look 5 periods ahead
                price_change = future_price - current_price

                if signal_data["signal"] == "BUY" and price_change > 0:
                    correct_signals += 1
                elif signal_data["signal"] == "SELL" and price_change < 0:
                    correct_signals += 1

        return (
            correct_signals / total_actionable_signals
            if total_actionable_signals > 0
            else 0.0
        )
