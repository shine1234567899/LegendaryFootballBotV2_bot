"""
MANUWORLD — LOAN HANDLER

Interface Telegram du système de prêts.

Le moteur métier se trouve dans :
    life_world/systems/loan_system.py

Commande principale :
    /loan

Fonctions :
    🏦 consulter les prêts
    💰 demander un prêt
    💸 rembourser un prêt
    📊 consulter ses statistiques

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

from life_world.systems.bank_system import get_banks

from life_world.systems.loan_system import (
    get_character_loans,
    get_loan,
    get_loan_stats,
    repay_loan,
    request_loan,
)


# ============================================================
# CONSTANTES
# ============================================================

LOAN_LIMIT = 10


# ============================================================
# UTILITAIRES
# ============================================================

def format_money(
    amount: int,
) -> str:
    return f"{int(amount):,}".replace(",", " ")


async def get_actor(
    update: Update,
) -> dict[str, Any] | None:
    """
    Retourne le personnage MANUWORLD lié au compte Telegram.
    """

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
    """
    Vérifie l'existence du personnage.
    """

    actor = await get_actor(update)

    if actor is not None:
        return actor

    message = update.effective_message

    if message is not None:
        await message.reply_text(
            "❌ Tu n'as pas encore créé "
            "ton personnage MANUWORLD."
        )

    return None


# ============================================================
# MENU PRINCIPAL
# ============================================================

def loan_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💰 Mes prêts",
                    callback_data="loan_list",
                ),
                InlineKeyboardButton(
                    "🏦 Demander un prêt",
                    callback_data="loan_request",
                ),
            ],
            [
                InlineKeyboardButton(
                    "📊 Statistiques",
                    callback_data="loan_stats",
                ),
            ],
        ]
    )


async def show_loan_home(
    target,
    actor: dict[str, Any],
):
    loans = await get_character_loans(
        int(actor["id"]),
        active_only=True,
    )

    total_remaining = sum(
        int(loan.get("remaining_balance") or 0)
        for loan in loans
    )

    text = (
        "🏦━━━━━━━━━━━━━━━━━━━━🏦\n"
        "          𝗠𝗔𝗡𝗨𝗪𝗢𝗥𝗟𝗗 𝗟𝗢𝗔𝗡𝗦\n"
        "🏦━━━━━━━━━━━━━━━━━━━━🏦\n\n"
        f"💰 Portefeuille : "
        f"{format_money(actor.get('balance', 0))} FCFA\n"
        f"📋 Prêts actifs : {len(loans)}\n"
        f"📉 Dette restante : "
        f"{format_money(total_remaining)} FCFA\n\n"
        "Choisis une option :"
    )

    await target.edit_message_text(
        text,
        reply_markup=loan_home_keyboard(),
    )


# ============================================================
# /LOAN
# ============================================================

async def loan_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    /loan
    """

    actor = await require_actor(update)

    if actor is None:
        return

    message = update.effective_message

    if message is None:
        return

    loans = await get_character_loans(
        int(actor["id"]),
        active_only=True,
    )

    total_remaining = sum(
        int(loan.get("remaining_balance") or 0)
        for loan in loans
    )

    await message.reply_text(
        (
            "🏦━━━━━━━━━━━━━━━━━━━━🏦\n"
            "          𝗠𝗔𝗡𝗨𝗪𝗢𝗥𝗟𝗗 𝗟𝗢𝗔𝗡𝗦\n"
            "🏦━━━━━━━━━━━━━━━━━━━━🏦\n\n"
            f"💰 Portefeuille : "
            f"{format_money(actor.get('balance', 0))} FCFA\n"
            f"📋 Prêts actifs : {len(loans)}\n"
            f"📉 Dette restante : "
            f"{format_money(total_remaining)} FCFA\n\n"
            "Choisis une option :"
        ),
        reply_markup=loan_home_keyboard(),
    )


# ============================================================
# LISTE DES PRÊTS
# ============================================================

def loans_keyboard(
    loans: list[dict[str, Any]],
) -> InlineKeyboardMarkup:

    buttons = []

    for loan in loans:

        loan_id = int(
            loan["id"]
        )

        bank_name = str(
            loan.get("bank_name")
            or "Banque"
        )

        remaining = int(
            loan.get("remaining_balance") or 0
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"🏦 {bank_name[:18]} — "
                        f"{format_money(remaining)} FCFA"
                    ),
                    callback_data=(
                        f"loan_view:{loan_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Accueil",
                callback_data="loan_home",
            )
        ]
    )

    return InlineKeyboardMarkup(buttons)


