import json
from typing import List

from langchain_core.rate_limiters import InMemoryRateLimiter
from duksu.config import get_llm
from duksu.feed import FeedCurator
from duksu.news.source import NewsSourceRegistry
from duksu.news.reader import ArticleContentNotAccessibleError, NewsArticleReader
from duksu.news.model import NewsArticle
from duksu.logging_config import logger
from duksu_exec.workflows.state.state import ArticlesRetrievalState, NewsSearchExecution
from ..state import CreateNewsFeedState, PopulateFeedState
from ...storage.db import Storage, get_db
from ...storage.model import NewsFeed, NewsArticle as DBNewsArticle, NewsFeedItem


async def _read_articles(article_reader: NewsArticleReader, articles: List[NewsArticle]) -> List[NewsArticle]:
    """
    Process articles: check if they exist in DB, read and store if not.
    """
    processed_articles = []
    count = 0
    def log(message: str):
        logger.debug(f"({count}/{len(articles)}) {message}")
    
    for article in articles:
        count += 1

        stored_article = Storage.get_news_article_by_url(article.url)

        if stored_article:
            log(f"Article {article.title} - {article.url} already exists in DB, skipping...")
            processed_articles.append(stored_article)
        else:
            # if article is not in DB, read it and store it
            try:
                log(f"AI reading article \"{article.title}\" - {article.url}")
                hydrated_article = await article_reader.read_article(article)

                await Storage.store_news_article(hydrated_article)
                processed_articles.append(hydrated_article)
            except ArticleContentNotAccessibleError:
                log(f"Article content is not accessible, skipping...")
                continue
    
    return processed_articles


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
            
        curator = FeedCurator(llm=get_llm())
        feed_topic = await curator.generate_feed_topic(state["query_prompt"])

        # Create the news feed
        news_feed = NewsFeed(
            user_id=state["user_id"],
            query_prompt=state["query_prompt"],
            feed_topic=feed_topic,
        )
        db.add(news_feed)
        db.flush()  # Get the ID

        return { "feed_id": news_feed.id, "feed_topic": feed_topic }
            
    except Exception as e:
        state["error_message"] = str(e)
        raise e


async def create_news_search_execution_plans_node(state: PopulateFeedState):
    try:
        llm = get_llm()
        news_search_plans = await NewsSourceRegistry.get_news_search_plans(llm, state["feed_query_prompt"])

        plans = []
        for plan in news_search_plans.search_plans:
            plans.append(NewsSearchExecution(
                source_name=plan.source_name,
                parameters=json.loads(plan.parameters),
                reasoning=plan.reasoning
            ))
            logger.debug(f"News Source: {plan.source_name}, Parameters: {plan.parameters}, Reasoning: {plan.reasoning}")

        if len(plans) == 0:
            raise ValueError("No news search plans found")

        return { "news_search_plans": plans }
        
    except Exception as e:
        state["error_message"] = str(e)
        raise e


async def retrieve_articles_node(state: ArticlesRetrievalState):
    try:
        search_execution_plan = state["news_search_plan"]

        logger.info(f"Retrieving articles from source: {search_execution_plan.source_name} with parameters {search_execution_plan.parameters}")
        
        raw_articles = await NewsSourceRegistry.retrieve_news_articles_from_source(
            source_name=search_execution_plan.source_name,
            params=search_execution_plan.parameters
        )
        if not raw_articles:
            state["error_message"] = f"No articles found for plan {search_execution_plan.source_name}"
            return state
        
        return {"articles_to_retrieve": raw_articles} # type: ignore
                
    except Exception as e:
        logger.error(f"Error retrieving articles for plan {search_execution_plan.source_name}: {e}")
        state["error_message"] = str(e)
        raise e


async def read_articles_node(state: PopulateFeedState) -> PopulateFeedState:
    
    llm_rate_limiter = InMemoryRateLimiter(requests_per_second=2) # 2 request per 1 seconds (to address TPM qouta)
    article_reader = NewsArticleReader(llm_model=get_llm(rate_limiter=llm_rate_limiter))

    raw_articles = state["articles_to_retrieve"]
    if len(raw_articles) == 0:
        raise ValueError("No articles to retrieve")
    
    articles = []

    articles.extend(await _read_articles(article_reader, raw_articles))

    return {"articles_retrieved": articles} # type: ignore


async def curate_and_store_articles_node(state: PopulateFeedState) -> PopulateFeedState:
    """
    Curate the retrieved articles and store them in the database.
    """
    try:
        if not state["articles_retrieved"]:
            raise ValueError("No articles to curate")
        
        db = get_db()
        feed = db.query(NewsFeed).filter(NewsFeed.id == state["feed_id"]).first()
        if not feed:
            raise ValueError(f"Feed with ID {state['feed_id']} not found")
        
        # Omit articles that are already in the feed
        articles_to_curate = []
        for article in state["articles_retrieved"]:
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
        curated_feed = await curator.curate_news_feed(
            feed_topic=str(feed.feed_topic),
            query_prompt=str(feed.query_prompt),
            articles=articles_to_curate,
            max_articles_per_batch=20,
            min_relevance_score=0.6
        )
            
        for curation_item in curated_feed.items:
            article = curation_item.item
            db_article = db.query(DBNewsArticle).filter(DBNewsArticle.url == article.url).first()
            if not db_article:
                raise Exception(f"Something went wrong. Article {article.url} not found in database")
            
            feed_item = NewsFeedItem(
                news_feed_id=feed.id,
                news_article_id=db_article.id,
                curation_scores=json.dumps(curation_item.scores)
            )
            db.add(feed_item)
            
        state["articles_curated"] = list(map(lambda x: x.item, curated_feed.items)) # type: ignore
        logger.info(f"Successfully curated {len(curated_feed.items)} articles for feed {feed.id}")
    
    except Exception as e:
        state["error_message"] = str(e)
        raise e
    
    return state

