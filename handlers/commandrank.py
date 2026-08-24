from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from sqlalchemy import text

from config import OWNER_IDS
from database.database import AsyncSessionLocal

async def commandrank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if user is None or message is None:
        return

    if user.id not in OWNER_IDS:
        await message.reply_text("⛔ This command is Owner only.")
        return

    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                text("""
                    SELECT c.user_id, c.command_count,
                           u.username, u.first_name
                    FROM command_usage c
                    LEFT JOIN users u ON u.id = c.user_id
                    ORDER BY c.command_count DESC, c.user_id ASC
                    LIMIT 10
                """)
            )
        ).all()

    if not rows:
        await message.reply_text(
            "🏆 𝐂𝐎𝐌𝐌𝐀𝐍𝐃 𝐑𝐀𝐍𝐊\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "No command usage recorded yet."
        )
        return

    lines = [
        "🏆 𝐂𝐎𝐌𝐌𝐀𝐍𝐃 𝐑𝐀𝐍𝐊",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    for position, row in enumerate(rows, 1):
        user_id, count, username, first_name = row
        display = f"@{username}" if username else (first_name or f"User {user_id}")
        lines.append(f"{position}. {display} — ⚡ {count}")

    await message.reply_text("\n".join(lines))

commandrank_handler = CommandHandler("commandrank", commandrank)