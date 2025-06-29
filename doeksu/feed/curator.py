import asyncio
from typing import List, Optional, Dict, Any, Tuple
from langchain.schema.language_model import BaseLanguageModel
from pydantic import BaseModel, Field

from doeksu.news.model import NewsArticle
from doeksu.feed.model import Feed, FeedItem, RelevanceScore
from doeksu.feed.scorer import RelevancyScorer, ArticleRelevanceScore
from doeksu.logging_config import logger
from doeksu.agent.prompts import AIPrompt, SystemPrompt


class FeedTopicGeneration(BaseModel):
    feed_topic: str = Field(
        description="A concise, one-sentence topic name that represents the feed based on the query prompt"
    )


class CurationResult(BaseModel):
    selected_articles: List[str] = Field(description="URLs of articles selected for the feed")
    feed_topic: str = Field(description="Generated topic name for the feed")
    curation_summary: str = Field(description="Summary of the curation process and rationale")


class FeedCurator:
    """
    News article curator for intelligent article selection.
    """
    
    def __init__(self, llm_model: BaseLanguageModel, system_prompt: Optional[SystemPrompt] = None):
        self.llm_model = llm_model
        self.topic_generator = llm_model.with_structured_output(FeedTopicGeneration)
        self.curator = llm_model.with_structured_output(CurationResult)
        self.system_prompt = system_prompt or SystemPrompt()
        
        # Initialize the Scorers
        self.relevancy_scorer = RelevancyScorer(llm_model, system_prompt)

    async def _generate_feed_topic(self, query_prompt: str) -> str:
        """Generate a concise feed topic from the query prompt."""
        try:
            prompt = AIPrompt(self.system_prompt)
            prompt.add_task_prompt(f"""
Generate a concise, one-sentence topic name for a news feed based on the following query prompt.
The topic should be descriptive, professional, and capture the essence of what the user is looking for.

Query Prompt: {query_prompt}

Examples:
- Query: "What are recent developments in AI and machine learning?" 
  Topic: "Recent AI and Machine Learning Developments"
- Query: "Show me news about climate change impacts on agriculture in developing countries"
  Topic: "Climate Change Impact on Agriculture in Developing Nations"
""")
            
            result = await self.topic_generator.ainvoke(prompt.get_prompt())
            
            if isinstance(result, FeedTopicGeneration):
                return result.feed_topic
            else:
                raise ValueError(f"Unexpected topic generation response: {type(result)}")
                
        except Exception as e:
            logger.error(f"Error generating feed topic: {e}")
            # Fallback to a simple topic generation
            return f"News Feed: {query_prompt[:50]}..."
    
    async def curate_news_feed(
        self,
        articles: List[NewsArticle],
        query_prompt: str,
        max_articles: Optional[int] = None,
        min_relevance_score: float = 0.5,
    ) -> Feed:
        """
        Curate a news feed from a list of articles based on a query prompt.
        """
        assert query_prompt.strip() != ""

        logger.info(f"Starting news curation job; query_prompt: {query_prompt[:100]}; articles: {[article.title[:30] + '...' if len(article.title) > 30 else article.title for article in articles]}")
        
        try:
            feed_topic = await self._generate_feed_topic(query_prompt)
            relevant_articles = await self.relevancy_scorer.filter_by_relevance_score(
                articles, query_prompt, min_relevance_score
            )
            
            if not relevant_articles:
                logger.warning("No articles met the minimum relevance criteria")
                return Feed(
                    query_prompt=query_prompt,
                    feed_topic=feed_topic,
                    items=[]
                )
            
            # Create FeedItems with scores
            selected_items = []
            articles_to_process = relevant_articles if max_articles is None else relevant_articles[:max_articles]
            
            for article, relevance_score in articles_to_process:
                feed_item = FeedItem(
                    item=article,
                    scores={
                        "relevance": RelevanceScore(
                            score=relevance_score.relevance_score,
                            reasoning=relevance_score.reasoning
                        )
                    }
                )
                selected_items.append(feed_item)
            
            return Feed(
                query_prompt=query_prompt,
                feed_topic=feed_topic,
                items=selected_items
            )
            
        except Exception as e:
            logger.error(f"Error during curation: {e}")
            raise