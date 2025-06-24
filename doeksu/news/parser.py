import asyncio
from typing import List, Optional
from newspaper import Article
from langchain.schema.language_model import BaseLanguageModel
from doeksu.news.model import NewsArticle
from doeksu.logging_config import logger
from pydantic import BaseModel, Field
from doeksu.config import CONFIG


class ArticleContentExtraction(BaseModel):
    summary: str = Field(description=f"A concise {CONFIG.ARTICLE_SUMMARY_MIN_WORD_COUNT}-{CONFIG.ARTICLE_SUMMARY_MAX_WORD_COUNT} words summary of the article")
    author: Optional[str] = Field(description="The author name if mentioned in the text, otherwise None")
    keywords: List[str] = Field(description=f"{CONFIG.ARTICLE_KEYWORDS_MIN_COUNT}-{CONFIG.ARTICLE_KEYWORDS_MAX_COUNT} relevant keywords/tags for the article")


class NewsArticleParser:

    def __init__(self, llm_model: BaseLanguageModel):
        self.llm_model = llm_model.with_structured_output(ArticleContentExtraction)
    
    async def parse_article(self, news_article: NewsArticle) -> NewsArticle:
        """
        Parse a news article by downloading its content and using LLM to extract additional info.
        
        Args:
            news_article: NewsArticle object with at least title and url
            
        Returns:
            NewsArticle with filled summary, author, keywords, and thumbnail_url, etc
        """
        try:
            article = Article(news_article.url)
            article.download()
            article.parse()
            
            article_text = article.text
            top_image = article.top_image
            
            if not article_text:
                raise ValueError(f"No text content found for article: {news_article.url}")
            
            article_content = await self._extract_article_content(
                title=news_article.title,
                text=article_text,
                source=news_article.source
            )
            
            news_article.summary = article_content.summary
            news_article.author = article_content.author
            news_article.keywords = article_content.keywords[:CONFIG.ARTICLE_KEYWORDS_MAX_COUNT]
            news_article.thumbnail_url = top_image if top_image else None
            
            return news_article
            
        except Exception as e:
            logger.error(f"Error parsing article {news_article.url}: {e}")
            return news_article
    
    async def _extract_article_content(self, title: str, text: str, source: str) -> ArticleContentExtraction:
        # Truncate text if too long (keep first 4000 characters to avoid token limits)
        truncated_text = text[:4000] if len(text) > 4000 else text
        
        extraction_prompt = f"""
Analyze the following news article and extract the requested information:

News Article:
- Title: {title}
- Source: {source}
- Content: {truncated_text}
"""
            
        response = await self.llm_model.ainvoke(extraction_prompt)
        
        if isinstance(response, ArticleContentExtraction):
            return response
        else:
            raise ValueError(f"Unexpected response type while extracting article content: {type(response)}")
