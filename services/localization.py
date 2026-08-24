from __future__ import annotations

import asyncio
import functools
import re
from contextvars import ContextVar
from typing import Any

from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import User


SUPPORTED_LANGUAGES = {
    "fr": "🇫🇷 Français",
    "en": "🇬🇧 English",
    "es": "🇪🇸 Español",
    "pt": "🇵🇹 Português",
    "de": "🇩🇪 Deutsch",
    "it": "🇮🇹 Italiano",
    "ar": "🇸🇦 العربية",
    "tr": "🇹🇷 Türkçe",
    "nl": "🇳🇱 Nederlands",
    "ja": "🇯🇵 日本語",
}

DEFAULT_LANGUAGE = "en"

_CURRENT_USER_ID: ContextVar[int | None] = ContextVar(
    "current_localization_user_id",
    default=None,
)

# Prevent nested monkey-patches from translating the same message twice.
_TRANSLATION_ACTIVE: ContextVar[bool] = ContextVar(
    "localization_translation_active",
    default=False,
)

_INSTALLED = False

_TRANSLATION_CACHE: dict[tuple[str, str], str] = {}

_URL_RE = re.compile(
    r"https?://\S+|@\w+|\B/\w+"
)

_PLACEHOLDER_RE = re.compile(
    r"(\{[^{}]+\}|"
    r"\[[^\]]+\]|"
    r"<[^>]+>)"
)

# Telegram hard limits.
MAX_TEXT_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024


async def get_user_language(
    user_id: int | None,
) -> str:
    if not user_id:
        return DEFAULT_LANGUAGE

    try:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)

            language = getattr(
                user,
                "language",
                None,
            )

            if language in SUPPORTED_LANGUAGES:
                return language

    except Exception:
        # Localization must never break a handler because the DB is
        # temporarily unavailable.
        pass

    return DEFAULT_LANGUAGE


def set_current_user_id(
    user_id: int | None,
):
    return _CURRENT_USER_ID.set(user_id)


def reset_current_user_id(token):
    _CURRENT_USER_ID.reset(token)


def _protect_tokens(
    text: str,
):
    protected: list[str] = []

    def repl(match):
        token = (
            f"ZXQPROT{len(protected)}QXZ"
        )
        protected.append(
            match.group(0)
        )
        return token

    result = _URL_RE.sub(
        repl,
        text,
    )

    result = _PLACEHOLDER_RE.sub(
        repl,
        result,
    )

    return result, protected


def _restore_tokens(
    text: str,
    protected: list[str],
):
    for index, value in enumerate(
        protected
    ):
        token = (
            f"ZXQPROT{index}QXZ"
        )
        text = text.replace(
            token,
            value,
        )

    return text


@functools.lru_cache(maxsize=16384)
def _load_translations(language: str) -> dict[str, str]:
    """Load local translations only. No online translation service."""
    if language == "en":
        return {}

    merged: dict[str, str] = {}

    # Legacy per-language modules, e.g. locales/fr.py.
    try:
        module = __import__(
            f"locales.{language}",
            fromlist=["TRANSLATIONS"],
        )
        values = getattr(module, "TRANSLATIONS", {})
        if isinstance(values, dict):
            merged.update(values)
    except Exception:
        pass

    # New catalog.py, when present.
    try:
        from locales.catalog import TRANSLATIONS
        values = TRANSLATIONS.get(language, {})
        if isinstance(values, dict):
            # Prefer explicit catalog entries over an older fallback.
            merged.update(values)
    except Exception:
        pass

    return merged


