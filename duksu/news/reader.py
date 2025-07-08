import asyncio
from typing import List, Optional
from bs4 import BeautifulSoup
from newspaper import Article
from langchain.schema.language_model import BaseLanguageModel
from langchain_text_splitters import RecursiveCharacterTextSplitter
from duksu.news.model import NewsArticle
from duksu.logging_config import create_logger
from pydantic import BaseModel, Field
from duksu.config import CONFIG
from duksu.agent.prompts import AIPrompt, SystemPrompt, count_tokens
import re


class ArticleContentNotAccessibleError(Exception):
    pass


class ArticleContentExtraction(BaseModel):
    summary: str = Field(default="", description=f"A concise summary of the article between minimum {CONFIG.ARTICLE_SUMMARY_MIN_WORD_COUNT} and maximum {CONFIG.ARTICLE_SUMMARY_MAX_WORD_COUNT} words.")
    summary_short: str = Field(default="", description=f"A shorter summary (1–2 sentences) highlighting the key point of the article to attract user interest at a glance.")
    author: str = Field(default="", description="The author name if mentioned in the text, otherwise None")
    keywords: List[str] = Field(default=[], description=f"{CONFIG.ARTICLE_KEYWORDS_MIN_COUNT}-{CONFIG.ARTICLE_KEYWORDS_MAX_COUNT} relevant keywords/tags for the article")
    is_content_sufficient: bool = Field(description="True if the article content is sufficient to provide a summary, False if content is behind subscription barrier, paywall, or otherwise inaccessible")
    is_content_sufficient_reasoning: str = Field(default="", description="Reasoning for the is_content_sufficient field")


class NewsArticleReader:

    def __init__(self, llm_model: BaseLanguageModel, system_prompt: Optional[SystemPrompt] = None):
        self.article_content_extraction_model = llm_model.with_structured_output(ArticleContentExtraction)
        self.system_prompt = system_prompt or SystemPrompt()
        self.logger = create_logger("NewsArticleReader")
    
    async def read_article(self, news_article: NewsArticle) -> NewsArticle:
        """
        Parse a news article by downloading its content and using LLM to extract additional info.
        
        Args:
            news_article: NewsArticle object with at least title and url
            
        Returns:
            NewsArticle with filled summary, author, keywords, and thumbnail_url, etc
        """
        article = Article(news_article.url)
        try:
            article.download()
            article.parse()
        except Exception as e:
            raise ArticleContentNotAccessibleError(f"Article unable to download: {e}")
        
        article_text = await self._extract_text_from_html(article.html)
        if not article_text:
            raise ArticleContentNotAccessibleError(f"No text content found from html for article: {news_article.url}. HTML: {article.html}")

        news_article.raw_html = article.html
        news_article.content = article_text
   
        article_content = await self._extract_article_content(
            title=news_article.title,
            text=article_text,
            source=news_article.source
        )

        if not article_content.is_content_sufficient:
            raise ArticleContentNotAccessibleError(f"Article content is not accessible: {article_content.is_content_sufficient_reasoning}")

        news_article.summary = article_content.summary
        news_article.author = article_content.author if article_content.author and article_content.author != "None" else None
        news_article.keywords = article_content.keywords[:CONFIG.ARTICLE_KEYWORDS_MAX_COUNT]
        news_article.thumbnail_url = article.top_image if article.top_image else None

        news_article.is_hydrated = True

        self.logger.info(f"Article Reader completed processing article \"{news_article.title}\" with summary: \"{news_article.summary[:100]}...\"")
        
        return news_article
    
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
        soup = BeautifulSoup(html, 'html.parser')
        # kill all script and style elements
        for script in soup(["script", "style"]):
            script.extract()    # rip it out

        text = soup.get_text()
        
        # Clean up the text: remove empty lines and trim whitespace
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped_line = line.strip()
            if stripped_line:
                cleaned_lines.append(stripped_line)
        
        text = '\n'.join(cleaned_lines)
        text_token_count = count_tokens(text)
        self.logger.debug(f"Extracted {text_token_count} tokens of text from article HTML")

        return text
    
    async def _extract_article_content(self, title: str, text: str, source: str) -> ArticleContentExtraction:
        max_tokens = CONFIG.ARTICLE_PARSER_CONTENT_MAX_TOKEN_LENGTH
        content_tokens = count_tokens(text)
        
        if content_tokens > max_tokens:
            self.logger.info(f"Article content ({content_tokens} tokens) exceeds max token limit ({max_tokens}). Truncating.")
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
            self.logger.info(f"Truncated content to {count_tokens(text)} tokens")
        
        prompt = AIPrompt(self.system_prompt)
        prompt.add_task_prompt(f"""
Analyze the following news article and extract the requested information. 

GUIDELINES:
1. Summary should be a concise, headline-style, a news brief tone. 
2. Begin the summary directly with the subject or action (e.g., "AI startup Abridge has..."), without using meta phrases like "This article reports..." or "According to the article."
3. Keywords should be a list of 3-5 relevant keywords/tags for the article.
4. Author should be the name of the author if mentioned in the text, otherwise None.

IMPORTANT:
If the provided article content is not sufficient to provide a summary due to subscription barrier, login required, cut off or insufficient length of content, or similar access restrictions. then
1. Set is_content_sufficient to False.
2. Provide a reasoning on why the article content is not sufficient for the is_content_sufficient_reasoning field.
3. Leave the other fields empty.

News Article:
- Title: {title}
- Source: {source}
- Content: {text}
"""
        )

        response = await self.article_content_extraction_model.ainvoke(prompt.get_prompt())

        if not isinstance(response, ArticleContentExtraction):
            self.logger.error(f"Unexpected response type while extracting article content; LLM response: {response}")
            return ArticleContentExtraction(
                is_content_sufficient=False,
                is_content_sufficient_reasoning=f"Unexpected response type while extracting article content: {type(response)}"
            )
        
        return response
