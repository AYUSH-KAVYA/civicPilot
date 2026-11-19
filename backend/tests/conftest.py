"""
Pytest configuration and async fixtures for CivicPilot test suite.
Uses an isolated temporary SQLite database for fast, reliable testing.
"""

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import AsyncGenerator

import httpx
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_FILE = Path("test_civicpilot.db")
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

# Set test environment variables before importing app
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["JWT_SECRET"] = "test-secret-key-32-characters-minimum-for-testing"
os.environ["OFFICER_PASSWORD"] = "testpassword123"
os.environ["MOCK_LLM"] = "true"
os.environ["SIM_TIME_SCALE"] = "1.0"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:3000"

import backend.app.db.session as db_session_module
from backend.app.db.models import Base
from backend.app.db.seed import seed_database
from backend.app.db.session import get_db
from backend.app.main import app

test_engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    future=True,
    json_serializer=lambda obj: json.dumps(obj, default=lambda o: o.isoformat() if isinstance(o, (datetime, date)) else str(o)),
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Rebind session module's engine and factory to test database
db_session_module.engine = test_engine
db_session_module.AsyncSessionLocal = TestAsyncSessionLocal


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_test_db():
    """Create all tables and seed master data for tests."""
    if TEST_DB_FILE.exists():
        TEST_DB_FILE.unlink()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        await seed_database(session)

    yield

    await test_engine.dispose()
    if TEST_DB_FILE.exists():
        TEST_DB_FILE.unlink()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session per test."""
    async with TestAsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async test client connected to the FastAPI app with test db override."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
