from collections.abc import AsyncGenerator


from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import DATABASE_URL


def get_async_database_url(url: str) -> str:
    """
    Convertit une URL PostgreSQL classique en URL asyncpg.
    """

    if url.startswith(
        "postgresql+asyncpg://"
    ):
        return url

    if url.startswith(
        "postgresql://"
    ):
        return url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )

    if url.startswith(
        "postgres://"
    ):
        return url.replace(
            "postgres://",
            "postgresql+asyncpg://",
            1,
        )

    raise ValueError(
        "DATABASE_URL must be a PostgreSQL connection URL."
    )


# ==========================================================
# DATABASE URL
# ==========================================================

ASYNC_DATABASE_URL = (
    get_async_database_url(
        DATABASE_URL
    )
)


# ==========================================================
# ENGINE
# ==========================================================

engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)


# ==========================================================
# SESSION
# ==========================================================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ==========================================================
# SESSION DEPENDENCY
# ==========================================================

async def get_session()-> AsyncGenerator[
    AsyncSession,
    None,
]:

 async with AsyncSessionLocal() as session:

        yield session


# ==========================================================
# CREATE DATABASE TABLES
# ==========================================================

async def init_database() -> None:

    # Import ici pour éviter les problèmes
    # de circular import.

    from database.models import Base

    async with engine.begin() as connection:

        await connection.run_sync(
            Base.metadata.create_all
        )


# ==========================================================
# CLOSE DATABASE
# ==========================================================

async def close_database() -> None:

    await engine.dispose()