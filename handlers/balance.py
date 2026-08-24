from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select

from database.database import AsyncSessionLocal
from database.models import User


def _format_amount(value: int) -> str:
    return f"{int(value or 0):,}"


async def balance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                User.id == user.id
            )
        )
        db_user = result.scalar_one_or_none()

    if db_user is None:
        await message.reply_text(
            (
                "❌ Your account was not found.\n"
                "Use /start first."
            )
        )
        return

    await message.reply_text(
        (
            "💰 𝐁𝐀𝐋𝐀𝐍𝐂𝐄\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🪙 Coins : {_format_amount(db_user.coins)}\n"
            f"💎 Gems  : {_format_amount(db_user.gems)}"
        )
    )


balance_handler = CommandHandler(
    "balance",
    balance,
)