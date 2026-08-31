"""
MANUWORLD — BANK HANDLER [MWL]

/bank
- liste des banques
- détail d'une banque
- ouverture avec dépôt initial
- comptes
- dépôt
- retrait
- historique
"""

from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from life_world.database import get_life_character
from life_world.systems.bank_system import (
    seed_default_banks,
    get_banks,
    get_bank,
    get_character_accounts,
    open_account,
    deposit,
    withdraw,
    get_bank_transactions,
    format_bank,
    format_accounts,
)

BANK_AMOUNT = 1


def account_keyboard(accounts):
    rows = []
    for account in accounts:
        rows.append([
            InlineKeyboardButton(
                f"💳 {account.get('bank_name','Banque')} — {int(account.get('balance') or 0):,} FCFA",
                callback_data=f"mwbank:account:{account['id']}",
            )
        ])
    rows.append([
        InlineKeyboardButton("🏦 Banques", callback_data="mwbank:list")
    ])
    return InlineKeyboardMarkup(rows)


async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    character = await get_life_character(user.id)
    if character is None:
        await message.reply_text("❌ Crée d'abord ton personnage avec /life.")
        return

    await seed_default_banks()
    banks = await get_banks()

    buttons = [
        [InlineKeyboardButton(
            f"{'👑' if int(b.get('prestige') or 0) >= 10 else '🏦'} {b['name']}",
            callback_data=f"mwbank:bank:{b['id']}"
        )]
        for b in banks
    ]
    buttons.append([
        InlineKeyboardButton("💳 Mes comptes", callback_data="mwbank:accounts")
    ])

    await message.reply_text(
        "🏦 **BANQUES MANUWORLD**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Choisis une banque pour voir ses conditions.",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )


async def show_accounts(query, character_id: int):
    accounts = await get_character_accounts(character_id)
    if not accounts:
        await query.edit_message_text(
            "💳 **MES COMPTES**\n\n"
            "Aucun compte bancaire.\n\n"
            "Ouvre un compte depuis la liste des banques.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏦 Banques", callback_data="mwbank:list")]
            ]),
            parse_mode="Markdown",
        )
        return

    await query.edit_message_text(
        "💳 **MES COMPTES BANCAIRES**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "Sélectionne un compte :",
        reply_markup=account_keyboard(accounts),
        parse_mode="Markdown",
    )


