import asyncio
from typing import List, Optional
from newspaper import Article
from langchain.schema.language_model import BaseLanguageModel
from doeksu.news.model import NewsArticle
from doeksu.logging_config import logger
from pydantic import BaseModel, Field
from doeksu.config import CONFIG


ARTICLE_HTML_CHUNK_SIZE = 100000
ARTICLE_CONTENT_MAX_LENGTH = 100000


class ArticleContentExtraction(BaseModel):
    summary: str = Field(description=f"A concise {CONFIG.ARTICLE_SUMMARY_MIN_WORD_COUNT}-{CONFIG.ARTICLE_SUMMARY_MAX_WORD_COUNT} words summary of the article")
    author: Optional[str] = Field(description="The author name if mentioned in the text, otherwise None")
    keywords: List[str] = Field(description=f"{CONFIG.ARTICLE_KEYWORDS_MIN_COUNT}-{CONFIG.ARTICLE_KEYWORDS_MAX_COUNT} relevant keywords/tags for the article")


class ArticleCompression(BaseModel):
    compressed_text: str = Field(description="The compressed version of the text that retains key information while being shorter")


class NewsArticleParser:

    def __init__(self, llm_model: BaseLanguageModel):
        self.llm_model = llm_model.with_structured_output(ArticleContentExtraction)
        self.compression_model = llm_model.with_structured_output(ArticleCompression)
        self.html_extraction_model = llm_model
    
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

            article_text = await self._extract_text_from_html(article.html)
            if not article_text:
                raise ValueError(f"No text content found for article: {news_article.url}")

            news_article.raw_html = article.html
            news_article.content = article_text
   
            article_content = await self._extract_article_content(
                title=news_article.title,
                text=article_text,
                source=news_article.source
            )

            news_article.summary = article_content.summary
            news_article.author = article_content.author if article_content.author and article_content.author != "None" else None
            news_article.keywords = article_content.keywords[:CONFIG.ARTICLE_KEYWORDS_MAX_COUNT]
            news_article.thumbnail_url = article.top_image if article.top_image else None

            news_article.is_hydrated = True
            
            return news_article
            
        except Exception as e:
            logger.error(f"Error parsing article {news_article.url}: {e}")
            raise e
    
    async def _extract_text_from_html(self, html: str) -> str:
        """Extract article text from HTML by processing it in chunks using LLM."""
        if not html:
            return ""
        
        html_chunk_size = ARTICLE_HTML_CHUNK_SIZE
        
        if len(html) <= html_chunk_size:
            return await self._extract_text_from_html_chunk(html)
        
        chunks = []
        for i in range(0, len(html), html_chunk_size):
            chunk = html[i:i + html_chunk_size]
            chunks.append(chunk)
        
        extracted_texts = []
        for i, chunk in enumerate(chunks):
            extracted_text = await self._extract_text_from_html_chunk(chunk)
            if extracted_text.strip():
                extracted_texts.append(extracted_text)
        
        combined_text = "\n\n".join(extracted_texts)
        logger.info(f"HTML extraction complete: {len(html)} -> {len(combined_text)} characters")
        
        return combined_text
    
    async def _extract_text_from_html_chunk(self, html_chunk: str) -> str:
        """Extract article text from a single HTML chunk."""
        extraction_prompt = f"""
Extract the main article text content from the following HTML. 
Focus on:
1. The main article body text content
2. Don't alter the original text, just extract the main article text content and focus on removing the non-article content such as HTML
3. Article title and subtitle if present
4. Author byline if present

Exclude:
1. Navigation menus and headers
2. Advertisements and promotional content
3. Comments and user-generated content
4. Footer information and copyright notices
5. Social media widgets and sharing buttons
6. Related articles and recommendations
7. HTML tags and formatting

Return only the clean, readable article text content without any HTML tags or formatting:

HTML Content:
{html_chunk}
"""
        
        response = await self.html_extraction_model.ainvoke(extraction_prompt)
        
        if hasattr(response, 'content'):
            return response.content
        elif isinstance(response, str):
            return response
        else:
            return str(response)
    
    async def _extract_article_content(self, title: str, text: str, source: str) -> ArticleContentExtraction:
        extraction_prompt = f"""
Analyze the following news article and extract the requested information:

News Article:
- Title: {title}
- Source: {source}
- Content: {text[:ARTICLE_CONTENT_MAX_LENGTH]}
"""

        response = await self.llm_model.ainvoke(extraction_prompt)

        if not isinstance(response, ArticleContentExtraction):
            raise ValueError(f"Unexpected response type while extracting article content: {type(response)}")
        
        return response
