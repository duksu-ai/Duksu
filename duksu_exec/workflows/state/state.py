import operator
from typing import Annotated, TypedDict, List, Optional

from duksu.news.model import NewsArticle
from duksu.news.source.registry import NewsSearchPlan


class BaseState(TypedDict):
    error_message: Optional[str]


class CreateNewsFeedState(BaseState):
    """State for the news source selection workflow."""
    user_id: str
    query_prompt: str
    feed_id: Optional[int]  # ID of the created feed


class PopulateFeedState(BaseState):
    """State for the populate feed workflow."""
    feed_id: int
    feed_query_prompt: str
    news_search_plans: List[NewsSearchPlan]
    articles_retrieved: Annotated[List[NewsArticle], operator.add]
    articles_curated: List[NewsArticle]