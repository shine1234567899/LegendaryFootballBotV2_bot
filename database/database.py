from collections.abc import AsyncGenerator
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import DATABASE_URL


def get_async_database_url(url: str) -> str:
    """
    Convertit une URL PostgreSQL classique en URL asyncpg
    et retire les paramètres SSL incompatibles avec asyncpg.
    """

    if url.startswith("postgresql://"):
        url = url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )

    elif url.startswith("postgres://"):
        url = url.replace(
            "postgres://",
            "postgresql+asyncpg://",
            1,
        )

    elif not url.startswith("postgresql+asyncpg://"):
        raise ValueError(
            "DATABASE_URL must be a PostgreSQL connection URL."
        )

    # Retirer sslmode de l'URL.
    # asyncpg recevra SSL via connect_args.
    parts = urlsplit(url)

    query = parse_qsl(
        parts.query,
        keep_blank_values=True,
    )

    query = [
        (key, value)
        for key, value in query
        if key.lower() != "sslmode"
    ]

    clean_url = urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )

    return clean_url


# ==========================================================
# DATABASE URL
# ==========================================================

ASYNC_DATABASE_URL = get_async_database_url(
    DATABASE_URL
)


# ==========================================================
# ENGINE
# ==========================================================

# ==========================================================
# SSL
# ==========================================================
#
# Northflank production uses SSL.
# For local Northflank addon forwarding, the forwarded
# PostgreSQL endpoint can reject an SSL upgrade.
#
# Set DATABASE_SSL=false locally when using:
#   northflank forward addon ...
#
# Keep DATABASE_SSL=true in production.
# ==========================================================

import os

DATABASE_SSL = os.getenv(
    "DATABASE_SSL",
    "true",
).strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}

connect_args = {
    "ssl": True,
} if DATABASE_SSL else {
    "ssl": False,
}


# ==========================================================
# ENGINE
# ==========================================================

engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args,
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

async def get_session() -> AsyncGenerator[
    AsyncSession,
    None,
]:
    async with AsyncSessionLocal() as session:
        yield session


# ==========================================================
# CREATE DATABASE TABLES
# ==========================================================

async def init_database() -> None:
    """
    Initialise toutes les tables SQLAlchemy.
    """

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