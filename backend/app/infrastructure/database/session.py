from typing import Any, AsyncGenerator, Dict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def _build_engine_kwargs() -> Dict[str, Any]:
    """Build production-grade connection arguments for SQLAlchemy 2.0 AsyncEngine."""
    db_url = settings.effective_database_url
    connect_args: Dict[str, Any] = {}

    # Supabase Transaction Pooler (Port 6543 / PgBouncer / Supavisor) compatibility:
    # Transaction poolers do not support named prepared statements across pooled sessions.
    # Disabling statement cache allows seamless operation with Supabase port 6543.
    if ":6543" in db_url or "pooler.supabase.com" in db_url or "pgbouncer" in db_url:
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0

    # Handle SSL configuration for remote cloud endpoints (e.g. Supabase Managed PostgreSQL)
    is_remote = any(
        host_indicator in db_url
        for host_indicator in (
            "supabase.co",
            "supabase.com",
            "pooler.supabase",
            ".amazonaws.com",
            ".azure.com",
        )
    )
    if settings.db_ssl_mode == "require" or (
        is_remote and settings.db_ssl_mode != "disable"
    ):
        connect_args["ssl"] = "require"

    engine_kwargs: Dict[str, Any] = {
        "echo": False,
        "future": True,
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout": settings.db_pool_timeout,
        "pool_recycle": settings.db_pool_recycle,
        "pool_pre_ping": settings.db_pool_pre_ping,
    }

    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    return engine_kwargs


# Production-Grade SQLAlchemy 2.0 Async Engine with Supabase Managed PostgreSQL Support
async_engine: AsyncEngine = create_async_engine(
    settings.effective_database_url,
    **_build_engine_kwargs(),
)

# Async Session Factory
async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injector providing an async database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> bool:
    """Probe database connectivity by executing a simple SELECT 1 query."""
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False
