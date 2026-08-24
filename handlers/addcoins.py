from __future__ import annotations

from pathlib import Path

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select

from config import OWNER_IDS
from database.database import AsyncSessionLocal
from database.models import User


IMAGE_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "addcoins.jpg"
)


async def _get_user_by_username(
    session,
    username: str,
):
    username = username.strip().lstrip("@")

    if not username:
        return None

    result = await session.execute(
        select(User).where(
            User.username.ilike(username)
        )
    )

    return result.scalar_one_or_none()




# ==========================================================
# /ADDCOINS
# ==========================================================
#
# Owner-only command.
#
# Usage:
#   /addcoins @username <amount>
#
# Example:
#   /addcoins @manager 5000000
#
# Adds game coins to the target User account.
# ==========================================================


async def addcoins(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    owner = update.effective_user

    if (
        message is None
        or owner is None
    ):
        return

    if owner.id not in OWNER_IDS:
        await message.reply_text(
            "⛔ This command is Owner only."
        )
        return

    if len(context.args) != 2:
        await message.reply_text(
            (
                "💰 𝐀𝐃𝐃 𝐂𝐎𝐈𝐍𝐒\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "Usage:\n"
                "/addcoins @username <amount>\n\n"
                "Example:\n"
                "/addcoins @manager 5000000"
            )
        )
        return

    username = context.args[0]

    try:
        amount = int(
            context.args[1]
        )
    except ValueError:
        await message.reply_text(
            "❌ Amount must be a number."
        )
        return

    if amount <= 0:
        await message.reply_text(
            "❌ Amount must be greater than 0."
        )
        return

    async with AsyncSessionLocal() as session:
        target = await _get_user_by_username(
            session,
            username,
        )

        if target is None:
            await message.reply_text(
                "❌ User not found."
            )
            return

        target.coins += amount

        await session.commit()

        new_balance = target.coins
        target_name = (
            f"@{target.username}"
            if target.username
            else f"User #{target.id}"
        )

    await message.reply_photo(
        photo=open(
            IMAGE_FILE,
            "rb",
        ),
        caption=(
            "💰 𝐂𝐎𝐈𝐍𝐒 𝐀𝐃𝐃𝐄𝐃\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 User : {target_name}\n"
            f"➕ Added : {amount:,} Coins\n"
            f"💰 New balance : {new_balance:,} Coins\n\n"
            "✅ Operation completed."
        ),
    )


addcoins_handler = CommandHandler(
    "addcoins",
    addcoins,
)