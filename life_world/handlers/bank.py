"""
MANUWORLD — BANK HANDLER

Interface Telegram du système bancaire.

Commandes :

    /bank

Fonctions :

    🏦 consulter les banques
    💳 consulter ses comptes
    ➕ ouvrir un compte
    💰 déposer
    💸 retirer
    🔄 transférer
    🧾 historique

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

from life_world.systems.bank_system import (
    deposit_to_bank,
    get_bank,
    get_bank_account,
    get_bank_account_by_number,
    get_banks,
    get_character_bank_accounts,
    get_bank_transactions,
    open_bank_account,
    transfer_bank_money,
    withdraw_from_bank,
)


# ============================================================
# CONSTANTES
# ============================================================

BANKS_PAGE_SIZE = 6
ACCOUNTS_PAGE_SIZE = 6
TRANSACTIONS_PAGE_SIZE = 10


# ============================================================
# UTILITAIRES
# ============================================================

def format_money(amount: int) -> str:
    return f"{int(amount):,}".replace(",", " ")


def format_account_number(
    account_number: str,
) -> str:
    """
    Formate un numéro de compte pour l'affichage.

    Exemple :
        123456789012
        ->
        1234 5678 9012
    """

    value = str(account_number or "")

    return " ".join(
        value[index:index + 4]
        for index in range(0, len(value), 4)
    )


async def get_actor(
    update: Update,
) -> dict[str, Any] | None:
    """
    Retourne le personnage MANUWORLD du joueur Telegram.
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
    Vérifie que le joueur possède un personnage MANUWORLD.
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

def bank_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏦 Banques",
                    callback_data="bank_banks",
                ),
                InlineKeyboardButton(
                    "💳 Mes comptes",
                    callback_data="bank_accounts",
                ),
            ],
            [
                InlineKeyboardButton(
                    "➕ Ouvrir un compte",
                    callback_data="bank_open",
                ),
            ],
        ]
    )


async def show_bank_menu(
    target,
    actor: dict[str, Any],
):
    """
    Affiche le menu bancaire principal.
    """

    wallet = int(
        actor.get("balance") or 0
    )

    text = (
        "🏦━━━━━━━━━━━━━━━━━━━━🏦\n"
        "        𝗠𝗔𝗡𝗨𝗪𝗢𝗥𝗟𝗗 𝗕𝗔𝗡𝗞\n"
        "🏦━━━━━━━━━━━━━━━━━━━━🏦\n\n"
        f"👤 {actor.get('first_name', 'Joueur')}\n"
        f"💰 Portefeuille : "
        f"{format_money(wallet)} FCFA\n\n"
        "Bienvenue dans le système bancaire "
        "de MANUWORLD.\n\n"
        "Choisis une option :"
    )

    await target.edit_message_text(
        text,
        reply_markup=bank_main_keyboard(),
    )


# ============================================================
# /BANK
# ============================================================

