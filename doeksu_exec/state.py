from typing import TypedDict, List, Dict, Any, Optional


class NewsSourceSelectionState(TypedDict):
    """State for the news source selection workflow."""
    user_id: str
    query_prompt: str
    selected_sources: Optional[Dict[str, Any]]  # Dictionary of selected news sources
    error_message: Optional[str]
