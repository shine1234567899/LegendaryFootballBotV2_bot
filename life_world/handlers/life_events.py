"""
MANUWORLD — LIFE EVENTS HANDLER

Interface Telegram pour l'historique des événements de vie.

Commande :
    /events
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

from life_world.systems.life_events_system import (
    get_life_events,
    get_event_statistics,
    format_event_history,
)


# ============================================================
# UTILITAIRE
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
# MENU
# ============================================================

def events_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📜 Historique",
                    callback_data="life_events:list",
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 Statistiques",
                    callback_data="life_events:stats",
                )
            ],
        ]
    )


# ============================================================
# /EVENTS
# ============================================================

async def events_command(
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

    events = await get_life_events(
        int(actor["id"]),
        limit=10,
    )

    await message.reply_text(
        format_event_history(events),
        reply_markup=events_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# HISTORIQUE
# ============================================================

async def show_events(
    query,
    character_id: int,
):

    events = await get_life_events(
        character_id,
        limit=20,
    )

    await query.edit_message_text(
        format_event_history(events),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📊 Statistiques",
                        callback_data="life_events:stats",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔄 Actualiser",
                        callback_data="life_events:list",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Retour",
                        callback_data="life_events:home",
                    )
                ],
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# STATISTIQUES
# ============================================================

async def show_statistics(
    query,
    character_id: int,
):

    stats = await get_event_statistics(
        character_id
    )

    total_events = int(
        stats.get("total_events", 0)
    )

    total_xp = int(
        stats.get("total_xp", 0)
    )

    total_money = int(
        stats.get("total_money", 0)
    )

    money_sign = (
        "+"
        if total_money > 0
        else ""
    )

    lines = [
        "📊━━━━━━━━━━━━━━━━━━━━📊",
        "      𝗦𝗧𝗔𝗧𝗜𝗦𝗧𝗜𝗤𝗨𝗘𝗦 𝗗𝗘 𝗩𝗜𝗘",
        "📊━━━━━━━━━━━━━━━━━━━━📊",
        "",
        f"📜 Événements : {total_events}",
        f"✨ XP générée : {total_xp}",
        (
            f"💰 Variation argent : "
            f"{money_sign}{total_money:,}"
            " FCFA"
        ).replace(",", " "),
        "",
    ]

    by_type = stats.get(
        "by_type",
        [],
    )

    if by_type:

        lines.extend(
            [
                "🏷️ **PAR TYPE**",
                "",
            ]
        )

        for row in by_type:

            event_type = row.get(
                "event_type",
                "life",
            )

            count = int(
                row.get("count", 0)
            )

            lines.append(
                f"• {event_type} : {count}"
            )

    else:

        lines.append(
            "Aucun événement enregistré."
        )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📜 Historique",
                        callback_data="life_events:list",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Retour",
                        callback_data="life_events:home",
                    )
                ],
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACK
# ============================================================

async def life_events_callback(
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

    character_id = int(
        actor["id"]
    )

    data = str(
        query.data or ""
    )

    if data == "life_events:home":

        await query.edit_message_text(
            (
                "📜━━━━━━━━━━━━━━━━━━━━📜\n"
                "       𝗘́𝗩𝗘́𝗡𝗘𝗠𝗘𝗡𝗧𝗦 𝗗𝗘 𝗩𝗜𝗘\n"
                "📜━━━━━━━━━━━━━━━━━━━━📜\n\n"
                "Consulte ton historique de vie."
            ),
            reply_markup=events_keyboard(),
        )

        return

    if data == "life_events:list":

        await show_events(
            query,
            character_id,
        )

        return

    if data == "life_events:stats":

        await show_statistics(
            query,
            character_id,
        )

        return

    await query.edit_message_text(
        "❌ Action inconnue."
    )


# ============================================================
# ENREGISTREMENT
# ============================================================

def register_life_events_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "events",
            events_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            life_events_callback,
            pattern=r"^life_events:",
        )
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "events_command",
    "life_events_callback",
    "register_life_events_handlers",
]