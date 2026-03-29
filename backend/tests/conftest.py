"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_engine():
    """Create async database engine for tests."""
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        future=True,
    )
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create database session for tests."""
    async_session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_factory() as session:
        yield session


@pytest.fixture
async def async_client():
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient
    from main import app
    
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment."""
    # Ensure we're using test database settings
    import os
    os.environ["PRODUCTION"] = "False"
    yield
