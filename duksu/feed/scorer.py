import asyncio
from dataclasses import dataclass
from typing import List, Tuple, Optional
from langchain.schema.language_model import BaseLanguageModel
from pydantic import BaseModel, Field

from duksu.news.model import NewsArticle
from duksu.agent.prompts import AIPrompt, SystemPrompt


class Score(BaseModel):
    score: float = Field(
        description="score based on criteria from 0.0 to 1.0, where 1.0 is most relevant",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(description="Brief explanation of why this score was assigned")


class ScorerResponse(BaseModel):
    scores: List[Score] = Field(description="List of score results for the articles")


class RelevanceScorer:
    """
    Scorer interface for evaluating article relevance to query prompts.
    """
    
    def __init__(self, llm_model: BaseLanguageModel, system_prompt: Optional[SystemPrompt] = None):
        self.relevance_scorer = llm_model.with_structured_output(ScorerResponse)
        self.system_prompt = system_prompt or SystemPrompt()
    
    def score_articles(
        self, 
        articles: List[NewsArticle], 
        query_prompt: str
    ) -> ScorerResponse:
        articles_content = ""
        for i, article in enumerate(articles, 1):
            articles_content += f"Article: {i}\n"
            if article.title: articles_content += f"Title: {article.title}\n"
            if article.source: articles_content += f"Source: {article.source}\n"
            if article.summary: articles_content += f"Summary: {article.summary}\n"
            if article.keywords: articles_content += f"Keywords: {', '.join(article.keywords)}\n"
            articles_content += "\n"

        prompt = AIPrompt(self.system_prompt)
        prompt.add_task_prompt(f"""
Score the relevance of these {len(articles)} news articles to the user's personalized news feed query.

The user has requested a curated news feed based on their interests and information needs. Their query represents what topics, themes, or types of news coverage they want to stay informed about.

User's News Feed Query: {query_prompt}

{articles_content}

For each article, provide a relevance score from 0.0 to 1.0, using the following crtieria to determine approximately one of these values:

- 1.0 = Perfectly relevant - Directly addresses the user's query with high-quality, engaging content
- 0.8 = Highly relevant - Strong connection to the query topic with substantial content
- 0.6 = Moderately relevant - Some connection to the query topic but may be tangential
- 0.3 = Minimally relevant - Weak connection to the query topic or low-quality content
- 0.0 = Not relevant - No meaningful connection to the query topic, or article is not sufficient to be included in the feed

Consider these factors when scoring:
1. Direct topic match - Does the article address the user's query topic?
2. User engagement potential - Attention-grabbing, interesting, or surprising content. Would this genuinely interest someone with this query?
3. Content depth and quality - Is this substantial, well-written content?
4. Source credibility - Is this from a reputable source?
5. Keyword alignment - How well do article keywords match the query intent?

Return result of EXACTLY {len(articles)} scores in the same order as the articles above. Each score should include clear reasoning explaining why that specific score was chosen.
""")
        
        result = self.relevance_scorer.invoke(prompt.get_prompt())
        
        if isinstance(result, ScorerResponse):
            if len(result.scores) != len(articles):
                raise ValueError(f"Expected {len(articles)} scores, but got {len(result.scores)}")
            return result
        else:
            raise ValueError(f"Unexpected scoring response: {type(result)}")