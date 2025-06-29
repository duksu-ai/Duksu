import json
from typing import Dict, Any
from doeksu.config import get_llm
from doeksu.news import NewsSourceRegistry
from ..state import NewsSourceSelectionState
from ..storage.db import get_db_session
from ..storage.model import NewsSourceMapping


async def select_news_sources_node(state: NewsSourceSelectionState) -> NewsSourceSelectionState:
    try:
        llm = get_llm()
        
        selected_sources = await NewsSourceRegistry.search_sources(
            llm_model=llm,
            query_prompt=state["query_prompt"]
        )
        
        if not selected_sources:
            state["error_message"] = "No relevant news sources found for the query"
            return state
        
        state["selected_sources"] = selected_sources
        
        # Save to database
        with get_db_session() as session:
            mapping = NewsSourceMapping(
                user_id=state["user_id"],
                query_prompt=state["query_prompt"],
                selected_sources=json.dumps(list(selected_sources.keys()))
            )
            session.add(mapping)
        
    except Exception as e:
        state["error_message"] = str(e)
        raise e
    
    return state 