@functools.lru_cache(maxsize=16384)
def _translate_sync(
    text: str,
    language: str,
) -> str:
    """
    Deterministic local localization.

    - English stays unchanged.
    - French uses the project's existing large locales/fr.py dictionary.
    - Other languages use local dictionaries/catalog entries when present.
    - There is NO runtime Google/DeepTranslator dependency.
    """
    if not isinstance(text, str) or not text.strip():
        return text

    language = (
        language.lower().strip().replace("_", "-").split("-", 1)[0]
    )

    if language == "en":
        return text

    translations = _load_translations(language)

    if not translations:
        return text

    translated = text

    # Longest phrases first so a short key cannot partially rewrite a
    # larger UI message.
    for source, target in sorted(
        translations.items(),
        key=lambda item: len(str(item[0])),
        reverse=True,
    ):
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        if source in translated:
            translated = translated.replace(source, target)

    return translated


async def translate_text(
    text: str,
    user_id: int | None = None,
) -> str:
    if not isinstance(
        text,
        str,
    ) or not text:
        return text

    uid = (
        user_id
        if user_id is not None
        else _CURRENT_USER_ID.get()
    )

    language = await get_user_language(
        uid
    )

    if language == "en":
        return text

    return await asyncio.to_thread(
        _translate_sync,
        text,
        language,
    )


async def get_text(
    text: str,
    user_id: int | None = None,
    language: str | None = None,
) -> str:
    if language is not None:
        normalized = (
            language.lower().strip().replace("_", "-").split("-", 1)[0]
        )
        return await asyncio.to_thread(
            _translate_sync,
            text,
            normalized,
        )

    return await translate_text(
        text,
        user_id=user_id,
    )


def _safe_limit(
    text: str,
    maximum: int,
) -> str:
    if not isinstance(
        text,
        str,
    ):
        return text

    if len(text) <= maximum:
        return text

    # Leave a small marker instead of allowing Telegram to reject
    # the whole message with "Message is too long".
    return (
        text[: maximum - 3]
        + "..."
    )


async def _translate_markup(
    reply_markup,
    user_id: int | None = None,
):
    if reply_markup is None:
        return None

    keyboard = getattr(
        reply_markup,
        "inline_keyboard",
        None,
    )

    if keyboard is None:
        return reply_markup

    from telegram import (
        InlineKeyboardButton,
        InlineKeyboardMarkup,
    )

    rows = []

    for row in keyboard:
        new_row = []

        for button in row:
            if not isinstance(
                button,
                InlineKeyboardButton,
            ):
                new_row.append(button)
                continue

            translated_text = (
                await translate_text(
                    button.text or "",
                    user_id=user_id,
                )
            )

            # Telegram button labels are not the same as message
            # captions, but keeping them bounded avoids pathological
            # translator output.
            translated_text = _safe_limit(
                translated_text,
                256,
            )

            kwargs = {
                "text": translated_text,
                "url": button.url,
                "callback_data": button.callback_data,
                "web_app": button.web_app,
                "login_url": button.login_url,
                "switch_inline_query": (
                    button.switch_inline_query
                ),
                "switch_inline_query_current_chat": (
                    button.switch_inline_query_current_chat
                ),
                "callback_game": button.callback_game,
                "pay": button.pay,
            }

            # copy_text is not available in every python-telegram-bot
            # version, so add it only when the installed version exposes it.
            if hasattr(
                button,
                "copy_text",
            ):
                kwargs["copy_text"] = (
                    button.copy_text
                )

            try:
                new_button = (
                    InlineKeyboardButton(
                        **kwargs
                    )
                )
            except TypeError:
                kwargs.pop(
                    "copy_text",
                    None,
                )
                new_button = (
                    InlineKeyboardButton(
                        **kwargs
                    )
                )

            new_row.append(
                new_button
            )

        rows.append(new_row)

    return InlineKeyboardMarkup(
        rows
    )


async def _translate_payload(
    text: str | None,
    reply_markup,
    *,
    user_id: int | None,
    limit: int,
):
    translated_text = text

    if isinstance(
        text,
        str,
    ):
        translated_text = (
            await translate_text(
                text,
                user_id=user_id,
            )
        )
        translated_text = _safe_limit(
            translated_text,
            limit,
        )

    translated_markup = (
        await _translate_markup(
            reply_markup,
            user_id=user_id,
        )
        if reply_markup is not None
        else None
    )

    return (
        translated_text,
        translated_markup,
    )


