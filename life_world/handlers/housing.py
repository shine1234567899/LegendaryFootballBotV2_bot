"""
MANUWORLD — HOUSING HANDLER

Interface Telegram du système de logement.

Moteur métier :
    life_world/systems/housing_system.py

Commande :
    /housing

IMPORTANT :
    Ce fichier ne modifie pas main.py.
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

from life_world.systems.housing_system import (
    housing_catalog,
    format_housing_catalog,
    housing_catalog_buttons,
    housing_action_buttons,
    current_housing_buttons,
    format_current_housing,
    parse_housing_callback,
)


# ============================================================
# UTILITAIRES
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


def buttons_to_markup(
    buttons: list[list[tuple[str, str]]],
) -> InlineKeyboardMarkup:

    keyboard = []

    for row in buttons:

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=data,
                )
                for data, label in row
            ]
        )

    return InlineKeyboardMarkup(
        keyboard
    )


# ============================================================
# /HOUSING
# ============================================================

async def housing_command(
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

    await message.reply_text(
        (
            "🏠━━━━━━━━━━━━━━━━━━━━🏠\n"
            "       𝗠𝗔𝗡𝗨𝗪𝗢𝗥𝗟𝗗 𝗛𝗢𝗨𝗦𝗜𝗡𝗚\n"
            "🏠━━━━━━━━━━━━━━━━━━━━🏠\n\n"
            "Bienvenue dans le système immobilier.\n\n"
            "Tu peux louer ou acheter un logement."
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🏘️ Catalogue",
                        callback_data="lw_housing:view",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Mon logement",
                        callback_data="lw_housing:current",
                    )
                ],
            ]
        ),
    )


# ============================================================
# CATALOGUE
# ============================================================

async def show_housing_catalog(
    query,
):

    text = format_housing_catalog()

    buttons = housing_catalog_buttons()

    await query.edit_message_text(
        text,
        reply_markup=buttons_to_markup(
            buttons
        ),
        parse_mode="HTML",
    )


# ============================================================
# DÉTAIL LOGEMENT
# ============================================================

async def show_housing_details(
    query,
    housing_type: str,
):

    catalog = housing_catalog()

    definition = catalog.get(
        housing_type
    )

    if definition is None:

        await query.edit_message_text(
            "❌ Type de logement introuvable."
        )

        return

    name = definition.get(
        "name",
        housing_type,
    )

    description = definition.get(
        "description",
        "",
    )

    daily_rent = int(
        definition.get("daily_rent", 0)
        or 0
    )

    purchase_price = definition.get(
        "purchase_price"
    )

    lines = [
        "🏠━━━━━━━━━━━━━━━━━━━━🏠",
        f"        {name}",
        "🏠━━━━━━━━━━━━━━━━━━━━🏠",
        "",
    ]

    if description:

        lines.extend(
            [
                f"📝 {description}",
                "",
            ]
        )

    lines.append(
        f"💰 Loyer quotidien : "
        f"{daily_rent:,} FCFA"
    )

    if purchase_price is not None:

        lines.append(
            f"🏡 Prix d'achat : "
            f"{int(purchase_price):,} FCFA"
        )

    buttons = housing_action_buttons(
        housing_type
    )

    buttons.append(
        [
            (
                "lw_housing:view",
                "⬅️ Catalogue",
            )
        ]
    )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=buttons_to_markup(
            buttons
        ),
    )


# ============================================================
# LOGEMENT ACTUEL
# ============================================================

async def show_current_housing(
    query,
    username: str,
):

    text = format_current_housing(
        username
    )

    buttons = current_housing_buttons()

    buttons.append(
        [
            (
                "lw_housing:view",
                "🏘️ Catalogue",
            )
        ]
    )

    await query.edit_message_text(
        text,
        reply_markup=buttons_to_markup(
            buttons
        ),
        parse_mode="HTML",
    )


# ============================================================
# ACTION
# ============================================================

async def execute_housing_action(
    query,
    actor: dict[str, Any],
    action_data: dict,
):

    action = action_data["action"]

    housing_type = action_data.get(
        "housing_type"
    )

    # --------------------------------------------------------
    # CATALOGUE
    # --------------------------------------------------------

    if action == "view":

        await show_housing_catalog(
            query
        )

        return

    # --------------------------------------------------------
    # LOGEMENT ACTUEL
    # --------------------------------------------------------

    if action == "current":

        username = str(
            actor.get("username") or ""
        )

        await show_current_housing(
            query,
            username,
        )

        return

    # --------------------------------------------------------
    # LOUER
    # --------------------------------------------------------

    if action == "rent":

        if not housing_type:

            await query.edit_message_text(
                "❌ Type de logement manquant."
            )

            return

        await query.edit_message_text(
            (
                "🔑━━━━━━━━━━━━━━━━━━━━🔑\n"
                "          𝗟𝗢𝗖𝗔𝗧𝗜𝗢𝗡\n"
                "🔑━━━━━━━━━━━━━━━━━━━━🔑\n\n"
                f"🏠 Logement : {housing_type}\n\n"
                "Confirmer la location ?"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Confirmer",
                            callback_data=(
                                f"lw_housing:confirmrent:"
                                f"{housing_type}"
                            ),
                        ),
                        InlineKeyboardButton(
                            "❌ Annuler",
                            callback_data=(
                                "lw_housing:view"
                            ),
                        ),
                    ]
                ]
            ),
        )

        return

    # --------------------------------------------------------
    # ACHETER
    # --------------------------------------------------------

    if action == "buy":

        if not housing_type:

            await query.edit_message_text(
                "❌ Type de logement manquant."
            )

            return

        await query.edit_message_text(
            (
                "🏡━━━━━━━━━━━━━━━━━━━━🏡\n"
                "          𝗔𝗖𝗛𝗔𝗧\n"
                "🏡━━━━━━━━━━━━━━━━━━━━🏡\n\n"
                f"🏠 Logement : {housing_type}\n\n"
                "Confirmer l'achat ?"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Confirmer",
                            callback_data=(
                                f"lw_housing:confirmbuy:"
                                f"{housing_type}"
                            ),
                        ),
                        InlineKeyboardButton(
                            "❌ Annuler",
                            callback_data=(
                                "lw_housing:view"
                            ),
                        ),
                    ]
                ]
            ),
        )

        return

    # --------------------------------------------------------
    # PAYER LOYER
    # --------------------------------------------------------

    if action == "payrent":

        await query.edit_message_text(
            (
                "🧾━━━━━━━━━━━━━━━━━━━━🧾\n"
                "          𝗟𝗢𝗬𝗘𝗥\n"
                "🧾━━━━━━━━━━━━━━━━━━━━🧾\n\n"
                "Confirmer le paiement du loyer ?"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Payer",
                            callback_data=(
                                "lw_housing:confirmpayrent"
                            ),
                        ),
                        InlineKeyboardButton(
                            "❌ Annuler",
                            callback_data=(
                                "lw_housing:current"
                            ),
                        ),
                    ]
                ]
            ),
        )

        return

    # --------------------------------------------------------
    # QUITTER
    # --------------------------------------------------------

    if action == "leave":

        await query.edit_message_text(
            (
                "🚪━━━━━━━━━━━━━━━━━━━━🚪\n"
                "        𝗤𝗨𝗜𝗧𝗧𝗘𝗥\n"
                "🚪━━━━━━━━━━━━━━━━━━━━🚪\n\n"
                "Confirmer que tu veux quitter "
                "ton logement ?"
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Confirmer",
                            callback_data=(
                                "lw_housing:confirmleave"
                            ),
                        ),
                        InlineKeyboardButton(
                            "❌ Annuler",
                            callback_data=(
                                "lw_housing:current"
                            ),
                        ),
                    ]
                ]
            ),
        )

        return

    await query.edit_message_text(
        "❌ Action logement inconnue."
    )


# ============================================================
# CALLBACKS
# ============================================================

async def housing_callback(
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

    data = str(
        query.data or ""
    )

    # --------------------------------------------------------
    # ACTIONS DE CONFIRMATION
    # --------------------------------------------------------

    if data.startswith(
        "lw_housing:confirmrent:"
    ):

        housing_type = data.split(
            ":",
            2,
        )[2]

        username = str(
            actor.get("username") or ""
        )

        from life_world.systems.housing_system import (
            rent_housing,
        )

        result = rent_housing(
            username,
            housing_type,
        )

        await query.edit_message_text(
            result.get(
                "message",
                "❌ Location impossible.",
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏠 Mon logement",
                            callback_data=(
                                "lw_housing:current"
                            ),
                        )
                    ]
                ]
            ),
        )

        return

    if data.startswith(
        "lw_housing:confirmbuy:"
    ):

        housing_type = data.split(
            ":",
            2,
        )[2]

        username = str(
            actor.get("username") or ""
        )

        from life_world.systems.housing_system import (
            buy_housing,
        )

        result = buy_housing(
            username,
            housing_type,
            int(actor.get("balance") or 0),
        )

        await query.edit_message_text(
            result.get(
                "message",
                "❌ Achat impossible.",
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏠 Mon logement",
                            callback_data=(
                                "lw_housing:current"
                            ),
                        )
                    ]
                ]
            ),
        )

        return

    if data == "lw_housing:confirmpayrent":

        username = str(
            actor.get("username") or ""
        )

        from life_world.systems.housing_system import (
            pay_rent,
        )

        result = pay_rent(
            username,
            int(actor.get("balance") or 0),
        )

        await query.edit_message_text(
            result.get(
                "message",
                "❌ Paiement impossible.",
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏠 Mon logement",
                            callback_data=(
                                "lw_housing:current"
                            ),
                        )
                    ]
                ]
            ),
        )

        return

    if data == "lw_housing:confirmleave":

        username = str(
            actor.get("username") or ""
        )

        from life_world.systems.housing_system import (
            leave_housing,
        )

        result = leave_housing(
            username
        )

        await query.edit_message_text(
            result.get(
                "message",
                "❌ Impossible de quitter le logement.",
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏘️ Catalogue",
                            callback_data=(
                                "lw_housing:view"
                            ),
                        )
                    ]
                ]
            ),
        )

        return

    # --------------------------------------------------------
    # ACTIONS NORMALES
    # --------------------------------------------------------

    if data == "lw_housing:current":

        await show_current_housing(
            query,
            str(actor.get("username") or ""),
        )

        return

    try:

        parsed = parse_housing_callback(
            data
        )

    except ValueError:

        await query.edit_message_text(
            "❌ Action logement invalide."
        )

        return

    await execute_housing_action(
        query,
        actor,
        parsed,
    )


# ============================================================
# REGISTRATION
# ============================================================

def register_housing_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "housing",
            housing_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            housing_callback,
            pattern=r"^lw_housing:",
        )
    )


__all__ = [
    "housing_command",
    "housing_callback",
    "register_housing_handlers",
]