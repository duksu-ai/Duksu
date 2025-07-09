import json
from typing import Any, Callable, Coroutine, List

from langchain_core.rate_limiters import InMemoryRateLimiter
from duksu.config import get_llm
from duksu.feed import FeedCurator
from duksu.news.source import NewsSourceRegistry
from duksu.news.reader import ArticleContentNotAccessibleError, NewsArticleReader
from duksu.logging_config import logger

from ..state import CreateNewsFeedState, PopulateFeedState
from ...storage.db import Storage, get_db
from ...storage.model import NewsFeed, NewsArticle as DBNewsArticle, NewsFeedItem


async def create_feed_node(state: CreateNewsFeedState):
    """
    Create a new news feed in the database after successful source selection.
    This creates an empty feed that can later be populated with articles.
    """
    try:
        db = get_db()

        # Check if feed with same user_id and query prompt already exists
        existing_feed = db.query(NewsFeed).filter(
            NewsFeed.user_id == state["user_id"],
            NewsFeed.query_prompt == state["query_prompt"]
        ).first()
        if existing_feed:
            state["error_message"] = "A feed with given user id and query prompt already exists"
            return state

        # Create the news feed
        news_feed = NewsFeed(
            user_id=state["user_id"],
            query_prompt=state["query_prompt"],
        )
        db.add(news_feed)
        db.flush()  # Get the ID

        return { "feed_id": news_feed.id }
            
    except Exception as e:
        state["error_message"] = str(e)
        raise e


async def create_news_search_plans_node(state: PopulateFeedState):
    try:
        llm = get_llm()

        news_search_plans = await NewsSourceRegistry.get_news_search_plans(llm, state["feed_query_prompt"])
        if len(news_search_plans.search_plans) == 0:
            raise ValueError("No news search plans found")

        for plan in news_search_plans.search_plans:
            logger.debug(f"News Source: {plan.source_name}, Parameters: {plan.parameters}, Reasoning: {plan.reasoning}")

        return {"news_search_plans": news_search_plans.search_plans }
        
    except Exception as e:
        state["error_message"] = str(e)
        raise e


async def retrieve_articles_node(state: Any):
    try:
        if "news_search_plan" not in state:
            raise ValueError("Malformed state, required field 'news_search_plan' not found")

        news_search_plan = state["news_search_plan"]

        logger.info(f"Retrieving articles from {news_search_plan.source_name} with parameters {news_search_plan.parameters}")
        
        raw_articles = await NewsSourceRegistry.retrieve_news_articles_from_source(
            source_name=news_search_plan.source_name,
            params=json.loads(news_search_plan.parameters)
        )
        if not raw_articles:
            state["error_message"] = f"No articles found from {news_search_plan.source_name} with parameters {news_search_plan.parameters}"
            return
        
        return {"articles_retrieved": raw_articles} # type: ignore
                
    except Exception as e:
        logger.error(f"Error retrieving articles from {news_search_plan.source_name}: {e}")
        state["error_message"] = str(e)
        raise e


async def read_and_store_articles_node(state: PopulateFeedState) -> PopulateFeedState:
    """
    Read articles through url to get the full article content, and store them in the database.
    """
    llm_rate_limiter = InMemoryRateLimiter(requests_per_second=2) # 2 request per 1 seconds (to address TPM qouta)
    article_reader = NewsArticleReader(llm_model=get_llm(rate_limiter=llm_rate_limiter))

    raw_articles = state["articles_curated"]
    
    articles = []
    
    for i, article in enumerate(raw_articles, 1):
        logger.debug(f"({i}/{len(raw_articles)}) AI is reading article \"{article.title}\" - {article.url}")

        # check if article is already in DB
        stored_article = Storage.get_news_article_by_url(article.url)
        if stored_article:
            logger.debug(f"Article {article.title} - {article.url} already exists in DB, skipping...")
            articles.append(stored_article)
        else:
            # if article is not in DB, read it and store it
            try:
                hydrated_article = await article_reader.read_article(article)
                await Storage.store_news_article(hydrated_article)

                articles.append(hydrated_article)
            except ArticleContentNotAccessibleError as e:
                logger.debug(f"Skipping article as content is not accessible: {e}")
                continue
    
    return {"articles_curated": articles} # type: ignore

def curate_articles_node(min_relevance_score: float, max_articles_per_batch: int) -> Any:
    """
    Curate the articles and store them in the database.
    """
    async def curate_articles_node_func(state: PopulateFeedState):
        try:
            if not state["articles_curated"]:
                raise ValueError("No articles to curate")

            db = get_db()
            feed = db.query(NewsFeed).filter(NewsFeed.id == state["feed_id"]).first()
            if not feed:
                raise ValueError(f"Feed with ID {state['feed_id']} not found")

            # Omit articles that are already linked to the feed
            articles_to_curate = []
            for article in state["articles_curated"]:
                existing_article = db.query(DBNewsArticle).filter(DBNewsArticle.url == article.url).first()
                if existing_article:
                    existing_feed_item = db.query(NewsFeedItem).filter(
                            NewsFeedItem.news_feed_id == state["feed_id"],
                            NewsFeedItem.news_article_id == existing_article.id
                        ).first()
                    if existing_feed_item:
                        continue
                    
                articles_to_curate.append(article)

            # Curate articles using FeedCurator
            curator = FeedCurator(llm=get_llm())
            news_curation_result = await curator.curate_news_feed(
                query_prompt=str(feed.query_prompt),
                articles=articles_to_curate,
                max_articles_per_batch=max_articles_per_batch,
                min_relevance_score=min_relevance_score
            )

            await Storage.store_curation_result(content={
                "query_prompt": feed.query_prompt,
                "articles": [
                    {
                        "title": x.item.title,
                        "url": x.item.url,
                        "summary": x.item.summary,
                        "scores": x.scores
                    } for x in news_curation_result.items
                ]
            })

            logger.info(f"Successfully curated {len(news_curation_result.items)} articles for feed {feed.id} with query prompt {feed.query_prompt}")
            return {"articles_curated": list(map(lambda x: x.item, news_curation_result.items))}

        except Exception as e:
            state["error_message"] = str(e)
            raise e
    
    return curate_articles_node_func


async def save_news_articles_to_feed_node(state: PopulateFeedState):
    articles = state["articles_curated"]
    db = get_db()
    feed = db.query(NewsFeed).filter(NewsFeed.id == state["feed_id"]).first()
    db_articles = db.query(DBNewsArticle).filter(DBNewsArticle.url.in_(list(map(lambda x: x.url, articles)))).all()
    if not feed:
        raise ValueError(f"Feed with ID {state['feed_id']} not found")
    
    for db_article in db_articles:
        feed_item = NewsFeedItem(
            news_feed_id=feed.id,
            news_article_id=db_article.id,
        )
        db.add(feed_item)

    return {}