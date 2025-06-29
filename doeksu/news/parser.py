import asyncio
from typing import List, Optional
from newspaper import Article
from langchain.schema.language_model import BaseLanguageModel
from langchain_text_splitters import RecursiveCharacterTextSplitter
from doeksu.news.model import NewsArticle
from doeksu.logging_config import logger
from pydantic import BaseModel, Field
from doeksu.config import CONFIG
from doeksu.agent.prompts import AIPrompt, SystemPrompt, count_tokens


class ArticleContentExtraction(BaseModel):
    summary: str = Field(description=f"A concise summary of the article between minimum {CONFIG.ARTICLE_SUMMARY_MIN_WORD_COUNT} and maximum {CONFIG.ARTICLE_SUMMARY_MAX_WORD_COUNT} words.")
    author: Optional[str] = Field(description="The author name if mentioned in the text, otherwise None")
    keywords: List[str] = Field(description=f"{CONFIG.ARTICLE_KEYWORDS_MIN_COUNT}-{CONFIG.ARTICLE_KEYWORDS_MAX_COUNT} relevant keywords/tags for the article")


class NewsArticleParser:

    def __init__(self, llm_model: BaseLanguageModel, system_prompt: Optional[SystemPrompt] = None):
        self.article_content_extraction_model = llm_model.with_structured_output(ArticleContentExtraction)
        self.html_to_text_model = llm_model
        self.system_prompt = system_prompt or SystemPrompt()
    
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

            logger.info(f"Article parsed successfully with summary: {news_article.summary[:100]}...")
            
            return news_article
            
        except Exception as e:
            logger.error(f"Error parsing article {news_article.url}: {e}")
            raise e
    
    def split_html_by_tokens(self, html: str, max_tokens: int) -> List[str]:
        """Split HTML content into chunks based on token count using LangChain's RecursiveCharacterTextSplitter."""
        
        # HTML-specific separators including tags and HTML-related symbols
        html_separators = [
            "</div>", "</section>", "</article>", "</main>", "</body>", "</html>",
            "<div", "<section", "<article", "<main", "<body", "<html",
            "</p>", "<p>", "</h1>", "</h2>", "</h3>", "</h4>", "</h5>", "</h6>",
            "<h1", "<h2", "<h3", "<h4", "<h5", "<h6",
            "</li>", "<li>", "</ul>", "<ul>", "</ol>", "<ol>",
            "</td>", "<td", "</tr>", "<tr>", "</table>", "<table",
            "</span>", "<span", "</a>", "<a ",
            "\n\n", "\n", ". ", "! ", "? ", "; ", ": ", " ", ""
        ]
        
        # Estimate chunk size based on average characters per token (approximately 4)
        chunk_size = max_tokens * 4
        chunk_overlap = min(200, chunk_size // 10)  # 10% overlap, max 200 chars
        
        text_splitter = RecursiveCharacterTextSplitter(
            separators=html_separators,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        
        chunks = text_splitter.split_text(html)
    
        return chunks
    
    async def _extract_text_from_html(self, html: str) -> str:
        """Extract article text from HTML by processing it in chunks using LLM."""
        if not html:
            return ""
        
        max_tokens = CONFIG.ARTICLE_PARSER_HTML_CHUNK_TOKEN_SIZE
        html_token_count = count_tokens(html)
        
        if html_token_count <= max_tokens:
            return await self._extract_text_from_html_chunk(html)
        
        logger.info(f"HTML content ({html_token_count} tokens) exceeds max token limit ({max_tokens}). Processing in chunks.")
        
        chunks = self.split_html_by_tokens(html, max_tokens)
        logger.info(f"Split HTML into {len(chunks)} chunks for extraction")
        
        extracted_texts = []
        for i, chunk in enumerate(chunks):
            chunk_tokens = count_tokens(chunk)
            logger.debug(f"Processing HTML chunk {i+1}/{len(chunks)} ({chunk_tokens} tokens)")
            extracted_text = await self._extract_text_from_html_chunk(chunk)
            if extracted_text.strip():
                extracted_texts.append(extracted_text)
        
        combined_text = "\n\n".join(extracted_texts)
        combined_tokens = count_tokens(combined_text)
        logger.info(f"Article text extraction from HTML complete: {html_token_count} tokens -> {combined_tokens} tokens ({len(combined_text)} chars)")
        
        return combined_text
    
    async def _extract_text_from_html_chunk(self, html_chunk: str) -> str:
        """Extract article text from a single HTML chunk."""

        prompt = AIPrompt(self.system_prompt)
        prompt.add_task_prompt(f"""
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
        )
        
        response = await self.html_to_text_model.ainvoke(prompt.get_prompt())
        
        if hasattr(response, 'content'):
            return response.content
        elif isinstance(response, str):
            return response
        else:
            return str(response)
    
    async def _extract_article_content(self, title: str, text: str, source: str) -> ArticleContentExtraction:
        max_tokens = CONFIG.ARTICLE_PARSER_CONTENT_MAX_TOKEN_LENGTH
        content_tokens = count_tokens(text)
        
        if content_tokens > max_tokens:
            logger.info(f"Article content ({content_tokens} tokens) exceeds max token limit ({max_tokens}). Truncating.")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=max_tokens * 3,
                chunk_overlap=100,
                length_function=len,
                is_separator_regex=False,
            )
            chunks = text_splitter.split_text(text)
            
            truncated_text = ""
            current_tokens = 0
            
            for chunk in chunks:
                chunk_tokens = count_tokens(chunk)
                if current_tokens + chunk_tokens <= max_tokens:
                    truncated_text += chunk + "\n\n"
                    current_tokens += chunk_tokens
                else:
                    break
            
            text = truncated_text.strip()
            logger.info(f"Truncated content to {count_tokens(text)} tokens")
        
        prompt = AIPrompt(self.system_prompt)
        prompt.add_task_prompt(f"""
Analyze the following news article and extract the requested information:

News Article:
- Title: {title}
- Source: {source}
- Content: {text}
"""
        )

        response = await self.article_content_extraction_model.ainvoke(prompt.get_prompt())

        if not isinstance(response, ArticleContentExtraction):
            raise ValueError(f"Unexpected response type while extracting article content: {type(response)}")
        
        return response
