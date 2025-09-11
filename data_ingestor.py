from typing import Dict

"""
Data Ingestor Module

This module is responsible for fetching alternative and on-chain data
from various external APIs.
"""

def get_geopolitical_scores() -> Dict[str, float]:
    """
    Fetches and scores geopolitical news from sources like NewsAPI or GDELT.
    Scores range from -1.0 (very negative) to +1.0 (very positive).
    
    **This is a mock function. In a real implementation, this would involve API calls.**
    """
    # Mock data: Simulates neutral-to-positive news from Brazil
    return {
        "brazil_regulatory_score": 0.5,
        "india_regulatory_score": 0.1,
    }

def get_sentiment_scores() -> Dict[str, float]:
    """
    Fetches and scores sentiment from social media and news.
    
    **This is a mock function. In a real implementation, this would involve API calls.**
    """
    # Mock data: Simulates a positive statement from a major political figure
    return {
        "trump_sentiment_score": 0.9,
        "market_fear_greed_index": 72.0, # Represents "Greed"
    }

def get_onchain_data() -> Dict[str, float]:
    """
    Fetches key on-chain metrics from sources like Glassnode or CryptoQuant.
    
    **This is a mock function. In a real implementation, this would involve API calls.**
    """
    # Mock data: Simulates a net outflow of Bitcoin from exchanges (bullish)
    return {
        "btc_exchange_netflow": -2000.0,
    }

def fetch_all_alternative_data() -> Dict[str, float]:
    """Combines all external data sources into a single dictionary."""
    all_data = {}
    all_data.update(get_geopolitical_scores())
    all_data.update(get_sentiment_scores())
    all_data.update(get_onchain_data())
    
    return all_data
