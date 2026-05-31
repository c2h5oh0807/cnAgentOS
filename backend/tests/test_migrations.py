"""Alembic migration and bootstrap acceptance tests — cross-database compatible.

By default tests run against SQLite in-memory.  Set ``DATABASE_URL`` to
``postgresql+asyncpg://...`` to run against PostgreSQL.
"""

import asyncio
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from cnagentos.config import get_settings
from cnagentos.models.entities import Function, Permission, Role
from cnagentos.services.bootstrap import (
    SYSTEM_FUNCTIONS,
    SYSTEM_ROLE_CODE,
    SYSTEM_ROLE_PERMISSION_CODES,
    create_system_admin,
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite://",
)
ADMIN_PASSWORD = "Admin-password-123"


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql") or url.startswith("postgresql+asyncpg")


def _alembic_config(database_url: str, *, monkeypatch: object) -> Config:
    backend_root = Path(__file__).resolve().parents[1]
    # Use monkeypatch environment for settings
    import builtins
    old_environ = os.environ.copy()
    os.environ["DATABASE_URL"] = database_url
    os.environ["CSRF_SECRET"] = "migration-test-csrf-secret"
    os.environ["ENCRYPTION_KEY"] = "migration-test-encryption-key-32b"
    os.environ["APP_ENV"] = "development"
    get_settings.cache_clear()

    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def _assert_bootstrap_reference_data(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        user, created = await create_system_admin(
            session,
            "migration-root",
            "迁移测试管理员",
            ADMIN_PASSWORD,
        )
        assert created is True
        assert user.is_system_admin is True

        permissions = set(await session.scalars(select(Permission.code)))
        assert SYSTEM_ROLE_PERMISSION_CODES.issubset(permissions)

        functions = set(await session.scalars(select(Function.code)))
        expected_functions = {item[0] for item in SYSTEM_FUNCTIONS}
        assert expected_functions.issubset(functions)

        system_role = await session.scalar(select(Role).where(Role.code == SYSTEM_ROLE_CODE))
        assert system_role is not None
    await engine.dispose()


async def _assert_tables_removed(database_url: str) -> None:
    engine = create_async_engine(database_url, poolclass=NullPool)
    async with engine.connect() as connection:
        tables = await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        assert "users" not in tables, f"users table still present: {tables}"
        # alembic_version may remain after downgrade base; verify it's empty
        from sqlalchemy import text as sa_text
        if "alembic_version" in tables:
            result = await connection.execute(sa_text("SELECT count(*) FROM alembic_version"))
            count = result.scalar()
            assert count == 0, f"alembic_version has {count} rows after downgrade base"
    await engine.dispose()


async def _recreate_postgres_db(database_name: str) -> str:
    admin_url = DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as connection:
        await connection.execute(
            text(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = :database_name AND pid <> pg_backend_pid()"
            ),
            {"database_name": database_name},
        )
        await connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        await connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    await engine.dispose()
    return DATABASE_URL.rsplit("/", 1)[0] + "/" + database_name


async def _drop_postgres_db(database_name: str) -> None:
    admin_url = DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as connection:
        await connection.execute(
            text(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = :database_name AND pid <> pg_backend_pid()"
            ),
            {"database_name": database_name},
        )
        await connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
    await engine.dispose()


def test_alembic_upgrade_bootstrap_and_downgrade_base(monkeypatch):
    """Verify that the full migration chain + bootstrap + downgrade works."""
    if _is_postgres(DATABASE_URL):
        database_name = f"cnagentos_migration_test_{uuid4().hex[:12]}"
        database_url = asyncio.run(_recreate_postgres_db(database_name))
        cleanup = lambda: asyncio.run(_drop_postgres_db(database_name))
    else:
        # SQLite file-based DB for migration testing (in-memory can't span
        # multiple Alembic operations).  We rely on the engine's ``NullPool``
        # behaviour so the file is unlocked after disposal.
        import tempfile
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".db")
        import os
        os.close(tmp_fd)  # close the fd so SQLite can open it
        database_url = f"sqlite+aiosqlite:///{tmp_path}"
        cleanup = lambda: Path(tmp_path).unlink(missing_ok=True)

    config = _alembic_config(database_url, monkeypatch=monkeypatch)

    try:
        command.upgrade(config, "head")
        asyncio.run(_assert_bootstrap_reference_data(database_url))
        command.downgrade(config, "base")
        asyncio.run(_assert_tables_removed(database_url))
    finally:
        cleanup()
        get_settings.cache_clear()