async def bank_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    /bank
    """

    actor = await require_actor(update)

    if actor is None:
        return

    message = update.effective_message

    if message is None:
        return

    await message.reply_text(
        (
            "🏦━━━━━━━━━━━━━━━━━━━━🏦\n"
            "        𝗠𝗔𝗡𝗨𝗪𝗢𝗥𝗟𝗗 𝗕𝗔𝗡𝗞\n"
            "🏦━━━━━━━━━━━━━━━━━━━━🏦\n\n"
            f"💰 Portefeuille : "
            f"{format_money(actor.get('balance', 0))} FCFA\n\n"
            "Choisis une option :"
        ),
        reply_markup=bank_main_keyboard(),
    )


# ============================================================
# BANQUES
# ============================================================

def banks_keyboard(
    banks: list[dict[str, Any]],
) -> InlineKeyboardMarkup:

    buttons: list[list[InlineKeyboardButton]] = []

    for bank in banks:

        bank_id = int(bank["id"])

        name = str(
            bank.get("name")
            or "Banque"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"🏦 {name[:30]}",
                    callback_data=(
                        f"bank_info:{bank_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Retour",
                callback_data="bank_home",
            )
        ]
    )

    return InlineKeyboardMarkup(buttons)


async def show_banks(
    query,
):
    banks = await get_banks()

    if not banks:
        await query.edit_message_text(
            (
                "🏦 Aucune banque n'est actuellement "
                "disponible."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Retour",
                            callback_data="bank_home",
                        )
                    ]
                ]
            ),
        )
        return

    lines = [
        "🏦━━━━━━━━━━━━━━━━━━━━🏦",
        "          𝗕𝗔𝗡𝗤𝗨𝗘𝗦",
        "🏦━━━━━━━━━━━━━━━━━━━━🏦",
        "",
        "Sélectionne une banque :",
        "",
    ]

    for bank in banks:
        rate = float(
            bank.get("interest_rate") or 0
        )

        lines.append(
            f"🏦 {bank['name']}\n"
            f"   📈 Intérêt : {rate:g}%\n"
            f"   💳 Ouverture : "
            f"{format_money(bank.get('account_fee', 0))} FCFA\n"
        )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=banks_keyboard(
            banks
        ),
    )


# ============================================================
# INFORMATIONS BANQUE
# ============================================================

async def show_bank_info(
    query,
    bank_id: int,
):
    bank = await get_bank(
        bank_id
    )

    if bank is None:
        await query.edit_message_text(
            "❌ Banque introuvable."
        )
        return

    rate = float(
        bank.get("interest_rate") or 0
    )

    maximum = bank.get(
        "maximum_balance"
    )

    maximum_text = (
        "Illimité"
        if maximum is None
        else f"{format_money(maximum)} FCFA"
    )

    text = (
        "🏦━━━━━━━━━━━━━━━━━━━━🏦\n"
        "       𝗜𝗡𝗙𝗢𝗦 𝗕𝗔𝗡𝗤𝗨𝗘\n"
        "🏦━━━━━━━━━━━━━━━━━━━━🏦\n\n"
        f"🏦 Nom : {bank['name']}\n"
        f"🏷️ Type : {bank['bank_type']}\n"
        f"⭐ Prestige : {bank['prestige']}\n\n"
        f"📈 Taux : {rate:g}%\n"
        f"💳 Frais d'ouverture : "
        f"{format_money(bank['account_fee'])} FCFA\n"
        f"🔄 Frais de transfert : "
        f"{format_money(bank['transfer_fee'])} FCFA\n"
        f"📉 Solde minimum : "
        f"{format_money(bank['minimum_balance'])} FCFA\n"
        f"📈 Plafond : {maximum_text}"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ Ouvrir ici",
                    callback_data=(
                        f"bank_open_here:{bank_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Banques",
                    callback_data="bank_banks",
                )
            ],
        ]
    )

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
    )


# ============================================================
# COMPTES DU JOUEUR
# ============================================================

def account_keyboard(
    accounts: list[dict[str, Any]],
) -> InlineKeyboardMarkup:

    buttons: list[list[InlineKeyboardButton]] = []

    for account in accounts:

        account_id = int(
            account["id"]
        )

        name = str(
            account.get("bank_name")
            or "Banque"
        )

        balance = int(
            account.get("balance") or 0
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"💳 {name[:20]} — "
                        f"{format_money(balance)} FCFA"
                    ),
                    callback_data=(
                        f"bank_account:{account_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Retour",
                callback_data="bank_home",
            )
        ]
    )

    return InlineKeyboardMarkup(buttons)


async def show_accounts(
    query,
    character_id: int,
):
    accounts = await get_character_bank_accounts(
        character_id
    )

    if not accounts:
        await query.edit_message_text(
            (
                "💳 TU N'AS AUCUN COMPTE\n\n"
                "Tu peux ouvrir ton premier "
                "compte bancaire."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "➕ Ouvrir un compte",
                            callback_data="bank_open",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "⬅️ Retour",
                            callback_data="bank_home",
                        )
                    ],
                ]
            ),
        )
        return

    lines = [
        "💳━━━━━━━━━━━━━━━━━━━━💳",
        "        𝗠𝗘𝗦 𝗖𝗢𝗠𝗣𝗧𝗘𝗦",
        "💳━━━━━━━━━━━━━━━━━━━━💳",
        "",
    ]

    for account in accounts:
        lines.append(
            f"🏦 {account['bank_name']}\n"
            f"🔢 "
            f"{format_account_number(account['account_number'])}\n"
            f"💰 "
            f"{format_money(account['balance'])} FCFA\n"
        )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=account_keyboard(
            accounts
        ),
    )


# ============================================================
# DÉTAIL D'UN COMPTE
# ============================================================

def account_actions_keyboard(
    account_id: int,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💰 Déposer",
                    callback_data=(
                        f"bank_deposit:{account_id}"
                    ),
                ),
                InlineKeyboardButton(
                    "💸 Retirer",
                    callback_data=(
                        f"bank_withdraw:{account_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔄 Transférer",
                    callback_data=(
                        f"bank_transfer:{account_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "🧾 Historique",
                    callback_data=(
                        f"bank_history:{account_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Mes comptes",
                    callback_data="bank_accounts",
                )
            ],
        ]
    )


async def show_account(
    query,
    character_id: int,
    account_id: int,
):
    account = await get_bank_account(
        account_id
    )

    if account is None:
        await query.edit_message_text(
            "❌ Compte introuvable."
        )
        return

    if int(account["character_id"]) != character_id:
        await query.edit_message_text(
            "❌ Ce compte ne t'appartient pas."
        )
        return

    rate = float(
        account.get("interest_rate") or 0
    )

    text = (
        "💳━━━━━━━━━━━━━━━━━━━━💳\n"
        "        𝗖𝗢𝗠𝗣𝗧𝗘 𝗕𝗔𝗡𝗖𝗔𝗜𝗥𝗘\n"
        "💳━━━━━━━━━━━━━━━━━━━━💳\n\n"
        f"🏦 Banque : {account['bank_name']}\n"
        f"🔢 Compte : "
        f"{format_account_number(account['account_number'])}\n"
        f"💰 Solde : "
        f"{format_money(account['balance'])} FCFA\n"
        f"📈 Intérêt : {rate:g}%\n"
        f"💵 Intérêts cumulés : "
        f"{format_money(account['interest_accrued'])} FCFA\n"
        f"📊 Statut : {account['status']}"
    )

    await query.edit_message_text(
        text,
        reply_markup=account_actions_keyboard(
            account_id
        ),
    )


# ============================================================
# OUVERTURE DE COMPTE
# ============================================================

async def show_open_account(
    query,
):
    banks = await get_banks()

    if not banks:
        await query.edit_message_text(
            "❌ Aucune banque disponible."
        )
        return

    buttons = []

    for bank in banks:

        bank_id = int(
            bank["id"]
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"🏦 {bank['name'][:25]} "
                        f"— {format_money(bank['account_fee'])} FCFA"
                    ),
                    callback_data=(
                        f"bank_open_here:{bank_id}"
                    ),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Retour",
                callback_data="bank_home",
            )
        ]
    )

    await query.edit_message_text(
        (
            "➕━━━━━━━━━━━━━━━━━━━━➕\n"
            "       𝗢𝗨𝗩𝗥𝗜𝗥 𝗨𝗡 𝗖𝗢𝗠𝗣𝗧𝗘\n"
            "➕━━━━━━━━━━━━━━━━━━━━➕\n\n"
            "Choisis la banque dans laquelle "
            "tu veux ouvrir ton compte :"
        ),
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


async def open_account(
    query,
    character_id: int,
    bank_id: int,
):
    result = await open_bank_account(
        character_id=character_id,
        bank_id=bank_id,
    )

    await query.edit_message_text(
        result.get(
            "message",
            "❌ Impossible d'ouvrir le compte.",
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💳 Mes comptes",
                        callback_data="bank_accounts",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏦 Accueil",
                        callback_data="bank_home",
                    )
                ],
            ]
        ),
    )


# ============================================================
# OPÉRATION — DEMANDE DE MONTANT
# ============================================================

async def request_amount(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    action: str,
    account_id: int,
):
    """
    Met le joueur en attente d'un montant.
    """

    context.user_data[
        "bank_pending_action"
    ] = {
        "action": action,
        "account_id": int(account_id),
    }

    labels = {
        "deposit": "💰 DÉPÔT",
        "withdraw": "💸 RETRAIT",
    }

    label = labels.get(
        action,
        "💳 OPÉRATION",
    )

    await query.edit_message_text(
        (
            f"{label}\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Envoie maintenant le montant.\n\n"
            "Exemple :\n"
            "`50000`"
        ),
        parse_mode="Markdown",
    )


# ============================================================
# TRANSFERT
# ============================================================

async def request_transfer(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    account_id: int,
):
    context.user_data[
        "bank_pending_transfer"
    ] = {
        "account_id": int(account_id),
        "step": "account",
    }

    await query.edit_message_text(
        (
            "🔄 TRANSFERT BANCAIRE\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "Envoie le numéro de compte "
            "du destinataire.\n\n"
            "Exemple :\n"
            "`123456789012`"
        ),
        parse_mode="Markdown",
    )


# ============================================================
# HISTORIQUE
# ============================================================

async def show_history(
    query,
    character_id: int,
    account_id: int,
):
    account = await get_bank_account(
        account_id
    )

    if account is None:
        await query.edit_message_text(
            "❌ Compte introuvable."
        )
        return

    if int(account["character_id"]) != character_id:
        await query.edit_message_text(
            "❌ Ce compte ne t'appartient pas."
        )
        return

    transactions = await get_bank_transactions(
        account_id,
        limit=TRANSACTIONS_PAGE_SIZE,
    )

    if not transactions:
        await query.edit_message_text(
            (
                "🧾 Aucun mouvement enregistré "
                "sur ce compte."
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Compte",
                            callback_data=(
                                f"bank_account:{account_id}"
                            ),
                        )
                    ]
                ]
            ),
        )
        return

    lines = [
        "🧾━━━━━━━━━━━━━━━━━━━━🧾",
        "        𝗛𝗜𝗦𝗧𝗢𝗥𝗜𝗤𝗨𝗘",
        "🧾━━━━━━━━━━━━━━━━━━━━🧾",
        "",
    ]

    for transaction in transactions:

        amount = int(
            transaction["amount"] or 0
        )

        sign = "+" if amount >= 0 else ""

        description = (
            transaction.get("description")
            or transaction.get("transaction_type")
            or "Opération"
        )

        lines.append(
            f"• {description}\n"
            f"  💵 {sign}{format_money(amount)} FCFA\n"
            f"  🏦 Solde : "
            f"{format_money(transaction['balance_after'])} FCFA\n"
        )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Compte",
                        callback_data=(
                            f"bank_account:{account_id}"
                        ),
                    )
                ]
            ]
        ),
    )


# ============================================================
# RÉCEPTION DES MESSAGES TEXTE
# ============================================================

async def bank_text_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Gère les montants et numéros de compte envoyés
    après une demande du système bancaire.
    """

    message = update.effective_message

    if message is None:
        return

    user = update.effective_user

    if user is None:
        return

    actor = await get_life_character(
        user.id
    )

    if actor is None:
        return

    text_value = (
        message.text or ""
    ).strip()

    # --------------------------------------------------------
    # MONTANT
    # --------------------------------------------------------

    pending = context.user_data.get(
        "bank_pending_action"
    )

    if pending:

        try:
            amount = int(
                text_value.replace(" ", "")
            )
        except ValueError:
            await message.reply_text(
                "❌ Montant invalide. Envoie uniquement "
                "un nombre."
            )
            return

        action = pending["action"]
        account_id = int(
            pending["account_id"]
        )

        context.user_data.pop(
            "bank_pending_action",
            None,
        )

        if action == "deposit":

            result = await deposit_to_bank(
                character_id=int(actor["id"]),
                account_id=account_id,
                amount=amount,
            )

        elif action == "withdraw":

            result = await withdraw_from_bank(
                character_id=int(actor["id"]),
                account_id=account_id,
                amount=amount,
            )

        else:
            await message.reply_text(
                "❌ Opération bancaire inconnue."
            )
            return

        await message.reply_text(
            result.get(
                "message",
                "❌ Opération impossible.",
            )
        )

        return

    # --------------------------------------------------------
    # TRANSFERT
    # --------------------------------------------------------

    transfer = context.user_data.get(
        "bank_pending_transfer"
    )

    if transfer:

        step = transfer.get("step")
        account_id = int(
            transfer["account_id"]
        )

        if step == "account":

            destination = await get_bank_account_by_number(
                text_value
            )

            if destination is None:
                await message.reply_text(
                    "❌ Compte destinataire introuvable.\n"
                    "Vérifie le numéro puis réessaie."
                )
                return

            transfer["destination"] = (
                destination["account_number"]
            )

            transfer["step"] = "amount"

            await message.reply_text(
                (
                    "🔄 DESTINATAIRE TROUVÉ\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🏦 Banque : "
                    f"{destination['bank_name']}\n"
                    f"🔢 Compte : "
                    f"{format_account_number(destination['account_number'])}\n\n"
                    "Envoie maintenant le montant "
                    "à transférer."
                )
            )

            return

        if step == "amount":

            try:
                amount = int(
                    text_value.replace(" ", "")
                )
            except ValueError:
                await message.reply_text(
                    "❌ Montant invalide."
                )
                return

            destination_number = transfer.get(
                "destination"
            )

            context.user_data.pop(
                "bank_pending_transfer",
                None,
            )

            if not destination_number:
                await message.reply_text(
                    "❌ Destinataire introuvable."
                )
                return

            result = await transfer_bank_money(
                character_id=int(actor["id"]),
                source_account_id=account_id,
                destination_account_number=(
                    destination_number
                ),
                amount=amount,
            )

            await message.reply_text(
                result.get(
                    "message",
                    "❌ Transfert impossible.",
                )
            )

            return


