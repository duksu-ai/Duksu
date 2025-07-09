import json
from langgraph.graph import StateGraph, END
from langgraph.types import Send

from duksu_exec.storage.db import get_db
from duksu_exec.storage.model import NewsFeed
from .state import PopulateFeedState
from .nodes.news_feed_manager import (
    create_news_search_plans_node, 
    curate_articles_node,
    retrieve_articles_node,
    read_and_store_articles_node,
    save_news_articles_to_feed_node
)


def continue_to_retrieve_articles(state: PopulateFeedState):
    # Create parallel branches for retrieving articles from each news source
    return [Send("retrieve_articles", {"news_search_plan": s}) for s in state["news_search_plans"]]


def create_populate_feed_workflow():
    workflow = StateGraph(PopulateFeedState)
    
    workflow.add_node("create_search_plans", create_news_search_plans_node)
    workflow.add_node("retrieve_articles", retrieve_articles_node)
    workflow.add_node("reduce_retrieved_articles", lambda state: {"articles_curated": state["articles_retrieved"]})
    workflow.add_node("curate_articles_with_title", curate_articles_node(min_relevance_score=0.8, max_articles_per_batch=30))
    workflow.add_node("curate_articles_with_full_content", curate_articles_node(min_relevance_score=0.6, max_articles_per_batch=20))
    workflow.add_node("read_and_store_articles", read_and_store_articles_node)
    workflow.add_node("save_news_articles_to_feed", save_news_articles_to_feed_node)
    
    workflow.add_conditional_edges("create_search_plans", continue_to_retrieve_articles, ["retrieve_articles"]) # type: ignore
    workflow.add_edge("retrieve_articles", "reduce_retrieved_articles")
    workflow.add_edge("reduce_retrieved_articles", "curate_articles_with_title")
    workflow.add_edge("curate_articles_with_title", "read_and_store_articles")
    workflow.add_edge("read_and_store_articles", "curate_articles_with_full_content")
    workflow.add_edge("curate_articles_with_full_content", "save_news_articles_to_feed")
    workflow.add_edge("save_news_articles_to_feed", END)
    
    workflow.set_entry_point("create_search_plans")
    return workflow.compile()


async def execute_populate_feed_workflow(feed_id: int):
    try:
        db = get_db()
        feed = db.query(NewsFeed).filter(NewsFeed.id == feed_id).first()
        if not feed:
            raise ValueError(f"Feed with id {feed_id} not found")

        # Get search plans first
        initial_state: PopulateFeedState = {
            "feed_id": getattr(feed, "id"),
            "feed_query_prompt": getattr(feed, "query_prompt"),
            "news_search_plans": [],
            "articles_retrieved": [],
            "articles_curated": [],
            "error_message": None
        }

        result = await create_populate_feed_workflow().ainvoke(initial_state)
        return {
            "feed_id": feed.id,
            "feed_query_prompt": feed.query_prompt,
            "news_search_plans": result["news_search_plans"],
            "articles_retrieved": len(result["articles_retrieved"]),
            "articles_curated": len(result["articles_curated"]),
            "error_message": result["error_message"]
        }
            
    except Exception as e:
        raise e 