async def show_loans(
    query,
    character_id: int,
):
    loans = await get_character_loans(
        character_id,
    )

    if not loans:
        await query.edit_message_text(
            (
                "📋 TU N'AS AUCUN PRÊT\n\n"
                "Tu peux demander un prêt "
                "auprès d'une banque disponible."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏦 Demander un prêt",
                            callback_data="loan_request",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⬅️ Accueil",
                            callback_data="loan_home",
                        )
                    ],
                ]
            ),
        )
        return

    lines = [
        "📋━━━━━━━━━━━━━━━━━━━━📋",
        "          𝗠𝗘𝗦 𝗣𝗥Ê𝗧𝗦",
        "📋━━━━━━━━━━━━━━━━━━━━📋",
        "",
    ]

    for loan in loans:

        status = str(
            loan.get("status")
            or "unknown"
        )

        lines.append(
            f"🏦 {loan['bank_name']}\n"
            f"💰 Emprunté : "
            f"{format_money(loan['principal'])} FCFA\n"
            f"💵 Total : "
            f"{format_money(loan['total_due'])} FCFA\n"
            f"💸 Payé : "
            f"{format_money(loan['amount_paid'])} FCFA\n"
            f"📉 Restant : "
            f"{format_money(loan['remaining_balance'])} FCFA\n"
            f"🔐 Statut : {status}\n"
        )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=loans_keyboard(
            loans
        ),
    )


# ============================================================
# DÉTAIL D'UN PRÊT
# ============================================================

