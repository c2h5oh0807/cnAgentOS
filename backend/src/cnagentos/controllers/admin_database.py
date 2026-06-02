"""Admin API routes for database configuration management."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from cnagentos.api import ApiError, success_response
from cnagentos.controllers.dependencies import (
    require_csrf,
    require_permission,
)
from cnagentos.services.auth import AuthContext
from cnagentos.services.database_config import (
    get_database_status,
    switch_database,
    test_mysql_connection,
)

router = APIRouter(prefix="/api/v1/admin/database", tags=["admin-database"])

SystemManager = Annotated[AuthContext, Depends(require_permission("system.settings"))]


# ── Request / Response schemas ──────────────────────────────────────────────


class MySQLConfigRequest(BaseModel):
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=3306, ge=1, le=65535)
    user: str = Field(default="cnagentos")
    password: str = Field(default="cnagentos_pass_here")
    database: str = Field(default="cnagentos")


class SwitchRequest(BaseModel):
    type: str = Field(..., pattern="^(sqlite|mysql)$")  # 'sqlite' or 'mysql'
    mysql: MySQLConfigRequest | None = None


# ── Helper: mask password in response ──────────────────────────────────────


def _mask_password(cfg: dict) -> dict:
    """Return a copy of the config dict with password masked."""
    result = dict(cfg)
    if "password" in result and result["password"]:
        result["password"] = "******"
    return result


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("/config")
async def get_config(
    request: Request,
    _system: SystemManager,
):
    """Return the current database configuration from settings (password masked)."""
    settings = request.app.state.settings
    data = {
        "active_database": settings.active_database,
        "mysql": _mask_password({
            "host": settings.mysql_host,
            "port": settings.mysql_port,
            "user": settings.mysql_user,
            "password": settings.mysql_password,
            "database": settings.mysql_database,
        }),
    }
    return success_response(request, data)


@router.get("/status")
async def get_status(
    request: Request,
    _system: SystemManager,
):
    """Return the current database connection status."""
    status = await get_database_status(request.app)
    return success_response(request, status)


@router.post("/test")
async def test_connection(
    request: Request,
    body: MySQLConfigRequest,
    _system: SystemManager,
    _csrf=Depends(require_csrf),
):
    """Test a MySQL connection with the provided parameters."""
    try:
        result = await test_mysql_connection(
            host=body.host,
            port=body.port,
            user=body.user,
            password=body.password,
            database=body.database,
        )
        return success_response(request, result)
    except Exception as exc:
        raise ApiError(
            400, "CONNECTION_FAILED",
            f"数据库连接失败: {exc}",
        ) from exc


@router.post("/switch")
async def switch_active_database(
    request: Request,
    body: SwitchRequest,
    _system: SystemManager,
    _csrf=Depends(require_csrf),
):
    """Switch the active database at runtime.

    Accepts ``type`` ('sqlite' | 'mysql') and optional ``mysql`` parameters.
    For SQLite switching, omit mysql or pass null.
    """
    lock = request.app.state.db_switch_lock
    if lock.locked():
        raise ApiError(409, "SWITCH_IN_PROGRESS", "数据库切换正在进行中，请稍后再试")

    async with lock:
        try:
            mysql_kwargs = body.mysql.model_dump() if body.mysql else None
            result = await switch_database(
                request.app,
                new_active=body.type,
                mysql_kwargs=mysql_kwargs,
            )
            return success_response(request, result)
        except Exception as exc:
            raise ApiError(
                500, "SWITCH_FAILED",
                f"数据库切换失败: {exc}",
            ) from exc