# ============================================================
# CALLBACKS
# ============================================================

async def bank_callback(
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

    data = query.data or ""

    character_id = int(
        actor["id"]
    )

    # --------------------------------------------------------
    # ACCUEIL
    # --------------------------------------------------------

    if data == "bank_home":

        await show_bank_menu(
            query,
            actor,
        )
        return

    # --------------------------------------------------------
    # BANQUES
    # --------------------------------------------------------

    if data == "bank_banks":

        await show_banks(
            query
        )
        return

    # --------------------------------------------------------
    # INFO BANQUE
    # --------------------------------------------------------

    if data.startswith("bank_info:"):

        try:
            bank_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await show_bank_info(
            query,
            bank_id,
        )
        return

    # --------------------------------------------------------
    # OUVRIR COMPTE
    # --------------------------------------------------------

    if data == "bank_open":

        await show_open_account(
            query
        )
        return

    if data.startswith("bank_open_here:"):

        try:
            bank_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await open_account(
            query,
            character_id,
            bank_id,
        )
        return

    # --------------------------------------------------------
    # COMPTES
    # --------------------------------------------------------

    if data == "bank_accounts":

        await show_accounts(
            query,
            character_id,
        )
        return

    # --------------------------------------------------------
    # COMPTE
    # --------------------------------------------------------

    if data.startswith("bank_account:"):

        try:
            account_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await show_account(
            query,
            character_id,
            account_id,
        )
        return

    # --------------------------------------------------------
    # DÉPÔT
    # --------------------------------------------------------

    if data.startswith("bank_deposit:"):

        try:
            account_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        account = await get_bank_account(
            account_id
        )

        if account is None:
            await query.edit_message_text(
                "❌ Compte introuvable."
            )
            return

        if int(account["character_id"]) != character_id:
            await query.edit_message_text(
                "❌ Ce compte ne t'appartient pas."
            )
            return

        await request_amount(
            query,
            context,
            "deposit",
            account_id,
        )
        return

    # --------------------------------------------------------
    # RETRAIT
    # --------------------------------------------------------

    if data.startswith("bank_withdraw:"):

        try:
            account_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        account = await get_bank_account(
            account_id
        )

        if account is None:
            await query.edit_message_text(
                "❌ Compte introuvable."
            )
            return

        if int(account["character_id"]) != character_id:
            await query.edit_message_text(
                "❌ Ce compte ne t'appartient pas."
            )
            return

        await request_amount(
            query,
            context,
            "withdraw",
            account_id,
        )
        return

    # --------------------------------------------------------
    # TRANSFERT
    # --------------------------------------------------------

    if data.startswith("bank_transfer:"):

        try:
            account_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        account = await get_bank_account(
            account_id
        )

        if account is None:
            await query.edit_message_text(
                "❌ Compte introuvable."
            )
            return

        if int(account["character_id"]) != character_id:
            await query.edit_message_text(
                "❌ Ce compte ne t'appartient pas."
            )
            return

        await request_transfer(
            query,
            context,
            account_id,
        )
        return

    # --------------------------------------------------------
    # HISTORIQUE
    # --------------------------------------------------------

    if data.startswith("bank_history:"):

        try:
            account_id = int(
                data.split(":")[1]
            )
        except (ValueError, IndexError):
            return

        await show_history(
            query,
            character_id,
            account_id,
        )
        return


# ============================================================
# ENREGISTREMENT
# ============================================================

def register_bank_handlers(
    application: Application,
) -> None:
    """
    Enregistre les handlers bancaires.

    Le branchement dans main.py sera fait lors
    de l'intégration finale.
    """

    application.add_handler(
        CommandHandler(
            "bank",
            bank_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            bank_callback,
            pattern=r"^bank_",
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            bank_text_handler,
        )
    )


__all__ = [
    "bank_command",
    "bank_callback",
    "bank_text_handler",
    "register_bank_handlers",
]