async def show_account(query, character_id: int, account_id: int):
    accounts = await get_character_accounts(character_id)
    account = next((a for a in accounts if int(a["id"]) == account_id), None)

    if account is None:
        await query.edit_message_text("❌ Compte introuvable.")
        return

    balance = int(account.get("balance") or 0)
    bank_name = account.get("bank_name") or "Banque"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Déposer", callback_data=f"mwbank:deposit:{account_id}"),
            InlineKeyboardButton("💸 Retirer", callback_data=f"mwbank:withdraw:{account_id}"),
        ],
        [
            InlineKeyboardButton("📜 Historique", callback_data=f"mwbank:history:{account_id}"),
        ],
        [
            InlineKeyboardButton("💳 Mes comptes", callback_data="mwbank:accounts"),
            InlineKeyboardButton("🏦 Banques", callback_data="mwbank:list"),
        ],
    ])

    await query.edit_message_text(
        "💳 **COMPTE BANCAIRE**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏦 Banque : **{bank_name}**\n"
        f"🔢 Compte : `{account['account_number']}`\n"
        f"💰 Solde : **{balance:,} FCFA**\n",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def bank_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    if query is None or user is None:
        return

    await query.answer()

    character = await get_life_character(user.id)
    if character is None:
        await query.edit_message_text("❌ Personnage introuvable.")
        return

    parts = (query.data or "").split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action == "list":
        await query.edit_message_text(
            "🏦 **BANQUES MANUWORLD**\n━━━━━━━━━━━━━━━━━━━━\n\nChoisis une banque :",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    b["name"], callback_data=f"mwbank:bank:{b['id']}"
                )] for b in await get_banks()
            ] + [[InlineKeyboardButton("💳 Mes comptes", callback_data="mwbank:accounts")]]),
            parse_mode="Markdown",
        )
        return

    if action == "accounts":
        await show_accounts(query, int(character["id"]))
        return

    if action == "bank" and len(parts) >= 3:
        bank = await get_bank(int(parts[2]))
        if not bank:
            await query.edit_message_text("❌ Banque introuvable.")
            return

        initial = int(bank.get("initial_deposit") or 0)
        minimum = int(bank.get("minimum_balance") or 0)
        card = bank.get("card_name") or "Aucune"

        await query.edit_message_text(
            f"🏦 **{bank['name']}**\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Dépôt initial : **{initial:,} FCFA**\n"
            f"💵 Solde minimum : **{minimum:,} FCFA**\n"
            f"📈 Intérêt : **{bank['interest_rate']} %**\n"
            f"💳 Carte : **{card}**\n"
            f"🏆 Prestige : **{bank['prestige']}**\n\n"
            "Le dépôt initial est crédité directement sur ton compte.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "💳 Ouvrir un compte",
                    callback_data=f"mwbank:open:{bank['id']}"
                )],
                [InlineKeyboardButton("⬅️ Banques", callback_data="mwbank:list")],
            ]),
            parse_mode="Markdown",
        )
        return

    if action == "open" and len(parts) >= 3:
        result = await open_account(int(character["id"]), int(parts[2]))
        await query.edit_message_text(
            result.get("message", "❌ Impossible d'ouvrir le compte."),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Mes comptes", callback_data="mwbank:accounts")],
                [InlineKeyboardButton("🏦 Banques", callback_data="mwbank:list")],
            ]),
            parse_mode="Markdown",
        )
        return

    if action == "account" and len(parts) >= 3:
        await show_account(query, int(character["id"]), int(parts[2]))
        return

    if action in {"deposit", "withdraw"} and len(parts) >= 3:
        context.user_data["mwbank_pending"] = {
            "action": action,
            "account_id": int(parts[2]),
        }
        verb = "déposer" if action == "deposit" else "retirer"
        await query.edit_message_text(
            f"💳 **OPÉRATION BANCAIRE**\n\n"
            f"Entre le montant à **{verb}** en FCFA.\n"
            "Exemple : `50000`\n\n"
            "Envoie uniquement le nombre.",
            parse_mode="Markdown",
        )
        return BANK_AMOUNT

    if action == "history" and len(parts) >= 3:
        transactions = await get_bank_transactions(int(parts[2]), 20)
        if not transactions:
            body = "Aucune transaction."
        else:
            body = "\n".join(
                f"• {t.get('transaction_type','transaction')} : "
                f"{int(t.get('amount') or 0):,} FCFA"
                for t in transactions
            )
        await query.edit_message_text(
            "📜 **HISTORIQUE BANCAIRE**\n━━━━━━━━━━━━━━━━━━━━\n\n" + body,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Compte", callback_data=f"mwbank:account:{parts[2]}")]
            ]),
        )
        return


async def bank_amount_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return ConversationHandler.END

    pending = context.user_data.get("mwbank_pending")
    if not pending:
        return ConversationHandler.END

    try:
        amount = int((message.text or "").replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("❌ Montant invalide. Envoie un nombre supérieur à 0.")
        return BANK_AMOUNT

    character = await get_life_character(user.id)
    if character is None:
        return ConversationHandler.END

    if pending["action"] == "deposit":
        result = await deposit(
            int(character["id"]),
            pending["account_id"],
            amount,
        )
    else:
        result = await withdraw(
            int(character["id"]),
            pending["account_id"],
            amount,
        )

    context.user_data.pop("mwbank_pending", None)

    await message.reply_text(
        result.get("message", "❌ Opération impossible."),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "💳 Voir le compte",
                callback_data=f"mwbank:account:{pending['account_id']}"
            )],
            [InlineKeyboardButton(
                "🏦 Banques",
                callback_data="mwbank:list"
            )],
        ]),
    )

    return ConversationHandler.END


def register_bank_handlers(application: Application):
    conversation = ConversationHandler(
        entry_points=[
            CommandHandler("bank", bank_command),
            CallbackQueryHandler(bank_callback, pattern=r"^mwbank:"),
        ],
        states={
            BANK_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bank_amount_message),
            ],
        },
        fallbacks=[],
        per_message=False,
        allow_reentry=True,
    )
    application.add_handler(conversation)


__all__ = [
    "bank_command",
    "bank_callback",
    "register_bank_handlers",
]
