"""
MANUWORLD — HEALTH HANDLER

Interface Telegram du système de santé.

Commande :
    /health

Affiche :
    - santé
    - énergie
    - bonheur

IMPORTANT :
    main.py n'est pas modifié ici.
"""

from __future__ import annotations

from typing import Any

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from life_world.database import get_life_character

from life_world.systems.health_system import (
    get_health_status,
    format_health_status,
)


# ============================================================
# CONSTANTES
# ============================================================

MAX_HAPPINESS = 100


# ============================================================
# ACTEUR
# ============================================================

async def get_actor(
    update: Update,
) -> dict[str, Any] | None:

    user = update.effective_user

    if user is None:
        return None

    character = await get_life_character(
        user.id
    )

    if character is None:
        return None

    return dict(character)


# ============================================================
# AFFICHAGE
# ============================================================

def format_full_status(
    status: dict[str, Any],
) -> str:

    health = int(
        status.get("health") or 0
    )

    energy = int(
        status.get("energy") or 0
    )

    happiness = int(
        status.get("happiness") or 0
    )

    return (
        "❤️━━━━━━━━━━━━━━━━━━━━❤️\n"
        "          𝗘́𝗧𝗔𝗧 𝗗𝗨 𝗣𝗘𝗥𝗦𝗢𝗡𝗡𝗔𝗚𝗘\n"
        "❤️━━━━━━━━━━━━━━━━━━━━❤️\n\n"
        f"❤️ Santé : **{health}/100**\n"
        f"⚡ Énergie : **{energy}/100**\n"
        f"😊 Bonheur : **{happiness}/100**"
    )


def health_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔄 Actualiser",
                    callback_data="health:refresh",
                )
            ]
        ]
    )


# ============================================================
# /HEALTH
# ============================================================

async def health_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:
        return

    actor = await get_actor(update)

    if actor is None:

        await message.reply_text(
            "❌ Tu n'as pas encore créé "
            "ton personnage MANUWORLD."
        )

        return

    status = await get_health_status(
        int(actor["id"])
    )

    if status is None:

        await message.reply_text(
            "❌ Impossible de récupérer "
            "l'état de ton personnage."
        )

        return

    await message.reply_text(
        format_full_status(status),
        reply_markup=health_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACK
# ============================================================

async def health_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    if query is None:
        return

    await query.answer()

    actor = await get_actor(update)

    if actor is None:

        await query.edit_message_text(
            "❌ Personnage MANUWORLD introuvable."
        )

        return

    status = await get_health_status(
        int(actor["id"])
    )

    if status is None:

        await query.edit_message_text(
            "❌ Impossible de récupérer "
            "l'état du personnage."
        )

        return

    await query.edit_message_text(
        format_full_status(status),
        reply_markup=health_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# REGISTRATION
# ============================================================

def register_health_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "health",
            health_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            health_callback,
            pattern=r"^health:",
        )
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "health_command",
    "health_callback",
    "register_health_handlers",
]