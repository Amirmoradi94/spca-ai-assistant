"""Database session management for async SQLAlchemy."""

import os
import time
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from .models import Base

logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from environment."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://spca:spca_password@localhost:5432/spca"
    )


# Lazy initialization
_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker] = None


def get_engine() -> AsyncEngine:
    """Get or create the database engine with retry logic."""
    global _engine
    if _engine is None:
        db_url = get_database_url()
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                logger.info(f"Creating database engine (attempt {attempt + 1}/{max_retries})")
                _engine = create_async_engine(
                    db_url,
                    echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
                    pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
                    max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
                    pool_pre_ping=True,  # Verify connections before using
                    connect_args={
                        "server_settings": {"application_name": "spca_assistant"},
                        "timeout": 10,
                    }
                )
                logger.info("Database engine created successfully")
                break
            except Exception as e:
                logger.warning(f"Failed to create engine (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Failed to create database engine after all retries")
                    raise
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Get or create the session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _async_session_factory


async def init_db() -> None:
    """Initialize database - create all tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """Drop all tables - use with caution."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session as a context manager."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session."""
    async with get_session() as session:
        yield session
