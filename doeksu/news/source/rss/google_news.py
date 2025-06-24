import feedparser
import aiohttp
from typing import List, Optional
from urllib.parse import urlencode
from dataclasses import dataclass
from datetime import datetime
import time
from email.utils import parsedate_to_datetime
from googlenewsdecoder import gnewsdecoder
from doeksu.news.model import NewsArticle
from doeksu.news.source.registry import news_source
from doeksu.logging_config import logger


@dataclass
class GoogleNewsParam:
    """Parameters for Google News RSS sources."""
    language: str = "en"
    country: str = "US"

@dataclass
class GoogleNewsSearchParam:
    """Parameters for Google News search RSS sources."""
    search_keyword: str
    language: str = "en"
    country: str = "US"


# Google News topic IDs
GOOGLE_NEWS_TOPIC_IDS = {
    "world": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pKVGlnQVAB",
    "business": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pKVGlnQVAB",
    "technology": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pKVGlnQVAB",
    "entertainment": "CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5RU0FtVnVHZ0pKVGlnQVAB",
    "sports": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnVHZ0pKVGlnQVAB",
    "science": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtVnVHZ0pKVGlnQVAB",
    "health": "CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3QwTlRFU0FtVnVLQUFQAQ"
}


def get_google_news_rss_url(topic: str, param: GoogleNewsParam) -> str:
    topic_lower = topic.lower()
    
    if topic_lower not in GOOGLE_NEWS_TOPIC_IDS:
        available_topics = list(GOOGLE_NEWS_TOPIC_IDS.keys())
        raise ValueError(f"Invalid topic '{topic}'. Available topics: {available_topics}")
    
    base_url = "https://news.google.com/rss"
    topic_id = GOOGLE_NEWS_TOPIC_IDS[topic_lower]
    params = {
        "hl": f"{param.language}-{param.country}",
        "gl": param.country,
        "ceid": f"{param.country}:{param.language}"
    }
    return f"{base_url}/topics/{topic_id}?{urlencode(params)}"


def parse_published_date_to_timestamp(date_str: str) -> int:
    """Parse RSS published date string to unix timestamp."""
    if not date_str:
        return int(time.time())  # Current time as fallback
    
    try:
        # Try parsing RFC 2822 format (common in RSS)
        dt = parsedate_to_datetime(date_str)
        return int(dt.timestamp())
    except Exception:
        try:
            # Try ISO format
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except Exception:
            logger.warning(f"Could not parse date '{date_str}', using current time")
            return int(time.time())


def decode_google_news_url(google_url: str) -> Optional[str]:
    try:
        result = gnewsdecoder(google_url, interval=1)
        
        if result.get("status"):
            decoded_url = result["decoded_url"]
            return decoded_url
        else:
            logger.error(f"Failed to decode Google News URL: {google_url}, error: {result.get('message', 'Unknown error')}")
            return None
            
    except Exception as e:
        logger.error(f"Error decoding Google News URL {google_url}: {e}")
        return None


async def fetch_google_news_rss(url: str) -> List[NewsArticle]:
    """Helper function to fetch news from Google News RSS using feedparser and newspaper3k."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"HTTP {response.status} when fetching {url}")
                    return []
                
                rss_content = await response.text()
        
        feed = feedparser.parse(rss_content)
        
        if not feed.entries:
            logger.warning(f"No entries found in RSS feed for {url}")
            return []
        
        articles = []
        for entry in feed.entries:
            title = str(entry.get('title', 'Untitled'))
            google_redirect_url = str(entry.get('link', ''))
            source = str(entry.get('source'))
            published_at = parse_published_date_to_timestamp(str(entry.get('published', '')))
            article_url = decode_google_news_url(google_redirect_url)
            if article_url is None:
                logger.warning(f"Skipping entry '{title}' - failed to decode Google News URL")
                continue

            article = NewsArticle(
                title=title,
                url=article_url,
                published_at=published_at,
                source=source,
            )
            articles.append(article)
        
        logger.info(f"Successfully parsed {len(articles)} articles from {url}")
        return articles
        
    except Exception as e:
        logger.error(f"Error collecting from {url}: {e}")
        return []


# @news_source(
#     source_name="Google News Top Stories",
#     description="General top headlines from Google News with country and language localization",
#     param_type=GoogleNewsParam
# )
# async def google_news_top_stories(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
#     """Get general top news from Google News RSS."""
#     logger.info(f"Fetching Google News Top Stories from: {param}")
#     base_url = "https://news.google.com/rss"
#     params = {
#         "hl": f"{param.language}-{param.country}",
#         "gl": param.country,
#         "ceid": f"{param.country}:{param.language}"
#     }
#     url = f"{base_url}?{urlencode(params)}"
#     return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News World",
    description="World news from Google News RSS",
    param_type=GoogleNewsParam
)
async def google_news_world(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get world news from Google News RSS."""
    logger.info(f"Fetching Google News World from: {param}")
    url = get_google_news_rss_url("world", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Business",
    description="Business news from Google News RSS",
    param_type=GoogleNewsParam
)
async def google_news_business(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get business news from Google News RSS."""
    logger.info(f"Fetching Google News Business from: {param}")
    url = get_google_news_rss_url("business", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Technology",
    description="Technology news from Google News RSS",
    param_type=GoogleNewsParam
)
async def google_news_technology(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get technology news from Google News RSS."""
    logger.info(f"Fetching Google News Technology from: {param}")
    url = get_google_news_rss_url("technology", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Entertainment",
    description="Entertainment news from Google News RSS",
    param_type=GoogleNewsParam
)
async def google_news_entertainment(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get entertainment news from Google News RSS."""
    logger.info(f"Fetching Google News Entertainment from: {param}")
    url = get_google_news_rss_url("entertainment", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Sports",
    description="Sports news from Google News RSS",
    param_type=GoogleNewsParam
)
async def google_news_sports(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get sports news from Google News RSS."""
    logger.info(f"Fetching Google News Sports from: {param}")
    url = get_google_news_rss_url("sports", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Science",
    description="Science news from Google News RSS",
    param_type=GoogleNewsParam
)
async def google_news_science(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get science news from Google News RSS."""
    logger.info(f"Fetching Google News Science from: {param}")
    url = get_google_news_rss_url("science", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Health",
    description="Health news from Google News RSS",
    param_type=GoogleNewsParam
)
async def google_news_health(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get health news from Google News RSS."""
    logger.info(f"Fetching Google News Health from: {param}")
    url = get_google_news_rss_url("health", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Search",
    description="Custom keyword search from Google News RSS",
    param_type=GoogleNewsSearchParam
)
async def google_news_search(param: GoogleNewsSearchParam) -> List[NewsArticle]:
    """Get search-based news from Google News RSS."""
    logger.info(f"Fetching Google News Search from: {param.search_keyword}")
    base_url = "https://news.google.com/rss"
    params = {
        "q": param.search_keyword,
        "hl": f"{param.language}-{param.country}",
        "gl": param.country,
        "ceid": f"{param.country}:{param.language}"
    }
    url = f"{base_url}/search?{urlencode(params)}"
    return await fetch_google_news_rss(url)
