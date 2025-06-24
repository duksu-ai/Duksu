from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


@dataclass
class NewsArticle:
    """Represents a single news article with full content extraction."""
    title: str
    url: str
    published_at: int  # Unix timestamp
    source: str
    thumbnail_url: Optional[str] = None
    keywords: Optional[List[str]] = None
    summary: Optional[str] = None
    author: Optional[str] = None


class NewsSourceType(Enum):
    """Types of news sources."""
    RSS = "rss"
    API = "api"
    WEB = "web"
