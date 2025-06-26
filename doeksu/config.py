from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Any
import os
import sys
import langchain_openai
import langchain_anthropic
import langchain_google_genai
import langchain_ollama
from dotenv import load_dotenv


load_dotenv()

class Config(BaseSettings):
    """Settings for the application using Pydantic BaseSettings for environment variables."""
    
    # Logging
    LOG_LEVEL: str = Field(default="info")

    # LLM Settings
    MODEL_NAME: str = Field(default="gemini-2.5-flash-preview-04-17", description="Default model name")
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama server base URL")
    
    # Storage Settings
    POSTGRES_DATABASE_URL: Optional[str] = Field(default=None, description="PostgreSQL connection string")

    S3_BUCKET_NAME: Optional[str] = Field(default=None, description="S3 bucket name")
    S3_ENDPOINT_URL: Optional[str] = Field(default=None, description="S3 endpoint URL (for S3-compatible services like MinIO)")
    S3_ACCESS_KEY: Optional[str] = Field(default=None, description="S3 access key ID")
    S3_SECRET_KEY: Optional[str] = Field(default=None, description="S3 secret access key")
    S3_REGION: str = Field(default="us-east-1", description="S3 region")
    
    # News Collection Settings
    ARTICLE_KEYWORDS_MIN_COUNT: int = Field(default=3, description="Minimum number of keywords per article")
    ARTICLE_KEYWORDS_MAX_COUNT: int = Field(default=5, description="Maximum number of keywords per article")
    ARTICLE_SUMMARY_MIN_WORD_COUNT: int = Field(default=200, description="Minimum number of words in article summary")
    ARTICLE_SUMMARY_MAX_WORD_COUNT: int = Field(default=400, description="Maximum number of words in article summary")
    ARTICLE_PARSER_HTML_CHUNK_TOKEN_SIZE: int = Field(default=100000, description="Maximum token size of HTML chunk for article parser")
    ARTICLE_PARSER_CONTENT_MAX_TOKEN_LENGTH: int = Field(default=100000, description="Maximum token length of article content for article parser")


def get_llm(model_name: Optional[str] = None, temperature: float = 0.0):
    """Get the language model based on config."""

    model_name = model_name or CONFIG.MODEL_NAME or "gemini-2.5-flash-preview-04-17"

    # Set environment variables if they're in the config but not in the environment
    if CONFIG.OPENAI_API_KEY:
        os.environ['OPENAI_API_KEY'] = CONFIG.OPENAI_API_KEY
    if CONFIG.ANTHROPIC_API_KEY:
        os.environ['ANTHROPIC_API_KEY'] = CONFIG.ANTHROPIC_API_KEY
    if CONFIG.GEMINI_API_KEY:
        os.environ['GOOGLE_API_KEY'] = CONFIG.GEMINI_API_KEY

    if model_name:
        if model_name.startswith('gpt'):
            if not CONFIG.OPENAI_API_KEY:
                print('⚠️  OpenAI API key not found or langchain-openai not installed. Please update your config or set OPENAI_API_KEY environment variable.')
                sys.exit(1)
            return langchain_openai.ChatOpenAI(model=model_name, temperature=temperature)
        elif model_name.startswith('claude'):
            if not CONFIG.ANTHROPIC_API_KEY:
                print('⚠️  Anthropic API key not found or langchain-anthropic not installed. Please update your config or set ANTHROPIC_API_KEY environment variable.')
                sys.exit(1)
            return langchain_anthropic.ChatAnthropic(model_name=model_name, temperature=temperature, timeout=30, stop=None)
        elif model_name.startswith('gemini'):
            if not CONFIG.GEMINI_API_KEY:
                print('⚠️  Google API key not found or langchain-google-genai not installed. Please update your config or set GEMINI_API_KEY environment variable.')
                sys.exit(1)
            return langchain_google_genai.ChatGoogleGenerativeAI(model=model_name, temperature=temperature)
        elif model_name.startswith('ollama-'):
            # Support for Ollama models with ollama- prefix
            actual_model_name = model_name[7:]  # Remove 'ollama-' prefix
            try:
                return langchain_ollama.ChatOllama(
                    model=actual_model_name,
                    temperature=temperature,
                    base_url=CONFIG.OLLAMA_BASE_URL
                )
            except Exception as e:
                print(f'⚠️  Failed to connect to Ollama at {CONFIG.OLLAMA_BASE_URL}. Make sure Ollama is running and the model "{actual_model_name}" is available.')
                print(f'   Error: {e}')
                sys.exit(1)
        else:
            raise ValueError(f"Unsupported model: {model_name}.")


CONFIG = Config()

__all__ = ["CONFIG", "get_llm"]
