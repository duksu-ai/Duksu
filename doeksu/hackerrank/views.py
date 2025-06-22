from typing import TypedDict, List
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """State for the tech news bot system."""
    messages: List[BaseMessage]
    next: str = ""  # Next node to run