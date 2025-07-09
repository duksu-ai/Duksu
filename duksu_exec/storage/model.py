from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .enums import WorkflowRunStatus

Base = declarative_base()


class User(Base):
    """Model for storing users."""
    __tablename__ = "users"

    user_id = Column(String(255), primary_key=True, index=True)
    auth_id = Column(UUID(as_uuid=True), nullable=True, unique=True, index=True)  # For Supabase auth integration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to news feeds
    news_feeds = relationship("NewsFeed", back_populates="user")


class WorkflowRunHistory(Base):
    """Model for storing workflow run history."""
    __tablename__ = "workflow_run_history"

    id = Column(Integer, primary_key=True, index=True)
    workflow_name = Column(String(255), nullable=False, index=True)
    input_data = Column(Text, nullable=False)  # JSON string of input parameters
    output_data = Column(Text, nullable=True)  # JSON string of output/result
    status = Column(SQLEnum(WorkflowRunStatus), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class NewsFeed(Base):
    """Model for storing news feeds."""
    __tablename__ = "news_feeds"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), ForeignKey("users.user_id"), nullable=False, index=True)
    query_prompt = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="news_feeds")
    feed_items = relationship("NewsFeedItem", back_populates="news_feed", cascade="all, delete-orphan")


class NewsFeedItem(Base):
    """Model for storing news feed items with curation scores."""
    __tablename__ = "news_feed_items"

    id = Column(Integer, primary_key=True, index=True)
    news_feed_id = Column(Integer, ForeignKey("news_feeds.id"), nullable=False, index=True)
    news_article_id = Column(Integer, ForeignKey("news_articles.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    news_feed = relationship("NewsFeed", back_populates="feed_items")
    news_article = relationship("NewsArticle", back_populates="feed_items")


class NewsArticle(Base):
    """Model for storing news articles."""
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False, unique=True, index=True)
    published_at = Column(Integer, nullable=False)  # Unix timestamp
    source = Column(String(255), nullable=False, index=True)
    raw_html_path = Column(Text, nullable=True)  # Path to saved HTML file
    content_markdown_path = Column(Text, nullable=True)  # Path to saved markdown content file
    thumbnail_url = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    summary_short = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)  # JSON string of keywords list
    author = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to feed items
    feed_items = relationship("NewsFeedItem", back_populates="news_article")
