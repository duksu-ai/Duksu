from typing import List, Dict, Any, TypedDict, Annotated, Literal
import asyncio
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import END
from pydantic import BaseModel, Field
from langgraph.prebuilt import ToolExecutor

from doeksu.agent.llm import LLMFactory
from doeksu.settings import logger
from doeksu.social_media.source import reddit
from doeksu.social_media.workflow import GraphState


# Create tool executor for Reddit tools
reddit_tools = [reddit.find_relevant_subreddits, reddit.get_trending_posts]
reddit_executor = ToolExecutor(reddit_tools)


# Define node functions for the workflow
async def get_relevant_subreddits(state: GraphState) -> GraphState:
    """Find subreddits relevant to the given subject."""
    logger.info(f"Finding subreddits relevant to: {state['subject']}")
    
    try:
        # Use the tool executor to call the find_relevant_subreddits tool
        subreddits = await reddit_executor.ainvoke(
            tool_name="find_relevant_subreddits",
            input={"subject": state["subject"]}
        )
        return {"subreddits": subreddits}
    except Exception as e:
        logger.error(f"Error finding subreddits: {str(e)}")
        return {"errors": state.get("errors", []) + [f"Error finding subreddits: {str(e)}"]}


async def get_trending_posts(state: GraphState) -> GraphState:
    """Get trending posts from the identified subreddits."""
    logger.info(f"Getting trending posts from {len(state['subreddits'])} subreddits")
    
    posts = {}
    errors = state.get("errors", [])
    
    for subreddit in state["subreddits"]:
        try:
            # Use the tool executor to call the get_trending_posts tool
            posts[subreddit] = await reddit_executor.ainvoke(
                tool_name="get_trending_posts",
                input={"subreddit": subreddit}
            )
        except Exception as e:
            error_msg = f"Error getting posts from {subreddit}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    return {"posts": posts, "errors": errors}


async def analyze_posts_for_trends(state: GraphState) -> GraphState:
    """Analyze posts to identify trends."""
    logger.info("Analyzing posts to identify trends")
    
    llm = LLMFactory.get_llm(temperature=0)
    posts_data = []
    
    # Flatten posts data for analysis
    for subreddit, subreddit_posts in state["posts"].items():
        for post in subreddit_posts:
            posts_data.append({
                "subreddit": subreddit,
                "title": post["title"],
                "content": post["content"],
                "url": post["url"],
                "score": post["score"]
            })
    
    if not posts_data:
        return {"trends": [], "current_source": "done"}
    
    # Analyze posts with LLM to identify trends
    system_msg = SystemMessage(content="""
    You are a social media trends analyzer. Based on the Reddit posts provided, identify key trends related to the subject.
    For each trend, provide:
    1. A concise summary
    2. Keywords/hashtags
    3. References to source posts
    
    Format your response as a valid JSON list of trend objects.
    """)
    
    human_msg = HumanMessage(content=f"""
    Subject: {state['subject']}
    
    Reddit Posts:
    {posts_data}
    
    Identify trends from these posts related to the subject. Return a JSON list of trend objects.
    """)
    
    try:
        response = await llm.ainvoke([system_msg, human_msg])
        # Use proper JSON parsing instead of eval in production
        import json
        trends_data = json.loads(response.content)
        
        trends = []
        for trend_data in trends_data:
            trends.append(Trend(
                summary=trend_data["summary"],
                keywords=trend_data["keywords"],
                references=trend_data["references"],
                source="reddit"
            ))
        
        return {"trends": trends, "current_source": "done"}
    except Exception as e:
        logger.error(f"Error analyzing trends: {str(e)}")
        return {"errors": state.get("errors", []) + [f"Error analyzing trends: {str(e)}"], "current_source": "done"}


def deduplicate_trends(state: GraphState) -> GraphState:
    """Deduplicate trends by combining similar ones."""
    logger.info(f"Deduplicating {len(state['trends'])} trends")
    
    if not state["trends"]:
        return {}
    
    # This is a simple implementation. In a real system, you might use
    # semantic similarity to identify similar trends.
    unique_trends = []
    summaries = set()
    
    for trend in state["trends"]:
        if trend.summary not in summaries:
            summaries.add(trend.summary)
            unique_trends.append(trend)
        else:
            # Find the existing trend and append references
            for existing_trend in unique_trends:
                if existing_trend.summary == trend.summary:
                    existing_trend.references.extend(trend.references)
                    # Merge keywords
                    for keyword in trend.keywords:
                        if keyword not in existing_trend.keywords:
                            existing_trend.keywords.append(keyword)
    
    return {"trends": unique_trends}


def decide_next_source(state: GraphState) -> Literal["reddit", "twitter", "done"]:
    """Decide which social media source to process next."""
    current = state.get("current_source", "reddit")
    
    # Currently only Reddit is implemented
    # When we add more sources, this will route to them
    if current == "reddit":
        return "done"  # In future: return "twitter"
    elif current == "twitter":
        return "done"
    else:
        return "done" 