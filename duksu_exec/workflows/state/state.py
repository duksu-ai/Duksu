import operator
from typing import Annotated, TypedDict, List, Dict, Any, Optional

from pydantic import BaseModel

from duksu.news.model import NewsArticle


class BaseState(TypedDict):
    error_message: Optional[str]


class CreateNewsFeedState(BaseState):
    """State for the news source selection workflow."""
    user_id: str
    query_prompt: str
    feed_id: Optional[int]  # ID of the created feed
    feed_topic: Optional[str]  # Topic/title for the feed


class NewsSearchExecution(BaseModel):
    source_name: str
    parameters: Dict[str, Any]
    reasoning: str


class ArticlesRetrievalState(BaseState):
    news_search_plan: NewsSearchExecution

class PopulateFeedState(BaseState):
    """State for the populate feed workflow."""
    feed_id: int
    feed_topic: str
    feed_query_prompt: str
    news_search_plans: List[NewsSearchExecution]
    articles_to_retrieve: Annotated[List[NewsArticle], operator.add]
    articles_retrieved: List[NewsArticle]
    articles_curated: List[NewsArticle]
