from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import text

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from life_world.utils.targeting import resolve_target


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
    """Transfer Life Coins using a reply or @username lookup.

    The recipient is always identified internally by Telegram ID.
    """
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    if len(context.args) == 1:
        amount_text = context.args[0]
    elif len(context.args) == 2:
        amount_text = context.args[1]
    else:
        await message.reply_text(
            "💸 𝐏𝐀𝐘 𝐋𝐈𝐅𝐄\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "• Réponds au message d'un joueur : `/paylife 500`\n"
            "• Ou utilise : `/paylife @username 500`"
        )
        return

    try:
        amount = int(amount_text.replace(" ", "").replace(",", ""))
    except ValueError:
        await message.reply_text("❌ Le montant doit être numérique.")
        return

    if amount <= 0:
        await message.reply_text("❌ Le montant doit être supérieur à 0.")
        return

    target_result = await resolve_target(update, allow_self=False)
    if target_result.character is None or target_result.error:
        await message.reply_text(
            target_result.error or "❌ Joueur introuvable."
        )
        return

    receiver_id = int(
        target_result.telegram_id
        or target_result.character["telegram_id"]
    )
    receiver = dict(target_result.character)

    async with AsyncSessionLocal() as session:
        sender = await _get_character(session, user.id)
        if sender is None:
            await message.reply_text(
                "❌ Tu n'as pas encore de personnage MANUWORLD.\n"
                "Utilise /life pour commencer."
            )
            return

        sender_result = await session.execute(
            text("""
                SELECT id, telegram_id, first_name, username, balance
                FROM life_characters
                WHERE telegram_id=:sender_id
                FOR UPDATE
            """),
            {"sender_id": int(user.id)},
        )
        sender_row = sender_result.mappings().first()

        receiver_result = await session.execute(
            text("""
                SELECT id, telegram_id, first_name, username, balance
                FROM life_characters
                WHERE telegram_id=:receiver_id
                FOR UPDATE
            """),
            {"receiver_id": receiver_id},
        )
        receiver_row = receiver_result.mappings().first()

        if sender_row is None or receiver_row is None:
            await session.rollback()
            await message.reply_text("❌ Joueur introuvable.")
            return

        if int(sender_row["balance"] or 0) < amount:
            await session.rollback()
            await message.reply_text("❌ Solde insuffisant.")
            return

        await session.execute(
            text("""
                UPDATE life_characters
                SET balance=balance-:amount, updated_at=NOW()
                WHERE telegram_id=:sender_id
            """),
            {"amount": amount, "sender_id": int(user.id)},
        )
        await session.execute(
            text("""
                UPDATE life_characters
                SET balance=balance+:amount, updated_at=NOW()
                WHERE telegram_id=:receiver_id
            """),
            {"amount": amount, "receiver_id": receiver_id},
        )
        await session.commit()

        balance_result = await session.execute(
            text("""
                SELECT balance FROM life_characters
                WHERE telegram_id=:telegram_id
            """),
            {"telegram_id": int(user.id)},
        )
        sender_balance = int(balance_result.scalar_one())

    target_username = str(
        receiver.get("username") or ""
    ).strip().lstrip("@")
    receiver_name = receiver.get("first_name") or target_username or "Joueur"

    await message.reply_text(
        "💸 𝐏𝐀𝐘𝐌𝐄𝐍𝐓 𝐒𝐄𝐍𝐓\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 From : {sender['first_name']}\n"
        f"➡️ To : {receiver_name}"
        + (f" (@{target_username})" if target_username else "")
        + f"\n💰 Amount : {amount:,} LC\n"
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