def loan_actions_keyboard(
    loan: dict[str, Any],
) -> InlineKeyboardMarkup:

    loan_id = int(
        loan["id"]
    )

    remaining = int(
        loan.get("remaining_balance") or 0
    )

    buttons = []

    if remaining > 0 and loan.get("status") in (
        "active",
        "overdue",
    ):
        buttons.append(
            [
                InlineKeyboardButton(
                    "💸 Rembourser",
                    callback_data=(
                        f"loan_pay:{loan_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Mes prêts",
                callback_data="loan_list",
            )
        ]
    )

    return InlineKeyboardMarkup(
        buttons
    )


async def show_loan(
    query,
    character_id: int,
    loan_id: int,
):

    loan = await get_loan(
        loan_id
    )

    if loan is None:
        await query.edit_message_text(
            "❌ Prêt introuvable."
        )
        return

    if int(loan["character_id"]) != character_id:
        await query.edit_message_text(
            "❌ Ce prêt ne t'appartient pas."
        )
        return

    interest_rate = float(
        loan.get("interest_rate") or 0
    )

    text = (
        "🏦━━━━━━━━━━━━━━━━━━━━🏦\n"
        "          𝗗𝗘́𝗧𝗔𝗜𝗟 𝗗𝗨 𝗣𝗥Ê𝗧\n"
        "🏦━━━━━━━━━━━━━━━━━━━━🏦\n\n"
        f"🏦 Banque : {loan['bank_name']}\n"
        f"🏷️ Type : {loan['loan_type']}\n\n"
        f"💰 Principal : "
        f"{format_money(loan['principal'])} FCFA\n"
        f"📈 Taux : {interest_rate:g}%\n"
        f"💵 Intérêts : "
        f"{format_money(loan['total_interest'])} FCFA\n"
        f"💳 Total dû : "
        f"{format_money(loan['total_due'])} FCFA\n"
        f"💸 Déjà payé : "
        f"{format_money(loan['amount_paid'])} FCFA\n"
        f"📉 Restant : "
        f"{format_money(loan['remaining_balance'])} FCFA\n\n"
        f"📅 Durée : "
        f"{loan['duration_days']} jours\n"
        f"⏰ Échéance : "
        f"{loan['due_at']}\n"
        f"🔐 Statut : {loan['status']}"
    )

    await query.edit_message_text(
        text,
        reply_markup=loan_actions_keyboard(
            loan
        ),
    )


# ============================================================
# DEMANDE DE PRÊT
# ============================================================

async def show_loan_request(
    query,
):

    banks = await get_banks()

    if not banks:
        await query.edit_message_text(
            (
                "🏦 Aucune banque n'est "
                "actuellement disponible."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Accueil",
                            callback_data="loan_home",
                        )
                    ]
                ]
            ),
        )
        return

    buttons = []

    for bank in banks:

        bank_id = int(
            bank["id"]
        )

        rate = float(
            bank.get("interest_rate") or 0
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"🏦 {bank['name'][:22]} "
                        f"— {rate:g}%"
                    ),
                    callback_data=(
                        f"loan_bank:{bank_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Retour",
                callback_data="loan_home",
            )
        ]
    )

    await query.edit_message_text(
        (
            "💰━━━━━━━━━━━━━━━━━━━━💰\n"
            "       𝗗𝗘𝗠𝗔𝗡𝗗𝗘 𝗗𝗘 𝗣𝗥Ê𝗧\n"
            "💰━━━━━━━━━━━━━━━━━━━━💰\n\n"
            "Choisis la banque auprès de laquelle "
            "tu souhaites demander ton prêt."
        ),
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


async def request_loan_amount(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    bank_id: int,
):

    context.user_data[
        "loan_pending_request"
    ] = {
        "bank_id": int(bank_id),
        "step": "amount",
    }

    await query.edit_message_text(
        (
            "💰 MONTANT DU PRÊT\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Envoie le montant que tu souhaites "
            "emprunter.\n\n"
            "Exemple :\n"
            "`500000`"
        ),
        parse_mode="Markdown",
    )


async def request_loan_duration(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    bank_id: int,
    amount: int,
):

    context.user_data[
        "loan_pending_request"
    ] = {
        "bank_id": int(bank_id),
        "step": "duration",
        "amount": int(amount),
    }

    await query.edit_message_text(
        (
            "📅 DURÉE DU PRÊT\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Envoie le nombre de jours souhaité.\n\n"
            "Exemple :\n"
            "`30`"
        ),
        parse_mode="Markdown",
    )


# ============================================================
# REMBOURSEMENT
# ============================================================

async def request_repayment(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    loan_id: int,
):

    context.user_data[
        "loan_pending_repayment"
    ] = {
        "loan_id": int(loan_id),
    }

    await query.edit_message_text(
        (
            "💸 REMBOURSEMENT\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Envoie le montant que tu souhaites "
            "rembourser.\n\n"
            "Exemple :\n"
            "`100000`"
        ),
        parse_mode="Markdown",
    )


# ============================================================
# STATISTIQUES
# ============================================================

async def show_loan_stats(
    query,
    character_id: int,
):

    stats = await get_loan_stats(
        character_id
    )

    text = (
        "📊━━━━━━━━━━━━━━━━━━━━📊\n"
        "         𝗦𝗧𝗔𝗧𝗦 𝗣𝗥Ê𝗧𝗦\n"
        "📊━━━━━━━━━━━━━━━━━━━━📊\n\n"
        f"📋 Total de prêts : "
        f"{stats['total_loans']}\n"
        f"🏦 Prêts actifs : "
        f"{stats['active_loans']}\n\n"
        f"💰 Total emprunté : "
        f"{format_money(stats['total_borrowed'])} FCFA\n"
        f"💸 Total payé : "
        f"{format_money(stats['total_paid'])} FCFA\n"
        f"📉 Dette restante : "
        f"{format_money(stats['total_remaining'])} FCFA\n"
        f"📈 Intérêts : "
        f"{format_money(stats['total_interest'])} FCFA"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Accueil",
                        callback_data="loan_home",
                    )
                ]
            ]
        ),
    )


# ============================================================
# TEXTE
# ============================================================

