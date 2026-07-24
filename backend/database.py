"""
database.py — async SQLAlchemy engine, session factory, and the Base
declarative class that models.py builds ORM tables from.
"""
from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from config import settings

# SQLite (the MVP's default store) serializes writes. Under concurrent request
# load a write can collide and surface as "database is locked" — exactly the
# symptom that made conversation history intermittently fail to save. We use
# NullPool (no connection reuse) so each session gets its own connection
# rather than fighting over a shared one, paired with a busy timeout and WAL
# mode for concurrent-read / single-write throughput.
# check_same_thread=False allows the connection to be shared across async tasks.
_connect_args = {}
_pool_class = None
if str(settings.DATABASE_URL).startswith("sqlite"):
    _connect_args = {"timeout": 30, "check_same_thread": False}
    _pool_class = NullPool

_engine_kwargs = {
    "echo": settings.DEBUG,
    "future": True,
    "connect_args": _connect_args,
}
if _pool_class is not None:
    _engine_kwargs["poolclass"] = _pool_class

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)


# Enable foreign-key enforcement + WAL mode on every new connection.
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.close()


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    # Free the underlying connection back to the pool promptly so a second
    # in-flight request never waits on a leaked handle.
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create tables on startup. For anything beyond SQLite-for-a-resume-project,
    replace this with Alembic migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency — yields a request-scoped async session."""
    async with AsyncSessionLocal() as session:
        yield session
