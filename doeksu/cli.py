import asyncio
import argparse
from typing import List, Optional, Union
from doeksu.news import NewsSource
from doeksu.config import CONFIG
from doeksu.logging_config import logger


class CLI:
    """Command Line Interface for the news collection system."""
    
    def __init__(self):
        self.parser = self._setup_parser()
    
    def _setup_parser(self) -> argparse.ArgumentParser:
        """Setup the argument parser."""
        parser = argparse.ArgumentParser(
            description="Automated News Collection using LangGraph"
        )
        
        parser.add_argument(
            "--topic",
            type=str,
            required=True,
            help="Topic prompt for news collection"
        )
        
        parser.add_argument(
            "--sources",
            type=str,
            nargs="+",
            required=True,
            help="News sources to collect from"
        )
        
        parser.add_argument(
            "--llm-model",
            type=str,
            default="gpt-3.5-turbo",
            help="LLM model to use for processing"
        )
        
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of articles per source"
        )
        
        parser.add_argument(
            "--output",
            type=str,
            help="Output file path (optional)"
        )
        
        return parser
    
    async def _execute_workflow(
        self,
        news_sources: List[NewsSource],
        topic: str,
        llm_model: str,
        limit: int,
        output: Optional[str]
    ) -> None:
        """Execute the news collection workflow."""
        # TODO: Implement LangGraph workflow execution
        logger.info("Workflow execution not yet implemented")
        
        # Placeholder for workflow steps:
        # 1. Collect news from sources
        # 2. Filter and process with LLM
        # 3. Assess relevance
        # 4. Aggregate results
        # 5. Output results
        
        for source in news_sources:
            logger.info(f"Collecting from {source.name}...")
            # articles = await source.collect_news(topic, limit)
            # TODO: Process articles through workflow
    
    def run(self, args: Optional[List[str]] = None) -> None:
        """Run the CLI with provided arguments."""
        parsed_args = self.parser.parse_args(args)
        
        # TODO: Parse source strings and create NewsSource instances
        # This will be implemented once we have the concrete source classes
        logger.info("CLI run method not fully implemented yet")
        logger.info(f"Parsed arguments: {parsed_args}")

    async def run_news_collection(
        self,
        news_sources: Union[NewsSource, List[NewsSource]],
        topic: str,
        llm_model: str = "gpt-3.5-turbo",
        limit: int = 10,
        output: Optional[str] = None
    ) -> None:
        """
        Run the news collection workflow.
        
        Args:
            news_sources: Single news source or list of news sources
            topic: Topic prompt for news collection
            llm_model: LLM model to use for processing
            limit: Maximum number of articles per source
            output: Optional output file path
        """
        logger.info(f"Starting news collection for topic: {topic}")
        logger.info(f"Using LLM model: {llm_model}")
        
        # Ensure news_sources is a list
        if isinstance(news_sources, NewsSource):
            news_sources = [news_sources]
        
        logger.info(f"Collecting from {len(news_sources)} source(s):")
        for source in news_sources:
            logger.info(f"  - {source}")
        
        # TODO: Implement the actual workflow
        # This will integrate with LangGraph workflow
        await self._execute_workflow(news_sources, topic, llm_model, limit, output)


def main():
    """Main entry point for the CLI."""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
