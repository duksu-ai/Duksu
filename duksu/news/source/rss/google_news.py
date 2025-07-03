import feedparser
import aiohttp
from typing import List, Optional
from urllib.parse import urlencode
from googlenewsdecoder import gnewsdecoder
from duksu.news.model import NewsArticle
from duksu.news.source.registry import news_source
from duksu.logging_config import logger
from pydantic import BaseModel, Field

from duksu.utils.time import convert_date_str_to_timestamp


class GoogleNewsParam(BaseModel):
    """Parameters for Google News RSS sources."""
    language: str = Field(default="en", description="Language code for news")
    country: str = Field(default="US", description="Country code for news")


class GoogleNewsSearchParam(BaseModel):
    """Parameters for Google News search RSS sources."""
    search_keyword: str = Field(description="Search keyword for news articles")
    language: str = Field(default="en", description="Language code for news (e.g., 'en', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'zh')")
    country: str = Field(default="US", description="Country code for news (e.g., 'US', 'GB', 'FR', 'DE', 'IT', 'JP', 'KR', 'CN')")


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


def clean_article_title(title: str) -> str:
    """Remove news vendor name from article title (the part after the last dash)."""
    if not title:
        return title
    
    # Find the last occurrence of " - " and remove everything after it
    # This handles cases like "Title - Vendor Name" -> "Title"
    last_dash_index = title.rfind(" - ")
    if last_dash_index != -1:
        cleaned_title = title[:last_dash_index].strip()
        # Only return the cleaned title if it's not empty
        if cleaned_title:
            return cleaned_title
    
    return title


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
            source = getattr(entry.get('source', ''), 'title', str(entry.get('source', '')))

            published_at = convert_date_str_to_timestamp(str(entry.get('published', '')))
            
            article_url = decode_google_news_url(google_redirect_url)
            if article_url is None:
                logger.warning(f"Skipping entry '{title}' - failed to decode Google News URL")
                continue

            article = NewsArticle(
                title=clean_article_title(title),
                url=article_url,
                published_at=published_at,
                source=source,
            )
            articles.append(article)
        
        logger.info(f"Successfully fetched {len(articles)} articles from news source url: {url}")
        return articles
        
    except Exception as e:
        logger.error(f"Error collecting from {url}: {e}")
        return []


@news_source(
    source_name="Google News Top Stories",
    description="General top headlines from Google News with country and language localization",
    param_model=GoogleNewsParam
)
async def google_news_top_stories(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get general top news from Google News RSS."""
    logger.info(f"Fetching Google News Top Stories from: {param}")
    base_url = "https://news.google.com/rss"
    params = {
        "hl": f"{param.language}-{param.country}",
        "gl": param.country,
        "ceid": f"{param.country}:{param.language}"
    }
    url = f"{base_url}?{urlencode(params)}"
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News World",
    description="Worldwide news from Google News with optional language and country customization",
    param_model=GoogleNewsParam
)
async def google_news_world(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get world news from Google News RSS."""
    url = get_google_news_rss_url("world", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Business",
    description="Business news from Google News with optional language and country customization",
    param_model=GoogleNewsParam
)
async def google_news_business(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get business news from Google News RSS."""
    url = get_google_news_rss_url("business", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Technology",
    description="Technology news from Google News with optional language and country customization",
    param_model=GoogleNewsParam
)
async def google_news_technology(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get technology news from Google News RSS."""
    url = get_google_news_rss_url("technology", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Entertainment",
    description="Entertainment news from Google News with optional language and country customization",
    param_model=GoogleNewsParam
)
async def google_news_entertainment(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get entertainment news from Google News RSS."""
    url = get_google_news_rss_url("entertainment", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Sports",
    description="Sports news from Google News with optional language and country customization",
    param_model=GoogleNewsParam
)
async def google_news_sports(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get sports news from Google News RSS."""
    url = get_google_news_rss_url("sports", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Science",
    description="Science news from Google News with optional language and country customization",
    param_model=GoogleNewsParam
)
async def google_news_science(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get science news from Google News RSS."""
    url = get_google_news_rss_url("science", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Health",
    description="Health news from Google News with optional language and country customization",
    param_model=GoogleNewsParam
)
async def google_news_health(param: GoogleNewsParam = GoogleNewsParam()) -> List[NewsArticle]:
    """Get health news from Google News RSS."""
    url = get_google_news_rss_url("health", param)
    return await fetch_google_news_rss(url)


@news_source(
    source_name="Google News Search",
    description="Custom keyword search from Google News, useful to answer if user query is specific and not fully covered by other general sources",
    param_model=GoogleNewsSearchParam
)
async def google_news_search(param: GoogleNewsSearchParam) -> List[NewsArticle]:
    """Get search-based news from Google News RSS using explicit parameter model."""
    base_url = "https://news.google.com/rss"
    params = {
        "q": param.search_keyword,
        "hl": f"{param.language}-{param.country}",
        "gl": param.country,
        "ceid": f"{param.country}:{param.language}"
    }
    url = f"{base_url}/search?{urlencode(params)}"
    return await fetch_google_news_rss(url)
