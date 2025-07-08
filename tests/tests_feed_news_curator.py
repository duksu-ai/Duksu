import pytest
import asyncio
import json
from pathlib import Path
from typing import List

from duksu.news.model import NewsArticle
from duksu.feed.curator import FeedCurator
from duksu.feed.model import Feed
from duksu.config import get_llm


class TestFeedCurator:
    
    def _feed_to_output_format(self, feed: Feed) -> dict:
        """Helper function to transform Feed object to output format for saving."""
        return {
            "query_prompt": feed.query_prompt,
            "feed_name": feed.feed_name,
            "items_count": len(feed.items),
            "items": [
                {
                    "article": {
                        "title": item.item.title,
                        "url": item.item.url,
                        "source": item.item.source,
                        "keywords": item.item.keywords
                    },
                    "scores": {
                        "relevance": {
                            "score": item.scores['relevance'].score,
                            "reasoning": item.scores['relevance'].reasoning
                        }
                    }
                }
                for item in feed.items
            ]
        }
    
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
    def sample_articles(self) -> List[NewsArticle]:
        data_file = Path("tests/datasets/news_articles.json")
        
        with open(data_file, 'r', encoding='utf-8') as f:
            articles_data = json.load(f)
        
        articles = []
        for article_data in articles_data:
            article = NewsArticle(
                title=article_data["title"],
                url=article_data["url"],
                source=article_data["source"],
                published_at=article_data["published_at"],
                is_hydrated=article_data["is_hydrated"],
                thumbnail_url=article_data.get("thumbnail_url"),
                summary=article_data.get("summary"),
                author=article_data.get("author"),
                keywords=article_data.get("keywords"),
                content=article_data.get("content")
            )
            articles.append(article)
        
        return articles
    
    @pytest.mark.asyncio
    async def test_curate_ai_focused_feed(self, llm_model, sample_articles, output_dir):
        """Test curation of AI-focused news feed."""
        curator = FeedCurator(llm_model)
        
        query_prompt = "Show me the latest developments in artificial intelligence and machine learning"
        
        curated_feed = await curator.curate_news_feed(
            articles=sample_articles,
            query_prompt=query_prompt,
            max_articles=3,
            min_relevance_score=0.6
        )
        
        assert isinstance(curated_feed, Feed)
        assert curated_feed.query_prompt == query_prompt
        assert curated_feed.feed_name is not None and curated_feed.feed_name.strip() != ""
        
        # Verify AI-related articles are prioritized
        ai_keywords = ["AI", "artificial intelligence", "machine learning", "OpenAI", "GPT"]
        ai_articles_count = sum(
            1 for item in curated_feed.items 
            if any(keyword.lower() in item.item.title.lower() or 
                   any(kw.lower() in keyword.lower() for kw in (item.item.keywords or []))
                   for keyword in ai_keywords)
        )
        
        assert ai_articles_count > 0, "Feed should contain AI-related articles"
        assert len(curated_feed.items) <= 3, "Should respect max_articles limit"
        
        # Save test output
        output_file = output_dir / "test_feed_news_curatoration_ai.json"
        feed_data = self._feed_to_output_format(curated_feed)

        print(f"== Curator generated feed: {feed_data}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(feed_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully curated AI feed: '{curated_feed.feed_name}'")
        print(f"✓ Output saved to: {output_file}")
    
    @pytest.mark.asyncio
    async def test_curate_sports_focused_feed(self, llm_model, sample_articles, output_dir):
        """Test curation of sports-focused news feed."""
        curator = FeedCurator(llm_model)
        
        query_prompt = "Show me the latest sports news and highlights from major leagues"
        
        curated_feed = await curator.curate_news_feed(
            articles=sample_articles,
            query_prompt=query_prompt,
            max_articles=3,
            min_relevance_score=0.5
        )
        
        # Verify feed structure
        assert isinstance(curated_feed, Feed)
        assert curated_feed.query_prompt == query_prompt
        assert curated_feed.feed_name is not None
        
        # Verify sports-related articles are selected
        sports_keywords = ["soccer", "football", "basketball", "NBA", "MLS", "championship", "finals"]
        sports_articles_count = sum(
            1 for item in curated_feed.items 
            if any(keyword.lower() in item.item.title.lower() or 
                   any(kw.lower() in keyword.lower() for kw in (item.item.keywords or []))
                   for keyword in sports_keywords)
        )
        
        assert sports_articles_count > 0, "Feed should contain sports-related articles"
        assert len(curated_feed.items) <= 3, "Should respect max_articles limit"
        
        # Save test output
        output_file = output_dir / "test_feed_news_curatoration_sports.json"
        feed_data = self._feed_to_output_format(curated_feed)

        print(f"== Curator generated feed: {feed_data}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(feed_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully curated sports feed: '{curated_feed.feed_name}'")
        print(f"✓ Output saved to: {output_file}")
    
