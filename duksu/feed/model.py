from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

from duksu.news.model import NewsArticle


@dataclass
class NewsCurationItem:
    """A feed item containing an article with its metadata and scores."""
    item: NewsArticle
    scores: Dict[str, Any] = field(default_factory=dict)  # For now contains relevance score


@dataclass
class NewsCuration:
    """Curated news feed with a query prompt and a list of scored items."""
    query_prompt: str
    feed_name: str
    items: List[NewsCurationItem] = field(default_factory=list)