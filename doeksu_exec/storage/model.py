from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from .enums import WorkflowRunStatus

Base = declarative_base()


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


class NewsSourceMapping(Base):
    """Model for storing news source mappings to query prompts."""
    __tablename__ = "news_source_mappings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    query_prompt = Column(Text, nullable=False)
    selected_sources = Column(Text, nullable=False)  # JSON string of selected source names
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
