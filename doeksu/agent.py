from langgraph.graph import StateGraph, START, END
from src.hackerrank.views import AgentState
from src.hackerrank.nodes import (
    make_supervisor_node,
    trending_news_node,
    topic_search_node,
    summarizer_node
)
import os
import sys
from langsmith import traceable
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage


# Load environment variables
load_dotenv()

# Load system prompt from markdown file
def load_system_prompt(file_path="system_prompt.md"):
    """Load the system prompt from a markdown file.
    
    Raises:
        FileNotFoundError: If the system prompt file cannot be found
        IOError: If there's an error reading the system prompt file
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(current_dir, file_path)
    
    try:
        with open(full_path, "r") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        error_msg = f"ERROR: System prompt file not found at {full_path}"
        print(error_msg, file=sys.stderr)
        raise FileNotFoundError(error_msg)
    except IOError as e:
        error_msg = f"ERROR: Failed to read system prompt file: {str(e)}"
        print(error_msg, file=sys.stderr)
        raise IOError(error_msg)

# Load the supervisor prompt
try:
    SUPERVISOR_PROMPT = load_system_prompt()
except (FileNotFoundError, IOError) as e:
    print(f"FATAL ERROR: {str(e)}", file=sys.stderr)
    sys.exit(1)

# Create supervisor node using the prompt
supervisor_node = make_supervisor_node(
    ["trending_news_agent", "topic_search_agent", "summarizer_agent"],
    SUPERVISOR_PROMPT
)

# Create the workflow graph
workflow = StateGraph(AgentState)

# Add all nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("trending_news_agent", trending_news_node)
workflow.add_node("topic_search_agent", topic_search_node)
workflow.add_node("summarizer_agent", summarizer_node)

# Add edges
workflow.add_edge(START, "supervisor")

# Compile the graph
graph = workflow.compile()


