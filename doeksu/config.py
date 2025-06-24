from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Config(BaseSettings):
    """Settings for the application using Pydantic BaseSettings for environment variables."""
    
    # Logging
    LOG_LEVEL: str = Field(default="info")

    # API Keys
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    MISTRAL_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    GROK_API_KEY: Optional[str] = Field(default=None)
    
    ARTICLE_KEYWORDS_MIN_COUNT: int = Field(default=3, description="Minimum number of keywords per article")
    ARTICLE_KEYWORDS_MAX_COUNT: int = Field(default=5, description="Maximum number of keywords per article")
    ARTICLE_SUMMARY_MIN_WORD_COUNT: int = Field(default=200, description="Minimum number of words in article summary")
    ARTICLE_SUMMARY_MAX_WORD_COUNT: int = Field(default=400, description="Maximum number of words in article summary")
    

CONFIG = Config()

__all__ = ["CONFIG"]
