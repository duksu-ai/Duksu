from typing import List, Dict, Any, Optional, Type, Callable, cast, get_type_hints, Union
from dataclasses import dataclass
import asyncio
import re
import time
from inspect import iscoroutinefunction, signature
from pathlib import Path

from langchain_core.language_models import BaseLanguageModel
from duksu.agent.prompts import AIPrompt, SystemPrompt
from duksu.config import CONFIG
from duksu.news.model import NewsArticle
from pydantic import BaseModel, Field
from duksu.logging_config import create_logger
from duksu.utils.time import parse_age_literal_to_seconds


@dataclass
class NewsSource:
    """Information about a registered news source function."""
    source_function: Callable
    source_name: str
    description: str
    param_model: Optional[Type[BaseModel]] = None


class NewsSearchPlan(BaseModel):
    """Plan for executing a news source with parameters."""
    source_name: str = Field(description="Name of the news source to search")
    parameters: str = Field(default="{}", description="Parameters to pass to the news search function as JSON string")
    reasoning: str = Field(description="Why this source was selected and how parameters were determined")

class NewsSearchPlanList(BaseModel):
    """List of execution plans for a news search."""
    search_plans: List[NewsSearchPlan] = Field(description="List of source and parameters for a news search")


class NewsSourceRegistry:
    """Registry for managing news source functions."""
    
    _sources: Dict[str, NewsSource] = {}
    logger = create_logger("NewsSourceRegistry")
    
    @classmethod
    def _validate_source_function(cls, func: Callable, param_model: Optional[Type[BaseModel]] = None) -> None:
        """Validate that the function can work with the given parameter model (Pydantic)."""
        try:
            sig = signature(func)
            parameters = list(sig.parameters.values())
            
            if param_model is not None:
                if not (hasattr(param_model, '__bases__') and 
                       any(issubclass(base, BaseModel) for base in param_model.__mro__)):
                    raise ValueError(f"Parameter model {param_model.__name__} must be a Pydantic BaseModel")
                
                # Check if function expects parameters when param_model is provided
                if len(parameters) == 0:
                    raise ValueError(f"Function {func.__name__} has no parameters but param_model {param_model.__name__} was provided")
                
                # Check if first parameter can accept the param_model
                first_param = parameters[0]
                if first_param.annotation != first_param.empty:
                    if first_param.annotation != param_model:
                        # Check if it's compatible (same base or inheritance)
                        if not (hasattr(first_param.annotation, '__mro__') and 
                               param_model in first_param.annotation.__mro__):
                            cls.logger.warning(f"Function {func.__name__} parameter type {first_param.annotation} may not match param_model {param_model}")
            else:
                # If no param_model, function should either have no params or have default values
                required_params = [p for p in parameters if p.default == p.empty]
                if required_params:
                    cls.logger.warning(f"Function {func.__name__} has required parameters {[p.name for p in required_params]} but no param_model provided")
                    
        except Exception as e:
            cls.logger.warning(f"Could not validate function {func.__name__} with param_model: {e}")

    @classmethod
    def _get_news_source_description_prompt(cls) -> str:
        """
        Get a description of all news sources for AI prompts.
        """
        sources = NewsSourceRegistry.get_all_sources()
        
        prompt_parts = [
            "AVAILABLE NEWS SOURCES:",
            "Each source below can be executed with specific parameters. Choose the most relevant source(s) based on the user's query.",
            ""
        ]
        
        for source_name, source in sources.items():
            source_desc = [f"SOURCE: {source_name}"]
            source_desc.append(f"DESCRIPTION: {source.description}")
            
            # Add parameter information if available
            if source.param_model:
                if not hasattr(source.param_model, 'model_fields'):
                    raise ValueError(f"Parameter model {source.param_model.__name__} is not a Pydantic model")

                param_info = []
                for field_name, field_info in source.param_model.model_fields.items():
                    field_type = getattr(field_info.annotation, '__name__', str(field_info.annotation))
                    field_desc = field_info.description or "No description provided"
                    default_val = f"[Default: {field_info.default}]" if field_info.default is not None else "[Required]"
                    
                    param_info.append(f"  - {field_name} ({field_type}): {field_desc} {default_val}")
                    
                if param_info:
                    source_desc.append("PARAMETERS:")
                    source_desc.extend(param_info)
                else:
                    source_desc.append("PARAMETERS: None required")
            else:
                source_desc.append("PARAMETERS: None required")
            
            source_desc.append("USAGE: Select this source if it can be utilized to answer the user's query.")
            prompt_parts.append("\n".join(source_desc))
            prompt_parts.append("")  # Empty line between sources
        
        prompt_parts.extend([
            "PARAMETER FORMULATION:",
            "Provide parameters as key-value in JSON string based on the user's specific requirements.",
            "",
            "IMPORTANT: The number of sources chosen should not exceed the configured max number of news sources ({CONFIG.ARTICLE_REGISTRY_MAX_NEWS_SOURCES})",
            "",
            "EXECUTION GUIDELINES:",
            f"1. Choose up to {CONFIG.ARTICLE_REGISTRY_MAX_NEWS_SOURCES} source(s) that best match the user's news query intent",
            "2. Parameter optimization: For search-based sources, extract relevant keywords from the user's query",
            "3. Provide clear reasoning for your source selection and parameter choices",
            "4. Multiple sources can be used if the query spans different topics or requires comprehensive coverage",
            "5. Override default parameters if needed to get more relevant results"
        ])
        
        return "\n".join(prompt_parts)

    @classmethod
    def _filter_articles_by_age(cls, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Filter articles based on configured age cap."""
        age_cap = CONFIG.ARTICLE_COLLECTION_AGE_CAP
        if not age_cap:
            return articles
        
        try:
            max_age_seconds = parse_age_literal_to_seconds(age_cap)
            current_timestamp = int(time.time())
            cutoff_timestamp = current_timestamp - max_age_seconds
            
            filtered_articles = [
                article for article in articles 
                if article.published_at >= cutoff_timestamp
            ]
            
            return filtered_articles
            
        except ValueError as e:
            cls.logger.error(f"Error parsing age cap '{age_cap}': {e}. Returning all articles.")
            return articles

    @classmethod
    def register(cls, source_name: str, description: str, param_model: Optional[Type[BaseModel]] = None):
        """
        Decorator to register a news source function.
        """
        def decorator(func: Callable) -> Callable:
            cls._validate_source_function(func, param_model)
            
            if not iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    return await asyncio.to_thread(func, *args, **kwargs)
                
                async_wrapper.__signature__ = signature(func)
                async_wrapper.__name__ = func.__name__
                async_wrapper.__annotations__ = func.__annotations__
                wrapped_func = async_wrapper
            else:
                wrapped_func = func
            
            cls._sources[source_name] = NewsSource(
                source_function=wrapped_func,
                source_name=source_name,
                description=description,
                param_model=param_model
            )
            
            return func
        return decorator
    
    @classmethod
    async def retrieve_news_articles_from_source(
        cls, 
        source_name: str, 
        params: Dict[str, Any]
    ) -> List[NewsArticle]:
        """
        Execute a registered news source function with parameters.
        """
        if source_name not in cls._sources:
            raise ValueError(f'News source {source_name} not found')
        
        source = cls._sources[source_name]
        articles = []

        try:
            if source.param_model:
                validated_params = source.param_model(**params)
                
                sig = signature(source.source_function)
                parameters = list(sig.parameters.values())
                
                first_param = parameters[0]
                is_pydantic_param = (
                    hasattr(first_param.annotation, '__bases__') and 
                    any(issubclass(base, BaseModel) for base in first_param.annotation.__bases__)
                ) if first_param.annotation != first_param.empty else False
                
                if is_pydantic_param:
                    articles = await source.source_function(validated_params)
                else:
                    articles = await source.source_function(**validated_params.model_dump())

            else:
                articles = await source.source_function()
            
            filtered_articles = cls._filter_articles_by_age(articles)
            cls.logger.info(f"Retrieved total {len(articles)} articles from {source_name}, dropped old (AGE_CAP: {CONFIG.ARTICLE_COLLECTION_AGE_CAP}) {len(articles) - len(filtered_articles)} articles.")
            return filtered_articles
                
        except Exception as e:
            raise RuntimeError(f'Error executing news source {source_name}: {str(e)}') from e
    
    @classmethod
    def get_all_sources(cls) -> Dict[str, NewsSource]:
        """Get all registered news sources."""
        sources = cls._sources.copy()
        if not sources:
            raise ValueError("No news sources registered")
        
        return sources

    @classmethod
    def get_source_by_name(cls, source_name: str) -> Optional[NewsSource]:
        """Get a news source by name."""
        return cls._sources.get(source_name)

    @classmethod
    async def get_news_search_plans(cls, llm: BaseLanguageModel, query_prompt: str, system_prompt: SystemPrompt = SystemPrompt()) -> NewsSearchPlanList:  
        structured_llm = llm.with_structured_output(NewsSearchPlanList)

        prompt = AIPrompt(system_prompt)
        prompt.add_task_prompt(f"""
        You are a news search planner. Given a user query, create a complete execution plan that includes:
        1. Which news sources to use
        2. What parameters to pass to each source
        3. Reasoning for each selection

        Available news source executor descriptions:
        {cls._get_news_source_description_prompt()}

        User Query Prompt: I want to know about {query_prompt}

        IMPORTANT: You can use the same source multiple times with different parameters to get comprehensive coverage.

        For example, if the query is about "AI and climate change", you could use:
        - Google News Search with search_keyword="artificial intelligence"
        - Google News Search with search_keyword="climate change AI"
        - Google News Technology (for general tech coverage)

        """)
        prompt.add_task_prompt(f"User Query: {query_prompt}")
        response = cast(NewsSearchPlanList, await structured_llm.ainvoke(prompt.get_prompt()))
        
        if len(response.search_plans) > CONFIG.ARTICLE_REGISTRY_MAX_NEWS_SOURCES:
            cls.logger.warning(f"Number of news search plans ({len(response.search_plans)}) exceeds configured max number of news sources ({CONFIG.ARTICLE_REGISTRY_MAX_NEWS_SOURCES})")

        return response



def news_source(source_name: str, description: str, param_model: Optional[Type[BaseModel]] = None):
    """
    Decorator for registering news source functions.
    
    Usage:
        # Simple source with no parameters:
        @news_source(
            source_name="Simple News",
            description="Simple news source with no parameters"
        )
        async def simple_news() -> List[NewsArticle]:
            # Implementation
            pass
            
        # Source with parameter model:
        @news_source(
            source_name="Google News Search",
            description="Custom keyword search from Google News RSS",
            param_model=GoogleNewsSearchParam
        )
        async def google_news_search(param: GoogleNewsSearchParam) -> List[NewsArticle]:
            # Implementation with explicit parameter model
            pass
    """
    return NewsSourceRegistry.register(source_name, description, param_model)