async def _safe_original_call(
    operation,
    *,
    operation_name: str,
):
    """
    Telegram's 'Message is not modified' is a harmless state, not
    a bot failure. Do not retry it and do not print an error.
    """
    try:
        return await operation()

    except Exception as error:
        error_text = str(error)

        if (
            "Message is not modified"
            in error_text
        ):
            return None

        # Do not hide real Telegram errors. The handler's own error
        # handling should still see them.
        raise


def install_localization():
    global _INSTALLED

    if _INSTALLED:
        return

    from telegram import (
        Bot,
        CallbackQuery,
        Message,
    )
    from telegram.ext import (
        Application,
    )

    original_process_update = (
        Application.process_update
    )

    original_reply_text = (
        Message.reply_text
    )
    original_reply_photo = (
        Message.reply_photo
    )
    original_edit_text = (
        Message.edit_text
    )
    original_edit_caption = (
        Message.edit_caption
    )

    original_callback_edit_text = (
        CallbackQuery.edit_message_text
    )
    original_callback_edit_caption = (
        CallbackQuery.edit_message_caption
    )

    original_callback_answer = (
        CallbackQuery.answer
    )

    # Direct context.bot.edit_message_text() is used by the Friendly
    # live engine, so it also needs localization.
    original_bot_edit_text = (
        Bot.edit_message_text
    )
    original_bot_edit_caption = (
        Bot.edit_message_caption
    )

    async def process_update(
        self,
        update,
    ):
        user = getattr(
            update,
            "effective_user",
            None,
        )

        token = set_current_user_id(
            user.id
            if user is not None
            else None
        )

        try:
            return await original_process_update(
                self,
                update,
            )
        finally:
            reset_current_user_id(
                token
            )

    async def reply_text(
        self,
        text,
        *args,
        **kwargs,
    ):
        if _TRANSLATION_ACTIVE.get():
            return await original_reply_text(
                self,
                text,
                *args,
                **kwargs,
            )

        token = _TRANSLATION_ACTIVE.set(
            True
        )

        try:
            user_id = (
                _CURRENT_USER_ID.get()
            )

            text, markup = (
                await _translate_payload(
                    text,
                    kwargs.get(
                        "reply_markup"
                    ),
                    user_id=user_id,
                    limit=MAX_TEXT_LENGTH,
                )
            )

            if (
                "reply_markup"
                in kwargs
            ):
                kwargs["reply_markup"] = (
                    markup
                )

            return await original_reply_text(
                self,
                text,
                *args,
                **kwargs,
            )

        finally:
            _TRANSLATION_ACTIVE.reset(
                token
            )

    async def reply_photo(
        self,
        photo,
        *args,
        **kwargs,
    ):
        if _TRANSLATION_ACTIVE.get():
            return await original_reply_photo(
                self,
                photo,
                *args,
                **kwargs,
            )

        token = _TRANSLATION_ACTIVE.set(
            True
        )

        try:
            user_id = (
                _CURRENT_USER_ID.get()
            )

            caption, markup = (
                await _translate_payload(
                    kwargs.get("caption"),
                    kwargs.get(
                        "reply_markup"
                    ),
                    user_id=user_id,
                    limit=MAX_CAPTION_LENGTH,
                )
            )

            if "caption" in kwargs:
                kwargs["caption"] = (
                    caption
                )

            if (
                "reply_markup"
                in kwargs
            ):
                kwargs["reply_markup"] = (
                    markup
                )

            return await original_reply_photo(
                self,
                photo,
                *args,
                **kwargs,
            )

        finally:
            _TRANSLATION_ACTIVE.reset(
                token
            )

    async def edit_text(
        self,
        text,
        *args,
        **kwargs,
    ):
        if _TRANSLATION_ACTIVE.get():
            return await original_edit_text(
                self,
                text,
                *args,
                **kwargs,
            )

        token = _TRANSLATION_ACTIVE.set(
            True
        )

        try:
            user_id = (
                _CURRENT_USER_ID.get()
            )

            text, markup = (
                await _translate_payload(
                    text,
                    kwargs.get(
                        "reply_markup"
                    ),
                    user_id=user_id,
                    limit=MAX_TEXT_LENGTH,
                )
            )

            if (
                "reply_markup"
                in kwargs
            ):
                kwargs["reply_markup"] = (
                    markup
                )

            return await _safe_original_call(
                lambda: original_edit_text(
                    self,
                    text,
                    *args,
                    **kwargs,
                ),
                operation_name="message edit",
            )

        finally:
            _TRANSLATION_ACTIVE.reset(
                token
            )

    async def edit_caption(
        self,
        caption=None,
        *args,
        **kwargs,
    ):
        if _TRANSLATION_ACTIVE.get():
            return await original_edit_caption(
                self,
                caption=caption,
                *args,
                **kwargs,
            )

        token = _TRANSLATION_ACTIVE.set(
            True
        )

        try:
            user_id = (
                _CURRENT_USER_ID.get()
            )

            caption, markup = (
                await _translate_payload(
                    caption,
                    kwargs.get(
                        "reply_markup"
                    ),
                    user_id=user_id,
                    limit=MAX_CAPTION_LENGTH,
                )
            )

            if (
                "reply_markup"
                in kwargs
            ):
                kwargs["reply_markup"] = (
                    markup
                )

            return await _safe_original_call(
                lambda: original_edit_caption(
                    self,
                    caption=caption,
                    *args,
                    **kwargs,
                ),
                operation_name="caption edit",
            )

        finally:
            _TRANSLATION_ACTIVE.reset(
                token
            )

    async def callback_edit_text(
        self,
        text,
        *args,
        **kwargs,
    ):
        if _TRANSLATION_ACTIVE.get():
            return await original_callback_edit_text(
                self,
                text,
                *args,
                **kwargs,
            )

        token = _TRANSLATION_ACTIVE.set(
            True
        )

        try:
            user_id = (
                _CURRENT_USER_ID.get()
            )

            text, markup = (
                await _translate_payload(
                    text,
                    kwargs.get(
                        "reply_markup"
                    ),
                    user_id=user_id,
                    limit=MAX_TEXT_LENGTH,
                )
            )

            if (
                "reply_markup"
                in kwargs
            ):
                kwargs["reply_markup"] = (
                    markup
                )

            return await _safe_original_call(
                lambda: original_callback_edit_text(
                    self,
                    text,
                    *args,
                    **kwargs,
                ),
                operation_name="callback text edit",
            )

        finally:
            _TRANSLATION_ACTIVE.reset(
                token
            )

    async def callback_edit_caption(
        self,
        caption=None,
        *args,
        **kwargs,
    ):
        if _TRANSLATION_ACTIVE.get():
            return await original_callback_edit_caption(
                self,
                caption=caption,
                *args,
                **kwargs,
            )

        token = _TRANSLATION_ACTIVE.set(
            True
        )

        try:
            user_id = (
                _CURRENT_USER_ID.get()
            )

            caption, markup = (
                await _translate_payload(
                    caption,
                    kwargs.get(
                        "reply_markup"
                    ),
                    user_id=user_id,
                    limit=MAX_CAPTION_LENGTH,
                )
            )

            if (
                "reply_markup"
                in kwargs
            ):
                kwargs["reply_markup"] = (
                    markup
                )

            return await _safe_original_call(
                lambda: original_callback_edit_caption(
                    self,
                    caption=caption,
                    *args,
                    **kwargs,
                ),
                operation_name="callback caption edit",
            )

        finally:
            _TRANSLATION_ACTIVE.reset(
                token
            )

    async def callback_answer(
        self,
        text=None,
        *args,
        **kwargs,
    ):
        if _TRANSLATION_ACTIVE.get():
            return await original_callback_answer(
                self,
                text=text,
                *args,
                **kwargs,
            )

        token = _TRANSLATION_ACTIVE.set(True)

        try:
            user_id = _CURRENT_USER_ID.get()

            if isinstance(text, str):
                text = await translate_text(
                    text,
                    user_id=user_id,
                )
                text = _safe_limit(text, 200)

            return await original_callback_answer(
                self,
                text=text,
                *args,
                **kwargs,
            )
        finally:
            _TRANSLATION_ACTIVE.reset(token)

    async def bot_edit_text(
        self,
        *args,
        **kwargs,
    ):
        if _TRANSLATION_ACTIVE.get():
            return await original_bot_edit_text(
                self,
                *args,
                **kwargs,
            )

        token = _TRANSLATION_ACTIVE.set(
            True
        )

        try:
            user_id = (
                _CURRENT_USER_ID.get()
            )

            text = kwargs.get(
                "text"
            )

            if text is None and len(args) >= 3:
                # Bot.edit_message_text signature:
                # chat_id, message_id, text, ...
                text = args[2]

            markup = kwargs.get(
                "reply_markup"
            )

            text, markup = (
                await _translate_payload(
                    text,
                    markup,
                    user_id=user_id,
                    limit=MAX_TEXT_LENGTH,
                )
            )

            if "text" in kwargs:
                kwargs["text"] = text
            elif len(args) >= 3:
                args = list(args)
                args[2] = text
                args = tuple(args)

            if (
                "reply_markup"
                in kwargs
            ):
                kwargs["reply_markup"] = (
                    markup
                )

            return await _safe_original_call(
                lambda: original_bot_edit_text(
                    self,
                    *args,
                    **kwargs,
                ),
                operation_name="bot text edit",
            )

        finally:
            _TRANSLATION_ACTIVE.reset(
                token
            )

    async def bot_edit_caption(
        self,
        *args,
        **kwargs,
    ):
        if _TRANSLATION_ACTIVE.get():
            return await original_bot_edit_caption(
                self,
                *args,
                **kwargs,
            )

        token = _TRANSLATION_ACTIVE.set(
            True
        )

        try:
            user_id = (
                _CURRENT_USER_ID.get()
            )

            caption = kwargs.get(
                "caption"
            )

            # Bot.edit_message_caption:
            # chat_id, message_id, caption, ...
            if caption is None and len(args) >= 3:
                caption = args[2]

            markup = kwargs.get(
                "reply_markup"
            )

            caption, markup = (
                await _translate_payload(
                    caption,
                    markup,
                    user_id=user_id,
                    limit=MAX_CAPTION_LENGTH,
                )
            )

            if "caption" in kwargs:
                kwargs["caption"] = (
                    caption
                )
            elif len(args) >= 3:
                args = list(args)
                args[2] = caption
                args = tuple(args)

            if (
                "reply_markup"
                in kwargs
            ):
                kwargs["reply_markup"] = (
                    markup
                )

            return await _safe_original_call(
                lambda: original_bot_edit_caption(
                    self,
                    *args,
                    **kwargs,
                ),
                operation_name="bot caption edit",
            )

        finally:
            _TRANSLATION_ACTIVE.reset(
                token
            )

    Application.process_update = (
        process_update
    )

    Message.reply_text = (
        reply_text
    )
    Message.reply_photo = (
        reply_photo
    )
    Message.edit_text = (
        edit_text
    )
    Message.edit_caption = (
        edit_caption
    )

    CallbackQuery.edit_message_text = (
        callback_edit_text
    )
    CallbackQuery.edit_message_caption = (
        callback_edit_caption
    )

    CallbackQuery.answer = (
        callback_answer
    )

    Bot.edit_message_text = (
        bot_edit_text
    )
    Bot.edit_message_caption = (
        bot_edit_caption
    )

    _INSTALLED = True