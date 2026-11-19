"""
Database Session Management for CivicPilot.
Handles async SQLAlchemy engine, sessions, and pgvector extension initialization.
"""

import json
from datetime import date, datetime
from typing import Any, AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from backend.app.core.config import get_settings

Base = declarative_base()


def json_serializer(obj: Any) -> str:
    """Safe JSON serializer handling datetime, UUID, and enums."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return json.dumps(obj, default=lambda o: o.isoformat() if isinstance(o, (datetime, date)) else str(o))


def get_engine_url() -> str:
    settings = get_settings()
    url = settings.DATABASE_URL
    # Normalise postgres:// or postgresql:// to postgresql+asyncpg://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# Create engine
engine = create_async_engine(
    get_engine_url(),
    echo=False,
    future=True,
    pool_pre_ping=True,
    json_serializer=lambda obj: json.dumps(obj, default=lambda o: o.isoformat() if isinstance(o, (datetime, date)) else str(o)),
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db_extensions() -> None:
    """Initialize required PostgreSQL extensions such as pgvector."""
    url = get_engine_url()
    if "postgresql" in url:
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception as e:
            # Non-fatal if user doesn't have superuser or on non-pgvector host
            print(f"[DB Warning] Could not execute CREATE EXTENSION IF NOT EXISTS vector: {e}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
