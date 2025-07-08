import json
from langgraph.graph import StateGraph, END
from .state import CreateNewsFeedState
from .nodes.news_feed_manager import create_feed_node
from ..storage.db import get_db_session
from ..storage.model import NewsFeed


def create_news_feed_workflow():
    workflow = StateGraph(CreateNewsFeedState)
    
    workflow.add_node("create_feed", create_feed_node)
    
    workflow.set_entry_point("create_feed")
    
    workflow.add_edge("create_feed", END)
    
    return workflow.compile()


async def execute_news_feed_workflow(user_id: str, query_prompt: str):
    try:
        workflow = create_news_feed_workflow()
        
        initial_state: CreateNewsFeedState = {
            "user_id": user_id,
            "query_prompt": query_prompt,
            "feed_id": None,
            "error_message": None
        }
        
        result = await workflow.ainvoke(initial_state)
        return result
            
    except Exception as e:
        raise e