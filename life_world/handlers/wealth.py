"""
MANUWORLD — WEALTH HANDLER

Interface Telegram du patrimoine du joueur.

Commande :
    /wealth

Ce handler utilise wealth_system.py.
Il ne modifie pas main.py.
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

from life_world.systems.wealth_system import (
    calculate_wealth,
)


# ============================================================
# UTILITAIRES
# ============================================================

def format_money(
    amount: int | float | None,
) -> str:

    return f"{int(amount or 0):,}".replace(",", " ")


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

def format_wealth(
    wealth: dict[str, Any],
) -> str:

    cash = int(
        wealth.get("cash") or 0
    )

    properties = int(
        wealth.get("properties") or 0
    )

    inventory = int(
        wealth.get("inventory") or 0
    )

    credit_debt = int(
        wealth.get("credit_debt") or 0
    )

    gross = int(
        wealth.get("gross_wealth") or 0
    )

    net = int(
        wealth.get("net_wealth") or 0
    )

    return (
        "💰━━━━━━━━━━━━━━━━━━━━💰\n"
        "          𝗣𝗔𝗧𝗥𝗜𝗠𝗢𝗜𝗡𝗘\n"
        "💰━━━━━━━━━━━━━━━━━━━━💰\n\n"
        f"💵 Argent liquide : "
        f"{format_money(cash)} FCFA\n\n"
        f"🏠 Propriétés : "
        f"{format_money(properties)} FCFA\n"
        f"🎒 Inventaire : "
        f"{format_money(inventory)} FCFA\n\n"
        f"📊 Patrimoine brut : "
        f"{format_money(gross)} FCFA\n"
        f"💳 Dette crédit : "
        f"{format_money(credit_debt)} FCFA\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 **PATRIMOINE NET : "
        f"{format_money(net)} FCFA**"
    )


def wealth_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔄 Actualiser",
                    callback_data="wealth:refresh",
                )
            ]
        ]
    )


# ============================================================
# COMMANDE
# ============================================================

async def wealth_command(
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

    wealth = calculate_wealth(
        actor.get("username")
        or actor.get("telegram_username")
        or ""
    )

    await message.reply_text(
        format_wealth(wealth),
        reply_markup=wealth_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACK
# ============================================================

async def wealth_callback(
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

    username = (
        actor.get("username")
        or actor.get("telegram_username")
        or ""
    )

    if not username:

        await query.edit_message_text(
            "❌ Username du personnage introuvable."
        )

        return

    wealth = calculate_wealth(
        username
    )

    await query.edit_message_text(
        format_wealth(wealth),
        reply_markup=wealth_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# ENREGISTREMENT
# ============================================================

def register_wealth_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "wealth",
            wealth_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            wealth_callback,
            pattern=r"^wealth:",
        )
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "wealth_command",
    "wealth_callback",
    "register_wealth_handlers",
]