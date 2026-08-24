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
from locales.catalog import LANGUAGE_NAMES


IMAGE_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "language.jpg"
)


LANGUAGES = {
    code: {
        "name": name,
        "saved": {
            "fr": "✅ Langue enregistrée : Français.",
            "en": "✅ Language saved: English.",
            "es": "✅ Idioma guardado: Español.",
            "pt": "✅ Idioma salvo: Português.",
            "de": "✅ Sprache gespeichert: Deutsch.",
            "it": "✅ Lingua salvata: Italiano.",
            "ar": "✅ تم حفظ اللغة: العربية.",
            "tr": "✅ Dil kaydedildi: Türkçe.",
            "nl": "✅ Taal opgeslagen: Nederlands.",
            "ja": "✅ 言語を保存しました：日本語。",
        }[code],
        "title": "🌍 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄",
        "choose": {
            "fr": "Choisis la langue du bot :",
            "en": "Choose the bot language:",
            "es": "Elige el idioma del bot:",
            "pt": "Escolha o idioma do bot:",
            "de": "Wähle die Sprache des Bots:",
            "it": "Scegli la lingua del bot:",
            "ar": "اختر لغة البوت:",
            "tr": "Bot dilini seç:",
            "nl": "Kies de taal van de bot:",
            "ja": "ボットの言語を選択してください：",
        }[code],
    }
    for code, name in LANGUAGE_NAMES.items()
}


async def _get_language(
    session,
    user_id: int,
) -> str:
    user = await session.get(User, user_id)

    if user is None:
        return "en"

    value = getattr(user, "language", None)

    return value if value in LANGUAGES else "en"


async def _save_language(
    session,
    user_id: int,
    language: str,
):
    user = await session.get(User, user_id)

    if user is None:
        return False

    user.language = language
    await session.flush()

    return True


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
    pattern=r"^language:(fr|en|es|pt|de|it|ar|tr|nl|ja|close)$",
)