"""APScheduler integration for scheduled collection tasks.

Phase 6 establishes the scheduler foundation with automatic collection
job registration based on WatchSource cron configuration.
"""

import logging
from collections.abc import Callable
from typing import Any

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker

from cnagentos.schemas import CollectionTaskCreate, CollectionTaskTarget

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_sessionmaker: async_sessionmaker | None = None

# Track registered source jobs so we can reschedule
_registered_source_jobs: set[str] = set()


def init_scheduler(database_url: str) -> AsyncIOScheduler:
    """Create and return an AsyncIOScheduler backed by the application database.

    Call this during app lifespan startup.  The caller is responsible for
    calling ``start()`` on the returned instance.
    """
    global _scheduler
    jobstore = SQLAlchemyJobStore(url=database_url)
    _scheduler = AsyncIOScheduler(jobstores={"default": jobstore})
    return _scheduler


async def reconfigure_scheduler(
    sync_database_url: str,
    sessionmaker: async_sessionmaker,
) -> None:
    """Reconfigure the APScheduler with a new database URL.

    Used when switching active databases at runtime.
    Shuts down the old scheduler, creates a new one with the new
    job store, and re-registers collection jobs.
    """
    global _scheduler, _sessionmaker

    old = _scheduler
    if old is not None:
        old.shutdown(wait=False)

    jobstore = SQLAlchemyJobStore(url=sync_database_url)
    _scheduler = AsyncIOScheduler(jobstores={"default": jobstore})
    _scheduler.start()
    _sessionmaker = sessionmaker

    # Re-register collection jobs from the active database
    _registered_source_jobs.clear()
    await register_all_collection_jobs()

    logger.info("APScheduler reconfigured with database URL: %s", sync_database_url)


def get_scheduler() -> AsyncIOScheduler | None:
    """Return the global scheduler instance, or None if not initialized."""
    return _scheduler


def set_sessionmaker(sm: async_sessionmaker) -> None:
    """Store the async sessionmaker for scheduled job execution."""
    global _sessionmaker
    _sessionmaker = sm


async def register_all_collection_jobs() -> None:
    """Register scheduled collection jobs for all sources with cron enabled.

    Called once during app startup.
    """
    if _scheduler is None or _sessionmaker is None:
        logger.warning("Scheduler or sessionmaker not initialized, skipping job registration")
        return

    from cnagentos.models.entities import WatchSource
    from sqlalchemy import select

    sm = _sessionmaker
    async with sm() as session:
        sources = await session.scalars(
            select(WatchSource).where(
                WatchSource.status == "active",
                WatchSource.cron_expression.is_not(None),
            )
        )
        for source in sources.all():
            if source.cron_expression:
                _add_collection_job(source.id, source.cron_expression)
                _registered_source_jobs.add(source.id)

    logger.info("Registered %d scheduled collection jobs", len(_registered_source_jobs))


async def reschedule_collection_job(source_id: str) -> None:
    """Remove and re-add a collection job for a source.

    Called when a source's cron configuration changes.
    """
    if _scheduler is None or _sessionmaker is None:
        return

    job_id = f"collection_{source_id}"

    # Remove existing job if any
    if job_id in _registered_source_jobs:
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)
        _registered_source_jobs.discard(source_id)

    # Re-read the source config
    from cnagentos.models.entities import WatchSource
    from sqlalchemy import select

    sm = _sessionmaker
    async with sm() as session:
        source = await session.get(WatchSource, source_id)
        if source and source.status == "active" and source.cron_expression:
            _add_collection_job(source_id, source.cron_expression)
            _registered_source_jobs.add(source_id)


def _add_collection_job(source_id: str, cron_expression: str) -> None:
    """Add an APScheduler cron job for a source."""
    if _scheduler is None:
        return

    job_id = f"collection_{source_id}"

    # Parse the cron expression: "0 9 * * *" → {'hour': 9, 'minute': 0}
    parts = cron_expression.strip().split()
    if len(parts) != 5:
        logger.warning("Invalid cron expression for source %s: %s", source_id, cron_expression)
        return

    cron_kwargs = {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }

    _scheduler.add_job(
        _execute_scheduled_collection,
        "cron",
        args=[source_id],
        id=job_id,
        replace_existing=True,
        name=f"collect-source-{source_id}",
        **cron_kwargs,
    )

    logger.info("Scheduled collection job for source %s: %s", source_id, cron_expression)


async def _execute_scheduled_collection(source_id: str) -> None:
    """Execute a scheduled collection for a single source.

    This is the APScheduler job callback. It creates a CollectionTask
    with trigger_type="scheduled" and runs it.
    """
    if _sessionmaker is None:
        logger.error("Sessionmaker not initialized, cannot execute scheduled collection")
        return

    from cnagentos.services.bootstrap import ensure_system_task_user
    from cnagentos.services.watch_and_data import WatchService

    sm = _sessionmaker
    async with sm() as session:
        try:
            actor = await ensure_system_task_user(session)
            service = WatchService(session, actor, None)
            target = CollectionTaskTarget(source_id=source_id)
            payload = CollectionTaskCreate(targets=[target])
            result = await service.create_task(payload, trigger_type="scheduled")
            task_id = result["id"]
            await session.commit()

            # Execute the task (will create its own session internally)
            async with sm() as exec_session:
                exec_actor = await ensure_system_task_user(exec_session)
                exec_service = WatchService(exec_session, exec_actor, None)
                await exec_service.execute_task(task_id)
                await exec_session.commit()

            logger.info("Scheduled collection completed for source %s (task %s)", source_id, task_id)
        except Exception:
            logger.exception("Scheduled collection failed for source %s", source_id)
