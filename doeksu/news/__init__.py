# Import core models
from .model import NewsArticle

from .source.registry import NewsSourceRegistry, NewsSource

# Import all news sources to trigger registration
from .source import *

from .parser import NewsArticleParser

__all__ = [
    "NewsArticle",
    "NewsSourceRegistry",
    "NewsSource",
    "NewsArticleParser",
] 