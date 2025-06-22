from langchain_core.tools import tool
import requests
from typing import List, Optional
import os
from datetime import datetime


@tool
def fetch_trending_tech_news(categories: Optional[List[str]] = None, period: str = "daily", limit: int = 5) -> str:
    """Fetch trending tech news from Hackerrank.
    
    Args:
        categories: List of tech categories to search [e.g., 'ai', 'web', 'mobile', 'cloud', 'data_science'].
                   Default is all categories.
        period: Time period for analysis - 'daily', 'weekly', or 'monthly'. Default is 'daily'.
        limit: Number of news items per category. Default is 5.
        
    Returns:
        Formatted report with trending tech news.
    """
    # Mock implementation - replace with actual Hackerrank API call
    trending_news = {
        "ai": [
            {"title": "New GPT-5 Breakthrough", "url": "https://hackerrank.com/news/gpt5", "votes": 320},
            {"title": "AI Ethics Framework Released", "url": "https://hackerrank.com/news/ai-ethics", "votes": 245}
        ],
        "web": [
            {"title": "Next.js 14 Features", "url": "https://hackerrank.com/news/nextjs14", "votes": 198},
            {"title": "WebAssembly for Frontend", "url": "https://hackerrank.com/news/wasm-frontend", "votes": 176}
        ]
    }
    
    # Format the response
    response = "# Trending Tech News\n\n"
    for category, news_items in trending_news.items():
        if categories and category not in categories:
            continue
        response += f"## {category.upper()}\n\n"
        for idx, item in enumerate(news_items[:limit], 1):
            response += f"{idx}. **{item['title']}**\n"
            response += f"   - Votes: {item['votes']}\n"
            response += f"   - Link: [{item['title']}]({item['url']})\n\n"
            
    return response


@tool
def search_tech_topics(keyword: str, source: str = None, period: str = "daily", limit: int = 10) -> str:
    """Search for specific tech topics on Hackerrank.
    
    Args:
        keyword: Tech topic to search for (e.g., "React", "Python", "DevOps")
        source: Optional filter for news source
        period: Time period - 'daily', 'weekly', or 'monthly'. Default is 'daily'.
        limit: Maximum number of results to return. Default is 10.
        
    Returns:
        Formatted report of tech news related to the keyword.
    """
    # Mock implementation - replace with actual Hackerrank API call
    search_results = [
        {"title": f"{keyword} Latest Developments", "url": f"https://hackerrank.com/news/{keyword.lower()}", "votes": 287},
        {"title": f"How {keyword} is Changing Tech", "url": f"https://hackerrank.com/news/{keyword.lower()}-impact", "votes": 212},
        {"title": f"Learning {keyword} in 2023", "url": f"https://hackerrank.com/news/learn-{keyword.lower()}", "votes": 198}
    ]
    
    response = f"# Search Results for '{keyword}'\n\n"
    for idx, item in enumerate(search_results[:limit], 1):
        response += f"{idx}. **{item['title']}**\n"
        response += f"   - Votes: {item['votes']}\n"
        response += f"   - Link: [{item['title']}]({item['url']})\n\n"
        
    return response


@tool
def read_notes() -> str:
    """Read the current tech news notes file.
    
    Returns:
        The current contents of the notes file.
    """
    notes_file = get_or_create_notes_file()
    
    try:
        with open(notes_file, "r") as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading notes file: {str(e)}"


@tool
def write_notes(content: str, section: str = "General") -> str:
    """Write content to the tech news notes file under a specific section.
    
    Args:
        content: The content to write to the notes
        section: The section heading to place the content under
        
    Returns:
        Confirmation message.
    """
    notes_file = get_or_create_notes_file()
    
    try:
        existing_content = ""
        try:
            with open(notes_file, "r") as f:
                existing_content = f.read()
        except FileNotFoundError:
            pass
        
        section_header = f"## {section}"
        if section_header in existing_content:
            lines = existing_content.split("\n")
            with open(notes_file, "w") as f:
                section_found = False
                for line in lines:
                    f.write(line + "\n")
                    if line == section_header:
                        section_found = True
                        f.write(f"\n{content}\n\n")
                
                if not section_found:
                    f.write(f"\n## {section}\n\n{content}\n\n")
        else:
            with open(notes_file, "a") as f:
                f.write(f"\n## {section}\n\n{content}\n\n")
        
        return f"Successfully added to tech news notes under section '{section}'."
    except Exception as e:
        return f"Error writing to notes file: {str(e)}"


# Helper functions
def get_or_create_notes_file():
    """Get the current notes file path or create a new one."""
    notes_dir = "tech_news_notes"
    os.makedirs(notes_dir, exist_ok=True)
    
    notes_file = os.path.join(notes_dir, "tech_news_notes.md")
    
    if not os.path.exists(notes_file):
        with open(notes_file, "w") as f:
            f.write(f"# Tech News Notes - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    return notes_file


