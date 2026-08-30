from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import text

from config import OWNER_IDS
from database.database import AsyncSessionLocal


# ==========================================================
# MANUWORLD — ECONOMY
# ==========================================================

async def _get_character(session, telegram_id: int):
    result = await session.execute(
        text(
            """
            SELECT id, telegram_id, first_name, balance
            FROM life_characters
            WHERE telegram_id = :telegram_id
            LIMIT 1
            """
        ),
        {"telegram_id": telegram_id},
    )
    return result.mappings().first()


async def addlifecoins(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Owner-only:
        /addlifecoins <telegram_id> <amount>

    Adds Life Coins directly to a player's balance.
    """
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    if user.id not in OWNER_IDS:
        await message.reply_text(
            "⛔ Cette commande est réservée à l'Owner."
        )
        return

    if len(context.args) != 2:
        await message.reply_text(
            "💰 𝐀𝐃𝐃 𝐋𝐈𝐅𝐄 𝐂𝐎𝐈𝐍𝐒\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Utilisation :\n"
            "/addlifecoins <telegram_id> <montant>\n\n"
            "Exemple :\n"
            "/addlifecoins 123456789 5000"
        )
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await message.reply_text(
            "❌ L'ID Telegram et le montant doivent être numériques."
        )
        return

    if amount <= 0:
        await message.reply_text(
            "❌ Le montant doit être supérieur à 0."
        )
        return

    async with AsyncSessionLocal() as session:
        character = await _get_character(session, target_id)

        if character is None:
            await message.reply_text(
                "❌ Aucun personnage MANUWORLD trouvé pour cet utilisateur."
            )
            return

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET balance = balance + :amount
                WHERE telegram_id = :telegram_id
                """
            ),
            {
                "amount": amount,
                "telegram_id": target_id,
            },
        )

        result = await session.execute(
            text(
                """
                SELECT balance
                FROM life_characters
                WHERE telegram_id = :telegram_id
                """
            ),
            {"telegram_id": target_id},
        )
        new_balance = result.scalar_one()

        await session.commit()

    await message.reply_text(
        "💰 𝐋𝐈𝐅𝐄 𝐂𝐎𝐈𝐍𝐒 𝐀𝐃𝐃𝐄𝐃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {character['first_name']}\n"
        f"➕ Amount : {amount:,} LC\n"
        f"💵 New balance : {new_balance:,} LC"
    )


async def paylife(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Player-to-player Life Coins transfer:

        /paylife @username <amount>

    The receiver is resolved by the MANUWORLD username, never by
    Telegram numeric ID.
    """
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    if len(context.args) != 2:
        await message.reply_text(
            "💸 𝐏𝐀𝐘 𝐋𝐈𝐅𝐄\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Utilisation :\n"
            "/paylife @username <montant>\n\n"
            "Exemple :\n"
            "/paylife @shine 500"
        )
        return

    target_username = context.args[0].strip().lstrip("@").lower()

    try:
        amount = int(
            context.args[1].replace(" ", "").replace(",", "")
        )
    except ValueError:
        await message.reply_text(
            "❌ Le montant doit être numérique."
        )
        return

    if not target_username:
        await message.reply_text(
            "❌ Username invalide."
        )
        return

    if amount <= 0:
        await message.reply_text(
            "❌ Le montant doit être supérieur à 0."
        )
        return

    async with AsyncSessionLocal() as session:
        sender = await _get_character(session, user.id)

        receiver_result = await session.execute(
            text(
                """
                SELECT id, telegram_id, first_name, username, balance
                FROM life_characters
                WHERE LOWER(REPLACE(COALESCE(username, ''), '@', ''))
                    = :username
                LIMIT 1
                """
            ),
            {"username": target_username},
        )
        receiver = receiver_result.mappings().first()

        if sender is None:
            await message.reply_text(
                "❌ Tu n'as pas encore de personnage MANUWORLD.\n"
                "Utilise /life pour commencer."
            )
            return

        if receiver is None:
            await message.reply_text(
                f"❌ Le joueur @{target_username} n'a pas été trouvé."
            )
            return

        if int(receiver["telegram_id"]) == int(user.id):
            await message.reply_text(
                "❌ Tu ne peux pas te payer toi-même."
            )
            return

        result = await session.execute(
            text(
                """
                UPDATE life_characters
                SET balance = balance - :amount
                WHERE telegram_id = :sender_id
                  AND balance >= :amount
                """
            ),
            {
                "amount": amount,
                "sender_id": user.id,
            },
        )

        if result.rowcount != 1:
            await session.rollback()
            await message.reply_text(
                "❌ Solde insuffisant."
            )
            return

        await session.execute(
            text(
                """
                UPDATE life_characters
                SET balance = balance + :amount
                WHERE id = :receiver_id
                """
            ),
            {
                "amount": amount,
                "receiver_id": int(receiver["id"]),
            },
        )

        await session.commit()

        balance_result = await session.execute(
            text(
                """
                SELECT balance
                FROM life_characters
                WHERE telegram_id = :telegram_id
                """
            ),
            {"telegram_id": user.id},
        )
        sender_balance = balance_result.scalar_one()

    receiver_name = receiver["first_name"] or f"@{target_username}"

    await message.reply_text(
        "💸 𝐏𝐀𝐘𝐌𝐄𝐍𝐓 𝐒𝐄𝐍𝐓\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 From : {sender['first_name']}\n"
        f"➡️ To : {receiver_name} (@{target_username})\n"
        f"💰 Amount : {amount:,} LC\n"
        f"💵 Remaining balance : {sender_balance:,} LC"
    )


addlifecoins_handler = CommandHandler(
    "addlifecoins",
    addlifecoins,
)

paylife_handler = CommandHandler(
    "paylife",
    paylife,
)
