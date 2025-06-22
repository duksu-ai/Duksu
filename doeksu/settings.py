from pydantic import BaseSettings, Field
from typing import Optional
import os
from pathlib import Path
import logging
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Settings for the application using Pydantic BaseSettings for environment variables."""
    
    # Logging
    LOG_LEVEL: str = Field(default="info")

    # API Keys
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    MISTRAL_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    GROK_API_KEY: Optional[str] = Field(default=None)
    
    LANGSMITH_API_KEY: Optional[str] = Field(default=None)
    
    class Config:
        env_file = os.path.join(BASE_DIR, ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True


def configure_logger():
    logger = logging.getLogger("doeksu")
    log_level = getattr(logging, settings.LOG_LEVEL.upper())
    logger.setLevel(log_level)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

settings = Settings()
logger = configure_logger()

__all__ = ["settings", "logger"]
