"""Database configuration management service.

Supports runtime switching between SQLite and MySQL backends
without requiring a process restart. Configuration is read from
the Pydantic Settings model (backed by .env file).
"""

import logging
import time

from fastapi import FastAPI
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from cnagentos.config import Settings
from cnagentos.db import Base, build_sessionmaker

logger = logging.getLogger(__name__)


def resolve_database_url(settings: Settings) -> str:
    """Return the effective database URL based on settings.

    When ``settings.active_database == 'mysql'``, constructs a MySQL async URL
    from the individual MYSQL_* fields. Otherwise returns the default URL.
    """
    if settings.active_database == "mysql":
        return (
            f"mysql+asyncmy://{settings.mysql_user}:{settings.mysql_password}"
            f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
        )
    return settings.database_url


def resolve_sync_database_url(async_url: str) -> str:
    """Strip async driver prefixes for APScheduler's SQLAlchemyJobStore."""
    for prefix in ("+aiosqlite", "+asyncpg", "+asyncmy", "+aiomysql"):
        async_url = async_url.replace(prefix, "")
    return async_url


async def test_mysql_connection(
    host: str, port: int, user: str, password: str, database: str
) -> dict:
    """Test a MySQL connection by executing SELECT 1.

    Returns a dict with ``success`` and ``latency_ms`` on success,
    or raises an exception on failure.
    """
    url = f"mysql+asyncmy://{user}:{password}@{host}:{port}/{database}"
    engine = create_async_engine(url, pool_pre_ping=True)
    start = time.monotonic()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        elapsed = round((time.monotonic() - start) * 1000, 1)
        return {"success": True, "latency_ms": elapsed}
    finally:
        await engine.dispose()


async def switch_database(
    app: FastAPI,
    new_active: str,
    mysql_kwargs: dict | None = None,
) -> dict:
    """Switch the active database at runtime.

    Steps:
    1. Resolve the new database URL from the provided parameters.
    2. If the URL is unchanged from the current one, return early.
    3. For MySQL, test the connection first.
    4. Dispose the old engine.
    5. Create a new engine and sessionmaker.
    6. Run ``Base.metadata.create_all`` to bootstrap tables.
    7. Reconfigure APScheduler with the new sync URL.
    """
    settings: Settings = app.state.settings

    # Update settings fields in-place for the new target
    settings.active_database = new_active
    if mysql_kwargs:
        if "host" in mysql_kwargs:
            settings.mysql_host = mysql_kwargs["host"]
        if "port" in mysql_kwargs:
            settings.mysql_port = mysql_kwargs["port"]
        if "user" in mysql_kwargs:
            settings.mysql_user = mysql_kwargs["user"]
        if "password" in mysql_kwargs:
            settings.mysql_password = mysql_kwargs["password"]
        if "database" in mysql_kwargs:
            settings.mysql_database = mysql_kwargs["database"]

    new_url = resolve_database_url(settings)
    current_url = app.state.settings.database_url

    # If switching to mysql, test the connection before proceeding
    if new_active == "mysql":
        test_result = await test_mysql_connection(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
        )
        logger.info("MySQL connection test: %s", test_result)

    # Check if URL actually changed
    if new_url == current_url and new_active != "sqlite":
        logger.info("Database URL unchanged, skipping switch")
        return {"changed": False, "url": new_url}

    # Dispose old engine
    old_engine: AsyncEngine = app.state.engine
    await old_engine.dispose()

    # Create new engine and sessionmaker
    engine = create_async_engine(new_url, pool_pre_ping=True)
    sessionmaker = build_sessionmaker(engine)

    # Bootstrap tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Verify tables were created
    async with engine.connect() as conn:
        table_count = await conn.run_sync(
            lambda sync_conn: len(inspect(sync_conn).get_table_names())
        )

    # Update app state
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    # Also update database_url on settings so that downstream code sees the active URL
    app.state.settings.database_url = new_url

    # Reconfigure APScheduler
    try:
        from cnagentos.services.scheduler import reconfigure_scheduler

        sync_url = resolve_sync_database_url(new_url)
        await reconfigure_scheduler(sync_url, sessionmaker)
    except Exception:
        logger.exception("Failed to reconfigure APScheduler after DB switch")

    logger.info(
        "Database switched to %s — %s (%d tables)",
        new_active, new_url, table_count,
    )
    return {"changed": True, "url": new_url, "table_count": table_count}


async def get_database_status(app: FastAPI) -> dict:
    """Return current database connection status."""
    engine: AsyncEngine = app.state.engine
    settings: Settings = app.state.settings
    connected = False
    table_count = 0
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            connected = True
            table_count = await conn.run_sync(
                lambda sync_conn: len(inspect(sync_conn).get_table_names())
            )
    except Exception:
        logger.warning("Database status check failed", exc_info=True)
    return {
        "type": settings.active_database,
        "connected": connected,
        "table_count": table_count,
    }
