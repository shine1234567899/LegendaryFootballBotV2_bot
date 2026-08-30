"""
MANUWORLD — EXPENSES HANDLER

Commandes :
    /expenses
    /expense <categorie> <montant> <description>
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

from life_world.systems.expenses_system import (
    add_expense,
    get_expenses,
    get_expense_statistics,
    format_expenses,
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


def expenses_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📜 Historique",
                    callback_data="expenses:list",
                ),
                InlineKeyboardButton(
                    "📊 Statistiques",
                    callback_data="expenses:stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔄 Actualiser",
                    callback_data="expenses:list",
                )
            ],
        ]
    )


# ============================================================
# /EXPENSES
# ============================================================

async def expenses_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:
        return

    actor = await get_actor(update)

    if actor is None:
        await message.reply_text(
            "❌ Tu n'as pas encore créé ton personnage MANUWORLD."
        )
        return

    expenses = await get_expenses(
        int(actor["id"]),
        limit=20,
    )

    await message.reply_text(
        format_expenses(expenses),
        reply_markup=expenses_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# /EXPENSE
# ============================================================

async def expense_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message

    if message is None:
        return

    actor = await get_actor(update)

    if actor is None:
        await message.reply_text(
            "❌ Tu n'as pas encore créé ton personnage MANUWORLD."
        )
        return

    if len(context.args) < 3:

        await message.reply_text(
            "💸 **AJOUTER UNE DÉPENSE**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Utilisation :\n"
            "`/expense <catégorie> <montant> <description>`\n\n"
            "Exemple :\n"
            "`/expense food 2500 Déjeuner`",
            parse_mode="Markdown",
        )

        return

    category = context.args[0]

    try:
        amount = int(context.args[1])
    except ValueError:

        await message.reply_text(
            "❌ Le montant doit être un nombre."
        )

        return

    description = " ".join(
        context.args[2:]
    )

    result = await add_expense(
        character_id=int(actor["id"]),
        category=category,
        description=description,
        amount=amount,
    )

    await message.reply_text(
        result.get(
            "message",
            "❌ Impossible d'enregistrer la dépense.",
        )
    )


# ============================================================
# HISTORIQUE
# ============================================================

async def show_expenses(
    query,
    character_id: int,
):

    expenses = await get_expenses(
        character_id,
        limit=20,
    )

    await query.edit_message_text(
        format_expenses(expenses),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📊 Statistiques",
                        callback_data="expenses:stats",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔄 Actualiser",
                        callback_data="expenses:list",
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

    stats = await get_expense_statistics(
        character_id
    )

    lines = [
        "📊━━━━━━━━━━━━━━━━━━━━📊",
        "      𝗦𝗧𝗔𝗧𝗜𝗦𝗧𝗜𝗤𝗨𝗘𝗦 𝗗𝗘́𝗣𝗘𝗡𝗦𝗘𝗦",
        "📊━━━━━━━━━━━━━━━━━━━━📊",
        "",
        f"🧾 Nombre : {stats['count']}",
        f"💰 Total : {stats['total']:,} FCFA".replace(",", " "),
        f"📈 Moyenne : {stats['average']:,} FCFA".replace(",", " "),
        "",
    ]

    categories = stats.get(
        "by_category",
        [],
    )

    if categories:

        lines.append(
            "📂 **PAR CATÉGORIE**"
        )
        lines.append("")

        for row in categories:

            category = row.get(
                "category",
                "other",
            )

            count = int(
                row.get("count") or 0
            )

            total = int(
                row.get("total") or 0
            )

            lines.append(
                f"• {category} — "
                f"{count} dépense(s) — "
                f"{total:,} FCFA".replace(
                    ",",
                    " ",
                )
            )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📜 Historique",
                        callback_data="expenses:list",
                    )
                ]
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACK
# ============================================================

async def expenses_callback(
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

    if data == "expenses:list":

        await show_expenses(
            query,
            character_id,
        )

        return

    if data == "expenses:stats":

        await show_statistics(
            query,
            character_id,
        )

        return

    await query.edit_message_text(
        "❌ Action inconnue."
    )


# ============================================================
# REGISTRATION
# ============================================================

def register_expenses_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "expenses",
            expenses_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "expense",
            expense_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            expenses_callback,
            pattern=r"^expenses:",
        )
    )


__all__ = [
    "expenses_command",
    "expense_command",
    "expenses_callback",
    "register_expenses_handlers",
]