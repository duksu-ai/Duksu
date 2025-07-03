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
    is_hydrated: bool = False # Whether the article has been hydrated with full content by the parser
    raw_html: Optional[str] = None
    content: Optional[str] = None
    thumbnail_url: Optional[str] = None
    summary: Optional[str] = None
    keywords: Optional[List[str]] = None
    author: Optional[str] = None


class NewsSourceType(Enum):
    """Types of news sources."""
    RSS = "rss"
    API = "api"
    WEB = "web"
