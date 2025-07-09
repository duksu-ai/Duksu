from typing import Optional
import os
import sys
import langchain_openai
import langchain_anthropic
import langchain_google_genai
import langchain_ollama
from langchain_core.rate_limiters import InMemoryRateLimiter
from dotenv import load_dotenv

load_dotenv()


class Config:
    """configuration class for environment variable"""

    # Logging
    @property
    def LOG_LEVEL(self) -> str:
        return os.getenv('LOG_LEVEL', 'info')

    # LLM Settings
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

    # News Collection Settings
    @property
    def ARTICLE_COLLECTION_AGE_CAP(self) -> str:
        return os.getenv('ARTICLE_COLLECTION_AGE_CAP', '30d')

    @property
    def ARTICLE_REGISTRY_MAX_NEWS_SOURCES(self) -> int:
        return int(os.getenv('ARTICLE_REGISTRY_MAX_NEWS_SOURCES', '3'))

    @property
    def ARTICLE_KEYWORDS_MIN_COUNT(self) -> int:
        return int(os.getenv('ARTICLE_KEYWORDS_MIN_COUNT', '3'))

    @property
    def ARTICLE_KEYWORDS_MAX_COUNT(self) -> int:
        return int(os.getenv('ARTICLE_KEYWORDS_MAX_COUNT', '5'))

    @property
    def ARTICLE_SUMMARY_MIN_WORD_COUNT(self) -> int:
        return int(os.getenv('ARTICLE_SUMMARY_MIN_WORD_COUNT', '100'))

    @property
    def ARTICLE_SUMMARY_MAX_WORD_COUNT(self) -> int:
        return int(os.getenv('ARTICLE_SUMMARY_MAX_WORD_COUNT', '200'))


CONFIG = Config()


def get_llm(model_name: Optional[str] = None, temperature: float = 0.0, rate_limiter: Optional[InMemoryRateLimiter] = None):
    """Get the language model based on config."""

    model_name = model_name or CONFIG.MODEL_NAME or "gemini-2.5-flash-preview-04-17"

    # Set environment variables if they're in the config but not in the environment
    if CONFIG.OPENAI_API_KEY:
        os.environ['OPENAI_API_KEY'] = CONFIG.OPENAI_API_KEY
    if CONFIG.ANTHROPIC_API_KEY:
        os.environ['ANTHROPIC_API_KEY'] = CONFIG.ANTHROPIC_API_KEY
    if CONFIG.GEMINI_API_KEY:
        os.environ['GOOGLE_API_KEY'] = CONFIG.GEMINI_API_KEY

    if model_name.startswith('gpt'):
        if not CONFIG.OPENAI_API_KEY:
            print('⚠️  OpenAI API key not found or langchain-openai not installed. Please update your config or set OPENAI_API_KEY environment variable.')
            sys.exit(1)
        return langchain_openai.ChatOpenAI(model=model_name, temperature=temperature, rate_limiter=rate_limiter)
    elif model_name.startswith('claude'):
        if not CONFIG.ANTHROPIC_API_KEY:
            print('⚠️  Anthropic API key not found or langchain-anthropic not installed. Please update your config or set ANTHROPIC_API_KEY environment variable.')
            sys.exit(1)
        return langchain_anthropic.ChatAnthropic(model_name=model_name, temperature=temperature, timeout=30, stop=None, rate_limiter=rate_limiter)
    elif model_name.startswith('gemini'):
        if not CONFIG.GEMINI_API_KEY:
            print('⚠️  Google API key not found or langchain-google-genai not installed. Please update your config or set GEMINI_API_KEY environment variable.')
            sys.exit(1)
        return langchain_google_genai.ChatGoogleGenerativeAI(model=model_name, temperature=temperature, rate_limiter=rate_limiter)
    elif model_name.startswith('ollama-'):
        # Support for Ollama models with ollama- prefix
        actual_model_name = model_name[7:]  # Remove 'ollama-' prefix
        try:
            return langchain_ollama.ChatOllama(
                model=actual_model_name,
                temperature=temperature,
                base_url=CONFIG.OLLAMA_BASE_URL,
                rate_limiter=rate_limiter
            )
        except Exception as e:
            print(f'⚠️  Failed to connect to Ollama at {CONFIG.OLLAMA_BASE_URL}. Make sure Ollama is running and the model "{actual_model_name}" is available.')
            print(f'   Error: {e}')
            sys.exit(1)
    else:
        raise ValueError(f"Unsupported model: {model_name}.")


__all__ = ["CONFIG", "get_llm"]
