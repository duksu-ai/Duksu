from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
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


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get database session with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Session:
    """Get database session (for dependency injection)."""
    return SessionLocal()
