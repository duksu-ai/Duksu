from typing import Literal, List, TypedDict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from langgraph.graph import END
import os
from src.hackerrank.tools import (
    fetch_trending_tech_news,
    search_tech_topics,
    read_notes,
    write_notes
)
from src.hackerrank.views import AgentState


# Initialize LLMs with API keys from environment
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
llm_big = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

# -------------------- Supervisor nodes --------------------

def make_supervisor_node(members: list[str], system_prompt: str):
    """Creates a supervisor node that routes to team members."""
    options = ["FINISH"] + members

    class Router(TypedDict):
        """Worker to route to next. If no workers needed, route to FINISH."""
        next: Literal[*options]
        instruction: str

    def supervisor_node(state: AgentState) -> Command[Literal[*members, "__end__"]]:
        """An LLM-based router with authority to end the workflow."""
        messages = [
            {"role": "system", "content": system_prompt},
        ] + state["messages"]
        
        response = llm.with_structured_output(Router).invoke(messages)
        goto = response["next"]
        instruction = response["instruction"]
        
        if goto == "FINISH":
            goto = END
            
            # Extract final summary from notes
            final_summary = extract_final_summary()
            instruction = f"{instruction}\n\n# FINAL TECH NEWS SUMMARY\n\n{final_summary}"
            
            return Command(
                goto=goto, 
                update={
                    "next": goto,
                    "messages": state["messages"] + [
                        AIMessage(content=instruction, name="supervisor")
                    ]
                }
            )

        return Command(
            goto=goto, 
            update={
                "next": goto,
                "messages": state["messages"] + [
                    HumanMessage(
                        content=f"[INSTRUCTION FROM SUPERVISOR]\n{instruction}",
                        name="supervisor"
                    )
                ]
            }
        )

    return supervisor_node

# -------------------- Researcher Nodes --------------------

trending_news_prompt = """⚠️ IMPORTANT: You MUST use the fetch_trending_tech_news tool and then save your findings using write_notes.

You are a tech news researcher. Your job is to:
1. Use fetch_trending_tech_news to get trending tech news
2. Save ALL findings to notes using write_notes under section="Trending Tech News"

REQUIRED STEPS:
1. Use fetch_trending_tech_news with appropriate categories and period parameters
2. Use write_notes to save ALL the findings under "Trending Tech News" section

After saving the research, inform the supervisor you've completed your task.
"""

trending_news_agent = create_react_agent(
    llm_big,
    tools=[fetch_trending_tech_news, write_notes],
    prompt=trending_news_prompt
)

def trending_news_node(state: AgentState) -> Command:
    """Node for fetching trending tech news."""
    result = trending_news_agent.invoke(state)
    
    agent_messages = [msg for msg in result["messages"] if msg.content.strip()]
    agent_content = agent_messages[-1].content if agent_messages else "No valid results."

    completed_label = "[COMPLETED trending_news_agent]\n"

    return Command(
        update={
            "messages": state["messages"] + [
                AIMessage(content=completed_label + agent_content, name="trending_news_agent")
            ]
        },
        goto="supervisor",
    )


topic_search_prompt = """⚠️ IMPORTANT: You MUST use the search_tech_topics tool and then save your findings using write_notes.

You are a tech topics researcher. Your job is to:
1. Use search_tech_topics to search for specific tech topics (like programming languages, frameworks, or tech concepts)
2. Save ALL findings to notes using write_notes under section="Tech Topics Search"

REQUIRED STEPS:
1. Use search_tech_topics with appropriate keyword parameter based on the instruction
2. Use write_notes to save ALL the findings under "Tech Topics Search" section

After saving the research, inform the supervisor you've completed your task.
"""

topic_search_agent = create_react_agent(
    llm_big,
    tools=[search_tech_topics, write_notes],
    prompt=topic_search_prompt
)

def topic_search_node(state: AgentState) -> Command:
    """Node for searching specific tech topics."""
    result = topic_search_agent.invoke(state)
    
    agent_messages = [msg for msg in result["messages"] if msg.content.strip()]
    agent_content = agent_messages[-1].content if agent_messages else "No valid results."

    completed_label = "[COMPLETED topic_search_agent]\n"

    return Command(
        update={
            "messages": state["messages"] + [
                AIMessage(content=completed_label + agent_content, name="topic_search_agent")
            ]
        },
        goto="supervisor",
    )

# -------------------- Summarizer Node --------------------

summarizer_prompt = """⚠️ IMPORTANT: You MUST use read_notes to read all the research, then create a concise summary, and save it with write_notes.

You are a tech news summarizer. Your job is to:
1. Read all collected research using read_notes
2. Create a clear, concise summary focusing on:
   - Most significant tech developments and trends
   - Key insights from the research
   - Why these developments matter
3. Save your summary using write_notes under section="Final Summary"

Your summary should be 300-500 words and include:
- A headline summary of top tech news
- Key developments in bullet points (5-8)
- Emerging trends section (2-3 paragraphs)
- Notable mentions section for interesting minor developments

After saving the summary, inform the supervisor you've completed your task.
"""

summarizer_agent = create_react_agent(
    llm_big,
    tools=[read_notes, write_notes],
    prompt=summarizer_prompt
)

def summarizer_node(state: AgentState) -> Command:
    """Node for summarizing all tech news research."""
    result = summarizer_agent.invoke(state)
    
    agent_messages = [msg for msg in result["messages"] if msg.content.strip()]
    agent_content = agent_messages[-1].content if agent_messages else "No valid results."

    completed_label = "[COMPLETED summarizer_agent]\n"

    return Command(
        update={
            "messages": state["messages"] + [
                AIMessage(content=completed_label + agent_content, name="summarizer_agent")
            ]
        },
        goto="supervisor",
    )

# -------------------- Helper Functions --------------------

def extract_final_summary():
    """Extract the final summary from notes."""
    try:
        notes_content = read_notes()
        lines = notes_content.split("\n")
        final_summary = []
        in_final_summary = False
        
        for line in lines:
            if not in_final_summary and "## Final Summary" in line:
                in_final_summary = True
                continue
            elif in_final_summary and line.startswith("##"):
                in_final_summary = False
                continue
            
            if in_final_summary:
                final_summary.append(line)
        
        return "\n".join(final_summary).strip() or "No final summary found in notes."
    except Exception as e:
        return f"Error extracting final summary: {str(e)}"
