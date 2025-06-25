from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

from doeksu.news.model import NewsArticle


@dataclass
class Feed:
    """Curated news feed with a query prompt and a list of articles."""
    query_prompt: str
    feed_topic: str
    articles: List[NewsArticle] = field(default_factory=list)