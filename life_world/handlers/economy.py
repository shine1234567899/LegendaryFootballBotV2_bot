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

        /paylife <telegram_id> <amount>

    The sender must have enough Life Coins.
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
            "/paylife <telegram_id> <montant>\n\n"
            "Exemple :\n"
            "/paylife 123456789 500"
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

    if target_id == user.id:
        await message.reply_text(
            "❌ Tu ne peux pas te payer toi-même."
        )
        return

    async with AsyncSessionLocal() as session:
        sender = await _get_character(session, user.id)
        receiver = await _get_character(session, target_id)

        if sender is None:
            await message.reply_text(
                "❌ Tu n'as pas encore de personnage MANUWORLD.\n"
                "Utilise /life pour commencer."
            )
            return

        if receiver is None:
            await message.reply_text(
                "❌ Le destinataire n'a pas de personnage MANUWORLD."
            )
            return

        # Atomic balance check/update prevents negative balances.
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
                WHERE telegram_id = :receiver_id
                """
            ),
            {
                "amount": amount,
                "receiver_id": target_id,
            },
        )

        await session.commit()

        result = await session.execute(
            text(
                """
                SELECT balance
                FROM life_characters
                WHERE telegram_id = :telegram_id
                """
            ),
            {"telegram_id": user.id},
        )
        sender_balance = result.scalar_one()

    await message.reply_text(
        "💸 𝐏𝐀𝐘𝐌𝐄𝐍𝐓 𝐒𝐄𝐍𝐓\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 From : {sender['first_name']}\n"
        f"➡️ To : {receiver['first_name']}\n"
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
