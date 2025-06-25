import pytest
import asyncio
import json
from pathlib import Path

from doeksu.news.model import NewsArticle
from doeksu.news.parser import NewsArticleParser
from doeksu.config import get_llm


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
            title="At Amazon’s Biggest Data Center, Everything Is Supersized for A.I. - The New York Times",
            url="https://www.nytimes.com/2025/06/24/technology/amazon-ai-data-centers.html",
            source="The New York Times",
            published_at=1750784976
        )
    
    @pytest.mark.asyncio
    async def test_parse_article(self, llm_model, sample_article, output_dir):
        """Test the complete article parsing workflow from URL to hydrated article."""
        parser = NewsArticleParser(llm_model)

        parsed_article = await parser.parse_article(sample_article)
        
        assert parsed_article.is_hydrated
        assert parsed_article.raw_html is not None
        assert parsed_article.content is not None
        assert parsed_article.summary is not None
        assert parsed_article.author is not None
        assert parsed_article.keywords is not None
        assert len(parsed_article.keywords) > 0
        
        # Save test output
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
        
        print(f"✓ Successfully parsed article: '{parsed_article.title}'")
        print(f"✓ Output saved to: {output_file}")
