"""News fetcher module to collect articles from RSS feeds."""

import feedparser
import re
from datetime import datetime, timedelta
from typing import List, Dict
import logging

from config import RSS_FEEDS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# STRICT 24-HOUR HARD FILTER - Prevents posting outdated news
# ============================================================
STRICT_24H_FILTER = True  # Set to False to disable (NOT recommended)
STALE_YEAR_PATTERNS = [r'\b2024\b', r'\b2023\b', r'\b2022\b']  # Years to reject


def filter_stale_articles(articles: List[Dict], max_age_hours: int = 24) -> List[Dict]:
    """
    STALE DATA FIREWALL: Remove any articles older than max_age_hours.

    This is a critical safety filter to prevent posting outdated news.
    The bot previously fetched 2024 news causing errors.

    Args:
        articles: List of article dictionaries with 'published' datetime
        max_age_hours: Maximum age in hours (default: 24)

    Returns:
        Filtered list containing only fresh articles
    """
    if not STRICT_24H_FILTER:
        logger.warning("⚠️ STRICT_24H_FILTER is DISABLED - stale news may leak through!")
        return articles

    now = datetime.now()
    cutoff = now - timedelta(hours=max_age_hours)
    fresh_articles = []
    rejected_count = 0

    for article in articles:
        published = article.get('published')
        title = article.get('title', '')
        summary = article.get('summary', '')
        text_to_check = f"{title} {summary}"

        # Check 1: Is the article older than 24 hours?
        if published and published < cutoff:
            age_hours = (now - published).total_seconds() / 3600
            logger.debug(f"REJECTED (age={age_hours:.1f}h > 24h): {title[:50]}...")
            rejected_count += 1
            continue

        # Check 2: Does the text contain stale year references?
        stale_year_found = False
        for pattern in STALE_YEAR_PATTERNS:
            if re.search(pattern, text_to_check):
                logger.debug(f"REJECTED (stale year pattern '{pattern}'): {title[:50]}...")
                stale_year_found = True
                rejected_count += 1
                break

        if stale_year_found:
            continue

        # Article passed all filters
        fresh_articles.append(article)

    logger.info(f"🛡️ STALE FILTER: {len(fresh_articles)} fresh / {rejected_count} rejected (24h cutoff: {cutoff.strftime('%Y-%m-%d %H:%M')})")

    if len(fresh_articles) == 0:
        logger.warning("⚠️ ALL ARTICLES FILTERED OUT - No fresh news available within 24 hours!")

    return fresh_articles


class NewsFetcher:
    def __init__(self, feeds: List[str] = None):
        self.feeds = feeds or RSS_FEEDS
        self._articles_cache: Dict[int, Dict] = {}  # Cache for full article lookup

    def fetch_recent_news(self, hours: int = 8, limit: int = 50) -> List[Dict]:
        """
        Fetch news from all RSS feeds from the last N hours.

        Args:
            hours: How many hours back to fetch news
            limit: Maximum number of articles to return

        Returns:
            List of news articles with id, title, link, source, published date
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        all_articles = []
        self._articles_cache = {}  # Clear cache

        for feed_url in self.feeds:
            try:
                logger.info(f"Fetching from: {feed_url}")
                feed = feedparser.parse(feed_url)

                for entry in feed.entries:
                    # Parse published date
                    published = self._parse_date(entry)

                    # Only include recent articles
                    if published and published > cutoff_time:
                        article = {
                            "title": entry.get("title", "No title"),
                            "link": entry.get("link", ""),
                            "source": feed.feed.get("title", feed_url),
                            "published": published,
                            "summary": entry.get("summary", "")[:500]  # Limit summary length
                        }
                        all_articles.append(article)

            except Exception as e:
                logger.error(f"Error fetching {feed_url}: {e}")
                continue

        # Sort by published date (newest first)
        all_articles.sort(key=lambda x: x["published"], reverse=True)

        # ============================================================
        # CRITICAL: Apply strict 24-hour filter AFTER initial fetch
        # This ensures no stale data leaks through regardless of
        # the 'hours' parameter passed to this method.
        # ============================================================
        all_articles = filter_stale_articles(all_articles, max_age_hours=24)

        # Limit and assign IDs
        all_articles = all_articles[:limit]
        for i, article in enumerate(all_articles):
            article["id"] = i
            self._articles_cache[i] = article

        logger.info(f"Fetched {len(all_articles)} recent articles (after 24h filter)")
        return all_articles

    def get_all_headlines(self, hours: int = 8, limit: int = 50) -> List[Dict]:
        """
        Get simplified headline list for AI curation.

        Returns:
            List of {id, title, source} for AI to select from
        """
        articles = self.fetch_recent_news(hours=hours, limit=limit)
        headlines = [
            {"id": a["id"], "title": a["title"], "source": a["source"]}
            for a in articles
        ]
        return headlines

    def get_articles_by_ids(self, ids: List[int]) -> List[Dict]:
        """
        Get full article details for selected IDs.

        Args:
            ids: List of article IDs selected by AI

        Returns:
            List of full article dictionaries
        """
        articles = []
        for article_id in ids:
            if article_id in self._articles_cache:
                articles.append(self._articles_cache[article_id])
            else:
                logger.warning(f"Article ID {article_id} not found in cache")
        return articles
    
    def _parse_date(self, entry) -> datetime:
        """Parse the published date from an RSS entry."""
        # Try different date fields
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except:
                pass

        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6])
            except:
                pass

        # If no date found, use current time
        return datetime.now()
