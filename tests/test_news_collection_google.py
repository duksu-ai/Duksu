import pytest
import asyncio
import aiohttp
import json
import os
from pathlib import Path
from urllib.parse import urlencode

from doeksu.news.source.rss.google_news import (
    GoogleNewsParam,
    GoogleNewsSearchParam,
    get_google_news_rss_url,
    google_news_search,
)


class TestGoogleNewsRSS:
    
    @pytest.fixture
    def output_dir(self):
        """Create and return the output directory path."""
        output_path = Path("tests/output")
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path
    
    @pytest.mark.asyncio
    async def test_all_google_news_sources_return_valid_xml(self):
        """Test that all Google News source URLs return valid XML responses."""
        param = GoogleNewsParam(language="en", country="US")
        
        # Test all topic-based sources
        topics = ["world", "business", "technology", "entertainment", "sports", "science", "health"]
        
        async with aiohttp.ClientSession() as session:
            for topic in topics:
                url = get_google_news_rss_url(topic, param)
                
                async with session.get(url) as response:
                    assert response.status == 200, f"Failed to fetch {topic} news: HTTP {response.status}"
                    
                    content = await response.text()
                    assert content.strip().startswith('<?xml'), f"{topic} response is not XML"
                    assert '<rss' in content, f"{topic} response is not RSS format"
                    assert '</rss>' in content, f"{topic} response is incomplete RSS"
        
        # Test search-based source
        search_param = GoogleNewsSearchParam(search_keyword="python programming")
        search_url = "https://news.google.com/rss/search"
        params = {
            "q": search_param.search_keyword,
            "hl": f"{search_param.language}-{search_param.country}",
            "gl": search_param.country,
            "ceid": f"{search_param.country}:{search_param.language}"
        }
        search_url = f"{search_url}?{urlencode(params)}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url) as response:
                assert response.status == 200, f"Failed to fetch search news: HTTP {response.status}"
                
                content = await response.text()
                assert content.strip().startswith('<?xml'), "Search response is not XML"
                assert '<rss' in content, "Search response is not RSS format"
                assert '</rss>' in content, "Search response is incomplete RSS"
    
    @pytest.mark.asyncio
    async def test_google_news_fetch_articles_and_validate(self, output_dir):
        """Test fetching news and validate article fields."""
        search_param = GoogleNewsSearchParam(search_keyword="artificial intelligence")
        
        articles = await google_news_search(search_param)
        
        assert len(articles) > 0, "No articles returned from Google News Search"
        
        for i, article in enumerate(articles):
            assert article.title, f"Article {i} has empty title"
            assert article.url, f"Article {i} has empty URL"
            assert article.source, f"Article {i} has empty source"
            assert article.published_at > 0, f"Article {i} has invalid published_at timestamp"
        
        output_file = output_dir / "test_news_collection_google_search.json"
        
        articles_data = []
        for article in articles:
            articles_data.append({
                "title": article.title,
                "url": article.url,
                "source": article.source,
                "published_at": article.published_at,
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_name": "Google News Search Integration Test",
                "search_keyword": search_param.search_keyword,
                "total_articles": len(articles),
                "articles": articles_data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully fetched {len(articles)} search articles for '{search_param.search_keyword}'")
        print(f"✓ Output saved to: {output_file}")
