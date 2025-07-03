from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field
from langchain.schema.language_model import BaseLanguageModel
import tiktoken


class MessageType(Enum):
    """Enumeration for different message types."""
    TASK = "task"
    INIT = "init"


class MessageMetadata(BaseModel):
    """Metadata for a prompt message including type and token count."""
    message_type: str = Field(description="Type of the message")
    tokens: int = Field(description="Number of tokens in the message")

class Message(BaseModel):
    message: str
    metadata: MessageMetadata


def count_tokens(text: str, model_name: Optional[str] = None) -> int:
    return len(tiktoken.encoding_for_model("gpt-4").encode(text))


class SystemPrompt:
    """Default system prompt for the news feed application."""
    
    def __init__(self, additional_instructions: Optional[str] = None):
        self.base_prompt = """You are an editor delivering up-to-date news article coverage feeds and their summaries based on user queries.

Your primary responsibilities include:
1. Analyzing and curating relevant news articles based on user interests and queries
2. Providing concise, accurate summaries of news articles
3. Maintaining objectivity and factual accuracy in all content
4. Identifying key themes, trends, and important developments across multiple sources

"""
        
        if additional_instructions:
            self.base_prompt += f"\n\nAdditional Instructions:\n{additional_instructions}"
    
    def get_prompt(self) -> str:
        """Get the complete system prompt."""
        return self.base_prompt


class AIPrompt:
    """Manager for handling prompt messages with token counting and message stacking."""
    
    def __init__(self, system_prompt: SystemPrompt, model_name: Optional[str] = None):
        self.system_prompt = system_prompt
        self.messages: List[Message] = []
        self.model_name = model_name
        
        self._add_message(self.system_prompt.get_prompt(), MessageType.INIT)
    
    def _add_message(self, message: str, message_type: MessageType) -> MessageMetadata:
        token_count = count_tokens(message, self.model_name)
        
        metadata = MessageMetadata(
            message_type=message_type.value,
            tokens=token_count
        )
        
        self.messages.append(Message(message=message, metadata=metadata))

        return metadata
    
    def add_task_prompt(self, message: str) -> MessageMetadata:
        formatted_message = f"<Your current task>\n{message}\n</Your current task>"
        return self._add_message(formatted_message, MessageType.TASK)

    def get_prompt(self) -> str:
        return "\n".join([message.message for message in self.messages])