async def loan_text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    actor = await get_life_character(
        user.id
    )

    if actor is None:
        return

    # --------------------------------------------------------
    # DEMANDE DE PRÊT
    # --------------------------------------------------------

    pending = context.user_data.get(
        "loan_pending_request"
    )

    if pending:

        step = pending.get("step")

        # ----------------------------------------------------
        # MONTANT
        # ----------------------------------------------------

        if step == "amount":

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

            if amount <= 0:
                await message.reply_text(
                    "❌ Le montant doit être supérieur à 0."
                )
                return

            await request_loan_duration(
                None if False else _MessageQueryProxy(message),
                context,
                int(pending["bank_id"]),
                amount,
            )

            return

        # ----------------------------------------------------
        # DURÉE
        # ----------------------------------------------------

        if step == "duration":

            try:
                duration = int(
                    (message.text or "")
                    .strip()
                    .replace(" ", "")
                )
            except ValueError:
                await message.reply_text(
                    "❌ Durée invalide."
                )
                return

            if duration <= 0:
                await message.reply_text(
                    "❌ La durée doit être supérieure à 0."
                )
                return

            bank_id = int(
                pending["bank_id"]
            )

            amount = int(
                pending["amount"]
            )

            context.user_data.pop(
                "loan_pending_request",
                None,
            )

            result = await request_loan(
                character_id=int(actor["id"]),
                bank_id=bank_id,
                amount=amount,
                duration_days=duration,
            )

            await message.reply_text(
                result.get(
                    "message",
                    "❌ Demande de prêt impossible.",
                )
            )

            return

    # --------------------------------------------------------
    # REMBOURSEMENT
    # --------------------------------------------------------

    pending_payment = context.user_data.get(
        "loan_pending_repayment"
    )

    if pending_payment:

        try:
            amount = int(
                (message.text or "")
                .strip()
                .replace(" ", "")
            )
        except ValueError:
            await message.reply_text(
                "❌ Montant invalide."
            )
            return

        loan_id = int(
            pending_payment["loan_id"]
        )

        context.user_data.pop(
            "loan_pending_repayment",
            None,
        )

        result = await repay_loan(
            character_id=int(actor["id"]),
            loan_id=loan_id,
            amount=amount,
        )

        await message.reply_text(
            result.get(
                "message",
                "❌ Remboursement impossible.",
            )
        )


# ============================================================
# PROXY POUR LES MESSAGES
# ============================================================

class _MessageQueryProxy:
    """
    Petit proxy permettant de réutiliser les fonctions
    d'affichage conçues pour CallbackQuery.

    Il transforme edit_message_text() en reply_text().
    """

    def __init__(
        self,
        message,
    ):
        self.message = message

    async def edit_message_text(
        self,
        text: str,
        **kwargs,
    ):
        return await self.message.reply_text(
            text,
            **kwargs,
        )


# ============================================================
# CALLBACKS
# ============================================================

async def loan_callback(
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

    if data == "loan_home":

        await show_loan_home(
            query,
            actor,
        )
        return

    # --------------------------------------------------------
    # LISTE
    # --------------------------------------------------------

    if data == "loan_list":

        await show_loans(
            query,
            character_id,
        )
        return

    # --------------------------------------------------------
    # STATS
    # --------------------------------------------------------

    if data == "loan_stats":

        await show_loan_stats(
            query,
            character_id,
        )
        return

    # --------------------------------------------------------
    # DEMANDE
    # --------------------------------------------------------

    if data == "loan_request":

        await show_loan_request(
            query
        )
        return

    # --------------------------------------------------------
    # BANQUE
    # --------------------------------------------------------

    if data.startswith("loan_bank:"):

        try:
            bank_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await request_loan_amount(
            query,
            context,
            bank_id,
        )
        return

    # --------------------------------------------------------
    # DÉTAIL
    # --------------------------------------------------------

    if data.startswith("loan_view:"):

        try:
            loan_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await show_loan(
            query,
            character_id,
            loan_id,
        )
        return

    # --------------------------------------------------------
    # REMBOURSEMENT
    # --------------------------------------------------------

    if data.startswith("loan_pay:"):

        try:
            loan_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        loan = await get_loan(
            loan_id
        )

        if loan is None:
            await query.edit_message_text(
                "❌ Prêt introuvable."
            )
            return

        if int(loan["character_id"]) != character_id:
            await query.edit_message_text(
                "❌ Ce prêt ne t'appartient pas."
            )
            return

        await request_repayment(
            query,
            context,
            loan_id,
        )
        return


# ============================================================
# ENREGISTREMENT
# ============================================================

def register_loan_handlers(
    application: Application,
) -> None:
    """
    Enregistre les handlers du système de prêts.

    Le branchement dans main.py sera effectué
    uniquement pendant l'intégration finale.
    """

    application.add_handler(
        CommandHandler(
            "loan",
            loan_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            loan_callback,
            pattern=r"^loan_",
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            loan_text_handler,
        )
    )


__all__ = [
    "loan_command",
    "loan_callback",
    "loan_text_handler",
    "register_loan_handlers",
]