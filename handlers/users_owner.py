from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import select, func

from database.database import AsyncSessionLocal
from database.models import User

try:
    from config import OWNER_IDS
except ImportError:
    OWNER_IDS = set()


def _is_owner(user_id: int) -> bool:
    return int(user_id) in {int(x) for x in OWNER_IDS}


async def users_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Owner-only command showing every registered bot user."""

    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    if not _is_owner(user.id):
        await message.reply_text(
            "⛔ This command is Owner only."
        )
        return

    async with AsyncSessionLocal() as session:
        total = await session.scalar(
            select(func.count(User.id))
        )

        result = await session.execute(
            select(User).order_by(User.id.asc())
        )
        users = result.scalars().all()

    if not users:
        await message.reply_text(
            "👥 𝐁𝐎𝐓 𝐔𝐒𝐄𝐑𝐒\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📭 No registered users."
        )
        return

    # Telegram messages have a length limit, so split the list.
    header = (
        "👥 𝐁𝐎𝐓 𝐔𝐒𝐄𝐑𝐒\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 Total users: {total or 0}\n\n"
    )

    chunks = []
    current = header

    for index, db_user in enumerate(users, start=1):
        username = (
            f"@{db_user.username}"
            if getattr(db_user, "username", None)
            else "No username"
        )

        first_name = (
            getattr(db_user, "first_name", None)
            or "Unknown"
        )

        line = (
            f"#{index} 👤 {first_name}\n"
            f"   🔹 {username}\n"
            f"   🆔 ID: {db_user.id}\n"
        )

        # Optional fields: only display them if the model has them.
        if hasattr(db_user, "coins"):
            line += (
                f"   💰 Coins: "
                f"{int(db_user.coins or 0):,}\n"
            )

        if hasattr(db_user, "gems"):
            line += (
                f"   💎 Gems: "
                f"{int(db_user.gems or 0):,}\n"
            )

        line += "\n"

        if len(current) + len(line) > 3800:
            chunks.append(current)
            current = header

        current += line

    if current.strip():
        chunks.append(current)

    for chunk in chunks:
        await message.reply_text(chunk)


users_handler = CommandHandler(
    "users",
    users_command,
)
