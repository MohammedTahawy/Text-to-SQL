# ==============================================================================
# Database Connection & Query Execution Engine
# Path: app/core/database.py
# Related Architecture Document: PROJECT_NOTES_FOR_KHALED.md (Section 3 & 4)
# Purpose: Manages database connections using SQLAlchemy connection pooling
#          (supporting embedded SQLite locally and MySQL/MariaDB in production)
#          and executes read-only queries safely using parameterized execution.
# ==============================================================================

# Standard logging library
import logging

# Typing utilities
from typing import Any, Dict, List

# create_engine: Establishes database engine and pool management
# text: Constructs parameterized SQL statement objects to prevent SQL injection
from sqlalchemy import create_engine, text

# sessionmaker: Factory for creating ORM/Core database sessions
# Session: Database session instance interface
from sqlalchemy.orm import sessionmaker, Session

# Application configuration instance
from app.config import settings

# Logger instance for database operations
logger = logging.getLogger(__name__)

# Extract dynamic connection URL from settings
db_url = settings.database_url

# Configure database engine based on dialect:
if db_url.startswith("sqlite"):
    # SQLite configuration:
    # check_same_thread=False allows multiple worker threads in FastAPI to read SQLite concurrently
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}
    )
else:
    # Production MySQL configuration:
    # Connection pooling parameters to optimize query latency:
    # pool_size: Number of permanently open connections in the pool
    # max_overflow: Maximum additional burst connections allowed under high load
    # pool_recycle: Recycles connections every hour (3600s) to prevent MySQL server timeout disconnections
    # pool_pre_ping: Emits a quick test query before checkout to ensure the connection is alive
    engine = create_engine(
        db_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=3600,
        pool_pre_ping=True,
    )

# Session factory for managing database transactional contexts
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    FastAPI dependency generator yielding a database session per request
    and ensuring graceful connection closure upon request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def execute_read_query(query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Executes a read-only query safely using bound parameters and returns a list of dictionaries.
    
    Parameters:
    - query: Sanitized SQL string containing parameter placeholders (:cmp_no, :brn_no, etc.)
    - params: Dictionary mapping placeholder names to parameter values
    
    Returns:
    - List of dictionaries representing rows, where keys match column aliases.
    """
    params = params or {}
    
    # Open connection from the pool and automatically release it on context exit
    with engine.connect() as connection:
        # Execute query using parameterized statement
        result = connection.execute(text(query), params)
        
        # Extract column names from result metadata
        keys = result.keys()
        
        # Convert each row tuple into a column-keyed dictionary
        rows = [dict(zip(keys, row)) for row in result.fetchall()]
        
        return rows
