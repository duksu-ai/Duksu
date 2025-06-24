from typing import List, Dict, Any, Optional, Type, Callable, get_type_hints
from dataclasses import dataclass
import inspect
from doeksu.news.model import NewsArticle
from langchain.schema.language_model import BaseLanguageModel
from pydantic import BaseModel, Field
from doeksu.logging_config import logger


@dataclass
class NewsSource:
    """Information about a registered news source function."""
    source_function: Callable
    source_name: str
    description: str
    param_type: Optional[Type] = None


class NewsSourceSelection(BaseModel):
    """Pydantic model for structured news source selection."""
    selected_sources: List[str] = Field(description="List of news source names that are most relevant to the query")


class NewsSourceRegistry:
    """Registry for managing news source functions."""
    
    _sources: Dict[str, NewsSource] = {}
    
    @classmethod
    def register(cls, source_name: str, description: str, param_type: Optional[Type] = None):
        """
        Decorator to register a news source function.
        
        Args:
            source_name: Name of the news source
            description: What this news source provides
            param_type: Optional parameter type for validation
        """
        def decorator(func: Callable) -> Callable:
            # Validate function signature and return type
            cls._validate_function(func)
            
            cls._sources[source_name] = NewsSource(
                source_function=func,
                source_name=source_name,
                description=description,
                param_type=param_type
            )
            
            return func
        return decorator
    
    @classmethod
    def _validate_function(cls, func: Callable) -> None:
        """Validate that the function returns List[NewsArticle]."""
        try:
            type_hints = get_type_hints(func)
            return_type = type_hints.get('return')
            
            # Check if return type is List[NewsArticle]
            if return_type is not None:
                if hasattr(return_type, '__origin__') and return_type.__origin__ is list:
                    if hasattr(return_type, '__args__') and return_type.__args__:
                        if return_type.__args__[0] is not NewsArticle:
                            raise ValueError(f"Function {func.__name__} must return List[NewsArticle], got {return_type}")
                else:
                    # Check if it's a coroutine that returns List[NewsArticle]
                    if inspect.iscoroutinefunction(func):
                        # For async functions, we need to check differently
                        pass  # Will validate at runtime
                    else:
                        raise ValueError(f"Function {func.__name__} must return List[NewsArticle]")
                    
        except Exception as e:
            print(f"Warning: Could not validate return type for {func.__name__}: {e}")
    
    @classmethod
    def get_all_sources(cls) -> Dict[str, NewsSource]:
        """Get all registered news sources."""
        return cls._sources.copy()

    @classmethod
    def get_source_by_name(cls, source_name: str) -> NewsSource:
        """Get a news source by name."""
        source = cls._sources.get(source_name)
        if source is None:
            raise ValueError(f"News source {source_name} not found")
        return source
    
    @classmethod
    async def search_sources(cls, llm_model: BaseLanguageModel, query_prompt: str) -> Dict[str, NewsSource]:
        if not cls._sources:
            logger.warning("No news sources registered")
            return {}
        
        # Create structured LLM for source selection
        structured_llm = llm_model.with_structured_output(NewsSourceSelection)
        
        sources_info = []
        for source_name, source in cls._sources.items():
            sources_info.append(f"- {source_name}: {source.description}")
        
        sources_list = "\n".join(sources_info)
        
        selection_prompt = f"""
You are a news source selection assistant. Given a user query, select the most relevant news sources from the available options.

User Query: {query_prompt}

Available News Sources:
{sources_list}

Please analyze the user query and select the news sources that are most likely to contain relevant articles. Consider:
1. Topic relevance (e.g., if query is about technology, select tech-related sources)
2. Source coverage (e.g., general sources vs. specialized sources)
3. If the query is very general, you can select more sources. If it's very specific, select fewer but more targeted sources.
"""
            
        response = await structured_llm.ainvoke(selection_prompt)
        
        if isinstance(response, NewsSourceSelection):
            # Filter and return selected sources
            selected_sources = {}
            for source_name in response.selected_sources:
                if source_name in cls._sources:
                    selected_sources[source_name] = cls._sources[source_name]
                else:
                    # Try to find by partial match if exact match fails
                    for registered_name, source in cls._sources.items():
                        if source_name.lower() in registered_name.lower():
                            selected_sources[registered_name] = source
                            break
            
            return selected_sources
        else:
            raise ValueError(f"Unexpected response type while selecting news sources: {type(response)}")
                


def news_source(source_name: str, description: str, param_type: Optional[Type] = None):
    """
    decorator for registering news source functions.
    
    Args:
        source_name: Name of the news source
        description: What this news source provides
        param_type: Optional parameter type for validation
    
    Usage:
        @news_source(
            source_name="Google Tech News",
            description="Technology news from Google News RSS"
        )
        async def google_tech_news() -> List[NewsArticle]:
            # Implementation
            pass
    """
    return NewsSourceRegistry.register(source_name, description, param_type)
