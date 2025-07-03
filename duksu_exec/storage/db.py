from datetime import datetime
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator, Dict, Optional

from duksu.news.model import NewsArticle
from duksu_exec.storage.objectstore import ObjectStore
from .model import NewsArticle as DBNewsArticle, NewsFeed
from ..config import CONFIG
from .model import Base


# Create engine
def create_db_engine():
    """Create database engine based on configuration."""
    database_url = CONFIG.DATABASE_URL
    
    engine = create_engine(database_url, echo=False)
    
    return engine


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_session_registry: Dict[str, Session] = {}


@contextmanager
def get_db_session(session_name: str = "default") -> Generator[Session, None, None]:
    """Get database session with automatic cleanup."""
    session = SessionLocal()
    _session_registry[session_name] = session
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db(session_name: str = "default") -> Session:
    """Get singleton database session by name."""
    if session_name in _session_registry:
        session = _session_registry[session_name]
        if session.is_active:
            return session
        else:
            _session_registry.pop(session_name, None)
    
    session = SessionLocal()
    _session_registry[session_name] = session
    return session


# ===============================
# Storage Helper Functions
# ===============================

class Storage:

    @classmethod
    async def store_news_article(cls, article: NewsArticle, session_name: Optional[str] = None) -> DBNewsArticle:
        """Store a news article in the database."""
        db = get_db(session_name) if session_name else get_db()
        object_store = ObjectStore(prefix=datetime.now().strftime("%Y-%m-%d"))

        html_path = None
        markdown_path = None

        if article.raw_html:
            html_path = await object_store.save_html(article.raw_html, article.url, filename=article.title)
        if article.content:
            markdown_path = await object_store.save_markdown(article.content, article.url, filename=article.title)

        # Create new article record
        db_article = DBNewsArticle(
            title=article.title,
            url=article.url,
            published_at=article.published_at,
            source=article.source,
            raw_html_path=html_path,
            content_markdown_path=markdown_path,
            thumbnail_url=article.thumbnail_url,
            summary=article.summary,
            keywords=json.dumps(article.keywords) if article.keywords else None,
            author=article.author
        )
        db.add(db_article)
        db.flush()

        return db_article

    @classmethod
    def get_news_article_by_url(cls, url: str, session_name: Optional[str] = None) -> NewsArticle | None:
        db = get_db(session_name) if session_name else get_db()
        db_article = db.query(DBNewsArticle).filter(
            DBNewsArticle.url == url
        ).first()

        if not db_article:
            return None

        keywords_json = getattr(db_article, 'keywords', None)
        return NewsArticle(
            title=getattr(db_article, 'title', ''),
            url=getattr(db_article, 'url', ''),
            thumbnail_url=getattr(db_article, 'thumbnail_url', None),
            published_at=getattr(db_article, 'published_at', 0),
            source=getattr(db_article, 'source', ''),
            summary=getattr(db_article, 'summary', None),
            keywords=json.loads(keywords_json) if keywords_json else None,
            author=getattr(db_article, 'author', None)
        )
