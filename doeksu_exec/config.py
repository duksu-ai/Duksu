from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration class for environment variables"""

    # Database Settings
    @property
    def DATABASE_URL(self) -> str:
        return os.getenv('DATABASE_URL', 'postgresql+psycopg2://username:password@localhost/doeksu_exec')

    # Logging
    @property
    def LOG_LEVEL(self) -> str:
        return os.getenv('LOG_LEVEL', 'info')

    # LLM Settings (inheriting from doeksu config)
    @property
    def MODEL_NAME(self) -> str:
        return os.getenv('MODEL_NAME', 'gemini-2.5-flash-preview-04-17')

    @property
    def OPENAI_API_KEY(self) -> Optional[str]:
        return os.getenv('OPENAI_API_KEY')

    @property
    def ANTHROPIC_API_KEY(self) -> Optional[str]:
        return os.getenv('ANTHROPIC_API_KEY')

    @property
    def GEMINI_API_KEY(self) -> Optional[str]:
        return os.getenv('GEMINI_API_KEY')

    @property
    def OLLAMA_BASE_URL(self) -> str:
        return os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')


CONFIG = Config()

__all__ = ["CONFIG"]
