"""
MANUWORLD — CREDIT CARD HANDLER

Interface Telegram du système de cartes de crédit.

Le moteur métier se trouve dans :
    life_world/systems/credit_card_system.py

IMPORTANT :
    Ce fichier ne modifie pas main.py.
    Le branchement sera effectué lors de l'intégration finale.
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
    MessageHandler,
    filters,
)

from life_world.database import get_life_character

from life_world.systems.credit_card_system import (
    get_credit_card,
    get_character_credit_cards,
    get_credit_card_stats,
    get_credit_card_transactions,
    pay_credit_card,
    set_credit_card_status,
)


# ============================================================
# CONSTANTES
# ============================================================

TRANSACTION_LIMIT = 10


# ============================================================
# UTILITAIRES
# ============================================================

def format_money(amount: int) -> str:
    return f"{int(amount):,}".replace(",", " ")


def format_card_number(
    card_number: str,
) -> str:
    value = str(card_number or "").replace(" ", "")

    return " ".join(
        value[index:index + 4]
        for index in range(0, len(value), 4)
    )


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


async def require_actor(
    update: Update,
) -> dict[str, Any] | None:

    actor = await get_actor(update)

    if actor is not None:
        return actor

    message = update.effective_message

    if message:
        await message.reply_text(
            "❌ Tu n'as pas encore créé "
            "ton personnage MANUWORLD."
        )

    return None


# ============================================================
# MENU PRINCIPAL
# ============================================================

def card_home_keyboard() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💳 Mes cartes",
                    callback_data="card_list",
                )
            ],
        ]
    )


async def show_card_home(
    target,
    actor: dict[str, Any],
):
    cards = await get_character_credit_cards(
        int(actor["id"])
    )

    total_used = sum(
        int(card.get("used_credit") or 0)
        for card in cards
    )

    total_available = sum(
        int(card.get("available_credit") or 0)
        for card in cards
    )

    text = (
        "💳━━━━━━━━━━━━━━━━━━━━💳\n"
        "      𝗠𝗔𝗡𝗨𝗪𝗢𝗥𝗟𝗗 𝗖𝗔𝗥𝗗\n"
        "💳━━━━━━━━━━━━━━━━━━━━💳\n\n"
        f"💳 Cartes : {len(cards)}\n"
        f"📉 Crédit utilisé : "
        f"{format_money(total_used)} FCFA\n"
        f"📊 Crédit disponible : "
        f"{format_money(total_available)} FCFA\n\n"
        "Choisis une option :"
    )

    await target.edit_message_text(
        text,
        reply_markup=card_home_keyboard(),
    )


# ============================================================
# /CARD
# ============================================================

async def card_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    actor = await require_actor(update)

    if actor is None:
        return

    message = update.effective_message

    if message is None:
        return

    cards = await get_character_credit_cards(
        int(actor["id"])
    )

    if not cards:
        await message.reply_text(
            (
                "💳 TU N'AS AUCUNE CARTE\n\n"
                "Aucune carte de crédit n'est "
                "actuellement associée à ton personnage."
            ),
            reply_markup=card_home_keyboard(),
        )
        return

    await message.reply_text(
        (
            "💳━━━━━━━━━━━━━━━━━━━━💳\n"
            "      𝗠𝗔𝗡𝗨𝗪𝗢𝗥𝗟𝗗 𝗖𝗔𝗥𝗗\n"
            "💳━━━━━━━━━━━━━━━━━━━━💳\n\n"
            "Sélectionne une carte :"
        ),
        reply_markup=cards_keyboard(cards),
    )


# ============================================================
# LISTE DES CARTES
# ============================================================

def cards_keyboard(
    cards: list[dict[str, Any]],
) -> InlineKeyboardMarkup:

    buttons = []

    for card in cards:

        card_id = int(card["id"])

        name = str(
            card.get("card_name")
            or "Carte"
        )

        available = int(
            card.get("available_credit") or 0
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"💳 {name[:22]} — "
                        f"{format_money(available)} FCFA"
                    ),
                    callback_data=(
                        f"card_view:{card_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Accueil",
                callback_data="card_home",
            )
        ]
    )

    return InlineKeyboardMarkup(buttons)


async def show_cards(
    query,
    character_id: int,
):

    cards = await get_character_credit_cards(
        character_id
    )

    if not cards:
        await query.edit_message_text(
            "💳 Tu ne possèdes aucune carte.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Accueil",
                            callback_data="card_home",
                        )
                    ]
                ]
            ),
        )
        return

    lines = [
        "💳━━━━━━━━━━━━━━━━━━━━💳",
        "          𝗠𝗘𝗦 𝗖𝗔𝗥𝗧𝗘𝗦",
        "💳━━━━━━━━━━━━━━━━━━━━💳",
        "",
    ]

    for card in cards:

        used = int(
            card.get("used_credit") or 0
        )

        available = int(
            card.get("available_credit") or 0
        )

        lines.append(
            f"💳 {card['card_name']}\n"
            f"🏦 {card['bank_name']}\n"
            f"💰 Limite : "
            f"{format_money(card['credit_limit'])} FCFA\n"
            f"📉 Utilisé : "
            f"{format_money(used)} FCFA\n"
            f"📊 Disponible : "
            f"{format_money(available)} FCFA\n"
            f"🔐 Statut : {card['status']}\n"
        )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=cards_keyboard(cards),
    )


# ============================================================
# DÉTAIL D'UNE CARTE
# ============================================================

def card_actions_keyboard(
    card: dict[str, Any],
) -> InlineKeyboardMarkup:

    card_id = int(card["id"])

    status = str(
        card.get("status")
        or "active"
    )

    buttons = [
        [
            InlineKeyboardButton(
                "🧾 Historique",
                callback_data=(
                    f"card_history:{card_id}"
                ),
            ),
            InlineKeyboardButton(
                "📊 Statistiques",
                callback_data=(
                    f"card_stats:{card_id}"
                ),
            ),
        ],
        [
            InlineKeyboardButton(
                "💵 Rembourser",
                callback_data=(
                    f"card_pay:{card_id}"
                ),
            )
        ],
    ]

    if status == "active":

        buttons.append(
            [
                InlineKeyboardButton(
                    "🔒 Bloquer",
                    callback_data=(
                        f"card_block:{card_id}"
                    ),
                )
            ]
        )

    elif status == "blocked":

        buttons.append(
            [
                InlineKeyboardButton(
                    "🔓 Débloquer",
                    callback_data=(
                        f"card_unblock:{card_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Mes cartes",
                callback_data="card_list",
            )
        ]
    )

    return InlineKeyboardMarkup(buttons)


async def show_card(
    query,
    character_id: int,
    card_id: int,
):

    card = await get_credit_card(
        card_id
    )

    if card is None:
        await query.edit_message_text(
            "❌ Carte introuvable."
        )
        return

    if int(card["character_id"]) != character_id:
        await query.edit_message_text(
            "❌ Cette carte ne t'appartient pas."
        )
        return

    text = (
        "💳━━━━━━━━━━━━━━━━━━━━💳\n"
        "       𝗖𝗔𝗥𝗧𝗘 𝗗𝗘 𝗖𝗥𝗘́𝗗𝗜𝗧\n"
        "💳━━━━━━━━━━━━━━━━━━━━💳\n\n"
        f"💳 Nom : {card['card_name']}\n"
        f"🏦 Banque : {card['bank_name']}\n"
        f"🔢 Carte : "
        f"{format_card_number(card['card_number'])}\n\n"
        f"💰 Limite : "
        f"{format_money(card['credit_limit'])} FCFA\n"
        f"📉 Utilisé : "
        f"{format_money(card['used_credit'])} FCFA\n"
        f"📊 Disponible : "
        f"{format_money(card['available_credit'])} FCFA\n\n"
        f"📈 Taux : "
        f"{float(card['interest_rate'] or 0):g}%\n"
        f"🎁 Rewards : "
        f"{float(card['reward_rate'] or 0):g}%\n"
        f"⭐ Credit Score : "
        f"{card['credit_score']}\n"
        f"🔐 Statut : {card['status']}"
    )

    await query.edit_message_text(
        text,
        reply_markup=card_actions_keyboard(
            card
        ),
    )


# ============================================================
# REMBOURSEMENT
# ============================================================

async def request_card_payment(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    card_id: int,
):

    context.user_data[
        "card_pending_payment"
    ] = {
        "card_id": int(card_id),
    }

    await query.edit_message_text(
        (
            "💵━━━━━━━━━━━━━━━━━━━━💵\n"
            "       𝗥𝗘𝗠𝗕𝗢𝗨𝗥𝗦𝗘𝗠𝗘𝗡𝗧\n"
            "💵━━━━━━━━━━━━━━━━━━━━💵\n\n"
            "Envoie le montant que tu veux "
            "rembourser.\n\n"
            "Exemple :\n"
            "`50000`"
        ),
        parse_mode="Markdown",
    )


# ============================================================
# HISTORIQUE
# ============================================================

async def show_card_history(
    query,
    character_id: int,
    card_id: int,
):

    card = await get_credit_card(
        card_id
    )

    if card is None:
        await query.edit_message_text(
            "❌ Carte introuvable."
        )
        return

    if int(card["character_id"]) != character_id:
        await query.edit_message_text(
            "❌ Cette carte ne t'appartient pas."
        )
        return

    transactions = await get_credit_card_transactions(
        card_id,
        limit=TRANSACTION_LIMIT,
    )

    if not transactions:
        await query.edit_message_text(
            (
                "🧾 Aucun mouvement enregistré "
                "sur cette carte."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Carte",
                            callback_data=(
                                f"card_view:{card_id}"
                            ),
                        )
                    ]
                ]
            ),
        )
        return

    lines = [
        "🧾━━━━━━━━━━━━━━━━━━━━🧾",
        "      𝗛𝗜𝗦𝗧𝗢𝗥𝗜𝗤𝗨𝗘 𝗖𝗔𝗥𝗧𝗘",
        "🧾━━━━━━━━━━━━━━━━━━━━🧾",
        "",
    ]

    for transaction in transactions:

        transaction_type = str(
            transaction.get("transaction_type")
            or "transaction"
        )

        amount = int(
            transaction.get("amount") or 0
        )

        reward = int(
            transaction.get("reward_earned") or 0
        )

        sign = "+" if amount >= 0 else ""

        merchant = transaction.get(
            "merchant"
        )

        description = transaction.get(
            "description"
        )

        lines.append(
            f"💳 {transaction_type}\n"
            f"💵 {sign}{format_money(amount)} FCFA\n"
        )

        if merchant:
            lines.append(
                f"🏪 {merchant}\n"
            )

        if description:
            lines.append(
                f"📝 {description}\n"
            )

        if reward:
            lines.append(
                f"🎁 Reward : "
                f"{format_money(reward)} FCFA\n"
            )

        lines.append(
            f"📉 Crédit après opération : "
            f"{format_money(transaction['balance_after'])} FCFA\n"
        )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Carte",
                        callback_data=(
                            f"card_view:{card_id}"
                        ),
                    )
                ]
            ]
        ),
    )


# ============================================================
# STATISTIQUES
# ============================================================

async def show_card_stats(
    query,
    character_id: int,
    card_id: int,
):

    card = await get_credit_card(
        card_id
    )

    if card is None:
        await query.edit_message_text(
            "❌ Carte introuvable."
        )
        return

    if int(card["character_id"]) != character_id:
        await query.edit_message_text(
            "❌ Cette carte ne t'appartient pas."
        )
        return

    stats = await get_credit_card_stats(
        card_id
    )

    if not stats.get("success"):
        await query.edit_message_text(
            stats.get(
                "message",
                "❌ Impossible de récupérer les statistiques.",
            )
        )
        return

    text = (
        "📊━━━━━━━━━━━━━━━━━━━━📊\n"
        "       𝗦𝗧𝗔𝗧𝗦 𝗖𝗔𝗥𝗧𝗘\n"
        "📊━━━━━━━━━━━━━━━━━━━━📊\n\n"
        f"💳 Carte : {card['card_name']}\n\n"
        f"🧾 Transactions : "
        f"{stats['transaction_count']}\n"
        f"🛒 Achats : "
        f"{format_money(stats['total_purchases'])} FCFA\n"
        f"🎁 Rewards : "
        f"{format_money(stats['total_rewards'])} FCFA\n\n"
        f"💰 Limite : "
        f"{format_money(stats['credit_limit'])} FCFA\n"
        f"📉 Utilisé : "
        f"{format_money(stats['used_credit'])} FCFA\n"
        f"📊 Disponible : "
        f"{format_money(stats['available_credit'])} FCFA"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Carte",
                        callback_data=(
                            f"card_view:{card_id}"
                        ),
                    )
                ]
            ]
        ),
    )


# ============================================================
# MESSAGE TEXTE — REMBOURSEMENT
# ============================================================

async def card_text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    pending = context.user_data.get(
        "card_pending_payment"
    )

    if not pending:
        return

    actor = await get_life_character(
        user.id
    )

    if actor is None:
        context.user_data.pop(
            "card_pending_payment",
            None,
        )

        await message.reply_text(
            "❌ Personnage MANUWORLD introuvable."
        )
        return

    try:
        amount = int(
            (message.text or "")
            .strip()
            .replace(" ", "")
        )
    except ValueError:
        await message.reply_text(
            "❌ Montant invalide. "
            "Envoie uniquement un nombre."
        )
        return

    card_id = int(
        pending["card_id"]
    )

    context.user_data.pop(
        "card_pending_payment",
        None,
    )

    result = await pay_credit_card(
        character_id=int(actor["id"]),
        card_id=card_id,
        amount=amount,
    )

    await message.reply_text(
        result.get(
            "message",
            "❌ Remboursement impossible.",
        )
    )


# ============================================================
# CALLBACKS
# ============================================================

async def credit_card_callback(
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

    data = query.data or ""

    # --------------------------------------------------------
    # ACCUEIL
    # --------------------------------------------------------

    if data == "card_home":

        await show_card_home(
            query,
            actor,
        )
        return

    # --------------------------------------------------------
    # LISTE
    # --------------------------------------------------------

    if data == "card_list":

        await show_cards(
            query,
            character_id,
        )
        return

    # --------------------------------------------------------
    # DÉTAIL
    # --------------------------------------------------------

    if data.startswith("card_view:"):

        try:
            card_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await show_card(
            query,
            character_id,
            card_id,
        )
        return

    # --------------------------------------------------------
    # HISTORIQUE
    # --------------------------------------------------------

    if data.startswith("card_history:"):

        try:
            card_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await show_card_history(
            query,
            character_id,
            card_id,
        )
        return

    # --------------------------------------------------------
    # STATS
    # --------------------------------------------------------

    if data.startswith("card_stats:"):

        try:
            card_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await show_card_stats(
            query,
            character_id,
            card_id,
        )
        return

    # --------------------------------------------------------
    # PAIEMENT
    # --------------------------------------------------------

    if data.startswith("card_pay:"):

        try:
            card_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        card = await get_credit_card(
            card_id
        )

        if card is None:
            await query.edit_message_text(
                "❌ Carte introuvable."
            )
            return

        if int(card["character_id"]) != character_id:
            await query.edit_message_text(
                "❌ Cette carte ne t'appartient pas."
            )
            return

        await request_card_payment(
            query,
            context,
            card_id,
        )
        return

    # --------------------------------------------------------
    # BLOCAGE
    # --------------------------------------------------------

    if data.startswith("card_block:"):

        try:
            card_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        result = await set_credit_card_status(
            card_id=card_id,
            character_id=character_id,
            status="blocked",
        )

        await query.edit_message_text(
            result.get(
                "message",
                "❌ Impossible de bloquer la carte.",
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Mes cartes",
                            callback_data="card_list",
                        )
                    ]
                ]
            ),
        )
        return

    # --------------------------------------------------------
    # DÉBLOCAGE
    # --------------------------------------------------------

    if data.startswith("card_unblock:"):

        try:
            card_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        result = await set_credit_card_status(
            card_id=card_id,
            character_id=character_id,
            status="active",
        )

        await query.edit_message_text(
            result.get(
                "message",
                "❌ Impossible de débloquer la carte.",
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Mes cartes",
                            callback_data="card_list",
                        )
                    ]
                ]
            ),
        )
        return


# ============================================================
# ENREGISTREMENT
# ============================================================

def register_credit_card_handlers(
    application: Application,
) -> None:
    """
    Enregistre les handlers Telegram des cartes.
    """

    application.add_handler(
        CommandHandler(
            "card",
            card_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            credit_card_callback,
            pattern=r"^card_",
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            card_text_handler,
        )
    )


__all__ = [
    "card_command",
    "credit_card_callback",
    "card_text_handler",
    "register_credit_card_handlers",
]