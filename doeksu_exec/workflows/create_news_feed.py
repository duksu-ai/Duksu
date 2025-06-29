import json
from langgraph import StateGraph, END
from ..state import NewsSourceSelectionState
from ..nodes.news_source_selector import select_news_sources_node
from ..storage.db import get_db_session
from ..storage.model import NewsSourceMapping


async def check_existing_mapping_node(state: NewsSourceSelectionState) -> NewsSourceSelectionState:
    """
    First check if user_id exists in database, then check if user_id and query_prompt mapping already exists.
    If existing mapping found, load it. If user doesn't exist, set error. Otherwise, pass through.
    """
    try:
        with get_db_session() as session:
            user_exists = session.query(NewsSourceMapping).filter(
                NewsSourceMapping.user_id == state["user_id"]
            ).first()
            
            if not user_exists:
                state["error_message"] = f"User ID '{state['user_id']}' not found in database"
                return state
            
            existing_mapping = session.query(NewsSourceMapping).filter(
                NewsSourceMapping.user_id == state["user_id"],
                NewsSourceMapping.query_prompt == state["query_prompt"],
            ).first()
            
            if existing_mapping:
                selected_sources_list = json.loads(existing_mapping.selected_sources)
                sources_dict = {source: {"name": source, "description": "Existing mapping"} for source in selected_sources_list}
                
                state["selected_sources"] = sources_dict
                state["error_message"] = "A feed with given user id and query prompt already exist"
                
    except Exception as e:
        state["error_message"] = str(e)
        raise e
    
    return state


def should_continue_to_select_sources(state: NewsSourceSelectionState) -> str:
    """Decide whether to continue to source selection or end based on existing data."""
    if state["error_message"] is not None:
        return "end"
    else:
        return "select_sources"


def create_news_feed_workflow():
    workflow = StateGraph(NewsSourceSelectionState)
    
    workflow.add_node("check_existing", check_existing_mapping_node)
    workflow.add_node("select_sources", select_news_sources_node)
    
    workflow.set_entry_point("check_existing")
    
    workflow.add_conditional_edges(
        "check_existing",
        should_continue_to_select_sources,
        {
            "select_sources": "select_sources",
            "end": END
        }
    )
    
    workflow.add_edge("select_sources", END)
    
    return workflow.compile()


async def execute_news_feed_workflow(user_id: str, query_prompt: str) -> NewsSourceSelectionState:
    try:
        workflow = create_news_feed_workflow()
        
        initial_state: NewsSourceSelectionState = {
            "user_id": user_id,
            "query_prompt": query_prompt,
            "selected_sources": None,
            "error_message": None
        }
        
        result = await workflow.ainvoke(initial_state)
        return result
            
    except Exception as e:
        raise e