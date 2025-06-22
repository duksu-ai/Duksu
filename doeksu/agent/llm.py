import logging
import os
from typing import Optional, Dict, Any, Literal, Type

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_mistral import ChatMistral
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from doeksu.settings import settings, logger


LLMType = Literal["openai", "anthropic", "gemini", "mistral", "grok"]

LLM_DEFAULTS = {
    "openai": {
        "class": ChatOpenAI,
        "default_model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
    },
    "anthropic": {
        "class": ChatAnthropic,
        "default_model": "claude-3-opus-20240229",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "gemini": {
        "class": ChatGoogleGenerativeAI,
        "default_model": "gemini-1.5-pro",
        "api_key_env": "GEMINI_API_KEY",
    },
    "mistral": {
        "class": ChatMistral,
        "default_model": "mistral-large-latest",
        "api_key_env": "MISTRAL_API_KEY",
    }
}

class LLMFactory:
    """Manager class for LLM interfaces."""
    
    @staticmethod
    def get_llm(
        provider: Optional[LLMType] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.0,
        streaming: bool = False,
        **additional_kwargs
    ) -> BaseChatModel:
        """
        Get a configured LLM instance based on available API keys.
        
        Args:
            provider: The LLM provider to use (optional, auto-detected if not provided)
            model_name: The specific model to use (optional, uses provider default if not provided)
            temperature: Temperature setting for model generation
            streaming: Whether to enable streaming responses
            **additional_kwargs: Additional parameters to pass to the LLM constructor
            
        Returns:
            A configured LangChain chat model instance
        """
        # Auto-detect provider if not specified
        if provider is None:
            provider = LLMFactory._auto_detect_provider()
            if provider is None:
                raise ValueError("No valid API keys found in environment or settings")
        
        # Verify API key is available
        api_key = LLMFactory._get_api_key(provider)
        if not api_key:
            raise ValueError(f"No API key found for {provider}")
        
        # Get provider configuration
        provider_config = LLM_DEFAULTS.get(provider)
        if not provider_config:
            raise ValueError(f"Unknown provider: {provider}")
        
        # If model_name not provided, use default for the provider
        if model_name is None:
            model_name = provider_config["default_model"]
        
        # Create LLM instance
        try:
            kwargs = {
                "model": model_name,
                "temperature": temperature,
                "streaming": streaming,
                **additional_kwargs
            }
            
            if provider == "openai" and api_key:
                kwargs["api_key"] = api_key
            elif provider == "anthropic" and api_key:
                kwargs["api_key"] = api_key
            elif provider == "gemini" and api_key:
                kwargs["google_api_key"] = api_key
            elif provider == "mistral" and api_key:
                kwargs["api_key"] = api_key
                
            return llm_class(**kwargs)
            
        except Exception as e:
            logger.error(f"Failed to initialize {provider} LLM: {str(e)}")
            raise
    
    @staticmethod
    def _auto_detect_provider() -> Optional[LLMType]:
        """Auto-detect available provider based on API keys."""
        for provider, config in LLM_DEFAULTS.items():
            if LLMFactory._get_api_key(provider):
                logger.info(f"Auto-detected {provider} API key")
                return provider
        return None
    
    @staticmethod
    def _get_api_key(provider: LLMType) -> Optional[str]:
        """Get API key for a provider from settings or environment."""
        env_var = LLM_DEFAULTS[provider]["api_key_env"]
        
        # Try to get from settings first
        api_key = getattr(settings, env_var, None)
        
        # If not in settings, try environment variable
        if not api_key:
            api_key = os.environ.get(env_var)
            
        return api_key
    
    @staticmethod
    def list_available_providers() -> Dict[LLMType, bool]:
        """List all providers and whether they have API keys available."""
        return {
            provider: bool(LLMFactory._get_api_key(provider)) 
            for provider in LLM_DEFAULTS.keys()
        }
        
    @staticmethod
    def get_default_model(provider: LLMType) -> str:
        """Get the default model name for a provider."""
        return LLM_DEFAULTS[provider]["default_model"]

# Convenient factory functions for specific providers
def get_openai_llm(model_name: Optional[str] = None, temperature: float = 0.0, **kwargs) -> ChatOpenAI:
    """Get an OpenAI LLM instance."""
    return LLMFactory.get_llm("openai", model_name, temperature, **kwargs)

def get_anthropic_llm(model_name: Optional[str] = None, temperature: float = 0.0, **kwargs) -> ChatAnthropic:
    """Get an Anthropic LLM instance."""
    return LLMFactory.get_llm("anthropic", model_name, temperature, **kwargs)

def get_gemini_llm(model_name: Optional[str] = None, temperature: float = 0.0, **kwargs) -> ChatGoogleGenerativeAI:
    """Get a Google Gemini LLM instance."""
    return LLMFactory.get_llm("gemini", model_name, temperature, **kwargs)

def get_mistral_llm(model_name: Optional[str] = None, temperature: float = 0.0, **kwargs) -> ChatMistral:
    """Get a Mistral LLM instance."""
    return LLMFactory.get_llm("mistral", model_name, temperature, **kwargs)
