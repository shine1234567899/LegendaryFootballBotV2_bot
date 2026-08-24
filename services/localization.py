from __future__ import annotations

import functools
from typing import Optional

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import User
from locales.catalog import LANGUAGE_NAMES, TRANSLATIONS

SUPPORTED_LANGUAGES = LANGUAGE_NAMES
DEFAULT_LANGUAGE = "en"


def normalize_language(language: Optional[str]) -> str:
    if not language:
        return DEFAULT_LANGUAGE

    language = language.lower().strip().replace("_", "-")
    code = language.split("-", 1)[0]

    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


async def get_user_language(user_id: int) -> str:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User.language).where(User.id == user_id)
        )
        language = result.scalar_one_or_none()

    return normalize_language(language)


async def set_user_language(user_id: int, language: str) -> str:
    language = normalize_language(language)

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)

        if user is None:
            return language

        user.language = language
        await session.commit()

    return language


@functools.lru_cache(maxsize=16384)
def _translate_sync(text: str, language: str) -> str:
    if not text or language == DEFAULT_LANGUAGE:
        return text

    return TRANSLATIONS.get(language, {}).get(text, text)


async def translate_text(
    text: str,
    language: Optional[str] = None,
    user_id: Optional[int] = None,
) -> str:
    if not text:
        return text

    if language is None and user_id is not None:
        language = await get_user_language(user_id)

    return _translate_sync(text, normalize_language(language))


async def t(
    text: str,
    user_id: Optional[int] = None,
    language: Optional[str] = None,
) -> str:
    return await translate_text(text, language=language, user_id=user_id)


def language_name(language: str) -> str:
    return SUPPORTED_LANGUAGES.get(
        normalize_language(language),
        SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE],
    )


def available_languages() -> dict[str, str]:
    return dict(SUPPORTED_LANGUAGES)
async def get_text(
    text: str,
    user_id: int | None = None,
    language: str | None = None,
) -> str:
    return await translate_text(
        text,
        language=language,
        user_id=user_id,
    )