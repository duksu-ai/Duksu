import pytest
import asyncio
import json
from pathlib import Path
import re

from doeksu.news.model import NewsArticle
from doeksu.news.parser import NewsArticleParser
from doeksu.config import get_llm, CONFIG


class TestNewsArticleParser:
    
    @pytest.fixture
    def output_dir(self):
        """Create and return the output directory path."""
        output_path = Path("tests/output")
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path
    
    @pytest.fixture
    def llm_model(self):
        return get_llm(temperature=0.0)
    
    @pytest.fixture
    def sample_article(self):
        return NewsArticle(
            title="At Amazon's Biggest Data Center, Everything Is Supersized for A.I. - The New York Times",
            url="https://www.nytimes.com/2025/06/24/technology/amazon-ai-data-centers.html",
            source="The New York Times",
            published_at=1750784976
        )
    
    def _count_words(self, text: str) -> int:
        """Count words in a text string."""
        if not text:
            return 0
        return len(text.split())
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text by removing extra spaces and converting to lowercase."""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip().lower())

    @pytest.mark.asyncio
    async def test_parse_article(self, llm_model, sample_article, output_dir):
        """Test the complete article parsing workflow from URL to hydrated article."""
        parser = NewsArticleParser(llm_model)

        parsed_article = await parser.parse_article(sample_article)
        
        # Save parsed output
        output_file = output_dir / "test_news_parse_article.json"
        
        article_data = {
            "title": parsed_article.title,
            "url": parsed_article.url,
            "source": parsed_article.source,
            "published_at": parsed_article.published_at,
            "is_hydrated": parsed_article.is_hydrated,
            "thumbnail_url": parsed_article.thumbnail_url,
            "summary": parsed_article.summary,
            "author": parsed_article.author,
            "keywords": parsed_article.keywords,
            "content": parsed_article.content,
            "has_raw_html": parsed_article.raw_html is not None,
            "raw_html_length": len(parsed_article.raw_html) if parsed_article.raw_html else 0,
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, indent=2, ensure_ascii=False)
        
        print(f"Parser result saved to: {output_file}")

        assert parsed_article.is_hydrated, "Article should be hydrated"
        assert parsed_article.raw_html is not None and len(parsed_article.raw_html) > 0, "Raw HTML should not be None"
        assert parsed_article.content is not None and len(parsed_article.content) > 0, "Content should not be None"
        assert parsed_article.summary is not None, "Summary should not be None"
        assert parsed_article.author is not None, "Author should not be None"
        assert parsed_article.keywords is not None, "Keywords should not be None"
        
        # Summary validation - check word count is within configured range
        summary_word_count = self._count_words(parsed_article.summary)
        assert summary_word_count >= CONFIG.ARTICLE_SUMMARY_MIN_WORD_COUNT, \
            f"Summary word count ({summary_word_count}) is below minimum ({CONFIG.ARTICLE_SUMMARY_MIN_WORD_COUNT})"
        assert summary_word_count <= CONFIG.ARTICLE_SUMMARY_MAX_WORD_COUNT, \
            f"Summary word count ({summary_word_count}) exceeds maximum ({CONFIG.ARTICLE_SUMMARY_MAX_WORD_COUNT})"
        
        assert len(parsed_article.keywords) >= CONFIG.ARTICLE_KEYWORDS_MIN_COUNT, \
            f"Keywords count ({len(parsed_article.keywords)}) is below minimum ({CONFIG.ARTICLE_KEYWORDS_MIN_COUNT})"
        assert len(parsed_article.keywords) <= CONFIG.ARTICLE_KEYWORDS_MAX_COUNT, \
            f"Keywords count ({len(parsed_article.keywords)}) exceeds maximum ({CONFIG.ARTICLE_KEYWORDS_MAX_COUNT})"
        
        assert any('amazon' in keyword.lower() for keyword in parsed_article.keywords), \
            f"Keywords should contain 'Amazon': {parsed_article.keywords}"
        assert any(
            any(ai_term in keyword.lower() for ai_term in ['artificial intelligence', 'ai', 'a.i.'])
            for keyword in parsed_article.keywords
        ), \
            f"Keywords should contain AI-related terms: {parsed_article.keywords} (case insensitive)"
        
        expected_authors = ["Karen Weise", "Cade Metz", "A.J. Mast"]
        normalized_author = self._normalize_text(parsed_article.author)
        normalized_expected = [self._normalize_text(author) for author in expected_authors]
        author_valid = any(
            normalized_expected in normalized_author or normalized_author in normalized_expected
            for normalized_expected in normalized_expected
        )
        
        assert author_valid, \
            f"Author '{parsed_article.author}' should contain one of {expected_authors} (case insensitive)"
        
