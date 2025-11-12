"""
Live API integration for alternative data sources
Fetches real-time sentiment, geopolitical events, and market psychology data
"""

import requests
import time
import logging
import os
from datetime import datetime
from typing import Dict

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveDataIngestor:
    def __init__(self):
        # API Keys from environment
        self.news_api_key = os.getenv("NEWS_API_KEY")

        # API endpoints
        self.fear_greed_url = "https://api.alternative.me/fng/"
        self.news_api_url = "https://newsapi.org/v2/everything"
        self.reddit_sentiment_url = "https://www.reddit.com/r/cryptocurrency/hot.json"

        # Cache to avoid rate limits
        self.cache = {}
        self.cache_duration = 300  # 5 minutes

    def fetch_fear_greed_index(self) -> Dict:
        """Fetch live Fear & Greed Index from Alternative.me API"""
        cache_key = "fear_greed"

        if self._is_cached(cache_key):
            return self.cache[cache_key]

        try:
            response = requests.get(self.fear_greed_url, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data and "data" in data and len(data["data"]) > 0:
                fng_data = data["data"][0]
                result = {
                    "score": float(fng_data["value"]),
                    "classification": fng_data["value_classification"],
                    "timestamp": datetime.fromtimestamp(int(fng_data["timestamp"])),
                }

                self._cache_data(cache_key, result)
                logger.info(f"Fear & Greed Index: {result['score']} ({result['classification']})")
                return result

        except Exception as e:
            logger.warning(f"Failed to fetch Fear & Greed Index: {e}")

        # Fallback to neutral
        return {"score": 50.0, "classification": "Neutral", "timestamp": datetime.now()}

    def fetch_crypto_news_sentiment(self) -> Dict:
        """Fetch crypto-related news and analyze sentiment"""
        cache_key = "news_sentiment"

        if self._is_cached(cache_key):
            return self.cache[cache_key]

        if not self.news_api_key:
            logger.warning("NEWS_API_KEY not configured, using fallback")
            return {"sentiment_score": 0.5, "article_count": 0, "timestamp": datetime.now()}

        try:
            # Fetch from NewsAPI
            params = {
                "q": "cryptocurrency OR bitcoin OR ethereum OR crypto",
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
                "apiKey": self.news_api_key,
            }

            response = requests.get(self.news_api_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            articles = data.get("articles", [])

            sentiment_scores = []
            for article in articles[:10]:  # Analyze top 10 articles
                title = article.get("title", "")
                description = article.get("description", "")
                text = f"{title} {description}"

                score = self._analyze_text_sentiment(text)
                sentiment_scores.append(score)

            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.5

            result = {"sentiment_score": avg_sentiment, "article_count": len(articles), "timestamp": datetime.now()}

            self._cache_data(cache_key, result)
            logger.info(f"News Sentiment: {avg_sentiment:.2f} ({len(articles)} articles)")
            return result

        except Exception as e:
            logger.warning(f"Failed to fetch news sentiment: {e}")

        return {"sentiment_score": 0.5, "article_count": 0, "timestamp": datetime.now()}

    def fetch_social_sentiment(self) -> Dict:
        """Fetch social media sentiment from Reddit"""
        cache_key = "social_sentiment"

        if self._is_cached(cache_key):
            return self.cache[cache_key]

        try:
            # Fetch Reddit crypto discussions
            headers = {"User-Agent": "BensonBot/1.0"}
            response = requests.get(self.reddit_sentiment_url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            posts = data.get("data", {}).get("children", [])

            sentiment_scores = []
            for post in posts[:20]:  # Analyze top 20 posts
                post_data = post.get("data", {})
                title = post_data.get("title", "")
                selftext = post_data.get("selftext", "")
                text = f"{title} {selftext}"

                score = self._analyze_text_sentiment(text)
                # Weight by upvotes/score
                upvotes = post_data.get("ups", 1)
                weighted_score = score * min(upvotes / 100, 2.0)  # Cap weight at 2x
                sentiment_scores.append(weighted_score)

            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.5

            result = {"social_sentiment": avg_sentiment, "post_count": len(posts), "timestamp": datetime.now()}

            self._cache_data(cache_key, result)
            logger.info(f"Social Sentiment: {avg_sentiment:.2f} ({len(posts)} posts)")
            return result

        except Exception as e:
            logger.warning(f"Failed to fetch social sentiment: {e}")

        return {"social_sentiment": 0.5, "post_count": 0, "timestamp": datetime.now()}

    def fetch_geopolitical_events(self) -> Dict:
        """Fetch geopolitical events that might impact crypto markets"""
        cache_key = "geopolitical"

        if self._is_cached(cache_key):
            return self.cache[cache_key]

        if not self.news_api_key:
            logger.warning("NEWS_API_KEY not configured for geopolitical data, using fallback")
            return {"geopolitical_score": 0.5, "events_count": 0, "timestamp": datetime.now()}

        try:
            # Fetch geopolitical news
            params = {
                "q": 'regulation OR ban OR government OR policy OR sanctions OR inflation OR "central bank"',
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 15,
                "apiKey": self.news_api_key,
            }

            response = requests.get(self.news_api_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            articles = data.get("articles", [])

            # Score geopolitical impact
            impact_scores = []
            for article in articles:
                title = article.get("title", "").lower()
                description = article.get("description", "").lower()
                text = f"{title} {description}"

                # Keywords that indicate crypto-relevant geopolitical events
                positive_keywords = ["adoption", "approval", "legal", "framework", "support"]
                negative_keywords = ["ban", "regulation", "crackdown", "sanctions", "restrict"]

                positive_score = sum(1 for keyword in positive_keywords if keyword in text)
                negative_score = sum(1 for keyword in negative_keywords if keyword in text)

                # Convert to 0-1 scale (0.5 = neutral)
                if positive_score > negative_score:
                    score = 0.5 + (positive_score * 0.1)
                elif negative_score > positive_score:
                    score = 0.5 - (negative_score * 0.1)
                else:
                    score = 0.5

                impact_scores.append(max(0, min(1, score)))

            avg_impact = sum(impact_scores) / len(impact_scores) if impact_scores else 0.5

            result = {"geopolitical_score": avg_impact, "events_count": len(articles), "timestamp": datetime.now()}

            self._cache_data(cache_key, result)
            logger.info(f"Geopolitical Score: {avg_impact:.2f} ({len(articles)} events)")
            return result

        except Exception as e:
            logger.warning(f"Failed to fetch geopolitical data: {e}")

        return {"geopolitical_score": 0.5, "events_count": 0, "timestamp": datetime.now()}

    def _analyze_text_sentiment(self, text: str) -> float:
        """Simple sentiment analysis"""
        if not text:
            return 0.5

        # Simple keyword-based sentiment
        positive_words = ["bullish", "positive", "growth", "gains", "up", "rise", "surge", "moon", "pump", "rally"]
        negative_words = ["bearish", "negative", "crash", "down", "fall", "dump", "fear", "sell", "loss", "drop"]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return 0.5 + min(0.3, positive_count * 0.1)
        elif negative_count > positive_count:
            return 0.5 - min(0.3, negative_count * 0.1)
        else:
            return 0.5

    def _is_cached(self, key: str) -> bool:
        """Check if data is cached and still valid"""
        if key not in self.cache:
            return False

        cache_time = self.cache[key].get("_cache_time")
        if not cache_time:
            return False

        return (datetime.now() - cache_time).seconds < self.cache_duration

    def _cache_data(self, key: str, data: Dict):
        """Cache data with timestamp"""
        data["_cache_time"] = datetime.now()
        self.cache[key] = data


# Global instance
live_ingestor = LiveDataIngestor()


# Legacy function compatibility
def fetch_geopolitical_data():
    """Legacy compatibility function"""
    result = live_ingestor.fetch_geopolitical_events()
    return result["geopolitical_score"]


def fetch_social_sentiment():
    """Legacy compatibility function"""
    result = live_ingestor.fetch_social_sentiment()
    return result["social_sentiment"]


def fetch_fear_greed_index():
    """Legacy compatibility function"""
    result = live_ingestor.fetch_fear_greed_index()
    return result["score"] / 100.0


def fetch_all_alternative_data():
    """Fetch all alternative data sources and combine into comprehensive sentiment"""
    logger.info("Fetching live alternative data...")

    # Fetch all data sources
    fear_greed = live_ingestor.fetch_fear_greed_index()
    news_sentiment = live_ingestor.fetch_crypto_news_sentiment()
    social_sentiment = live_ingestor.fetch_social_sentiment()
    geopolitical = live_ingestor.fetch_geopolitical_events()

    # Normalize and combine scores
    fear_greed_normalized = fear_greed["score"] / 100.0  # Convert 0-100 to 0-1

    # Weighted combination
    composite_score = (
        geopolitical["geopolitical_score"] * 0.2
        + social_sentiment["social_sentiment"] * 0.3
        + fear_greed_normalized * 0.3
        + news_sentiment["sentiment_score"] * 0.2
    )

    result = {
        "geopolitical": geopolitical["geopolitical_score"],
        "social_sentiment": social_sentiment["social_sentiment"],
        "fear_greed": fear_greed_normalized,
        "news_sentiment": news_sentiment["sentiment_score"],
        "composite": composite_score,
        "timestamp": time.time(),
        "details": {
            "fear_greed_raw": fear_greed["score"],
            "fear_greed_class": fear_greed["classification"],
            "news_articles": news_sentiment["article_count"],
            "social_posts": social_sentiment["post_count"],
            "geo_events": geopolitical["events_count"],
        },
    }

    logger.info(
        f"Live Sentiment - Composite: {composite_score:.2f} | "
        f"F&G: {fear_greed_normalized:.2f} ({fear_greed['classification']}) | "
        f"News: {news_sentiment['sentiment_score']:.2f} | "
        f"Social: {social_sentiment['social_sentiment']:.2f} | "
        f"Geo: {geopolitical['geopolitical_score']:.2f}"
    )

    return result
