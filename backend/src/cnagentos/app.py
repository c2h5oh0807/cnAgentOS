from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Request

from cnagentos.api import register_api_support, success_response
from cnagentos.config import Settings, get_settings
from cnagentos.controllers.admin import router as admin_router
from cnagentos.controllers.auth import router as auth_router
from cnagentos.controllers.chat import router as chat_router
from cnagentos.controllers.model_engine import router as model_engine_router
from cnagentos.controllers.watch_and_data import router as watch_data_router, _background_tasks
from cnagentos.controllers.qa import router as qa_router
from cnagentos.controllers.ws import router as ws_router
from cnagentos.controllers.file import router as file_router
from cnagentos.controllers.admin_chat import router as admin_chat_router
from cnagentos.controllers.admin_employee import router as admin_employee_router
from cnagentos.controllers.admin_server import router as admin_server_router
from cnagentos.controllers.admin_sentiment import router as admin_sentiment_router
from cnagentos.db import Base, build_engine, build_sessionmaker
from cnagentos.security import init_cipher


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    init_cipher(active_settings.encryption_key)
    engine = build_engine(active_settings)
    sessionmaker = build_sessionmaker(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # --- Startup ---
        # Auto-create tables for development
        async with engine.connect() as conn:
            from sqlalchemy import inspect
            has_tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).has_table("users"))
        if not has_tables:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        # Initialize and start the APScheduler
        from cnagentos.services.scheduler import init_scheduler, set_sessionmaker, register_all_collection_jobs
        scheduler = init_scheduler(active_settings.sync_database_url)
        set_sessionmaker(sessionmaker)
        scheduler.start()
        app.state.scheduler = scheduler
        # Register scheduled collection jobs for sources with cron enabled
        await register_all_collection_jobs()

        yield

        # --- Shutdown ---
        # Shut down the scheduler first (stop accepting new jobs)
        scheduler.shutdown(wait=False)
        # Wait for background collection tasks to complete
        if _background_tasks:
            await asyncio.gather(*_background_tasks, return_exceptions=True)
        await engine.dispose()

    app = FastAPI(title=active_settings.app_name, version="0.1.0", lifespan=lifespan)
    app.state.settings = active_settings
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    register_api_support(app)
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(model_engine_router)
    app.include_router(watch_data_router)
    app.include_router(qa_router)
    app.include_router(ws_router)
    app.include_router(chat_router)
    app.include_router(file_router)
    app.include_router(admin_chat_router)
    app.include_router(admin_employee_router)
    app.include_router(admin_server_router)
    app.include_router(admin_sentiment_router)

    @app.get("/health")
    async def health(request: Request):
        return success_response(request, {"status": "ok"})

    return app
