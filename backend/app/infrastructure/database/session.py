from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# Production-Grade SQLAlchemy 2.0 Async Engine with Optimized Connection Pooling
# Rationale:
# - pool_size=20: Allocates baseline pool of persistent connections for low-latency request handling.
# - max_overflow=10: Permits burst capacity during high-concurrency traffic spikes (total max 30).
# - pool_timeout=30: Enforces a 30s timeout before raising PoolTimeoutException during saturation.
# - pool_recycle=1800: Recycles connections every 30 mins to prevent stale PostgreSQL socket drops.
# - pool_pre_ping=True: Executes lightweight test ping before checkout to recover broken connections.
async_engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
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
