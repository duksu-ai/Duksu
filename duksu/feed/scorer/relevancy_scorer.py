import asyncio
from typing import List, Tuple, Optional
from langchain.schema.language_model import BaseLanguageModel
from pydantic import BaseModel, Field

from duksu.news.model import NewsArticle
from duksu.agent.prompts import AIPrompt, SystemPrompt


class RelevanceScore(BaseModel):
    """Model for scoring item relevance to query."""
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
        self.relevance_scorer = llm_model.with_structured_output(RelevanceScore)
        self.system_prompt = system_prompt or SystemPrompt()
    
    async def score_article(
        self, 
        article: NewsArticle, 
        query_prompt: str
    ) -> RelevanceScore:
        """
        Score a single's relevance to the query prompt.
        """
        prompt = AIPrompt(self.system_prompt)
        prompt.add_task_prompt(f"""
Score the relevance of this news article to the given query prompt.

User Query Prompt: I want to know about {query_prompt}

Article Details:
- Title: {article.title}
- Summary: {article.summary}
- Keywords: {", ".join(article.keywords or [])}
- URL: {article.url}

Provide a relevance score from 0.0 to 1.0 using this two-step approach:

STEP 1 - Base Relevancy (determines tier):
- 0.8 = Highly relevant with strong connection to query topic
- 0.6 = Moderately relevant with some connection to query topic  
- 0.4 = Tangentially related to query topic
- 0.0-0.3 = Not relevant or off-topic

Consider for base relevancy:
1. Direct topic match - Does the article address the query topic?
2. Content depth and quality - Is this substantial, well-written content?
3. Keyword alignment - How well do article keywords match query intent?
4. Source credibility - Is this from a reputable source?

STEP 2 - User Interest Boost:
If the article would genuinely engage and interest someone asking this query, add +0.1 to the base score:
- 0.8 → 0.9 or 1.0 (highly relevant + engaging)
- 0.6 → 0.7 (moderately relevant + engaging)
- 0.4 → 0.5 (tangentially relevant + engaging)

Consider for user interest boost:
- Uniqueness of insights, surprising angles, practical implications, compelling narratives
- Would this article be genuinely fascinating vs dry/routine for someone with this query?

Provide clear reasoning that explains both the base relevancy tier and whether the user interest boost applies.
""")
        
        result = await self.relevance_scorer.ainvoke(prompt.get_prompt())
        
        if isinstance(result, RelevanceScore):
            return result
        else:
            raise ValueError(f"Unexpected scoring response: {type(result)}")

    async def filter_by_relevance_score(
        self,
        articles: List[NewsArticle],
        query_prompt: str,
        min_score: float = 0.5
    ) -> List[Tuple[NewsArticle, RelevanceScore]]:
        """
        Score articles and filter by minimum relevance score.
        """
        scored_articles = [
            (article, await self.score_article(article, query_prompt))
            for article in articles
        ]
        
        relevant_articles = [
            (article, score) for article, score in scored_articles
            if score.relevance_score >= min_score
        ]
        
        return relevant_articles 