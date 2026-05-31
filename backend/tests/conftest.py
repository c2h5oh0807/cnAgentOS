"""Test configuration and shared fixtures — cross-database compatible.

Reads ``DATABASE_URL`` from the environment (default ``sqlite+aiosqlite://``).
Also works with ``postgresql+asyncpg://...``.
"""

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from cnagentos.app import create_app
from cnagentos.config import Settings
from cnagentos.db import Base
from cnagentos.services.bootstrap import create_system_admin


DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite://",
)
ADMIN_PASSWORD = "Admin-password-123"

_db_initialized = False


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql") or url.startswith("postgresql+asyncpg")


@pytest_asyncio.fixture(scope="function")
async def app():
    """每个测试函数创建新的应用实例和数据库"""
    global _db_initialized

    if _is_postgres(DATABASE_URL):
        # PostgreSQL: create test database if it doesn't exist
        admin_url = DATABASE_URL.replace("/cnagentos_test", "/postgres")
        if DATABASE_URL.endswith("_test"):
            pass  # already targeted at test DB
        else:
            admin_url = DATABASE_URL.replace(
                DATABASE_URL.rsplit("/", 1)[-1], "postgres"
            )

        admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
        async with admin_engine.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = 'cnagentos_test'")
            )
            if not exists:
                await connection.execute(text("CREATE DATABASE cnagentos_test"))
        await admin_engine.dispose()

        test_db_url = DATABASE_URL
    else:
        # SQLite: in-memory database — no admin setup needed
        test_db_url = DATABASE_URL

    settings = Settings(
        DATABASE_URL=test_db_url,
        CSRF_SECRET="integration-test-csrf-secret-value",
        APP_ENV="development",
        ENCRYPTION_KEY="integration-test-encryption-key-32b",
    )
    application = create_app(settings)
    async with application.state.engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async with application.state.sessionmaker() as session:
        await create_system_admin(session, "root", "系统管理员", ADMIN_PASSWORD)
    yield application
    await application.state.engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(app):
    """每个测试函数使用新的 HTTP 客户端"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http_client:
        yield http_client


@pytest_asyncio.fixture
async def admin_session(client):
    """每个测试函数重新登录获取新的 CSRF token"""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "root", "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["data"]["csrf_token"]
