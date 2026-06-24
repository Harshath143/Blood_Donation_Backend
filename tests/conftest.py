import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from redis.asyncio import Redis, from_url
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import get_db, Base
from app.dependencies import get_redis
from app.config import get_settings
from app.integrations.geocoding import GeocodingService

settings = get_settings()
TEST_REDIS_URL = "redis://localhost:6379/1"

@pytest_asyncio.fixture
async def test_engine():
    """Provides a fresh SQL connection engine for the test."""
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"ssl": False}
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provides an isolated database session with transactional rollback."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def test_redis() -> AsyncGenerator[Redis, None]:
    """Provides a clean Redis connection."""
    client = from_url(TEST_REDIS_URL)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()

@pytest_asyncio.fixture(autouse=True)
async def clean_database_and_redis(db_session, test_redis):
    """Truncates all tables and flushes test Redis to ensure clean, isolated states."""
    # Flush Redis
    await test_redis.flushdb()
    
    # Truncate all tables
    await db_session.execute(text("TRUNCATE matches, donations, blood_requests, donors, users, blood_banks, hospitals CASCADE"))
    await db_session.commit()
    
    yield

@pytest_asyncio.fixture
async def client(db_session, test_redis) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI test client with database and Redis dependency overrides."""
    
    async def override_get_db():
        yield db_session
        
    async def override_get_redis():
        yield test_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    
    # Mock SMTP mail delivery and Nominatim geocoder calls
    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send, \
         patch.object(GeocodingService, "geocode", new_callable=AsyncMock) as mock_geocode:
        
        # Default mock coordinates (Bangalore)
        mock_geocode.return_value = (12.9716, 77.5946)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
            
    app.dependency_overrides.clear()
