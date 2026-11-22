import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_SQLITE_URL = "sqlite+aiosqlite:///./sahayak.db"


def get_async_database_url(url: Optional[str]) -> str:
    """Normalize database URL for async SQLAlchemy (asyncpg for PG, aiosqlite for SQLite).

    Handles:
    - Empty/None/Whitespace -> sqlite+aiosqlite:///./sahayak.db
    - postgres:// -> postgresql+asyncpg://
    - postgresql:// -> postgresql+asyncpg://
    - sqlite:// -> sqlite+aiosqlite://
    - sslmode= -> ssl= (asyncpg compatibility)
    """
    if url is None or not str(url).strip():
        return DEFAULT_SQLITE_URL

    normalized = str(url).strip()
    if normalized.startswith("postgres://"):
        normalized = "postgresql+asyncpg://" + normalized[len("postgres://"):]
    elif normalized.startswith("postgresql://") and not normalized.startswith("postgresql+"):
        normalized = "postgresql+asyncpg://" + normalized[len("postgresql://"):]
    elif normalized.startswith("sqlite://") and not normalized.startswith("sqlite+"):
        normalized = "sqlite+aiosqlite://" + normalized[len("sqlite://"):]

    if "sslmode=" in normalized:
        normalized = normalized.replace("sslmode=", "ssl=")

    return normalized


def create_engine_instance(url: Optional[str] = None) -> AsyncEngine:
    """Create an AsyncEngine instance with appropriate dialect-specific connect args."""
    async_url = get_async_database_url(url or settings.DATABASE_URL)
    connect_args = {}

    if async_url.startswith("postgresql"):
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0
    elif async_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_async_engine(
        async_url,
        echo=settings.APP_DEBUG,
        future=True,
        connect_args=connect_args,
    )


# Module-level engine and session factory
try:
    engine = create_engine_instance(settings.DATABASE_URL)
except Exception as e:
    logger.warning(
        f"Error configuring primary engine for {settings.DATABASE_URL}: {e}. Falling back to SQLite."
    )
    engine = create_engine_instance(DEFAULT_SQLITE_URL)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection yielding an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(database_url: Optional[str] = None) -> None:
    """Initialize database tables with graceful fallback to local SQLite."""
    # Ensure all 6 models register in Base.metadata
    from app.models import models  # noqa: F401

    global engine

    target_url = get_async_database_url(database_url or settings.DATABASE_URL)
    if str(engine.url) != target_url:
        await engine.dispose()
        engine = create_engine_instance(target_url)
        AsyncSessionLocal.configure(bind=engine)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"Connected to primary database: {engine.url.render_as_string(hide_password=True)}")
    except Exception as exc:
        if "sqlite" in str(engine.url):
            logger.error(f"Fatal error initializing SQLite database: {exc}")
            raise exc

        logger.warning(
            f"Failed to connect to primary database ({engine.url.render_as_string(hide_password=True)}): {exc}. "
            f"Falling back to local SQLite database ({DEFAULT_SQLITE_URL})."
        )
        await engine.dispose()
        engine = create_engine_instance(DEFAULT_SQLITE_URL)
        AsyncSessionLocal.configure(bind=engine)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Successfully initialized fallback SQLite database.")


async def close_db() -> None:
    """Dispose active database engine connections."""
    await engine.dispose()
