"""
MANUWORLD — INVENTORY HANDLER

Interface Telegram de l'inventaire.

Commande :
    /inventory

IMPORTANT :
    Le branchement dans main.py sera effectué à la fin.
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

from life_world.database import (
    AsyncSessionLocal,
    get_life_character,
)

from sqlalchemy import text


# ============================================================
# UTILITAIRES
# ============================================================

def format_money(amount: int) -> str:
    return f"{int(amount):,}".replace(",", " ")


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
# INVENTAIRE
# ============================================================

async def get_inventory(
    character_id: int,
) -> list[dict[str, Any]]:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    i.id,
                    i.character_id,
                    i.item_name,
                    i.quantity,
                    i.item_data
                FROM life_inventory i
                WHERE i.character_id = :character_id
                ORDER BY i.item_name ASC
                """
            ),
            {
                "character_id": int(character_id),
            },
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


async def get_inventory_item(
    character_id: int,
    item_id: int,
) -> dict[str, Any] | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            text(
                """
                SELECT
                    id,
                    character_id,
                    item_name,
                    quantity,
                    item_data
                FROM life_inventory
                WHERE id = :item_id
                  AND character_id = :character_id
                LIMIT 1
                """
            ),
            {
                "item_id": int(item_id),
                "character_id": int(character_id),
            },
        )

        row = result.mappings().first()

        return dict(row) if row else None


# ============================================================
# MENU
# ============================================================

def inventory_keyboard(
    items: list[dict[str, Any]],
) -> InlineKeyboardMarkup:

    buttons = []

    for item in items:

        item_id = int(
            item["id"]
        )

        quantity = int(
            item["quantity"] or 0
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    (
                        f"🎒 {item['item_name'][:24]} "
                        f"×{quantity}"
                    ),
                    callback_data=(
                        f"inventory_item:{item_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "🔄 Actualiser",
                callback_data="inventory_list",
            )
        ]
    )

    return InlineKeyboardMarkup(
        buttons
    )


# ============================================================
# AFFICHAGE
# ============================================================

async def show_inventory(
    target,
    character_id: int,
):

    items = await get_inventory(
        character_id
    )

    if not items:

        text_message = (
            "🎒━━━━━━━━━━━━━━━━━━━━🎒\n"
            "          𝗜𝗡𝗩𝗘𝗡𝗧𝗔𝗜𝗥𝗘\n"
            "🎒━━━━━━━━━━━━━━━━━━━━🎒\n\n"
            "Ton inventaire est vide."
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔄 Actualiser",
                        callback_data="inventory_list",
                    )
                ]
            ]
        )

        await target.edit_message_text(
            text_message,
            reply_markup=keyboard,
        )

        return

    total_quantity = sum(
        int(item["quantity"] or 0)
        for item in items
    )

    lines = [
        "🎒━━━━━━━━━━━━━━━━━━━━🎒",
        "          𝗜𝗡𝗩𝗘𝗡𝗧𝗔𝗜𝗥𝗘",
        "🎒━━━━━━━━━━━━━━━━━━━━🎒",
        "",
        f"📦 Types d'objets : {len(items)}",
        f"🔢 Quantité totale : {total_quantity}",
        "",
    ]

    for item in items:

        lines.append(
            f"🎁 {item['item_name']} "
            f"×{item['quantity']}"
        )

    await target.edit_message_text(
        "\n".join(lines),
        reply_markup=inventory_keyboard(
            items
        ),
    )


# ============================================================
# DÉTAIL OBJET
# ============================================================

async def show_item(
    query,
    character_id: int,
    item_id: int,
):

    item = await get_inventory_item(
        character_id,
        item_id,
    )

    if item is None:

        await query.edit_message_text(
            "❌ Objet introuvable dans ton inventaire.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Inventaire",
                            callback_data="inventory_list",
                        )
                    ]
                ]
            ),
        )

        return

    item_data = item.get(
        "item_data"
    ) or {}

    lines = [
        "🎁━━━━━━━━━━━━━━━━━━━━🎁",
        "          𝗢𝗕𝗝𝗘𝗧",
        "🎁━━━━━━━━━━━━━━━━━━━━🎁",
        "",
        f"🏷️ Nom : {item['item_name']}",
        f"🔢 Quantité : {item['quantity']}",
    ]

    if isinstance(item_data, dict):

        description = item_data.get(
            "description"
        )

        category = item_data.get(
            "category"
        )

        rarity = item_data.get(
            "rarity"
        )

        if category:
            lines.append(
                f"📂 Catégorie : {category}"
            )

        if rarity:
            lines.append(
                f"✨ Rareté : {rarity}"
            )

        if description:
            lines.extend(
                [
                    "",
                    f"📝 {description}",
                ]
            )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Inventaire",
                        callback_data="inventory_list",
                    )
                ]
            ]
        ),
    )


# ============================================================
# COMMANDE
# ============================================================

async def inventory_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    actor = await get_actor(update)

    message = update.effective_message

    if message is None:
        return

    if actor is None:

        await message.reply_text(
            "❌ Tu n'as pas encore créé "
            "ton personnage MANUWORLD."
        )

        return

    items = await get_inventory(
        int(actor["id"])
    )

    if not items:

        await message.reply_text(
            (
                "🎒━━━━━━━━━━━━━━━━━━━━🎒\n"
                "          𝗜𝗡𝗩𝗘𝗡𝗧𝗔𝗜𝗥𝗘\n"
                "🎒━━━━━━━━━━━━━━━━━━━━🎒\n\n"
                "Ton inventaire est vide."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔄 Actualiser",
                            callback_data="inventory_list",
                        )
                    ]
                ]
            ),
        )

        return

    total_quantity = sum(
        int(item["quantity"] or 0)
        for item in items
    )

    lines = [
        "🎒━━━━━━━━━━━━━━━━━━━━🎒",
        "          𝗜𝗡𝗩𝗘𝗡𝗧𝗔𝗜𝗥𝗘",
        "🎒━━━━━━━━━━━━━━━━━━━━🎒",
        "",
        f"📦 Types : {len(items)}",
        f"🔢 Objets : {total_quantity}",
        "",
    ]

    for item in items:

        lines.append(
            f"🎁 {item['item_name']} "
            f"×{item['quantity']}"
        )

    await message.reply_text(
        "\n".join(lines),
        reply_markup=inventory_keyboard(
            items
        ),
    )


# ============================================================
# CALLBACK
# ============================================================

async def inventory_callback(
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

    # --------------------------------------------------------
    # LISTE
    # --------------------------------------------------------

    if data == "inventory_list":

        await show_inventory(
            query,
            character_id,
        )

        return

    # --------------------------------------------------------
    # OBJET
    # --------------------------------------------------------

    if data.startswith(
        "inventory_item:"
    ):

        try:
            item_id = int(
                data.split(":")[1]
            )
        except (
            ValueError,
            IndexError,
        ):
            await query.edit_message_text(
                "❌ Objet invalide."
            )
            return

        await show_item(
            query,
            character_id,
            item_id,
        )

        return

    await query.edit_message_text(
        "❌ Action d'inventaire inconnue."
    )


# ============================================================
# ENREGISTREMENT
# ============================================================

def register_inventory_handlers(
    application: Application,
) -> None:

    application.add_handler(
        CommandHandler(
            "inventory",
            inventory_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            inventory_callback,
            pattern=r"^inventory_",
        )
    )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "get_inventory",
    "get_inventory_item",
    "inventory_command",
    "inventory_callback",
    "register_inventory_handlers",
]