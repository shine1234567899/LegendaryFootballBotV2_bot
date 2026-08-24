from __future__ import annotations

from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import GameSetting, User


IMAGE_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "language.jpg"
)


LANGUAGES = {
    "fr": {
        "name": "🇫🇷 Français",
        "saved": "✅ Langue enregistrée : Français.",
        "title": "🌍 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄",
        "choose": "Choisis la langue du bot :",
    },
    "en": {
        "name": "🇬🇧 English",
        "saved": "✅ Language saved: English.",
        "title": "🌍 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄",
        "choose": "Choose the bot language:",
    },
}


def _language_key(user_id: int) -> str:
    return f"user_language:{user_id}"


async def _get_language(
    session,
    user_id: int,
) -> str:
    result = await session.execute(
        select(GameSetting).where(
            GameSetting.key
            == _language_key(user_id)
        )
    )

    setting = result.scalar_one_or_none()

    if setting is None:
        return "en"

    return (
        setting.value
        if setting.value in LANGUAGES
        else "en"
    )


async def _save_language(
    session,
    user_id: int,
    language: str,
):
    result = await session.execute(
        select(GameSetting).where(
            GameSetting.key
            == _language_key(user_id)
        )
    )

    setting = result.scalar_one_or_none()

    if setting is None:
        session.add(
            GameSetting(
                key=_language_key(user_id),
                value=language,
                description="Language selected by the user.",
            )
        )
    else:
        setting.value = language


def _language_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    LANGUAGES["fr"]["name"],
                    callback_data="language:fr",
                ),
            ],
            [
                InlineKeyboardButton(
                    LANGUAGES["en"]["name"],
                    callback_data="language:en",
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ CLOSE",
                    callback_data="language:close",
                ),
            ],
        ]
    )


async def language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    telegram_user = update.effective_user

    if (
        message is None
        or telegram_user is None
    ):
        return

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(
                User.id == telegram_user.id
            )
        )

        user = user_result.scalar_one_or_none()

        if user is None:
            await message.reply_text(
                "❌ Your account was not found.\n"
                "Use /start first."
            )
            return

        current = await _get_language(
            session,
            telegram_user.id,
        )

    info = LANGUAGES[current]

    await message.reply_photo(
        photo=open(
            IMAGE_FILE,
            "rb",
        ),
        caption=(
            f"{info['title']}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{info['choose']}"
        ),
        reply_markup=_language_keyboard(),
    )


async def language_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if (
        query is None
        or not query.data
        or query.from_user is None
    ):
        return

    try:
        await query.answer()
    except Exception:
        pass

    action = str(
        query.data
    ).split(":", 1)[1]

    if action == "close":
        await query.message.reply_photo(
            photo=open(
                IMAGE_FILE,
                "rb",
            ),
            caption="🌍 Language menu closed.",
        )
        return

    if action not in LANGUAGES:
        return

    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(
                User.id
                == query.from_user.id
            )
        )

        user = user_result.scalar_one_or_none()

        if user is None:
            await _reply_not_found(query)
            return

        await _save_language(
            session,
            query.from_user.id,
            action,
        )

        await session.commit()

    selected = LANGUAGES[action]

    await query.message.reply_photo(
        photo=open(
            IMAGE_FILE,
            "rb",
        ),
        caption=selected["saved"],
    )


async def _reply_not_found(query):
    await query.message.reply_photo(
        photo=open(
            IMAGE_FILE,
            "rb",
        ),
        caption="❌ User not found.",
    )


language_handler = CommandHandler(
    "language",
    language,
)

language_callback_handler = CallbackQueryHandler(
    language_callback,
    pattern=r"^language:(fr|en|close)$",
)