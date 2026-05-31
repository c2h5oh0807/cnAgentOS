"""APScheduler integration skeleton (Phase 9+).

Phase 5 establishes the scheduler foundation:
  - AsyncIOScheduler with SQLAlchemy job store for persistence.
  - Initialisation during app lifespan.
  - Cross-DB compatible (SQLite and PostgreSQL).

Full scheduled task management (admin CRUD, handler registry, execution
logging) is implemented in Phase 9.
"""

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

_scheduler: AsyncIOScheduler | None = None


def init_scheduler(database_url: str) -> AsyncIOScheduler:
    """Create and return an AsyncIOScheduler backed by the application database.

    Call this during app lifespan startup.  The caller is responsible for
    calling ``start()`` on the returned instance.
    """
    global _scheduler
    jobstore = SQLAlchemyJobStore(url=database_url)
    _scheduler = AsyncIOScheduler(jobstores={"default": jobstore})
    return _scheduler


def get_scheduler() -> AsyncIOScheduler:
    """Return the global scheduler instance.

    Raises ``AssertionError`` if ``init_scheduler`` has not been called.
    """
    assert _scheduler is not None, "scheduler not initialised; call init_scheduler first"
    return _scheduler
