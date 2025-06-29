import asyncio
from typing import List, Tuple, Optional
from langchain.schema.language_model import BaseLanguageModel
from pydantic import BaseModel, Field

from doeksu.news.model import NewsArticle
from doeksu.logging_config import logger
from doeksu.agent.prompts import AIPrompt, SystemPrompt


class ArticleRelevanceScore(BaseModel):
    """Model for scoring article relevance to query."""
    article_url: str = Field(description="The URL of the article being scored")
    relevance_score: float = Field(
        description="Relevance score from 0.0 to 1.0, where 1.0 is most relevant",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(description="Brief explanation of why this score was assigned")


class RelevancyScorer:
    """
    Scorer interface for evaluating article relevance to query prompts.
    Uses LLM to provide intelligent relevance scoring with reasoning.
    """
    
    def __init__(self, llm_model: BaseLanguageModel, system_prompt: Optional[SystemPrompt] = None):
        """
        Initialize the relevancy scorer.
        
        Args:
            llm_model: Language model to use for scoring
            system_prompt: Optional system prompt to use for scoring
        """
        self.relevance_scorer = llm_model.with_structured_output(ArticleRelevanceScore)
        self.system_prompt = system_prompt or SystemPrompt()
    
    async def score_article(
        self, 
        article: NewsArticle, 
        query_prompt: str
    ) -> ArticleRelevanceScore:
        """
        Score a single's relevance to the query prompt.
        """
        if not article.is_hydrated:
            raise ValueError(f"Article must be hydrated before scoring: {article.url}")
        
        prompt = AIPrompt(self.system_prompt)
        prompt.add_task_prompt(f"""
Score the relevance of this news article to the given query prompt.

Query Prompt: {query_prompt}

Article Details:
- Title: {article.title}
- Summary: {article.summary}
- Keywords: {", ".join(article.keywords or [])}
- URL: {article.url}

Provide a relevance score from 0.0 to 1.0 where:
- 1.0 = Perfectly matches the query intent and topic
- 0.8-0.9 = Highly relevant with strong connection to query
- 0.6-0.7 = Moderately relevant with some connection
- 0.4-0.5 = Tangentially related
- 0.0-0.3 = Not relevant or off-topic

Consider:
1. Direct topic match
2. Keyword alignment
3. Content depth and quality
4. Recency and timeliness
5. Source credibility

Be precise and analytical in your scoring. Provide clear reasoning for your score.
""")
        
        result = await self.relevance_scorer.ainvoke(prompt.get_prompt())
        
        if isinstance(result, ArticleRelevanceScore):
            return result
        else:
            raise ValueError(f"Unexpected scoring response: {type(result)}")

    async def filter_by_relevance_score(
        self,
        articles: List[NewsArticle],
        query_prompt: str,
        min_score: float = 0.5
    ) -> List[Tuple[NewsArticle, ArticleRelevanceScore]]:
        """
        Score articles and filter by minimum relevance score.
        """
        scored_articles = [
            (article, await self.score_article(article, query_prompt))
            for article in articles
        ]
        scored_articles.sort(key=lambda x: x[1].relevance_score, reverse=True)
        
        relevant_articles = [
            (article, score) for article, score in scored_articles
            if score.relevance_score >= min_score
        ]
        
        return relevant_articles 