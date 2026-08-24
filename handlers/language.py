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
from database.models import User
from locales.catalog import LANGUAGE_NAMES


IMAGE_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "language.jpg"
)


# ==========================================================
# COMPLETE LANGUAGE MENU
# ==========================================================

LANGUAGES = {
    "fr": {
        "name": "🇫🇷 Français",
        "title": "🌍 𝐋𝐀𝐍𝐆𝐔𝐄",
        "choose": "Choisis la langue du bot :",
        "saved": "✅ Langue enregistrée : Français.",
        "closed": "🌍 Menu de langue fermé.",
    },
    "en": {
        "name": "🇬🇧 English",
        "title": "🌍 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄",
        "choose": "Choose the bot language:",
        "saved": "✅ Language saved: English.",
        "closed": "🌍 Language menu closed.",
    },
    "es": {
        "name": "🇪🇸 Español",
        "title": "🌍 𝐈𝐃𝐈𝐎𝐌𝐀",
        "choose": "Elige el idioma del bot:",
        "saved": "✅ Idioma guardado: Español.",
        "closed": "🌍 Menú de idioma cerrado.",
    },
    "pt": {
        "name": "🇵🇹 Português",
        "title": "🌍 𝐈𝐃𝐈𝐎𝐌𝐀",
        "choose": "Escolha o idioma do bot:",
        "saved": "✅ Idioma salvo: Português.",
        "closed": "🌍 Menu de idioma fechado.",
    },
    "de": {
        "name": "🇩🇪 Deutsch",
        "title": "🌍 𝐒𝐏𝐑𝐀𝐂𝐇𝐄",
        "choose": "Wähle die Sprache des Bots:",
        "saved": "✅ Sprache gespeichert: Deutsch.",
        "closed": "🌍 Sprachmenü geschlossen.",
    },
    "it": {
        "name": "🇮🇹 Italiano",
        "title": "🌍 𝐋𝐈𝐍𝐆𝐔𝐀",
        "choose": "Scegli la lingua del bot:",
        "saved": "✅ Lingua salvata: Italiano.",
        "closed": "🌍 Menu della lingua chiuso.",
    },
    "ar": {
        "name": "🇸🇦 العربية",
        "title": "🌍 𝐀𝐑𝐀𝐁𝐈𝐂",
        "choose": "اختر لغة البوت:",
        "saved": "✅ تم حفظ اللغة: العربية.",
        "closed": "🌍 تم إغلاق قائمة اللغة.",
    },
    "tr": {
        "name": "🇹🇷 Türkçe",
        "title": "🌍 𝐃𝐈𝐋",
        "choose": "Bot dilini seç:",
        "saved": "✅ Dil kaydedildi: Türkçe.",
        "closed": "🌍 Dil menüsü kapatıldı.",
    },
    "nl": {
        "name": "🇳🇱 Nederlands",
        "title": "🌍 𝐓𝐀𝐀𝐋",
        "choose": "Kies de taal van de bot:",
        "saved": "✅ Taal opgeslagen: Nederlands.",
        "closed": "🌍 Taalmenu gesloten.",
    },
    "ja": {
        "name": "🇯🇵 日本語",
        "title": "🌍 𝐋𝐀𝐍𝐆𝐔𝐀𝐆𝐄",
        "choose": "ボットの言語を選択してください：",
        "saved": "✅ 言語を保存しました：日本語。",
        "closed": "🌍 言語メニューを閉じました。",
    },
}


# Keep catalog names as the source of truth when available.
for _code, _name in LANGUAGE_NAMES.items():
    if _code in LANGUAGES:
        LANGUAGES[_code]["name"] = _name


def _language_keyboard() -> InlineKeyboardMarkup:
    # All supported languages are displayed, not only French/English.
    language_codes = list(LANGUAGES.keys())

    rows = []
    for index in range(0, len(language_codes), 2):
        row = []
        for code in language_codes[index:index + 2]:
            row.append(
                InlineKeyboardButton(
                    LANGUAGES[code]["name"],
                    callback_data=f"language:{code}",
                )
            )
        rows.append(row)

    rows.append(
        [
            InlineKeyboardButton(
                "❌ CLOSE",
                callback_data="language:close",
            )
        ]
    )

    return InlineKeyboardMarkup(rows)


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
) -> bool:
    if language not in LANGUAGES:
        return False

    user = await session.get(User, user_id)

    if user is None:
        return False

    user.language = language
    await session.flush()

    return True


def _language_caption(language: str) -> str:
    info = LANGUAGES[language]

    return (
        f"{info['title']}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{info['choose']}"
    )


async def language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    telegram_user = update.effective_user

    if message is None or telegram_user is None:
        return

    async with AsyncSessionLocal() as session:
        user = await session.get(User, telegram_user.id)

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

    with IMAGE_FILE.open("rb") as photo:
        await message.reply_photo(
            photo=photo,
            caption=_language_caption(current),
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
        or query.message is None
    ):
        return

    try:
        await query.answer()
    except Exception:
        pass

    action = str(query.data).split(":", 1)[1]

    if action == "close":
        # Use the user's current language for the close message.
        async with AsyncSessionLocal() as session:
            current = await _get_language(
                session,
                query.from_user.id,
            )

        with IMAGE_FILE.open("rb") as photo:
            await query.message.reply_photo(
                photo=photo,
                caption=LANGUAGES[current]["closed"],
            )
        return

    if action not in LANGUAGES:
        return

    async with AsyncSessionLocal() as session:
        user = await session.get(
            User,
            query.from_user.id,
        )

        if user is None:
            await _reply_not_found(query)
            return

        saved = await _save_language(
            session,
            query.from_user.id,
            action,
        )

        if not saved:
            await _reply_not_found(query)
            return

        await session.commit()

    selected = LANGUAGES[action]

    with IMAGE_FILE.open("rb") as photo:
        await query.message.reply_photo(
            photo=photo,
            caption=selected["saved"],
            reply_markup=_language_keyboard(),
        )


async def _reply_not_found(query):
    with IMAGE_FILE.open("rb") as photo:
        await query.message.reply_photo(
            photo=photo,
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