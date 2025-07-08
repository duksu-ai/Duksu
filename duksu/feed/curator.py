import asyncio
from typing import List, Optional, Dict, Any, Tuple
from langchain.schema.language_model import BaseLanguageModel
from pydantic import BaseModel, Field

from duksu.news.model import NewsArticle
from duksu.feed.model import NewsCuration, NewsCurationItem
from duksu.feed.scorer import RelevancyScorer
from duksu.logging_config import create_logger
from duksu.agent.prompts import AIPrompt, SystemPrompt


class FeedTopicGeneration(BaseModel):
    feed_name: str = Field(
        description="A concise, one-sentence topic name that represents the feed based on the query prompt"
    )


class CurationResult(BaseModel):
    selected_articles: List[str] = Field(description="URLs of articles selected for the feed")
    feed_name: str = Field(description="Generated topic name for the feed")
    curation_summary: str = Field(description="Summary of the curation process and rationale")


class FeedCurator:
    """
    News article curator for intelligent article selection.
    """
    
    def __init__(self, llm: BaseLanguageModel, system_prompt: Optional[SystemPrompt] = None):
        self.llm = llm
        self.topic_generator = llm.with_structured_output(FeedTopicGeneration)
        self.curator = llm.with_structured_output(CurationResult)
        self.system_prompt = system_prompt or SystemPrompt()
        self.logger = create_logger("FeedCurator")
        
        # Initialize the Scorers
        self.relevancy_scorer = RelevancyScorer(llm, system_prompt)

    async def generate_feed_name(self, query_prompt: str) -> str:
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
                return result.feed_name
            else:
                raise ValueError(f"Unexpected topic generation response: {type(result)}")
                
        except Exception as e:
            self.logger.error(f"Error generating feed topic: {e}")
            # Fallback to a simple topic generation
            return f"News Feed: {query_prompt[:50]}..."
    
    async def curate_news_feed(
        self,
        feed_name: str,
        query_prompt: str,
        articles: List[NewsArticle],
        min_relevance_score: float,
        max_articles_per_batch: Optional[int] = None,        
    ) -> NewsCuration:
        """
        Curate a news feed from a list of articles based on a query prompt.
        """
        assert query_prompt.strip() != ""

        self.logger.info(f"Starting news curation job; query_prompt: \"{query_prompt[:100]}\"; considering {len(articles)} articles; articles per batch: {max_articles_per_batch}")
        
        try:
            relevant_articles = []
            articles_batches = [articles] if max_articles_per_batch is None else [articles[i:i + max_articles_per_batch] for i in range(0, len(articles), max_articles_per_batch)]

            count = 0
            for batch in articles_batches:
                count += 1
                self.logger.debug(f"Scoring batch ({count}/{len(articles_batches)}) of {len(batch)} articles")

                relevant_articles_in_batch = await self.relevancy_scorer.filter_by_relevance_score(
                    batch, query_prompt, min_relevance_score
                )
                self.logger.debug(f"Found {len(relevant_articles_in_batch)} relevant articles in batch")

                relevant_articles.extend(relevant_articles_in_batch)
            
            if not relevant_articles:
                self.logger.warning("No articles met the minimum relevance criteria")
                return NewsCuration(
                    query_prompt=query_prompt,
                    feed_name=feed_name,
                    items=[]
                )

            # Sort articles by relevance score in descending order
            relevant_articles.sort(key=lambda x: x[1].relevance_score, reverse=True)
            
            curation_items = []
            for article, relevance_score in relevant_articles:
                curation_items.append(NewsCurationItem(
                    item=article,
                    scores={
                        "relevance": {
                            "score": relevance_score.relevance_score,
                            "reasoning": relevance_score.reasoning
                        }
                    }
                ))
            
            return NewsCuration(
                query_prompt=query_prompt,
                feed_name=feed_name,
                items=curation_items
            )
            
        except Exception as e:
            self.logger.error(f"Error during curation: {e}")
            raise