from typing import List, Dict, Any, Optional, TypedDict, Literal
import asyncio
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langgraph.graph.tags import tagged_for_trace
from doeksu.settings import logger

from doeksu.social_media.nodes import (
    get_relevant_subreddits, 
    get_trending_posts, 
    analyze_posts_for_trends, 
    deduplicate_trends,
    decide_next_source
)

SocialMediaSource = Literal["reddit", "twitter"]

class Trend(BaseModel):
    source: SocialMediaSource = Field(description="The social media source")
    summary: str = Field(description="A concise summary of the trend")
    tags: List[str] = Field(description="Keywords associated with the trend")
    urls: List[Dict[str, str]] = Field(
        description="URLs to source materials (e.g. posts, tweets, etc.)",
        default_factory=list
    )


class GraphState(TypedDict):
    """State object for the social media trends workflow."""
    subject: str
    trends: List[Trend]
    errors: List[str]


workflow = StateGraph(GraphState)

# Define the nodes
workflow.add_node("get_subreddits", get_relevant_subreddits)
workflow.add_node("get_posts", get_trending_posts)
workflow.add_node("analyze_trends", analyze_posts_for_trends)
workflow.add_node("deduplicate", deduplicate_trends)

# Add the START edge
workflow.add_edge(START, "get_subreddits")

# Connect the nodes
workflow.add_edge("get_subreddits", "get_posts")
workflow.add_edge("get_posts", "analyze_trends")
workflow.add_edge("analyze_trends", "deduplicate")

# Add conditional branching based on the current source
workflow.add_conditional_edges(
    "deduplicate",
    decide_next_source,
    {
        "reddit": "get_subreddits",  # In the future, this would route to the next social media source
        "twitter": "get_subreddits",  # Placeholder for future Twitter implementation
        "done": END
    }
)

# Set the output structure
workflow.set_entry_point(START)